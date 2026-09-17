"""What the motion of the roll says: the scroll speed and the two edges.

Tasks 3.4.1 and, through the same fact, V-28. Both rest on one thing: **the roll
scrolls and nothing else does**. A toolbar, a progress bar, a title band, a
watermark, a photograph behind the roll and the strike light at the upper line
all stay where they are, and the rectangles fall.

So two measurements answer three questions:

* **How fast do the rectangles fall** (V-06, V-45). The rectangles say it
  themselves: every run of a frame is linked to its own self in the next sampled
  frame, one to one, and the fall of every free edge is collected. The per-pair
  mean is the series V-06 asks for, and the answer is the mean over every linked
  edge. It is the travel vote of V-33 with the part of a pixel kept, and it
  replaces the correlation of row profiles Phase 1 chose, which on a roll drawn
  over a photograph was pulled by the light swirls and the glow band — things
  that move, but not with the roll — and answered six usable pairs of 1891.
  Measured on that video: 48 396 linked edges over 1815 pairs, 20.22 px per
  frame, the same to 0.05 px in each third of the piece.
* **Where the roll starts, and where it stops being trustworthy** (V-28, V-24).
  For every row of the plate difference: does the next sampled frame look like
  this row moved down by one frame of travel, or like it did not move at all?
  The roll top is the first row from the top where moving wins; the halo guard
  band is the rows above the upper line, read upward, until moving wins. The
  difference against the plate and not the raw picture, because on a photograph
  every raw row looks still. Measured: guard band 56 rows, 1.82 white keys, on
  the photograph, against a strike glow that starts about row 440 of 515.

A video whose speed is not stable is said to be unstable, plainly, rather than
transcribed quietly (V-06).
"""

from __future__ import annotations

from typing import Callable

import numpy as np

from aitu_backend.schemas.video import DetectedRun, ScrollSpeed, VideoMeasurement
from aitu_backend.video import momentum

#: How many linked edges a pair needs before its mean fall counts. Under this a
#: pair is a rest or a lone rectangle, and a lone rectangle's two edges cannot
#: outvote the noise of one detection.
MIN_EDGES = 6

#: Every how many pairs the integer travel is voted for (V-33) before the pairs
#: are linked at it. The vote is the slow part and the travel does not change
#: from one pair to the next, so a sample of the pairs is enough to find it.
VOTE_EVERY = 8

#: Share of the pairs that answered. More pairs than this that held rectangles
#: on both sides and could not follow one of them is a roll that jumps rather
#: than scrolls, and V-05 cannot turn a distance into a time on it.
LOST_SHARE = 0.25

#: How far apart the quartiles of the per-pair fall may sit, as a share of the
#: answer, before the speed is called unstable. Measured on two videos the
#: quartiles sit 0.7% and 1.8% apart; a tenth of the answer is far past anything
#: a steady rendering does and is the point at which V-05 stops being usable.
STABLE_SPREAD = 0.10

#: A row counts as part of the roll when it looks this much more like it moved
#: than like it stood still. The score is a difference of two correlations, so it
#: runs from -2 to 2 and this is a low bar on purpose: the question is which of
#: the two answers is true, not how strongly.
ROLL_SCORE = 0.05

#: Rows the roll score is smoothed over, so one row of texture cannot cut the
#: roll in two.
ROLL_SMOOTH = 9

#: How many pairs of frames the roll bounds are read from, spread over the video.
#: The score is an average over them; on a sparse piece most rows have nothing
#: falling in most pairs, so more pairs than the fifteen the spike used.
BOUND_PAIRS = 60


def _free_falls(runs: list[DetectedRun], after: list[DetectedRun], travel: float) -> list[float]:
    """How far every free edge of ``runs`` fell into ``after``, one to one.

    A pinned edge is not evidence (V-42): a run cut by the upper line keeps its
    lowest row at the line however fast it falls, and one still entering at the
    roll top keeps its highest, so only the free edges of linked pairs are read.
    """
    candidates = [run for run in runs if not run.clipped and not run.entering]
    links, _ = momentum.link(candidates, after, +travel)
    out: list[float] = []
    for run, index in zip(candidates, links):
        if index is None:
            continue
        other = after[index]
        if other.clipped or other.entering:
            continue
        out.append(float(other.y_top - run.y_top))
        out.append(float(other.y_bottom - run.y_bottom))
    return out


def scroll_speed(
    per_frame: list[list[DetectedRun]], sample_ms: float, *, vote_every: int = VOTE_EVERY
) -> ScrollSpeed:
    """The rectangles' own answer to how far they fall in one sampled frame.

    First the integer travel, voted for by a sample of the pairs the way the
    momentum rule does (V-33) and settled by their median; then every pair
    linked at that travel and the fall of every free edge collected. The mean of
    those edges is the answer, the per-pair means are the series, and the
    quartiles of the pairs that answered say whether the speed is stable.
    """
    if len(per_frame) < 2:
        return ScrollSpeed(
            px_per_frame=0.0,
            px_per_second=0.0,
            stable=False,
            reason="a scroll speed needs at least two sampled frames",
        )

    votes: list[int] = []
    for index in range(0, len(per_frame) - 1, max(1, vote_every)):
        travel, agreeing, _ = momentum.vote_for_travel(per_frame[index + 1], per_frame[index])
        if agreeing >= 2:
            votes.append(travel)
    if not votes:
        return ScrollSpeed(
            px_per_frame=0.0,
            px_per_second=0.0,
            total_pairs=len(per_frame) - 1,
            stable=False,
            reason=(
                "no rectangle could be followed from one sampled frame to the next: nothing "
                "in the roll fell. Check the upper line, or that this video shows a piano "
                "roll at all."
            ),
        )
    integer_travel = float(np.median(votes))

    series: list[float] = []
    means: list[float] = []
    falls: list[float] = []
    still = 0
    lost = 0
    for before, after in zip(per_frame, per_frame[1:]):
        edges = _free_falls(before, after, integer_travel)
        if len(edges) >= MIN_EDGES:
            mean = float(np.mean(edges))
            series.append(round(mean, 3))
            means.append(mean)
            falls.extend(edges)
        else:
            series.append(0.0)
            if before and after and momentum.matches_at(after, before, 0) > 0:
                still += 1
            elif len(before) >= MIN_EDGES and len(after) >= MIN_EDGES:
                # Rectangles on both sides and none of them followed: the roll
                # jumped by something other than its travel.
                lost += 1

    if not means:
        return ScrollSpeed(
            px_per_frame=0.0,
            px_per_second=0.0,
            total_pairs=len(series),
            still_pairs=still,
            stable=False,
            reason="no pair of sampled frames held enough rectangles to measure a fall",
            series=series,
        )

    answer = float(np.mean(falls))
    q1, q3 = (float(x) for x in np.percentile(means, [25, 75]))
    spread = abs(q3 - q1) / answer if answer else float("inf")
    stable = answer > 0 and spread <= STABLE_SPREAD and lost <= LOST_SHARE * len(means)
    if stable:
        reason = ""
    elif answer <= 0:
        reason = "the roll does not move between sampled frames"
    elif spread > STABLE_SPREAD:
        reason = (
            f"the fall per sampled frame varies by {spread * 100:.1f}% between its quartiles "
            f"({q1:.1f} to {q3:.1f} px around {answer:.1f}). V-05 turns a distance into a "
            "time with one speed, so this video cannot be read that way."
        )
    else:
        reason = (
            f"in {lost} pairs of sampled frames the rectangles could not be followed at "
            f"{answer:.1f} px a frame, against {len(means)} pairs where they could: the roll "
            "jumps rather than scrolls, and V-05 cannot turn a distance into a time on it."
        )
    return ScrollSpeed(
        px_per_frame=answer,
        px_per_second=answer * 1000.0 / sample_ms,
        q1=q1,
        q3=q3,
        p5=float(np.percentile(means, 5)),
        p95=float(np.percentile(means, 95)),
        usable_pairs=len(means),
        total_pairs=len(series),
        still_pairs=still,
        stable=bool(stable),
        reason=reason,
        series=series,
    )


def _correlation(a: np.ndarray, b: np.ndarray) -> float:
    a = a - a.mean()
    b = b - b.mean()
    size = float(np.sqrt((a * a).sum() * (b * b).sum()))
    return float((a * b).sum() / size) if size > 1e-6 else 0.0


def roll_bounds(
    load: Callable[[int], np.ndarray],
    indices: list[int],
    upper_line: float,
    travel: float,
    plate: np.ndarray | None = None,
) -> tuple[int, int, np.ndarray]:
    """Where the roll starts and where it stops being trustworthy (V-28).

    Returns (roll top, roll bottom, the score of every row). Every row above the
    upper line is scored on the difference against ``plate`` — on the raw grey
    picture when there is no plate — and the two edges are read from the two
    ends: the roll top is the first row from the top where moving wins, and the
    bottom is the first row above the upper line, read upward, where the score
    turns positive. (0, 0) means the roll was not seen to move at all.

    The band read this way is up to one travel wider than the strike light
    itself, because a row whose content falls *into* the light within one frame
    cannot be seen to move either. That is the safe side of the answer: a guard
    band a little too tall costs a few rows of the head, a band too short trusts
    a tip the light has eaten.
    """
    upper = int(round(upper_line))
    step = int(round(travel))
    score = np.zeros(max(1, upper))
    pairs = 0
    for index in indices:
        a = load(index)
        b = load(index + 1)
        if plate is not None:
            a = np.abs(a - plate[: a.shape[0]]).max(axis=2)
            b = np.abs(b - plate[: b.shape[0]]).max(axis=2)
        else:
            a = a.mean(axis=2)
            b = b.mean(axis=2)
        if a.shape[0] < upper or step < 1:
            continue
        pairs += 1
        for y in range(0, upper):
            if y + step >= b.shape[0]:
                break
            score[y] += _correlation(a[y], b[y + step]) - _correlation(a[y], b[y])
    if pairs:
        score /= pairs
    smoothed = np.convolve(score, np.ones(ROLL_SMOOTH) / ROLL_SMOOTH, mode="same")

    moved = np.where(smoothed > ROLL_SCORE)[0]
    if moved.size == 0:
        return 0, 0, smoothed
    top = int(moved[0])
    bottom = upper - 1
    while bottom > top and smoothed[bottom] <= 0:
        bottom -= 1
    return top, bottom + 1, smoothed


def measure(
    load: Callable[[int], np.ndarray],
    per_frame: list[list[DetectedRun]],
    upper_line: float,
    sample_ms: float,
    plate: np.ndarray | None = None,
) -> VideoMeasurement:
    """Everything the motion of the roll says about one video, in one answer.

    The scroll speed first, because the roll bounds need a travel to ask about.
    The offset line falls straight out of it: on a video it is not a free
    parameter, it is the measured scroll speed times the sampling granularity and
    nothing else (V-25). A roll the bounds cannot see leaves the guard band at
    zero, which the geometry reads as its measured default (V-24).
    """
    count = len(per_frame)
    speed = scroll_speed(per_frame, sample_ms)
    if speed.px_per_frame <= 0:
        return VideoMeasurement(scroll_speed=speed)

    picks = np.linspace(0, max(0, count - 2), min(BOUND_PAIRS, max(1, count - 1)))
    indices = sorted({int(round(x)) for x in picks})
    top, bottom, _ = roll_bounds(load, indices, upper_line, speed.px_per_frame, plate=plate)
    guard = float(max(0, int(round(upper_line)) - bottom)) if bottom > top else 0.0
    return VideoMeasurement(
        scroll_speed=speed,
        roll_top=float(top),
        guard_band=guard,
        offset_px=speed.px_per_frame,
    )
