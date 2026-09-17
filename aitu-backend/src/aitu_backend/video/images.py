"""Reading a picture at the one resolution everything else assumes.

The example screenshots are 3600 px wide and a downloaded video is capped at
720p, so a threshold measured on one would be wrong on the other if either were
read at its own size. Every picture that enters the detector is therefore resized
to :data:`WORK_WIDTH` first, and the browser is served that same copy — so a
coordinate in a calibration means the same thing in the UI and in the detector.

This is the twin of V-22 for coordinates: V-22 puts every *length* in white key
widths, and this puts every *coordinate* in one picture's pixels at one width.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

#: The working resolution, in pixels of width. 1280 because Phase 3 caps the
#: video download at 720p, so this is the width the detector really sees.
WORK_WIDTH = 1280

#: JPEG quality for the derived copy. 92 keeps the rectangle borders crisp; the
#: detector reads the same file the browser does, so a lossy copy would otherwise
#: be a difference between what the user sees and what the detector reads.
JPEG_QUALITY = 92


def work_size(width: int, height: int) -> tuple[int, int]:
    """The working-resolution size of a picture that is ``width`` x ``height``."""
    return WORK_WIDTH, max(1, round(height * WORK_WIDTH / width))


def load_rgb(path: Path) -> np.ndarray:
    """A picture as float RGB in 0..255, already at the working resolution."""
    with Image.open(path) as handle:
        image = handle.convert("RGB")
        if image.width != WORK_WIDTH:
            image = image.resize(work_size(image.width, image.height), Image.Resampling.LANCZOS)
        return np.asarray(image, dtype=np.float32)


def write_work_copy(source: Path, destination: Path) -> tuple[int, int]:
    """Write the working-resolution copy of ``source`` and report its size."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as handle:
        image = handle.convert("RGB")
        if image.width != WORK_WIDTH:
            image = image.resize(work_size(image.width, image.height), Image.Resampling.LANCZOS)
        image.save(destination, "JPEG", quality=JPEG_QUALITY)
        return image.width, image.height


def ensure_work_copy(source: Path, destination: Path) -> tuple[int, int]:
    """The working-resolution copy, written if it is missing or out of date."""
    if destination.exists() and destination.stat().st_mtime >= source.stat().st_mtime:
        with Image.open(destination) as handle:
            return handle.width, handle.height
    return write_work_copy(source, destination)
