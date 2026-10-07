"""The audio of a part, as every route keyed by a uuid sees it (implementation 02, plan P-6).

Before implementation 02, Phase 3, a piece was one folder ``data/audio/<uuid>/`` with a
``metadata.json``. Now the uuid is the id of a **part** of a project bundle (section 8.3), and this
module keeps the functions every reader already calls (:func:`get`, :func:`read_metadata`,
:func:`update`, :func:`set_cuts` ...) on top of the bundle:

==========================  =====================================================================
``AudioMetadata`` field     Where it is stored now
==========================  =====================================================================
``uuid``                    the id of the part
``alias``                   ``project.json`` ``title``
``createdAt``, ``frameMs``  ``project.json``
``source``, ``format``,     ``project.json`` ``parts[].source``: ``kind``, ``format``,
the file facts              ``originalFilename``, ``durationSeconds``, ``sampleRate``, ``url`` ...
``cuts``, ``audioRevision`` ``timeline.json``: the cuts are the gaps between its segments
==========================  =====================================================================

The audio file itself is in the audio store, ``.database/audio/<sha256>.<ext>``
(:mod:`aitu_backend.storage.audio_files`), and never changes. ``normalized.wav`` (16 kHz mono, the
engine's input) and ``waveform.json`` are derived files in the part's ``cache/`` folder, written
again from the stored file when they are missing.

**A part of several files** (**add audio**, Phase 5): its files are laid end to end, and the
"original" is that axis. ``normalized.wav`` is the files' 16 kHz copies joined, and the original
the Audio step plays is a joined FLAC (:mod:`aitu_backend.audio.sources`). ``durationSeconds`` is
the length of the axis, and the cuts are ranges of it. :func:`append` adds a file;
:func:`rename_file`, :func:`reorder_files` and :func:`remove_file` change the list (the Source
step), and :func:`files_of` describes it.

**Every filesystem access for the audio of a part goes through this module** (and
:mod:`aitu_backend.audio.sources` for the joined files of a part of several files).
"""

from __future__ import annotations

import json
import math
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Iterable

from aitu_backend.audio import formats, sources
from aitu_backend.db.users import current_user_id
from aitu_backend.schemas.metadata import AudioMetadata, AudioSource, TimeRange
from aitu_backend.storage import audio_files, bundle, locate, paths
from aitu_backend.storage.bundle import AudioEntry, PartSource, Segment, SourceFile, Timeline

#: Copied in chunks so a large upload never lands in memory whole.
COPY_CHUNK_BYTES = audio_files.CHUNK_BYTES


class AudioNotFound(KeyError):
    """No part with the requested uuid."""

    def __init__(self, audio_uuid: str) -> None:
        self.audio_uuid = audio_uuid
        super().__init__(f"No audio with uuid '{audio_uuid}'")


@dataclass(frozen=True)
class StoredAudio:
    """A part: its metadata, its stored audio file, and its folder of derived files."""

    metadata: AudioMetadata
    #: ``<project>/cache/<partId>/``: derived files and scratch clips of this part.
    directory: Path
    #: The file in the audio store, or ``None`` before the first audio arrives. For a part of
    #: several files, the joined FLAC in the cache, which may not be written yet: read it through
    #: :func:`original_file`.
    original_path: Path | None = None
    #: The timeline the entry was read from.
    timeline: Timeline | None = None

    @property
    def joined(self) -> bool:
        """Several files laid end to end (``timeline.sources``)."""
        return self.timeline is not None and len(self.timeline.source_list()) > 1

    @property
    def uuid(self) -> str:
        return self.metadata.uuid

    @property
    def normalized_path(self) -> Path:
        return self.directory / "normalized.wav"

    @property
    def waveform_path(self) -> Path:
        return self.directory / "waveform.json"

    def has_normalized(self) -> bool:
        return self.normalized_path.is_file()


# ------------------------------------------------------------------ helpers


def _project_of(audio_uuid: str) -> bundle.ProjectFile:
    try:
        where = locate.part(audio_uuid)
        return bundle.read_project(where.project_id)
    except locate.NotFound:
        raise AudioNotFound(audio_uuid) from None


def _metadata(project: bundle.ProjectFile, part_id: str, timeline: Timeline) -> AudioMetadata:
    source = project.part(part_id).source
    duration = source.duration_seconds
    if len(timeline.source_list()) > 1:
        frames = timeline.axis_frames()
        duration = None if frames is None else frames * bundle.FRAME_MS / 1000.0
    return AudioMetadata.model_validate(
        {
            "uuid": part_id,
            "alias": project.title,
            "source": source.kind,
            "format": source.format or "wav",
            "originalFilename": source.original_filename,
            "durationSeconds": duration,
            "sampleRate": source.sample_rate,
            "sourceUrl": source.url,
            "sourceAudioUuid": source.source_audio_uuid,
            "sourceTimeRange": source.source_time_range,
            "frameMs": project.frame_ms,
            "createdAt": project.created_at,
            "cuts": bundle.cuts_of(timeline),
            "audioRevision": timeline.audio_revision,
        }
    )


def _source_of(metadata: AudioMetadata, files: list[SourceFile] | None = None) -> PartSource:
    return PartSource(
        kind=metadata.source.value,
        format=metadata.format,
        original_filename=metadata.original_filename,
        duration_seconds=metadata.duration_seconds,
        sample_rate=metadata.sample_rate,
        url=metadata.source_url,
        source_audio_uuid=metadata.source_audio_uuid,
        source_time_range=(
            metadata.source_time_range.model_dump(by_alias=True)
            if metadata.source_time_range
            else None
        ),
        files=list(files or []),
    )


def _original_of(part_id: str, timeline: Timeline) -> Path | None:
    files = timeline.source_list()
    if not files:
        return None
    if len(files) > 1:
        return sources.listen_path(part_id, timeline)
    return audio_files.file_path(files[0], timeline.audio[files[0]].format)


def original_file(entry: StoredAudio) -> Path | None:
    """The original of a part, ready to read: its one stored file, or, for a part of several
    files, their joined FLAC (written now when it is missing)."""
    if entry.joined and entry.timeline is not None:
        return sources.ensure_listen(entry.uuid, entry.timeline)
    return entry.original_path


_normalize_locks: dict[str, threading.Lock] = {}
_normalize_guard = threading.Lock()


def _restore_normalized(audio_uuid: str, entry: StoredAudio) -> None:
    """Write ``normalized.wav`` again from the stored file, when the cache lost it.

    Only once the part has been measured (``durationSeconds``): before that, the ingest is still
    writing it.
    """
    if entry.has_normalized() or entry.metadata.duration_seconds is None:
        return
    if not formats.ffmpeg_available():
        return
    with _normalize_guard:
        lock = _normalize_locks.setdefault(audio_uuid, threading.Lock())
    if entry.joined and entry.timeline is not None:
        with lock:
            if not entry.has_normalized():
                sources.write_normalized(audio_uuid, entry.timeline, entry.normalized_path)
        return
    original = entry.original_path
    if original is None or not original.is_file():
        return
    with lock:
        if not entry.has_normalized():
            entry.directory.mkdir(parents=True, exist_ok=True)
            formats.normalize_to_wav(original, entry.normalized_path)


# ------------------------------------------------------------------- creating


def new_uuid() -> str:
    return bundle.new_id()


def create(
    alias: str,
    source: AudioSource | str,
    extension: str,
    *,
    audio_uuid: str | None = None,
    original_filename: str | None = None,
    source_url: str | None = None,
    source_audio_uuid: str | None = None,
    source_time_range: TimeRange | None = None,
) -> StoredAudio:
    """A new project of one part in the Personal Vault of the current user. No audio bytes yet."""
    metadata = AudioMetadata(
        uuid=audio_uuid or new_uuid(),
        alias=alias,
        source=AudioSource(source),
        format=extension.lstrip("."),
        original_filename=original_filename,
        source_url=source_url,
        source_audio_uuid=source_audio_uuid,
        source_time_range=source_time_range,
    )
    try:
        bundle.create_project(
            owner_id=current_user_id(),
            title=metadata.alias,
            source=_source_of(metadata),
            project_id=metadata.uuid,
            created_at=metadata.created_at,
        )
    except FileExistsError:
        raise FileExistsError(f"Audio folder already exists: {metadata.uuid}") from None
    return get(metadata.uuid)


def save_original(audio_uuid: str, stream: BinaryIO | Iterable[bytes], extension: str) -> Path:
    """Write the incoming bytes into the audio store and make them the part's one audio file."""
    content_hash = audio_files.add_stream(stream, extension)
    return _use_audio(audio_uuid, content_hash, extension, frames=None)


def replace_original(
    audio_uuid: str, source: Path, extension: str = "wav", *, keep_cuts: bool = True
) -> Path:
    """A new audio file for the part (a splice, a passage put in, a segment): stored by its
    content, and every segment now points at it. The cuts stay where they were unless
    ``keep_cuts`` is false. The previous file stays in the store for the history snapshots.

    A WAV is measured now; any other file is measured when it is normalized
    (:func:`set_audio_frames`).
    """
    frames = None
    if extension.lstrip(".").lower() == "wav":
        rate, samples = formats.sample_count(source)
        frames = math.ceil(samples * 1000 / (rate * bundle.FRAME_MS))
    content_hash = audio_files.add_file(
        source, extension, duration_ms=None if frames is None else frames * bundle.FRAME_MS
    )
    return _use_audio(audio_uuid, content_hash, extension, frames=frames, keep_cuts=keep_cuts)


def _use_audio(
    audio_uuid: str,
    content_hash: str,
    extension: str,
    *,
    frames: int | None,
    keep_cuts: bool = False,
) -> Path:
    extension = extension.lstrip(".").lower()
    project = _project_of(audio_uuid)
    with bundle.project_lock(project.id):
        timeline = bundle.read_timeline(audio_uuid)
        cuts = bundle.cuts_of(timeline) if keep_cuts else []
        timeline = timeline.model_copy(
            update={
                "audio": {content_hash: AudioEntry(format=extension, frames=frames)},
                "sources": None,
                "segments": bundle.segments_for_cuts(content_hash, [], None),
            }
        )
        if cuts:
            timeline = _with_cuts(timeline, cuts)
        bundle.write_timeline(audio_uuid, timeline)
        # The derived files of the old audio: the joined audio of the cuts and the peaks, and the
        # joined files of a part that had several.
        cache = paths.part_cache_dir(audio_uuid)
        for stale in [*cache.glob("piece-r*.*"), cache / "waveform.json"]:
            stale.unlink(missing_ok=True)
        sources.clear(audio_uuid, keep_sources=False)
        project = bundle.read_project(project.id)
        source = project.part(audio_uuid).source
        source.format = extension
        source.files = []
        bundle.write_project(project)
    return audio_files.file_path(content_hash, extension)


def set_audio_frames(audio_uuid: str, frames: int) -> None:
    """Record the length of the part's file in 10 ms frames, once ``normalized.wav`` measured it."""
    project = _project_of(audio_uuid)
    with bundle.project_lock(project.id):
        timeline = bundle.read_timeline(audio_uuid)
        files = timeline.source_list()
        if len(files) != 1:
            return
        content_hash = files[0]
        cuts = bundle.cuts_of(timeline)
        audio = dict(timeline.audio)
        audio[content_hash] = audio[content_hash].model_copy(update={"frames": int(frames)})
        timeline = timeline.model_copy(update={"audio": audio})
        bundle.write_timeline(audio_uuid, _with_cuts(timeline, cuts))


def _with_cuts(timeline: Timeline, cuts: list[tuple[int, int]]) -> Timeline:
    return timeline.model_copy(update={"segments": bundle.segments_with_cuts(timeline, cuts)})


def append(
    audio_uuid: str,
    content_hash: str,
    extension: str,
    frames: int,
    *,
    original_filename: str | None = None,
    kind: str = "upload",
    name: str | None = None,
    url: str | None = None,
) -> AudioMetadata:
    """Add a stored, measured file at the end of the part's audio (**add audio**).

    The axis grows at its end, so every cut keeps its frames. ``audioRevision`` goes up by one: the
    audio of the part changed, so its notes are stale until it is transcribed again. The joined
    files are written again; a part that had one file keeps that file's 16 kHz copy as the first
    one's.
    """
    extension = extension.lstrip(".").lower()
    project = _project_of(audio_uuid)
    cache = paths.part_cache_dir(audio_uuid)
    with bundle.project_lock(project.id):
        timeline = bundle.read_timeline(audio_uuid)
        files = timeline.source_list()
        if not files:
            raise ValueError("This part has no audio yet: upload its first file instead")
        described = bundle.source_files(bundle.read_project(project.id), audio_uuid, timeline)
        if timeline.axis_frames() is None:
            raise ValueError("The first audio file is not measured yet. Try again in a moment.")
        if len(files) == 1:
            # Its normalized.wav is that file's own 16 kHz copy: keep it as the first source's.
            first = cache / f"{sources.SOURCE_PREFIX}{files[0]}.wav"
            normalized = cache / "normalized.wav"
            if normalized.is_file() and not first.is_file():
                first.write_bytes(normalized.read_bytes())
        cuts = bundle.cuts_of(timeline)
        audio = dict(timeline.audio)
        audio.setdefault(content_hash, AudioEntry(format=extension, frames=frames))
        timeline = timeline.model_copy(
            update={
                "audio": audio,
                "sources": [*files, content_hash],
                "audio_revision": timeline.audio_revision + 1,
            }
        )
        timeline = _with_cuts(timeline, cuts)
        bundle.write_timeline(audio_uuid, timeline)
        for stale in [*cache.glob("piece-r*.*"), cache / "waveform.json", cache / "normalized.wav"]:
            stale.unlink(missing_ok=True)
        sources.clear(audio_uuid)
        project = bundle.read_project(project.id)
        project.part(audio_uuid).source.files = [
            *described,
            SourceFile(
                audio=content_hash,
                name=(name or "").strip()
                or bundle.default_name(original_filename, f"Audio {len(described) + 1}"),
                kind=kind,
                format=extension,
                original_filename=original_filename,
                duration_seconds=frames * bundle.FRAME_MS / 1000.0,
                url=url,
            ),
        ]
        bundle.write_project(project)
    entry = get(audio_uuid)  # writes the joined normalized.wav
    return entry.metadata


def _forget_joined(audio_uuid: str) -> None:
    """The derived files of the axis, which changed: written again on the next request."""
    cache = paths.part_cache_dir(audio_uuid)
    for stale in [*cache.glob("piece-r*.*"), cache / "waveform.json", cache / "normalized.wav"]:
        stale.unlink(missing_ok=True)
    sources.clear(audio_uuid)


def _check_revision(timeline: Timeline, base_revision: int | None) -> None:
    if base_revision is not None and base_revision != timeline.audio_revision:
        raise RevisionMismatch(timeline.audio_revision, base_revision)


class RevisionMismatch(ValueError):
    """The audio changed since the page loaded it."""

    def __init__(self, current: int, base: int) -> None:
        self.current = current
        super().__init__(
            "The audio was changed somewhere else since this page loaded it "
            f"(revision {current}, not {base}). Reload the page to see it."
        )


def rename_file(audio_uuid: str, index: int, name: str) -> list[SourceFile]:
    """Give file ``index`` of the part's audio a name. Nothing else changes."""
    cleaned = " ".join(name.split())
    if not cleaned:
        raise ValueError("A name cannot be empty")
    project = _project_of(audio_uuid)
    with bundle.project_lock(project.id):
        project = bundle.read_project(project.id)
        timeline = bundle.read_timeline(audio_uuid)
        files = bundle.source_files(project, audio_uuid, timeline)
        if not 0 <= index < len(files):
            raise IndexError(f"This audio has no file {index + 1}")
        files[index].name = cleaned[:200]
        project.part(audio_uuid).source.files = files
        bundle.write_project(project)
    return files


def _segments_by_file(timeline: Timeline) -> list[list[Segment]]:
    """The segments of each file of the axis, in order (a part of one file has one list)."""
    count = len(timeline.source_list())
    groups: list[list[Segment]] = [[] for _ in range(count)]
    for segment in timeline.segments:
        groups[segment.source if segment.source is not None else 0].append(segment)
    return groups


def _with_files(timeline: Timeline, order: list[str], groups: list[list[Segment]]) -> Timeline:
    """A timeline of the files ``order`` (hashes) with their kept segments ``groups``."""
    several = len(order) > 1
    segments = [
        segment.model_copy(update={"source": index if several else None})
        for index, group in enumerate(groups)
        for segment in group
    ]
    audio = {key: value for key, value in timeline.audio.items() if key in order}
    return timeline.model_copy(
        update={
            "audio": audio,
            "sources": order if several else None,
            "segments": segments,
            "audio_revision": timeline.audio_revision + 1,
        }
    )


def reorder_files(
    audio_uuid: str, order: list[int], *, base_revision: int | None = None
) -> list[SourceFile]:
    """Put the files of the part's audio in a new order (``order`` lists the current positions).

    Each file keeps its own cuts: its kept ranges move with it. The audio of the part changed, so
    ``audioRevision`` goes up and the notes become stale.
    """
    project = _project_of(audio_uuid)
    with bundle.project_lock(project.id):
        project = bundle.read_project(project.id)
        timeline = bundle.read_timeline(audio_uuid)
        _check_revision(timeline, base_revision)
        files = bundle.source_files(project, audio_uuid, timeline)
        if sorted(order) != list(range(len(files))):
            raise ValueError(f"The order must name each of the {len(files)} files once")
        if order == list(range(len(files))):
            return files
        groups = _segments_by_file(timeline)
        hashes = timeline.source_list()
        timeline = _with_files(timeline, [hashes[at] for at in order], [groups[at] for at in order])
        bundle.write_timeline(audio_uuid, timeline)
        files = [files[at] for at in order]
        project.part(audio_uuid).source.files = files
        bundle.write_project(project)
        _forget_joined(audio_uuid)
    return files


def remove_file(
    audio_uuid: str, index: int, *, base_revision: int | None = None
) -> list[SourceFile]:
    """Take file ``index`` out of the part's audio. The last file cannot be removed.

    The stored file is deleted when no project uses it any more. The audio changed, so
    ``audioRevision`` goes up and the notes become stale.
    """
    project = _project_of(audio_uuid)
    with bundle.project_lock(project.id):
        project = bundle.read_project(project.id)
        timeline = bundle.read_timeline(audio_uuid)
        _check_revision(timeline, base_revision)
        files = bundle.source_files(project, audio_uuid, timeline)
        if not 0 <= index < len(files):
            raise IndexError(f"This audio has no file {index + 1}")
        if len(files) == 1:
            raise ValueError("A project keeps at least one audio file")
        groups = _segments_by_file(timeline)
        hashes = timeline.source_list()
        removed = hashes[index]
        keep = [at for at in range(len(files)) if at != index]
        if not any(groups[at] for at in keep):
            raise ValueError("The other files are cut completely: restore a part of them first")
        timeline = _with_files(timeline, [hashes[at] for at in keep], [groups[at] for at in keep])
        bundle.write_timeline(audio_uuid, timeline)
        files = [files[at] for at in keep]
        source = project.part(audio_uuid).source
        source.files = files
        if index == 0:
            # The fields of the source describe the first file.
            first = files[0]
            source.kind = first.kind
            source.format = first.format
            source.original_filename = first.original_filename
            source.duration_seconds = first.duration_seconds
            source.url = first.url
        bundle.write_project(project)
        _forget_joined(audio_uuid)
    audio_files.delete_unused([removed])
    return files


def files_of(audio_uuid: str) -> list[dict[str, object]]:
    """The files of the part's axis in order: their place, name and origin, their first frame and
    length in frames, and how many of their frames are cut. Empty while the part has no measured
    audio."""
    project = _project_of(audio_uuid)
    timeline = bundle.read_timeline(audio_uuid)
    try:
        axis = timeline.axis()
    except ValueError:
        return []
    described = bundle.source_files(project, audio_uuid, timeline)
    cuts = bundle.cuts_of(timeline)
    out: list[dict[str, object]] = []
    start = 0
    for index, ((_, frames), file) in enumerate(zip(axis, described)):
        end = start + frames
        cut = sum(max(0, min(end, b) - max(start, a)) for a, b in cuts)
        out.append(
            {
                "index": index,
                "name": file.name,
                "kind": file.kind,
                "originalFilename": file.original_filename,
                "url": file.url,
                "startFrame": start,
                "frames": frames,
                "cutFrames": cut,
            }
        )
        start = end
    return out


# -------------------------------------------------------------------- reading


def exists(audio_uuid: str) -> bool:
    try:
        _project_of(audio_uuid)
    except AudioNotFound:
        return False
    return True


def read_metadata(audio_uuid: str) -> AudioMetadata:
    """The metadata of one part. Raises :class:`AudioNotFound`."""
    project = _project_of(audio_uuid)
    return _metadata(project, audio_uuid, bundle.read_timeline(audio_uuid))


def get(audio_uuid: str) -> StoredAudio:
    """The full entry for one part. A lost ``normalized.wav`` is written again here."""
    project = _project_of(audio_uuid)
    timeline = bundle.read_timeline(audio_uuid)
    entry = StoredAudio(
        metadata=_metadata(project, audio_uuid, timeline),
        directory=paths.part_cache_dir(audio_uuid),
        original_path=_original_of(audio_uuid, timeline),
        timeline=timeline,
    )
    _restore_normalized(audio_uuid, entry)
    return entry


def list_all() -> list[StoredAudio]:
    """Every part of the current user, in the Personal Vault and the Private Library, newest first.

    A part that cannot be read is skipped rather than raising: a half-written ingest must not break
    the whole list.
    """
    entries: list[StoredAudio] = []
    for audio_uuid in bundle.list_parts(current_user_id(), layers=("vault", "private")):
        try:
            entries.append(get(audio_uuid))
        except (AudioNotFound, ValueError):
            continue
    entries.sort(key=lambda entry: entry.metadata.created_at, reverse=True)
    return entries


# -------------------------------------------------------------------- writing


def write_metadata(metadata: AudioMetadata) -> AudioMetadata:
    """Persist every field: the title and the source in ``project.json``, the cuts and the revision
    in ``timeline.json``."""
    project = _project_of(metadata.uuid)
    with bundle.project_lock(project.id):
        project = bundle.read_project(project.id)
        entry = project.part(metadata.uuid)
        first_duration = entry.source.duration_seconds
        several = len(bundle.read_timeline(metadata.uuid).source_list()) > 1
        entry.source = _source_of(metadata, entry.source.files)
        if several:
            # The metadata's length is the axis; the source keeps its first file's own length.
            entry.source.duration_seconds = first_duration
        project = project.model_copy(
            update={"title": metadata.alias, "frame_ms": metadata.frame_ms}
        )
        bundle.write_project(project)
        timeline = bundle.read_timeline(metadata.uuid)
        changed = (
            list(metadata.cuts) != bundle.cuts_of(timeline)
            or metadata.audio_revision != timeline.audio_revision
        )
        if changed:
            timeline = _with_cuts(
                timeline.model_copy(update={"audio_revision": metadata.audio_revision}),
                list(metadata.cuts),
            )
            bundle.write_timeline(metadata.uuid, timeline)
    return metadata


def update(audio_uuid: str, **changes: object) -> AudioMetadata:
    """Patch metadata fields by name and persist. Returns the new metadata.

    Only known fields are accepted; ``uuid`` cannot be changed, since it is the id of the part.
    """
    metadata = read_metadata(audio_uuid)
    if "uuid" in changes:
        raise ValueError("An audio's uuid is the id of its part and cannot be changed")

    unknown = set(changes) - set(type(metadata).model_fields)
    if unknown:
        raise ValueError(f"Unknown audio metadata field(s): {sorted(unknown)}")

    updated = metadata.model_copy(update={k: v for k, v in changes.items() if v is not None})
    write_metadata(updated)
    return updated


def set_cuts(audio_uuid: str, cuts: list[tuple[int, int]]) -> AudioMetadata:
    """Store the cuts, already normalized (:func:`aitu_backend.audio.frames.normalize_cuts`).

    ``audioRevision`` goes up by one only when the cuts change, so saving the same cuts twice does
    not make the notes stale (implementation 08, plan section 8.2). Validated, unlike
    :func:`update`, because a wrong cut would move every note of the next transcription.
    """
    metadata = read_metadata(audio_uuid)
    wanted = [(int(start), int(end)) for start, end in cuts]
    if wanted == list(metadata.cuts):
        return metadata
    updated = AudioMetadata.model_validate(
        {
            **metadata.model_dump(by_alias=True),
            "cuts": wanted,
            "audioRevision": metadata.audio_revision + 1,
        }
    )
    write_metadata(updated)
    # The cached waveform is the part's, and the part just changed length.
    get(audio_uuid).waveform_path.unlink(missing_ok=True)
    return updated


def rename(audio_uuid: str, alias: str) -> AudioMetadata:
    """Change the display alias, which is the project's title."""
    if not alias.strip():
        raise ValueError("Alias cannot be empty")
    return update(audio_uuid, alias=alias.strip())


def delete(audio_uuid: str) -> None:
    """Delete the project of this part, with everything it has. Raises :class:`AudioNotFound`."""
    project = _project_of(audio_uuid)
    bundle.delete_project(project.id)


# ------------------------------------------------------------------- waveform


def read_waveform(audio_uuid: str) -> dict | None:
    """Cached peaks, or ``None`` when they have not been computed yet."""
    path = paths.waveform_path(audio_uuid)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def write_waveform(audio_uuid: str, payload: dict) -> Path:
    """Cache computed peaks next to the part's other derived files."""
    path = paths.waveform_path(audio_uuid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path
