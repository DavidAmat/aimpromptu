"""The Public Library's songs and artists as one list in memory, for search, filters and sorting
(implementation 02, Phase 13, plan sections 6.1, 15.3 and 15.6).

The Public Library has about 9,000 songs and 3,000 artists (the chart download of Phase 12). A
search must match a word anywhere in a title or an artist's name, ignoring case and accents
("beyonce" finds "Beyoncé"), and SQLite's ``LIKE`` folds only ASCII letters. So the songs and
artists are read once into memory (about 0.3 s), and each request filters and sorts that list
(a few ms).

**The list stays current by a fingerprint**: a few counts and sums of the public rows (how many
songs, the sum of their years, of their popularity, of the length of their titles; the artists'
names; the links to artists, regions, genres, tags; the versions). Each request reads it (a few
ms); when it changed (an import, a change by the master user in Phase 14, a new version), the list
is read again. A change that leaves every count and sum the same (two titles of the same length
swapped) is not seen until the next change: :func:`forget` is called by the code that changes
public rows.

**Popularity in a time range** (the app context: "if we filter by a given decade, and ask to sort
by popularity, these popularities need to be recalculated on the fly") is worked out from the chart
weeks of that range (:func:`aitu_backend.library.popularity.song_scores`, about 50 ms for a decade)
and kept with the list until it changes.

The decade of a song is worked out from its year, never stored (section 8.6): 1978 is the decade
1970, shown "70s".
"""

from __future__ import annotations

import re
import threading
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from typing import Callable, Iterable, Literal

from sqlalchemy import select, text
from sqlalchemy.orm import Session as DbSession

from aitu_backend.db.models import (
    Artist,
    ArtistName,
    Region,
    Song,
    SongArtist,
    SongGenre,
    SongRegion,
    SongRegionPopularity,
    SongTag,
    SongVersion,
    UserVersion,
)
from aitu_backend.library import popularity

__all__ = [
    "CatalogueArtist",
    "CatalogueSong",
    "Facets",
    "SongPage",
    "artists_page",
    "decade_label",
    "decade_of",
    "fold",
    "forget",
    "songs_page",
    "suggest",
]

SongSort = Literal["popularity", "year", "title"]
ArtistSort = Literal["popularity", "name", "songs"]


def fold(text_in: str) -> str:
    """The form a search compares in: no accents, no case, ``&`` as "and", no punctuation.

    "Beyoncé" is ``beyonce``, "Stayin' Alive" is ``stayin alive``, "Ke$ha" is ``kesha``. Unlike the
    seed list's comparison, a leading "the" stays: a search for "the" finds "The Weeknd"."""
    out = unicodedata.normalize("NFKD", text_in).encode("ascii", "ignore").decode().casefold()
    out = out.replace("$", "s").replace("&", " and ")
    out = re.sub(r"['.]", "", out)
    return " ".join(re.sub(r"[^a-z0-9]+", " ", out).split())


def decade_of(year: int | None) -> int | None:
    """1978 → 1970."""
    return None if year is None else year - year % 10


def decade_label(decade: int) -> str:
    """1970 → "70s", 2000 → "00s"."""
    return f"{decade % 100:02d}s"


@dataclass(frozen=True)
class Credit:
    artist_id: int
    name: str


@dataclass(frozen=True)
class CatalogueSong:
    id: int
    title: str
    year: int | None
    #: All time, as stored; for a song no chart lists anywhere, its inferred worldwide one (Phase 17).
    popularity: float
    credits: tuple[Credit, ...]
    region_ids: frozenset[int]
    #: ``(region id, popularity)`` in each region other than worldwide (Phase 16), and worldwide
    #: for a song with an inferred value there (Phase 17).
    region_scores: tuple[tuple[int, float], ...]
    genre_ids: frozenset[int]
    tag_value_ids: frozenset[int]
    #: Fixed versions with a project, and user versions.
    versions: int
    #: The title and the artists' names, folded.
    words: str
    title_words: str
    artist_words: str

    @property
    def decade(self) -> int | None:
        return decade_of(self.year)

    def popularity_in(self, region_id: int | None) -> float:
        """The popularity in a region; worldwide (the stored one) when none is given."""
        if region_id is None:
            return self.popularity
        return next((value for one, value in self.region_scores if one == region_id), 0.0)


@dataclass(frozen=True)
class CatalogueArtist:
    id: int
    #: The default name.
    name: str
    #: Every other name.
    other_names: tuple[str, ...]
    song_ids: tuple[int, ...]
    #: The popularity of the artist's most popular song.
    popularity: float
    #: Songs of the artist that have a version.
    with_versions: int
    words: str


@dataclass
class _Catalogue:
    fingerprint: tuple[object, ...]
    songs: dict[int, CatalogueSong]
    artists: dict[int, CatalogueArtist]
    #: Region id -> code (``worldwide``, ``spain``, ``catalan``).
    region_codes: dict[int, str] = field(default_factory=dict)
    #: ``(start, end, region) -> song id -> popularity`` in that range and region.
    ranges: dict[tuple[date, date, str], dict[int, float]] = field(default_factory=dict)


_lock = threading.Lock()
_current: _Catalogue | None = None

_FINGERPRINT = text("""
    SELECT
      (SELECT count(*) || ':' || ifnull(max(id), 0) || ':' || total(year) || ':'
              || total(popularity) || ':' || total(length(title))
         FROM songs WHERE scope = 'public'),
      (SELECT count(*) || ':' || total(length(n.name)) || ':' || total(n.is_default)
         FROM artist_names n JOIN artists a ON a.id = n.artist_id WHERE a.scope = 'public'),
      (SELECT count(*) || ':' || total(sa.position)
         FROM song_artists sa JOIN songs s ON s.id = sa.song_id WHERE s.scope = 'public'),
      (SELECT count(*) FROM song_regions),
      (SELECT count(*) || ':' || total(popularity) FROM song_region_popularity),
      (SELECT count(*) FROM song_genres),
      (SELECT count(*) FROM song_tags),
      (SELECT count(*) FROM song_versions WHERE project_id IS NOT NULL),
      (SELECT count(*) FROM user_versions)
    """)


def forget() -> None:
    """Read the list again at the next request (called by code that changes public rows)."""
    global _current
    with _lock:
        _current = None


def _fingerprint(db: DbSession) -> tuple[object, ...]:
    return tuple(db.execute(_FINGERPRINT).one())


def _read(db: DbSession, fingerprint: tuple[object, ...]) -> _Catalogue:
    songs = db.execute(
        select(Song.id, Song.title, Song.year, Song.popularity).where(Song.scope == "public")
    ).all()
    credits: dict[int, list[Credit]] = {}
    for song_id, artist_id, name in db.execute(
        select(SongArtist.song_id, ArtistName.artist_id, ArtistName.name)
        .join(ArtistName, ArtistName.id == SongArtist.artist_name_id)
        .join(Song, Song.id == SongArtist.song_id)
        .where(Song.scope == "public")
        .order_by(SongArtist.song_id, SongArtist.position)
    ):
        credits.setdefault(song_id, []).append(Credit(artist_id, name))

    def links(
        model: type[SongRegion] | type[SongGenre] | type[SongTag], column: str
    ) -> dict[int, set[int]]:
        found: dict[int, set[int]] = {}
        for song_id, other in db.execute(select(model.song_id, getattr(model, column))):
            found.setdefault(song_id, set()).add(other)
        return found

    regions = links(SongRegion, "region_id")
    region_scores: dict[int, list[tuple[int, float]]] = {}
    for song_id, region_id, value in db.execute(
        select(
            SongRegionPopularity.song_id,
            SongRegionPopularity.region_id,
            SongRegionPopularity.popularity,
        )
    ):
        region_scores.setdefault(song_id, []).append((region_id, float(value)))
    genres = links(SongGenre, "genre_id")
    tags = links(SongTag, "tag_value_id")
    versions: dict[int, int] = {}
    for (song_id,) in db.execute(
        select(SongVersion.song_id).where(SongVersion.project_id.is_not(None))
    ):
        versions[song_id] = versions.get(song_id, 0) + 1
    for (song_id,) in db.execute(select(UserVersion.song_id)):
        versions[song_id] = versions.get(song_id, 0) + 1

    worldwide = db.scalar(select(Region.id).where(Region.code == popularity.WORLDWIDE))
    by_id: dict[int, CatalogueSong] = {}
    for song_id, title, year, score in songs:
        # Only an inferred value is stored for worldwide: the song is on no chart (Phase 17).
        inferred = next((v for r, v in region_scores.get(song_id, ()) if r == worldwide), None)
        credited = tuple(credits.get(song_id, ()))
        by_id[song_id] = CatalogueSong(
            id=song_id,
            title=title,
            year=year,
            popularity=float(score or 0.0) if inferred is None else inferred,
            credits=credited,
            region_ids=frozenset(regions.get(song_id, ())),
            region_scores=tuple(region_scores.get(song_id, ())),
            genre_ids=frozenset(genres.get(song_id, ())),
            tag_value_ids=frozenset(tags.get(song_id, ())),
            versions=versions.get(song_id, 0),
            words=fold(" ".join([title, *(one.name for one in credited)])),
            title_words=fold(title),
            artist_words=fold(" ".join(one.name for one in credited)),
        )

    names: dict[int, list[tuple[str, bool]]] = {}
    for artist_id, name, is_default in db.execute(
        select(ArtistName.artist_id, ArtistName.name, ArtistName.is_default)
        .join(Artist, Artist.id == ArtistName.artist_id)
        .where(Artist.scope == "public")
        .order_by(ArtistName.artist_id, ArtistName.is_default.desc(), ArtistName.id)
    ):
        names.setdefault(artist_id, []).append((name, is_default))
    songs_of: dict[int, list[int]] = {}
    for song in by_id.values():
        for credit in song.credits:
            listed = songs_of.setdefault(credit.artist_id, [])
            if song.id not in listed:
                listed.append(song.id)
    artists: dict[int, CatalogueArtist] = {}
    for artist_id, found in names.items():
        own = songs_of.get(artist_id, [])
        artists[artist_id] = CatalogueArtist(
            id=artist_id,
            name=found[0][0],
            other_names=tuple(name for name, _ in found[1:]),
            song_ids=tuple(own),
            popularity=max((by_id[one].popularity for one in own), default=0.0),
            with_versions=sum(1 for one in own if by_id[one].versions > 0),
            words=fold(" ".join(name for name, _ in found)),
        )
    region_codes = {int(i): str(code) for i, code in db.execute(select(Region.id, Region.code))}
    return _Catalogue(
        fingerprint=fingerprint, songs=by_id, artists=artists, region_codes=region_codes
    )


def _catalogue(db: DbSession) -> _Catalogue:
    global _current
    fingerprint = _fingerprint(db)
    with _lock:
        if _current is None or _current.fingerprint != fingerprint:
            _current = _read(db, fingerprint)
        return _current


def _range_scores(
    db: DbSession, catalogue: _Catalogue, decade: int, region: str = popularity.WORLDWIDE
) -> dict[int, float]:
    key = (date(decade, 1, 1), date(decade + 9, 12, 31), region)
    with _lock:
        found = catalogue.ranges.get(key)
    if found is None:
        found = popularity.song_scores(db, key[0], key[1], region=region)
        with _lock:
            catalogue.ranges[key] = found
    return found


def _matches(words: str, query: list[str]) -> bool:
    return all(word in words for word in query)


# ----------------------------------------------------------------------- songs


@dataclass(frozen=True)
class SongFilter:
    query: str = ""
    decade: int | None = None
    region: int | None = None
    genre: int | None = None
    tag: int | None = None


@dataclass
class Facets:
    """How many songs each value of each filter would leave, given the other filters."""

    decades: dict[int, int] = field(default_factory=dict)
    regions: dict[int, int] = field(default_factory=dict)
    genres: dict[int, int] = field(default_factory=dict)
    tags: dict[int, int] = field(default_factory=dict)


@dataclass
class SongPage:
    total: int
    #: ``(song, the popularity it is sorted and shown by)``.
    rows: list[tuple[CatalogueSong, float]]
    facets: Facets


def _keep(song: CatalogueSong, wanted: SongFilter, query: list[str], skip: str = "") -> bool:
    if query and not _matches(song.words, query):
        return False
    if skip != "decade" and wanted.decade is not None and song.decade != wanted.decade:
        return False
    if skip != "region" and wanted.region is not None and wanted.region not in song.region_ids:
        return False
    if skip != "genre" and wanted.genre is not None and wanted.genre not in song.genre_ids:
        return False
    if skip != "tag" and wanted.tag is not None and wanted.tag not in song.tag_value_ids:
        return False
    return True


def _facets(songs: Iterable[CatalogueSong], wanted: SongFilter, query: list[str]) -> Facets:
    facets = Facets()
    counters: dict[str, tuple[dict[int, int], Callable[[CatalogueSong], Iterable[int]]]] = {
        "decade": (facets.decades, lambda one: [] if one.decade is None else [one.decade]),
        "region": (facets.regions, lambda one: one.region_ids),
        "genre": (facets.genres, lambda one: one.genre_ids),
        "tag": (facets.tags, lambda one: one.tag_value_ids),
    }
    for song in songs:
        if query and not _matches(song.words, query):
            continue
        for name, (counts, values) in counters.items():
            if _keep(song, wanted, [], skip=name):
                for value in values(song):
                    counts[value] = counts.get(value, 0) + 1
    return facets


def songs_page(
    db: DbSession,
    wanted: SongFilter,
    *,
    sort: SongSort = "popularity",
    descending: bool = True,
    offset: int = 0,
    limit: int = 50,
) -> SongPage:
    """One page of the public songs that match, sorted. The popularity shown and sorted by is the
    region's when a region is chosen (Phase 16), worldwide otherwise; with a decade, it is worked
    out from that region's chart weeks of the decade."""
    catalogue = _catalogue(db)
    query = fold(wanted.query).split()
    kept = [one for one in catalogue.songs.values() if _keep(one, wanted, query)]
    code = catalogue.region_codes.get(wanted.region) if wanted.region is not None else None
    regional = code is not None and code != popularity.WORLDWIDE
    if wanted.decade is not None:
        scores = _range_scores(db, catalogue, wanted.decade, code or popularity.WORLDWIDE)
    else:
        scores = {one.id: one.popularity_in(wanted.region if regional else None) for one in kept}

    def popularity_of(one: CatalogueSong) -> float:
        return scores.get(one.id, 0.0)

    if sort == "title":
        kept.sort(key=lambda one: (one.title_words, one.id), reverse=descending)
    elif sort == "year":
        # Within a year the most popular first, both ways; a song with no year last.
        kept.sort(key=lambda one: -popularity_of(one))
        dated = [one for one in kept if one.year is not None]
        dated.sort(key=lambda one: one.year or 0, reverse=descending)
        kept = dated + [one for one in kept if one.year is None]
    else:
        kept.sort(key=lambda one: (popularity_of(one), -one.id), reverse=descending)
    rows = [(one, popularity_of(one)) for one in kept[offset : offset + limit]]
    return SongPage(
        total=len(kept), rows=rows, facets=_facets(catalogue.songs.values(), wanted, query)
    )


def song(db: DbSession, song_id: int) -> CatalogueSong | None:
    return _catalogue(db).songs.get(song_id)


# --------------------------------------------------------------------- artists


def artists_page(
    db: DbSession,
    query_text: str = "",
    *,
    sort: ArtistSort = "popularity",
    descending: bool = True,
    offset: int = 0,
    limit: int = 50,
) -> tuple[int, list[CatalogueArtist]]:
    """One page of the public artists whose names match, sorted."""
    catalogue = _catalogue(db)
    query = fold(query_text).split()
    kept = [one for one in catalogue.artists.values() if _matches(one.words, query)]
    if sort == "name":
        kept.sort(key=lambda one: (fold(one.name), one.id), reverse=descending)
    elif sort == "songs":
        kept.sort(key=lambda one: (len(one.song_ids), one.popularity), reverse=descending)
    else:
        kept.sort(key=lambda one: (one.popularity, len(one.song_ids)), reverse=descending)
    return len(kept), kept[offset : offset + limit]


def songs_of(db: DbSession, song_ids: Iterable[int]) -> list[CatalogueSong]:
    catalogue = _catalogue(db)
    return [catalogue.songs[one] for one in song_ids if one in catalogue.songs]


def artist(db: DbSession, artist_id: int) -> CatalogueArtist | None:
    return _catalogue(db).artists.get(artist_id)


# --------------------------------------------------------------------- suggest


def suggest(
    db: DbSession, query_text: str, *, artist_text: str = "", limit: int = 8
) -> tuple[list[CatalogueSong], list[CatalogueArtist]]:
    """The most popular songs and artists that match what is typed: the suggestions of **Save to
    library** and of **Search**. ``artist_text`` keeps the songs of artists whose names match it."""
    catalogue = _catalogue(db)
    query = fold(query_text).split()
    by_artist = fold(artist_text).split()
    if not query and not by_artist:
        return [], []
    songs = [
        one
        for one in catalogue.songs.values()
        if (not query or _matches(one.title_words, query))
        and (not by_artist or _matches(one.artist_words, by_artist))
    ]
    songs.sort(key=lambda one: (-one.popularity, one.id))
    artists = (
        [one for one in catalogue.artists.values() if _matches(one.words, query)] if query else []
    )
    artists.sort(key=lambda one: (-one.popularity, one.id))
    return songs[:limit], artists[:limit]
