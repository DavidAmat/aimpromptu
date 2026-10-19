"""The signals of a song outside the charts (implementation 02, Phase 17;
``context/music-library/popularity.md`` section 6): the official channel rule, the reader of a
kworb page, the answers kept and forgotten after 30 days, the day's searches, and the collection
of a song's video and streams into ``song_signals``, with no network (the client's answers are
written in the test)."""

from __future__ import annotations

import json
import urllib.parse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest
from sqlalchemy import select

from aitu_backend.db.database import session
from aitu_backend.db.models import Region, Song, SongRegion, SongRegionPopularity, SongSignal
from aitu_backend.library import catalogue, inferred, popularity, signals
from tests.test_regional_import import folder, run, song_titled  # noqa: F401 - the fixture

PAGE = """<table class="addpos sortable"><tr><th>Song Title</th><th>Streams</th></tr>
<tr><td class="text"><div><a href="https://open.spotify.com/track/6habFhsOp2NvshLv26DqMb" target="_blank">Despacito</a></div></td><td>2,233,943,590</td><td>576,172</td></tr>
<tr><td class="text"><div>* <a href="https://open.spotify.com/track/1vnn" target="_blank">Despacito - Remix</a></div></td><td>1,942,927,424</td><td>275,897</td></tr>
<tr><td class="text"><div><a href="https://open.spotify.com/track/0mlA" target="_blank">&Eacute;chame La Culpa</a></div></td><td>1,119,337,042</td><td>189,909</td></tr>
</table>"""


def test_an_official_channel_is_the_artists_its_topic_its_vevo_or_a_labels() -> None:
    kind = signals.channel_kind
    assert kind("Luis Fonsi", ["Luis Fonsi"]) == "artist"
    assert kind("LuisFonsiVEVO", ["Luis Fonsi"]) == "vevo"
    assert kind("The Mamas & The Papas - Topic", ["The Mamas & The Papas"]) == "topic"
    assert kind("SimonGarfunkelVEVO", ["Simon & Garfunkel"]) == "vevo"
    assert kind("SouljaBoyTellemVEVO", ["Soulja Boy"]) == "vevo"
    assert kind("Flo Rida Videos", ["Flo Rida"]) == "artist"
    # A label's channel counts when the video names the artist and the song: not a cover.
    title = "Cabaret Pop - Juegos de amor (Video clip)"
    assert kind("Warner Music Spain", ["Cabaret Pop"], title, "Juegos de amor") == "label"
    cover = "A Day To Remember - Since U Been Gone (Official Video)"
    assert kind("ADayToRememberVEVO", ["Kelly Clarkson"], cover, "Since U Been Gone") is None
    # A fan, an archive, a TV show.
    assert kind("OscarOsR", ["The Mamas & The Papas"]) is None
    assert kind("U2Archive", ["U2"]) is None
    assert kind("Queen Fan Club", ["Queen"]) is None


def test_a_kworb_page_gives_each_track_and_its_streams() -> None:
    assert signals.kworb_rows(PAGE) == [
        ("Despacito", 2233943590),
        ("Despacito - Remix", 1942927424),
        ("Échame La Culpa", 1119337042),
    ]


class Offline(signals.Client):
    """A client whose network is a dict: an address's start -> (status, body)."""

    def __init__(self, answers: signals.Answers, pages: dict[str, tuple[int, str]]):
        super().__init__(answers, youtube_key="k", spotify=("id", "secret"), say=False)
        self.pages = pages
        self.urls: list[str] = []

    def _fetch(self, url, data=None, headers=None):  # type: ignore[no-untyped-def]
        self.urls.append(url)
        if "accounts.spotify.com" in url:
            return 200, json.dumps({"access_token": "t", "expires_in": 3600})
        if "/youtube/v3/videos?" in url:
            wanted = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)["id"][0].split(",")
            items = [
                json.loads(self.pages[f"video:{one}"][1])
                for one in wanted
                if f"video:{one}" in self.pages
            ]
            return 200, json.dumps({"items": items})
        for start, answer in self.pages.items():
            if url.startswith(start):
                return answer
        return 404, ""

    def wikidata_songs(self):  # type: ignore[no-untyped-def]
        return []

    def enderrock_videos(self):  # type: ignore[no-untyped-def]
        return []


def video(
    one: str, channel: str, views: int, title: str = "", published: str = "2019-05-01"
) -> tuple[int, str]:
    return 200, json.dumps(
        {
            "id": one,
            "snippet": {
                "title": title,
                "channelTitle": channel,
                "publishedAt": f"{published}T00:00:00Z",
            },
            "statistics": {"viewCount": str(views)},
        }
    )


def test_a_youtube_statistic_is_kept_30_days_then_read_again(tmp_path: Path) -> None:
    answers = signals.Answers(tmp_path / "answers.sqlite")
    client = Offline(answers, {"video:abcdefghijk": video("abcdefghijk", "AitanaVEVO", 1000)})
    assert client.videos(["abcdefghijk"])["abcdefghijk"].views == 1000
    client.videos(["abcdefghijk"])
    assert len(client.urls) == 1  # the second time from the answers
    old = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat(timespec="seconds")
    answers.connection.execute("UPDATE answers SET read_at = ?", (old,))
    client.pages["video:abcdefghijk"] = video("abcdefghijk", "AitanaVEVO", 2000)
    assert client.videos(["abcdefghijk"])["abcdefghijk"].views == 2000
    assert len(client.urls) == 2
    # Opening the answers again deletes a statistic older than 30 days.
    answers.connection.execute("UPDATE answers SET read_at = ?", (old,))
    answers.connection.commit()
    assert signals.Answers(tmp_path / "answers.sqlite").get("youtube:video:abcdefghijk") is None


def test_the_searches_of_the_day_are_counted_and_refused_after_100(tmp_path: Path) -> None:
    answers = signals.Answers(tmp_path / "answers.sqlite")
    for n in range(signals.SEARCHES_A_DAY):
        answers.put(f"youtube:search:song {n}", 200, json.dumps({"items": []}))
    assert answers.searches_today() == signals.SEARCHES_A_DAY
    client = Offline(answers, {})
    assert client.search("song 3") == []  # an answer kept is no search
    with pytest.raises(signals.OutOfQuota):
        client.search("another song")


def test_a_songs_video_and_streams_are_collected_and_stored(
    folder: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: F811
) -> None:
    run(folder)
    monkeypatch.setenv("MUSIC_LIBRARY_REGIONS_DIR", str(folder))
    answers = signals.Answers(tmp_path / "answers.sqlite")
    spotify = {"artists": {"items": [{"name": "Aitana", "id": "ait"}]}}
    client = Offline(
        answers,
        {
            # Los 40 links Superestrella to a fan's upload; the search finds the official one.
            "video:abcdefghijk": video(
                "abcdefghijk", "fan of aitana", 50, "Aitana - Superestrella"
            ),
            "https://www.googleapis.com/youtube/v3/search": (
                200,
                json.dumps({"items": [{"id": {"videoId": "OFFICIAL001"}}]}),
            ),
            "video:OFFICIAL001": video(
                "OFFICIAL001", "AitanaVEVO", 9_000_000, "Aitana - SUPERESTRELLA"
            ),
            "https://api.spotify.com/v1/search": (200, json.dumps(spotify)),
            "https://kworb.net/spotify/artist/ait_songs.html": (
                200,
                PAGE.replace("Despacito", "Superestrella"),
            ),
        },
    )
    with session() as db:
        song = song_titled(db, "Superestrella")
        found = signals.collect(db, client, [song.id])
        one = found[song.id]
        assert one.video is not None and one.video.id == "OFFICIAL001"
        assert (one.found_by, one.channel_kind) == ("search", "vevo")
        assert [v.channel for v in one.unofficial] == ["fan of aitana"]
        assert one.streams == 2233943590  # the most streamed track of the same title
        assert inferred.store_signals(db, found) == 1
        stored = db.get(SongSignal, song.id)
        assert stored is not None and stored.views == 9_000_000 and stored.channel == "vevo"
        rows = inferred.sample_rows(db)
    assert [(r.region, r.views, r.streams) for r in rows if r.song_id == song.id] == [
        ("spain", 9_000_000, 2233943590)
    ]
    # Asked again: every answer is kept, nothing is asked twice.
    asked = len(client.urls)
    with session() as db:
        signals.collect(db, client, [song.id])
    assert len(client.urls) == asked


def test_an_inferred_value_is_kept_by_the_import_until_a_chart_gives_one(
    folder: Path,  # noqa: F811 - the fixture
) -> None:
    run(folder)
    with session() as db:
        catalan = int(db.scalar(select(Region.id).where(Region.code == "catalan")))
        tu_fas = song_titled(db, "Tu Fas").id
        other = song_titled(db, "Black is black").id
        db.add(SongSignal(song_id=other, read_on=date.today(), views=10))
        for song_id in (tu_fas, other):
            db.merge(
                SongRegionPopularity(
                    song_id=song_id,
                    region_id=catalan,
                    popularity=12.0,
                    basis="inferred",
                    inferred_on=date.today(),
                )
            )
    run(folder)
    with session() as db:
        kept = {
            (row.song_id, row.basis)
            for row in db.scalars(
                select(SongRegionPopularity).where(SongRegionPopularity.region_id == catalan)
            )
        }
    assert (tu_fas, "weeks") in kept  # the chart replaced the inferred value
    assert (other, "inferred") in kept


def test_a_song_on_no_chart_is_listed_by_its_inferred_worldwide_value(
    folder: Path,  # noqa: F811 - the fixture
) -> None:
    run(folder)
    with session() as db:
        song = Song(scope="public", title="Nueva canción", year=2024)
        db.add(song)
        db.flush()
        worldwide = int(db.scalar(select(Region.id).where(Region.code == "worldwide")))
        db.add(
            SongRegionPopularity(
                song_id=song.id, region_id=worldwide, popularity=41.5, basis="inferred"
            )
        )
        assert not db.scalars(select(SongRegion).where(SongRegion.song_id == song.id)).all()
        song_id = song.id
    catalogue.forget()
    with session() as db:
        page = catalogue.songs_page(db, catalogue.SongFilter(query="nueva cancion"))
    assert [(one.id, value) for one, value in page.rows] == [(song_id, 41.5)]


def test_a_relation_is_measured_on_the_songs_left_out() -> None:
    rng = np.random.default_rng(1)
    rows = []
    for n in range(400):
        views = int(10 ** rng.uniform(3, 9))
        value = float(np.clip((np.log10(views) - 3) * 16 + rng.normal(0, 3), 0, 100))
        region = ("worldwide", "spain", "catalan")[n % 3]
        rows.append(
            inferred.Row(n, region, value, "weeks", 2015, views, date(2016, 1, 1), date(2026, 1, 1))
        )
    results = {one["key"]: one for one in inferred.evaluate(rows, inferred.CANDIDATES[:2])}
    assert results["views"]["error"] < 4 < results["median"]["error"]
    assert results["views"]["order"] > 0.9


def test_a_song_on_no_chart_gets_an_inferred_value_until_a_chart_lists_it(
    folder: Path, tmp_path: Path  # noqa: F811 - the fixture
) -> None:
    run(folder)
    today = date(2026, 10, 19)
    with session() as db:
        regions = dict(db.execute(select(Region.code, Region.id)).all())
        catalan_song = Song(scope="public", title="Cançó nova", year=2021)
        lonely = Song(scope="public", title="Proposed by request", year=2024)
        db.add_all([catalan_song, lonely])
        db.flush()
        db.add(SongRegion(song_id=catalan_song.id, region_id=regions["catalan"]))
        for song, views in ((catalan_song, 200_000), (lonely, 5_000_000)):
            db.add(
                SongSignal(
                    song_id=song.id,
                    video_id=f"VIDEO{song.id:06d}",
                    found_by="search",
                    channel="artist",
                    published_on=date(2021, 3, 1),
                    views=views,
                    read_on=today,
                )
            )
        ids = (catalan_song.id, lonely.id)
    client = Offline(signals.Answers(tmp_path / "answers.sqlite"), {})
    with session() as db:
        assert (ids[0], "catalan") in inferred.targets(db)
        assert (ids[1], "worldwide") in inferred.targets(db)
        report = inferred.infer(db, client, today=today)
    assert client.urls == []  # fresh signals are not read again
    with session() as db:
        values = {
            (row.song_id, row.region_id): (row.popularity, row.basis, row.inferred_on)
            for row in db.scalars(
                select(SongRegionPopularity).where(SongRegionPopularity.song_id.in_(ids))
            )
        }
    expected = popularity.inferred(
        region="catalan",
        year=2021,
        views=200_000,
        published=date(2021, 3, 1),
        read_on=today,
        channel="artist",
        streams=None,
    )
    assert values[(ids[0], regions["catalan"])] == (expected, "inferred", today)
    assert values[(ids[1], regions["worldwide"])][1] == "inferred"
    assert report.written["catalan"] >= 1 and report.written["worldwide"] >= 1

    # 40 days later the views are read again (one video is gone), and the values follow.
    later = today + timedelta(days=40)
    client.pages[f"video:VIDEO{ids[0]:06d}"] = video(f"VIDEO{ids[0]:06d}", "x", 900_000)
    with session() as db:
        report = inferred.refresh(db, client, today=later)
        assert (report.refreshed, report.gone) == (1, 1)
        rows = {
            row.song_id: row.popularity
            for row in db.scalars(
                select(SongRegionPopularity).where(SongRegionPopularity.song_id.in_(ids))
            )
        }
    assert rows[ids[0]] > expected and ids[1] not in rows

    # A chart lists the lonely song now: its worldwide inferred value goes.
    with session() as db:
        db.add(SongRegion(song_id=ids[1], region_id=regions["spain"]))
        db.add(
            SongRegionPopularity(
                song_id=ids[1], region_id=regions["spain"], popularity=50.0, basis="weeks"
            )
        )
    with session() as db:
        inferred.infer(db, client, today=later)
        assert db.get(SongRegionPopularity, (ids[1], regions["worldwide"])) is None


def test_the_formula_gives_what_its_fit_gives() -> None:
    rng = np.random.default_rng(3)
    rows = []
    for n in range(600):
        views = int(10 ** rng.uniform(3, 9))
        streams = int(10 ** rng.uniform(5, 9)) if n % 2 else None
        year = int(rng.integers(1970, 2026)) if n % 7 else None
        published = date(int(rng.integers(2007, 2026)), 6, 1)
        value = float(np.clip(10 * np.log10(views) - 30 + rng.normal(0, 8), 0, 100))
        rows.append(
            inferred.Row(
                n,
                ("worldwide", "spain", "catalan")[n % 3],
                value,
                "weeks",
                year,
                views,
                published,
                date(2026, 10, 19),
                streams,
                ("artist", "vevo", "topic", "label")[n % 4],
            )
        )
    weights = inferred.chosen_weights(rows)
    fitted = next(c for c in inferred.CANDIDATES if c.key == inferred.CHOSEN).fit(rows)(rows)
    formula = [
        popularity.inferred(
            region=r.region,
            year=r.year,
            views=r.views,
            published=r.published,
            read_on=r.read_on,
            channel=r.channel,
            streams=r.streams,
            weights=weights,
        )
        for r in rows
    ]
    assert float(np.abs(np.array(formula) - fitted).max()) < 0.2
