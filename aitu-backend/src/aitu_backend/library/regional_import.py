"""The import of the `spain` and `catalan` sources into the public rows (implementation 02, Phase 16;
``context/music-library/regional-sources.md``).

It reads the databases ``scripts/music-library-regions/build.py`` writes, one per source, in
``data/music-library-regions/<source>/<source>.sqlite`` next to the repository, read only:

* ``spanishcharts``: the weekly Spanish chart (PROMUSICAE) from 2001-12-30, `spain`;
* ``los40``: the Lista LOS40, its number ones from 1966 and its 40 places from 2004, `spain`;
* ``kworb``: the totals of each song of Spotify Spain's weekly chart from 2013, `spain`;
* ``wikipedia``: the weekly number ones of Spain 1959 to 2001 and the weekly top 10 of 1982 to
  1996, `spain`; the Catalan songs most played on Spotify, `catalan`;
* ``apecat``: the two monthly TOP 30 of APECAT / BMAT from 2018, `catalan`.

**The identity rule of Phase 12.** A song of a source is the public song that already has its key
(``external_key`` or a row of ``song_keys``); else the public song of the same title (compared
without case, accents, punctuation or a closing ``(...)``) that credits one of its artists; else a
new public song, with its artists found by name or made. Each source keeps its own key, so a
second run finds every row again and makes nothing. A title, a name or a link is never written
again; only an empty year is filled.

**The chart weeks belong to the sources**: the weeks of their charts are written again on every
run. A monthly list counts as the weeks it covers (four), or fewer when its top would be flat
(Q-6: at most 1 % of its songs at 95 or more); a list of number ones only counts each week at
number 1 with its chart's weight, fitted where the full lists exist (the weekly top 10 of 1982 to
1996 for the sales list, the 40 places from 2004 for Los 40) so that a number one scored from its
weeks at the top alone comes closest to its score on the full list; then lowered together, as little
as needed, so that at most 1 % of the region's songs score 95 or more (Q-6's spread top). Then each song's
popularity in each region is written to ``song_region_popularity``: the largest of its charts'
scores; a song no chart lists gets an estimate from Spotify's totals.

::

    python -m aitu_backend.library.regional_import [--folder DIR] [--database DIR]
"""

from __future__ import annotations

import argparse
import math
import os
import re
import sqlite3
import statistics
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.orm import Session as DbSession

from aitu_backend.db.models import (
    Artist,
    ArtistKey,
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
from aitu_backend.library import popularity
from aitu_backend.library.public_import import plain

__all__ = ["SOURCES", "Report", "default_folder", "import_regions", "read_source"]

#: Read in this order: the richest first, so the later sources find its songs.
SOURCES = ("spanishcharts", "los40", "kworb", "wikipedia", "apecat")
#: The site each source's keys start with.
SITES = {
    "spanishcharts": "spanishcharts.com",
    "los40": "los40.com",
    "kworb": "kworb.net",
    "wikipedia": "wikipedia",
    "apecat": "apecat.com",
}
#: A chart of number ones only, and the full chart its weight is fitted on: the sales list's own
#: weekly top 10 of 1982 to 1996, and Los 40's full lists from 2004.
NUMBER_ONES = {
    "wikipedia-spain-number-ones": "wikipedia-spain-top10",
    "los40-number-ones": "los40",
}
#: The source of totals whose estimate is fitted on the full chart of the same years.
ESTIMATED = {"spotify-spain": "promusicae-singles"}

_REPOSITORY = Path(__file__).resolve().parents[4]
_FEATURING = re.compile(r"\s+(?:feat\.?|ft\.?|featuring|con|amb|with)\s+", re.IGNORECASE)
_LIST = re.compile(r"\s*(?:;|/|,)\s*")
_AND = re.compile(r"\s+(?:&|y|i|and|x|vs\.?)\s+", re.IGNORECASE)


def default_folder() -> Path:
    """``MUSIC_LIBRARY_REGIONS_DIR``, else ``data/music-library-regions`` beside the repository."""
    folder = os.environ.get("MUSIC_LIBRARY_REGIONS_DIR")
    return Path(folder) if folder else _REPOSITORY.parent / "data" / "music-library-regions"


# ---------------------------------------------------------------------- the sources


@dataclass
class SourceChart:
    code: str
    name: str
    region: str
    period: str  # week, month, number_one, totals
    size: int = 1


@dataclass
class SourceSong:
    key: str
    title: str
    artist: str
    #: (chart code, first day, last day, place)
    entries: list[tuple[str, date, date, int]] = field(default_factory=list)
    #: chart code: (weeks, top 10 weeks, peak, weeks at the peak, year)
    totals: dict[str, tuple[int | None, int | None, int | None, int | None, int | None]] = field(
        default_factory=dict
    )

    def first_year(self) -> int | None:
        years = [start.year for _, start, _, _ in self.entries]
        years += [t[4] for t in self.totals.values() if t[4]]
        return min(years) if years else None


def read_source(path: Path, source: str) -> tuple[list[SourceChart], list[SourceSong]]:
    """One source database, read only (``mode=ro&immutable=1``: nothing is written beside it)."""
    connection = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    try:
        charts = [
            SourceChart(code, name, region, period)
            for code, name, region, period in connection.execute(
                "SELECT code, name, region, period FROM charts ORDER BY code"
            )
        ]
        sizes = dict(
            connection.execute("SELECT chart, MAX(size) FROM entries GROUP BY chart").fetchall()
        )
        for chart in charts:
            chart.size = int(sizes.get(chart.code) or 1)
        songs = {
            song_id: SourceSong(f"{SITES[source]}:{key}", title, artist)
            for song_id, key, title, artist in connection.execute(
                "SELECT id, key, title, artist FROM songs"
            )
        }
        for song_id, chart, start, end, rank in connection.execute(
            "SELECT song_id, chart, start, end, rank FROM entries"
        ):
            songs[song_id].entries.append(
                (chart, date.fromisoformat(start), date.fromisoformat(end), int(rank))
            )
        for song_id, chart, weeks, top10, peak, times, year in connection.execute(
            "SELECT song_id, chart, weeks, top10_weeks, peak, peak_times, year FROM totals"
        ):
            songs[song_id].totals[chart] = (weeks, top10, peak, times, year)
    finally:
        connection.close()
    return charts, list(songs.values())


# ---------------------------------------------------------------------- matching


def title_forms(title: str) -> set[str]:
    """A title as compared: whole, without a closing ``(...)`` / ``[...]``, without a ``feat.``
    part, without a `` - Remix`` ending."""
    forms = {plain(title)}
    for shorter in (
        re.sub(r"\s*[(\[][^)\]]*[)\]]\s*$", "", title),
        _FEATURING.split(title)[0],
        re.sub(r"\s+-\s+.*$", "", title),
    ):
        if shorter.strip() and shorter != title:
            forms.add(plain(shorter))
    forms.discard("")
    return forms or {title.strip().casefold()}  # a title of symbols only: "+", "÷ (Dividido)"


def artist_parts(printed: str) -> list[str]:
    """The artists of a printed credit, split on the separators no band name uses (``;``, ``/``,
    ``,``, ``feat.``, ``con``, ``amb``): "Karol G / Nicki Minaj", "Pitbull feat. Ne-Yo"."""
    parts: list[str] = []
    for piece in _LIST.split(printed):
        for name in _FEATURING.split(piece):
            name = name.strip()
            if name and name not in parts:
                parts.append(name)
    return parts


def matching_names(printed: str) -> set[str]:
    """Every compared form a credit may match: the whole, its parts, and the parts of an ``&`` or
    ``y`` ("J Balvin & Bad Bunny"); only used to find, never to make, an artist."""
    found = {plain(printed)}
    for part in artist_parts(printed):
        found.add(plain(part))
        found.update(plain(one) for one in _AND.split(part))
    found.discard("")
    return found


class Index:
    """The public songs and artists, as the identity rule looks them up; updated as rows are made."""

    def __init__(self, db: DbSession):
        self.by_key: dict[str, int] = {}
        for key, song_id in db.execute(
            select(Song.external_key, Song.id).where(
                Song.scope == "public", Song.external_key.is_not(None)
            )
        ):
            self.by_key[str(key)] = int(song_id)
        for key, song_id in db.execute(select(SongKey.key, SongKey.song_id)):
            self.by_key[str(key)] = int(song_id)
        self.titles: dict[str, set[int]] = defaultdict(set)
        self.popularity: dict[int, float] = {}
        self.year: dict[int, int | None] = {}
        for song_id, title, value, year in db.execute(
            select(Song.id, Song.title, Song.popularity, Song.year).where(Song.scope == "public")
        ):
            for form in title_forms(title):
                self.titles[form].add(int(song_id))
            self.popularity[int(song_id)] = float(value or 0.0)
            self.year[int(song_id)] = year
        # Every name of every public artist: name -> (artist, the name's own id)
        self.names: dict[str, tuple[int, int]] = {}
        names_of: dict[int, set[str]] = defaultdict(set)
        for name_id, artist_id, name, default in db.execute(
            select(ArtistName.id, ArtistName.artist_id, ArtistName.name, ArtistName.is_default)
            .join(Artist, Artist.id == ArtistName.artist_id)
            .where(Artist.scope == "public")
            .order_by(ArtistName.is_default.desc(), ArtistName.id)
        ):
            self.names.setdefault(plain(name), (int(artist_id), int(name_id)))
            names_of[int(artist_id)].add(plain(name))
        self.credited: dict[int, set[str]] = defaultdict(set)
        for song_id, artist_id in db.execute(
            select(SongArtist.song_id, ArtistName.artist_id)
            .join(ArtistName, ArtistName.id == SongArtist.artist_name_id)
            .join(Song, Song.id == SongArtist.song_id)
            .where(Song.scope == "public")
        ):
            self.credited[int(song_id)] |= names_of[int(artist_id)]
        self.artist_keys: dict[str, int] = dict(
            db.execute(select(ArtistKey.key, ArtistKey.artist_id)).all()
        )

    def find(self, song: SourceSong) -> int | None:
        if song.key in self.by_key:
            return self.by_key[song.key]
        candidates: set[int] = set()
        for form in title_forms(song.title):
            candidates |= self.titles.get(form, set())
        wanted = matching_names(song.artist)
        credited = [one for one in candidates if self.credited.get(one, set()) & wanted]
        if not credited:
            return None
        return max(credited, key=lambda one: (self.popularity.get(one, 0.0), -one))

    def add_song(self, song_id: int, song: SourceSong, credited: set[str]) -> None:
        self.by_key[song.key] = song_id
        for form in title_forms(song.title):
            self.titles[form].add(song_id)
        self.credited[song_id] |= credited
        self.popularity[song_id] = 0.0


# ---------------------------------------------------------------------- the import


@dataclass
class Report:
    #: source: [matched to a song of the US chart or the seed list, matched to a song an earlier
    #: regional source made, made]
    songs: dict[str, list[int]] = field(default_factory=dict)
    artists_made: int = 0
    #: chart name: weeks written
    weeks: dict[str, int] = field(default_factory=dict)
    #: number-ones chart: its closest weight, the songs it was fitted on, the mean difference
    weights: dict[str, tuple[float, int, float]] = field(default_factory=dict)
    #: region: the factor its number-ones weights were lowered by, for a spread top
    top_factor: dict[str, float] = field(default_factory=dict)
    #: the weeks a month of a monthly list counts for
    month_weeks: int | None = None
    #: Spotify estimate: the factor, the songs it was fitted on, the mean error in points
    estimate: tuple[float, int, float] | None = None
    #: region: (songs with the region, songs with a popularity, by basis)
    regions: dict[str, tuple[int, int, dict[str, int]]] = field(default_factory=dict)
    seconds: float = 0.0

    def lines(self) -> list[str]:
        out = []
        for source, (old, earlier, made) in self.songs.items():
            out.append(
                f"{source}: {old} found among the songs already there, {earlier} among the"
                f" regional songs of an earlier source, {made} made"
            )
        out.append(f"artists made: {self.artists_made}")
        out += [f"chart weeks: {name}: {count}" for name, count in self.weeks.items()]
        out += [
            f"closest weight of {name}: {w:.2f} (fitted on {n} number ones, mean difference {e:.1f} points)"
            for name, (w, n, e) in self.weights.items()
        ]
        out += [
            f"number-ones weights of {r} lowered by {f:.2f} for a spread top"
            for r, f in self.top_factor.items()
        ]
        if self.month_weeks is not None:
            out.append(f"a month of a monthly list counts as {self.month_weeks} weeks")
        if self.estimate:
            k, n, err = self.estimate
            out.append(
                f"Spotify estimate: factor {k:.2f}, fitted on {n} songs, mean error {err:.1f} points"
            )
        for region, (songs, valued, bases) in self.regions.items():
            out.append(f"{region}: {songs} songs, {valued} with a popularity {dict(bases)}")
        out.append(f"time: {self.seconds:.1f} s")
        return out


def _weeks(start: date, end: date, most: int | None = None) -> list[date]:
    """The weeks a list stands for: one a week, a month as about four (or ``most``)."""
    count = max(1, round(((end - start).days + 1) / 7))
    return [start + timedelta(days=7 * k) for k in range(min(count, most or count))]


def _month_weeks(
    monthly: list[tuple[int, int, date, date, int]],
    size_of: dict[int, int],
    weights: popularity.Weights,
) -> int:
    """How many weeks a month of a monthly list counts for: 4 (the weeks it covers), or fewer, the
    most that keeps at most :data:`TOP_SHARE` of its songs at 95 or more (Q-6's spread top). A
    radio's monthly list keeps a song for many months, so four weeks a month saturates its top."""
    for most in (4, 3, 2, 1):
        weeks: dict[tuple[int, int], list[popularity.Week]] = defaultdict(list)
        for song_id, chart_id, start, end, rank in monthly:
            weeks[(song_id, chart_id)] += [popularity.Week(rank, size_of[chart_id])] * len(
                _weeks(start, end, most)
            )
        best: dict[int, float] = {}
        for (song_id, _chart), found in weeks.items():
            best[song_id] = max(popularity.score(found, weights), best.get(song_id, 0.0))
        if sum(1 for v in best.values() if v >= 95) <= TOP_SHARE * len(best):
            return most
    return 1


def _region_ids(db: DbSession) -> dict[str, int]:
    return {str(code): int(i) for i, code in db.execute(select(Region.id, Region.code))}


def _chart_ids(
    db: DbSession, charts: Iterable[SourceChart], regions: dict[str, int]
) -> dict[str, int]:
    """A ``chart_sources`` row per chart with places; made once, its size kept current. A weight the
    master user changed is kept, except the measured weight of a number-ones chart."""
    ids = {}
    for chart in charts:
        if chart.period == "totals":
            continue
        found = db.scalar(select(ChartSource).where(ChartSource.name == chart.name))
        if found is None:
            found = ChartSource(
                name=chart.name, region_id=regions[chart.region], size=chart.size, weight=1.0
            )
            db.add(found)
            db.flush()
        else:
            found.size = max(found.size, chart.size)
        ids[chart.code] = int(found.id)
    return ids


def _artist_names(
    db: DbSession, index: Index, printed: str, source: str, report: Report
) -> list[int]:
    """The artist names a new song points at: each part found by name, or made."""
    whole = plain(printed)
    if whole in index.names:
        return [index.names[whole][1]]
    parts = artist_parts(printed)
    # "J Balvin & Bad Bunny": split on "&" only when every part is a known artist.
    finer: list[str] = []
    for part in parts:
        pieces = _AND.split(part)
        known = len(pieces) > 1 and all(plain(p) in index.names for p in pieces)
        finer.extend(pieces if known else [part])
    name_ids: list[int] = []
    for part in finer:
        compared = plain(part)
        if not compared:
            continue
        found = index.names.get(compared)
        key = f"{SITES[source]}:artist:{compared}"
        if found is None and key in index.artist_keys:
            artist_id = index.artist_keys[key]
            name_id = db.scalar(
                select(ArtistName.id).where(
                    ArtistName.artist_id == artist_id, ArtistName.is_default.is_(True)
                )
            )
            found = (artist_id, int(name_id)) if name_id is not None else None
        if found is None:
            artist = Artist(scope="public", external_key=key)
            db.add(artist)
            db.flush()
            name = ArtistName(artist_id=artist.id, name=part.strip(), is_default=True)
            db.add(name)
            db.flush()
            found = (int(artist.id), int(name.id))
            index.names[compared] = found
            index.artist_keys[key] = found[0]
            report.artists_made += 1
        if found[1] not in name_ids:
            name_ids.append(found[1])
    return name_ids


def _number_one_weight(
    entries: dict[tuple[int, int, date], int], chart_id: int, weights: popularity.Weights
) -> tuple[float, int, float]:
    """The weight of a list of number ones only, fitted on the full list ``chart_id`` as the
    Spotify estimate is: the weight that brings a number one's score from its weeks at number 1
    alone closest to its score on the full list. Returns the weight, the songs it was fitted on
    and the mean difference in points."""
    full: dict[int, list[popularity.Week]] = defaultdict(list)
    at_one: dict[int, int] = defaultdict(int)
    for (song_id, chart, _week), rank in entries.items():
        if chart == chart_id:
            full[song_id].append(popularity.Week(rank))
            if rank == 1:
                at_one[song_id] += 1
    if not at_one:
        return 1.0, 0, 0.0
    target = {song: popularity.score(full[song], weights) for song in at_one}
    fits = []
    for step in range(10, 801, 5):  # 0.10 to 8.00
        k = step / 100
        scored = {
            n: popularity.score([popularity.Week(1, 1, k)] * n, weights)
            for n in set(at_one.values())
        }
        fits.append(
            (round(statistics.fmean(abs(scored[at_one[s]] - target[s]) for s in at_one), 3), k)
        )
    error, k = min(fits)
    return k, len(at_one), error


#: Q-6's criterion of a spread top: at most this share of a region's songs at 95 or more.
TOP_SHARE = 0.01


def _spread_top(
    db: DbSession, region: str, ones: dict[int, float], weights: popularity.Weights
) -> float:
    """The factor (1.0, 0.95, ...) the number-ones weights of ``region`` are lowered by together,
    the least that keeps at most :data:`TOP_SHARE` of the region's songs at 95 or more.

    The number ones of the 60s and 70s held the top three or four weeks, against one or two since
    the full lists, so the closest weights put many of them at 100."""
    others: dict[int, float] = {}
    at_one: dict[int, dict[int, int]] = defaultdict(dict)
    for (song_id, chart_id), value in popularity.chart_scores(db, region, weights).items():
        if chart_id not in ones:
            others[song_id] = max(value, others.get(song_id, 0.0))
    for song_id, chart_id, count in db.execute(
        select(ChartEntry.song_id, ChartEntry.chart_source_id, func.count())
        .where(ChartEntry.chart_source_id.in_(ones), ChartEntry.rank == 1)
        .group_by(ChartEntry.song_id, ChartEntry.chart_source_id)
    ):
        at_one[chart_id][song_id] = int(count)
    factor = 1.0
    while factor > 0.05:
        best = dict(others)
        for chart_id, counts in at_one.items():
            for song_id, n in counts.items():
                value = popularity.score(
                    [popularity.Week(1, 1, ones[chart_id] * factor)] * n, weights
                )
                best[song_id] = max(value, best.get(song_id, 0.0))
        if not best or sum(1 for v in best.values() if v >= 95) <= TOP_SHARE * len(best):
            return factor
        factor = round(factor - 0.05, 2)
    return factor


def _from_totals(
    weeks: int, top10: int, peak: int, times: int, weights: popularity.Weights
) -> tuple[float, float]:
    """The points a song of a top 200 has, from its totals only: its weeks at the peak at the peak,
    its other top 10 weeks spread over the places below the peak, its other weeks over 11 to 200;
    and its peak's share. (``points`` is zero below place 100.)"""

    def mean(first: int, last: int) -> float:
        places = range(max(first, 1), last + 1)
        return (
            sum(popularity.points(r, 200, weights) for r in places) / len(places) if places else 0.0
        )

    times = min(times or 1, weeks)
    top = max(0, min(top10, weeks) - times) if peak <= 10 else 0
    rest = max(0, weeks - times - top)
    total = times * popularity.points(peak, 200, weights)
    total += top * mean(peak + 1, 10)
    total += rest * mean(max(11, peak + 1), 200)
    share = max(0.0, (101 - peak) / 100) if peak <= 100 else 0.0
    return total, share


def _p(total: float, share: float, weights: popularity.Weights) -> float:
    return round(
        100.0
        * (
            weights.sum_weight * (1.0 - math.exp(-total / weights.saturation))
            + weights.peak_weight * share**weights.peak_power
        ),
        1,
    )


def import_regions(
    db: DbSession,
    sources: list[tuple[str, list[SourceChart], list[SourceSong]]],
    weights: popularity.Weights = popularity.DEFAULT,
) -> Report:
    """Write the regional sources into the public rows of ``db`` (one transaction: the caller
    commits)."""
    started = time.monotonic()
    report = Report()
    regions = _region_ids(db)
    index = Index(db)
    before = set(index.popularity)
    charts = {chart.code: chart for _, found, _ in sources for chart in found}
    chart_ids = _chart_ids(db, charts.values(), regions)
    have_region = {
        (int(s), int(r)) for s, r in db.execute(select(SongRegion.song_id, SongRegion.region_id))
    }
    have_key = set(index.by_key)
    made_here: set[int] = set()
    entries: dict[tuple[int, int, date], int] = {}
    monthly: list[tuple[int, int, date, date, int]] = []
    totals: dict[str, dict[int, tuple]] = defaultdict(dict)
    new_regions: list[dict] = []
    new_keys: list[dict] = []
    years: dict[int, int] = {}

    for source, _charts, songs in sources:
        counts = [0, 0, 0]
        for song in songs:
            song_id = index.find(song)
            if song_id is None:
                row = Song(
                    scope="public",
                    external_key=song.key,
                    title=song.title.strip(),
                    year=song.first_year(),
                    popularity=0.0,
                )
                db.add(row)
                db.flush()
                song_id = int(row.id)
                names = _artist_names(db, index, song.artist, source, report)
                for position, name_id in enumerate(names):
                    db.add(SongArtist(song_id=song_id, artist_name_id=name_id, position=position))
                index.add_song(song_id, song, matching_names(song.artist))
                made_here.add(song_id)
                counts[2] += 1
            else:
                counts[0 if song_id in before else 1] += 1
                if song.key not in have_key:
                    index.by_key[song.key] = song_id
                    new_keys.append({"key": song.key, "song_id": song_id})
                year = song.first_year()
                if year and index.year.get(song_id) is None:
                    years[song_id] = min(year, years.get(song_id, year))
            have_key.add(song.key)
            for region in {charts[code].region for code, *_ in song.entries} | {
                charts[code].region for code in song.totals
            }:
                pair = (song_id, regions[region])
                if pair not in have_region:
                    have_region.add(pair)
                    new_regions.append({"song_id": song_id, "region_id": regions[region]})
            for code, start, end, rank in song.entries:
                if charts[code].period == "month":
                    monthly.append((song_id, chart_ids[code], start, end, rank))
                    continue
                for week in _weeks(start, end):
                    key = (song_id, chart_ids[code], week)
                    entries[key] = min(rank, entries.get(key, rank))
            for code, values in song.totals.items():
                totals[code][song_id] = values
        report.songs[source] = counts

    if monthly:
        report.month_weeks = _month_weeks(
            monthly, {chart_ids[c]: charts[c].size for c in chart_ids}, weights
        )
        for song_id, chart_id, start, end, rank in monthly:
            for week in _weeks(start, end, report.month_weeks):
                key = (song_id, chart_id, week)
                entries[key] = min(rank, entries.get(key, rank))

    db.flush()
    if new_keys:
        db.execute(insert(SongKey), new_keys)
    if new_regions:
        db.execute(insert(SongRegion), new_regions)
    if years:
        db.execute(update(Song), [{"id": s, "year": y} for s, y in years.items()])

    # The weeks belong to the sources: written again.
    db.execute(delete(ChartEntry).where(ChartEntry.chart_source_id.in_(chart_ids.values())))
    if entries:
        db.execute(
            insert(ChartEntry),
            [
                {"song_id": s, "chart_source_id": c, "week": w, "rank": r}
                for (s, c, w), r in entries.items()
            ],
        )
    names_by_id = {chart_ids[code]: charts[code].name for code in chart_ids}
    counted: dict[int, int] = defaultdict(int)
    for _s, chart_id, _w in entries:
        counted[chart_id] += 1
    report.weeks = {names_by_id[c]: n for c, n in sorted(counted.items())}

    fitted_weights: dict[str, dict[int, float]] = defaultdict(dict)
    for ones, full in NUMBER_ONES.items():
        if ones in chart_ids and full in chart_ids:
            weight, fitted, error = _number_one_weight(entries, chart_ids[full], weights)
            fitted_weights[charts[ones].region][chart_ids[ones]] = weight
            report.weights[charts[ones].name] = (weight, fitted, error)
    db.flush()
    for region, ones_of in fitted_weights.items():
        factor = _spread_top(db, region, ones_of, weights)
        report.top_factor[region] = factor
        for chart_id, weight in ones_of.items():
            db.execute(
                update(ChartSource)
                .where(ChartSource.id == chart_id)
                .values(weight=round(weight * factor, 2))
            )
    db.flush()

    _store_regions(db, report, regions, chart_ids, charts, totals, weights)
    report.seconds = time.monotonic() - started
    return report


def _store_regions(
    db: DbSession,
    report: Report,
    regions: dict[str, int],
    chart_ids: dict[str, int],
    charts: dict[str, SourceChart],
    totals: dict[str, dict[int, tuple]],
    weights: popularity.Weights,
) -> None:
    kind = {chart_ids[code]: charts[code].period for code in chart_ids}
    regional = [code for code in regions if code != popularity.WORLDWIDE]
    db.execute(
        delete(SongRegionPopularity).where(
            SongRegionPopularity.region_id.in_([regions[c] for c in regional])
        )
    )
    for region in regional:
        best: dict[int, tuple[float, str, int | None]] = {}
        scored = popularity.chart_scores(db, region, weights)
        for (song_id, chart_id), value in scored.items():
            basis = "number_ones" if kind.get(chart_id) == "number_one" else "weeks"
            if value > best.get(song_id, (-1.0,))[0]:
                best[song_id] = (value, basis, chart_id)
        for code, full in ESTIMATED.items():
            if code not in totals or charts[code].region != region or full not in chart_ids:
                continue
            measured = {
                song_id: value
                for (song_id, chart_id), value in scored.items()
                if chart_id == chart_ids[full]
            }
            raw = {
                song_id: _from_totals(w or 0, t or 0, p, x or 1, weights)
                for song_id, (w, t, p, x, _y) in totals[code].items()
                if p
            }
            both = [s for s in raw if s in measured]
            factor, error = 1.0, 0.0
            if both:
                fits = []
                for step in range(5, 61):
                    k = step / 20
                    err = statistics.fmean(
                        abs(_p(raw[s][0] * k, raw[s][1], weights) - measured[s]) for s in both
                    )
                    fits.append((err, k))
                error, factor = min(fits)
            report.estimate = (factor, len(both), error)
            for song_id, (total, share) in raw.items():
                if song_id not in best:  # a value from places always wins over an estimate
                    best[song_id] = (_p(total * factor, share, weights), "estimated", None)
        rows = [
            {
                "song_id": s,
                "region_id": regions[region],
                "popularity": v,
                "basis": b,
                "chart_source_id": c,
            }
            for s, (v, b, c) in best.items()
        ]
        if rows:
            db.execute(insert(SongRegionPopularity), rows)
        count = db.scalar(
            select(func.count())
            .select_from(SongRegion)
            .where(SongRegion.region_id == regions[region])
        )
        bases: dict[str, int] = defaultdict(int)
        for _v, b, _c in best.values():
            bases[b] += 1
        report.regions[region] = (int(count or 0), len(rows), dict(bases))


# ------------------------------------------------------------------------- command


def read_all(folder: Path) -> list[tuple[str, list[SourceChart], list[SourceSong]]]:
    found = []
    for source in SOURCES:
        path = folder / source / f"{source}.sqlite"
        if path.is_file():
            charts, songs = read_source(path, source)
            found.append((source, charts, songs))
        else:
            print(f"  {source}: no database at {path} (run build.py), left out")
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--folder", type=Path, default=None, help="data/music-library-regions")
    parser.add_argument("--database", type=Path, default=None, help="another .database/ folder")
    args = parser.parse_args(argv)
    if args.database is not None:
        os.environ["AITU_DATABASE_DIR"] = str(args.database.resolve())

    from aitu_backend.db.database import session  # noqa: PLC0415 - after AITU_DATABASE_DIR

    folder = args.folder or default_folder()
    print(f"reading {folder}")
    sources = read_all(folder)
    with session() as db:
        report = import_regions(db, sources)
    print("\n".join(report.lines()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
