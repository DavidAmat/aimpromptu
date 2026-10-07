"""``/library``: the current user's Private Library (implementation 02, Phase 6, plan sections 6.1,
15.1 and 15.2): songs with their versions, artists with their names, and the history of a version.

Every route works on the user's own rows only, and answers 404 for a row of another user, as the
project routes do (section 9.3). A project is put into the library by ``POST
/projects/{id}/library`` and copied out of it for editing by ``POST /projects/{id}/edit``
(:mod:`aitu_backend.api.projects`); the flows are in :mod:`aitu_backend.library.flow`.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Iterator

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from aitu_backend.db import tools
from aitu_backend.db.database import session
from aitu_backend.db.models import Artist, ArtistName, PrivateVersion, Project, Song, SongArtist
from aitu_backend.db.users import current_user_id
from aitu_backend.library import flow, rows
from aitu_backend.storage import bundle

router = APIRouter(prefix="/library", tags=["library"])


class _Camel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class Credit(_Camel):
    artist_id: int = Field(..., alias="artistId")
    name_id: int = Field(..., alias="nameId")
    name: str


class SongRow(_Camel):
    id: int
    title: str
    artists: list[Credit]
    versions: int
    #: A version of the song is being edited in Projects.
    editing: bool = False
    updated_at: datetime | None = Field(None, alias="updatedAt")


class VersionRow(_Camel):
    id: int
    name: str
    project_id: str = Field(..., alias="projectId")
    #: The parts of the project, in order; the first is the uuid the step routes take.
    parts: list[str]
    step: str | None = None
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime | None = Field(None, alias="updatedAt")
    #: The project in Projects that edits this version (section 10.6), if one is open.
    edit_copy: str | None = Field(None, alias="editCopy")
    #: How many earlier states the version keeps.
    history: int = 0


class SongDetail(_Camel):
    id: int
    title: str
    artists: list[Credit]
    versions: list[VersionRow]


class NameRow(_Camel):
    id: int
    name: str
    is_default: bool = Field(..., alias="isDefault")


class ArtistSong(_Camel):
    id: int
    title: str
    versions: int


class ArtistRow(_Camel):
    id: int
    #: The default name.
    name: str
    names: list[NameRow]
    songs: int


class ArtistDetail(ArtistRow):
    song_list: list[ArtistSong] = Field(default_factory=list, alias="songList")


class Earlier(_Camel):
    number: int
    saved_at: datetime = Field(..., alias="savedAt")
    reason: str


class SongChange(_Camel):
    title: str | None = Field(None, max_length=300)
    #: The song's artists by name, in order; a name not known yet makes a new artist.
    artists: list[str] | None = None


class VersionChange(_Camel):
    name: str = Field(..., max_length=200)


class NameIn(_Camel):
    name: str = Field(..., max_length=300)


class NameChange(_Camel):
    name: str | None = Field(None, max_length=300)
    is_default: bool = Field(False, alias="isDefault")


class MergeIn(_Camel):
    #: The artist that keeps its id and its default name.
    into: int


@contextmanager
def _answers() -> Iterator[None]:
    """The library's refusals as HTTP answers."""
    try:
        yield
    except rows.NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (rows.Conflict, flow.Refused) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _credits(found: list[rows.Credit]) -> list[Credit]:
    return [Credit(artist_id=one.artist_id, name_id=one.name_id, name=one.name) for one in found]


def _versions(owner: int, versions: list[PrivateVersion]) -> list[VersionRow]:
    project_ids = [one.project_id for one in versions]
    with session() as db:
        copies = rows.edit_copies(db, owner, project_ids)
        projects = {
            row.id: (row.step, row.updated_at)
            for row in db.scalars(select(Project).where(Project.id.in_(project_ids)))
        }
    out: list[VersionRow] = []
    for one in versions:
        step, updated = projects.get(one.project_id, (None, None))
        if step is None:
            step = tools.refresh_step(one.project_id)
        out.append(
            VersionRow(
                id=one.id,
                name=one.version_name,
                project_id=one.project_id,
                parts=bundle.part_ids_of(one.project_id),
                step=step,
                created_at=one.created_at,
                updated_at=bundle.last_change(one.project_id) or updated,
                edit_copy=copies.get(one.project_id),
                history=len(flow.history(one.project_id)),
            )
        )
    return out


def _song(owner: int, song_id: int) -> SongDetail:
    with session() as db:
        song = rows.song(db, owner, song_id)
        credits = rows.credits_of(db, [song.id])[song.id]
        versions = rows.versions_of(db, [song.id])[song.id]
        title = song.title
    return SongDetail(
        id=song_id, title=title, artists=_credits(credits), versions=_versions(owner, versions)
    )


def _artist(owner: int, artist_id: int) -> ArtistDetail:
    with session() as db:
        rows.artist(db, owner, artist_id)
        names = rows.names_of(db, artist_id)
        song_ids = rows.song_ids_of_artist(db, artist_id)
        versions = rows.versions_of(db, song_ids)
        songs = sorted(
            (
                ArtistSong(id=one.id, title=one.title, versions=len(versions[one.id]))
                for one in db.scalars(select(Song).where(Song.id.in_(song_ids)))
            ),
            key=lambda item: item.title.casefold(),
        )
        default = next(
            (one.name for one in names if one.is_default), names[0].name if names else ""
        )
        return ArtistDetail(
            id=artist_id,
            name=default,
            names=[NameRow(id=one.id, name=one.name, is_default=one.is_default) for one in names],
            songs=len(songs),
            song_list=songs,
        )


# ----------------------------------------------------------------------- songs


@router.get("/songs", response_model=list[SongRow], response_model_by_alias=True)
def list_songs() -> list[SongRow]:
    """The user's songs, by title."""
    owner = current_user_id()
    with session() as db:
        songs = list(
            db.scalars(select(Song).where(Song.scope == "private", Song.owner_id == owner))
        )
        ids = [one.id for one in songs]
        credits = rows.credits_of(db, ids)
        versions = rows.versions_of(db, ids)
        project_ids = [v.project_id for group in versions.values() for v in group]
        copies = rows.edit_copies(db, owner, project_ids)
        times = rows.project_times(db, project_ids)
        out = [
            SongRow(
                id=one.id,
                title=one.title,
                artists=_credits(credits[one.id]),
                versions=len(versions[one.id]),
                editing=any(v.project_id in copies for v in versions[one.id]),
                updated_at=max(
                    (times[v.project_id] for v in versions[one.id] if v.project_id in times),
                    default=one.created_at,
                ),
            )
            for one in songs
        ]
    out.sort(key=lambda row: row.title.casefold())
    return out


@router.get("/songs/{song_id}", response_model=SongDetail, response_model_by_alias=True)
def get_song(song_id: int) -> SongDetail:
    with _answers():
        return _song(current_user_id(), song_id)


@router.patch("/songs/{song_id}", response_model=SongDetail, response_model_by_alias=True)
def change_song(song_id: int, body: SongChange) -> SongDetail:
    """Rename a song, or give it its artists by name."""
    owner = current_user_id()
    with _answers():
        with session() as db:
            song = rows.song(db, owner, song_id)
            if body.title is not None:
                song.title = rows.clean(body.title, "A song's title")
            if body.artists is not None:
                rows.set_artists(db, owner, song_id, body.artists)
        return _song(owner, song_id)


@router.delete("/songs/{song_id}", status_code=204)
def delete_song(song_id: int) -> None:
    """Delete a song and every version it has."""
    with _answers():
        flow.delete_song(song_id, owner=current_user_id())


# -------------------------------------------------------------------- versions


@router.patch("/versions/{version_id}", response_model=SongDetail, response_model_by_alias=True)
def rename_version(version_id: int, body: VersionChange) -> SongDetail:
    owner = current_user_id()
    with _answers():
        with session() as db:
            version = rows.version(db, owner, version_id)
            version.version_name = rows.check_version_name(
                db, version.song_id, body.name, except_id=version.id
            )
            song_id = version.song_id
        return _song(owner, song_id)


@router.delete("/versions/{version_id}", status_code=204)
def delete_version(version_id: int) -> None:
    """Delete a version: its project, its history, and the audio no other project uses."""
    with _answers():
        flow.delete_version(version_id, owner=current_user_id())


@router.get(
    "/versions/{version_id}/history", response_model=list[Earlier], response_model_by_alias=True
)
def version_history(version_id: int) -> list[Earlier]:
    """The earlier states of a version, the newest first."""
    with _answers():
        with session() as db:
            project_id = rows.version(db, current_user_id(), version_id).project_id
        return [
            Earlier(number=one.number, saved_at=one.saved_at, reason=one.reason)
            for one in flow.history(project_id)
        ]


@router.post(
    "/versions/{version_id}/history/{number}/restore",
    response_model=SongDetail,
    response_model_by_alias=True,
)
def restore_version(version_id: int, number: int) -> SongDetail:
    """Make an earlier state the version again; the state it replaces goes to the history."""
    owner = current_user_id()
    with _answers():
        with session() as db:
            version = rows.version(db, owner, version_id)
            project_id, song_id = version.project_id, version.song_id
        flow.restore(project_id, number)
        return _song(owner, song_id)


# --------------------------------------------------------------------- artists


@router.get("/artists", response_model=list[ArtistRow], response_model_by_alias=True)
def list_artists() -> list[ArtistRow]:
    """The user's artists, by their default name, with every name they have."""
    owner = current_user_id()
    with session() as db:
        artists = list(
            db.scalars(select(Artist).where(Artist.scope == "private", Artist.owner_id == owner))
        )
        ids = [one.id for one in artists]
        names: dict[int, list[NameRow]] = {artist_id: [] for artist_id in ids}
        for one in db.scalars(
            select(ArtistName)
            .where(ArtistName.artist_id.in_(ids))
            .order_by(ArtistName.is_default.desc(), ArtistName.name)
        ):
            names[one.artist_id].append(
                NameRow(id=one.id, name=one.name, is_default=one.is_default)
            )
        counts: dict[int, set[int]] = {artist_id: set() for artist_id in ids}
        for artist_id, song_id in db.execute(
            select(ArtistName.artist_id, SongArtist.song_id)
            .join(SongArtist, SongArtist.artist_name_id == ArtistName.id)
            .where(ArtistName.artist_id.in_(ids))
        ):
            counts[artist_id].add(song_id)
    out = [
        ArtistRow(
            id=artist_id,
            name=next((one.name for one in names[artist_id] if one.is_default), ""),
            names=names[artist_id],
            songs=len(counts[artist_id]),
        )
        for artist_id in ids
        if names[artist_id]
    ]
    out.sort(key=lambda row: row.name.casefold())
    return out


@router.get("/artists/{artist_id}", response_model=ArtistDetail, response_model_by_alias=True)
def get_artist(artist_id: int) -> ArtistDetail:
    with _answers():
        return _artist(current_user_id(), artist_id)


@router.post(
    "/artists/{artist_id}/names", response_model=ArtistDetail, response_model_by_alias=True
)
def add_name(artist_id: int, body: NameIn) -> ArtistDetail:
    """Another name of the artist ("Jackson Five" for "The Jackson 5")."""
    owner = current_user_id()
    with _answers():
        with session() as db:
            rows.add_name(db, owner, artist_id, body.name)
        return _artist(owner, artist_id)


@router.patch(
    "/artists/{artist_id}/names/{name_id}",
    response_model=ArtistDetail,
    response_model_by_alias=True,
)
def change_name(artist_id: int, name_id: int, body: NameChange) -> ArtistDetail:
    """Rename one name of the artist, or make it the default."""
    owner = current_user_id()
    with _answers():
        with session() as db:
            rows.change_name(
                db, owner, artist_id, name_id, name=body.name, make_default=body.is_default
            )
        return _artist(owner, artist_id)


@router.delete(
    "/artists/{artist_id}/names/{name_id}",
    response_model=ArtistDetail,
    response_model_by_alias=True,
)
def remove_name(artist_id: int, name_id: int) -> ArtistDetail:
    """Remove a name that is not the default: its songs use the default name instead."""
    owner = current_user_id()
    with _answers():
        with session() as db:
            rows.remove_name(db, owner, artist_id, name_id)
        return _artist(owner, artist_id)


@router.post(
    "/artists/{artist_id}/merge", response_model=ArtistDetail, response_model_by_alias=True
)
def merge_artists(artist_id: int, body: MergeIn) -> ArtistDetail:
    """Two artists become one: every name of this artist becomes a name of ``into``."""
    owner = current_user_id()
    with _answers():
        with session() as db:
            rows.merge(db, owner, artist_id, body.into)
        return _artist(owner, body.into)


@router.delete("/artists/{artist_id}", status_code=204)
def delete_artist(artist_id: int) -> None:
    """Delete an artist that has no song."""
    with _answers():
        with session() as db:
            rows.delete_artist(db, current_user_id(), artist_id)
