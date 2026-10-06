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

**Every filesystem access for the audio of a part goes through this module.**
"""

from __future__ import annotations

import json
import math
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Iterable

from aitu_backend.audio import formats
from aitu_backend.db.users import current_user_id
from aitu_backend.schemas.metadata import AudioMetadata, AudioSource, TimeRange
from aitu_backend.storage import audio_files, bundle, locate, paths
from aitu_backend.storage.bundle import AudioEntry, PartSource, Segment, Timeline

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
    #: The file in the audio store, or ``None`` before the first audio arrives.
    original_path: Path | None = None

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
    return AudioMetadata.model_validate(
        {
            "uuid": part_id,
            "alias": project.title,
            "source": source.kind,
            "format": source.format or "wav",
            "originalFilename": source.original_filename,
            "durationSeconds": source.duration_seconds,
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


def _source_of(metadata: AudioMetadata) -> PartSource:
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
    )


def _original_of(timeline: Timeline) -> Path | None:
    content_hash = timeline.single_audio
    if content_hash is None:
        return None
    return audio_files.file_path(content_hash, timeline.audio[content_hash].format)


_normalize_locks: dict[str, threading.Lock] = {}
_normalize_guard = threading.Lock()


def _restore_normalized(audio_uuid: str, entry: StoredAudio) -> None:
    """Write ``normalized.wav`` again from the stored file, when the cache lost it.

    Only once the part has been measured (``durationSeconds``): before that, the ingest is still
    writing it.
    """
    if entry.has_normalized() or entry.metadata.duration_seconds is None:
        return
    original = entry.original_path
    if original is None or not original.is_file():
        return
    if not formats.ffmpeg_available():
        return
    with _normalize_guard:
        lock = _normalize_locks.setdefault(audio_uuid, threading.Lock())
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
                "segments": bundle.segments_for_cuts(content_hash, [], None),
            }
        )
        if cuts:
            timeline = _with_cuts(timeline, cuts)
        bundle.write_timeline(audio_uuid, timeline)
        # The derived files of the old audio: the joined audio of the cuts and the peaks.
        cache = paths.part_cache_dir(audio_uuid)
        for stale in [*cache.glob("piece-r*.*"), cache / "waveform.json"]:
            stale.unlink(missing_ok=True)
        project = bundle.read_project(project.id)
        project.part(audio_uuid).source.format = extension
        bundle.write_project(project)
    return audio_files.file_path(content_hash, extension)


def set_audio_frames(audio_uuid: str, frames: int) -> None:
    """Record the length of the part's file in 10 ms frames, once ``normalized.wav`` measured it."""
    project = _project_of(audio_uuid)
    with bundle.project_lock(project.id):
        timeline = bundle.read_timeline(audio_uuid)
        content_hash = timeline.single_audio
        if content_hash is None:
            return
        cuts = bundle.cuts_of(timeline)
        audio = dict(timeline.audio)
        audio[content_hash] = audio[content_hash].model_copy(update={"frames": int(frames)})
        timeline = timeline.model_copy(update={"audio": audio})
        bundle.write_timeline(audio_uuid, _with_cuts(timeline, cuts))


def _with_cuts(timeline: Timeline, cuts: list[tuple[int, int]]) -> Timeline:
    content_hash = timeline.single_audio
    if content_hash is None:
        if cuts:
            raise ValueError("A part with no audio has nothing to cut")
        return timeline
    segments: list[Segment] = bundle.segments_for_cuts(
        content_hash, cuts, timeline.audio[content_hash].frames
    )
    return timeline.model_copy(update={"segments": segments})


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
        original_path=_original_of(timeline),
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
        entry.source = _source_of(metadata)
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
