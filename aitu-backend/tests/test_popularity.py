"""Popularity from the chart weeks (implementation 02, plan section 15.6, Phase 12): the formula and
its examples, a position outside the chart, a time range, the chart's size and weight, the stored
all-time value, and the tuning on a hand ranking (Q-6)."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select

from aitu_backend.db.database import session
from aitu_backend.db.models import Album, ChartEntry, ChartSource, Song
from aitu_backend.library.popularity import (
    PLAN,
    Week,
    Weights,
    kendall_tau,
    points,
    score,
    song_scores,
    store_all_time,
    tune,
)


def weeks(rank: int, count: int, size: int = 100, weight: float = 1.0) -> list[Week]:
    return [Week(rank, size, weight)] * count


def test_the_examples_of_the_plan() -> None:
    # Plan section 15.6, and the unit examples of the parallel work (97.0, 77.9, 45.7).
    assert score(weeks(1, 30)) == 97.0
    assert score(weeks(1, 10)) == 77.9
    assert round(score(weeks(20, 20))) == 65
    assert score(weeks(1, 1)) == 45.7
    assert round(score(weeks(5, 1))) == 41
    assert round(score(weeks(80, 3))) == 1


def test_a_position_outside_the_chart_adds_nothing() -> None:
    assert points(1) == 1.0
    assert points(101) == 0.0
    assert score(weeks(2000, 50)) == 0.0
    assert score([]) == 0.0
    assert score(weeks(1, 3) + weeks(150, 40)) == score(weeks(1, 3))


def test_the_size_and_the_weight_of_a_chart() -> None:
    # Place 40 of a top 40 is its last place, worth almost nothing; of a top 100, more.
    assert score(weeks(40, 5, size=40)) < score(weeks(40, 5, size=100))
    # A chart of weight 0.5 counts half: the same weeks give a lower score.
    assert score(weeks(1, 10, weight=0.5)) < score(weeks(1, 10))
    assert score(weeks(1, 10, weight=0.0)) == 0.0


def test_other_weights_change_the_order_of_two_songs() -> None:
    held = weeks(20, 30)  # places 10 to 30 for many weeks
    once = weeks(1, 1)  # number 1 for one week
    assert score(held) > score(once)
    peak_first = Weights(sum_weight=0.4, peak_weight=0.6, saturation=30.0, week_power=3.0)
    assert score(held, peak_first) < score(once, peak_first)


def put_song(db, title: str, ranks: list[tuple[date, int]], chart: int):  # type: ignore[no-untyped-def]
    song = Song(scope="public", title=title)
    db.add(song)
    db.flush()
    for week, rank in ranks:
        db.add(ChartEntry(song_id=song.id, chart_source_id=chart, week=week, rank=rank))
    return song


def test_a_time_range_counts_only_its_weeks_and_the_all_time_value_is_stored() -> None:
    with session() as db:
        chart = ChartSource(name="test singles", size=100, weight=1.0)
        db.add(chart)
        db.flush()
        eighties = put_song(
            db, "Eighties", [(date(1984, 1, 7), 1), (date(1984, 1, 14), 1)], chart.id
        )
        later = put_song(db, "Later", [(date(1984, 1, 7), 50), (date(2001, 6, 2), 1)], chart.id)
        silent = Song(scope="public", title="Never charted")
        db.add(silent)
        db.add(Song(scope="private", title="Mine", owner_id=None))
        db.flush()

        every = song_scores(db)
        assert every[eighties.id] == score(weeks(1, 2))
        decade = song_scores(db, date(1980, 1, 1), date(1989, 12, 31))
        assert decade == {eighties.id: score(weeks(1, 2)), later.id: score(weeks(50, 1))}
        assert song_scores(db, start=date(2001, 6, 2), end=date(2001, 6, 2)) == {
            later.id: score(weeks(1, 1))
        }

        assert store_all_time(db) == (3, 0)
        stored = {s.title: s.popularity for s in db.scalars(select(Song))}
        assert stored["Eighties"] == every[eighties.id]
        assert stored["Never charted"] == 0.0
        assert stored["Mine"] is None
        assert list(db.scalars(select(Album))) == []


def test_kendall_tau() -> None:
    assert kendall_tau([1, 2, 3], [10, 20, 30]) == 1.0
    assert kendall_tau([1, 2, 3], [30, 20, 10]) == -1.0
    assert kendall_tau([1, 2], [5, 5]) == 0.0


def test_the_tuning_finds_weights_that_follow_a_hand_ranking() -> None:
    # Songs of different shapes, ranked by hand the way a peak-first formula ranks them.
    profiles = [
        weeks(1, 1),
        weeks(20, 30),
        weeks(1, 12),
        weeks(5, 2) + weeks(40, 10),
        weeks(60, 25),
        weeks(2, 8) + weeks(15, 20),
    ]
    wanted = Weights(sum_weight=0.4, peak_weight=0.6, saturation=30.0, week_power=3.0)
    order = sorted(range(len(profiles)), key=lambda i: -score(profiles[i], wanted))
    hand = [order.index(i) + 1 for i in range(len(profiles))]
    assert kendall_tau([score(p) for p in profiles], [-h for h in hand]) < 1.0

    best_agreement, best = tune(profiles, hand)[0]
    assert best_agreement == 1.0
    found = [score(p, best) for p in profiles]
    assert sorted(range(len(profiles)), key=lambda i: -found[i]) == order
    assert best != PLAN
