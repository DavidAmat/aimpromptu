"""The Public Library's records: one song with its metadata and versions, one artist, the public
playlists, likes, and the place of a project as a public version (implementation 02, Phase 13, plan
sections 15.1 to 15.3).

The lists, the search and the sort are :mod:`aitu_backend.library.catalogue`. Pulling into the
Private Library (**Add to my library**) is :mod:`aitu_backend.library.pull`.

**Versions** (section 15.2). A public song has **fixed versions** (``song_versions``: Hard, Medium,
Easy, or a custom name the master user accepted; **Default** is a pointer to one of them, Hard
unless changed) and **Other versions** (``user_versions``: one project per user and version name,
the app context's ``user_versions/<user>/<version name>/``). Each points at a project of the public
layer (``.database/public/<projectId>/``). They arrive by an accepted request (Phase 14,
:mod:`aitu_backend.library.requests`), in two steps: :func:`copy_to_public` copies the project and
:func:`point_version` points the version at it, inside the review's one transaction.
:func:`place_version` does both, for the tests and the browser checks, always on a copy.

**Likes** (section 15.2): a user likes a public version's project once; Other versions are sorted by
likes, then by date.

Public rows have no owner (Phase 12); every signed-in user reads them (section 9.3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session as DbSession

from aitu_backend.db.database import session
from aitu_backend.db.models import (
    Album,
    AlbumArtist,
    Artist,
    ArtistName,
    ChartEntry,
    ChartSource,
    Genre,
    Like,
    Playlist,
    PlaylistItem,
    Project,
    Region,
    Song,
    SongAlbum,
    SongGenre,
    SongLyrics,
    SongRegion,
    SongRegionPopularity,
    SongTag,
    SongVersion,
    TagCategory,
    TagValue,
    User,
    UserVersion,
)
from aitu_backend.library import catalogue, flow, rows
from aitu_backend.storage import bundle, locate

__all__ = [
    "FIXED_NAMES",
    "ArtistFacts",
    "SongFacts",
    "VersionFacts",
    "artist_facts",
    "copy_to_public",
    "delete_if_unused",
    "like",
    "place_version",
    "point_version",
    "playlist_facts",
    "playlists",
    "remove_version",
    "song_facts",
    "unlike",
]

#: The fixed versions every song has a place for, in the order a page shows them (section 15.2).
FIXED_NAMES = ("hard", "medium", "easy")
#: A public version name: lowercase letters, digits and hyphens, at most 24 characters.
NAME_RULE = "lowercase letters, digits and hyphens, at most 24 characters"


def check_public_name(name: str) -> str:
    cleaned = name.strip()
    allowed = all(c.isascii() and (c.islower() or c.isdigit() or c == "-") for c in cleaned)
    if not cleaned or len(cleaned) > 24 or not allowed or not cleaned[0].isalnum():
        raise ValueError(f"A public version name is {NAME_RULE}")
    return cleaned


# ----------------------------------------------------------------------- facts


@dataclass
class VersionFacts:
    project_id: str
    #: The parts of the project, in order: the first is the uuid the step routes take.
    parts: list[str]
    #: ``hard``, ``medium``, ``easy`` or a custom fixed name; a user version's own name.
    name: str
    #: The user whose project it is.
    creator: str | None
    likes: int
    liked: bool
    created_at: datetime | None
    #: The piano sheet of every part is saved (a version always has one).
    ready: bool


@dataclass
class UserVersions:
    username: str
    versions: list[VersionFacts]


@dataclass
class Named:
    id: int
    name: str


@dataclass
class AlbumOfSong:
    id: int
    title: str
    year: int | None
    track: int | None


@dataclass
class Chart:
    name: str
    #: The region the chart counts in (``Worldwide``, ``Spain``, ``Catalan``).
    region: str | None
    #: How many places it lists; 1 is a list of number ones only.
    size: int
    best: int
    weeks: int
    first: date
    last: date
    #: ``(week, rank)``, oldest first.
    history: list[tuple[date, int]]


@dataclass
class SongFacts:
    id: int
    title: str
    year: int | None
    popularity: float
    artists: list[tuple[int, str]]
    albums: list[AlbumOfSong]
    genres: list[str]
    regions: list[Named]
    #: ``(category, value)``.
    tags: list[tuple[str, str]]
    #: ``(region name, popularity, basis)`` in each region other than worldwide (Phase 16).
    region_popularity: list[tuple[str, float, str]]
    charts: list[Chart]
    has_lyrics: bool
    #: The fixed version Default points at.
    default_version: str
    fixed: list[VersionFacts]
    others: list[UserVersions]
    #: The user's private song pulled from (or linked to) this one.
    in_library: int | None


def _usernames(db: DbSession, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    return dict(db.execute(select(User.id, User.username).where(User.id.in_(ids))).all())


def _likes(db: DbSession, project_ids: list[str], user_id: int) -> tuple[dict[str, int], set[str]]:
    if not project_ids:
        return {}, set()
    counts = dict(
        db.execute(
            select(Like.project_id, func.count())
            .where(Like.project_id.in_(project_ids))
            .group_by(Like.project_id)
        ).all()
    )
    mine = set(
        db.scalars(
            select(Like.project_id).where(Like.project_id.in_(project_ids), Like.user_id == user_id)
        )
    )
    return counts, mine


def _version(
    project_id: str,
    name: str,
    creator: str | None,
    likes: tuple[dict[str, int], set[str]],
    created_at: datetime | None,
) -> VersionFacts:
    try:
        ready = flow.sheet_ready(bundle.read_project(project_id))
        parts = bundle.part_ids_of(project_id)
    except (locate.NotFound, FileNotFoundError):
        ready, parts = False, []
    return VersionFacts(
        project_id=project_id,
        parts=parts,
        name=name,
        creator=creator,
        likes=likes[0].get(project_id, 0),
        liked=project_id in likes[1],
        created_at=created_at,
        ready=ready,
    )


def public_song(db: DbSession, song_id: int) -> Song:
    row = db.get(Song, song_id)
    if row is None or row.scope != "public":
        raise rows.NotFound(f"No public song with id {song_id}")
    return row


def versions_of(
    db: DbSession, song_id: int, user_id: int
) -> tuple[list[VersionFacts], list[UserVersions]]:
    """The fixed versions in the order of :data:`FIXED_NAMES` then custom names; the Other versions
    grouped by user, each group's versions by likes then date, the groups by their best likes."""
    fixed_rows = list(
        db.scalars(
            select(SongVersion).where(
                SongVersion.song_id == song_id, SongVersion.project_id.is_not(None)
            )
        )
    )
    user_rows = list(db.scalars(select(UserVersion).where(UserVersion.song_id == song_id)))
    project_ids = [one.project_id for one in fixed_rows if one.project_id] + [
        one.project_id for one in user_rows
    ]
    likes = _likes(db, project_ids, user_id)
    names = _usernames(
        db,
        {one.creator_id for one in fixed_rows if one.creator_id is not None}
        | {one.user_id for one in user_rows},
    )

    def order(name: str) -> tuple[int, str]:
        return (FIXED_NAMES.index(name), "") if name in FIXED_NAMES else (len(FIXED_NAMES), name)

    fixed = [
        _version(
            one.project_id or "",
            one.name,
            names.get(one.creator_id) if one.creator_id is not None else None,
            likes,
            one.updated_at,
        )
        for one in sorted(fixed_rows, key=lambda row: order(row.name))
    ]
    groups: dict[int, list[VersionFacts]] = {}
    for one in user_rows:
        groups.setdefault(one.user_id, []).append(
            _version(
                one.project_id, one.version_name, names.get(one.user_id), likes, one.created_at
            )
        )
    others = []
    for user, found in groups.items():
        found.sort(key=lambda v: (-v.likes, -(v.created_at.timestamp() if v.created_at else 0)))
        others.append(UserVersions(username=names.get(user, ""), versions=found))
    others.sort(
        key=lambda group: (-max(v.likes for v in group.versions), group.username.casefold())
    )
    return fixed, others


def _charts(db: DbSession, song_id: int) -> list[Chart]:
    found: dict[str, list[tuple[date, int]]] = {}
    region_of: dict[str, str | None] = {}
    size_of: dict[str, int] = {}
    for name, region, size, week, rank in db.execute(
        select(ChartSource.name, Region.name, ChartSource.size, ChartEntry.week, ChartEntry.rank)
        .join(ChartSource, ChartSource.id == ChartEntry.chart_source_id)
        .outerjoin(Region, Region.id == ChartSource.region_id)
        .where(ChartEntry.song_id == song_id)
        .order_by(ChartEntry.week)
    ):
        found.setdefault(name, []).append((week, rank))
        region_of[name] = region
        size_of[name] = size
    return [
        Chart(
            name=name,
            region=region_of[name],
            size=size_of[name],
            best=min(rank for _, rank in weeks),
            weeks=len(weeks),
            first=weeks[0][0],
            last=weeks[-1][0],
            history=weeks,
        )
        for name, weeks in found.items()
    ]


def linked_private_song(db: DbSession, user_id: int, public_id: int) -> int | None:
    return db.scalar(
        select(Song.id).where(
            Song.scope == "private", Song.owner_id == user_id, Song.public_id == public_id
        )
    )


def song_facts(db: DbSession, song_id: int, user_id: int) -> SongFacts:
    song = public_song(db, song_id)
    credits = rows.credits_of(db, [song_id])[song_id]
    albums = [
        AlbumOfSong(id=album.id, title=album.title, year=album.year, track=track)
        for album, track in db.execute(
            select(Album, SongAlbum.track_number)
            .join(SongAlbum, SongAlbum.album_id == Album.id)
            .where(SongAlbum.song_id == song_id)
            .order_by(Album.year, Album.id)
        )
    ]
    genres = list(
        db.scalars(
            select(Genre.name)
            .join(SongGenre, SongGenre.genre_id == Genre.id)
            .where(SongGenre.song_id == song_id)
        )
    )
    regions = [
        Named(id=region_id, name=name)
        for region_id, name in db.execute(
            select(Region.id, Region.name)
            .join(SongRegion, SongRegion.region_id == Region.id)
            .where(SongRegion.song_id == song_id)
        )
    ]
    tags = [
        (category, value)
        for category, value in db.execute(
            select(TagCategory.name, TagValue.value)
            .join(TagValue, TagValue.category_id == TagCategory.id)
            .join(SongTag, SongTag.tag_value_id == TagValue.id)
            .where(SongTag.song_id == song_id)
            .order_by(TagCategory.name, TagValue.value)
        )
    ]
    region_popularity = [
        (str(name), float(value), str(basis))
        for name, value, basis in db.execute(
            select(Region.name, SongRegionPopularity.popularity, SongRegionPopularity.basis)
            .join(Region, Region.id == SongRegionPopularity.region_id)
            .where(SongRegionPopularity.song_id == song_id)
            .order_by(Region.id)
        )
    ]
    fixed, others = versions_of(db, song_id, user_id)
    return SongFacts(
        id=song.id,
        title=song.title,
        year=song.year,
        popularity=float(song.popularity or 0.0),
        artists=[(one.artist_id, one.name) for one in credits],
        albums=albums,
        genres=genres,
        regions=regions,
        tags=tags,
        region_popularity=region_popularity,
        charts=_charts(db, song_id),
        has_lyrics=db.get(SongLyrics, song_id) is not None,
        default_version=song.default_version,
        fixed=fixed,
        others=others,
        in_library=linked_private_song(db, user_id, song_id),
    )


def lyrics(db: DbSession, song_id: int) -> str:
    public_song(db, song_id)
    found = db.get(SongLyrics, song_id)
    if found is None:
        raise rows.NotFound("This song has no lyrics")
    return found.text


# --------------------------------------------------------------------- artists


@dataclass
class AlbumOfArtist:
    id: int
    title: str
    year: int | None
    popularity: float


@dataclass
class ArtistFacts:
    id: int
    name: str
    other_names: list[str]
    songs: list[catalogue.CatalogueSong]
    albums: list[AlbumOfArtist] = field(default_factory=list)
    #: The user's private artist pulled from (or linked to) this one.
    in_library: int | None = None


def public_artist(db: DbSession, artist_id: int) -> Artist:
    row = db.get(Artist, artist_id)
    if row is None or row.scope != "public":
        raise rows.NotFound(f"No public artist with id {artist_id}")
    return row


def artist_facts(db: DbSession, artist_id: int, user_id: int) -> ArtistFacts:
    """An artist's names, songs by popularity and albums by popularity (the app context: "sort the
    songs within a given artist")."""
    public_artist(db, artist_id)
    found = catalogue.artist(db, artist_id)
    names = rows.names_of(db, artist_id)
    default = next((one.name for one in names if one.is_default), names[0].name if names else "")
    songs = catalogue.songs_of(db, found.song_ids if found else [])
    songs.sort(key=lambda one: (-one.popularity, one.title_words))
    albums = [
        AlbumOfArtist(
            id=album.id, title=album.title, year=album.year, popularity=album.popularity or 0.0
        )
        for album in db.scalars(
            select(Album)
            .join(AlbumArtist, AlbumArtist.album_id == Album.id)
            .join(ArtistName, ArtistName.id == AlbumArtist.artist_name_id)
            .where(ArtistName.artist_id == artist_id)
            .distinct()
        )
    ]
    albums.sort(key=lambda one: (-one.popularity, one.year or 0))
    in_library = db.scalar(
        select(Artist.id).where(
            Artist.scope == "private", Artist.owner_id == user_id, Artist.public_id == artist_id
        )
    )
    return ArtistFacts(
        id=artist_id,
        name=default,
        other_names=[one.name for one in names if one.name != default],
        songs=songs,
        albums=albums,
        in_library=in_library,
    )


# ------------------------------------------------------------------- playlists


@dataclass
class PublicItem:
    id: int
    song_id: int | None
    song_title: str
    artists: list[str]
    project_id: str | None
    parts: list[str]
    version_name: str | None
    from_ms: int | None
    to_ms: int | None


@dataclass
class PublicPlaylist:
    id: int
    title: str
    songs: int
    updated_at: datetime
    items: list[PublicItem] = field(default_factory=list)


def playlists(db: DbSession) -> list[PublicPlaylist]:
    counts = dict(
        db.execute(
            select(PlaylistItem.playlist_id, func.count()).group_by(PlaylistItem.playlist_id)
        ).all()
    )
    out = [
        PublicPlaylist(
            id=one.id, title=one.title, songs=counts.get(one.id, 0), updated_at=one.updated_at
        )
        for one in db.scalars(select(Playlist).where(Playlist.scope == "public"))
    ]
    out.sort(key=lambda one: one.title.casefold())
    return out


def public_playlist(db: DbSession, playlist_id: int) -> Playlist:
    row = db.get(Playlist, playlist_id)
    if row is None or row.scope != "public":
        raise rows.NotFound(f"No public playlist with id {playlist_id}")
    return row


def version_name_of(db: DbSession, project_id: str) -> str | None:
    """The public version name a project is: a fixed name, or a user version's name."""
    fixed = db.scalar(select(SongVersion.name).where(SongVersion.project_id == project_id))
    if fixed is not None:
        return fixed
    return db.scalar(select(UserVersion.version_name).where(UserVersion.project_id == project_id))


def playlist_facts(db: DbSession, playlist_id: int) -> PublicPlaylist:
    row = public_playlist(db, playlist_id)
    items = list(
        db.scalars(
            select(PlaylistItem)
            .where(PlaylistItem.playlist_id == playlist_id)
            .order_by(PlaylistItem.position)
        )
    )
    song_ids = [one.song_id for one in items if one.song_id is not None]
    credits = rows.credits_of(db, song_ids)
    titles = dict(db.execute(select(Song.id, Song.title).where(Song.id.in_(song_ids))).all())
    out = PublicPlaylist(id=row.id, title=row.title, songs=len(items), updated_at=row.updated_at)
    for one in items:
        parts: list[str] = []
        if one.project_id:
            try:
                parts = bundle.part_ids_of(one.project_id)
            except (locate.NotFound, FileNotFoundError):
                parts = []
        out.items.append(
            PublicItem(
                id=one.id,
                song_id=one.song_id,
                song_title=titles.get(one.song_id, "") if one.song_id is not None else "",
                artists=[c.name for c in credits.get(one.song_id, [])] if one.song_id else [],
                project_id=one.project_id,
                parts=parts,
                version_name=version_name_of(db, one.project_id) if one.project_id else None,
                from_ms=one.from_ms,
                to_ms=one.to_ms,
            )
        )
    return out


# ----------------------------------------------------------------------- likes


def _public_version_project(db: DbSession, project_id: str) -> None:
    row = db.get(Project, project_id)
    if row is None or row.layer != "public" or version_name_of(db, project_id) is None:
        raise rows.NotFound(f"No public version with project {project_id}")


def like(db: DbSession, user_id: int, project_id: str) -> int:
    """Like a public version (once per user); answers its count of likes."""
    _public_version_project(db, project_id)
    if db.get(Like, (user_id, project_id)) is None:
        db.add(Like(user_id=user_id, project_id=project_id))
        db.flush()
    return int(db.scalar(select(func.count()).where(Like.project_id == project_id)) or 0)


def unlike(db: DbSession, user_id: int, project_id: str) -> int:
    _public_version_project(db, project_id)
    db.execute(delete(Like).where(Like.user_id == user_id, Like.project_id == project_id))
    return int(db.scalar(select(func.count()).where(Like.project_id == project_id)) or 0)


# ------------------------------------------------------------ public versions


def copy_to_public(source_project_id: str, *, creator_id: int, title: str | None = None) -> str:
    """A **copy** of a project in ``.database/public/``, owned by its creator: the first step of
    making it a public version. The copy has new ids, so the source is never changed, and no audio
    bytes are copied (P-3). The project must have its piano sheet (a version always has one)."""
    source = bundle.read_project(source_project_id)
    if not flow.sheet_ready(source):
        raise flow.Refused("A version must have its piano sheet saved")
    copy = bundle.duplicate_project(
        source_project_id, owner_id=creator_id, layer="public", title=title or source.title
    )
    return copy.id


def point_version(
    db: DbSession,
    *,
    song_id: int,
    name: str,
    project_id: str,
    creator_id: int,
    user_version: bool,
) -> str | None:
    """Make a public project a version of a public song: a fixed version (``user_version=False``)
    takes the place of the one of that name; a user version is the one project of its user and
    name (section 15.2). Answers the project it replaced, if any, which the caller deletes once the
    transaction is written and nothing uses it (:func:`delete_if_unused`).

    A user version replaced by a better one of the same name keeps its likes and its place in the
    public playlists: they move to the new project (Phase 14). A fixed version is a pointer the
    master user accepted to one project, so it does not follow."""
    name = check_public_name(name)
    public_song(db, song_id)
    replaced: str | None = None
    if user_version:
        existing_user = db.scalar(
            select(UserVersion).where(
                UserVersion.song_id == song_id,
                UserVersion.user_id == creator_id,
                UserVersion.version_name == name,
            )
        )
        if existing_user is not None:
            replaced = existing_user.project_id
            existing_user.project_id = project_id
            if replaced != project_id:
                _move_uses(db, replaced, project_id)
        else:
            db.add(
                UserVersion(
                    song_id=song_id, user_id=creator_id, version_name=name, project_id=project_id
                )
            )
    else:
        existing = db.scalar(
            select(SongVersion).where(SongVersion.song_id == song_id, SongVersion.name == name)
        )
        if existing is not None:
            replaced = existing.project_id
            existing.project_id = project_id
            existing.creator_id = creator_id
            existing.updated_at = datetime.now(timezone.utc)
        else:
            db.add(
                SongVersion(
                    song_id=song_id, name=name, project_id=project_id, creator_id=creator_id
                )
            )
    db.flush()
    return replaced if replaced != project_id else None


def _move_uses(db: DbSession, old: str, new: str) -> None:
    """The likes and the public playlist items of one project, moved to another."""
    for one in db.scalars(select(Like).where(Like.project_id == old)).all():
        if db.get(Like, (one.user_id, new)) is None:
            db.add(Like(user_id=one.user_id, project_id=new, created_at=one.created_at))
        db.delete(one)
    for item in db.scalars(
        select(PlaylistItem)
        .join(Playlist, Playlist.id == PlaylistItem.playlist_id)
        .where(Playlist.scope == "public", PlaylistItem.project_id == old)
    ):
        item.project_id = new


def place_version(
    source_project_id: str,
    *,
    song_id: int,
    name: str,
    creator_id: int,
    user_version: bool,
) -> str:
    """A **copy** of a project becomes a version of a public song, in ``.database/public/``
    (:func:`copy_to_public`, then :func:`point_version`). The accepted requests of Phase 14 use the
    two steps inside their own transaction; the tests and ``public_fixture`` use this."""
    name = check_public_name(name)
    with session() as db:
        public_song(db, song_id)
    copy = copy_to_public(source_project_id, creator_id=creator_id)
    try:
        with session() as db:
            replaced = point_version(
                db,
                song_id=song_id,
                name=name,
                project_id=copy,
                creator_id=creator_id,
                user_version=user_version,
            )
    except BaseException:
        bundle.delete_project(copy)
        raise
    if replaced is not None:
        delete_if_unused(replaced)
    catalogue.forget()
    return copy


def still_used(project_id: str) -> bool:
    """A public project is still a fixed version, a user version, or an item of a public playlist."""
    with session() as db:
        return (
            db.scalar(select(SongVersion.id).where(SongVersion.project_id == project_id))
            is not None
            or db.scalar(select(UserVersion.id).where(UserVersion.project_id == project_id))
            is not None
            or db.scalar(
                select(PlaylistItem.id)
                .join(Playlist, Playlist.id == PlaylistItem.playlist_id)
                .where(Playlist.scope == "public", PlaylistItem.project_id == project_id)
            )
            is not None
        )


def delete_if_unused(project_id: str) -> None:
    """Delete a public project nothing points at any more (a version replaced)."""
    try:
        if locate.project(project_id).layer != "public":
            return
    except locate.NotFound:
        return
    if not still_used(project_id):
        bundle.delete_project(project_id)


def remove_version(project_id: str) -> None:
    """Take a public version away and delete its project (and the audio no project uses)."""
    with session() as db:
        row = db.get(Project, project_id)
        if row is None or row.layer != "public":
            raise rows.NotFound(f"No public project {project_id}")
        db.execute(delete(UserVersion).where(UserVersion.project_id == project_id))
        for fixed in db.scalars(select(SongVersion).where(SongVersion.project_id == project_id)):
            db.delete(fixed)
    bundle.delete_project(project_id)
    catalogue.forget()
