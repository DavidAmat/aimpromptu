"""The portable ``.pmn.json`` file: the default format for any future export (D-30).

A header, then the columns of :mod:`aitu_backend.pmn.columns` and the velocity::

    {"format": "aimpromptu-pmn", "version": 1,
     "lowestMidi": 21, "keys": 88, "frameMs": 10, "timeUnit": "ms",
     "durationMs": 189160, "title": "Superestrella",
     "id": [0, 1], "key": [39, 43], "onMs": [3070, 3363], "lenMs": [1220, 587],
     "hand": "lr", "velocity": [64, 64]}

``keys`` and ``lowestMidi`` say how a ``key`` becomes a MIDI note, so the file reads without this
code. ``frameMs`` is the time frame of the shared axis of the audio and the piano matrix notation
(plan section 9.2): a dense matrix at that step, or at any other, is derived from the times. The
times are milliseconds with at most one decimal, which keeps the pieces transcribed by ByteDance
exact; a MuScriptor piece has whole numbers only. Notes marked removed are not exported.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from aitu_backend.pmn.columns import decode_hands, encode_hands
from aitu_backend.pmn.notes import KEY_COUNT, LOWEST_MIDI, Notes

__all__ = ["FORMAT", "VERSION", "from_portable", "read_portable", "to_portable", "write_portable"]

FORMAT = "aimpromptu-pmn"
VERSION = 1
#: The shared time frame of the audio and the notes (plan section 9.2).
FRAME_MS = 10


def _numbers(values: np.ndarray) -> list[float | int]:
    rounded = np.round(values, 1)
    return [int(value) if value.is_integer() else value for value in rounded.tolist()]


def to_portable(notes: Notes, *, duration_ms: float, title: str | None = None) -> dict[str, Any]:
    live = notes.live().sorted()
    return {
        "format": FORMAT,
        "version": VERSION,
        "lowestMidi": LOWEST_MIDI,
        "keys": KEY_COUNT,
        "frameMs": FRAME_MS,
        "timeUnit": "ms",
        "durationMs": _numbers(np.array([duration_ms]))[0],
        "title": title,
        "id": live.id.tolist(),
        "key": live.key.tolist(),
        "onMs": _numbers(live.on_ms),
        "lenMs": _numbers(live.len_ms),
        "hand": encode_hands(live.hand),
        "velocity": live.velocity.tolist(),
    }


def from_portable(payload: dict[str, Any]) -> tuple[Notes, float, str | None]:
    """The notes, the duration in milliseconds and the title of a ``.pmn.json`` payload."""
    if payload.get("format") != FORMAT:
        raise ValueError(f"Not a {FORMAT} file (format is {payload.get('format')!r})")
    if int(payload.get("version", 0)) > VERSION:
        raise ValueError(
            f"{FORMAT} version {payload['version']} is newer than this reader ({VERSION})"
        )
    if (
        payload.get("lowestMidi", LOWEST_MIDI) != LOWEST_MIDI
        or payload.get("keys", KEY_COUNT) != KEY_COUNT
    ):
        raise ValueError(f"Only the {KEY_COUNT} keys from MIDI {LOWEST_MIDI} are supported")
    count = len(payload.get("id", []))
    notes = Notes(
        id=payload["id"],
        key=payload["key"],
        on_ms=payload["onMs"],
        len_ms=payload["lenMs"],
        hand=decode_hands(payload.get("hand") or "-" * count),
        velocity=payload.get("velocity") or (),
    )
    return notes, float(payload["durationMs"]), payload.get("title")


def write_portable(
    notes: Notes, path: Path, *, duration_ms: float, title: str | None = None
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = to_portable(notes, duration_ms=duration_ms, title=title)
    path.write_text(json.dumps(body, separators=(",", ":")), encoding="utf-8")
    return path


def read_portable(path: Path) -> tuple[Notes, float, str | None]:
    return from_portable(json.loads(path.read_text(encoding="utf-8")))
