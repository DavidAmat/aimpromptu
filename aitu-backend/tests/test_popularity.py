"""Popularity from the chart weeks (implementation 02, plan section 15.6, Phase 12): the formula and
its examples, a position outside the chart, a time range, the chart's size and weight, the stored
all-time value, and the weights the app uses, chosen by objective criteria (Q-6)."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select

from aitu_backend.db.database import session
from aitu_backend.db.models import Album, ChartEntry, ChartSource, Song
from aitu_backend.library.popularity import (
    DEFAULT,
    PLAN,
    Week,
    Weights,
    criteria,
    points,
    score,
    song_scores,
    spearman,
    store_all_time,
)


def weeks(rank: int, count: int, size: int = 100, weight: float = 1.0) -> list[Week]:
    return [Week(rank, size, weight)] * count


def test_the_examples_of_the_plan() -> None:
    # Plan section 15.6, and the unit examples of the parallel work (97.0, 77.9, 45.7).
    assert score(weeks(1, 30), PLAN) == 97.0
    assert score(weeks(1, 10), PLAN) == 77.9
    assert round(score(weeks(20, 20), PLAN)) == 65
    assert score(weeks(1, 1), PLAN) == 45.7
    assert round(score(weeks(5, 1), PLAN)) == 41
    assert round(score(weeks(80, 3), PLAN)) == 1


def test_the_app_s_weights_keep_number_1_and_put_long_middle_runs_below_it() -> None:
    # One number differs from the plan: the weeks at number 1 give the same scores, and 20 weeks
    # at place 20 is now close to, a little below, one week at number 1 (the app context).
    assert DEFAULT == Weights(week_power=8.0)
    assert (score(weeks(1, 30)), score(weeks(1, 10)), score(weeks(1, 1))) == (97.0, 77.9, 45.7)
    assert 0.8 * score(weeks(1, 1)) <= score(weeks(20, 20)) <= score(weeks(1, 1))
    assert score(weeks(20, 20)) == 39.8
    assert score(weeks(80, 3)) < 1
    assert round(points(10), 2) == 0.47


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
    assert score(held, PLAN) > score(once, PLAN)
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


def test_spearman() -> None:
    assert spearman([1, 2, 3], [10, 20, 30]) == 1.0
    assert spearman([1, 2, 3], [30, 20, 10]) == -1.0
    assert round(spearman([1, 2, 3, 4], [1, 1, 2, 2]), 3) == 0.894


def test_the_criteria_tell_the_two_weights_apart() -> None:
    # A small chart history: a long run held in the middle, a short one at number 1, a long one at
    # number 1, and songs below.
    history = {
        "/singles/held": [(f"2000-01-{d:02d}", 20) for d in range(1, 29)],
        "/singles/once": [("2001-01-06", 1), ("2001-01-13", 30)],
        "/singles/long": [(f"2002-02-{d:02d}", 1) for d in range(1, 13)],
        "/singles/low": [("2003-01-04", 80)],
    }
    plan, app = criteria(history, PLAN), criteria(history, DEFAULT)
    assert not plan.passes() and app.passes()
    assert plan.examples["20 x 20"] > plan.examples["1 x 1"]
    assert app.follows_weeks_at_1 == 1.0
    assert app.songs == 4
