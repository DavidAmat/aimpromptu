"""The time frames of the audio, the cuts, and the table from the piece to the original audio.

Implementation 08, plan section 9.2 (the answer to Q-1). A **time frame** is 10 ms: 160 samples of
the 16 kHz ``normalized.wav``, one MuScriptor frame, and one column of the piano matrix notation at
``frameMs = 10``. The audio and the notes therefore share one axis.

A **cut** is a range of frames ``[startFrame, endFrame)`` of the original audio that the user
deleted. The file on disk never changes: the cuts are stored in ``metadata.json`` and the **kept**
frames are joined end to end in memory. The joined frames are the frames of the **piece**, which is
shorter than the original by the length of the cuts. Notes, the piano matrix notation, the hand
split and the piano sheet all work in the frames of the piece.

:class:`FrameTable` links the two: one row per kept range, ``(pieceStart, originalStart, length)``
in frames. Any frame or range converts with one ``searchsorted`` in that table, whatever the length
of the piece. The player uses it to jump over the cuts, and the waveform and the piano roll
visualization use it to stay aligned (Phase 6 and Phase 7).

:func:`join_kept` builds the audio of the piece for the engine. At each join a 5 ms fade out and a
5 ms fade in, inside the kept samples, avoid a click that could be read as a note, without changing
the number of frames.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np

__all__ = [
    "FADE_MS",
    "FRAME_MS",
    "SAMPLES_PER_FRAME",
    "SAMPLE_RATE",
    "FrameTable",
    "frame_count",
    "frame_peaks",
    "join_kept",
    "normalize_cuts",
]

#: One time frame, in milliseconds.
FRAME_MS = 10
#: The rate of ``normalized.wav`` and of MuScriptor.
SAMPLE_RATE = 16_000
SAMPLES_PER_FRAME = SAMPLE_RATE * FRAME_MS // 1000
#: The fade at each side of a join.
FADE_MS = 5


def frame_count(samples: int) -> int:
    """How many frames cover ``samples`` samples. A last partial frame counts as one frame."""
    return math.ceil(int(samples) / SAMPLES_PER_FRAME)


def frame_peaks(samples: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """The lowest and the highest sample of every time frame, for the Audio tab's waveform.

    One pair per frame, so the page can zoom down to a single frame (the step a cut snaps to) from
    one request, and every pixel of the waveform falls on the same axis as the cuts. The values are
    ``int8``, scaled so the loudest sample of the audio is 127: 2 bytes per frame, 38 KB for the
    189 s of Superestrella. The third value is that loudest sample, for a reader that wants the
    real amplitude back.
    """
    total = frame_count(len(samples))
    if total == 0:
        empty = np.zeros(0, dtype=np.int8)
        return empty, empty, 0.0
    padded = np.zeros(total * SAMPLES_PER_FRAME, dtype=np.float32)
    padded[: len(samples)] = samples
    frames = padded.reshape(total, SAMPLES_PER_FRAME)
    low, high = frames.min(axis=1), frames.max(axis=1)
    peak = float(max(abs(float(low.min())), abs(float(high.max()))))
    scale = 127.0 / peak if peak > 0 else 0.0
    return (
        np.round(low * scale).astype(np.int8),
        np.round(high * scale).astype(np.int8),
        peak,
    )


def normalize_cuts(
    cuts: Iterable[Sequence[int]], total_frames: int | None = None
) -> list[tuple[int, int]]:
    """Sorted, clipped to the audio, empty ranges dropped, overlapping or touching ranges merged.

    Two cuts that touch (``[a, b)`` and ``[b, c)``) are one cut ``[a, c)``: they delete the same
    frames, so they are stored the same way, and saving them twice is not a change.
    """
    ranges: list[tuple[int, int]] = []
    for pair in cuts:
        start, end = int(pair[0]), int(pair[1])
        if total_frames is not None:
            start, end = max(0, start), min(int(total_frames), end)
        start = max(0, start)
        if end > start:
            ranges.append((start, end))
    ranges.sort()
    merged: list[tuple[int, int]] = []
    for start, end in ranges:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


@dataclass(frozen=True)
class FrameTable:
    """From a frame of the piece to a frame of the original audio, one row per kept range."""

    piece_start: np.ndarray
    original_start: np.ndarray
    length: np.ndarray
    #: Frames of the original audio.
    total_frames: int

    @classmethod
    def from_cuts(cls, cuts: Iterable[Sequence[int]], total_frames: int) -> "FrameTable":
        total = int(total_frames)
        piece, original, length = [], [], []
        cursor = 0
        kept_so_far = 0
        for start, end in [*normalize_cuts(cuts, total), (total, total)]:
            if start > cursor:
                piece.append(kept_so_far)
                original.append(cursor)
                length.append(start - cursor)
                kept_so_far += start - cursor
            cursor = max(cursor, end)
        return cls(
            piece_start=np.asarray(piece, dtype=np.int64),
            original_start=np.asarray(original, dtype=np.int64),
            length=np.asarray(length, dtype=np.int64),
            total_frames=total,
        )

    @property
    def piece_frames(self) -> int:
        """Frames of the piece: the original minus every cut."""
        return int(self.length.sum())

    @property
    def is_whole(self) -> bool:
        """No cut: the piece is the original audio."""
        return self.piece_frames == self.total_frames

    def cuts(self) -> list[tuple[int, int]]:
        """The cuts this table was made from, normalized."""
        out, cursor = [], 0
        for start, length in zip(self.original_start.tolist(), self.length.tolist()):
            if start > cursor:
                out.append((cursor, start))
            cursor = start + length
        if cursor < self.total_frames:
            out.append((cursor, self.total_frames))
        return out

    def _row(self, piece_frames: np.ndarray) -> np.ndarray:
        rows = np.searchsorted(self.piece_start, piece_frames, side="right") - 1
        return np.clip(rows, 0, max(0, len(self.piece_start) - 1))

    def to_original(self, piece_frame: int | np.ndarray) -> int | np.ndarray:
        """The original frame of a frame of the piece. The end of the piece maps to the end of the
        last kept range."""
        frames = np.asarray(piece_frame, dtype=np.int64)
        if len(self.piece_start) == 0:
            result = np.zeros_like(frames)
        else:
            rows = self._row(frames)
            result = self.original_start[rows] + frames - self.piece_start[rows]
        return int(result) if result.ndim == 0 else result

    def to_piece(self, original_frame: int | np.ndarray) -> int | np.ndarray:
        """The piece frame of an original frame. A frame inside a cut maps to the first kept frame
        after the cut (the place the player lands when it jumps over it)."""
        frames = np.asarray(original_frame, dtype=np.int64)
        if len(self.original_start) == 0:
            result = np.zeros_like(frames)
        else:
            rows = np.searchsorted(self.original_start, frames, side="right") - 1
            before = rows < 0
            rows = np.clip(rows, 0, len(self.original_start) - 1)
            offset = frames - self.original_start[rows]
            inside = offset < self.length[rows]
            result = np.where(
                inside,
                self.piece_start[rows] + offset,
                # In the cut after this row: the start of the next row, or the end of the piece.
                self.piece_start[rows] + self.length[rows],
            )
            result = np.where(before, 0, result)
        return int(result) if result.ndim == 0 else result

    def range_to_original(self, start: int, end: int) -> list[tuple[int, int]]:
        """A range of frames of the piece as ranges of the original: one per kept range it covers."""
        start, end = max(0, int(start)), min(self.piece_frames, int(end))
        out: list[tuple[int, int]] = []
        if end <= start:
            return out
        first = int(self._row(np.asarray(start)))
        for row in range(first, len(self.piece_start)):
            row_start = int(self.piece_start[row])
            row_end = row_start + int(self.length[row])
            if row_start >= end:
                break
            low, high = max(start, row_start), min(end, row_end)
            if high > low:
                origin = int(self.original_start[row]) - row_start
                out.append((low + origin, high + origin))
        return out

    def rows(self) -> list[dict[str, int]]:
        """The table for the frontend (camelCase, frames)."""
        return [
            {"pieceStart": piece, "originalStart": original, "length": length}
            for piece, original, length in zip(
                self.piece_start.tolist(), self.original_start.tolist(), self.length.tolist()
            )
        ]


def join_kept(samples: np.ndarray, table: FrameTable, *, fade_ms: float = FADE_MS) -> np.ndarray:
    """The audio of the piece: the kept frames of ``samples`` joined end to end.

    Without a cut this is ``samples`` itself, untouched. With cuts, every join gets a linear fade
    out on the left and a fade in on the right, inside the kept samples, so the length in frames is
    exactly :attr:`FrameTable.piece_frames` (the last frame may be partial, as in the file).
    """
    signal = np.asarray(samples, dtype=np.float32)
    if table.is_whole:
        return signal
    fade = max(1, int(round(SAMPLE_RATE * fade_ms / 1000.0)))
    ramp = np.linspace(0.0, 1.0, fade, endpoint=False, dtype=np.float32)
    pieces = []
    last = len(table.original_start) - 1
    for row, (start, length) in enumerate(
        zip(table.original_start.tolist(), table.length.tolist())
    ):
        part = signal[start * SAMPLES_PER_FRAME : (start + length) * SAMPLES_PER_FRAME].copy()
        size = min(fade, len(part))
        if row > 0 and size:
            part[:size] *= ramp[:size]
        if row < last and size:
            part[-size:] *= ramp[:size][::-1]
        pieces.append(part)
    return np.concatenate(pieces) if pieces else np.zeros(0, dtype=np.float32)
