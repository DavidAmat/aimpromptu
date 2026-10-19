"""The import of the `spain` and `catalan` sources (implementation 02, Phase 16;
``context/music-library/regional-sources.md``): the identity rule of Phase 12 across sources, the
monthly lists as weeks, the weight of a list of number ones, the popularity per region and what it
rests on, the worldwide popularity unchanged, a second run that makes nothing, and the list and the
song page by region."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import func, select

from aitu_backend.db.database import session
from aitu_backend.db.models import (
    Artist,
    ArtistName,
    ChartEntry,
    ChartSource,
    Region,
    Song,
    SongArtist,
    SongKey,
    SongRegion,
    SongRegionPopularity,
)
from aitu_backend.library import catalogue, popularity, public
from aitu_backend.library.public_import import external_key, import_library, read_source
from aitu_backend.library.regional_import import (
    artist_parts,
    import_regions,
    read_all,
    title_forms,
)
from tests.test_public_import import ROWS, SOURCE_SCHEMA

#: The tables ``scripts/music-library-regions/build.py`` writes, one database per source.
SCHEMA = """
CREATE TABLE charts (code TEXT PRIMARY KEY, name TEXT, region TEXT, period TEXT, source TEXT);
CREATE TABLE songs (id INTEGER PRIMARY KEY, key TEXT UNIQUE, title TEXT, artist TEXT,
                    youtube_id TEXT, apple_id TEXT, spotify_id TEXT);
CREATE TABLE entries (song_id INTEGER, chart TEXT, start TEXT, end TEXT, rank INTEGER, size INTEGER,
                      PRIMARY KEY (chart, start, rank));
CREATE TABLE totals (song_id INTEGER, chart TEXT, weeks INTEGER, top10_weeks INTEGER, peak INTEGER,
                     peak_times INTEGER, peak_streams INTEGER, streams INTEGER, year INTEGER,
                     PRIMARY KEY (song_id, chart));
CREATE TABLE notes (text TEXT);
"""

SOURCES = {
    "spanishcharts": """
        INSERT INTO charts VALUES ('promusicae-singles', 'PROMUSICAE singles (spanishcharts.com)',
            'spain', 'week', 'spanishcharts.com');
        INSERT INTO songs (id, key, title, artist) VALUES
            (1, 'Pitbull feat. Ne-Yo|Give Me Everything', 'Give Me Everything', 'Pitbull feat. Ne-Yo'),
            (2, 'Aitana|Superestrella', 'Superestrella', 'Aitana'),
            (3, 'Alaska y Dinarama|A quién le importa', 'A quién le importa', 'Alaska y Dinarama');
        INSERT INTO entries VALUES
            (1, 'promusicae-singles', '2011-07-03', '2011-07-09', 1, 50),
            (1, 'promusicae-singles', '2011-07-10', '2011-07-16', 2, 50),
            (2, 'promusicae-singles', '2019-05-05', '2019-05-11', 1, 100),
            (2, 'promusicae-singles', '2019-05-12', '2019-05-18', 1, 100),
            (2, 'promusicae-singles', '2019-05-19', '2019-05-25', 1, 100),
            (2, 'promusicae-singles', '2019-05-26', '2019-06-01', 5, 100),
            (3, 'promusicae-singles', '2004-01-04', '2004-01-10', 3, 20);
    """,
    "los40": """
        INSERT INTO charts VALUES ('los40', 'Lista LOS40 (los40.com)', 'spain', 'week', 'los40.com'),
            ('los40-number-ones', 'Lista LOS40, number ones (los40.com)', 'spain', 'number_one',
             'los40.com');
        INSERT INTO songs (id, key, title, artist, youtube_id) VALUES
            (1, 'superestrella|aitana', 'superestrella', 'Aitana', 'abcdefghijk'),
            (2, 'black is black|los bravos', 'Black is black', 'Los Bravos', NULL);
        INSERT INTO entries VALUES
            (1, 'los40', '2019-05-04', '2019-05-10', 1, 40),
            (1, 'los40', '2019-05-11', '2019-05-17', 1, 40),
            (1, 'los40', '2019-05-18', '2019-05-24', 3, 40),
            (2, 'los40-number-ones', '1966-07-16', '1966-07-22', 1, 1);
    """,
    "kworb": """
        INSERT INTO charts VALUES ('spotify-spain', 'Spotify Spain weekly chart, totals (kworb.net)',
            'spain', 'totals', 'kworb.net');
        INSERT INTO songs (id, key, title, artist, spotify_id) VALUES
            (1, '1x', 'Superestrella', 'Aitana', '1x'),
            (2, '2x', 'Solo en Spotify', 'Nadie Conocido', '2x');
        INSERT INTO totals VALUES (1, 'spotify-spain', 30, 10, 1, 4, NULL, NULL, NULL),
            (2, 'spotify-spain', 12, 2, 6, 1, NULL, NULL, NULL);
    """,
    "apecat": """
        INSERT INTO charts VALUES ('apecat-llengua', 'APECAT / BMAT TOP 30, songs in Catalan',
            'catalan', 'month', 'apecat.com');
        INSERT INTO songs (id, key, title, artist) VALUES (1, 'tu fas|doctor prats', 'Tu Fas', 'Doctor Prats');
        INSERT INTO entries VALUES (1, 'apecat-llengua', '2018-10-12', '2018-11-08', 1, 30);
    """,
}


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    us = tmp_path / "library.sqlite"
    with sqlite3.connect(us) as connection:
        connection.executescript(SOURCE_SCHEMA + ROWS)
    with session() as db:
        import_library(db, read_source(us), seed=None)
    root = tmp_path / "regions"
    for source, rows in SOURCES.items():
        (root / source).mkdir(parents=True)
        with sqlite3.connect(root / source / f"{source}.sqlite") as connection:
            connection.executescript(SCHEMA + rows)
    return root


def run(folder: Path):  # type: ignore[no-untyped-def]
    with session() as db:
        return import_regions(db, read_all(folder))


def song_titled(db, title: str) -> Song:  # type: ignore[no-untyped-def]
    found = db.scalars(select(Song).where(Song.title == title, Song.scope == "public")).all()
    assert len(found) == 1, (title, len(found))
    return found[0]


def region_id(db, code: str) -> int:  # type: ignore[no-untyped-def]
    return int(db.scalar(select(Region.id).where(Region.code == code)))


def test_the_sources_become_public_rows_by_the_identity_rule(folder: Path) -> None:
    with session() as db:
        worldwide_before = {
            s.id: s.popularity for s in db.scalars(select(Song).where(Song.scope == "public"))
        }
    report = run(folder)
    # spanishcharts: Give Me Everything is the US song; two songs are new. los40 and kworb find
    # Superestrella, the song spanishcharts made; Black is black and the Spotify song are new.
    assert report.songs["spanishcharts"] == [1, 0, 2]
    assert report.songs["los40"] == [0, 1, 1]
    assert report.songs["kworb"] == [0, 1, 1]
    assert report.songs["apecat"] == [0, 0, 1]
    with session() as db:
        given = db.scalar(
            select(Song).where(
                Song.external_key == external_key("/singles/pitbull/give-me-everything")
            )
        )
        assert given is not None
        keys = set(db.scalars(select(SongKey.key).where(SongKey.song_id == given.id)))
        assert keys == {"spanishcharts.com:Pitbull feat. Ne-Yo|Give Me Everything"}
        spain, catalan = region_id(db, "spain"), region_id(db, "catalan")
        regions = set(
            db.scalars(select(SongRegion.region_id).where(SongRegion.song_id == given.id))
        )
        assert regions == {region_id(db, "worldwide"), spain}
        # The worldwide popularity is the US chart's only, as before.
        for song in db.scalars(select(Song).where(Song.id.in_(worldwide_before))):
            assert song.popularity == worldwide_before[song.id]
        # One Superestrella, with three keys, the year of its first week, Aitana as its artist.
        star = song_titled(db, "Superestrella")
        assert star.year == 2019
        assert (
            db.scalar(select(func.count()).select_from(SongKey).where(SongKey.song_id == star.id))
            == 2
        )
        # "Pitbull feat. Ne-Yo" made no artist; "Alaska y Dinarama" is one artist.
        names = set(db.scalars(select(ArtistName.name)))
        assert "Pitbull feat. Ne-Yo" not in names and "Alaska y Dinarama" in names
        importa = song_titled(db, "A quién le importa")
        credited = db.scalars(
            select(ArtistName.name)
            .join(SongArtist, SongArtist.artist_name_id == ArtistName.id)
            .where(SongArtist.song_id == importa.id)
        ).all()
        assert credited == ["Alaska y Dinarama"]
        assert (
            db.scalar(
                select(Artist.scope).join(ArtistName).where(ArtistName.name == "Alaska y Dinarama")
            )
            == "public"
        )
        # The Catalan song is only catalan.
        tu_fas = song_titled(db, "Tu Fas")
        assert set(
            db.scalars(select(SongRegion.region_id).where(SongRegion.song_id == tu_fas.id))
        ) == {catalan}


def test_the_weeks_the_weights_and_the_popularity_of_each_region(folder: Path) -> None:
    report = run(folder)
    with session() as db:
        tu_fas = song_titled(db, "Tu Fas")
        # A monthly list counts as the weeks it covers: 12 October to 8 November is four.
        assert (
            db.scalar(
                select(func.count()).select_from(ChartEntry).where(ChartEntry.song_id == tu_fas.id)
            )
            == 4
        )
        # The weight of Los 40's number ones is fitted on its full list: Superestrella's two weeks
        # at 1, scored alone with it, come closest to its score with all its weeks.
        weight = db.scalar(
            select(ChartSource.weight).where(
                ChartSource.name == "Lista LOS40, number ones (los40.com)"
            )
        )
        target = popularity.score([popularity.Week(1, 40)] * 2 + [popularity.Week(3, 40)])
        assert abs(popularity.score([popularity.Week(1, 1, weight)] * 2) - target) <= 0.5
        closest, fitted, _error = report.weights["Lista LOS40, number ones (los40.com)"]
        assert (closest, fitted) == (weight, 1)
        # No song of this small region is at 95 or more, so nothing is lowered; a month is 4 weeks.
        assert report.top_factor == {"spain": 1.0}
        assert report.month_weeks == 4
        expected = weight

        def value(title: str, code: str) -> tuple[float, str]:
            row = db.get(SongRegionPopularity, (song_titled(db, title).id, region_id(db, code)))
            assert row is not None, title
            return row.popularity, row.basis

        # Superestrella: the largest of its two charts' scores; Spotify's estimate is not used.
        star_spain = value("Superestrella", "spain")
        assert star_spain[1] == "weeks"
        assert star_spain[0] == max(
            popularity.score([popularity.Week(1)] * 3 + [popularity.Week(5)]),
            popularity.score([popularity.Week(1, 40)] * 2 + [popularity.Week(3, 40)]),
        )
        bravos = value("Black is black", "spain")
        assert bravos == (popularity.score([popularity.Week(1, 1, expected)]), "number_ones")
        assert value("Solo en Spotify", "spain")[1] == "estimated"
        assert value("Tu Fas", "catalan") == (
            popularity.score([popularity.Week(1, 30)] * 4),
            "weeks",
        )
        # A region's popularity of a decade counts only that region's charts.
        tens = popularity.song_scores(
            db,
            region="spain",
            start=__import__("datetime").date(2010, 1, 1),
            end=__import__("datetime").date(2019, 12, 31),
        )
        assert song_titled(db, "Superestrella").id in tens
        assert song_titled(db, "Tu Fas").id not in tens


def test_a_second_run_makes_nothing(folder: Path) -> None:
    run(folder)
    with session() as db:
        songs = db.scalar(select(func.count()).select_from(Song))
        artists = db.scalar(select(func.count()).select_from(Artist))
        weeks = db.scalar(select(func.count()).select_from(ChartEntry))
        song_titled(db, "Superestrella").title = "Superestrella (the master user's title)"
    report = run(folder)
    assert all(made == 0 for _, _, made in report.songs.values())
    assert report.artists_made == 0
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Song)) == songs
        assert db.scalar(select(func.count()).select_from(Artist)) == artists
        assert db.scalar(select(func.count()).select_from(ChartEntry)) == weeks
        song_titled(db, "Superestrella (the master user's title)")


def test_the_list_and_the_song_page_by_region(folder: Path) -> None:
    run(folder)
    catalogue.forget()
    with session() as db:
        spain = region_id(db, "spain")
        page = catalogue.songs_page(db, catalogue.SongFilter(region=spain))
        assert page.total == 5
        ordered = [score for _, score in page.rows]
        assert ordered == sorted(ordered, reverse=True)
        star = song_titled(db, "Superestrella")
        assert (
            dict((one.id, score) for one, score in page.rows)[star.id]
            == db.get(SongRegionPopularity, (star.id, spain)).popularity
        )
        # With no region, the worldwide popularity: a song only on Spanish charts has none
        # (None, shown "–"), and it sorts after every song with a value (the user, 2026-10-19).
        worldwide = catalogue.songs_page(db, catalogue.SongFilter(), limit=200).rows
        assert dict((one.id, score) for one, score in worldwide)[star.id] is None
        scores = [score for _, score in worldwide]
        assert all(score is None for score in scores[scores.index(None) :])
        facts = public.song_facts(db, star.id, 1)
        assert [(r, b) for r, _, b in facts.region_popularity] == [("Spain", "weeks")]
        assert {(c.name, c.region, c.size) for c in facts.charts} == {
            ("PROMUSICAE singles (spanishcharts.com)", "Spain", 100),
            ("Lista LOS40 (los40.com)", "Spain", 40),
        }


def test_the_compared_forms() -> None:
    assert artist_parts("Karol G / Nicki Minaj") == ["Karol G", "Nicki Minaj"]
    assert artist_parts("Pitbull feat. Ne-Yo") == ["Pitbull", "Ne-Yo"]
    assert artist_parts("Frank Sinatra;Nelson Riddle") == ["Frank Sinatra", "Nelson Riddle"]
    assert artist_parts("Alaska y Dinarama") == ["Alaska y Dinarama"]
    assert title_forms("Stronger (What Doesn't Kill You)") == {
        "stronger what doesnt kill you",
        "stronger",
    }
    assert "despacito" in title_forms("Despacito - Remix")
    assert title_forms("+") == {"+"}


def test_a_month_counts_for_fewer_weeks_when_the_top_would_be_flat() -> None:
    from datetime import date, timedelta

    from aitu_backend.library.regional_import import _month_weeks

    # One song at number 1 for twelve months: four weeks a month puts it near 100.
    months = [
        (
            1,
            7,
            date(2020, 1, 1) + timedelta(days=28 * m),
            date(2020, 1, 28) + timedelta(days=28 * m),
            1,
        )
        for m in range(12)
    ]
    assert popularity.score([popularity.Week(1, 30)] * 48) >= 95
    most = _month_weeks(months, {7: 30}, popularity.DEFAULT)
    assert most < 4
    assert popularity.score([popularity.Week(1, 30)] * 12 * most) < 95
    # A short run keeps the four weeks a month covers.
    assert _month_weeks(months[:1], {7: 30}, popularity.DEFAULT) == 4
