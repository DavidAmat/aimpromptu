"""Shared loading / labelling helpers for the onset-IOI PoC.

Nothing here imports the aitu_backend package. The PoC reads the *stored
artifacts* of a transcription (``events.json`` plus the two persisted one-hand
matrices) and re-derives everything it needs, so it can never perturb the app.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# --------------------------------------------------------------------------
# Constants that mirror the app (kept local on purpose -- see module docstring)
# --------------------------------------------------------------------------

LOWEST_MIDI = 21          # matrix row 0 == MIDI 21 == A0
KEY_COUNT = 88
GRANULARITY_BEATS = {
    "redonda": 4.0, "blanca": 2.0, "negra": 1.0, "corchea": 0.5,
    "semicorchea": 0.25, "fusa": 0.125, "semifusa": 0.0625,
}

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = Path(__file__).resolve().parent.parent / "out"


def seconds_per_column(granularity: str, tempo_bpm: float) -> float:
    return GRANULARITY_BEATS[granularity] * 60.0 / tempo_bpm


def load_matrix(name: str) -> np.ndarray:
    """Dense 88 x N int8 grid from one of the app's sparse COO ``.npz`` files."""
    z = np.load(DATA / name, allow_pickle=True)
    grid = np.zeros(tuple(z["shape"]), dtype=np.int8)
    grid[z["row"], z["col"]] = z["data"]
    return grid


def load_events() -> tuple[list[dict], float, str]:
    payload = json.loads((DATA / "events.json").read_text())
    return payload["events"], float(payload["durationSeconds"]), payload["title"]


def infer_tempo_bpm(raw_columns: int, duration_seconds: float,
                    granularity: str = "semifusa") -> float:
    """The BPM the stored grids were written at.

    ``frames = ceil(duration / step)``, so the BPM is recoverable from the
    column count to well within a hundredth of a beat. We only need it to map an
    event's wall-clock onset onto a matrix column for the hand lookup; it never
    touches the interval statistics.
    """
    beats = GRANULARITY_BEATS[granularity]
    return raw_columns * beats * 60.0 / duration_seconds


# --------------------------------------------------------------------------
# Hand labelling
# --------------------------------------------------------------------------

@dataclass
class LabelReport:
    matched_right: int = 0
    matched_left: int = 0
    unmatched: int = 0
    out_of_range: int = 0
    offsets: dict[int, int] | None = None

    def describe(self) -> str:
        return (f"{self.matched_right} right, {self.matched_left} left, "
                f"{self.unmatched} unmatched, {self.out_of_range} out of range "
                f"(column offsets used: {self.offsets})")


def label_hands(events: list[dict], right: np.ndarray, left: np.ndarray,
                tempo_bpm: float, granularity: str = "semicorchea",
                search: tuple[int, ...] = (0, -1, 1, -2, 2)) -> tuple[list[str | None], LabelReport]:
    """Attach ``"R"``/``"L"`` to every raw event using the app's stored split.

    The two one-hand matrices are a *partition* of the transcription: every
    engine onset ends up in exactly one of them. So instead of re-running the
    beam-DP splitter we simply look each raw event up in the pair. The event
    keeps its **exact float onset time** -- the matrices are consulted for
    identity only, never for timing. ``search`` widens the lookup by a column or
    two because ``snap_note`` rounds an onset with a tolerance that can differ
    from a plain ``round()``.
    """
    step = seconds_per_column(granularity, tempo_bpm)
    frames = right.shape[1]
    labels: list[str | None] = []
    report = LabelReport(offsets={})
    for event in events:
        row = event["midiNote"] - LOWEST_MIDI
        if not 0 <= row < KEY_COUNT:
            labels.append(None)
            report.out_of_range += 1
            continue
        column = int(round(event["start"] / step))
        hand = None
        for delta in search:
            candidate = column + delta
            if not 0 <= candidate < frames:
                continue
            if right[row, candidate] == 1:
                hand, used = "R", delta
                break
            if left[row, candidate] == 1:
                hand, used = "L", delta
                break
        if hand is None:
            labels.append(None)
            report.unmatched += 1
            continue
        labels.append(hand)
        report.offsets[used] = report.offsets.get(used, 0) + 1
        if hand == "R":
            report.matched_right += 1
        else:
            report.matched_left += 1
    return labels, report


# --------------------------------------------------------------------------
# Chords -> attacks
# --------------------------------------------------------------------------

def collapse_attacks(onset_seconds: np.ndarray, window_ms: float = 20.0) -> np.ndarray:
    """Group near-simultaneous onsets into one attack; return the group starts.

    A chord is one rhythmic event even when the three keys land 8 ms apart, and
    without this step those 8 ms gaps would dominate the low end of the
    histogram. The rule is deliberately **non-chaining**: a group is opened by an
    onset and admits every later onset within ``window_ms`` *of the group's
    first onset*, not of the previous one. Single linkage would let a dense run
    of fast notes swallow itself one 19 ms hop at a time; this cannot.
    """
    times = np.sort(np.asarray(onset_seconds, dtype=float))
    if times.size == 0:
        return times
    window = window_ms / 1000.0
    starts = [times[0]]
    anchor = times[0]
    for t in times[1:]:
        if t - anchor > window:
            starts.append(t)
            anchor = t
    return np.asarray(starts)


def inter_onset_intervals_ms(attack_seconds: np.ndarray) -> np.ndarray:
    """Consecutive attack-to-attack gaps, in milliseconds."""
    return np.diff(np.asarray(attack_seconds, dtype=float)) * 1000.0
