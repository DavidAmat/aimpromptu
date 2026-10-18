"""``/public``: the Public Library (implementation 02, Phase 13, plan sections 6.1, 15.1 to 15.3
and 15.6): its songs with search, filters and sort, one song with its metadata and versions, its
artists, its playlists, likes, and **Add to my library**.

Every signed-in user reads it (section 9.3). Nothing here changes a public row: the master user
changes them by accepting requests (Phase 14). A like and a pull change only the user's own rows.

The lists come from :mod:`aitu_backend.library.catalogue` (in memory, a few ms a request); one song,
one artist and the playlists from :mod:`aitu_backend.library.public`; the pulls from
:mod:`aitu_backend.library.pull`. The like routes name their project ``public_project``, not
``project_id``: the router's rights check would read a like (a write) as a write of the public
project, which only the master user may do.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime
from typing import Iterator, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from aitu_backend.db.database import session
from aitu_backend.db.models import Genre, Region, TagCategory, TagValue
from aitu_backend.db.users import current_user_id
from aitu_backend.library import catalogue, flow, public, pull, rows

router = APIRouter(prefix="/public", tags=["public"])


class _Camel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class Credit(_Camel):
    artist_id: int = Field(..., alias="artistId")
    name: str


class SongRow(_Camel):
    id: int
    title: str
    artists: list[Credit]
    year: int | None = None
    #: All time, or in the decade the list is filtered by.
    popularity: float
    versions: int


class FacetValue(_Camel):
    #: The value a filter takes: a decade's first year, a region's code, a genre's or a tag's id.
    value: str
    label: str
    count: int
    #: A tag's category ("films").
    group: str | None = None


class Facets(_Camel):
    decades: list[FacetValue]
    regions: list[FacetValue]
    genres: list[FacetValue]
    tags: list[FacetValue]


class SongPage(_Camel):
    total: int
    rows: list[SongRow]
    facets: Facets


class Version(_Camel):
    project_id: str = Field(..., alias="projectId")
    parts: list[str]
    name: str
    creator: str | None = None
    likes: int
    liked: bool
    created_at: datetime | None = Field(None, alias="createdAt")
    ready: bool
    #: The private copy the user pulled, if any.
    in_library: str | None = Field(None, alias="inLibrary")


class UserVersions(_Camel):
    username: str
    versions: list[Version]


class AlbumRef(_Camel):
    id: int
    title: str
    year: int | None = None
    track: int | None = None


class ChartOut(_Camel):
    name: str
    best: int
    weeks: int
    first: date
    last: date
    #: ``[week, rank]``, oldest first.
    history: list[tuple[date, int]]


class SongDetail(_Camel):
    id: int
    title: str
    year: int | None = None
    decade: str | None = None
    popularity: float
    artists: list[Credit]
    albums: list[AlbumRef]
    genres: list[str]
    regions: list[str]
    tags: list[tuple[str, str]]
    charts: list[ChartOut]
    has_lyrics: bool = Field(..., alias="hasLyrics")
    default_version: str = Field(..., alias="defaultVersion")
    fixed: list[Version]
    others: list[UserVersions]
    in_library: int | None = Field(None, alias="inLibrary")


class Lyrics(_Camel):
    text: str


class ArtistRow(_Camel):
    id: int
    name: str
    other_names: list[str] = Field(..., alias="otherNames")
    songs: int
    popularity: float
    #: Songs that have a version (what **Add to my library** would add).
    with_versions: int = Field(..., alias="withVersions")


class ArtistPage(_Camel):
    total: int
    rows: list[ArtistRow]


class ArtistSong(_Camel):
    id: int
    title: str
    year: int | None = None
    popularity: float
    versions: int


class AlbumRow(_Camel):
    id: int
    title: str
    year: int | None = None
    popularity: float


class ArtistDetail(_Camel):
    id: int
    name: str
    other_names: list[str] = Field(..., alias="otherNames")
    songs: list[ArtistSong]
    albums: list[AlbumRow]
    with_versions: int = Field(..., alias="withVersions")
    in_library: int | None = Field(None, alias="inLibrary")


class PlaylistRow(_Camel):
    id: int
    title: str
    songs: int
    updated_at: datetime = Field(..., alias="updatedAt")


class PlaylistItemOut(_Camel):
    id: int
    song_id: int | None = Field(None, alias="songId")
    song_title: str = Field(..., alias="songTitle")
    artists: list[str]
    project_id: str | None = Field(None, alias="projectId")
    parts: list[str]
    version_name: str | None = Field(None, alias="versionName")
    from_ms: int | None = Field(None, alias="fromMs")
    to_ms: int | None = Field(None, alias="toMs")


class PlaylistDetail(PlaylistRow):
    items: list[PlaylistItemOut]


class Suggestions(_Camel):
    songs: list[SongRow]
    artists: list[ArtistRow]


class RegionOut(_Camel):
    code: str
    name: str


class ListsOut(_Camel):
    """The fixed lists a song's metadata takes its values from (section 15.3)."""

    genres: list[str]
    regions: list[RegionOut]
    tag_categories: list[str] = Field(..., alias="tagCategories")


class LikeOut(_Camel):
    likes: int
    liked: bool


class PullIn(_Camel):
    #: The public versions to add, by project; the song's default version when empty.
    projects: list[str] = Field(default_factory=list)


class PulledOut(_Camel):
    #: The private song, artist or playlist the pull made or used.
    id: int
    songs: int
    versions: int
    already: int


@contextmanager
def _answers() -> Iterator[None]:
    try:
        yield
    except rows.NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (rows.Conflict, flow.Refused) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _song_row(song: catalogue.CatalogueSong, score: float | None = None) -> SongRow:
    return SongRow(
        id=song.id,
        title=song.title,
        artists=[Credit(artist_id=one.artist_id, name=one.name) for one in song.credits],
        year=song.year,
        popularity=song.popularity if score is None else score,
        versions=song.versions,
    )


def _artist_row(found: catalogue.CatalogueArtist) -> ArtistRow:
    return ArtistRow(
        id=found.id,
        name=found.name,
        other_names=list(found.other_names),
        songs=len(found.song_ids),
        popularity=found.popularity,
        with_versions=found.with_versions,
    )


# ----------------------------------------------------------------------- songs


@router.get("/songs", response_model=SongPage, response_model_by_alias=True)
def list_songs(
    q: str = "",
    decade: int | None = None,
    region: str | None = None,
    genre: int | None = None,
    tag: int | None = None,
    sort: Literal["popularity", "year", "title"] = "popularity",
    direction: Literal["asc", "desc"] = Query("desc", alias="dir"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> SongPage:
    """The public songs that match ``q`` (title and artists, any order, accents ignored) and the
    filters, sorted, one page at a time. With a ``decade`` (its first year: 1980), the popularity
    shown and sorted by is the one of that decade's chart weeks (section 15.6). ``facets`` counts the
    songs each filter value would leave."""
    with session() as db:
        regions = {
            code: (region_id, name)
            for region_id, code, name in db.execute(select(Region.id, Region.code, Region.name))
        }
        region_id = None
        if region is not None:
            if region not in regions:
                raise HTTPException(status_code=422, detail=f"No region '{region}'")
            region_id = regions[region][0]
        page = catalogue.songs_page(
            db,
            catalogue.SongFilter(query=q, decade=decade, region=region_id, genre=genre, tag=tag),
            sort=sort,
            descending=direction == "desc",
            offset=offset,
            limit=limit,
        )
        genres = dict(db.execute(select(Genre.id, Genre.name)).all())
        tags = {
            value_id: (category, value)
            for value_id, category, value in db.execute(
                select(TagValue.id, TagCategory.name, TagValue.value).join(
                    TagCategory, TagCategory.id == TagValue.category_id
                )
            )
        }
    code_of = {region_id: (code, name) for code, (region_id, name) in regions.items()}
    facets = Facets(
        decades=[
            FacetValue(value=str(one), label=catalogue.decade_label(one), count=count)
            for one, count in sorted(page.facets.decades.items())
        ],
        regions=[
            FacetValue(value=code_of[one][0], label=code_of[one][1], count=count)
            for one, count in sorted(page.facets.regions.items())
            if one in code_of
        ],
        genres=[
            FacetValue(value=str(one), label=genres.get(one, ""), count=count)
            for one, count in sorted(
                page.facets.genres.items(), key=lambda kv: genres.get(kv[0], "")
            )
        ],
        tags=[
            FacetValue(value=str(one), label=tags[one][1], group=tags[one][0], count=count)
            for one, count in sorted(
                page.facets.tags.items(), key=lambda kv: tags.get(kv[0], ("", ""))
            )
            if one in tags
        ],
    )
    return SongPage(
        total=page.total, rows=[_song_row(one, score) for one, score in page.rows], facets=facets
    )


def _version_out(found: public.VersionFacts, copies: dict[str, str]) -> Version:
    return Version(
        project_id=found.project_id,
        parts=found.parts,
        name=found.name,
        creator=found.creator,
        likes=found.likes,
        liked=found.liked,
        created_at=found.created_at,
        ready=found.ready,
        in_library=copies.get(found.project_id),
    )


@router.get("/songs/{song_id}", response_model=SongDetail, response_model_by_alias=True)
def get_song(song_id: int) -> SongDetail:
    """One public song: its metadata (section 15.3), its chart history, its fixed versions and its
    Other versions by user (section 15.2), and whether it is in the user's library."""
    user = current_user_id()
    with _answers(), session() as db:
        found = public.song_facts(db, song_id, user)
        project_ids = [one.project_id for one in found.fixed] + [
            one.project_id for group in found.others for one in group.versions
        ]
        copies = pull.pulled_copies(db, user, project_ids)
    decade = catalogue.decade_of(found.year)
    return SongDetail(
        id=found.id,
        title=found.title,
        year=found.year,
        decade=None if decade is None else catalogue.decade_label(decade),
        popularity=found.popularity,
        artists=[Credit(artist_id=artist_id, name=name) for artist_id, name in found.artists],
        albums=[
            AlbumRef(id=one.id, title=one.title, year=one.year, track=one.track)
            for one in found.albums
        ],
        genres=found.genres,
        regions=[one.name for one in found.regions],
        tags=found.tags,
        charts=[
            ChartOut(
                name=one.name,
                best=one.best,
                weeks=one.weeks,
                first=one.first,
                last=one.last,
                history=one.history,
            )
            for one in found.charts
        ],
        has_lyrics=found.has_lyrics,
        default_version=found.default_version,
        fixed=[_version_out(one, copies) for one in found.fixed],
        others=[
            UserVersions(
                username=group.username,
                versions=[_version_out(one, copies) for one in group.versions],
            )
            for group in found.others
        ],
        in_library=found.in_library,
    )


@router.get("/songs/{song_id}/lyrics", response_model=Lyrics)
def get_lyrics(song_id: int) -> Lyrics:
    """The words of a public song, as the download gave them (kept for this personal version only:
    reconciliation section 3)."""
    with _answers(), session() as db:
        return Lyrics(text=public.lyrics(db, song_id))


@router.post(
    "/songs/{song_id}/pull", response_model=PulledOut, response_model_by_alias=True, status_code=201
)
def pull_song(song_id: int, body: PullIn) -> PulledOut:
    """**Add to my library**: the song (and its artists) as the user's own, with the chosen
    versions copied into their Private Library. ``409`` when the song has no version yet."""
    with _answers():
        found = pull.pull_song(current_user_id(), song_id, body.projects or None)
    return PulledOut(id=found.id, songs=found.songs, versions=found.versions, already=found.already)


# --------------------------------------------------------------------- artists


@router.get("/artists", response_model=ArtistPage, response_model_by_alias=True)
def list_artists(
    q: str = "",
    sort: Literal["popularity", "name", "songs"] = "popularity",
    direction: Literal["asc", "desc"] = Query("desc", alias="dir"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> ArtistPage:
    """The public artists whose names match ``q``. An artist's popularity is its most popular
    song's."""
    with session() as db:
        total, found = catalogue.artists_page(
            db, q, sort=sort, descending=direction == "desc", offset=offset, limit=limit
        )
    return ArtistPage(total=total, rows=[_artist_row(one) for one in found])


@router.get("/artists/{artist_id}", response_model=ArtistDetail, response_model_by_alias=True)
def get_artist(artist_id: int) -> ArtistDetail:
    """One public artist: its names, its songs and its albums, each by popularity."""
    with _answers(), session() as db:
        found = public.artist_facts(db, artist_id, current_user_id())
    return ArtistDetail(
        id=found.id,
        name=found.name,
        other_names=found.other_names,
        songs=[
            ArtistSong(
                id=one.id,
                title=one.title,
                year=one.year,
                popularity=one.popularity,
                versions=one.versions,
            )
            for one in found.songs
        ],
        albums=[
            AlbumRow(id=one.id, title=one.title, year=one.year, popularity=one.popularity)
            for one in found.albums
        ],
        with_versions=sum(1 for one in found.songs if one.versions > 0),
        in_library=found.in_library,
    )


@router.post(
    "/artists/{artist_id}/pull",
    response_model=PulledOut,
    response_model_by_alias=True,
    status_code=201,
)
def pull_artist(artist_id: int) -> PulledOut:
    """**Add to my library** on an artist: every song of it that has a version, each with its
    default version. ``409`` when none has one yet."""
    with _answers():
        found = pull.pull_artist(current_user_id(), artist_id)
    return PulledOut(id=found.id, songs=found.songs, versions=found.versions, already=found.already)


# ------------------------------------------------------------------- playlists


@router.get("/playlists", response_model=list[PlaylistRow], response_model_by_alias=True)
def list_playlists() -> list[PlaylistRow]:
    with session() as db:
        return [
            PlaylistRow(id=one.id, title=one.title, songs=one.songs, updated_at=one.updated_at)
            for one in public.playlists(db)
        ]


@router.get("/playlists/{playlist_id}", response_model=PlaylistDetail, response_model_by_alias=True)
def get_playlist(playlist_id: int) -> PlaylistDetail:
    with _answers(), session() as db:
        found = public.playlist_facts(db, playlist_id)
    return PlaylistDetail(
        id=found.id,
        title=found.title,
        songs=found.songs,
        updated_at=found.updated_at,
        items=[
            PlaylistItemOut(
                id=one.id,
                song_id=one.song_id,
                song_title=one.song_title,
                artists=one.artists,
                project_id=one.project_id,
                parts=one.parts,
                version_name=one.version_name,
                from_ms=one.from_ms,
                to_ms=one.to_ms,
            )
            for one in found.items
        ],
    )


@router.post(
    "/playlists/{playlist_id}/pull",
    response_model=PulledOut,
    response_model_by_alias=True,
    status_code=201,
)
def pull_playlist(playlist_id: int) -> PulledOut:
    """**Add to my library** on a playlist: a songs playlist of the user's own, its songs and
    versions pulled. Pulled before: the playlist made then."""
    with _answers():
        found = pull.pull_playlist(current_user_id(), playlist_id)
    return PulledOut(id=found.id, songs=found.songs, versions=found.versions, already=found.already)


# ----------------------------------------------------------------------- likes


@router.put("/likes/{public_project}", response_model=LikeOut)
def like(public_project: str) -> LikeOut:
    """Like a public version (once per user)."""
    with _answers(), session() as db:
        return LikeOut(likes=public.like(db, current_user_id(), public_project), liked=True)


@router.delete("/likes/{public_project}", response_model=LikeOut)
def unlike(public_project: str) -> LikeOut:
    with _answers(), session() as db:
        return LikeOut(likes=public.unlike(db, current_user_id(), public_project), liked=False)


# ----------------------------------------------------------------------- lists


@router.get("/lists", response_model=ListsOut, response_model_by_alias=True)
def lists() -> ListsOut:
    """The genres, regions and tag categories a request can give a song (Phase 14)."""
    with session() as db:
        return ListsOut(
            genres=list(db.scalars(select(Genre.name).order_by(Genre.id))),
            regions=[
                RegionOut(code=code, name=name)
                for code, name in db.execute(select(Region.code, Region.name).order_by(Region.id))
            ],
            tag_categories=list(db.scalars(select(TagCategory.name).order_by(TagCategory.id))),
        )


# --------------------------------------------------------------------- suggest


@router.get("/suggest", response_model=Suggestions, response_model_by_alias=True)
def suggest(q: str = "", artist: str = "", limit: int = Query(8, ge=1, le=50)) -> Suggestions:
    """The most popular songs whose title matches ``q`` (by an artist matching ``artist``, when
    given) and artists whose names match ``q``: the suggestions of **Save to library** and
    **Search**."""
    with session() as db:
        songs, artists = catalogue.suggest(db, q, artist_text=artist, limit=limit)
    return Suggestions(
        songs=[_song_row(one) for one in songs], artists=[_artist_row(one) for one in artists]
    )
