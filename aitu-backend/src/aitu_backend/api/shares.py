"""``/shares`` and ``/shared``: sharing a Private Library (implementation 02, Phase 14, plan
section 15.4).

``/shares`` is the owner's side: who they share their whole library with (read only). ``/shared``
is the reader's side: the libraries shared with them, their songs, one song with its versions, and
**Add to my library**. The rules are in :mod:`aitu_backend.library.shares`. A library that is not
shared with the user answers **404**, as another user's library always does (section 9.3).
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from aitu_backend.db.users import current_user_id
from aitu_backend.library import rows, shares

router = APIRouter(tags=["shares"])


class _Camel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class PersonOut(_Camel):
    id: int
    username: str
    songs: int = 0


class SharesOut(_Camel):
    #: The other users, to choose from.
    people: list[PersonOut]
    #: The ones the user shares their library with.
    shared_with: list[int] = Field(..., alias="sharedWith")
    #: The users who share their library with this user.
    shared_with_me: list[PersonOut] = Field(..., alias="sharedWithMe")


class SharedRowOut(_Camel):
    id: int
    title: str
    artists: list[str]
    versions: int


class SharedLibraryOut(_Camel):
    owner: str
    songs: list[SharedRowOut]


class SharedVersionOut(_Camel):
    id: int
    name: str
    project_id: str = Field(..., alias="projectId")
    parts: list[str]
    in_library: str | None = Field(None, alias="inLibrary")


class SharedSongOut(_Camel):
    id: int
    title: str
    artists: list[str]
    owner_id: int = Field(..., alias="ownerId")
    owner: str
    versions: list[SharedVersionOut]
    in_library: int | None = Field(None, alias="inLibrary")


class PullIn(_Camel):
    #: The versions to add; every version of the song when empty.
    versions: list[int] = Field(default_factory=list)


class AddedOut(_Camel):
    song_id: int = Field(..., alias="songId")
    versions: int
    already: int


@contextmanager
def _answers() -> Iterator[None]:
    try:
        yield
    except rows.NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _shares_out(me: int) -> SharesOut:
    return SharesOut(
        people=[PersonOut(id=one.id, username=one.username) for one in shares.people(me)],
        shared_with=shares.shared_by_me(me),
        shared_with_me=[
            PersonOut(id=one.id, username=one.username, songs=one.songs)
            for one in shares.shared_with_me(me)
        ],
    )


@router.get("/shares", response_model=SharesOut, response_model_by_alias=True)
def list_shares() -> SharesOut:
    return _shares_out(current_user_id())


@router.put("/shares/{user_id}", response_model=SharesOut, response_model_by_alias=True)
def share(user_id: int) -> SharesOut:
    """Share the whole Private Library with a user, read only."""
    me = current_user_id()
    with _answers():
        shares.set_shared(me, user_id, True)
    return _shares_out(me)


@router.delete("/shares/{user_id}", response_model=SharesOut, response_model_by_alias=True)
def stop_sharing(user_id: int) -> SharesOut:
    me = current_user_id()
    with _answers():
        shares.set_shared(me, user_id, False)
    return _shares_out(me)


@router.get("/shared/{owner_id}/songs", response_model=SharedLibraryOut)
def shared_songs(owner_id: int) -> SharedLibraryOut:
    """The songs of a library shared with the user, by title."""
    with _answers():
        owner, found = shares.songs_of(current_user_id(), owner_id)
    return SharedLibraryOut(
        owner=owner,
        songs=[
            SharedRowOut(id=one.id, title=one.title, artists=one.artists, versions=one.versions)
            for one in found
        ],
    )


@router.get("/shared/songs/{song_id}", response_model=SharedSongOut, response_model_by_alias=True)
def shared_song(song_id: int) -> SharedSongOut:
    with _answers():
        found = shares.shared_song(current_user_id(), song_id)
    return SharedSongOut(
        id=found.id,
        title=found.title,
        artists=found.artists,
        owner_id=found.owner_id,
        owner=found.owner,
        versions=[
            SharedVersionOut(
                id=one.id,
                name=one.name,
                project_id=one.project_id,
                parts=one.parts,
                in_library=one.in_library,
            )
            for one in found.versions
        ],
        in_library=found.in_library,
    )


@router.post(
    "/shared/songs/{song_id}/pull",
    response_model=AddedOut,
    response_model_by_alias=True,
    status_code=201,
)
def pull_shared(song_id: int, body: PullIn) -> AddedOut:
    """**Add to my library**: the chosen versions of a shared song, copied into the user's own."""
    with _answers():
        found = shares.pull_song(current_user_id(), song_id, body.versions or None)
    return AddedOut(song_id=found.song_id, versions=found.versions, already=found.already)
