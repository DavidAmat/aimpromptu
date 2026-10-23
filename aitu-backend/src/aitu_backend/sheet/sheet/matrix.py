"""The piano matrix notation side of F1: onset cells and matrix -> frames sheet.

The matrix holds, per hand, 88 rows x N columns of 40 ms; a cell is onset, sustain or silence. The
formats keep the onsets only (rule 5 of the plan: sustains are not important), so the round trip is
measured on **onset cells**: (hand, key, column) for every cell that is an onset in the matrix of
that hand. Notes without a hand (the old Mac matrices) are a third matrix.
"""

from __future__ import annotations

import numpy as np

from aitu_backend.sheet.sheet.data import FRAME_MS, Note, Sheet
from aitu_backend.pmn.dense import to_dense
from aitu_backend.matrix.keys import LOWEST_MIDI
from aitu_backend.pmn.notes import HAND_LEFT, HAND_NONE, HAND_RIGHT, Notes

__all__ = ["cells", "cells_of_sheet", "sheet_from_matrix"]

STAFF_OF_HAND = {HAND_RIGHT: 1, HAND_LEFT: 2, HAND_NONE: 0}
_SHARP = [
    ("C", 0),
    ("C", 1),
    ("D", 0),
    ("D", 1),
    ("E", 0),
    ("F", 0),
    ("F", 1),
    ("G", 0),
    ("G", 1),
    ("A", 0),
    ("A", 1),
    ("B", 0),
]
_FLAT = [
    ("C", 0),
    ("D", -1),
    ("D", 0),
    ("E", -1),
    ("E", 0),
    ("F", 0),
    ("G", -1),
    ("G", 0),
    ("A", -1),
    ("A", 0),
    ("B", -1),
    ("B", 0),
]


def cells(notes: Notes, frame_ms: float = FRAME_MS) -> set[tuple[int, int, int]]:
    """Onset cells (staff, midi, column) of the matrices of each hand (staff 0 = no hand)."""
    out: set[tuple[int, int, int]] = set()
    live = notes.live()
    if not len(live):
        return out
    duration = float((live.on_ms + live.len_ms).max()) + frame_ms
    for hand, staff in STAFF_OF_HAND.items():
        if not (live.hand == hand).any():
            continue
        grid = to_dense(live, frame_ms, duration, hand=hand)
        rows, cols = np.nonzero(grid == 1)
        out.update((staff, int(r) + LOWEST_MIDI, int(c)) for r, c in zip(rows, cols))
    return out


def cells_of_sheet(sheet: Sheet) -> set[tuple[int, int, int]]:
    """Onset cells of the notes of a frames sheet (inside the 88 keys)."""
    return {
        (n.staff, n.midi, n.frame)
        for n in sheet.notes
        if n.frame is not None and LOWEST_MIDI <= n.midi <= LOWEST_MIDI + 87
    }


def sheet_from_matrix(notes: Notes, *, key: int = 0, frame_ms: float = FRAME_MS) -> Sheet:
    """A frames sheet with one note per onset cell: pitch spelled with the key family (sharps in sharp
    keys and C, flats in flat keys: the vexflow-v2 rule), no figure, the hand of its matrix."""
    names = _FLAT if key < 0 else _SHARP
    out = []
    for staff, midi, col in sorted(cells(notes, frame_ms), key=lambda c: (c[2], c[0], c[1])):
        step, alter = names[midi % 12]
        out.append(
            Note(
                time=None,
                staff=staff,
                step=step,
                alter=alter,
                octave=(midi - alter) // 12 - 1,
                frame=col,
                hand_known=staff != 0,
            )
        )
    return Sheet(notes=out, clefs={1: "G2", 2: "F4"}, key=key).sort()
