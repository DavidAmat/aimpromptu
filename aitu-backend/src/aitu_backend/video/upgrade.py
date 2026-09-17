"""A grid calibration, spelt out into per-key borders.

Implementation 04 kept the piano overlay as a grid: a left border, one white key
width, a count, and five black key offsets replicated across every octave.
Implementation 05 keeps per-key borders instead (V-38). Every record saved as a
grid — the 21 calibrations Phase 1 of 04 seeded, and the two with hand readings
— is spelt out on the way in, so nothing saved is lost and the score board reads
the same before and after the change.

The one rectangle of a spelt-out grid is the full width of the picture, its top
edge on the upper line, at an angle of zero, so a distance along its top edge is
a picture x.
"""

from __future__ import annotations

from typing import Any

#: How the real piano offsets 04 guessed shifted each black key off the boundary
#: between its two white keys, in white key widths. Only a grid saved by 04 uses
#: them; a found calibration carries the borders the picture showed.
REAL_BLACK_OFFSETS = {1: -0.10, 3: +0.10, 6: -0.13, 8: 0.0, 10: +0.13}
BLACK_PITCH_CLASSES = [1, 3, 6, 8, 10]
WHITE_PITCH_CLASSES = [0, 2, 4, 5, 7, 9, 11]


def is_grid(raw: dict[str, Any]) -> bool:
    """A record written by 04: it has a white key width and a count, no borders."""
    return "whiteBorders" not in raw and "whiteWidth" in raw and "whiteCount" in raw


def grid_to_borders(raw: dict[str, Any]) -> dict[str, Any]:
    """Spell a grid calibration out. Takes and returns the camelCase wire shape."""
    left = float(raw["leftBorder"])
    width = float(raw["whiteWidth"])
    count = int(raw["whiteCount"])
    upper = float(raw["upperLine"])
    image_width = int(raw["imageWidth"])
    image_height = int(raw["imageHeight"])
    first_pc = int(raw.get("firstWhitePitchClass", 9))
    black_width = width * float(raw.get("blackRatio", 0.58))
    offsets = raw.get("blackOffsets")

    def black_offset(pitch_class: int) -> float:
        if offsets:
            return float(offsets[BLACK_PITCH_CLASSES.index(pitch_class)])
        base = REAL_BLACK_OFFSETS[pitch_class] if raw.get("blackMode", "real") == "real" else 0.0
        return base + float(raw.get("blackNudge", 0.0))

    borders = [left + width * i for i in range(count + 1)]
    blacks = []
    first = WHITE_PITCH_CLASSES.index(first_pc)
    for i in range(count - 1):
        pc_a = WHITE_PITCH_CLASSES[(first + i) % 7]
        pc_b = WHITE_PITCH_CLASSES[(first + i + 1) % 7]
        if (pc_b - pc_a) % 12 != 2:
            continue
        centre = borders[i + 1] + black_offset((pc_a + 1) % 12) * width
        blacks.append({"left": centre - black_width / 2, "right": centre + black_width / 2})

    note = str(raw.get("note", "")).strip()
    return {
        "imageWidth": image_width,
        "imageHeight": image_height,
        "pianoRect": {
            "x": 0.0,
            "y": upper,
            "width": float(image_width),
            "height": max(1.0, float(image_height) - upper),
            "angle": 0.0,
        },
        "upperLine": upper,
        "whiteBorders": borders,
        "blackBorders": blacks,
        "blackDepth": float(raw.get("blackHeight", width * 2.8)),
        "whiteWidth": width,
        "firstWhitePitchClass": first_pc,
        "firstWhiteOctave": int(raw.get("firstWhiteOctave", 0)),
        "rollTop": float(raw.get("rollTop", 0.0)),
        "guardBand": float(raw.get("guardBand", 0.0)),
        "found": None,
        "note": f"{note} · spelt out from a grid" if note else "spelt out from a grid",
    }


def upgrade(raw: dict[str, Any]) -> dict[str, Any]:
    """The wire shape of a calibration, whichever shape it was saved in."""
    return grid_to_borders(raw) if is_grid(raw) else raw
