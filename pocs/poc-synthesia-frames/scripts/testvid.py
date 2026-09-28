"""The test video the user asked for: 90 seconds of pgLt4WmPMYQ as test.mp4."""
from __future__ import annotations

import pathlib

import numpy as np
from PIL import Image

import common

VIDEO = common.DATA / "video"
FRAMES = VIDEO / "frames_test"
SAMPLE_MS = 100


def frames() -> list[pathlib.Path]:
    return sorted(FRAMES.glob("f*.jpg"))


def load(i: int) -> np.ndarray:
    return np.asarray(Image.open(frames()[i]).convert("RGB"), dtype=np.float32)


def at_second(t: float) -> int:
    """The sampled frame index for a time in seconds. Frame 1 is t = 0.1 s."""
    return max(0, min(len(frames()) - 1, int(round(t * 1000 / SAMPLE_MS)) - 1))


def plate(n: int = 100, percentile: float = 20.0, rebuild: bool = False) -> np.ndarray:
    """The background plate (V-15), as a low percentile rather than the median.

    V-15 says the plate is the per-pixel median of frames spread over the video.
    On this video the median is contaminated: a lane holding a long note is lit
    in more than half the frames at some rows, so the median of those pixels is
    the note, the plate goes blue in bands, and the difference against it puts
    dark bands across a held rectangle. The detector then cuts the rectangle at
    those bands, in the same place in every frame, which is exactly what a false
    rectangle looks like.

    More frames do not fix it and neither does picking them at random: the rows
    really are lit most of the time. What fixes it is asking for a lower
    percentile. Measured on the lane that broke, the brightest hundredth of the
    plate sits 62.5 above the floor at the median, 7.7 at the 20th percentile and
    3.6 at the 10th.

    This assumes the rectangles are lighter than the roll behind them, which is
    true of all 21 example screenshots and of both videos. A rendering that drew
    dark notes on a light roll would need the percentile taken from the other
    end, and the way to tell is to compare a frame's roll against the plate and
    see which way the difference goes.
    """
    path = VIDEO / f"plate_test_p{int(percentile)}.npy"
    if path.exists() and not rebuild:
        return np.load(path)
    paths = frames()
    pick = np.linspace(0, len(paths) - 1, n).round().astype(int)
    stack = np.stack([load(int(i)) for i in pick])
    bg = np.percentile(stack, percentile, axis=0)
    np.save(path, bg)
    Image.fromarray(bg.astype("uint8")).save(
        VIDEO / f"plate_test_p{int(percentile)}.jpg", quality=90)
    return bg


_CAL = None


def calibration(speed: float = 16.89):
    """The piano overlay, plus the roll top and the guard band measured from
    the motion of the roll itself."""
    global _CAL
    if _CAL is not None:
        return _CAL
    import find_keyboard
    import roll_top
    cal = find_keyboard.find(load(len(frames()) // 2), "test")
    u = int(round(cal.upper_line))
    r = roll_top.find(load, range(200, 215), u, speed)
    cal.roll_top = float(r["roll_top"])
    cal.guard_band = float(max(0, u - r["roll_bottom"]))
    _CAL = cal
    return cal
