"""The background plate, and how far a pixel is from it.

Everything static is subtracted before anything is detected (V-15). Titles,
watermarks, logos, moons, decorative scrolls, the octave guide lines and the
steady part of the glow line are in every frame, so they are in the plate, and
they are gone from the difference. It is the first line of defence against an
invented note and it costs one pass over a hundred and fifty frames.

The plate is **the median of what stands still** (V-44). About 150 frames spread
over the video, and for each of them the two sampled frames either side. A pixel
of a frame counts only where it did not change across those neighbouring frames,
so no moving edge of a rectangle is ever on it; and a frame whose roll changed on
fewer than 0.2% of its pixels is a rest, a title card or an end screen, not a
picture of the roll's background, and is left out whole. The plate is the
per-pixel median of what counts.

Why not a percentile. V-29 took the 20th percentile per colour channel, which
assumes the rectangles are lighter than the roll behind them. On a dark roll every
colour is; on a grey photograph a blue rectangle is darker in red and green, so
once a lane held a rectangle in a fifth of the frames the plate took the
rectangle's colour in those channels and the whole lane inverted. Measured on a
roll drawn over a photograph: the lane of the most played key read as foreground
in 92% of frames under the percentile and in 39% under the median, while the
keyboard lit that key in 35% of them. The median assumes nothing about colour.

Why only still pixels, and why so short a stillness. A value a pixel holds for
longer than a rectangle can fall is background — unless the lane is busy, and
then the background is never still that long and whatever else stands still
wins: measured on the first video, an end screen and a chord held longer than the
roll is tall both took over the lanes of the keys they sat on. Two frames either
side is long enough to drop a moving edge and short enough that a busy lane keeps
hundreds of background votes: 74 still frames a pixel at the 10th percentile on
one video and 97 on the other, of 150.

What it cannot do, said plainly: a key held still for more than half the piece
would put its rectangle in the plate. The reading reports the lanes that are
foreground more than :data:`BUSY_LANE` of the time so such a lane is named rather
than trusted.

One screenshot cannot give a plate, so it gets a stand-in. Which is honest about
what it costs: the real plate removed 27% of what the stand-in reported, so every
score measured on the screenshots is a floor and the invented onsets that survive
there are static decoration the stand-in cannot see.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from scipy import ndimage

if TYPE_CHECKING:  # pragma: no cover - import cycle only matters to the checker
    from aitu_backend.video.detector import DetectorSettings

#: How many frames feed the plate, spread over the whole video, and how many
#: sampled frames either side of each one say whether a pixel stood still.
PLATE_FRAMES = 150
PLATE_NEIGHBOURS = 2
#: Levels, in any channel. A pixel that changed by less than this between two
#: sampled frames stood still. The JPEG noise of a static photograph is 3 to 4.
STILL_TOLERANCE = 12.0
#: Share of the roll's pixels. A frame whose roll changed on fewer than this is
#: a rest or a card and is left out. Measured: the pairs of an end screen change
#: under 0.2%, and the 1st percentile of pairs that scroll is 0.34% on the
#: busiest video and 4.6% on the other.
STILL_ROLL_SHARE = 0.002
#: A lane foreground more often than this is named in the report (V-20): the
#: median cannot tell a drone from the roll behind it.
BUSY_LANE = 0.6


@dataclass(frozen=True)
class PlateSample:
    """One frame's vote: its pixels, which of them stood still, and whether the
    roll moved at all around it."""

    frame: np.ndarray
    still: np.ndarray
    roll_moved: bool


def sample(
    window: list[np.ndarray], upper: int | None = None, centre: int | None = None
) -> PlateSample:
    """The vote of one frame of ``window`` — the middle one unless ``centre``
    says otherwise — with its neighbours either side.

    ``upper`` is the upper line: only the roll above it says whether the roll
    moved, because the keyboard below it lights and dims on its own. Without one
    the whole picture is asked.
    """
    frame = window[len(window) // 2 if centre is None else centre]
    still = np.ones(frame.shape[:2], dtype=bool)
    moved = len(window) > 1
    for a, b in zip(window, window[1:]):
        changed = np.abs(a - b).max(axis=2) >= STILL_TOLERANCE
        still &= ~changed
        if changed[:upper].mean() < STILL_ROLL_SHARE:
            moved = False
    return PlateSample(frame=frame.astype(np.uint8), still=still, roll_moved=moved)


def build_plate(samples: list[PlateSample]) -> np.ndarray:
    """The per-pixel median of what stood still, over the frames the roll moved in.

    A pixel that never stood still — none on either video measured — takes the
    plain median of the same frames, and a video in which the roll never moved
    at all takes the plain median of every frame, because a plate of nothing is
    worse than a plate of something.
    """
    if not samples:
        raise ValueError("a plate needs at least one frame")
    moving = [one for one in samples if one.roll_moved] or samples
    stack = np.stack([one.frame for one in moving])
    mask = np.stack([one.still for one in moving])
    plain = np.median(stack, axis=0).astype(np.float32)
    plate = np.empty_like(plain)
    rows = stack.shape[1]
    for y0 in range(0, rows, 60):
        block = stack[:, y0 : y0 + 60].astype(np.float32)
        block[~mask[:, y0 : y0 + 60]] = np.nan
        with np.errstate(all="ignore"):
            median = np.nanmedian(block, axis=0)
        plate[y0 : y0 + 60] = np.where(np.isnan(median), plain[y0 : y0 + 60], median)
    return plate


def stand_in_plate(roll: np.ndarray) -> np.ndarray:
    """The plate of a single screenshot: the per-row median across the width.

    Whatever most of a row looks like is the background of that row. It removes a
    vertical gradient and the glow that fades upward from the upper line, which
    is most of what the real plate removes. It does **not** remove a title drawn
    across the roll, and a real plate does.
    """
    return np.median(roll, axis=1, keepdims=True)


def _gradient_strength(roll: np.ndarray, tau_foreground: float) -> np.ndarray:
    """Edges, as a second channel for the outlined renderings.

    The only primitive that reads an outlined rectangle whose fill is the
    background colour: 22 runs on `not-immediate-strokes` against 15 for the
    plate. It is scaled onto the same 0..255-ish range as the plate difference so
    one ``tau_foreground`` serves both.
    """
    grey = ndimage.gaussian_filter(roll.mean(axis=2), 1.0)
    magnitude = np.hypot(ndimage.sobel(grey, axis=1), ndimage.sobel(grey, axis=0))
    scale = max(30.0, float(np.percentile(magnitude, 97))) / tau_foreground
    return magnitude / max(scale, 1e-6)


def foreground_strength(
    roll: np.ndarray,
    plate: np.ndarray | None,
    channel: str = "plate",
    settings: "DetectorSettings | None" = None,
) -> np.ndarray:
    """How far each pixel of the roll is from the background, as a number.

    Kept as a number and not only as a yes or a no, because the edge step of the
    detector needs how strong it is, not whether it passed.

    ``channel`` picks which foreground rule is used. ``plate`` is the one the plan
    chose (V-21): it is the only rule that does not care how a rectangle is filled
    — solid, shallow, outlined, gradient or shining — because it does not look at
    the rectangle, it looks at what changed. ``edges`` is the gradient second
    channel, and ``both`` is the larger of the two at each pixel.
    """
    from aitu_backend.video.detector import DEFAULTS

    settings = settings or DEFAULTS
    if channel in ("plate", "both"):
        background = plate[: roll.shape[0]] if plate is not None else stand_in_plate(roll)
        plate_strength = np.abs(roll - background).max(axis=2)
        if channel == "plate":
            return plate_strength
    if channel in ("edges", "both"):
        edge_strength = _gradient_strength(roll, settings.tau_foreground)
        if channel == "edges":
            return edge_strength
        return np.maximum(plate_strength, edge_strength)
    raise ValueError(f"unknown channel '{channel}'; expected plate, edges or both")
