"""The hands saved on the notes: the split read back from them, and the quick rule for a new note.

Before implementation 08 the hand split was a hidden computation that ran again on every read
(D-31). Phase 5 makes it a step: **Predict hands** runs the same split once, the user checks and
corrects it, and **Save** writes one hand per note into ``events.json``. From then on the two hand
matrices are painted from the saved hands, which is one NumPy pass instead of 0.3 to 4.3 s of
inference (plan sections 4 and 9.7). A piece whose live notes do not all have a hand keeps the old
behaviour: the inference, then the reader's pinned hands on top.

Three functions:

* :func:`split_with_saved_hands`: the two hand matrices from the saved hands. It paints the same
  cells the inference would have painted for the same hand per onset, so a piece gives the same
  sheet before and after its hands are saved (checked on the whole library in the Phase 5 report).
* :func:`hands_of_split`: any split, read back as one hand per note id. **Predict hands** and the
  first hand change on the piano sheet use it.
* :func:`quick_hand` and :func:`fill_quick_hands`: the hand of a note added after the split, taken
  from the notes around it, so the Hands tab stays usable after a small edit (plan section 8.3).
"""

from __future__ import annotations

from typing import Iterable

import numpy as np

from aitu_backend.matrix.keys import LOWEST_MIDI, MIDDLE_C_ROW
from aitu_backend.matrix.time_grid import DEFAULT_FRAME_MS, validate_frame_ms
from aitu_backend.progress import BaseProgress
from aitu_backend.schemas.matrix import ONSET, Hand, MatrixProcessingStep
from aitu_backend.transcription.artifacts import DEFAULT_ARTIFACTS, ArtifactConfig
from aitu_backend.transcription.engine import NoteEvent
from aitu_backend.transcription.events_to_matrix import events_to_time_matrix
from aitu_backend.transcription.leakage import DEFAULT_LEAKAGE, LeakageConfig
from aitu_backend.transcription.time_pipeline import TimeHands

__all__ = [
    "NEAR_SECONDS",
    "fill_quick_hands",
    "hands_complete",
    "placed_ids",
    "hands_of_split",
    "live_events",
    "quick_hand",
    "split_with_saved_hands",
]

#: How far in time a note counts as "around" a new note for the quick rule, in seconds.
NEAR_SECONDS = 1.0

#: Hand codes of the paint: 0 is no hand.
_RIGHT, _LEFT = 1, 2
_CODE = {"right": _RIGHT, "left": _LEFT}

#: The pitch rule when there is nothing to copy: middle C and above is the right hand.
_MIDDLE_C_MIDI = MIDDLE_C_ROW + LOWEST_MIDI


def live_events(events: Iterable[NoteEvent]) -> list[NoteEvent]:
    """The notes that were played: every note not marked removed."""
    return [event for event in events if not event.removed]


def placed_ids(
    events: Iterable[NoteEvent],
    duration_seconds: float,
    *,
    frame_ms: float = DEFAULT_FRAME_MS,
    leakage: LeakageConfig | None = DEFAULT_LEAKAGE,
    artifacts: ArtifactConfig | None = DEFAULT_ARTIFACTS,
) -> set[int]:
    """The ids of the live notes the piano sheet's matrix places at ``frame_ms``.

    A note it does not place (shorter than one column, dropped by a filter, or sharing its column
    with an earlier note of its key) is left out of the piano sheet and gets no hand from the split.
    About 20 ms for 4,000 notes.
    """
    played = live_events(events)
    if not played:
        return set()
    step = validate_frame_ms(frame_ms)
    build = events_to_time_matrix(
        played,
        max(duration_seconds, step / 1000.0),
        frame_ms=step,
        leakage=leakage,
        artifacts=artifacts,
    )
    return set(build.event_ids.values())


def hands_complete(events: Iterable[NoteEvent], placed: set[int] | None = None) -> bool:
    """Does every live note have a hand? True for a piece with no live note.

    With ``placed`` (:func:`placed_ids`), only the notes the piano sheet places count: a note the
    split cannot place stays without a hand (red on the Hands tab) and does not keep the hands
    from being complete (the user's rule of 2026-10-01). A note with no id yet (added in this
    edit) counts.
    """
    return all(
        event.hand
        for event in events
        if not event.removed and (placed is None or event.id is None or event.id in placed)
    )


# --------------------------------------------------------------------------- the quick rule


def quick_hand(
    midi: int,
    start: float,
    reference: list[NoteEvent],
    *,
    arrays: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None = None,
) -> str:
    """The hand of a new note, from the notes with a hand around it.

    The plan's rule is "the hand of the nearest note in time, or by pitch when there is no
    neighbour". Nearest in time alone is ambiguous in a chord, where a left-hand bass and a
    right-hand melody start together, so the rule is: among the notes that start within
    :data:`NEAR_SECONDS` of the new one or are still sounding at its onset, the one closest in
    pitch gives its hand (the nearest in time breaks a tie). With no such note, middle C and above
    is the right hand.
    """
    starts, ends, midis, codes = arrays if arrays is not None else _reference_arrays(reference)
    if starts.size:
        near = (np.abs(starts - start) <= NEAR_SECONDS) | ((starts <= start) & (ends > start))
        if near.any():
            index = np.flatnonzero(near)
            order = np.lexsort((np.abs(starts[index] - start), np.abs(midis[index] - midi)))
            return "right" if codes[index[order[0]]] == _RIGHT else "left"
    return "right" if midi >= _MIDDLE_C_MIDI else "left"


def _reference_arrays(
    reference: list[NoteEvent],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    handed = [event for event in reference if event.hand and not event.removed]
    return (
        np.array([event.start for event in handed], dtype=np.float64),
        np.array([event.end for event in handed], dtype=np.float64),
        np.array([event.midi_note for event in handed], dtype=np.int64),
        np.array([_CODE[event.hand] for event in handed], dtype=np.int8),  # type: ignore[index]
    )


def fill_quick_hands(events: list[NoteEvent], placed: set[int] | None = None) -> list[NoteEvent]:
    """Give every live note without a hand the quick rule's hand, marked as guessed.

    The notes it copies from are the ones that already had a hand, so two new notes side by side
    do not copy each other. Returns the notes it changed. With ``placed``, a note the piano sheet
    does not place keeps no hand (it stays red for the user to decide); a new note (no id yet) is
    always given one.
    """
    missing = [
        event
        for event in events
        if not event.removed
        and not event.hand
        and (placed is None or event.id is None or event.id in placed)
    ]
    if not missing:
        return []
    arrays = _reference_arrays(events)
    for event in missing:
        event.hand = quick_hand(event.midi_note, event.start, [], arrays=arrays)
        event.hand_guessed = True
    return missing


# --------------------------------------------------------------------------- saved hands to cells


def split_with_saved_hands(
    events: list[NoteEvent],
    duration_seconds: float,
    *,
    frame_ms: float = DEFAULT_FRAME_MS,
    title: str | None = None,
    leakage: LeakageConfig | None = DEFAULT_LEAKAGE,
    artifacts: ArtifactConfig | None = DEFAULT_ARTIFACTS,
    reporter: BaseProgress | None = None,
) -> TimeHands:
    """The two hand matrices painted from the hands saved on the notes. No inference runs.

    The whole keyboard is built exactly as :func:`impose_granularity_and_split` builds it (the
    same grouping, snapping and filters), so the cells are the same. Each onset cell then takes
    the hand of the note that owns it, and each sustain the hand of its onset, which is how the
    inference paints its answer (:func:`aitu_backend.hands.events.split_grids`). An onset with no
    note behind it, which does not happen for a matrix built from notes, falls back to the pitch
    rule.
    """
    step = validate_frame_ms(frame_ms)
    played = live_events(events)
    build = events_to_time_matrix(
        played,
        duration_seconds,
        frame_ms=step,
        title=title,
        leakage=leakage,
        artifacts=artifacts,
        reporter=reporter,
    )
    hand_by_id = {
        event.id: _CODE[event.hand]
        for event in played
        if event.id is not None and event.hand in _CODE
    }
    right_grid, left_grid = _paint(build.matrix.grid, build.event_ids, hand_by_id)
    common = {"processing_step": MatrixProcessingStep.TWO_HANDS}
    return TimeHands(
        frame_ms=step,
        right=build.matrix.with_grid(right_grid, hand=Hand.RIGHT.value, **common),
        left=build.matrix.with_grid(left_grid, hand=Hand.LEFT.value, **common),
        unsplit=build.matrix,
        build=build,
    )


def _paint(
    grid: np.ndarray,
    event_ids: dict[tuple[int, int], int],
    hand_by_id: dict[int, int],
) -> tuple[np.ndarray, np.ndarray]:
    """Split ``grid`` into two grids by the hand of each run's first cell.

    A run starts at an onset, or at a sustain with silence before it (an orphan, which the
    inference's decoder turns into an onset, so it is written as one here too). Every cell of a
    run takes the hand of its start, found by carrying the start's column forward along the row.
    """
    rows, columns = grid.shape
    sounding = grid != 0
    before = np.zeros_like(sounding)
    before[:, 1:] = sounding[:, :-1]
    starts = (grid == ONSET) | (sounding & ~before)

    labels = np.zeros_like(grid, dtype=np.int8)
    start_rows, start_columns = np.nonzero(starts)
    labels[start_rows, start_columns] = np.where(start_rows >= MIDDLE_C_ROW, _RIGHT, _LEFT)
    for (column, row), note_id in event_ids.items():
        code = hand_by_id.get(note_id)
        if code is not None and starts[row, column]:
            labels[row, column] = code

    position = np.where(starts, np.arange(columns)[None, :], 0)
    np.maximum.accumulate(position, axis=1, out=position)
    owner = labels[np.arange(rows)[:, None], position]
    owner[~sounding] = 0

    cells = grid.copy()
    cells[starts] = ONSET
    right = np.where(owner == _RIGHT, cells, 0).astype(np.int8)
    left = np.where(owner == _LEFT, cells, 0).astype(np.int8)
    return right, left


# --------------------------------------------------------------------------- a split to note ids


def hands_of_split(
    split: TimeHands, events: list[NoteEvent], *, guess_unplaced: bool = True
) -> dict[int, str]:
    """``note id -> "right" | "left"`` for every live note, read off a split.

    A note placed in the matrix takes the hand of its onset cell. A note the matrix did not place
    (shorter than one column, dropped by a filter, merged into its neighbour, or sharing a cell with
    an earlier note of its key) takes the quick rule's hand from the placed notes, so every live
    note gets one and the hands are complete.

    ``guess_unplaced=False`` leaves those notes out instead. **Predict hands** does this (the user's
    rule after Phase 6): such a note is often one the engine imagined, so the page shows it in red
    for the user to delete or to give a hand, rather than hiding a guess in it.
    """
    right, left = split.right.grid, split.left.grid
    hand: dict[int, str] = {}
    for (column, row), note_id in split.build.event_ids.items():
        if right[row, column] == ONSET:
            hand[note_id] = "right"
        elif left[row, column] == ONSET:
            hand[note_id] = "left"

    played = live_events(events)
    if not guess_unplaced:
        live_ids = {event.id for event in played}
        return {note_id: side for note_id, side in hand.items() if note_id in live_ids}
    placed = [
        event.model_copy(update={"hand": hand[event.id]}) for event in played if event.id in hand
    ]
    arrays = _reference_arrays(placed)
    for event in played:
        if event.id is not None and event.id not in hand:
            hand[event.id] = quick_hand(event.midi_note, event.start, [], arrays=arrays)
    return hand
