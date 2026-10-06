"""The project bundle (implementation 02, plan section 8.3): ``project.json``, the parts, the audio
timeline of each part, and the records of the ``projects``, ``parts`` and ``audio_refs`` tables.

A bundle has the same layout in the three layers and in an export (Phase 5)::

    <projectId>/
      project.json
      parts/<partId>/notes.pmn, sheet.json, timeline.json
      staging/<sessionId>/
      cache/<partId>/

**project.json** holds the project's own metadata: ``id``, ``kind``, ``title``, ``subtitle``,
``artistText``, ``ownerId``, ``frameMs``, ``origin``, ``basedOn``, ``createdAt``, ``updatedAt``,
``revision``, and the parts in order. Each part carries its ``subheader`` and its ``source``: where
its audio came from (an upload, YouTube, a recording) and the facts of that file. The links to a
song, an artist and a version are records of a library, never in the bundle (section 8.3).

**timeline.json** is the audio timeline of section 8.5::

    {"schemaVersion": 1, "audioRevision": 1,
     "audio": {"9f3c…": {"format": "mp3", "frames": 18956}},
     "segments": [{"audio": "9f3c…", "fromMs": 3160, "toMs": 260220},
                  {"audio": "9f3c…", "fromMs": 263510, "toMs": 263510}]}

``audio`` lists the files the part uses, with their extension and their length in 10 ms frames,
so the timeline reads without the database and a cut that reaches the end of the file is still a
cut. ``toMs`` is ``null`` for a segment that runs to the end of a file whose length is not measured
yet (between the upload and its normalization).

Phase 3 has one audio per part, as the plan says: the cuts of implementation 08 are the gaps
between the segments of that one file (:func:`cuts_of`, :func:`segments_for_cuts`).

A project made by this app has the id of its first part, so a project of one part has one uuid.
"""

from __future__ import annotations

import json
import shutil
import threading
import uuid as uuid_module
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select

from aitu_backend.db.database import session
from aitu_backend.db.models import AudioRef, Part, Project
from aitu_backend.storage import audio_files, locate, paths

__all__ = [
    "PartEntry",
    "PartSource",
    "ProjectFile",
    "Segment",
    "Timeline",
    "create_project",
    "cuts_of",
    "delete_project",
    "duplicate_project",
    "list_parts",
    "part_ids_of",
    "read_project",
    "read_timeline",
    "segments_for_cuts",
    "sync_audio_refs",
    "write_project",
    "write_timeline",
]

PROJECT_SCHEMA_VERSION = 1
TIMELINE_SCHEMA_VERSION = 1
#: One time frame of the shared axis of the audio and the notes (implementation 08, section 9.2).
FRAME_MS = 10


def _now() -> datetime:
    return datetime.now(timezone.utc)


class _Camel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class PartSource(_Camel):
    """Where the audio of a part came from, and the facts of that file."""

    #: ``upload``, ``recording``, ``youtube``, ``segment`` or ``composed``.
    kind: str = "upload"
    format: str | None = None
    original_filename: str | None = Field(None, alias="originalFilename")
    duration_seconds: float | None = Field(None, alias="durationSeconds")
    sample_rate: int | None = Field(None, alias="sampleRate")
    url: str | None = None
    source_audio_uuid: str | None = Field(None, alias="sourceAudioUuid")
    source_time_range: dict[str, float] | None = Field(None, alias="sourceTimeRange")


class PartEntry(_Camel):
    id: str
    #: The title drawn above the part in an integrated playlist (section 8.4).
    subheader: str | None = None
    source: PartSource = Field(default_factory=PartSource)


class ProjectFile(_Camel):
    """``project.json``."""

    schema_version: int = Field(PROJECT_SCHEMA_VERSION, alias="schemaVersion")
    id: str
    kind: str = "song"
    title: str = ""
    subtitle: str | None = None
    artist_text: str | None = Field(None, alias="artistText")
    owner_id: int = Field(..., alias="ownerId")
    #: The column length a project made from scratch is meant to be read at; still a view (D-01).
    frame_ms: float | None = Field(None, alias="frameMs")
    #: The project or passages it was made from (sections 10.3 and 10.4).
    origin: dict[str, Any] | None = None
    #: The library project a vault project edits (section 10.6).
    based_on: str | None = Field(None, alias="basedOn")
    created_at: datetime = Field(default_factory=_now, alias="createdAt")
    updated_at: datetime = Field(default_factory=_now, alias="updatedAt")
    revision: int = 1
    parts: list[PartEntry] = Field(default_factory=list)

    def part(self, part_id: str) -> PartEntry:
        for entry in self.parts:
            if entry.id == part_id:
                return entry
        raise locate.NotFound("part", part_id)


class Segment(_Camel):
    audio: str
    from_ms: int = Field(..., alias="fromMs")
    #: ``None``: to the end of the file, whose length is not measured yet.
    to_ms: int | None = Field(None, alias="toMs")


class AudioEntry(_Camel):
    format: str
    #: The length of the file in 10 ms frames, once it is measured.
    frames: int | None = None


class Timeline(_Camel):
    """``timeline.json``: the audio segments a part plays one after the other."""

    schema_version: int = Field(TIMELINE_SCHEMA_VERSION, alias="schemaVersion")
    audio_revision: int = Field(0, alias="audioRevision")
    audio: dict[str, AudioEntry] = Field(default_factory=dict)
    segments: list[Segment] = Field(default_factory=list)

    @property
    def single_audio(self) -> str | None:
        """The one file of a part of Phase 3, or ``None`` when the part has no audio yet."""
        if not self.audio:
            return None
        if len(self.audio) > 1:
            raise ValueError("This part plays several audio files; cuts need one")
        return next(iter(self.audio))


_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def project_lock(project_id: str) -> threading.Lock:
    """One lock per project, held from a read of ``project.json`` to its write."""
    with _locks_guard:
        return _locks.setdefault(project_id, threading.Lock())


# ------------------------------------------------------------------- files


def _write_json(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(body, encoding="utf-8")
    temporary.replace(path)


def read_project(project_id: str) -> ProjectFile:
    path = paths.project_json_path(project_id)
    if not path.is_file():
        raise locate.NotFound("project", project_id)
    return ProjectFile.model_validate_json(path.read_text(encoding="utf-8"))


def write_project(project: ProjectFile, *, touch: bool = True) -> ProjectFile:
    """Write ``project.json`` and keep the ``projects`` row in step (title, time)."""
    if touch:
        project = project.model_copy(update={"updated_at": _now()})
    _write_json(
        paths.project_json_path(project.id),
        project.model_dump_json(by_alias=True, indent=2) + "\n",
    )
    with session() as db:
        row = db.get(Project, project.id)
        if row is not None:
            row.title = project.title
            row.kind = project.kind
            row.based_on = project.based_on
            row.updated_at = project.updated_at
    return project


def read_timeline(part_id: str) -> Timeline:
    path = paths.part_timeline_path(part_id)
    if not path.is_file():
        return Timeline()
    return Timeline.model_validate_json(path.read_text(encoding="utf-8"))


def write_timeline(part_id: str, timeline: Timeline) -> Timeline:
    """Write ``timeline.json`` and record which audio files the project now uses."""
    _write_json(
        paths.part_timeline_path(part_id),
        timeline.model_dump_json(by_alias=True, indent=2) + "\n",
    )
    sync_audio_refs(locate.part(part_id).project_id)
    return timeline


# ------------------------------------------------------------------- cuts


def segments_for_cuts(
    content_hash: str, cuts: Iterable[tuple[int, int]], total_frames: int | None
) -> list[Segment]:
    """The kept ranges of one file around ``cuts`` (``[startFrame, endFrame)``, normalized)."""
    ranges = list(cuts)
    if total_frames is None:
        if ranges:
            raise ValueError("The length of the audio must be known to store cuts")
        return [Segment(audio=content_hash, from_ms=0, to_ms=None)]
    segments: list[Segment] = []
    start = 0
    for cut_start, cut_end in ranges:
        if cut_start > start:
            segments.append(
                Segment(audio=content_hash, from_ms=start * FRAME_MS, to_ms=cut_start * FRAME_MS)
            )
        start = max(start, cut_end)
    if start < total_frames:
        segments.append(
            Segment(audio=content_hash, from_ms=start * FRAME_MS, to_ms=total_frames * FRAME_MS)
        )
    return segments


def cuts_of(timeline: Timeline) -> list[tuple[int, int]]:
    """The cuts of a part of one audio file: the gaps between its segments, in frames."""
    content_hash = timeline.single_audio
    if content_hash is None:
        return []
    total = timeline.audio[content_hash].frames
    cuts: list[tuple[int, int]] = []
    position = 0
    for segment in timeline.segments:
        start = segment.from_ms // FRAME_MS
        end = total if segment.to_ms is None else segment.to_ms // FRAME_MS
        if end is None:  # the last segment of a file not measured yet: nothing is cut
            return cuts
        if start > position:
            cuts.append((position, start))
        position = max(position, end)
    if total is not None and position < total:
        cuts.append((position, total))
    return cuts


# ---------------------------------------------------------------- projects


def new_id() -> str:
    return str(uuid_module.uuid4())


def create_project(
    *,
    owner_id: int,
    title: str,
    source: PartSource | None = None,
    layer: str = "vault",
    kind: str = "song",
    project_id: str | None = None,
    part_id: str | None = None,
    frame_ms: float | None = None,
    created_at: datetime | None = None,
) -> ProjectFile:
    """A new project of one part, in the folder of its owner and layer, with its rows.

    The part's id is the project's unless both are given. Raises ``FileExistsError`` when the id is
    taken.
    """
    project_id = project_id or part_id or new_id()
    part_id = part_id or project_id
    with session() as db:
        if db.get(Project, project_id) is not None or db.get(Part, part_id) is not None:
            raise FileExistsError(f"A project or a part already has the id {project_id}")
    directory = paths.project_dir_at(project_id, owner_id, layer)
    if directory.exists():
        raise FileExistsError(f"Project folder already exists: {directory}")
    moment = created_at or _now()
    project = ProjectFile(
        id=project_id,
        kind=kind,
        title=title,
        owner_id=owner_id,
        frame_ms=frame_ms,
        created_at=moment,
        updated_at=moment,
        parts=[PartEntry(id=part_id, source=source or PartSource())],
    )
    with session() as db:
        db.add(
            Project(
                id=project_id,
                owner_id=owner_id,
                layer=layer,
                kind=kind,
                title=title,
                created_at=moment,
                updated_at=moment,
            )
        )
        db.flush()
        db.add(Part(id=part_id, project_id=project_id, position=0))
    locate.forget(project_id)
    (directory / "parts" / part_id).mkdir(parents=True)
    (directory / "cache" / part_id).mkdir(parents=True)
    write_project(project, touch=False)
    write_timeline(part_id, Timeline())
    return project


def part_ids_of(project_id: str) -> list[str]:
    with session() as db:
        return list(
            db.scalars(select(Part.id).where(Part.project_id == project_id).order_by(Part.position))
        )


def list_parts(owner_id: int | None = None, layers: Iterable[str] | None = None) -> list[str]:
    """Every part id, of one owner and some layers when asked, newest project first."""
    query = select(Part.id).join(Project, Part.project_id == Project.id)
    if owner_id is not None:
        query = query.where(Project.owner_id == owner_id)
    if layers is not None:
        query = query.where(Project.layer.in_(list(layers)))
    query = query.order_by(Project.created_at.desc(), Part.position)
    with session() as db:
        return list(db.scalars(query))


def _history_hashes(project_id: str) -> set[str]:
    """The audio the history snapshots of a project point at, so it is never deleted under them."""
    found: set[str] = set()
    root = paths.history_dir() / project_id
    if not root.is_dir():
        return found
    for path in root.rglob("timeline.json"):
        try:
            found.update(json.loads(path.read_text(encoding="utf-8")).get("audio", {}))
        except (ValueError, OSError):
            continue
    return found


def used_hashes(project_id: str) -> set[str]:
    """Every audio file the parts of a project and their history use."""
    found = _history_hashes(project_id)
    for part_id in part_ids_of(project_id):
        found.update(read_timeline(part_id).audio)
    return found


def sync_audio_refs(project_id: str) -> None:
    """Make ``audio_refs`` say exactly which files the project uses."""
    wanted = used_hashes(project_id)
    with session() as db:
        current = set(db.scalars(select(AudioRef.hash).where(AudioRef.project_id == project_id)))
        for content_hash in current - wanted:
            db.execute(
                delete(AudioRef).where(
                    AudioRef.project_id == project_id, AudioRef.hash == content_hash
                )
            )
        for content_hash in wanted - current:
            db.add(AudioRef(project_id=project_id, hash=content_hash))


def delete_project(project_id: str) -> None:
    """Delete a project everywhere: its folder, its temporary files, its history, its rows, and
    the audio files no other project uses."""
    where = locate.project(project_id)
    part_ids = part_ids_of(project_id)
    hashes = used_hashes(project_id)
    shutil.rmtree(paths.project_dir_at(project_id, where.owner_id, where.layer), ignore_errors=True)
    for part_id in part_ids:
        shutil.rmtree(paths.tmp_dir() / str(where.owner_id) / part_id, ignore_errors=True)
    shutil.rmtree(paths.history_dir() / project_id, ignore_errors=True)
    with session() as db:
        row = db.get(Project, project_id)
        if row is not None:
            db.delete(row)
    locate.forget(project_id)
    audio_files.delete_unused(hashes)


#: Copied by :func:`duplicate_project`. Staging, history and the video are not: a copy starts with
#: no open session, no earlier states and no temporary files.
PART_FILES = ("notes.pmn", "sheet.json", "timeline.json", "needs-rederivation.json")
#: The cache files worth copying: normalizing again costs a second of ffmpeg per part.
CACHE_FILES = ("normalized.wav",)


def duplicate_project(
    project_id: str,
    *,
    owner_id: int | None = None,
    layer: str = "vault",
    title: str | None = None,
) -> ProjectFile:
    """A copy of a project with new ids: no audio bytes copied (P-3), only the bundle."""
    source = read_project(project_id)
    owner = source.owner_id if owner_id is None else owner_id
    new_project = new_id()
    mapping = {
        entry.id: (new_project if index == 0 else new_id())
        for index, entry in enumerate(source.parts)
    }
    moment = _now()
    copy = source.model_copy(
        update={
            "id": new_project,
            "owner_id": owner,
            "title": source.title if title is None else title,
            "created_at": moment,
            "updated_at": moment,
            "revision": 1,
            "origin": {"duplicateOf": project_id},
            "parts": [entry.model_copy(update={"id": mapping[entry.id]}) for entry in source.parts],
        }
    )
    with session() as db:
        db.add(
            Project(
                id=new_project,
                owner_id=owner,
                layer=layer,
                kind=copy.kind,
                title=copy.title,
                based_on=copy.based_on,
                created_at=moment,
                updated_at=moment,
            )
        )
        db.flush()
        for position, entry in enumerate(copy.parts):
            db.add(Part(id=entry.id, project_id=new_project, position=position))
    locate.forget(new_project)
    target = paths.project_dir_at(new_project, owner, layer)
    for old_id, new_part in mapping.items():
        source_part = paths.part_dir(old_id)
        target_part = target / "parts" / new_part
        target_part.mkdir(parents=True)
        (target / "cache" / new_part).mkdir(parents=True, exist_ok=True)
        for name in PART_FILES:
            if (source_part / name).is_file():
                shutil.copy2(source_part / name, target_part / name)
        source_cache = paths.part_cache_dir(old_id)
        for name in CACHE_FILES:
            if (source_cache / name).is_file():
                shutil.copy2(source_cache / name, target / "cache" / new_part / name)
    write_project(copy, touch=False)
    sync_audio_refs(new_project)
    return copy
