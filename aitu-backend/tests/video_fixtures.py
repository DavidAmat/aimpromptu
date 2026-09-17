"""One video drawn on the spot: black roll, rectangles falling at a known speed.

Shared by `test_video_stitch.py` and `test_video_piece.py` so the two read the
same picture. It is not a test module — it draws the video the tests assert
against, and every note in it is arithmetic rather than a guess: a rectangle
whose tip starts at row ``tip_at_frame_zero`` and falls ``TRAVEL`` rows per
sampled frame crosses the upper line at a time the drawing already knows.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from aitu_backend.schemas.video import (
    WHITE_PITCH_CLASSES,
    WHITE_WITH_BLACK_AFTER,
    BlackBorder,
    Calibration,
    PianoRect,
    ScrollSpeed,
    VideoMeasurement,
    VideoMetadata,
)
from aitu_backend.storage import paths
from aitu_backend.video import geometry, images, store

UUID = "stitched-video"

#: The picture. Narrow and short on purpose: the test is about the arithmetic.
WIDTH, HEIGHT, UPPER = 260, 340, 300
KEY = 26.0
#: How far the roll falls between one sampled frame and the next, and how often
#: we look at the video. Ten frames a second is the plan's granularity (V-04).
TRAVEL = 17.0
SAMPLE_MS = 100.0
SPEED = TRAVEL * 1000.0 / SAMPLE_MS
FRAMES = 40
#: Rows above the upper line the strike light makes unreadable (V-08). One row,
#: because this drawing has no strike light and the arithmetic is easier to read.
GUARD = 1.0


@dataclass(frozen=True)
class Drawn:
    """One rectangle drawn into the video: which key, and where it starts."""

    key_index: int
    #: Row of the rectangle's tip — its lowest row — in the very first frame.
    tip_at_frame_zero: float
    height: int

    def onset_seconds(self) -> float:
        """When its tip reaches the upper line, from the drawing alone."""
        return (UPPER - self.tip_at_frame_zero) / SPEED

    def release_seconds(self) -> float:
        return self.onset_seconds() + self.height / SPEED


def calibration() -> Calibration:
    borders = [i * KEY for i in range(11)]
    first = WHITE_PITCH_CLASSES.index(9)
    black = [
        BlackBorder(left=(i + 1) * KEY - 0.29 * KEY, right=(i + 1) * KEY + 0.29 * KEY)
        for i in range(len(borders) - 2)
        if WHITE_PITCH_CLASSES[(first + i) % 7] in WHITE_WITH_BLACK_AFTER
    ]
    return Calibration(
        image_width=WIDTH,
        image_height=HEIGHT,
        piano_rect=PianoRect(x=0.0, y=float(UPPER), width=float(WIDTH), height=40.0),
        upper_line=float(UPPER),
        white_borders=borders,
        black_borders=black,
        black_depth=12.0,
        first_white_pitch_class=9,
        first_white_octave=0,
        roll_top=0.0,
        guard_band=GUARD,
    )


def measurement() -> VideoMeasurement:
    return VideoMeasurement(
        scroll_speed=ScrollSpeed(
            px_per_frame=TRAVEL,
            px_per_second=SPEED,
            usable_pairs=FRAMES - 1,
            total_pairs=FRAMES - 1,
            stable=True,
        ),
        roll_top=0.0,
        guard_band=GUARD,
        offset_px=TRAVEL,
    )


def white_midi(index: int) -> int:
    whites = [key for key in geometry.keys(calibration()) if key.kind == "white"]
    return whites[index].midi


def draw_frame(index: int, drawn: list[Drawn]) -> np.ndarray:
    """One picture: a black roll with every rectangle at the row it has fallen to."""
    frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    for one in drawn:
        left = int(one.key_index * KEY) + 3
        right = int((one.key_index + 1) * KEY) - 3
        tip = one.tip_at_frame_zero + index * TRAVEL
        top = int(round(tip - one.height))
        bottom = int(round(tip))
        top, bottom = max(0, top), min(UPPER, bottom)
        if bottom > top:
            frame[top:bottom, left:right] = 235
    # The keyboard below the upper line, so the picture looks like what it is.
    frame[UPPER:, :] = 200
    return frame


def make_video(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, drawn: list[Drawn]) -> None:
    monkeypatch.setattr(paths, "backend_root", lambda: tmp_path)
    monkeypatch.setattr(images, "WORK_WIDTH", WIDTH)
    paths.ensure_data_tree()
    folder = paths.video_frames_dir(UUID)
    folder.mkdir(parents=True, exist_ok=True)
    for index in range(FRAMES):
        Image.fromarray(draw_frame(index, drawn)).save(
            folder / f"f{index + 1:06d}.jpg", "JPEG", quality=95
        )
    paths.video_source_path(UUID).write_bytes(b"not read by anything in this test")
    store.save_metadata(
        VideoMetadata(
            audio_uuid=UUID,
            title="Drawn",
            duration_seconds=FRAMES * SAMPLE_MS / 1000.0,
            sample_ms=SAMPLE_MS,
            frame_count=FRAMES,
            frame_width=WIDTH,
            frame_height=HEIGHT,
        )
    )
    store.save_calibration(UUID, calibration())
    store.save_measurement(UUID, measurement())
