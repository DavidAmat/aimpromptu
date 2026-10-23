"""The saved notes of an aimpromptu song part (``notes.pmn``) as :class:`Notes`, and the key of its ``sheet.json``.

``notes.pmn`` is the wire form of :mod:`aitu_backend.pmn.columns` plus ``removed`` (ids of the notes the user
deleted): the live notes keep their saved hand (``r``, ``l``, ``-`` = none yet).

In the research core this was ``sheet/pmn/load.py``, beside copies of ``aitu_backend.pmn`` (``notes``, ``columns``,
``dense``) and ``aitu_backend.matrix.keys``. The backend uses its own modules instead (implementation 03, Phase 1:
the copies were identical, imports aside), so only the loader stays here.
"""

from __future__ import annotations

import numpy as np

from aitu_backend.pmn.columns import decode_hands
from aitu_backend.pmn.notes import HAND_LEFT, HAND_NONE, HAND_RIGHT, Notes

__all__ = [
    "HAND_LEFT",
    "HAND_NONE",
    "HAND_RIGHT",
    "KEYS",
    "Notes",
    "key_of_sheet_json",
    "notes_from_pmn",
]

#: ``sheet.json`` ``keySignature`` -> fifths (sharps > 0, flats < 0)
KEYS = {
    "C": 0,
    "G": 1,
    "D": 2,
    "A": 3,
    "E": 4,
    "B": 5,
    "F#": 6,
    "C#": 7,
    "F": -1,
    "Bb": -2,
    "Eb": -3,
    "Ab": -4,
    "Db": -5,
    "Gb": -6,
    "Cb": -7,
}


def notes_from_pmn(body: dict) -> Notes:
    """The live notes of a ``notes.pmn`` body (the removed ones left out), with their saved hands."""
    removed = set(body.get("removed", []))
    keep = [i for i, nid in enumerate(body["id"]) if nid not in removed]
    hands = decode_hands(body.get("hand") or "-" * len(body["id"]))
    return Notes.build(
        key=np.asarray(body["key"])[keep],
        on_ms=np.asarray(body["onMs"], dtype=float)[keep],
        len_ms=np.asarray(body["lenMs"], dtype=float)[keep],
        hand=hands[keep],
    ).live()


def key_of_sheet_json(sheet_json: dict) -> int:
    return KEYS[sheet_json.get("keySignature") or "C"]
