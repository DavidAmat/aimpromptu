"""The wire form for the browser: one list per field instead of one object per note.

Plan section 6.4. The frontend copies each list once into a typed array and draws from the arrays
with no conversion::

    {"revision": 7, "handsRevision": 3, "durationMs": 189160,
     "id": [0, 1, 2], "key": [39, 43, 46], "onMs": [3070, 3363, 3364],
     "lenMs": [1220, 587, 137], "hand": "llr"}

* Only the live notes travel (a note marked removed is not drawn), in canonical order: by onset,
  then key.
* Times are whole milliseconds. ``lenMs`` is the rounded release minus the rounded onset, so the
  release the browser computes is the stored release rounded, and never shorter than 1 ms.
* ``hand`` is a string with one character per note: ``r``, ``l``, or ``-`` for a note with no hand
  yet. The same idea as the hand map of :mod:`aitu_backend.hands.encoding`.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from aitu_backend.pmn.notes import HAND_LEFT, HAND_NONE, HAND_RIGHT, Notes

__all__ = ["HAND_CHARS", "decode_hands", "encode_hands", "from_columns", "to_columns"]

#: One character per hand code, and back.
HAND_CHARS = {HAND_NONE: "-", HAND_RIGHT: "r", HAND_LEFT: "l"}
_CHAR_CODES = {char: code for code, char in HAND_CHARS.items()}
_LOOKUP = np.array([ord(HAND_CHARS[code]) for code in range(3)], dtype=np.uint8)


def encode_hands(hand: np.ndarray) -> str:
    """``[1, 2, 0]`` -> ``"rl-"``."""
    return _LOOKUP[np.asarray(hand, dtype=np.int64)].tobytes().decode("ascii")


def decode_hands(text: str) -> np.ndarray:
    """``"rl-"`` -> ``[1, 2, 0]``. Raises on any other character."""
    unknown = set(text) - set(_CHAR_CODES)
    if unknown:
        raise ValueError(f"hand holds {sorted(unknown)}; only 'r', 'l' and '-' are allowed")
    return np.array([_CHAR_CODES[char] for char in text], dtype=np.int8)


def to_columns(
    notes: Notes,
    *,
    revision: int | None = None,
    hands_revision: int | None = None,
    duration_ms: float | None = None,
) -> dict[str, Any]:
    """The live notes as the frontend receives them. The header fields are included when given."""
    live = notes.live().sorted()
    on = np.rint(live.on_ms).astype(np.int64)
    end = np.maximum(on + 1, np.rint(live.end_ms).astype(np.int64))
    payload: dict[str, Any] = {}
    if revision is not None:
        payload["revision"] = int(revision)
    if hands_revision is not None:
        payload["handsRevision"] = int(hands_revision)
    if duration_ms is not None:
        payload["durationMs"] = int(round(duration_ms))
    payload.update(
        {
            "id": live.id.tolist(),
            "key": live.key.tolist(),
            "onMs": on.tolist(),
            "lenMs": (end - on).tolist(),
            "hand": encode_hands(live.hand),
        }
    )
    return payload


def from_columns(payload: dict[str, Any]) -> Notes:
    """Notes from the columns form. ``hand`` may be absent (every note without a hand)."""
    try:
        ids, keys = payload["id"], payload["key"]
        on_ms, len_ms = payload["onMs"], payload["lenMs"]
    except KeyError as exc:
        raise ValueError(
            f"The columns form needs id, key, onMs and lenMs; {exc} is missing"
        ) from exc
    hand_text = payload.get("hand") or HAND_CHARS[HAND_NONE] * len(ids)
    if len(hand_text) != len(ids):
        raise ValueError(f"hand has {len(hand_text)} characters for {len(ids)} notes")
    return Notes(
        id=ids,
        key=keys,
        on_ms=on_ms,
        len_ms=len_ms,
        hand=decode_hands(hand_text),
        velocity=payload.get("velocity") or (),
    )
