"""Trills: two pitches alternating quickly, proposed as a ``tr`` rather than printed as a storm.

A trill is a suggestion, not a rewrite. Detection runs on the raw event times (D-03, D-07), never
on snapped columns: the grid is a view of the playing, and a fast alternation is a fact about the
playing. The notes stay in ``events.json``. Accepting the mark hides the storm on the page and
prints ``tr`` over the lower pitch held for the length of the run; playback still sounds every
alternation (D-29). Removing the mark puts the notes back.

The rule is deliberately narrow, because a wrong trill hides real notes and a missed one costs
nothing. Qualifying runs are:

* one hand
* exactly two pitches, a whole tone or closer
* strictly alternating (A B A B …), not a chord, not a repeated note
* at least six pitch changes (seven notes)
* consecutive gaps even with one another, and each short enough to be an ornament rather than a
  measured figure
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from aitu_backend.matrix.keys import KEY_COUNT, LOWEST_MIDI, midi_to_row
from aitu_backend.matrix.time_grid import DEFAULT_FRAME_MS, MS_PER_SECOND, frame_of_seconds
from aitu_backend.schemas.matrix import ONSET, SILENCE, SUSTAIN
from aitu_backend.schemas.time_matrix import PrintedHand, TrillMark
from aitu_backend.transcription.engine import NoteEvent
from aitu_backend.transcription.time_pipeline import TimeHands

__all__ = [
    "DEFAULT_EVENNESS_TOLERANCE",
    "DEFAULT_MAX_GAP_MS",
    "DEFAULT_MIN_ALTERNATIONS",
    "DEFAULT_MIN_GAP_MS",
    "MAX_INTERVAL_SEMITONES",
    "Trill",
    "apply_trills",
    "find_trills",
    "find_trills_in_hands",
    "to_trill_mark",
]

#: Six pitch changes, so a qualifying run is at least seven notes. A mordent or a turn is shorter
#: and is left as written; other ornaments are ignored by design.
DEFAULT_MIN_ALTERNATIONS = 6

#: A whole tone. A minor third is already a measured figure, not a trill.
MAX_INTERVAL_SEMITONES = 2

#: How far consecutive gaps may differ from their average, as a fraction. Same number as tresillos:
#: roughly the jitter a steady player shows. Wider than this and ordinary fast playing starts being
#: read as an ornament.
DEFAULT_EVENNESS_TOLERANCE = 0.12

#: Slowest gap that still counts as an ornament, in milliseconds. A corchea at a slow negra is
#: longer than this; a trill is not.
DEFAULT_MAX_GAP_MS = 160.0

#: Fastest gap that still counts as an alternation rather than a chord. Near-simultaneous notes are
#: grouped on raw times (D-04); a pair inside that window is one attack, not a trill.
DEFAULT_MIN_GAP_MS = 25.0


@dataclass(frozen=True)
class Trill:
    """One detected alternation, still a suggestion until the reader accepts it."""

    hand: PrintedHand
    #: Inclusive index of the first note of the run in that hand's time-ordered events.
    start_index: int
    #: Exclusive index of the first note after the run.
    end_index: int
    lower_midi: int
    upper_midi: int
    #: Wall-clock start of the first note, in seconds.
    start_seconds: float
    #: Wall-clock start of the last note, in seconds.
    end_seconds: float
    #: Average inner gap, in milliseconds.
    gap_ms: float
    frame_ms: float

    @property
    def alternations(self) -> int:
        return self.end_index - self.start_index - 1

    @property
    def note_count(self) -> int:
        return self.end_index - self.start_index

    @property
    def lower_row(self) -> int:
        return midi_to_row(self.lower_midi)

    @property
    def upper_row(self) -> int:
        return midi_to_row(self.upper_midi)

    @property
    def from_column(self) -> int:
        return frame_of_seconds(self.start_seconds, self.frame_ms)

    @property
    def to_column(self) -> int:
        """Half-open: the column after the last onset, so that onset is included in the range."""
        return frame_of_seconds(self.end_seconds, self.frame_ms) + 1


def to_trill_mark(trill: Trill) -> TrillMark:
    """The stored / wire form: a frame range on one hand, and the two rows it collapses."""
    return TrillMark(
        hand=trill.hand,
        from_column=trill.from_column,
        to_column=max(trill.to_column, trill.from_column + 1),
        lower_row=trill.lower_row,
        upper_row=trill.upper_row,
        alternations=trill.alternations,
    )


def find_trills(
    events: Sequence[NoteEvent],
    *,
    hand_for: Callable[[NoteEvent], PrintedHand | None] | None = None,
    frame_ms: float = DEFAULT_FRAME_MS,
    min_alternations: int = DEFAULT_MIN_ALTERNATIONS,
    max_interval: int = MAX_INTERVAL_SEMITONES,
    evenness_tolerance: float = DEFAULT_EVENNESS_TOLERANCE,
    min_gap_ms: float = DEFAULT_MIN_GAP_MS,
    max_gap_ms: float = DEFAULT_MAX_GAP_MS,
) -> list[Trill]:
    """Every qualifying alternation, non-overlapping, in time order.

    ``hand_for`` assigns a staff. When omitted, the event's own ``hand`` is used, so a test can pin
    the split without building a matrix. Events with no hand, and events a reader took off the
    recording, are skipped.
    """
    assign = hand_for if hand_for is not None else (lambda event: _pinned_hand(event))
    by_hand: dict[PrintedHand, list[NoteEvent]] = {"right": [], "left": []}
    for event in events:
        if event.removed:
            continue
        hand = assign(event)
        if hand not in by_hand:
            continue
        by_hand[hand].append(event)

    found: list[Trill] = []
    for hand, stream in by_hand.items():
        ordered = sorted(stream, key=lambda event: (event.start, event.midi_note))
        found.extend(
            _trills_in_stream(
                hand,
                ordered,
                frame_ms=frame_ms,
                min_alternations=min_alternations,
                max_interval=max_interval,
                evenness_tolerance=evenness_tolerance,
                min_gap_ms=min_gap_ms,
                max_gap_ms=max_gap_ms,
            )
        )
    found.sort(key=lambda trill: (trill.start_seconds, trill.hand))
    return found


def find_trills_in_hands(events: Sequence[NoteEvent], hands: TimeHands) -> list[Trill]:
    """Detect on raw times, using the split matrix only to say which hand played each note."""

    def hand_for(event: NoteEvent) -> PrintedHand | None:
        pinned = _pinned_hand(event)
        if pinned is not None:
            return pinned
        return _hand_from_matrix(event, hands)

    return find_trills(events, hand_for=hand_for, frame_ms=hands.frame_ms)


def apply_trills(hands: TimeHands, trills: Sequence[TrillMark]) -> TimeHands:
    """Collapse accepted trills on a *copy* of the hands: one held lower note, the rest silent.

    The recording is not touched. Printed duration is the gap to the next remaining onset in the
    same hand (D-14), so deleting the storm is what makes the lower note last for the run.
    """
    if not trills:
        return hands

    edited = copy.deepcopy(hands)
    planes = {"right": edited.right, "left": edited.left}

    for mark in trills:
        plane = planes[mark.hand]
        start = mark.from_column
        end = min(mark.to_column, plane.frame_count)
        if end <= start:
            continue
        for row in (mark.lower_row, mark.upper_row):
            if not (0 <= row < KEY_COUNT):
                continue
            _silence_run(plane.grid, row, start, end, sustain=SUSTAIN, silence=SILENCE)
        plane.grid[mark.lower_row, start] = ONSET
        if end - start > 1:
            plane.grid[mark.lower_row, start + 1 : end] = SUSTAIN
    return edited


def _silence_run(grid, row: int, start: int, end: int, *, sustain: int, silence: int) -> None:
    """Clear both pitches across the range, including a sustain tail that outlives the last onset."""
    column = start
    while column < end:
        if grid[row, column] == ONSET:
            tail = column + 1
            while tail < grid.shape[1] and grid[row, tail] == sustain:
                tail += 1
            grid[row, column:tail] = silence
            column = tail
            continue
        if grid[row, column] == sustain:
            grid[row, column] = silence
        column += 1


def _trills_in_stream(
    hand: PrintedHand,
    events: Sequence[NoteEvent],
    *,
    frame_ms: float,
    min_alternations: int,
    max_interval: int,
    evenness_tolerance: float,
    min_gap_ms: float,
    max_gap_ms: float,
) -> list[Trill]:
    found: list[Trill] = []
    index = 0
    while index + min_alternations < len(events):
        match = _trill_from(
            hand,
            events,
            index,
            frame_ms=frame_ms,
            min_alternations=min_alternations,
            max_interval=max_interval,
            evenness_tolerance=evenness_tolerance,
            min_gap_ms=min_gap_ms,
            max_gap_ms=max_gap_ms,
        )
        if match is None:
            index += 1
            continue
        found.append(match)
        index = match.end_index
    return found


def _trill_from(
    hand: PrintedHand,
    events: Sequence[NoteEvent],
    start: int,
    *,
    frame_ms: float,
    min_alternations: int,
    max_interval: int,
    evenness_tolerance: float,
    min_gap_ms: float,
    max_gap_ms: float,
) -> Trill | None:
    first = events[start]
    second = events[start + 1]
    pitches = {first.midi_note, second.midi_note}
    if len(pitches) != 2:
        return None
    lower, upper = min(pitches), max(pitches)
    if upper - lower > max_interval:
        return None
    first_gap = (second.start - first.start) * MS_PER_SECOND
    if not (min_gap_ms <= first_gap <= max_gap_ms):
        return None

    gaps = [first_gap]
    cursor = start + 2
    while cursor < len(events):
        previous = events[cursor - 1]
        nxt = events[cursor]
        if nxt.midi_note not in pitches or nxt.midi_note == previous.midi_note:
            break
        gap = (nxt.start - previous.start) * MS_PER_SECOND
        if not (min_gap_ms <= gap <= max_gap_ms):
            break
        gaps.append(gap)
        cursor += 1

    if cursor - start - 1 < min_alternations:
        return None
    if not _gaps_are_even(gaps, evenness_tolerance):
        return None
    last = events[cursor - 1]
    return Trill(
        hand=hand,
        start_index=start,
        end_index=cursor,
        lower_midi=lower,
        upper_midi=upper,
        start_seconds=first.start,
        end_seconds=last.start,
        gap_ms=sum(gaps) / len(gaps),
        frame_ms=frame_ms,
    )


def _gaps_are_even(gaps: Sequence[float], tolerance: float) -> bool:
    mean = sum(gaps) / len(gaps)
    if mean <= 0:
        return False
    return all(abs(gap - mean) / mean <= tolerance for gap in gaps)


def _pinned_hand(event: NoteEvent) -> PrintedHand | None:
    if event.hand in ("right", "left"):
        return event.hand  # type: ignore[return-value]
    return None


def _hand_from_matrix(event: NoteEvent, hands: TimeHands) -> PrintedHand | None:
    row = event.midi_note - LOWEST_MIDI
    if not (0 <= row < KEY_COUNT):
        return None
    column = frame_of_seconds(event.start, hands.frame_ms)
    for delta in (0, -1, 1, -2, 2):
        nearby = column + delta
        if nearby < 0:
            continue
        if nearby < hands.right.frame_count and hands.right.cell(row, nearby) == ONSET:
            return "right"
        if nearby < hands.left.frame_count and hands.left.cell(row, nearby) == ONSET:
            return "left"
    return None
