"""The import of the downloaded music library into the public rows of ``.database/`` (implementation
02, Phase 12, plan section 15.5; the mapping is ``context/music-library/reconciliation.md``).

It reads ``library.sqlite`` of the parallel work (``data/music-library/`` next to the repository)
read only, and writes public rows: artists with their one default name, albums with their artists,
release date and chart history, songs with their artists, albums, lyrics, region and chart history,
and the popularity of each. Public rows have no owner; the master user manages them.

**Running it again changes no row a person may have changed** (section 4 of the reconciliation):

* a row is found by its ``external_key``, the source's own path with the site's name in front
  (``musicchartsarchive.com/singles/bee-gees/stayin-alive``), so a second run finds the same row;
* a row the run makes gets everything the source gives; a row that exists only gets the fields that
  are still empty (a year, a release date, the lyrics). A title, a name or a link is never written
  again;
* the chart history belongs to the source, so the weeks of its two charts are written again every
  run, and the popularity is worked out again from them.

A song that charted again ("Billie Jean [re-release]", "White Christmas [seasonal]") is the same
song: it becomes one row with the song it repeats (same title without the bracket, same first
artist), whose chart weeks it adds. When that song charted before 1976, the source has no other row,
and the song keeps its own row with the bracket taken out of its title.

The **seed list** (``scripts/seed/youtube-library/library.json``, the 31 songs of the starting
library) is checked at the end: each piece is found among the public songs, and a piece the charts
do not have is added with the title and the artist the list gives, nothing else (``--no-seed``
leaves them out; Q-5).

::

    python -m aitu_backend.library.public_import [--source library.sqlite] [--database DIR]
                                                 [--seed library.json | --no-seed]

``--database`` points at another ``.database/`` folder (a copy, to try it). Phase 13 runs it on the
real one. The source is never written: it is opened with ``mode=ro&immutable=1``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import bindparam, delete, insert, select, update
from sqlalchemy.orm import Session as DbSession

from aitu_backend.db.models import (
    Album,
    AlbumArtist,
    AlbumChartEntry,
    Artist,
    ArtistName,
    ChartEntry,
    ChartSource,
    Region,
    Song,
    SongAlbum,
    SongArtist,
    SongLyrics,
    SongRegion,
)
from aitu_backend.library import popularity

__all__ = [
    "SITE",
    "Report",
    "default_seed",
    "default_source",
    "external_key",
    "import_library",
    "plain",
    "read_source",
    "song_title",
]

#: The site the parallel work downloaded (``public-library-build/``).
SITE = "musicchartsarchive.com"
#: The two charts of the site, as rows of ``chart_sources``. Their size is the ``N`` of the
#: popularity (section 15.6): the chart history holds positions 1 to 100.
CHARTS = {"singles": f"{SITE} singles", "albums": f"{SITE} albums"}
CHART_SIZE = 100
REGION = "worldwide"

_REPOSITORY = Path(__file__).resolve().parents[4]
_REENTRY = re.compile(r"\s*\[(re-release|seasonal|re-recorded version)\]\s*$", re.IGNORECASE)


def default_source() -> Path:
    """``library.sqlite`` of ``MUSIC_LIBRARY_DIR``, else ``data/music-library/`` beside the
    repository (the parallel work's own default)."""
    folder = os.environ.get("MUSIC_LIBRARY_DIR")
    root = Path(folder) if folder else _REPOSITORY.parent / "data" / "music-library"
    return root / "library.sqlite"


def default_seed() -> Path:
    return _REPOSITORY / "scripts" / "seed" / "youtube-library" / "library.json"


def external_key(source_path: str) -> str:
    """The identity of a downloaded row: the site, then its path (``/singles/...``)."""
    return f"{SITE}{source_path}"


def song_title(title: str) -> tuple[str, bool]:
    """The title without a re-entry bracket, and whether it had one."""
    stripped = _REENTRY.sub("", title)
    return stripped, stripped != title


def plain(text: str) -> str:
    """The form two titles or two names are compared in for the seed list: no accents, no case, no
    punctuation, ``&`` as "and", ``$`` as "s", no leading "the". "Party In The U.S.A." is
    ``party in the usa``; "Ke$ha" is ``kesha``."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()
    text = text.replace("$", "s").replace("&", " and ")
    text = re.sub(r"['.]", "", text)
    text = " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())
    return text[4:] if text.startswith("the ") else text


# ---------------------------------------------------------------------- the source


@dataclass
class SourceSong:
    id: int
    path: str
    title: str
    year: int | None
    lyrics: str | None
    album_id: int | None
    artists: list[int] = field(default_factory=list)


@dataclass
class Source:
    """What ``library.sqlite`` holds, keyed by its own integer ids."""

    artists: dict[int, tuple[str, str]]  # id: (path, default name)
    albums: dict[int, tuple[str, str, str | None, int | None]]  # id: (path, title, release, year)
    album_artists: dict[int, list[int]]  # album id: artist ids in order
    songs: dict[int, SourceSong]
    tracks: list[tuple[int, int, int]]  # (album id, position, song id)
    rankings: list[tuple[str, str, int, int | None, int | None]]  # (chart, date, rank, song, album)


def read_source(path: Path) -> Source:
    """Read the whole download (about 2 s); the file is opened read only and never changed."""
    if not path.is_file():
        raise FileNotFoundError(f"No downloaded library at {path}")
    connection = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    try:
        artists = {
            int(row[0]): (str(row[1]), str(row[2]))
            for row in connection.execute(
                "SELECT a.id, a.source_path, n.name FROM artist AS a"
                " JOIN artist_name AS n ON n.artist_id = a.id AND n.is_default = 1"
            )
        }
        albums = {
            int(row[0]): (str(row[1]), str(row[2]), row[3], row[4])
            for row in connection.execute(
                "SELECT id, source_path, title, release_date, year FROM album"
            )
        }
        album_artists: dict[int, list[int]] = {}
        for album_id, artist_id in connection.execute(
            "SELECT album_id, artist_id FROM album_artist ORDER BY album_id, position"
        ):
            album_artists.setdefault(int(album_id), []).append(int(artist_id))
        songs = {
            int(row[0]): SourceSong(int(row[0]), row[1], row[2], row[3], row[4], row[5])
            for row in connection.execute(
                "SELECT id, source_path, title, year, lyrics, album_id FROM song"
            )
        }
        for song_id, artist_id in connection.execute(
            "SELECT song_id, artist_id FROM song_artist ORDER BY song_id, position"
        ):
            songs[int(song_id)].artists.append(int(artist_id))
        tracks = [
            (int(album_id), int(position), int(song_id))
            for album_id, position, song_id in connection.execute(
                "SELECT album_id, position, song_id FROM album_track WHERE song_id IS NOT NULL"
            )
        ]
        rankings = [
            (str(kind), str(day), int(rank), song_id, album_id)
            for kind, day, rank, song_id, album_id in connection.execute(
                "SELECT c.kind, w.chart_date, r.position, r.song_id, r.album_id"
                " FROM ranking AS r JOIN chart AS c ON c.id = r.chart_id"
                " JOIN chart_week AS w ON w.id = r.chart_week_id"
            )
        ]
    finally:
        connection.close()
    return Source(artists, albums, album_artists, songs, tracks, rankings)


def same_songs(source: Source) -> dict[int, int]:
    """Each source song's id, to the id of the song it is: itself, or the song it charted again.

    A re-entry joins the song with its title without the bracket and the same first artist."""
    by_title: dict[tuple[str, int | None], int] = {}
    for song in source.songs.values():
        title, again = song_title(song.title)
        if not again:
            by_title[(title.casefold(), song.artists[0] if song.artists else None)] = song.id
    target = {}
    for song in source.songs.values():
        title, again = song_title(song.title)
        first = song.artists[0] if song.artists else None
        target[song.id] = by_title.get((title.casefold(), first), song.id) if again else song.id
    return target


# ---------------------------------------------------------------------- the import


@dataclass
class Report:
    artists_made: int = 0
    artists_kept: int = 0
    albums_made: int = 0
    albums_kept: int = 0
    songs_made: int = 0
    songs_kept: int = 0
    songs_joined: int = 0
    lyrics_written: int = 0
    song_weeks: int = 0
    album_weeks: int = 0
    seconds: float = 0.0
    #: One line per piece of the seed list: (title, artist, what happened).
    seed: list[tuple[str, str | None, str]] = field(default_factory=list)

    def lines(self) -> list[str]:
        found = [
            f"  {title} ({artist or 'no artist'}): {what}" for title, artist, what in self.seed
        ]
        return [
            f"artists: {self.artists_made} made, {self.artists_kept} already there",
            f"albums:  {self.albums_made} made, {self.albums_kept} already there",
            f"songs:   {self.songs_made} made, {self.songs_kept} already there,"
            f" {self.songs_joined} re-entries joined to the song they repeat",
            f"lyrics:  {self.lyrics_written} written",
            f"chart weeks: {self.song_weeks} of songs, {self.album_weeks} of albums",
            f"time: {self.seconds:.1f} s",
            *(["seed list:"] + found if found else []),
        ]


def _keys(db: DbSession, model: Any) -> dict[str, int]:
    rows = db.execute(
        select(model.external_key, model.id).where(
            model.scope == "public", model.external_key.is_not(None)
        )
    )
    return {str(key): int(row_id) for key, row_id in rows}


def _region(db: DbSession) -> int:
    found = db.scalar(select(Region.id).where(Region.code == REGION))
    if found is None:
        raise LookupError(f"The region {REGION!r} is missing (revision 0001 writes it)")
    return int(found)


def _chart_sources(db: DbSession, region_id: int) -> dict[str, int]:
    """The rows of the two charts, made once. A weight the master user changed is kept."""
    ids = {}
    for kind, name in CHARTS.items():
        found = db.scalar(select(ChartSource.id).where(ChartSource.name == name))
        if found is None:
            row = ChartSource(name=name, region_id=region_id, size=CHART_SIZE, weight=1.0)
            db.add(row)
            db.flush()
            found = row.id
        ids[kind] = int(found)
    return ids


def _default_names(db: DbSession, artist_ids: Iterable[int]) -> dict[int, int]:
    """Artist id: the id of its default name (what a new link of the import points at)."""
    wanted = set(artist_ids)
    rows = db.execute(
        select(ArtistName.artist_id, ArtistName.id)
        .where(ArtistName.is_default.is_(True))
        .order_by(ArtistName.id)
    )
    found: dict[int, int] = {}
    for artist_id, name_id in rows:
        if artist_id in wanted:
            found.setdefault(int(artist_id), int(name_id))
    return found


def _fill_empty(db: DbSession, model: Any, column: str, values: dict[int, Any]) -> None:
    """Write ``column`` of each row id where it is still empty."""
    table = model.__table__
    rows = [
        {"row_id": row_id, "value": value} for row_id, value in values.items() if value is not None
    ]
    if rows:
        db.connection().execute(
            update(table)
            .where(table.c.id == bindparam("row_id"), table.c[column].is_(None))
            .values({column: bindparam("value")}),
            rows,
        )


def _day(text: str | None) -> date | None:
    return date.fromisoformat(text) if text else None


def import_library(
    db: DbSession,
    source: Source,
    seed: Path | None = None,
    weights: popularity.Weights = popularity.PLAN,
) -> Report:
    """Write ``source`` into the public rows of ``db`` (one transaction: the caller commits)."""
    started = time.monotonic()
    report = Report()
    region_id = _region(db)
    charts = _chart_sources(db, region_id)

    # Artists, each with its one default name (the heading of its page).
    artist_keys = _keys(db, Artist)
    new_artists = {
        artist_id: (path, name)
        for artist_id, (path, name) in source.artists.items()
        if external_key(path) not in artist_keys
    }
    report.artists_kept = len(source.artists) - len(new_artists)
    report.artists_made = len(new_artists)
    if new_artists:
        db.execute(
            insert(Artist),
            [{"scope": "public", "external_key": external_key(p)} for p, _ in new_artists.values()],
        )
        artist_keys = _keys(db, Artist)
        db.execute(
            insert(ArtistName),
            [
                {"artist_id": artist_keys[external_key(path)], "name": name, "is_default": True}
                for path, name in new_artists.values()
            ],
        )
    artist_of = {sid: artist_keys[external_key(p)] for sid, (p, _) in source.artists.items()}
    name_of = _default_names(db, artist_of.values())

    def names(artist_ids: list[int]) -> list[int]:
        seen: list[int] = []
        for artist_id in artist_ids:
            name_id = name_of.get(artist_of.get(artist_id, -1))
            if name_id is not None and name_id not in seen:
                seen.append(name_id)
        return seen

    # Albums.
    album_keys = _keys(db, Album)
    new_albums = {
        album_id
        for album_id, (path, *_rest) in source.albums.items()
        if external_key(path) not in album_keys
    }
    report.albums_made = len(new_albums)
    report.albums_kept = len(source.albums) - len(new_albums)
    if new_albums:
        db.execute(
            insert(Album),
            [
                {
                    "scope": "public",
                    "external_key": external_key(path),
                    "title": title,
                    "year": year,
                    "release_date": _day(release),
                }
                for album_id, (path, title, release, year) in source.albums.items()
                if album_id in new_albums
            ],
        )
        album_keys = _keys(db, Album)
    album_of = {aid: album_keys[external_key(row[0])] for aid, row in source.albums.items()}
    kept_albums = {album_of[aid]: aid for aid in source.albums if aid not in new_albums}
    _fill_empty(db, Album, "year", {a: source.albums[s][3] for a, s in kept_albums.items()})
    _fill_empty(
        db,
        Album,
        "release_date",
        {a: _day(source.albums[s][2]) for a, s in kept_albums.items()},
    )
    album_links = [
        {"album_id": album_of[album_id], "artist_name_id": name_id, "position": position}
        for album_id in new_albums
        for position, name_id in enumerate(names(source.album_artists.get(album_id, [])))
    ]
    if album_links:
        db.execute(insert(AlbumArtist), album_links)

    # Songs: a re-entry joins the song it repeats.
    target = same_songs(source)
    report.songs_joined = sum(1 for sid, to in target.items() if sid != to)
    members: dict[int, list[SourceSong]] = {}
    for song in sorted(source.songs.values(), key=lambda s: (target[s.id] != s.id, s.id)):
        members.setdefault(target[song.id], []).append(song)
    song_keys = _keys(db, Song)
    canonical = {sid: source.songs[sid] for sid in members}
    new_songs = {sid for sid, song in canonical.items() if external_key(song.path) not in song_keys}
    report.songs_made = len(new_songs)
    report.songs_kept = len(canonical) - len(new_songs)

    def year_of(sid: int) -> int | None:
        years = [song.year for song in members[sid] if song.year is not None]
        return min(years) if years else None

    if new_songs:
        db.execute(
            insert(Song),
            [
                {
                    "scope": "public",
                    "external_key": external_key(canonical[sid].path),
                    "title": song_title(canonical[sid].title)[0],
                    "year": year_of(sid),
                }
                for sid in sorted(new_songs)
            ],
        )
        song_keys = _keys(db, Song)
    song_of = {sid: song_keys[external_key(song.path)] for sid, song in canonical.items()}
    _fill_empty(
        db, Song, "year", {song_of[sid]: year_of(sid) for sid in canonical if sid not in new_songs}
    )

    song_links = [
        {"song_id": song_of[sid], "artist_name_id": name_id, "position": position}
        for sid in new_songs
        for position, name_id in enumerate(names(canonical[sid].artists))
    ]
    if song_links:
        db.execute(insert(SongArtist), song_links)
    regions = [{"song_id": song_of[sid], "region_id": region_id} for sid in new_songs]
    if regions:
        db.execute(insert(SongRegion), regions)

    # Albums of a song: the album of its page, and every track list it is on. Written when the
    # song or the album is new; the track number is its place in the album's reading order.
    pairs: dict[tuple[int, int], int | None] = {}
    for song in source.songs.values():
        if song.album_id is not None:
            pairs.setdefault((target[song.id], song.album_id), None)
    for album_id, position, song_id in source.tracks:
        pair = (target[song_id], album_id)
        known = pairs.get(pair)
        pairs[pair] = position if known is None else min(known, position)
    album_rows = [
        {"song_id": song_of[sid], "album_id": album_of[aid], "track_number": number}
        for (sid, aid), number in pairs.items()
        if sid in new_songs or aid in new_albums
    ]
    if album_rows:
        db.execute(insert(SongAlbum), album_rows)

    # Lyrics: written where the song has none yet.
    have_words = set(db.scalars(select(SongLyrics.song_id)))
    words = []
    for sid, group in members.items():
        text = next((s.lyrics for s in group if s.lyrics and s.lyrics.strip()), None)
        if text is not None and song_of[sid] not in have_words:
            words.append({"song_id": song_of[sid], "text": text})
    if words:
        db.execute(insert(SongLyrics), words)
    report.lyrics_written = len(words)

    # The chart history belongs to the source: its weeks are written again.
    db.execute(delete(ChartEntry).where(ChartEntry.chart_source_id == charts["singles"]))
    db.execute(delete(AlbumChartEntry).where(AlbumChartEntry.chart_source_id == charts["albums"]))
    song_weeks: dict[tuple[int, str], int] = {}
    album_weeks: dict[tuple[int, str], int] = {}
    for kind, day, rank, song_ref, album_ref in source.rankings:
        if kind == "singles" and song_ref is not None:
            key = (song_of[target[int(song_ref)]], day)
            song_weeks[key] = min(rank, song_weeks.get(key, rank))
        elif kind == "albums" and album_ref is not None:
            key = (album_of[int(album_ref)], day)
            album_weeks[key] = min(rank, album_weeks.get(key, rank))
    if song_weeks:
        db.execute(
            insert(ChartEntry),
            [
                {"song_id": s, "chart_source_id": charts["singles"], "week": _day(d), "rank": r}
                for (s, d), r in song_weeks.items()
            ],
        )
    if album_weeks:
        db.execute(
            insert(AlbumChartEntry),
            [
                {"album_id": a, "chart_source_id": charts["albums"], "week": _day(d), "rank": r}
                for (a, d), r in album_weeks.items()
            ],
        )
    report.song_weeks = len(song_weeks)
    report.album_weeks = len(album_weeks)

    popularity.store_all_time(db, weights)
    if seed is not None:
        report.seed = seed_songs(db, seed)
    report.seconds = time.monotonic() - started
    return report


# ------------------------------------------------------------------- the seed list

#: Two pieces of the seed list that the rules cannot match: ELO is written in full on the chart,
#: and "99 Red Balloons" charted in the US under its German title.
SEED_ARTISTS = {"elo": "electric light orchestra"}
SEED_SONGS = {("99 red balloons", "nena"): external_key("/singles/nena/99-luftballons")}


def _title_forms(title: str) -> set[str]:
    """A title, and the title without a closing ``(...)``: "Stronger (What Doesn't Kill You)"."""
    forms = {plain(title)}
    shorter = re.sub(r"\s*[(\[][^)\]]*[)\]]\s*$", "", title)
    if shorter and shorter != title:
        forms.add(plain(shorter))
    return forms


def seed_songs(db: DbSession, seed: Path) -> list[tuple[str, str | None, str]]:
    """Find each piece of the seed list among the public songs; add the ones the charts lack."""
    pieces = json.loads(seed.read_text(encoding="utf-8"))["pieces"]
    songs = db.execute(
        select(Song.id, Song.title, Song.external_key, Song.popularity).where(
            Song.scope == "public"
        )
    ).all()
    credited: dict[int, set[str]] = {}
    for song_id, name in db.execute(
        select(SongArtist.song_id, ArtistName.name).join(
            ArtistName, ArtistName.id == SongArtist.artist_name_id
        )
    ):
        credited.setdefault(int(song_id), set()).add(plain(name))
    by_form: dict[str, list[tuple[int, str, str | None, float | None]]] = {}
    for row in songs:
        for form in _title_forms(row.title):
            by_form.setdefault(form, []).append(tuple(row))  # type: ignore[arg-type]
    by_key = {row.external_key: row for row in songs if row.external_key}

    results = []
    for piece in pieces:
        title, artist = str(piece["title"]), piece.get("artist")
        who = plain(artist) if artist else None
        who = SEED_ARTISTS.get(who, who) if who else None
        alias = SEED_SONGS.get((plain(title), who or ""))
        if alias and alias in by_key:
            row = by_key[alias]
            results.append((title, artist, f"found as “{row.title}” ({row.external_key})"))
            continue
        matches = by_form.get(plain(title), [])
        if who:
            matches = [m for m in matches if who in credited.get(m[0], set())]
        if matches:
            best = max(matches, key=lambda m: m[3] or 0.0)
            more = f", the most popular of {len(matches)}" if len(matches) > 1 else ""
            results.append((title, artist, f"found as “{best[1]}” ({best[2]}{more})"))
            continue
        results.append((title, artist, _add_seed_song(db, title, artist)))
    return results


def _add_seed_song(db: DbSession, title: str, artist: str | None) -> str:
    key = f"seed:{plain(title)}|{plain(artist or '')}"
    found = db.scalar(select(Song.id).where(Song.scope == "public", Song.external_key == key))
    if found is not None:
        return f"added before from the seed list ({key})"
    song = Song(scope="public", external_key=key, title=title, popularity=0.0)
    db.add(song)
    db.flush()
    made = ""
    if artist:
        name_id = _public_name(db, artist)
        if name_id is None:
            new = Artist(scope="public", external_key=f"seed:{plain(artist)}")
            db.add(new)
            db.flush()
            name = ArtistName(artist_id=new.id, name=artist, is_default=True)
            db.add(name)
            db.flush()
            name_id = name.id
            made = ", with a new artist"
        db.add(SongArtist(song_id=song.id, artist_name_id=name_id, position=0))
    return f"not on the charts: added from the seed list{made} ({key})"


def _public_name(db: DbSession, artist: str) -> int | None:
    wanted = plain(artist)
    rows = db.execute(
        select(ArtistName.id, ArtistName.name)
        .join(Artist, Artist.id == ArtistName.artist_id)
        .where(Artist.scope == "public")
        .order_by(ArtistName.is_default.desc(), ArtistName.id)
    )
    return next((int(i) for i, name in rows if plain(name) == wanted), None)


# ------------------------------------------------------------------------- command


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--database", type=Path, default=None, help="another .database/ folder")
    parser.add_argument("--seed", type=Path, default=None)
    parser.add_argument("--no-seed", action="store_true")
    args = parser.parse_args(argv)
    if args.database is not None:
        os.environ["AITU_DATABASE_DIR"] = str(args.database.resolve())

    from aitu_backend.db.database import session  # noqa: PLC0415 - after AITU_DATABASE_DIR

    source_path = args.source or default_source()
    seed = None if args.no_seed else (args.seed or default_seed())
    print(f"reading {source_path}")
    source = read_source(source_path)
    with session() as db:
        report = import_library(db, source, seed=seed)
    print("\n".join(report.lines()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
