"""The compact hand map: one character per onset, in canonical matrix order.

A four-minute piece has a few thousand onsets. Writing
``{"col": 12, "row": 39, "hand": "r"}`` for each would add ~100 KB of JSON that
merely restates ``rows``/``cols``, which the sparse COO payload already carries.
So the hand map is a **string parallel to the onsets**::

    "hands": "rrlrlllrr…"

Character ``i`` is the hand of onset ``i`` when onsets are read in canonical
``(column, row)`` order — the same order
:meth:`~aitu_backend.matrix.model.PianoMatrix.to_coo_payload` emits and the same
order the frontend gets in ``rows``/``cols``. One byte per note, no lookup
structure, and a consumer that walks the COO arrays can read the hand off the
same index it is already holding.

Consuming it is deliberately trivial::

    let onsetIndex = 0;
    for (let i = 0; i < rows.length; i += 1) {
      if (onset[i] === -1) continue;          // sustain: inherits its onset's hand
      const hand = hands[onsetIndex];          // "l" | "r"
      onsetIndex += 1;
    }

Sustains carry no character. They cannot disagree with their onset — a note is
played by one hand from strike to release — so a character per sustain would be
redundant data that could go out of sync.
"""

from __future__ import annotations

#: Wire characters. Short on purpose: this string is one per note.
RIGHT_CHAR = "r"
LEFT_CHAR = "l"
HAND_CHARS = (LEFT_CHAR, RIGHT_CHAR)

_CHAR_TO_HAND = {LEFT_CHAR: "left", RIGHT_CHAR: "right"}
_HAND_TO_CHAR = {"left": LEFT_CHAR, "right": RIGHT_CHAR}


def hand_char(hand: str) -> str:
    """``"left"`` -> ``"l"``, ``"right"`` -> ``"r"``."""
    try:
        return _HAND_TO_CHAR[hand]
    except KeyError as exc:
        raise ValueError(f"Unknown hand '{hand}'. Expected 'left' or 'right'") from exc


def char_hand(char: str) -> str:
    """``"l"`` -> ``"left"``, ``"r"`` -> ``"right"``."""
    try:
        return _CHAR_TO_HAND[char]
    except KeyError as exc:
        raise ValueError(f"Unknown hand character '{char}'. Expected 'l' or 'r'") from exc


def encode_hand_map(onset_ids: list[str], hand_map: dict[str, str]) -> str:
    """Build the compact string for ``onset_ids`` in the order they are given.

    ``onset_ids`` must be in canonical ``(column, row)`` order — pass
    :attr:`~aitu_backend.hands.events.DecodedMatrix.onset_ids`, which is.
    """
    missing = [onset_id for onset_id in onset_ids if onset_id not in hand_map]
    if missing:
        raise ValueError(
            f"{len(missing)} onset(s) have no hand assignment, first is {missing[0]!r}"
        )
    return "".join(hand_char(hand_map[onset_id]) for onset_id in onset_ids)


def decode_hand_map(onset_ids: list[str], encoded: str) -> dict[str, str]:
    """Inverse of :func:`encode_hand_map`.

    Raises when the string and the matrix disagree in length: that means the
    stored map belongs to a different matrix, and guessing which notes shifted
    would silently mis-color a score.
    """
    if len(encoded) != len(onset_ids):
        raise ValueError(
            f"Hand map has {len(encoded)} entries but the matrix has {len(onset_ids)} onsets; "
            "the map does not belong to this matrix"
        )
    return {onset_id: char_hand(char) for onset_id, char in zip(onset_ids, encoded)}


def is_valid(encoded: str) -> bool:
    """True when every character is a known hand."""
    return all(char in _CHAR_TO_HAND for char in encoded)


__all__ = [
    "HAND_CHARS",
    "LEFT_CHAR",
    "RIGHT_CHAR",
    "char_hand",
    "decode_hand_map",
    "encode_hand_map",
    "hand_char",
    "is_valid",
]
