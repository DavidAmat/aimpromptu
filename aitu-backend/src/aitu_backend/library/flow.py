"""Saving a project to the Private Library, and changing a version through a copy (implementation
02, plan sections 8.5, 10.2 and 10.6).

**Save to library** moves a project of the Personal Vault into the Private Library, under a song
and a version name. On the way (section 8.5, Q-3):

* each audio file the project uses only in part is written again with only the ranges in use
  (:mod:`aitu_backend.audio.compact`), and the old file is deleted once no project uses it;
* the temporary files go: the video and its frames, the open edit sessions, and the history of
  the parts, whose earlier states point at the audio that was just written again.

**A version is changed through a copy.** **Edit** copies the library project into the Personal
Vault with ``basedOn`` pointing at it (no audio bytes copied); the library project does not change.
In the vault, **Save to library** then either **replaces the version** (the library project gets
the copy's content and keeps its ids; its previous content goes to its history) or **saves a new
version**. Deleting the copy discards the changes. A version's history can be restored: the state
it replaces goes to the history first, so nothing is lost.

The history of a version is ``.database/history/<projectId>/v<N>/``: ``project.json``,
``snapshot.json`` (when and why) and each part's files. Its audio stays in the store because
``audio_refs`` counts the files a history names.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, update

from aitu_backend.audio import compact
from aitu_backend.db.database import session
from aitu_backend.db.models import Part, PrivateVersion, Project, Song
from aitu_backend.library import rows
from aitu_backend.pieces import status as piece_status
from aitu_backend.storage import audio_files, bundle, locate, paths
from aitu_backend.storage.bundle import ProjectFile
from aitu_backend.transcription import jobs, split_cache

__all__ = [
    "Refused",
    "Saved",
    "delete_song",
    "delete_version",
    "history",
    "open_edit",
    "restore",
    "save",
    "snapshot",
]

#: The files of a part that a version carries (the history of the part, ``music-version.json``,
#: stays with the part).
VERSION_FILES = (
    "notes.pmn",
    "sheet.json",
    "timeline.json",
    "needs-rederivation.json",
    "audio-mismatches.json",
)
#: The derived files worth carrying with a part's content: writing them again costs ffmpeg time.
CACHE_FILES = ("normalized.wav",)

#: What the history says about a saved state.
REASONS = {"replaced": "Replaced by an edit", "restored": "Replaced by a restore"}


class Refused(ValueError):
    """The project cannot be saved or edited now, in words for the page: the routes answer 409."""


@dataclass(frozen=True)
class Saved:
    song_id: int
    version_id: int
    project_id: str


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------- checks


def _check_ready(project: ProjectFile) -> None:
    for entry in project.parts:
        if jobs.active(f"transcribe:{entry.id}") or jobs.active(f"video-read:{entry.id}"):
            raise Refused("The notes are being written: save to the library when they are done")
        if piece_status.piece_status(entry.id).step("sheet").state != "ready":
            raise Refused("Save the piano sheet first")


def _compact(project: ProjectFile) -> list[compact.Plan]:
    plans: list[compact.Plan] = []
    try:
        for entry in project.parts:
            plan = compact.prepare(entry.id, project)
            if plan is not None:
                plans.append(plan)
    except Exception:
        for plan in plans:
            compact.discard(plan)
        raise
    return plans


def _apply(plans: list[compact.Plan]) -> list[str]:
    replaced: list[str] = []
    for plan in plans:
        compact.apply(plan)
        replaced.extend(plan.replaced)
    return replaced


def _drop_temporary(project_id: str, owner: int, part_ids: list[str]) -> None:
    """The video and its frames, the open edit sessions, and the history of the parts."""
    for part_id in part_ids:
        shutil.rmtree(paths.tmp_dir() / str(owner) / part_id, ignore_errors=True)
    shutil.rmtree(paths.project_dir(project_id) / "staging", ignore_errors=True)
    shutil.rmtree(paths.saved_versions_dir(project_id) / "parts", ignore_errors=True)


# ----------------------------------------------------------------------- save


def save(
    project_id: str,
    *,
    owner: int,
    version_name: str,
    song_id: int | None = None,
    song_title: str | None = None,
    artist: str | None = None,
    replace: bool = False,
) -> Saved:
    """Save a project of the Personal Vault to the Private Library (section 10.2).

    The song is ``song_id``, or the owner's song called ``song_title`` by ``artist``, made when it
    does not exist. ``replace`` saves an edit copy over the version it was made from (section
    10.6); the song and the version name are then that version's.
    """
    where = locate.project(project_id)
    if where.layer != "vault" or where.owner_id != owner:
        raise Refused("Only a project of your Projects can be saved to the library")
    with bundle.project_lock(project_id):
        project = bundle.read_project(project_id)
        _check_ready(project)
        if replace:
            return _replace(project, owner)

        with session() as db:
            title = None
            found: Song | None
            if song_id is not None:
                found = rows.song(db, owner, song_id)
            else:
                title = rows.clean(song_title, "A song's title")
                found = rows.find_song(db, owner, title, artist)
            if found is not None:
                name = rows.check_version_name(db, found.id, version_name)
                known_song = found.id
            else:
                name = rows.clean(version_name, "A version name", rows.VERSION_LIMIT)
                known_song = None
            if artist is not None and artist.strip():
                rows.clean(artist, "An artist's name")

        part_ids = [entry.id for entry in project.parts]
        plans = _compact(project)
        source = paths.project_dir_at(project_id, owner, "vault")
        target = paths.project_dir_at(project_id, owner, "private")
        if target.exists():
            for plan in plans:
                compact.discard(plan)
            raise Refused("The library already has a project with this id")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))
        with session() as db:
            row = db.get(Project, project_id)
            assert row is not None
            row.layer = "private"
            row.based_on = None
        locate.forget(project_id)

        replaced = _apply(plans)
        project = bundle.read_project(project_id)
        if project.based_on is not None:
            # A copy saved as a new version stops being a copy.
            bundle.write_project(project.model_copy(update={"based_on": None}), touch=False)
        _drop_temporary(project_id, owner, part_ids)
        bundle.sync_audio_refs(project_id)
        audio_files.delete_unused(replaced)

        with session() as db:
            if known_song is not None:
                song = rows.song(db, owner, known_song)
            else:
                song = rows.make_song(db, owner, title or "", artist)
            version = PrivateVersion(song_id=song.id, version_name=name, project_id=project_id)
            db.add(version)
            db.flush()
            return Saved(song_id=song.id, version_id=version.id, project_id=project_id)


def _replace(copy: ProjectFile, owner: int) -> Saved:
    """The edit copy's content becomes the version's; the copy is deleted (section 10.6)."""
    library_id = copy.based_on
    if not library_id:
        raise Refused("This project is not a copy of a version of your library")
    try:
        where = locate.project(library_id)
    except locate.NotFound:
        raise Refused(
            "The version this project edits was deleted: save it as a new version"
        ) from None
    if where.layer != "private" or where.owner_id != owner:
        raise Refused("This project is not a copy of a version of your library")
    with session() as db:
        version = rows.version_of_project(db, library_id)
        if version is None:
            raise Refused("The version this project edits was deleted: save it as a new version")
        saved = Saved(song_id=version.song_id, version_id=version.id, project_id=library_id)

    with bundle.project_lock(library_id):
        replaced = _apply(_compact(copy))
        copy = bundle.read_project(copy.id)
        snapshot(library_id, "replaced")
        _write_into(
            library_id,
            copy,
            [paths.part_dir(entry.id) for entry in copy.parts],
            [paths.part_cache_dir(entry.id) for entry in copy.parts],
        )
        bundle.sync_audio_refs(library_id)
    bundle.delete_project(copy.id)
    audio_files.delete_unused(replaced)
    return saved


def _write_into(
    library_id: str,
    source: ProjectFile,
    part_dirs: list[Path],
    cache_dirs: list[Path | None],
) -> None:
    """The content of ``source`` (its ``project.json`` and the files of its parts) becomes the
    library project's. The library project keeps its id and its parts' ids, in order."""
    library = bundle.read_project(library_id)
    old_ids = [entry.id for entry in library.parts]
    entries = [
        entry.model_copy(update={"id": old_ids[index] if index < len(old_ids) else bundle.new_id()})
        for index, entry in enumerate(source.parts)
    ]
    gone = old_ids[len(entries) :]
    with session() as db:
        for part_id in gone:
            row = db.get(Part, part_id)
            if row is not None:
                db.delete(row)
        db.flush()
        for index, entry in enumerate(entries):
            if db.get(Part, entry.id) is None:
                db.add(Part(id=entry.id, project_id=library_id, position=index))
    locate.forget(library_id)

    root = paths.project_dir(library_id)
    for part_id in gone:
        shutil.rmtree(root / "parts" / part_id, ignore_errors=True)
        shutil.rmtree(root / "cache" / part_id, ignore_errors=True)
    for index, entry in enumerate(entries):
        folder = root / "parts" / entry.id
        folder.mkdir(parents=True, exist_ok=True)
        for name in VERSION_FILES:
            origin = part_dirs[index] / name
            if origin.is_file():
                # A copy with a new time: the caches keyed by a file's time see a new file.
                shutil.copyfile(origin, folder / name)
            else:
                (folder / name).unlink(missing_ok=True)
        cache = root / "cache" / entry.id
        shutil.rmtree(cache, ignore_errors=True)
        cache.mkdir(parents=True)
        from_cache = cache_dirs[index]
        if from_cache is not None and from_cache.is_dir():
            for path in [
                *(from_cache / name for name in CACHE_FILES),
                *from_cache.glob("src-*.wav"),
            ]:
                if path.is_file():
                    shutil.copyfile(path, cache / path.name)
        split_cache.forget(entry.id)
    bundle.write_project(
        source.model_copy(
            update={
                "id": library_id,
                "owner_id": library.owner_id,
                "created_at": library.created_at,
                "origin": library.origin,
                "based_on": None,
                "revision": library.revision + 1,
                "parts": entries,
            }
        )
    )
    for entry in entries:
        bundle.step_changed(entry.id)


# ------------------------------------------------------------------- history


def _numbers(project_id: str) -> list[int]:
    root = paths.saved_versions_dir(project_id)
    if not root.is_dir():
        return []
    return sorted(
        int(path.name[1:])
        for path in root.iterdir()
        if path.is_dir() and path.name.startswith("v") and path.name[1:].isdigit()
    )


def snapshot(project_id: str, reason: str) -> int:
    """Keep the current state of a library project in its history. Returns its number."""
    number = (_numbers(project_id) or [0])[-1] + 1
    target = paths.saved_version_dir(project_id, number)
    temporary = target.with_name(f".{target.name}.tmp")
    shutil.rmtree(temporary, ignore_errors=True)
    temporary.mkdir(parents=True)
    root = paths.project_dir(project_id)
    project = bundle.read_project(project_id)
    shutil.copyfile(root / "project.json", temporary / "project.json")
    for entry in project.parts:
        folder = temporary / "parts" / entry.id
        folder.mkdir(parents=True)
        for name in VERSION_FILES:
            if (root / "parts" / entry.id / name).is_file():
                shutil.copy2(root / "parts" / entry.id / name, folder / name)
    (temporary / "snapshot.json").write_text(
        json.dumps({"version": number, "savedAt": _now().isoformat(), "reason": reason}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    temporary.rename(target)
    return number


@dataclass(frozen=True)
class Earlier:
    number: int
    saved_at: datetime
    reason: str


def history(project_id: str) -> list[Earlier]:
    """The earlier states of a library project, the newest first."""
    out: list[Earlier] = []
    for number in reversed(_numbers(project_id)):
        path = paths.saved_version_dir(project_id, number) / "snapshot.json"
        try:
            body = json.loads(path.read_text(encoding="utf-8"))
            moment = datetime.fromisoformat(body["savedAt"])
            reason = REASONS.get(body.get("reason", ""), body.get("reason", ""))
        except (OSError, ValueError, KeyError):
            continue
        out.append(Earlier(number=number, saved_at=moment, reason=reason))
    return out


def restore(project_id: str, number: int) -> None:
    """Make an earlier state the version's content again; the current one goes to the history."""
    folder = paths.saved_version_dir(project_id, number)
    if not (folder / "project.json").is_file():
        raise rows.NotFound(f"No earlier state {number}")
    with bundle.project_lock(project_id):
        source = ProjectFile.model_validate_json((folder / "project.json").read_text("utf-8"))
        snapshot(project_id, "restored")
        _write_into(
            project_id,
            source,
            [folder / "parts" / entry.id for entry in source.parts],
            [None] * len(source.parts),
        )
        bundle.sync_audio_refs(project_id)


# ----------------------------------------------------------------- edit copies


def open_edit(library_id: str, *, owner: int) -> str:
    """The vault copy that edits a version: the one already open, or a new one (section 10.6)."""
    where = locate.project(library_id)
    if where.layer != "private" or where.owner_id != owner:
        raise Refused("Only a version of your own library can be edited")
    with session() as db:
        existing = rows.edit_copies(db, owner, [library_id]).get(library_id)
    if existing is not None:
        return existing
    library = bundle.read_project(library_id)
    copy = bundle.duplicate_project(library_id, owner_id=owner, layer="vault", title=library.title)
    bundle.write_project(
        copy.model_copy(update={"based_on": library_id, "origin": {"editOf": library_id}}),
        touch=False,
    )
    return copy.id


def _forget_edits_of(owner: int, library_id: str) -> None:
    """The edit copies of a deleted version become ordinary projects of the vault."""
    with session() as db:
        copies = list(
            db.scalars(
                select(Project.id).where(Project.owner_id == owner, Project.based_on == library_id)
            )
        )
        db.execute(update(Project).where(Project.id.in_(copies)).values(based_on=None))
    for copy_id in copies:
        with bundle.project_lock(copy_id):
            project = bundle.read_project(copy_id)
            bundle.write_project(project.model_copy(update={"based_on": None}), touch=False)


def delete_version(version_id: int, *, owner: int) -> None:
    """Delete a version and its project, its history, and the audio no other project uses."""
    with session() as db:
        version = rows.version(db, owner, version_id)
        project_id = version.project_id
        db.delete(version)
    _forget_edits_of(owner, project_id)
    bundle.delete_project(project_id)


def delete_song(song_id: int, *, owner: int) -> None:
    """Delete a song with every version it has."""
    with session() as db:
        song = rows.song(db, owner, song_id)
        version_ids = [one.id for one in rows.versions_of(db, [song.id])[song.id]]
    for version_id in version_ids:
        delete_version(version_id, owner=owner)
    with session() as db:
        db.delete(rows.song(db, owner, song_id))
