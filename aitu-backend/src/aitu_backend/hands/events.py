"""Matrix decoding: onsets, the sustains they own, and simultaneous onset groups.

The optimizer never sees cells. It sees **onset groups** — all notes struck in
one column — because that is the unit a pianist allocates hands over, and
because there are far fewer of them than there are cells (a four-minute piece is
~960 frames but a few hundred groups). Latency follows the group count, not the
matrix size.

Event identity: an onset is ``c{column}:r{row}``. A sustain run belongs to the
most recent onset in the same row, and a same-row ``1`` always starts a *new*
onset even when the row was already sounding — repeated strikes are distinct
events. Malformed data is reported in :attr:`DecodedMatrix.warnings`, never
silently deleted.

This module reads a :class:`~aitu_backend.matrix.model.PianoMatrix` directly.
The research PoC went through JSON envelopes because it was a separate process;
here the grid is already in memory and a round-trip would only lose time.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from aitu_backend.matrix.keys import KEY_COUNT, build_grand_piano_rows, row_to_midi
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.schemas.matrix import ONSET, SUSTAIN

_KEY_NAMES = build_grand_piano_rows()


@dataclass(frozen=True)
class NoteEvent:
    """One onset plus the sustain run it owns."""

    onset_id: str
    row: int
    column: int
    duration_frames: int
    onset_time: float
    duration_seconds: float
    #: ``row + 21``. Stored rather than derived: the cost model reads it millions
    #: of times per piece, and a property call was measurably the second hottest
    #: line in the search.
    midi: int = 0
    #: Every column this note occupies, onset first. Used to paint the split matrices.
    cells: tuple[int, ...] = ()

    @property
    def note(self) -> str:
        """Spanish solfège name, e.g. ``"Fa#-5"``."""
        return _KEY_NAMES[self.row]

    @property
    def end_time(self) -> float:
        return self.onset_time + self.duration_seconds

    @property
    def end_column(self) -> int:
        return self.column + self.duration_frames


@dataclass(frozen=True)
class OnsetGroup:
    """All onsets struck in the same frame, ascending by pitch.

    Pitch order matters: candidate partitions are described as low/high splits,
    and the interleaving cost counts pitch-order inversions.
    """

    column: int
    time_seconds: float
    events: tuple[NoteEvent, ...]

    @property
    def rows(self) -> tuple[int, ...]:
        return tuple(event.row for event in self.events)

    @property
    def midis(self) -> tuple[int, ...]:
        return tuple(event.midi for event in self.events)

    def __len__(self) -> int:
        return len(self.events)


@dataclass
class DecodedMatrix:
    """Canonical decoding of a one-hand matrix."""

    frame_count: int
    time_step_seconds: float
    events: list[NoteEvent]
    groups: list[OnsetGroup]
    warnings: list[str]

    def event_by_id(self) -> dict[str, NoteEvent]:
        return {event.onset_id: event for event in self.events}

    @property
    def onset_ids(self) -> list[str]:
        """Onset ids in canonical ``(column, row)`` order.

        This is the order the compact hand string indexes against, and the same
        order ``PianoMatrix.to_coo_payload`` emits its onsets in.
        """
        return [event.onset_id for event in self.events]


def decode_matrix(
    matrix: PianoMatrix,
    *,
    promote_orphan_sustains: bool = True,
) -> DecodedMatrix:
    """Decode a one-hand matrix into note events and onset groups.

    ``promote_orphan_sustains`` turns a ``-1`` with no preceding onset into an
    onset. A transcription or a hand-edited grid can produce one; dropping it
    would silently lose a note, so the default repairs and warns.
    """
    grid = matrix.grid
    frame_count = matrix.frame_count
    time_step = matrix.time_step_seconds
    warnings: list[str] = []

    # row -> (onset column, columns owned so far)
    open_events: dict[int, tuple[int, list[int]]] = {}
    finished: list[tuple[int, int, list[int]]] = []

    def close(row: int) -> None:
        onset_col, cells = open_events.pop(row)
        finished.append((onset_col, row, cells))

    # Only rows that sound at all can open an event; on a sparse matrix this is
    # the difference between scanning 88 rows per frame and scanning a handful.
    active_rows = np.nonzero(np.any(grid != 0, axis=1))[0].astype(int).tolist()

    for column in range(frame_count):
        frame = grid[:, column]
        for row in active_rows:
            cell = int(frame[row])
            if cell == ONSET:
                if row in open_events:
                    close(row)
                open_events[row] = (column, [column])
            elif cell == SUSTAIN:
                if row in open_events:
                    open_events[row][1].append(column)
                elif promote_orphan_sustains:
                    warnings.append(
                        f"Orphan sustain at column {column}, row {row} promoted to an onset"
                    )
                    open_events[row] = (column, [column])
                else:
                    warnings.append(f"Orphan sustain at column {column}, row {row} ignored")
            elif row in open_events:
                close(row)

    for row in list(open_events):
        close(row)

    finished.sort(key=lambda item: (item[0], item[1]))
    events = [
        NoteEvent(
            onset_id=f"c{onset_col}:r{row}",
            row=row,
            column=onset_col,
            duration_frames=len(cells),
            onset_time=onset_col * time_step,
            duration_seconds=len(cells) * time_step,
            midi=row_to_midi(row),
            cells=tuple(cells),
        )
        for onset_col, row, cells in finished
    ]

    by_column: dict[int, list[NoteEvent]] = {}
    for event in events:
        by_column.setdefault(event.column, []).append(event)
    groups = [
        OnsetGroup(
            column=column,
            time_seconds=column * time_step,
            events=tuple(sorted(by_column[column], key=lambda event: event.row)),
        )
        for column in sorted(by_column)
    ]

    return DecodedMatrix(
        frame_count=frame_count,
        time_step_seconds=time_step,
        events=events,
        groups=groups,
        warnings=warnings,
    )


def split_grids(
    decoded: DecodedMatrix,
    hand_map: dict[str, str],
) -> tuple[np.ndarray, np.ndarray]:
    """Paint aligned right/left ``88 x N`` grids from an onset -> hand mapping.

    Both grids are full size and frame-aligned, so the two staves stack and the
    piano-roll views can draw them together. Every cell of an onset's sustain run
    goes to the same hand as its onset — that is the invariant that makes
    ``combine(right, left) == original`` hold.
    """
    shape = (KEY_COUNT, decoded.frame_count)
    right = np.zeros(shape, dtype=np.int8)
    left = np.zeros(shape, dtype=np.int8)

    for event in decoded.events:
        target = right if hand_map[event.onset_id] == "right" else left
        for index, column in enumerate(event.cells):
            target[event.row, column] = ONSET if index == 0 else SUSTAIN

    return right, left


__all__ = [
    "DecodedMatrix",
    "NoteEvent",
    "OnsetGroup",
    "decode_matrix",
    "split_grids",
]
