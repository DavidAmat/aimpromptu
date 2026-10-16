"""``/projects``: the projects of the Personal Vault (implementation 02, plan sections 8.8 and 10.1).

List, create, rename, delete, duplicate, export and import; **Save to library** and **Edit** (Phase
6, sections 10.2 and 10.6), which move a project into the Private Library and copy a version out of
it; **From other projects** and the parts of a project (Phase 10, sections 10.4 and 14.1). A project made by this app has the id of
its first part, so the uuid of a piece is also the id of its project, and the routes of the steps
(``/audio``, ``/pieces``, ``/time``, ``/matrix``) keep working on it.

**The step of a row** is the lowest step its parts reached (section 10.5), kept in
``projects.step``. Computing it reads the notes and the sheet of every part (about 25 ms a part), so
it is stored: a write of a part's notes, sheet or timeline clears it
(:func:`aitu_backend.storage.bundle.step_changed`), and the list works out again only the rows it
finds cleared. A part whose transcription or video reading is running says so instead.
"""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path
from typing import Annotated, Callable, Literal

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from starlette.background import BackgroundTask

from aitu_backend.db import tools
from aitu_backend.db.database import session
from aitu_backend.db.models import Project
from aitu_backend.auth.dependencies import require_part
from aitu_backend.db.users import current_user_id
from aitu_backend.editing import parts as project_parts, paste
from aitu_backend.library import flow, rows
from aitu_backend.matrix.time_grid import DEFAULT_FRAME_MS
from aitu_backend.schemas.rhythm import SavedRhythm
from aitu_backend.storage import bundle, exchange, locate
from aitu_backend.transcription import jobs, pipeline
from aitu_backend.video import store as video_store

router = APIRouter(prefix="/projects", tags=["projects"])

Layer = Literal["vault", "private"]


class _Camel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class LibraryLink(_Camel):
    """The song and the version a project is (or, for an edit copy, the one it edits)."""

    song_id: int = Field(..., alias="songId")
    song_title: str = Field(..., alias="songTitle")
    artists: list[str]
    version_id: int = Field(..., alias="versionId")
    version_name: str = Field(..., alias="versionName")
    #: The library project of that version.
    project_id: str = Field(..., alias="projectId")


class ProjectRow(_Camel):
    """One project, as the Projects page lists it."""

    id: str
    title: str
    kind: str
    #: ``vault`` (Personal Vault), ``private`` (Private Library), ``public``, or ``request`` (the
    #: copy a request sent, Phase 14).
    layer: str
    #: The user of this call owns it. A library project of another user is one shared with them
    #: (Phase 14), which they read and never edit.
    mine: bool = True
    #: The lowest step the parts reached: ``audio``, ``notes``, ``hands`` or ``sheet``.
    step: str | None = None
    #: ``transcribing`` or ``reading`` while a job works on a part, else ``None``.
    running: str | None = None
    #: The ids of the parts, in order. The first one is the uuid the step routes take.
    parts: list[str]
    #: Where the audio of the first part came from: ``upload``, ``youtube``, ``recording`` ...
    source: str | None = None
    has_video: bool = Field(False, alias="hasVideo")
    has_notes: bool = Field(False, alias="hasNotes")
    based_on: str | None = Field(None, alias="basedOn")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime | None = Field(None, alias="updatedAt")
    #: A project of the Private Library: its song and version.
    library: LibraryLink | None = None
    #: A project of the Personal Vault that edits a version (section 10.6): that version.
    editing: LibraryLink | None = None


class ProjectOut(_Camel):
    id: str
    title: str
    #: The ids of the parts, in order. The first one is the uuid the other routes take.
    parts: list[str]


class DuplicateIn(_Camel):
    #: The title of the copy; the original's when absent.
    title: str | None = Field(None, max_length=300)


class CreateIn(_Camel):
    title: str = Field("", max_length=300)
    #: **From scratch** (section 10.3): a blank piano sheet, with no notes and no audio yet, that
    #: opens on the Sheet step. Without it the project waits for its source.
    scratch: bool = False


class RenameIn(_Camel):
    title: str = Field(..., min_length=1, max_length=300)


class SaveIn(_Camel):
    """**Save to library**: the song (an existing one by id, or a title and an artist) and the
    version name; or ``replace`` for an edit copy, which saves over the version it edits."""

    song_id: int | None = Field(None, alias="songId")
    song: str | None = Field(None, max_length=300)
    artist: str | None = Field(None, max_length=300)
    version: str = Field("", max_length=200)
    replace: bool = False
    #: A song or an artist of the Public Library chosen in the dialog (Phase 13): the private song
    #: or artist that stands for it is used, or made with a link to it.
    public_song_id: int | None = Field(None, alias="publicSongId")
    public_artist_id: int | None = Field(None, alias="publicArtistId")


class SavedOut(_Camel):
    song_id: int = Field(..., alias="songId")
    version_id: int = Field(..., alias="versionId")
    project_id: str = Field(..., alias="projectId")


class ChosenIn(_Camel):
    """One passage of **From other projects**: a part the user may read and a stretch of it."""

    part: str
    #: The stretch in ms of the part; both absent for the whole of it.
    from_ms: float | None = Field(None, alias="fromMs", ge=0)
    to_ms: float | None = Field(None, alias="toMs", gt=0)
    #: How it joins the passage before it: in the same part, or a new part with a title.
    join: Literal["sequential", "subheader"] = "sequential"
    subheader: str | None = Field(None, max_length=300)


class ComposeIn(_Camel):
    title: str = Field("", max_length=300)
    kind: Literal["song", "integratedPlaylist"] = "song"
    passages: list[ChosenIn] = Field(..., min_length=1, max_length=200)


class PartRow(_Camel):
    id: str
    #: The title drawn above the part; ``None`` when it has none.
    subheader: str | None = None
    duration_ms: float = Field(..., alias="durationMs")


class PartsOrderIn(_Camel):
    order: list[str] = Field(..., min_length=1)


class PartChangeIn(_Camel):
    subheader: str | None = Field(None, max_length=300)


class SplitIn(_Camel):
    #: Where the new part starts, in ms of the part.
    at_ms: float = Field(..., alias="atMs", gt=0)
    subheader: str | None = Field(None, max_length=300)
    #: The part's sheet as the page holds it, unsaved edits included; saved by the split.
    sheet: SavedRhythm | None = None


class PartsOut(_Camel):
    parts: list[PartRow]
    #: The part the change left on show: the one joined into, or the new one of a split.
    part: str | None = None


def _running(part_ids: list[str]) -> str | None:
    for part_id in part_ids:
        if jobs.active(f"transcribe:{part_id}") is not None:
            return "transcribing"
        if jobs.active(f"video-read:{part_id}") is not None:
            return "reading"
    return None


def _links(projects: list[Project]) -> dict[str, LibraryLink]:
    """The song and version of each library project, and of the version each edit copy edits."""
    wanted = [row.id for row in projects if row.layer == "private"]
    wanted += [row.based_on for row in projects if row.based_on]
    with session() as db:
        found = rows.links_of(db, wanted)
    return {
        project_id: LibraryLink(
            song_id=link.song_id,
            song_title=link.song_title,
            artists=link.artists,
            version_id=link.version_id,
            version_name=link.version_name,
            project_id=project_id,
        )
        for project_id, link in found.items()
    }


def _row(project: Project, links: dict[str, LibraryLink] | None = None) -> ProjectRow:
    part_ids = bundle.part_ids_of(project.id)
    step = project.step
    if step is None:
        step = tools.refresh_step(project.id)
    source = None
    try:
        source = bundle.read_project(project.id).parts[0].source.kind
    except (locate.NotFound, IndexError, ValueError):
        pass
    first = part_ids[0] if part_ids else None
    if links is None:
        links = _links([project])
    return ProjectRow(
        id=project.id,
        title=project.title,
        kind=project.kind,
        layer=project.layer,
        mine=project.owner_id == current_user_id(),
        step=step,
        running=_running(part_ids),
        parts=part_ids,
        source=source,
        has_video=bool(first and video_store.exists(first)),
        has_notes=bool(first and pipeline.has_events(first)),
        based_on=project.based_on,
        created_at=project.created_at,
        updated_at=bundle.last_change(project.id) or project.updated_at,
        library=links.get(project.id) if project.layer == "private" else None,
        editing=links.get(project.based_on) if project.based_on else None,
    )


def _project_or_404(project_id: str) -> Project:
    with session() as db:
        row = db.get(Project, project_id)
        if row is None:
            raise HTTPException(status_code=404, detail=f"No project with id '{project_id}'")
        db.expunge(row)
        return row


@router.get("", response_model=list[ProjectRow], response_model_by_alias=True)
def list_projects(
    layer: Annotated[list[Layer] | None, Query()] = None,
) -> list[ProjectRow]:
    """The current user's projects, the most recently changed first: the Personal Vault, or the
    layers asked for (``?layer=vault&layer=private``)."""
    layers = layer or ["vault"]
    with session() as db:
        found = list(
            db.scalars(
                select(Project).where(
                    Project.owner_id == current_user_id(),
                    Project.layer.in_(layers),
                    # A passage being re-recorded and its takes are work of the Sheet step.
                    Project.kind != "passage",
                )
            )
        )
        for row in found:
            db.expunge(row)
    links = _links(found)
    out = [_row(row, links) for row in found]
    out.sort(key=lambda item: item.updated_at or item.created_at, reverse=True)
    return out


@router.post("", response_model=ProjectRow, response_model_by_alias=True, status_code=201)
def create_project(body: CreateIn | None = None) -> ProjectRow:
    """An empty project in the Personal Vault: no audio. With ``scratch`` it is **From scratch**
    (section 10.3): an empty ``notes.pmn`` at the default frame length, so it opens on a blank
    piano sheet, filled by Record and Paste."""
    title = body.title if body else ""
    if body is not None and body.scratch:
        project = bundle.create_project(
            owner_id=current_user_id(),
            title=title,
            source=bundle.PartSource(kind="composed", format="wav"),
            frame_ms=DEFAULT_FRAME_MS,
        )
        pipeline.save_note_events(project.parts[0].id, [], 0.0, title)
    else:
        project = bundle.create_project(owner_id=current_user_id(), title=title)
    return _row(_project_or_404(project.id))


@router.post("/compose", response_model=ProjectRow, response_model_by_alias=True, status_code=201)
def compose_project(body: ComposeIn) -> ProjectRow:
    """**From other projects** (section 10.4): a new project of the Personal Vault made of the
    passages, in order. A ``subheader`` join starts a new part. Every source must be a part the
    user may read (``404`` otherwise); the passages are copies, and no audio byte is copied."""
    for chosen in body.passages:
        require_part(chosen.part, write=False)
    try:
        project = project_parts.assemble(
            owner_id=current_user_id(),
            title=body.title,
            kind=body.kind,
            passages=[
                project_parts.Chosen(
                    part=one.part,
                    from_ms=one.from_ms,
                    to_ms=one.to_ms,
                    join=one.join,
                    subheader=one.subheader,
                )
                for one in body.passages
            ],
        )
    except locate.NotFound as exc:
        raise HTTPException(
            status_code=404, detail="A chosen passage is not there any more."
        ) from exc
    except (project_parts.PartsError, paste.PasteError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _row(_project_or_404(project.id))


@router.post("/import", response_model=ProjectRow, response_model_by_alias=True, status_code=201)
def import_project(file: Annotated[UploadFile, File()]) -> ProjectRow:
    """A ``.aitu`` file made into a new project of the current user's Personal Vault."""
    try:
        project = exchange.import_upload(file.file, owner_id=current_user_id())
    except exchange.ImportRefused as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _row(_project_or_404(project.id))


@router.get("/{project_id}", response_model=ProjectRow, response_model_by_alias=True)
def get_project(project_id: str) -> ProjectRow:
    return _row(_project_or_404(project_id))


@router.patch("/{project_id}", response_model=ProjectRow, response_model_by_alias=True)
def rename_project(project_id: str, body: RenameIn) -> ProjectRow:
    """Change the title of a project."""
    _project_or_404(project_id)
    title = body.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="A title cannot be empty")
    with bundle.project_lock(project_id):
        project = bundle.read_project(project_id)
        bundle.write_project(project.model_copy(update={"title": title}))
    return _row(_project_or_404(project_id))


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: str) -> None:
    """Delete a project with everything it has: its bundle, its history, its temporary files (a
    video and its frames), and the audio files no other project uses."""
    _project_or_404(project_id)
    bundle.delete_project(project_id)


@router.post(
    "/{project_id}/duplicate",
    status_code=201,
    response_model=ProjectOut,
    response_model_by_alias=True,
)
def duplicate(project_id: str, body: DuplicateIn | None = None) -> ProjectOut:
    """A copy of the project in the current user's Personal Vault, with new ids. The audio files
    are shared, not copied (P-3); staging, history and the video are not copied."""
    try:
        copy = bundle.duplicate_project(
            project_id,
            owner_id=current_user_id(),
            title=body.title if body else None,
        )
    except locate.NotFound as exc:
        raise HTTPException(status_code=404, detail=f"No project with id '{project_id}'") from exc
    return ProjectOut(id=copy.id, title=copy.title, parts=[part.id for part in copy.parts])


@router.get("/{project_id}/export")
def export_project(project_id: str) -> FileResponse:
    """The ``.aitu`` file of the project: its bundle and the audio files it uses (section 8.3)."""
    row = _project_or_404(project_id)
    handle, name = tempfile.mkstemp(prefix="aitu-export-", suffix=exchange.EXTENSION)
    target = Path(name)
    with open(handle, "wb"):
        pass
    try:
        exchange.export_project(project_id, target)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return FileResponse(
        target,
        media_type="application/zip",
        filename=exchange.export_name(row.title),
        background=BackgroundTask(target.unlink, missing_ok=True),
    )


@router.post(
    "/{project_id}/library",
    response_model=SavedOut,
    response_model_by_alias=True,
    status_code=201,
)
def save_to_library(project_id: str, body: SaveIn) -> SavedOut:
    """**Save to library** (section 10.2): the project moves from the Personal Vault into the
    Private Library as a version of a song. Its audio is written again with only the ranges in use,
    and its temporary files are deleted (section 8.5, Q-3). An edit copy can instead **replace the
    version** it edits (section 10.6). ``409`` when the piano sheet is not saved yet, a job is
    writing the notes, or the song already has a version of that name."""
    _project_or_404(project_id)
    try:
        saved = flow.save(
            project_id,
            owner=current_user_id(),
            version_name=body.version,
            song_id=body.song_id,
            song_title=body.song,
            artist=body.artist,
            replace=body.replace,
            public_song_id=body.public_song_id,
            public_artist_id=body.public_artist_id,
        )
    except rows.NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (rows.Conflict, flow.Refused) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return SavedOut(song_id=saved.song_id, version_id=saved.version_id, project_id=saved.project_id)


@router.post("/{project_id}/edit", response_model=ProjectRow, response_model_by_alias=True)
def edit_version(project_id: str) -> ProjectRow:
    """**Edit** a version of the Private Library (section 10.6): a copy in the Personal Vault that
    points at it (``basedOn``). The copy already open is returned instead of a second one."""
    _project_or_404(project_id)
    try:
        copy_id = flow.open_edit(project_id, owner=current_user_id())
    except flow.Refused as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _row(_project_or_404(copy_id))


# ----------------------------------------------------------------------- parts


def _parts_out(project_id: str, part: str | None = None) -> PartsOut:
    return PartsOut(
        parts=[
            PartRow(id=one.id, subheader=one.subheader, duration_ms=one.duration_ms)
            for one in project_parts.facts(project_id)
        ],
        part=part,
    )


def _part_of(project_id: str, part_id: str) -> None:
    try:
        if locate.part(part_id).project_id == project_id:
            return
    except locate.NotFound:
        pass
    raise HTTPException(status_code=404, detail=f"No part with id '{part_id}' in this project")


@router.get("/{project_id}/parts", response_model=PartsOut, response_model_by_alias=True)
def list_parts(project_id: str) -> PartsOut:
    """The parts of a project in order (section 8.4): the sub-songs of an integrated playlist."""
    _project_or_404(project_id)
    return _parts_out(project_id)


@router.put("/{project_id}/parts", response_model=PartsOut, response_model_by_alias=True)
def reorder_parts(project_id: str, body: PartsOrderIn) -> PartsOut:
    """The parts in a new order; ``order`` names every part once."""
    _project_or_404(project_id)
    try:
        bundle.reorder_parts(project_id, body.order)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _parts_out(project_id)


@router.patch(
    "/{project_id}/parts/{part_id}", response_model=PartsOut, response_model_by_alias=True
)
def change_part(project_id: str, part_id: str, body: PartChangeIn) -> PartsOut:
    """The title above a part (its subheader); empty takes it away."""
    _part_of(project_id, part_id)
    project_parts.rename(project_id, part_id, body.subheader)
    return _parts_out(project_id, part_id)


def _parts_answers(action: Callable[[], str]) -> str:
    try:
        return action()
    except locate.NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (project_parts.PartsError, paste.PasteError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post(
    "/{project_id}/parts/{part_id}/join", response_model=PartsOut, response_model_by_alias=True
)
def join_part(project_id: str, part_id: str) -> PartsOut:
    """The part joined to the one before it: one part, played without a break (section 14.1)."""
    _part_of(project_id, part_id)
    kept = _parts_answers(lambda: project_parts.join(project_id, part_id))
    return _parts_out(project_id, kept)


@router.post(
    "/{project_id}/parts/{part_id}/split", response_model=PartsOut, response_model_by_alias=True
)
def split_part(project_id: str, part_id: str, body: SplitIn) -> PartsOut:
    """The part split at ``atMs``: what follows becomes a new part after it (section 14.1)."""
    _part_of(project_id, part_id)
    new_part = _parts_answers(
        lambda: project_parts.split(
            project_id, part_id, body.at_ms, subheader=body.subheader, sheet=body.sheet
        )
    )
    return _parts_out(project_id, new_part)
