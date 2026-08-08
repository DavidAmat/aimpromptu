"""Gaps between consecutive attacks, measured on raw timestamps.

This is the input to everything the user will be asked to look at. The plot of gaps in Phase 7, the
peaks in :mod:`aitu_backend.matrix.peaks` and the ladder in :mod:`aitu_backend.matrix.ladder` all
start here, so the one rule this module enforces is worth stating first.

**Never measure on snapped columns (D-07).** Rounding an onset to a column before measuring splits
every peak in two. A real gap of 337 ms becomes 8 or 9 columns of 40 ms depending on where the two
notes happen to fall, so it arrives as 320 ms about 57 % of the time and 360 ms the rest. The
clearest signal in the data, one spike holding half of all gaps, would appear as two half-height
spikes and the user would be asked to name a peak that does not exist. The same happens to 211,
which splits into 200 and 240, and to 125, which splits into 120 and 160.

That is measured, not assumed: see ``poc-onset-duration-distribution/RESULTS.md``. The regression
test in ``tests/test_matrix_peaks.py`` reproduces the split and must never be deleted.

Gaps are measured **per hand**. A right-hand run above a held left-hand chord produces gaps between
the two hands that no player would call a rhythm, and mixing them fills the low end of the
distribution with noise.

Ported from ``poc-onset-duration-distribution/scripts/common.py``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from aitu_backend.matrix.time_grid import DEFAULT_FRAME_MS
from aitu_backend.transcription.engine import NoteEvent
from aitu_backend.transcription.grouping import DEFAULT_GROUP_WINDOW_MS, group_onsets

__all__ = [
    "IntervalSet",
    "attack_times_seconds",
    "check_measured_on_raw_times",
    "intervals_from_events",
    "intervals_ms",
]


@dataclass
class IntervalSet:
    """The gaps found in one stretch of one hand, with enough context to read them."""

    #: Consecutive attack-to-attack gaps, in milliseconds, in time order.
    values_ms: np.ndarray
    #: How many attacks produced them. One more than the number of gaps, when there is any.
    attack_count: int
    #: The stretch actually measured, in seconds from the start of the audio.
    start_seconds: float
    end_seconds: float

    @property
    def count(self) -> int:
        return int(self.values_ms.size)

    @property
    def median_ms(self) -> float:
        """The middle gap. Zero when there is nothing to measure."""
        return float(np.median(self.values_ms)) if self.count else 0.0

    def describe(self) -> str:
        if not self.count:
            return f"no gaps between {self.start_seconds:.2f} s and {self.end_seconds:.2f} s."
        return (
            f"{self.count} gaps from {self.attack_count} attacks between "
            f"{self.start_seconds:.2f} s and {self.end_seconds:.2f} s, median "
            f"{self.median_ms:.1f} ms."
        )


def attack_times_seconds(
    events: list[NoteEvent],
    window_ms: float = DEFAULT_GROUP_WINDOW_MS,
) -> np.ndarray:
    """When each attack happened, in seconds, in order.

    A chord counts once. Without that, the eight milliseconds between the notes of a chord would
    become the most common gap in the piece and the real rhythm would disappear underneath it.
    """
    return np.asarray(
        [group.start_seconds for group in group_onsets(events, window_ms=window_ms)],
        dtype=float,
    )


def intervals_ms(attack_seconds: np.ndarray | list[float]) -> np.ndarray:
    """Consecutive attack-to-attack gaps, in milliseconds.

    The times must already be sorted, which :func:`attack_times_seconds` guarantees.
    """
    times = np.asarray(attack_seconds, dtype=float)
    if times.size < 2:
        return np.empty(0, dtype=float)
    return np.diff(times) * 1000.0


def intervals_from_events(
    events: list[NoteEvent],
    *,
    window_ms: float = DEFAULT_GROUP_WINDOW_MS,
    start_seconds: float = 0.0,
    end_seconds: float | None = None,
) -> IntervalSet:
    """Gaps for one hand, optionally limited to a stretch of the piece.

    Pass the events of a single hand. The range is applied to the **attacks**, not to the gaps, so a
    passage's first gap is the one from its first attack to its second and never a gap reaching back
    into the previous passage.
    """
    limit = float("inf") if end_seconds is None else end_seconds
    if limit <= start_seconds:
        raise ValueError(
            f"The range must end after it starts, got {start_seconds} s to {end_seconds} s"
        )
    inside = [event for event in events if start_seconds <= event.start < limit]
    attacks = attack_times_seconds(inside, window_ms=window_ms)
    return IntervalSet(
        values_ms=intervals_ms(attacks),
        attack_count=int(attacks.size),
        start_seconds=float(start_seconds),
        end_seconds=float(attacks[-1]) if attacks.size else float(start_seconds),
    )


def check_measured_on_raw_times(
    values_ms: np.ndarray,
    frame_ms: float = DEFAULT_FRAME_MS,
    *,
    minimum_sample: int = 8,
    tolerance_ms: float = 1e-6,
) -> None:
    """Refuse a set of gaps that was measured on columns rather than on raw times (D-07).

    A gap taken from column indices is always a whole number of frames, so a set where *every* gap
    is an exact multiple of the frame length can only have come from snapped data. Real playing
    never does that: a person cannot place forty consecutive notes on 40 ms boundaries.

    The check needs a few values before it means anything, so a short set passes. This is a guard
    against a mistake that is easy to make and silent when made, not a proof.
    """
    values = np.asarray(values_ms, dtype=float)
    if values.size < minimum_sample:
        return
    remainder = np.abs(values / frame_ms - np.round(values / frame_ms)) * frame_ms
    if np.all(remainder <= tolerance_ms):
        raise ValueError(
            f"Every one of these {values.size} gaps is an exact multiple of {frame_ms} ms, so they "
            "were measured on snapped columns. Peak finding and ladder fitting read the raw "
            "timestamps from events.json (D-07): snapping first splits every peak in two."
        )
