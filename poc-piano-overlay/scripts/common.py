"""Shared pieces of the Phase 1 spike of implementation 05.

Every picture is read at the working resolution of the app, 1280 px wide (V-35),
so every number measured here is a number at the resolution the finder will
really see. The one rectangle per picture is kept in `data/rects.json`, placed
by hand once, and the strip inside it is rotated straight before anything reads
it — that is the same rectification the app will do.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT.parent / "context" / "implementations" / "04-synthesia-to-notes" / "examples"
DATA = ROOT / "data"
OUT = ROOT / "out"
WORK_WIDTH = 1280

# Pitch classes, white and black, in an octave from C.
WHITE_PITCH_CLASSES = [0, 2, 4, 5, 7, 9, 11]
BLACK_PITCH_CLASSES = [1, 3, 6, 8, 10]
#: For each white pitch class, whether a black key follows it (C# after C, ...).
BLACK_AFTER = {0: True, 2: True, 4: False, 5: True, 7: True, 9: True, 11: False}


def slugs() -> list[str]:
    return sorted(p.stem for p in EXAMPLES.glob("*.png"))


def load_rgb(slug: str) -> np.ndarray:
    """One picture as float RGB in 0..255 at the working resolution."""
    with Image.open(EXAMPLES / f"{slug}.png") as handle:
        image = handle.convert("RGB")
        height = max(1, round(image.height * WORK_WIDTH / image.width))
        image = image.resize((WORK_WIDTH, height), Image.Resampling.LANCZOS)
        return np.asarray(image, dtype=np.float32)


def grey(rgb: np.ndarray) -> np.ndarray:
    return rgb.mean(axis=2)


@dataclass(frozen=True)
class Rect:
    """The one rectangle: top left corner, size, and angle in degrees.

    The angle is positive clockwise on the screen (y grows downward), and the
    rectangle is rotated about its top left corner, so the top edge runs from
    (x, y) along (cos a, sin a).
    """

    x: float
    y: float
    width: float
    height: float
    angle: float = 0.0

    def top_edge_point(self, u: float) -> tuple[float, float]:
        a = np.deg2rad(self.angle)
        return self.x + u * np.cos(a), self.y + u * np.sin(a)


def load_rects() -> dict[str, Rect]:
    raw = json.loads((DATA / "rects.json").read_text())
    return {slug: Rect(**value) for slug, value in raw.items()}


def save_rects(rects: dict[str, Rect]) -> None:
    (DATA / "rects.json").write_text(
        json.dumps({s: r.__dict__ for s, r in sorted(rects.items())}, indent=2) + "\n"
    )


def rectify(image: np.ndarray, rect: Rect) -> np.ndarray:
    """The picture inside the rectangle, rotated straight: rows are v, columns u.

    Sampled with bilinear interpolation at one sample per pixel of the top edge,
    so a length in u is a length in picture pixels along that edge.
    """
    w, h = int(round(rect.width)), int(round(rect.height))
    a = np.deg2rad(rect.angle)
    u = np.arange(w)[None, :]
    v = np.arange(h)[:, None]
    xs = rect.x + u * np.cos(a) - v * np.sin(a)
    ys = rect.y + u * np.sin(a) + v * np.cos(a)
    if image.ndim == 2:
        return ndimage.map_coordinates(image, [ys, xs], order=1, mode="nearest")
    return np.stack(
        [ndimage.map_coordinates(image[..., c], [ys, xs], order=1, mode="nearest") for c in range(3)],
        axis=2,
    )


def runs(flags: np.ndarray) -> list[tuple[int, int]]:
    """Every stretch of True, as half-open (start, end)."""
    out: list[tuple[int, int]] = []
    start: int | None = None
    for i, value in enumerate(flags):
        if value and start is None:
            start = i
        elif not value and start is not None:
            out.append((start, i))
            start = None
    if start is not None:
        out.append((start, len(flags)))
    return out


def save_image(array: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(array, 0, 255).astype(np.uint8)).save(path)
