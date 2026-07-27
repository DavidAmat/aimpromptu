"""Canonical 88-key tables: Spanish solfège, English names and MIDI numbers.

Row order is fixed for the whole project: index 0 is ``La-0`` (A0, MIDI 21),
index 87 is ``Do-8`` (C8, MIDI 108). Everything that needs a key name — the
matrix grid headers, the piano SVG, the notation builder — reads it from here.

Spanish names are the notation contract (see
``context/music/notation-logic/02-notation-spec.md``); English names exist for
the UI, which shows both.
"""

from __future__ import annotations

#: Chromatic set in the notation's Spanish solfège, starting at Do.
CHROMATIC_ES = [
    "Do",
    "Do#",
    "Re",
    "Re#",
    "Mi",
    "Fa",
    "Fa#",
    "Sol",
    "Sol#",
    "La",
    "La#",
    "Si",
]

#: Same order, English letter names. Sharps only — the matrix has no enharmonics.
CHROMATIC_EN = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

#: Number of keys on a grand piano; the matrix always has this many rows.
KEY_COUNT = 88

#: MIDI note number of row 0 (``La-0`` / A0).
LOWEST_MIDI = 21

_ES_TO_EN = dict(zip(CHROMATIC_ES, CHROMATIC_EN))


def build_grand_piano_rows() -> list[str]:
    """88-key row order in Spanish solfège, lowest to highest: ``La-0`` … ``Do-8``."""
    rows: list[str] = ["La-0", "La#-0", "Si-0"]
    for octave in range(1, 8):
        rows.extend(f"{note}-{octave}" for note in CHROMATIC_ES)
    rows.append("Do-8")
    assert len(rows) == KEY_COUNT
    return rows


def build_grand_piano_rows_en() -> list[str]:
    """Same 88 keys in English scientific pitch notation: ``A0`` … ``C8``."""
    return [es_to_en(name) for name in build_grand_piano_rows()]


def es_to_en(name: str) -> str:
    """``"Fa#-5"`` -> ``"F#5"``. Raises ``ValueError`` on an unknown name."""
    pitch, _, octave = name.rpartition("-")
    if not pitch or pitch not in _ES_TO_EN:
        raise ValueError(f"Unknown note name '{name}'")
    return f"{_ES_TO_EN[pitch]}{octave}"


def row_to_midi(row: int) -> int:
    """Matrix row index -> MIDI note number (row 0 = 21 = A0)."""
    if not 0 <= row < KEY_COUNT:
        raise ValueError(f"Row {row} outside the 88-key range")
    return LOWEST_MIDI + row


def midi_to_row(midi: int) -> int:
    """MIDI note number -> matrix row index. Raises outside the 88 keys."""
    row = midi - LOWEST_MIDI
    if not 0 <= row < KEY_COUNT:
        raise ValueError(f"MIDI note {midi} outside the 88-key range (21..108)")
    return row


def note_to_row(name: str) -> int:
    """Spanish note name -> matrix row index."""
    try:
        return _ROW_INDEX[name]
    except KeyError as exc:
        raise ValueError(f"Unknown note '{name}'. Expected La-0 ... Do-8") from exc


#: Row index of the two-hands split threshold: Do-4 (C4, middle C) and above is
#: the right hand (Appendix D of the matrix notation logic).
def _build_row_index() -> dict[str, int]:
    return {name: index for index, name in enumerate(build_grand_piano_rows())}


_ROW_INDEX = _build_row_index()

#: Do-4 / C4 / MIDI 60 — the right-hand threshold, inclusive.
MIDDLE_C_ROW = _ROW_INDEX["Do-4"]
