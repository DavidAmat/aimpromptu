"""Popularity: a number from 0 to 100 worked out from the chart weeks of a song or an album
(implementation 02, plan section 15.6; ``context/music-library/reconciliation.md`` section 5).

For each week where the song is at position ``r`` of a chart of size ``N``::

    points(r) = ((N + 1 - r) / N) ^ week_power          a position worse than N adds nothing
    S         = sum of weight(chart) * points(r)          over the weeks inside the time range
    peak      = ((N + 1 - best position) / N) ^ peak_power
    P         = 100 * (sum_weight * (1 - e^(-S / saturation)) + peak_weight * peak)

The weights are :class:`Weights`; :data:`PLAN` is the first formula of the plan, which Phase 12
tunes on a list of songs the user ranks by hand (Q-6, :func:`tune`). A time range is applied to the
weeks before the sum, so the popularity "in the 80s" is computed from the weeks of the 80s only.

``python -m aitu_backend.library.popularity tune --order <letters>`` fits the weights to the hand
ranking of ``hand_ranking.json`` and prints the result; it reads the downloaded ``library.sqlite``
and writes nothing.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import sqlite3
import sys
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, Sequence

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
    "PLAN",
    "Week",
    "Weights",
    "album_scores",
    "kendall_tau",
    "points",
    "score",
    "song_scores",
    "store_all_time",
    "tune",
]

HAND_RANKING = Path(__file__).with_name("hand_ranking.json")


@dataclass(frozen=True)
class Weights:
    sum_weight: float = 0.6
    peak_weight: float = 0.4
    saturation: float = 10.0
    week_power: float = 2.0
    peak_power: float = 3.0


#: The formula of plan section 15.6, as written before any tuning.
PLAN = Weights()


@dataclass(frozen=True)
class Week:
    """One week of one chart: the position, the chart's size and its weight."""

    rank: int
    size: int = 100
    weight: float = 1.0


def points(rank: int, size: int = 100, weights: Weights = PLAN) -> float:
    """The points of one week at ``rank``: zero outside ``1..size``."""
    if rank < 1 or rank > size:
        return 0.0
    return float(((size + 1 - rank) / size) ** weights.week_power)


def score(weeks: Iterable[Week], weights: Weights = PLAN) -> float:
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
    weights: Weights = PLAN,
) -> dict[int, float]:
    """The popularity of every song with a chart week inside ``start..end`` (both included).

    This is what a filter by decade sorts by: worked out again from the weeks, not stored."""
    return _scores(db, ChartEntry, "song_id", start, end, weights)


def album_scores(
    db: DbSession,
    start: date | None = None,
    end: date | None = None,
    weights: Weights = PLAN,
) -> dict[int, float]:
    return _scores(db, AlbumChartEntry, "album_id", start, end, weights)


def store_all_time(db: DbSession, weights: Weights = PLAN) -> tuple[int, int]:
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


# ------------------------------------------------------------------- the tuning


def kendall_tau(first: Sequence[float], second: Sequence[float]) -> float:
    """How much two orders agree: 1 the same order, -1 the reverse, 0 no relation. Ties count 0."""
    agree = 0
    pairs = 0
    for i, j in itertools.combinations(range(len(first)), 2):
        pairs += 1
        product = (first[i] - first[j]) * (second[i] - second[j])
        agree += (product > 0) - (product < 0)
    return agree / pairs if pairs else 0.0


GRID = {
    "peak_weight": (0.2, 0.3, 0.4, 0.5, 0.6),
    "saturation": (5.0, 10.0, 15.0, 20.0, 30.0, 40.0),
    "week_power": (1.0, 2.0, 3.0, 4.0),
    "peak_power": (1.0, 2.0, 3.0, 4.0),
}


def tune(
    profiles: Sequence[Sequence[Week]], hand_order: Sequence[int]
) -> list[tuple[float, Weights]]:
    """Every weight of :data:`GRID`, best first, by how well its scores follow the hand order.

    ``hand_order[i]`` is the place the user gave to ``profiles[i]`` (1 = the most popular)."""
    wanted = [-float(place) for place in hand_order]
    results = []
    for peak_weight, saturation, week_power, peak_power in itertools.product(*GRID.values()):
        weights = Weights(
            sum_weight=round(1.0 - peak_weight, 2),
            peak_weight=peak_weight,
            saturation=saturation,
            week_power=week_power,
            peak_power=peak_power,
        )
        found = [score(weeks, weights) for weeks in profiles]
        results.append((kendall_tau(found, wanted), weights))
    results.sort(key=lambda item: (-item[0], _distance(item[1])))
    return results


def _distance(weights: Weights) -> float:
    """How far from the plan's formula: among equal fits, the closest one wins."""
    plan, other = asdict(PLAN), asdict(weights)
    return sum(abs(plan[key] - other[key]) / max(plan[key], 1.0) for key in plan)


def _source_weeks(source: Path, source_path: str) -> list[Week]:
    connection = sqlite3.connect(f"file:{source}?mode=ro&immutable=1", uri=True)
    try:
        rows = connection.execute(
            """
            SELECT r.position FROM ranking AS r
            JOIN song AS s ON s.id = r.song_id
            JOIN chart AS c ON c.id = r.chart_id
            WHERE s.source_path = ? AND c.kind = 'singles'
            """,
            (source_path,),
        ).fetchall()
    finally:
        connection.close()
    return [Week(int(rank)) for (rank,) in rows]


def main(argv: list[str] | None = None) -> int:
    from aitu_backend.library.public_import import default_source  # noqa: PLC0415

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    tune_parser = sub.add_parser("tune", help="fit the weights to the hand ranking")
    tune_parser.add_argument("--source", type=Path, default=None)
    tune_parser.add_argument(
        "--order",
        default=None,
        help="the letters of hand_ranking.json, most popular first (default: its userOrder)",
    )
    tune_parser.add_argument("--top", type=int, default=5)
    args = parser.parse_args(argv)

    source = args.source or default_source()
    listed = json.loads(HAND_RANKING.read_text(encoding="utf-8"))
    songs = listed["songs"]
    order = args.order or listed.get("userOrder")
    if not order:
        print("No order: pass --order, or write userOrder in hand_ranking.json.", file=sys.stderr)
        return 1
    letters = [letter.strip().upper() for letter in order.replace(",", " ").split()]
    if len(letters) == 1:
        letters = list(letters[0])
    known = [song["letter"] for song in songs]
    if sorted(letters) != sorted(known):
        print(f"The order must name each of {''.join(known)} once.", file=sys.stderr)
        return 1
    place = {letter: index + 1 for index, letter in enumerate(letters)}
    profiles = [_source_weeks(source, song["sourcePath"]) for song in songs]
    hand = [place[song["letter"]] for song in songs]

    plan_scores = [score(weeks) for weeks in profiles]
    print(f"the plan's formula: agreement {kendall_tau(plan_scores, [-p for p in hand]):.3f}")
    results = tune(profiles, hand)
    for agreement, weights in results[: args.top]:
        print(f"agreement {agreement:.3f}  {weights}")
    best = results[0][1]
    print("\nplace  letter  plan   tuned  song")
    for letter in letters:
        index = known.index(letter)
        weeks = profiles[index]
        print(
            f"{place[letter]:5}  {letter:6}  {score(weeks):5.1f}  {score(weeks, best):5.1f}"
            f"  {songs[index]['title']} ({songs[index]['artist']})"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
