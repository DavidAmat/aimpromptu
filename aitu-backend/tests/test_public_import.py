"""The import of the downloaded music library into public rows (implementation 02, Phase 12, plan
section 15.5; ``context/music-library/reconciliation.md``): the mapping, the re-entries joined, the
identity across runs, the rule that a second run changes nothing a person may have changed, the
seed list, and the source never written."""

from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import select

from aitu_backend.db.database import session
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
from aitu_backend.library.public_import import (
    external_key,
    import_library,
    plain,
    read_source,
    song_title,
)

#: The tables of ``library.sqlite`` the import reads, as the parallel work's ``build_library.py``
#: makes them (``public-library-build/02-a-public-library-build-implementation.md`` section 6.2).
SOURCE_SCHEMA = """
CREATE TABLE region (id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE);
CREATE TABLE artist (id INTEGER PRIMARY KEY, source_path TEXT NOT NULL UNIQUE);
CREATE TABLE artist_name (id INTEGER PRIMARY KEY, artist_id INTEGER NOT NULL, name TEXT NOT NULL,
    is_default INTEGER NOT NULL);
CREATE TABLE album (id INTEGER PRIMARY KEY, source_path TEXT NOT NULL UNIQUE, title TEXT NOT NULL,
    release_date TEXT, year INTEGER, region_id INTEGER NOT NULL);
CREATE TABLE album_artist (album_id INTEGER NOT NULL, artist_id INTEGER NOT NULL,
    position INTEGER NOT NULL, PRIMARY KEY (album_id, artist_id));
CREATE TABLE song (id INTEGER PRIMARY KEY, source_path TEXT NOT NULL UNIQUE, title TEXT NOT NULL,
    year INTEGER, lyrics TEXT, album_id INTEGER, region_id INTEGER NOT NULL);
CREATE TABLE song_artist (song_id INTEGER NOT NULL, artist_id INTEGER NOT NULL,
    position INTEGER NOT NULL, PRIMARY KEY (song_id, artist_id));
CREATE TABLE album_track (album_id INTEGER NOT NULL, position INTEGER NOT NULL,
    printed_number INTEGER NOT NULL, title TEXT NOT NULL, song_id INTEGER,
    PRIMARY KEY (album_id, position));
CREATE TABLE chart (id INTEGER PRIMARY KEY, kind TEXT NOT NULL UNIQUE);
CREATE TABLE chart_week (id INTEGER PRIMARY KEY, chart_date TEXT NOT NULL UNIQUE);
CREATE TABLE ranking (id INTEGER PRIMARY KEY, chart_id INTEGER NOT NULL,
    chart_week_id INTEGER NOT NULL, position INTEGER NOT NULL, song_id INTEGER, album_id INTEGER);
"""

ROWS = """
INSERT INTO region VALUES (1, 'worldwide');
INSERT INTO artist VALUES (1, '/artists/bee-gees'), (2, '/artists/pitbull'), (3, '/artists/ne-yo'),
    (4, '/artists/michael-jackson'), (5, '/artists/bing-crosby');
INSERT INTO artist_name VALUES (1, 1, 'Bee Gees', 1), (2, 2, 'Pitbull', 1), (3, 3, 'Ne-Yo', 1),
    (4, 4, 'Michael Jackson', 1), (5, 5, 'Bing Crosby', 1);
INSERT INTO album VALUES
    (1, '/albums/bee-gees/saturday-night-fever', 'Saturday Night Fever', '1977-11-15', 1977, 1),
    (2, '/albums/michael-jackson/thriller', 'Thriller', NULL, 1982, 1);
INSERT INTO album_artist VALUES (1, 1, 1), (2, 4, 1);
INSERT INTO song VALUES
    (1, '/singles/bee-gees/stayin-alive', 'Stayin'' Alive', 1977, 'Well, you can tell', 1, 1),
    (2, '/singles/pitbull/give-me-everything', 'Give Me Everything', 2011, NULL, NULL, 1),
    (3, '/singles/michael-jackson/billie-jean', 'Billie Jean', 1983, NULL, 2, 1),
    (4, '/singles/michael-jackson/billie-jean-re-release', 'Billie Jean [re-release]', 2009,
        'She was more like a beauty queen', NULL, 1),
    (5, '/singles/bing-crosby/white-christmas', 'White Christmas [seasonal]', NULL, NULL, NULL, 1),
    (6, '/singles/everlast/what-its-like', 'What It''s Like', NULL, NULL, NULL, 1);
INSERT INTO song_artist VALUES (1, 1, 1), (2, 2, 1), (2, 3, 2), (3, 4, 1), (4, 4, 1), (5, 5, 1);
INSERT INTO album_track VALUES (1, 1, 1, 'Stayin'' Alive', 1), (1, 2, 2, 'How Deep', NULL),
    (2, 1, 1, 'Wanna Be Startin'' Somethin''', NULL), (2, 6, 6, 'Billie Jean', 3);
INSERT INTO chart VALUES (1, 'singles'), (2, 'albums');
INSERT INTO chart_week VALUES (1, '1977-12-10'), (2, '1978-01-21'), (3, '1978-02-11'),
    (4, '1983-03-05'), (5, '2009-07-11'), (6, '2010-12-25');
INSERT INTO ranking VALUES (1, 1, 1, 65, 1, NULL), (2, 1, 3, 1, 1, NULL), (3, 1, 4, 1, 3, NULL),
    (4, 1, 5, 25, 4, NULL), (5, 1, 6, 30, 5, NULL), (6, 2, 2, 1, NULL, 1), (7, 1, 5, 3, 2, NULL);
"""


@pytest.fixture
def source(tmp_path: Path) -> Path:
    path = tmp_path / "library.sqlite"
    with sqlite3.connect(path) as connection:
        connection.executescript(SOURCE_SCHEMA + ROWS)
    return path


def run(path: Path, seed: Path | None = None):  # type: ignore[no-untyped-def]
    with session() as db:
        return import_library(db, read_source(path), seed=seed)


def song_row(db, path: str) -> Song:  # type: ignore[no-untyped-def]
    found = db.scalar(select(Song).where(Song.external_key == external_key(path)))
    assert found is not None, path
    return found


def credited(db, song_id: int) -> list[str]:  # type: ignore[no-untyped-def]
    return list(
        db.scalars(
            select(ArtistName.name)
            .join(SongArtist, SongArtist.artist_name_id == ArtistName.id)
            .where(SongArtist.song_id == song_id)
            .order_by(SongArtist.position)
        )
    )


def test_every_downloaded_row_becomes_a_public_row(source: Path) -> None:
    report = run(source)
    assert (report.artists_made, report.albums_made, report.songs_made) == (5, 2, 5)
    assert report.songs_joined == 1
    with session() as db:
        assert all(
            row.scope == "public" and row.owner_id is None for row in db.scalars(select(Song))
        )
        names = {n.name: n for n in db.scalars(select(ArtistName))}
        assert all(name.is_default for name in names.values())

        alive = song_row(db, "/singles/bee-gees/stayin-alive")
        assert (alive.title, alive.year) == ("Stayin' Alive", 1977)
        assert credited(db, alive.id) == ["Bee Gees"]
        assert db.get(SongLyrics, alive.id).text == "Well, you can tell"  # type: ignore[union-attr]
        weeks = db.execute(
            select(ChartEntry.week, ChartEntry.rank)
            .where(ChartEntry.song_id == alive.id)
            .order_by(ChartEntry.week)
        ).all()
        assert [tuple(w) for w in weeks] == [(date(1977, 12, 10), 65), (date(1978, 2, 11), 1)]
        assert alive.popularity == popularity.score([popularity.Week(65), popularity.Week(1)])

        # Two artists, in the order of the source; a song with no artist page has none.
        both = song_row(db, "/singles/pitbull/give-me-everything")
        assert credited(db, both.id) == ["Pitbull", "Ne-Yo"]
        assert credited(db, song_row(db, "/singles/everlast/what-its-like").id) == []

        # The album: its artist, its release date, its chart history, its songs by track number.
        fever = db.scalar(select(Album).where(Album.title == "Saturday Night Fever"))
        assert fever is not None
        assert (fever.year, fever.release_date) == (1977, date(1977, 11, 15))
        album_artist = db.scalar(select(AlbumArtist).where(AlbumArtist.album_id == fever.id))
        assert album_artist is not None and album_artist.artist_name_id == names["Bee Gees"].id
        album_weeks = list(db.scalars(select(AlbumChartEntry.rank)))
        assert album_weeks == [1]
        assert fever.popularity == popularity.score([popularity.Week(1)])
        links = {
            (link.song_id, link.album_id): link.track_number
            for link in db.scalars(select(SongAlbum))
        }
        thriller = db.scalar(select(Album).where(Album.title == "Thriller"))
        assert thriller is not None
        jean = song_row(db, "/singles/michael-jackson/billie-jean")
        assert links == {(alive.id, fever.id): 1, (jean.id, thriller.id): 6}

        # Every song is of the region of its chart; the two charts are rows of chart_sources.
        worldwide = db.scalar(select(Region.id).where(Region.code == "worldwide"))
        assert {r.region_id for r in db.scalars(select(SongRegion))} == {worldwide}
        assert len(list(db.scalars(select(SongRegion)))) == 5
        charts = {c.name: (c.size, c.weight) for c in db.scalars(select(ChartSource))}
        assert charts == {
            "musicchartsarchive.com singles": (100, 1.0),
            "musicchartsarchive.com albums": (100, 1.0),
        }


def test_a_song_that_charted_again_is_one_song(source: Path) -> None:
    run(source)
    with session() as db:
        titles = list(db.scalars(select(Song.title).where(Song.title.like("Billie Jean%"))))
        assert titles == ["Billie Jean"]
        jean = song_row(db, "/singles/michael-jackson/billie-jean")
        assert jean.year == 1983
        assert list(db.scalars(select(ChartEntry.rank).where(ChartEntry.song_id == jean.id))) == [
            1,
            25,
        ]
        # The words came with the re-entry, since the song itself has none.
        assert db.get(SongLyrics, jean.id).text.startswith("She was")  # type: ignore[union-attr]
        # A re-entry with no earlier row keeps its own row, without the bracket.
        christmas = song_row(db, "/singles/bing-crosby/white-christmas")
        assert christmas.title == "White Christmas"


def test_a_second_run_finds_the_same_rows_and_keeps_what_a_person_changed(source: Path) -> None:
    run(source)
    with session() as db:
        alive = song_row(db, "/singles/bee-gees/stayin-alive")
        alive.title = "Stayin’ Alive (edited)"
        name = db.scalar(select(ArtistName).where(ArtistName.name == "Bee Gees"))
        assert name is not None
        name.name = "The Bee Gees"
        both = song_row(db, "/singles/pitbull/give-me-everything")
        db.execute(SongArtist.__table__.delete().where(SongArtist.song_id == both.id))
        db.execute(SongLyrics.__table__.delete().where(SongLyrics.song_id == alive.id))
    with sqlite3.connect(source) as connection:
        connection.execute("UPDATE song SET year = 1942 WHERE id = 5")
        connection.execute("UPDATE ranking SET position = 2 WHERE id = 2")

    report = run(source)
    assert (report.artists_made, report.albums_made, report.songs_made) == (0, 0, 0)
    assert (report.artists_kept, report.albums_kept, report.songs_kept) == (5, 2, 5)
    with session() as db:
        assert len(list(db.scalars(select(Song)))) == 5
        assert len(list(db.scalars(select(Artist)))) == 5
        alive = song_row(db, "/singles/bee-gees/stayin-alive")
        assert alive.title == "Stayin’ Alive (edited)"
        assert credited(db, alive.id) == ["The Bee Gees"]
        assert credited(db, song_row(db, "/singles/pitbull/give-me-everything").id) == []
        # Empty fields are filled; the chart history is the source's, written again.
        assert db.get(SongLyrics, alive.id).text == "Well, you can tell"  # type: ignore[union-attr]
        assert song_row(db, "/singles/bing-crosby/white-christmas").year == 1942
        ranks = db.scalars(select(ChartEntry.rank).where(ChartEntry.song_id == alive.id))
        assert sorted(ranks) == [2, 65]
        assert alive.popularity == popularity.score([popularity.Week(65), popularity.Week(2)])


def test_the_seed_list_is_checked_and_its_missing_songs_added_once(
    source: Path, tmp_path: Path
) -> None:
    seed = tmp_path / "library.json"
    pieces = [
        {"title": "Stayin Alive", "artist": "Bee Gees"},
        {"title": "billie jean", "artist": None},
        {"title": "Give Me Everything", "artist": "Ne-Yo"},
        {"title": "Stayin' Alive", "artist": "Another Band"},
        {"title": "Superestrella", "artist": "Aitana"},
    ]
    seed.write_text(json.dumps({"pieces": pieces}))
    report = run(source, seed)
    found = [what.split(":")[0].split(" as ")[0] for _t, _a, what in report.seed]
    assert found == ["found", "found", "found", "not on the charts", "not on the charts"]
    run(source, seed)
    with session() as db:
        added = list(db.scalars(select(Song).where(Song.external_key.like("seed:%"))))
        assert sorted(song.title for song in added) == ["Stayin' Alive", "Superestrella"]
        aitana = next(song for song in added if song.title == "Superestrella")
        assert (aitana.year, aitana.popularity) == (None, 0.0)
        assert credited(db, aitana.id) == ["Aitana"]
        assert db.scalar(select(SongRegion).where(SongRegion.song_id == aitana.id)) is None


def test_the_source_is_never_written(source: Path) -> None:
    before = (source.read_bytes(), source.stat().st_mtime_ns)
    run(source)
    assert (source.read_bytes(), source.stat().st_mtime_ns) == before
    assert sorted(p.name for p in source.parent.iterdir()) == ["library.sqlite"]


def test_the_compared_forms() -> None:
    assert plain("Party In The U.S.A.") == "party in the usa"
    assert plain("Ke$ha") == "kesha"
    assert plain("The Fate Of Ophelia") == plain("Fate of Ophelia")
    assert plain("Can't Stop The Feeling!") == plain("Can't Stop the Feeling")
    assert plain("Anne-Marie") == "anne marie"
    assert song_title("All I Want For Christmas Is You [seasonal]") == (
        "All I Want For Christmas Is You",
        True,
    )
    assert song_title("The Beatles [White Album]") == ("The Beatles [White Album]", False)
