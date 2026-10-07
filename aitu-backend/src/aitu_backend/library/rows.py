"""The Private Library's records: artists, artist names, songs and versions (implementation 02, plan
sections 8.6, 15.1 and 15.2).

A user's private music library is their own ontology: they name artists and songs as they like.
These are rows of the ``private`` scope, each with ``owner_id``, and every function here takes the
owner and never reads another user's rows (section 9.3).

* An **artist** has one or more **artist names**; one is the default. "The Jackson 5" and "Jackson
  Five" are two names of one artist, and two artists can be merged into one (the app context asks
  to let names converge on one artist id).
* A **song** points at artist names (``song_artists``), each of which points at its artist.
* A **version** of a private song (``private_versions``) has a free name ("original", "easy",
  "acoustic") and points at one project of the Private Library. A song's version names are unique,
  ignoring case.

Names are compared ignoring case and repeated spaces, so "aitana" finds "Aitana".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session as DbSession

from aitu_backend.db.models import (
    Artist,
    ArtistName,
    PrivateVersion,
    Project,
    Song,
    SongArtist,
)

__all__ = [
    "Conflict",
    "NotFound",
    "clean",
    "edit_copies",
    "find_or_make_name",
    "find_song",
    "same",
]

TITLE_LIMIT = 300
VERSION_LIMIT = 60


class NotFound(LookupError):
    """No row of this user with this id: the routes answer 404."""


class Conflict(ValueError):
    """The change would break a rule of the library (a version name taken): the routes answer 409."""


def clean(text: str | None, what: str, limit: int = TITLE_LIMIT) -> str:
    """``text`` with its spaces collapsed; refused when empty or longer than ``limit``."""
    cleaned = " ".join((text or "").split())
    if not cleaned:
        raise ValueError(f"{what} cannot be empty")
    if len(cleaned) > limit:
        raise ValueError(f"{what} is longer than {limit} characters")
    return cleaned


def same(text: str) -> str:
    """The form two names are compared in."""
    return " ".join(text.split()).casefold()


# --------------------------------------------------------------------- artists


def _name_row(db: DbSession, owner: int, name: str) -> ArtistName | None:
    """The owner's artist name equal to ``name`` (ignoring case and spaces), the default first.

    Compared here, not in SQL: SQLite's ``lower`` folds only ASCII letters, so "Él" would not
    find "él"."""
    wanted = same(name)
    rows = db.scalars(
        select(ArtistName)
        .join(Artist, ArtistName.artist_id == Artist.id)
        .where(Artist.scope == "private", Artist.owner_id == owner)
        .order_by(ArtistName.is_default.desc(), ArtistName.id)
    )
    return next((row for row in rows if same(row.name) == wanted), None)


def find_or_make_name(db: DbSession, owner: int, name: str) -> ArtistName:
    """The owner's artist name ``name``, made with a new artist when no artist has it."""
    name = clean(name, "An artist's name")
    found = _name_row(db, owner, name)
    if found is not None:
        return found
    artist = Artist(scope="private", owner_id=owner)
    db.add(artist)
    db.flush()
    row = ArtistName(artist_id=artist.id, name=name, is_default=True)
    db.add(row)
    db.flush()
    return row


def artist(db: DbSession, owner: int, artist_id: int) -> Artist:
    row = db.get(Artist, artist_id)
    if row is None or row.scope != "private" or row.owner_id != owner:
        raise NotFound(f"No artist with id {artist_id}")
    return row


def names_of(db: DbSession, artist_id: int) -> list[ArtistName]:
    return list(
        db.scalars(
            select(ArtistName)
            .where(ArtistName.artist_id == artist_id)
            .order_by(ArtistName.is_default.desc(), ArtistName.name)
        )
    )


def song_ids_of_artist(db: DbSession, artist_id: int) -> list[int]:
    return list(
        db.scalars(
            select(SongArtist.song_id)
            .join(ArtistName, SongArtist.artist_name_id == ArtistName.id)
            .where(ArtistName.artist_id == artist_id)
            .distinct()
        )
    )


def add_name(db: DbSession, owner: int, artist_id: int, name: str) -> ArtistName:
    artist(db, owner, artist_id)
    name = clean(name, "An artist's name")
    found = _name_row(db, owner, name)
    if found is not None:
        if found.artist_id == artist_id:
            return found
        raise Conflict(f"“{found.name}” is a name of another artist: merge the two artists instead")
    row = ArtistName(artist_id=artist_id, name=name, is_default=False)
    db.add(row)
    db.flush()
    return row


def _name_of(db: DbSession, owner: int, artist_id: int, name_id: int) -> ArtistName:
    artist(db, owner, artist_id)
    row = db.get(ArtistName, name_id)
    if row is None or row.artist_id != artist_id:
        raise NotFound(f"No artist name with id {name_id}")
    return row


def change_name(
    db: DbSession,
    owner: int,
    artist_id: int,
    name_id: int,
    *,
    name: str | None = None,
    make_default: bool = False,
) -> None:
    row = _name_of(db, owner, artist_id, name_id)
    if name is not None:
        name = clean(name, "An artist's name")
        found = _name_row(db, owner, name)
        if found is not None and found.id != row.id:
            raise Conflict(f"An artist already has the name “{found.name}”")
        row.name = name
    if make_default:
        db.execute(
            update(ArtistName).where(ArtistName.artist_id == artist_id).values(is_default=False)
        )
        row.is_default = True


def remove_name(db: DbSession, owner: int, artist_id: int, name_id: int) -> None:
    """Remove a name that is not the default; songs that used it now use the default name."""
    row = _name_of(db, owner, artist_id, name_id)
    if row.is_default:
        raise Conflict("The default name cannot be removed: make another name the default first")
    default = next(one for one in names_of(db, artist_id) if one.is_default)
    for link in db.scalars(select(SongArtist).where(SongArtist.artist_name_id == row.id)).all():
        taken = db.get(SongArtist, (link.song_id, default.id))
        if taken is None:
            db.add(
                SongArtist(song_id=link.song_id, artist_name_id=default.id, position=link.position)
            )
        db.delete(link)
    db.flush()
    db.delete(row)


def merge(db: DbSession, owner: int, artist_id: int, into_id: int) -> None:
    """Every name of ``artist_id`` becomes a name of ``into_id``, which keeps its default name."""
    if artist_id == into_id:
        raise Conflict("An artist cannot be merged with itself")
    source = artist(db, owner, artist_id)
    artist(db, owner, into_id)
    db.execute(
        update(ArtistName)
        .where(ArtistName.artist_id == artist_id)
        .values(artist_id=into_id, is_default=False)
    )
    db.flush()
    db.delete(source)


def delete_artist(db: DbSession, owner: int, artist_id: int) -> None:
    row = artist(db, owner, artist_id)
    if song_ids_of_artist(db, artist_id):
        raise Conflict("This artist still has songs")
    db.execute(delete(ArtistName).where(ArtistName.artist_id == artist_id))
    db.delete(row)


# ----------------------------------------------------------------------- songs


def song(db: DbSession, owner: int, song_id: int) -> Song:
    row = db.get(Song, song_id)
    if row is None or row.scope != "private" or row.owner_id != owner:
        raise NotFound(f"No song with id {song_id}")
    return row


@dataclass(frozen=True)
class Credit:
    """One artist of a song, by the name the song uses."""

    artist_id: int
    name_id: int
    name: str


def credits_of(db: DbSession, song_ids: list[int]) -> dict[int, list[Credit]]:
    out: dict[int, list[Credit]] = {song_id: [] for song_id in song_ids}
    if not song_ids:
        return out
    rows = db.execute(
        select(SongArtist.song_id, ArtistName.artist_id, ArtistName.id, ArtistName.name)
        .join(ArtistName, SongArtist.artist_name_id == ArtistName.id)
        .where(SongArtist.song_id.in_(song_ids))
        .order_by(SongArtist.song_id, SongArtist.position, ArtistName.name)
    ).all()
    for song_id, artist_id, name_id, name in rows:
        out[song_id].append(Credit(artist_id=artist_id, name_id=name_id, name=name))
    return out


def find_song(db: DbSession, owner: int, title: str, artist_name: str | None) -> Song | None:
    """The owner's song with this title and this artist (or with no artist), if there is one."""
    wanted_title = same(title)
    candidates = [
        one
        for one in db.scalars(select(Song).where(Song.scope == "private", Song.owner_id == owner))
        if same(one.title) == wanted_title
    ]
    if not candidates:
        return None
    credits = credits_of(db, [one.id for one in candidates])
    wanted = None
    if artist_name:
        name = _name_row(db, owner, artist_name)
        if name is None:
            return None
        wanted = name.artist_id
    for one in candidates:
        artists = {credit.artist_id for credit in credits[one.id]}
        if (wanted is None and not artists) or (wanted is not None and wanted in artists):
            return one
    return None


def make_song(db: DbSession, owner: int, title: str, artist_name: str | None) -> Song:
    row = Song(scope="private", owner_id=owner, title=clean(title, "A song's title"))
    db.add(row)
    db.flush()
    if artist_name and artist_name.strip():
        name = find_or_make_name(db, owner, artist_name)
        db.add(SongArtist(song_id=row.id, artist_name_id=name.id, position=0))
        db.flush()
    return row


def set_artists(db: DbSession, owner: int, song_id: int, names: list[str]) -> None:
    """The song's artists, by name, in order: names not known yet make new artists."""
    song(db, owner, song_id)
    db.execute(delete(SongArtist).where(SongArtist.song_id == song_id))
    seen: set[int] = set()
    for position, name in enumerate(names):
        if not name.strip():
            continue
        row = find_or_make_name(db, owner, name)
        if row.id in seen:
            continue
        seen.add(row.id)
        db.add(SongArtist(song_id=song_id, artist_name_id=row.id, position=position))
    db.flush()


# -------------------------------------------------------------------- versions


def versions_of(db: DbSession, song_ids: list[int]) -> dict[int, list[PrivateVersion]]:
    out: dict[int, list[PrivateVersion]] = {song_id: [] for song_id in song_ids}
    if not song_ids:
        return out
    for row in db.scalars(
        select(PrivateVersion)
        .where(PrivateVersion.song_id.in_(song_ids))
        .order_by(PrivateVersion.created_at, PrivateVersion.id)
    ):
        out[row.song_id].append(row)
    return out


def version(db: DbSession, owner: int, version_id: int) -> PrivateVersion:
    row = db.get(PrivateVersion, version_id)
    if row is None:
        raise NotFound(f"No version with id {version_id}")
    song(db, owner, row.song_id)
    return row


def version_of_project(db: DbSession, project_id: str) -> PrivateVersion | None:
    return db.scalar(select(PrivateVersion).where(PrivateVersion.project_id == project_id))


def check_version_name(
    db: DbSession, song_id: int, name: str, *, except_id: int | None = None
) -> str:
    """``name`` cleaned, refused when another version of the song has it."""
    name = clean(name, "A version name", VERSION_LIMIT)
    for row in db.scalars(select(PrivateVersion).where(PrivateVersion.song_id == song_id)):
        if row.id != except_id and same(row.version_name) == same(name):
            raise Conflict(f"This song already has a version named “{row.version_name}”")
    return name


def edit_copies(db: DbSession, owner: int, project_ids: list[str]) -> dict[str, str]:
    """``library project id -> the vault project that edits it`` (section 10.6)."""
    if not project_ids:
        return {}
    rows = db.execute(
        select(Project.based_on, Project.id).where(
            Project.owner_id == owner,
            Project.layer == "vault",
            Project.based_on.in_(project_ids),
        )
    ).all()
    return {based_on: copy for based_on, copy in rows if based_on is not None}


def project_times(db: DbSession, project_ids: list[str]) -> dict[str, datetime]:
    if not project_ids:
        return {}
    rows = db.execute(select(Project.id, Project.updated_at).where(Project.id.in_(project_ids)))
    return {project_id: moment for project_id, moment in rows}


@dataclass(frozen=True)
class Link:
    """The song and the version a library project is, for the pages that show a project."""

    song_id: int
    song_title: str
    artists: list[str]
    version_id: int
    version_name: str


def links_of(db: DbSession, project_ids: list[str]) -> dict[str, Link]:
    """``project id -> its song and version``, for the projects that are a version of a song."""
    if not project_ids:
        return {}
    found = db.execute(
        select(PrivateVersion, Song)
        .join(Song, PrivateVersion.song_id == Song.id)
        .where(PrivateVersion.project_id.in_(project_ids))
    ).all()
    credits = credits_of(db, [song_row.id for _, song_row in found])
    return {
        version_row.project_id: Link(
            song_id=song_row.id,
            song_title=song_row.title,
            artists=[credit.name for credit in credits[song_row.id]],
            version_id=version_row.id,
            version_name=version_row.version_name,
        )
        for version_row, song_row in found
    }
