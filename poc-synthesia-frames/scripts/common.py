"""Shared pieces of the Phase 1 research spike.

Nothing here is imported by the app. It reads the example screenshots in
context/implementations/04-synthesia-to-notes/examples and writes pictures and
tables into poc-synthesia-frames/out.

Working resolution is 1280 px wide on purpose: Phase 3 caps the video download
at 720p, so every threshold measured here is measured at the resolution the
detector will really see.
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, asdict, field

import numpy as np
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "context/implementations/04-synthesia-to-notes/examples"
OUT = ROOT / "poc-synthesia-frames/out"
DATA = ROOT / "poc-synthesia-frames/data"
WORK_WIDTH = 1280

# The twelve semitones of an octave, and which of them are black keys.
BLACK_IN_OCTAVE = {1, 3, 6, 8, 10}
# White key index inside an octave, for the seven white pitch classes.
WHITE_PITCH_CLASSES = [0, 2, 4, 5, 7, 9, 11]


def load(slug: str) -> np.ndarray:
    """The example at the working resolution, as float RGB in 0..255."""
    im = Image.open(EXAMPLES / f"{slug}.png").convert("RGB")
    w, h = im.size
    new = (WORK_WIDTH, max(1, round(h * WORK_WIDTH / w)))
    im = im.resize(new, Image.LANCZOS)
    return np.asarray(im, dtype=np.float32)


def slugs() -> list[str]:
    return sorted(p.stem for p in EXAMPLES.glob("*.png"))


@dataclass
class Calibration:
    """The piano overlay of one example, in working-resolution pixels.

    `upper_line` is the top edge of the keyboard. `left_border` is the left
    border of the leftmost white key, `white_width` the width of one white key,
    `white_count` how many white keys the picture shows, `first_white_pc` the
    pitch class of the leftmost white key (0 = C, 2 = D, ... 11 = B) and
    `first_white_octave` its octave. `black_mode` is "boundary" when the black
    keys are drawn centred on the boundary between two white keys, and "real"
    when the real piano offsets are used.
    """

    slug: str
    upper_line: float
    left_border: float
    white_width: float
    white_count: int
    first_white_pc: int = 9          # A
    first_white_octave: int = 0      # A0, the 88 key default
    black_ratio: float = 0.58        # black key width as a fraction of a white key
    black_mode: str = "boundary"
    # The roll is bounded above as well as below. A video may carry a toolbar, a
    # progress bar, a title band or a letterbox over the top of the picture, and
    # nothing above `roll_top` is music. `guard_band` is how many rows above the
    # upper line the strike light makes unreadable (V-24). Both are measured
    # from the video by roll_top.find; on a single screenshot there is no motion
    # to measure them from, so they keep these defaults.
    roll_top: float = 0.0
    guard_band: float = 0.0
    note: str = ""

    # ---- geometry ----------------------------------------------------------
    def white_borders(self) -> np.ndarray:
        return self.left_border + self.white_width * np.arange(self.white_count + 1)

    def keys(self) -> list[dict]:
        """Every key in the picture: pitch, kind, left, right, midpoint."""
        out: list[dict] = []
        borders = self.white_borders()
        # The white keys.
        pc = self.first_white_pc
        octave = self.first_white_octave
        wi = WHITE_PITCH_CLASSES.index(pc)
        whites: list[tuple[int, int]] = []      # (midi, white index in picture)
        for i in range(self.white_count):
            idx = (wi + i) % 7
            oct_ = octave + (wi + i) // 7
            midi = 12 * (oct_ + 1) + WHITE_PITCH_CLASSES[idx]
            whites.append((midi, i))
            out.append(
                dict(midi=midi, kind="white", left=float(borders[i]),
                     right=float(borders[i + 1]),
                     mid=float((borders[i] + borders[i + 1]) / 2))
            )
        # The black keys sit between two white keys whose pitch classes differ
        # by two semitones. That is the whole rule; no colour is involved.
        bw = self.white_width * self.black_ratio
        for (midi_a, i), (midi_b, _) in zip(whites, whites[1:]):
            if midi_b - midi_a != 2:
                continue
            centre = borders[i + 1]
            if self.black_mode == "real":
                centre += _real_offset(midi_a + 1) * self.white_width
            out.append(
                dict(midi=midi_a + 1, kind="black", left=float(centre - bw / 2),
                     right=float(centre + bw / 2), mid=float(centre))
            )
        out.sort(key=lambda k: k["midi"])
        return out

    def lanes(self, margin: float = 0.25) -> list[dict]:
        """One vertical lane per key, widened by `margin` white key widths."""
        m = margin * self.white_width
        return [
            dict(midi=k["midi"], kind=k["kind"], mid=k["mid"],
                 x0=k["left"] - m, x1=k["right"] + m)
            for k in self.keys()
        ]


# Real piano black key offsets, as a fraction of a white key width, measured
# from the boundary between the two white keys the black key sits between.
# Positive is to the right. These are the standard keyboard proportions.
_REAL_OFFSETS = {1: -0.10, 3: +0.10, 6: -0.13, 8: 0.0, 10: +0.13}


def _real_offset(midi: int) -> float:
    return _REAL_OFFSETS.get(midi % 12, 0.0)


def load_calibrations() -> dict[str, Calibration]:
    path = DATA / "calibrations.json"
    if not path.exists():
        return {}
    raw = json.loads(path.read_text())
    return {k: Calibration(**v) for k, v in raw.items()}


def save_calibrations(cals: dict[str, Calibration]) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "calibrations.json").write_text(
        json.dumps({k: asdict(v) for k, v in sorted(cals.items())}, indent=2) + "\n"
    )
