"""Sharing a Private Library (implementation 02, Phase 14, plan section 15.4).

The app context: "any private library cannot be viewed by other users, but of course you can share
your private library between users, so that will be allowed in your shared library tab". The owner
shares their **whole** Private Library, read only, with the users they choose
(``library_shares``). The other user sees it under **My library → Shared**: they play its versions,
copy passages from them (a read, Phase 8), and add its songs to their own library, as from the
Public Library.

The rights check of every project route already lets a user read a library project shared with
them (:mod:`aitu_backend.auth.rights`); this module lists what is shared and makes the copies.

**Add to my library** from a shared song copies the chosen versions into the reader's Private
Library (no audio bytes, P-3), named ``<version> (<owner>)``, under the reader's own song: the one
that stands for the same public song when the shared song has one, else the reader's song of the
same title and first artist, or a new one with the same artists by name. A version added before
is not added again (its copy keeps ``origin.sharedVersion``).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session as DbSession

from aitu_backend.db.database import session
from aitu_backend.db.models import LibraryShare, PrivateVersion, Song, User
from aitu_backend.library import pull, rows
from aitu_backend.storage import bundle, locate

__all__ = [
    "Person",
    "SharedSong",
    "people",
    "pull_song",
    "set_shared",
    "shared_by_me",
    "shared_song",
    "shared_with_me",
    "songs_of",
]


@dataclass
class Person:
    id: int
    username: str
    #: For a library shared with the user: how many songs it has.
    songs: int = 0


def people(me: int) -> list[Person]:
    """The other users who can be chosen to share with: enabled, by name."""
    with session() as db:
        found = db.scalars(
            select(User).where(User.id != me, User.disabled.is_(False)).order_by(User.username)
        )
        return [Person(id=one.id, username=one.username) for one in found]


def shared_by_me(me: int) -> list[int]:
    with session() as db:
        return list(
            db.scalars(select(LibraryShare.shared_with_id).where(LibraryShare.owner_id == me))
        )


def set_shared(me: int, user_id: int, shared: bool) -> None:
    """Share the whole library with a user, or stop sharing it."""
    if user_id == me:
        raise ValueError("Your library is already yours")
    with session() as db:
        other = db.get(User, user_id)
        if other is None or other.disabled:
            raise rows.NotFound(f"No user with id {user_id}")
        found = db.get(LibraryShare, (me, user_id))
        if shared and found is None:
            db.add(
                LibraryShare(
                    owner_id=me, shared_with_id=user_id, created_at=datetime.now(timezone.utc)
                )
            )
        elif not shared:
            db.execute(
                delete(LibraryShare).where(
                    LibraryShare.owner_id == me, LibraryShare.shared_with_id == user_id
                )
            )


def _song_count(db: DbSession, owner: int) -> int:
    return int(
        db.scalar(select(func.count()).where(Song.scope == "private", Song.owner_id == owner)) or 0
    )


def shared_with_me(me: int) -> list[Person]:
    """The users who share their library with me, by name."""
    with session() as db:
        found = db.execute(
            select(User.id, User.username)
            .join(LibraryShare, LibraryShare.owner_id == User.id)
            .where(LibraryShare.shared_with_id == me, User.disabled.is_(False))
            .order_by(User.username)
        ).all()
        return [
            Person(id=owner, username=name, songs=_song_count(db, owner)) for owner, name in found
        ]


def _owner_shares(db: DbSession, owner: int, me: int) -> str:
    """The owner's username, when they share their library with me; else not found."""
    if db.get(LibraryShare, (owner, me)) is None:
        raise rows.NotFound("This library is not shared with you")
    user = db.get(User, owner)
    if user is None or user.disabled:
        raise rows.NotFound("This library is not shared with you")
    return user.username


@dataclass
class SharedRow:
    id: int
    title: str
    artists: list[str]
    versions: int


def songs_of(me: int, owner: int) -> tuple[str, list[SharedRow]]:
    """The songs of a library shared with me, by title: ``(owner's username, songs)``."""
    with session() as db:
        name = _owner_shares(db, owner, me)
        songs = list(
            db.scalars(select(Song).where(Song.scope == "private", Song.owner_id == owner))
        )
        ids = [one.id for one in songs]
        credits = rows.credits_of(db, ids)
        versions = rows.versions_of(db, ids)
        out = [
            SharedRow(
                id=one.id,
                title=one.title,
                artists=[c.name for c in credits[one.id]],
                versions=len(versions[one.id]),
            )
            for one in songs
        ]
    out.sort(key=lambda row: row.title.casefold())
    return name, out


@dataclass
class SharedVersion:
    id: int
    name: str
    project_id: str
    parts: list[str]
    #: My copy of it, if I added it to my library.
    in_library: str | None


@dataclass
class SharedSong:
    id: int
    title: str
    artists: list[str]
    owner_id: int
    owner: str
    versions: list[SharedVersion]
    #: My own song it is in, if I added a version of it.
    in_library: int | None


def _shared_song_row(db: DbSession, me: int, song_id: int) -> tuple[Song, str]:
    song = db.get(Song, song_id)
    if song is None or song.scope != "private" or song.owner_id is None:
        raise rows.NotFound(f"No song with id {song_id}")
    return song, _owner_shares(db, song.owner_id, me)


def _my_copies(db: DbSession, me: int, project_ids: list[str]) -> dict[str, tuple[str, int]]:
    """``shared project -> (my copy, my song)`` for the versions I added before."""
    wanted = set(project_ids)
    found: dict[str, tuple[str, int]] = {}
    for version in db.scalars(
        select(PrivateVersion)
        .join(Song, Song.id == PrivateVersion.song_id)
        .where(Song.scope == "private", Song.owner_id == me)
    ):
        try:
            origin = bundle.read_project(version.project_id).origin or {}
        except (locate.NotFound, OSError, ValueError):
            continue
        source = origin.get("sharedVersion")
        if source in wanted:
            found[source] = (version.project_id, version.song_id)
    return found


def shared_song(me: int, song_id: int) -> SharedSong:
    with session() as db:
        song, owner = _shared_song_row(db, me, song_id)
        credits = rows.credits_of(db, [song.id])[song.id]
        versions = rows.versions_of(db, [song.id])[song.id]
        mine = _my_copies(db, me, [one.project_id for one in versions])
        return SharedSong(
            id=song.id,
            title=song.title,
            artists=[c.name for c in credits],
            owner_id=song.owner_id or 0,
            owner=owner,
            versions=[
                SharedVersion(
                    id=one.id,
                    name=one.version_name,
                    project_id=one.project_id,
                    parts=bundle.part_ids_of(one.project_id),
                    in_library=mine.get(one.project_id, (None, 0))[0],
                )
                for one in versions
            ],
            in_library=next((pair[1] for pair in mine.values()), None),
        )


def _target_song(db: DbSession, me: int, source: Song) -> Song:
    """My song for a shared song: by its public song, or by title and first artist, or new."""
    if source.public_id is not None:
        return pull.private_song_for(db, me, source.public_id)
    names = [c.name for c in rows.credits_of(db, [source.id])[source.id]]
    found = rows.find_song(db, me, source.title, names[0] if names else None)
    if found is not None:
        return found
    made = rows.make_song(db, me, source.title, None)
    rows.set_artists(db, me, made.id, names)
    return made


@dataclass
class Added:
    song_id: int
    versions: int
    already: int


def pull_song(me: int, song_id: int, version_ids: list[int] | None = None) -> Added:
    """Add a shared song to my library with the chosen versions (all of them when none is named)."""
    with session() as db:
        song, owner = _shared_song_row(db, me, song_id)
        versions = rows.versions_of(db, [song.id])[song.id]
        if version_ids:
            chosen = [one for one in versions if one.id in set(version_ids)]
            if len(chosen) != len(set(version_ids)):
                raise rows.NotFound("That is not a version of this song")
        else:
            chosen = versions
        if not chosen:
            raise rows.NotFound("This song has no version")
        already = _my_copies(db, me, [one.project_id for one in chosen])
        wanted = [
            (one.project_id, one.version_name) for one in chosen if one.project_id not in already
        ]
        title = song.title

    made: list[tuple[str, str]] = []
    for project_id, name in wanted:
        copy = bundle.duplicate_project(project_id, owner_id=me, layer="private", title=title)
        bundle.write_project(
            copy.model_copy(update={"origin": {"sharedVersion": project_id}}), touch=False
        )
        made.append((copy.id, name))

    with session() as db:
        source = db.get(Song, song_id)
        assert source is not None
        target = _target_song(db, me, source)
        for copy_id, name in made:
            db.add(
                PrivateVersion(
                    song_id=target.id,
                    version_name=pull.free_name(db, target.id, f"{name} ({owner})"),
                    project_id=copy_id,
                )
            )
            db.flush()
        return Added(song_id=target.id, versions=len(made), already=len(already))
