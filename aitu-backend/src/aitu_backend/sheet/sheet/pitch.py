"""Spelled pitches: step letters and MIDI numbers (C4 = 60)."""

from __future__ import annotations

__all__ = ["STEPS", "pitch_to_midi"]

STEPS = "CDEFGAB"
_STEP_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def pitch_to_midi(step: str, alter: int, octave: int) -> int:
    """Spelled pitch to MIDI: C4 = 60."""
    return 12 * (octave + 1) + _STEP_PC[step] + alter
