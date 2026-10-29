"""**Add to my library**: a public song, an artist or a playlist pulled into the user's Private
Library (implementation 02, Phase 13, plan section 15.1).

The app context: "A given user can pull from the public library any song or any playlist that it
wants, or maybe it can pull all the songs from a given artist." A pull **copies**:

* the entities into private rows that keep the public id (``public_id``): the song (title, year)
  and its artists with every name they have. A private row that already stands for the public one
  is used again: the one with that ``public_id``, or else the user's own song of the same title
  and artist, or artist of the same name (it gets the link). After the pull there is no sync: the
  private rows are the user's own (section 15.1);
* the public song's tags (its film, its TV show) as the private song's metadata (implementation
  04-3, Phase 1); the public rows do not change;
* the chosen version projects into ``users/<id>/library/`` as versions of the private song, each
  pointing back at its public project (``projects.public_source_id``). No audio bytes are copied
  (P-3). A version already pulled is not pulled twice.

**Only songs with a version are pulled** (the user, 2026-10-16, Phase 13): a song in My library has
its piano sheet, so a public song with no version yet cannot be added. An artist adds its songs
that have a version; a playlist, its songs with the version each item names.

The name of a pulled version is the public one: ``hard`` for a fixed version, ``easy (anna)`` for
anna's user version, with `` 2`` added when the song already has that name.

The same links serve **Save to library** with a public song or artist chosen (Phase 13): the
private song or artist is found or made the same way (:func:`find_private_song`,
:func:`private_song_for`, :func:`private_artist_for`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from aitu_backend.db.database import session
from aitu_backend.db.models import (
    Artist,
    ArtistName,
    Playlist,
    PlaylistItem,
    PrivateVersion,
    Project,
    Song,
    SongArtist,
)
from aitu_backend.library import flow, metadata, public, rows
from aitu_backend.storage import bundle

__all__ = [
    "Pulled",
    "find_private_song",
    "free_name",
    "private_artist_for",
    "private_song_for",
    "pulled_copies",
    "pull_artist",
    "pull_playlist",
    "pull_song",
]


# ------------------------------------------------------------- private entities


def _private_artist(db: DbSession, owner: int, public_artist_id: int) -> Artist | None:
    return db.scalar(
        select(Artist).where(
            Artist.scope == "private",
            Artist.owner_id == owner,
            Artist.public_id == public_artist_id,
        )
    )


def private_artist_for(db: DbSession, owner: int, public_artist_id: int) -> ArtistName:
    """The owner's artist for a public artist, as its default name: the one linked to it, the
    owner's artist of the same name (linked now), or a new one with every public name."""
    public.public_artist(db, public_artist_id)
    names = rows.names_of(db, public_artist_id)
    found = _private_artist(db, owner, public_artist_id)
    if found is None and names:
        default = next((one for one in names if one.is_default), names[0])
        same = rows.find_name(db, owner, default.name)
        if same is not None:
            found = db.get(Artist, same.artist_id)
            if found is not None and found.public_id is None:
                found.public_id = public_artist_id
    if found is None:
        found = Artist(scope="private", owner_id=owner, public_id=public_artist_id)
        db.add(found)
        db.flush()
        for one in names:
            if rows.find_name(db, owner, one.name) is None:
                db.add(ArtistName(artist_id=found.id, name=one.name, is_default=one.is_default))
        db.flush()
    own = rows.names_of(db, found.id)
    return next((one for one in own if one.is_default), own[0])


def find_private_song(db: DbSession, owner: int, public_song_id: int) -> Song | None:
    """The owner's song for a public song, if there is one: linked to it, or of the same title
    and first artist (not linked yet)."""
    song = public.public_song(db, public_song_id)
    linked = db.scalar(
        select(Song).where(
            Song.scope == "private", Song.owner_id == owner, Song.public_id == public_song_id
        )
    )
    if linked is not None:
        return linked
    credits = rows.credits_of(db, [song.id])[song.id]
    same = rows.find_song(db, owner, song.title, credits[0].name if credits else None)
    return same if same is not None and same.public_id is None else None


def private_song_for(db: DbSession, owner: int, public_song_id: int) -> Song:
    """The owner's song for a public song, made with its artists when there is none. A song made
    or linked now gets the public song's tags as its metadata (implementation 04-3, Phase 1); a song
    already linked keeps the metadata the user gave it."""
    found = find_private_song(db, owner, public_song_id)
    if found is not None:
        if found.public_id != public_song_id:
            found.public_id = public_song_id
            metadata.copy_public_tags(db, owner, public_song_id, found.id)
        return found
    song = public.public_song(db, public_song_id)
    made = Song(
        scope="private",
        owner_id=owner,
        title=song.title,
        year=song.year,
        public_id=public_song_id,
    )
    db.add(made)
    db.flush()
    seen: set[int] = set()
    for position, credit in enumerate(rows.credits_of(db, [song.id])[song.id]):
        name = private_artist_for(db, owner, credit.artist_id)
        if name.id not in seen:
            seen.add(name.id)
            db.add(SongArtist(song_id=made.id, artist_name_id=name.id, position=position))
    db.flush()
    metadata.copy_public_tags(db, owner, public_song_id, made.id)
    return made


# ------------------------------------------------------------------ versions


@dataclass(frozen=True)
class _Choice:
    project_id: str
    #: The private version name it takes.
    name: str


def _choices(db: DbSession, song_id: int, owner: int) -> tuple[list[_Choice], str | None]:
    """Every ready public version of a song as a private name, and the default one's project."""
    fixed, others = public.versions_of(db, song_id, owner)
    song = public.public_song(db, song_id)
    found = [_Choice(one.project_id, one.name) for one in fixed if one.ready] + [
        _Choice(one.project_id, f"{one.name} ({group.username})")
        for group in others
        for one in group.versions
        if one.ready
    ]
    ready_fixed = [one for one in fixed if one.ready]
    default = next(
        (one.project_id for one in ready_fixed if one.name == song.default_version),
        ready_fixed[0].project_id if ready_fixed else None,
    )
    if default is None:
        best = sorted(
            (one for group in others for one in group.versions if one.ready),
            key=lambda one: -one.likes,
        )
        default = best[0].project_id if best else None
    return found, default


def free_name(db: DbSession, song_id: int, name: str) -> str:
    taken = {
        rows.same(one.version_name)
        for one in db.scalars(select(PrivateVersion).where(PrivateVersion.song_id == song_id))
    }
    candidate, number = name, 1
    while rows.same(candidate) in taken:
        number += 1
        candidate = f"{name} {number}"
    return candidate


def pulled_copies(db: DbSession, owner: int, project_ids: list[str]) -> dict[str, str]:
    """``public project -> the owner's library copy of it``."""
    if not project_ids:
        return {}
    return {
        source: copy
        for copy, source in db.execute(
            select(Project.id, Project.public_source_id).where(
                Project.owner_id == owner,
                Project.layer == "private",
                Project.public_source_id.in_(project_ids),
            )
        )
        if source is not None
    }


@dataclass
class Pulled:
    #: The private song (for a song), or the private artist (for an artist), or the private
    #: playlist (for a playlist).
    id: int
    songs: int = 0
    #: Versions copied by this pull.
    versions: int = 0
    #: Versions that were already in the library.
    already: int = 0
    #: ``public project -> private project`` for every chosen version.
    copies: dict[str, str] = field(default_factory=dict)


def pull_song(owner: int, song_id: int, project_ids: list[str] | None = None) -> Pulled:
    """Add a public song to the owner's library with the chosen versions (its default version when
    none is named). ``flow.Refused`` when the song has no version yet."""
    with session() as db:
        choices, default = _choices(db, song_id, owner)
        by_project = {one.project_id: one for one in choices}
        wanted = project_ids if project_ids else ([default] if default else [])
        if not wanted:
            raise flow.Refused("This song has no version yet")
        for one in wanted:
            if one not in by_project:
                raise rows.NotFound("That is not a version of this song")
        already = pulled_copies(db, owner, wanted)
        title = public.public_song(db, song_id).title

    made: dict[str, str] = {}
    for project_id in wanted:
        if project_id in already:
            continue
        copy = bundle.duplicate_project(project_id, owner_id=owner, layer="private", title=title)
        bundle.write_project(
            copy.model_copy(update={"origin": {"publicVersion": project_id}}), touch=False
        )
        made[project_id] = copy.id

    with session() as db:
        song = private_song_for(db, owner, song_id)
        for project_id, copy_id in made.items():
            row = db.get(Project, copy_id)
            assert row is not None
            row.public_source_id = project_id
            db.add(
                PrivateVersion(
                    song_id=song.id,
                    version_name=free_name(db, song.id, by_project[project_id].name),
                    project_id=copy_id,
                )
            )
            db.flush()
        return Pulled(
            id=song.id,
            songs=1,
            versions=len(made),
            already=len(already),
            copies={**already, **made},
        )


def pull_artist(owner: int, artist_id: int) -> Pulled:
    """Add every song of a public artist that has a version, each with its default version."""
    with session() as db:
        public.public_artist(db, artist_id)
        song_ids = rows.song_ids_of_artist(db, artist_id)
        with_version = [one for one in song_ids if _choices(db, one, owner)[1] is not None]
        if not with_version:
            raise flow.Refused("No song of this artist has a version yet")
    total = Pulled(id=0)
    for song_id in with_version:
        pulled = pull_song(owner, song_id)
        total.songs += 1
        total.versions += pulled.versions
        total.already += pulled.already
    with session() as db:
        total.id = private_artist_for(db, owner, artist_id).artist_id
    return total


def pull_playlist(owner: int, playlist_id: int) -> Pulled:
    """A private songs playlist made from a public one: each song with the version its item names
    (or its default version), pulled into the library; songs with no version are left out."""
    with session() as db:
        source = public.public_playlist(db, playlist_id)
        existing = db.scalar(
            select(Playlist.id).where(
                Playlist.scope == "private",
                Playlist.owner_id == owner,
                Playlist.public_id == playlist_id,
            )
        )
        items = list(
            db.scalars(
                select(PlaylistItem)
                .where(PlaylistItem.playlist_id == playlist_id)
                .order_by(PlaylistItem.position)
            )
        )
        title = source.title
        playable = [
            one
            for one in items
            if one.song_id is not None and _choices(db, one.song_id, owner)[1] is not None
        ]
    if existing is not None:
        return Pulled(id=existing, songs=len(playable))
    if not playable:
        raise flow.Refused("No song of this playlist has a version yet")
    total = Pulled(id=0)
    made_items: list[tuple[int, str | None, int | None, int | None]] = []
    for item in playable:
        assert item.song_id is not None
        pulled = pull_song(owner, item.song_id, [item.project_id] if item.project_id else None)
        total.versions += pulled.versions
        total.already += pulled.already
        copy = next(iter(pulled.copies.values()), None)
        made_items.append((pulled.id, copy, item.from_ms, item.to_ms))
    now = datetime.now(timezone.utc)
    with session() as db:
        playlist = Playlist(
            owner_id=owner,
            scope="private",
            public_id=playlist_id,
            title=title,
            created_at=now,
            updated_at=now,
        )
        db.add(playlist)
        db.flush()
        for position, (song_id, project_id, from_ms, to_ms) in enumerate(made_items):
            db.add(
                PlaylistItem(
                    playlist_id=playlist.id,
                    position=position,
                    song_id=song_id,
                    project_id=project_id,
                    from_ms=from_ms,
                    to_ms=to_ms,
                )
            )
        total.id = playlist.id
        total.songs = len(made_items)
    return total
