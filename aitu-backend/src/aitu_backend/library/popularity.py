"""Popularity: a number from 0 to 100 worked out from the chart weeks of a song or an album
(implementation 02, plan section 15.6; ``context/music-library/reconciliation.md`` section 5).

For each week where the song is at position ``r`` of a chart of size ``N``::

    points(r) = ((N + 1 - r) / N) ^ week_power          a position worse than N adds nothing
    S         = sum of weight(chart) * points(r)          over the weeks inside the time range
    peak      = ((N + 1 - best position) / N) ^ peak_power
    P         = 100 * (sum_weight * (1 - e^(-S / saturation)) + peak_weight * peak)

:data:`PLAN` is the first formula of the plan. :data:`DEFAULT`, the one the app uses, differs in
one number, chosen in Phase 12 (Q-6) by objective criteria instead of a hand ranking: the power of
a week's points is 8, not 2, so the weeks near the top count far more than the weeks lower down.
:func:`criteria` measures both on the downloaded chart history. A time range is applied to the
weeks before the sum, so the popularity "in the 80s" is computed from the weeks of the 80s only.

``python -m aitu_backend.library.popularity check`` (``make popularity-check``) prints the criteria
for both; it reads the downloaded ``library.sqlite`` and writes nothing.
"""

from __future__ import annotations

import argparse
import math
import sqlite3
import statistics
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Iterable

from sqlalchemy import select, update
from sqlalchemy.orm import Session as DbSession

from aitu_backend.db.models import (
    Album,
    AlbumChartEntry,
    ChartEntry,
    ChartSource,
    Song,
)

__all__ = [
    "DEFAULT",
    "PLAN",
    "Criteria",
    "Week",
    "Weights",
    "album_scores",
    "criteria",
    "points",
    "score",
    "song_scores",
    "store_all_time",
]


@dataclass(frozen=True)
class Weights:
    sum_weight: float = 0.6
    peak_weight: float = 0.4
    saturation: float = 10.0
    week_power: float = 2.0
    peak_power: float = 3.0


#: The formula of plan section 15.6, as written before any tuning.
PLAN = Weights()
#: The weights the app uses (Phase 12, Q-6): the plan's, with the weeks near the top counting far
#: more. Place 1 is worth 1.0 a week, place 10 0.47, place 20 0.18, place 40 0.02 (with the
#: plan's power 2: 1.0, 0.83, 0.66, 0.37).
DEFAULT = Weights(week_power=8.0)


@dataclass(frozen=True)
class Week:
    """One week of one chart: the position, the chart's size and its weight."""

    rank: int
    size: int = 100
    weight: float = 1.0


def points(rank: int, size: int = 100, weights: Weights = DEFAULT) -> float:
    """The points of one week at ``rank``: zero outside ``1..size``."""
    if rank < 1 or rank > size:
        return 0.0
    return float(((size + 1 - rank) / size) ** weights.week_power)


def score(weeks: Iterable[Week], weights: Weights = DEFAULT) -> float:
    """P for these weeks, rounded to one decimal place; 0.0 when none is inside its chart."""
    total = 0.0
    peak = 0.0
    counted = False
    for week in weeks:
        if week.rank < 1 or week.rank > week.size:
            continue
        counted = True
        total += week.weight * points(week.rank, week.size, weights)
        best = week.weight * ((week.size + 1 - week.rank) / week.size) ** weights.peak_power
        peak = max(peak, min(best, 1.0))
    if not counted:
        return 0.0
    value = 100.0 * (
        weights.sum_weight * (1.0 - math.exp(-total / weights.saturation))
        + weights.peak_weight * peak
    )
    return round(value, 1)


# ---------------------------------------------------------------- from the tables


def _scores(
    db: DbSession,
    entry: type[ChartEntry] | type[AlbumChartEntry],
    owner_column: str,
    start: date | None,
    end: date | None,
    weights: Weights,
) -> dict[int, float]:
    owner = getattr(entry, owner_column)
    query = select(owner, entry.rank, ChartSource.size, ChartSource.weight).join(
        ChartSource, ChartSource.id == entry.chart_source_id
    )
    if start is not None:
        query = query.where(entry.week >= start)
    if end is not None:
        query = query.where(entry.week <= end)
    weeks: dict[int, list[Week]] = {}
    for owner_id, rank, size, weight in db.execute(query):
        weeks.setdefault(owner_id, []).append(Week(rank, size, weight))
    return {owner_id: score(found, weights) for owner_id, found in weeks.items()}


def song_scores(
    db: DbSession,
    start: date | None = None,
    end: date | None = None,
    weights: Weights = DEFAULT,
) -> dict[int, float]:
    """The popularity of every song with a chart week inside ``start..end`` (both included).

    This is what a filter by decade sorts by: worked out again from the weeks, not stored."""
    return _scores(db, ChartEntry, "song_id", start, end, weights)


def album_scores(
    db: DbSession,
    start: date | None = None,
    end: date | None = None,
    weights: Weights = DEFAULT,
) -> dict[int, float]:
    return _scores(db, AlbumChartEntry, "album_id", start, end, weights)


def store_all_time(db: DbSession, weights: Weights = DEFAULT) -> tuple[int, int]:
    """Write ``songs.popularity`` and ``albums.popularity`` of the public rows from all their
    weeks; a public row with no week gets 0.0. Returns how many songs and albums were written."""
    written = []
    for model, found in (
        (Song, song_scores(db, weights=weights)),
        (Album, album_scores(db, weights=weights)),
    ):
        ids = list(db.scalars(select(model.id).where(model.scope == "public")))
        rows = [{"id": row_id, "popularity": found.get(row_id, 0.0)} for row_id in ids]
        if rows:
            db.execute(update(model), rows)  # one UPDATE per row, by primary key
        written.append(len(rows))
    return written[0], written[1]


# ----------------------------------------------------------- the objective criteria

#: Billboard's Greatest of All Time Hot 100 Songs, top 10, as published in November 2021 (Blinding
#: Lights first): a ranking made by the chart's own owner from weeks on the chart and positions.
#: The eight of them the download has (The Twist and Mack the Knife are older than 1976).
BENCHMARK_DATE = "2021-11-20"
BENCHMARK = (
    "/singles/the-weeknd/blinding-lights",
    "/singles/santana/smooth",
    "/singles/mark-ronson/uptown-funk",
    "/singles/leann-rimes/how-do-i-live",
    "/singles/lmfao/party-rock-anthem",
    "/singles/black-eyed-peas/i-gotta-feeling",
    "/singles/los-del-rio/macarena-bayside-boys-mix",
    "/singles/ed-sheeran/shape-of-you",
)


@dataclass
class Criteria:
    """What the app context asks of the popularity, measured (reconciliation section 5)."""

    #: Number 1 for 30 weeks, for 10 weeks, for 1 week; place 20 for 20 weeks; place 80 for 3.
    examples: dict[str, float] = field(default_factory=dict)
    #: Songs at 95 or more: few, or a sort by popularity cannot tell the biggest hits apart.
    at_95: int = 0
    songs: int = 0
    #: Among the songs that reached number 1, how well the score follows the weeks at number 1
    #: (Spearman's rank correlation: 1 the same order, 0 no relation).
    follows_weeks_at_1: float = 0.0
    #: The places of :data:`BENCHMARK` in the all-time order, weeks up to :data:`BENCHMARK_DATE`.
    benchmark_places: list[int] = field(default_factory=list)

    def passes(self) -> bool:
        e = self.examples
        return (
            e["1 x 30"] >= 95
            and e["1 x 30"] - e["1 x 10"] >= 8
            and 0.8 * e["1 x 1"] <= e["20 x 20"] <= e["1 x 1"]
            and e["80 x 3"] < 1
            and self.at_95 <= self.songs // 100
        )


def _ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2.0
        i = j + 1
    return ranks


def spearman(first: list[float], second: list[float]) -> float:
    """Spearman's rank correlation of two lists of the same length."""
    a, b = _ranks(first), _ranks(second)
    return statistics.correlation(a, b) if len(a) > 1 else 0.0


def criteria(weeks_of: dict[str, list[tuple[str, int]]], weights: Weights) -> Criteria:
    """Measure ``weights`` on a chart history: source path -> [(date, position)]."""
    found = Criteria(
        examples={
            label: score([Week(rank)] * count, weights)
            for label, (rank, count) in {
                "1 x 30": (1, 30),
                "1 x 10": (1, 10),
                "1 x 1": (1, 1),
                "20 x 20": (20, 20),
                "80 x 3": (80, 3),
            }.items()
        }
    )
    every = {
        path: score([Week(rank) for _, rank in weeks], weights) for path, weeks in weeks_of.items()
    }
    found.songs = len(every)
    found.at_95 = sum(1 for value in every.values() if value >= 95)
    number_1 = [path for path, weeks in weeks_of.items() if min(rank for _, rank in weeks) == 1]
    found.follows_weeks_at_1 = spearman(
        [every[path] for path in number_1],
        [float(sum(1 for _, rank in weeks_of[path] if rank == 1)) for path in number_1],
    )
    until = {
        path: score([Week(rank) for day, rank in weeks if day <= BENCHMARK_DATE], weights)
        for path, weeks in weeks_of.items()
    }
    order = sorted(until, key=lambda path: -until[path])
    found.benchmark_places = [order.index(path) + 1 for path in BENCHMARK if path in until]
    return found


def _source_history(source: Path) -> dict[str, list[tuple[str, int]]]:
    """The singles chart history of the download, by song path (re-entries kept apart)."""
    connection = sqlite3.connect(f"file:{source}?mode=ro&immutable=1", uri=True)
    try:
        rows = connection.execute("""
            SELECT s.source_path, w.chart_date, r.position FROM ranking AS r
            JOIN song AS s ON s.id = r.song_id
            JOIN chart AS c ON c.id = r.chart_id
            JOIN chart_week AS w ON w.id = r.chart_week_id
            WHERE c.kind = 'singles'
            """).fetchall()
    finally:
        connection.close()
    history: dict[str, list[tuple[str, int]]] = {}
    for path, day, rank in rows:
        history.setdefault(str(path), []).append((str(day), int(rank)))
    return history


def main(argv: list[str] | None = None) -> int:
    from aitu_backend.library.public_import import default_source  # noqa: PLC0415

    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="the criteria of the plan's weights and of the app's")
    check.add_argument("--source", type=Path, default=None)
    args = parser.parse_args(argv)

    history = _source_history(args.source or default_source())
    for name, weights in (("the plan's weights", PLAN), ("the app's weights", DEFAULT)):
        found = criteria(history, weights)
        print(f"{name}: {weights}")
        print(f"  examples: {found.examples}")
        print(f"  songs at 95 or more: {found.at_95} of {found.songs}")
        print(f"  follows the weeks at number 1: {found.follows_weeks_at_1:.3f}")
        print(
            f"  Billboard's all-time top 10 (2021), places among {found.songs} songs:"
            f" {found.benchmark_places}"
        )
        print(f"  meets the criteria: {'yes' if found.passes() else 'no'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
