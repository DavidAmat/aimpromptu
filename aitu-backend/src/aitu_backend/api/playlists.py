"""``/playlists``: the songs playlists of the current user's Private Library (implementation 02,
plan section 14.2, Phase 10).

Every route works on the user's own playlists only and answers 404 for another user's, as the
library routes do (section 9.3). The logic is in :mod:`aitu_backend.library.playlists`.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Iterator

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from aitu_backend.db.database import session
from aitu_backend.db.users import current_user_id
from aitu_backend.library import playlists, rows
from aitu_backend.storage import bundle

router = APIRouter(prefix="/playlists", tags=["playlists"])


class _Camel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class VersionChoice(_Camel):
    project_id: str = Field(..., alias="projectId")
    name: str


class ItemRow(_Camel):
    id: int
    song_id: int = Field(..., alias="songId")
    song_title: str = Field(..., alias="songTitle")
    artists: list[str]
    #: The version on show: the chosen one, or the song's first.
    project_id: str | None = Field(None, alias="projectId")
    version_name: str | None = Field(None, alias="versionName")
    #: The parts of that version; the first is the uuid the step routes take.
    parts: list[str] = Field(default_factory=list)
    versions: list[VersionChoice]
    from_ms: int | None = Field(None, alias="fromMs")
    to_ms: int | None = Field(None, alias="toMs")


class PlaylistRow(_Camel):
    id: int
    title: str
    songs: int
    updated_at: datetime = Field(..., alias="updatedAt")


class PlaylistDetail(_Camel):
    id: int
    title: str
    updated_at: datetime = Field(..., alias="updatedAt")
    items: list[ItemRow]


class ItemIn(_Camel):
    song_id: int = Field(..., alias="songId")
    #: The version; the song's first when absent.
    project_id: str | None = Field(None, alias="projectId")
    from_ms: int | None = Field(None, alias="fromMs", ge=0)
    to_ms: int | None = Field(None, alias="toMs", gt=0)


class PlaylistIn(_Camel):
    title: str = Field(..., max_length=300)
    items: list[ItemIn] = Field(default_factory=list, max_length=500)


class PlaylistChange(_Camel):
    title: str | None = Field(None, max_length=300)
    #: Every item id once, in the new order.
    order: list[int] | None = None


class ItemsIn(_Camel):
    items: list[ItemIn] = Field(..., min_length=1, max_length=500)


class ItemChange(_Camel):
    project_id: str | None = Field(None, alias="projectId")
    #: A stretch of the song; ``whole`` takes the stretch away.
    from_ms: int | None = Field(None, alias="fromMs", ge=0)
    to_ms: int | None = Field(None, alias="toMs", gt=0)
    whole: bool = False


@contextmanager
def _answers() -> Iterator[None]:
    try:
        yield
    except rows.NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except rows.Conflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _new(items: list[ItemIn]) -> list[playlists.NewItem]:
    return [
        playlists.NewItem(
            song_id=one.song_id, project_id=one.project_id, from_ms=one.from_ms, to_ms=one.to_ms
        )
        for one in items
    ]


def _detail(owner: int, playlist_id: int) -> PlaylistDetail:
    with session() as db:
        facts = playlists.describe(db, owner, playlist_id)
    return PlaylistDetail(
        id=facts.id,
        title=facts.title,
        updated_at=facts.updated_at,
        items=[
            ItemRow(
                id=item.id,
                song_id=item.song_id,
                song_title=item.song_title,
                artists=item.artists,
                project_id=item.project_id,
                version_name=item.version_name,
                parts=bundle.part_ids_of(item.project_id) if item.project_id else [],
                versions=[
                    VersionChoice(project_id=project_id, name=name)
                    for project_id, name in item.versions
                ],
                from_ms=item.from_ms,
                to_ms=item.to_ms,
            )
            for item in facts.items
        ],
    )


@router.get("", response_model=list[PlaylistRow], response_model_by_alias=True)
def list_playlists() -> list[PlaylistRow]:
    with session() as db:
        return [
            PlaylistRow(id=row.id, title=row.title, songs=count, updated_at=row.updated_at)
            for row, count in playlists.list_of(db, current_user_id())
        ]


@router.post("", response_model=PlaylistDetail, response_model_by_alias=True, status_code=201)
def create_playlist(body: PlaylistIn) -> PlaylistDetail:
    """A new playlist, empty or with songs (**Make a playlist** from a selection of songs)."""
    owner = current_user_id()
    with _answers():
        with session() as db:
            row = playlists.create(db, owner, body.title, _new(body.items))
            playlist_id = row.id
        return _detail(owner, playlist_id)


@router.get("/{playlist_id}", response_model=PlaylistDetail, response_model_by_alias=True)
def get_playlist(playlist_id: int) -> PlaylistDetail:
    with _answers():
        return _detail(current_user_id(), playlist_id)


@router.patch("/{playlist_id}", response_model=PlaylistDetail, response_model_by_alias=True)
def change_playlist(playlist_id: int, body: PlaylistChange) -> PlaylistDetail:
    """Rename it, or put its songs in another order."""
    owner = current_user_id()
    with _answers():
        with session() as db:
            if body.title is not None:
                playlists.rename(db, owner, playlist_id, body.title)
            if body.order is not None:
                playlists.reorder(db, owner, playlist_id, body.order)
        return _detail(owner, playlist_id)


@router.delete("/{playlist_id}", status_code=204)
def delete_playlist(playlist_id: int) -> None:
    """The playlist goes; its songs and their versions stay as they are."""
    with _answers():
        with session() as db:
            playlists.delete_playlist(db, current_user_id(), playlist_id)


@router.post("/{playlist_id}/items", response_model=PlaylistDetail, response_model_by_alias=True)
def add_items(playlist_id: int, body: ItemsIn) -> PlaylistDetail:
    """Songs added at the end."""
    owner = current_user_id()
    with _answers():
        with session() as db:
            playlists.add_items(db, owner, playlist_id, _new(body.items))
        return _detail(owner, playlist_id)


@router.patch(
    "/{playlist_id}/items/{item_id}",
    response_model=PlaylistDetail,
    response_model_by_alias=True,
)
def change_item(playlist_id: int, item_id: int, body: ItemChange) -> PlaylistDetail:
    """Another version of the song, or a stretch of it (``whole`` for all of it)."""
    owner = current_user_id()
    fields = body.model_fields_set
    with _answers():
        with session() as db:
            kwargs: dict[str, object] = {}
            if "project_id" in fields:
                kwargs["project_id"] = body.project_id
            if body.whole:
                kwargs["stretch"] = None
            elif body.from_ms is not None or body.to_ms is not None:
                if body.from_ms is None or body.to_ms is None:
                    raise ValueError("A stretch needs its start and its end")
                kwargs["stretch"] = (body.from_ms, body.to_ms)
            playlists.change_item(db, owner, playlist_id, item_id, **kwargs)
        return _detail(owner, playlist_id)


@router.delete(
    "/{playlist_id}/items/{item_id}",
    response_model=PlaylistDetail,
    response_model_by_alias=True,
)
def remove_item(playlist_id: int, item_id: int) -> PlaylistDetail:
    owner = current_user_id()
    with _answers():
        with session() as db:
            playlists.remove_item(db, owner, playlist_id, item_id)
        return _detail(owner, playlist_id)
