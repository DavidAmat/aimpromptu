"""``/metadata``: the metadata of a song of My Library or of a project of My projects
(implementation 04-3, Phase 1, plan section 4.4).

A metadata row is a primary key (``films``, ``tv_shows``, ``video_games``, ``adverts``: the list of
the Public Library) and a secondary key of the user's own ("The Lord of the Rings"). The rows of
``GET /projects`` and ``GET /library/songs`` carry each item's metadata; the Filter is worked out on
the page from them. The logic is in :mod:`aitu_backend.library.metadata`.

``GET /metadata/info/{project_id}`` is what the **info button** of the sheet page opens: the song or
the project the sheet belongs to, its metadata, its folders, and whether the user may change them:

* a project of My projects (also an edit copy of a version): the project's own metadata;
* a version of My Library: the song's;
* a version of the Public Library (or of a library shared with the user): the song's, read only.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from aitu_backend.db.database import session
from aitu_backend.db.models import PrivateVersion, Project, Song, SongVersion, UserVersion
from aitu_backend.db.users import current_user_id
from aitu_backend.library import folders, metadata, rows

router = APIRouter(prefix="/metadata", tags=["metadata"])


class _Camel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class TagRow(_Camel):
    #: The primary key: ``films``, ``tv_shows``, ``video_games`` or ``adverts``.
    category: str
    #: The secondary key.
    value: str = Field(..., max_length=metadata.VALUE_LIMIT)


class TagsIn(_Camel):
    #: Every metadata row of the item; an empty list takes them all away.
    tags: list[TagRow] = Field(default_factory=list, max_length=metadata.MAX_TAGS)


class TagsOut(_Camel):
    tags: list[TagRow]


class SuggestionRow(_Camel):
    category: str
    value: str
    #: The user's own value; else one of the Public Library.
    mine: bool


class KeysOut(_Camel):
    #: The primary keys, in the order of the Public Library.
    categories: list[str]
    suggestions: list[SuggestionRow]


class InfoOut(_Camel):
    """What the info button shows for the sheet of a project."""

    #: ``project`` (My projects), ``song`` (My Library, or a library shared with the user),
    #: ``public`` (the Public Library), ``none`` (a sheet with no song: a request's copy).
    kind: Literal["project", "song", "public", "none"]
    project_id: str = Field(..., alias="projectId")
    #: The song of a ``song`` or ``public`` sheet.
    song_id: int | None = Field(None, alias="songId")
    title: str
    artists: list[str]
    tags: list[TagRow]
    #: The folders of the item, in its tree (``project``: My projects; ``song``: My Library).
    folders: list[int]
    #: The user may change the metadata and the folders.
    editable: bool


@contextmanager
def _answers() -> Iterator[None]:
    try:
        yield
    except rows.NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def tag_rows(tags: list[metadata.Tag]) -> list[TagRow]:
    return [TagRow(category=one.category, value=one.value) for one in tags]


def _tags(body: TagsIn) -> list[metadata.Tag]:
    return [metadata.Tag(one.category, one.value) for one in body.tags]


@router.get("/keys", response_model=KeysOut, response_model_by_alias=True)
def keys() -> KeysOut:
    """The primary keys, and the secondary keys the field suggests: the user's own, then the
    Public Library's (so "The Lord of the Rings" is typed once)."""
    with session() as db:
        found = metadata.suggestions(db, current_user_id())
    return KeysOut(
        categories=metadata.categories(),
        suggestions=[
            SuggestionRow(category=one.category, value=one.value, mine=one.mine) for one in found
        ],
    )


@router.put("/projects/{project_id}", response_model=TagsOut, response_model_by_alias=True)
def set_project_tags(project_id: str, body: TagsIn) -> TagsOut:
    """The metadata of a project of My projects, all of it."""
    owner = current_user_id()
    with _answers(), session() as db:
        row = db.get(Project, project_id)
        if row is None or row.owner_id != owner or row.layer != "vault":
            raise rows.NotFound(f"No project with id '{project_id}' in your projects")
        return TagsOut(tags=tag_rows(metadata.set_project_tags(db, owner, project_id, _tags(body))))


@router.put("/songs/{song_id}", response_model=TagsOut, response_model_by_alias=True)
def set_song_tags(song_id: int, body: TagsIn) -> TagsOut:
    """The metadata of a song of My Library, all of it."""
    with _answers(), session() as db:
        return TagsOut(
            tags=tag_rows(metadata.set_song_tags(db, current_user_id(), song_id, _tags(body)))
        )


def _public_song_of(db: DbSession, project_id: str) -> int | None:
    fixed = db.scalar(select(SongVersion.song_id).where(SongVersion.project_id == project_id))
    if fixed is not None:
        return int(fixed)
    other = db.scalar(select(UserVersion.song_id).where(UserVersion.project_id == project_id))
    return int(other) if other is not None else None


@router.get("/info/{project_id}", response_model=InfoOut, response_model_by_alias=True)
def info(project_id: str) -> InfoOut:
    """The info button of the sheet page (the route's rights already let the user read it)."""
    user = current_user_id()
    with _answers(), session() as db:
        project = db.get(Project, project_id)
        if project is None:
            raise rows.NotFound(f"No project with id '{project_id}'")
        if project.layer == "vault":
            link = rows.links_of(db, [project.based_on] if project.based_on else [])
            edited = link.get(project.based_on or "")
            return InfoOut(
                kind="project",
                project_id=project_id,
                title=project.title,
                artists=edited.artists if edited else [],
                tags=tag_rows(metadata.tags_of_projects(db, [project_id])[project_id]),
                folders=folders.folders_of_projects(db, [project_id])[project_id],
                editable=project.owner_id == user,
            )
        song: Song | None = None
        kind: Literal["song", "public"] = "song"
        tags: list[metadata.Tag] = []
        if project.layer == "private":
            song_id = db.scalar(
                select(PrivateVersion.song_id).where(PrivateVersion.project_id == project_id)
            )
            song = db.get(Song, song_id) if song_id is not None else None
            if song is not None:
                tags = metadata.tags_of_songs(db, [song.id])[song.id]
        elif project.layer == "public":
            public_id = _public_song_of(db, project_id)
            song = db.get(Song, public_id) if public_id is not None else None
            kind = "public"
            if song is not None:
                tags = metadata.public_tags_of(db, song.id)
        if song is None:
            return InfoOut(
                kind="none",
                project_id=project_id,
                title=project.title,
                artists=[],
                tags=[],
                folders=[],
                editable=False,
            )
        mine = kind == "song" and song.owner_id == user
        return InfoOut(
            kind=kind,
            project_id=project_id,
            song_id=song.id,
            title=song.title,
            artists=[credit.name for credit in rows.credits_of(db, [song.id])[song.id]],
            tags=tag_rows(tags),
            folders=folders.folders_of_songs(db, [song.id])[song.id] if mine else [],
            editable=mine,
        )
