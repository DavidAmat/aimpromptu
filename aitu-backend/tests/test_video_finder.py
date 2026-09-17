"""The finder: one picture and one rectangle in, the piano overlay out (V-37).

Everything here is drawn on purpose rather than photographed, so a failure says
which step broke. The real pictures are measured in `poc-piano-overlay/` and the
seeded examples are checked against those numbers by `test_video_examples.py`.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from scipy import ndimage

from aitu_backend.schemas.video import PianoRect
from aitu_backend.video import finder, geometry
from aitu_backend.video.finder import NoKeyboard

WHITE = 24.0
BLACK = 14.0
DEPTH = 60
HEIGHT = 100
PITCH_CLASSES = [0, 2, 4, 5, 7, 9, 11]
#: The real piano family, as the finder assumes it, so the drawn keyboard is one
#: the finder has a right to read exactly.
OFFSETS = {1: -0.095, 3: 0.100, 6: -0.131, 8: 0.009, 10: 0.137}


def draw_keyboard(
    white_count: int = 36,
    first_pc: int = 0,
    left: float = 100.0,
    top: int = 300,
    widths: list[float] | None = None,
    canvas: tuple[int, int] = (500, 1280),
) -> tuple[np.ndarray, list[float]]:
    """A keyboard: light white keys with thin dark lines, dark black keys, a dark
    roll above and dark wood below. Returns the picture and the white borders."""
    h, w = canvas
    image = np.full((h, w, 3), 30.0, dtype=np.float32)
    widths = widths or [WHITE] * white_count
    borders = [left]
    for width in widths:
        borders.append(borders[-1] + width)
    x0, x1 = int(round(borders[0])), int(round(borders[-1]))
    image[top : top + HEIGHT, x0:x1] = 235.0
    for b in borders:
        x = int(round(b))
        image[top : top + HEIGHT, max(0, x - 1) : x + 1] = 60.0
    first = PITCH_CLASSES.index(first_pc)
    for i in range(white_count - 1):
        pc = PITCH_CLASSES[(first + i) % 7]
        if pc in (4, 11):
            continue
        local = (widths[i] + widths[i + 1]) / 2
        centre = borders[i + 1] + OFFSETS[pc + 1] * local
        a, b = int(round(centre - BLACK / 2)), int(round(centre + BLACK / 2))
        image[top : top + DEPTH, a:b] = 20.0
    return image, borders


def rect_for(
    top: int = 300,
    height: int = HEIGHT + 20,
    angle: float = 0.0,
    x: float = 0.0,
    width: float = 1280.0,
) -> PianoRect:
    return PianoRect(x=x, y=float(top), width=width, height=float(height), angle=angle)


def test_a_drawn_keyboard_is_found_border_for_border() -> None:
    image, borders = draw_keyboard(white_count=36, first_pc=0)
    cal = finder.find_overlay(image, rect_for())
    assert cal.first_white_pitch_class == 0
    assert len(cal.white_borders) == len(borders)
    assert cal.white_borders == pytest.approx(borders, abs=1.0)
    assert len(cal.black_borders) == 25
    assert cal.black_depth == pytest.approx(DEPTH, abs=3)
    assert cal.found is not None and cal.found.route == "A" and cal.found.extrapolated == []
    assert cal.white_width == pytest.approx(WHITE, abs=0.5)


def test_the_pitch_class_comes_from_the_pattern_and_the_octave_from_the_user() -> None:
    """V-10. A keyboard from A: the first black key is A#, one white key in."""
    image, borders = draw_keyboard(white_count=52, first_pc=9, left=48.0, canvas=(500, 1400))
    cal = finder.find_overlay(image, rect_for(width=1400.0), first_white_octave=0)
    assert cal.first_white_pitch_class == 9
    assert cal.first_white_octave == 0
    keys = geometry.keys(cal)
    assert keys[0].name_en == "A0" and keys[-1].name_en == "C8"
    assert len(cal.black_borders) == 36


def test_keys_a_hand_hides_are_placed_through_it_and_flagged() -> None:
    """Section 6.1 of the plan: extrapolated, and confirmed only where the pixels are dark."""
    image, borders = draw_keyboard(white_count=36, first_pc=0)
    # a hand over six white keys and their black keys, lighter than a black key
    x0, x1 = int(borders[14]), int(borders[20])
    image[300 : 300 + HEIGHT, x0:x1] = 150.0
    cal = finder.find_overlay(image, rect_for())
    assert cal.white_borders == pytest.approx(borders, abs=1.5)
    assert cal.found is not None
    assert (
        len(cal.found.extrapolated) >= 3
    ), "the black keys under the hand were placed from the pattern"
    assert cal.found.confirmed == [], "a hand is lighter than a black key, so none is confirmed"
    hidden = {k.midi for k in geometry.keys(cal) if k.kind == "black" and x0 < k.mid < x1}
    assert set(cal.found.extrapolated) == hidden


def test_a_rectangle_reaching_past_both_ends_stops_at_the_keyboard() -> None:
    image, borders = draw_keyboard(white_count=21, first_pc=0, left=300.0)
    cal = finder.find_overlay(image, rect_for())
    assert len(cal.white_borders) - 1 == 21
    assert cal.white_borders[0] == pytest.approx(300.0, abs=1.0)


def test_a_rotated_keyboard_is_read_inside_a_rotated_rectangle() -> None:
    """The rectifier: the same keyboard turned by 5 degrees, the rectangle turned with it."""
    image, borders = draw_keyboard(
        white_count=36, first_pc=0, left=200.0, top=200, canvas=(700, 1400)
    )
    angle = 5.0
    # rotate the picture about its centre, the way a camera would tilt it
    rotated = np.stack(
        [
            ndimage.rotate(image[..., c], -angle, reshape=False, order=1, mode="nearest")
            for c in range(3)
        ],
        axis=2,
    )
    # where the keyboard's top left corner went
    cy, cx = (image.shape[0] - 1) / 2, (image.shape[1] - 1) / 2
    a = math.radians(angle)
    px, py = 100.0 - cx, 200.0 - cy  # a point left of the keyboard on its top edge
    rx = cx + px * math.cos(a) - py * math.sin(a)
    ry = cy + px * math.sin(a) + py * math.cos(a)
    cal = finder.find_overlay(
        rotated, PianoRect(x=rx, y=ry, width=1150.0, height=120.0, angle=angle)
    )
    assert cal.first_white_pitch_class == 0
    assert len(cal.white_borders) - 1 == 36
    # borders in u are distances along the top edge from the rectangle's corner
    expected = [b - 100.0 for b in borders]
    assert cal.white_borders == pytest.approx(expected, abs=1.5)
    # and the lanes are vertical strips: picture x = rect.x + u cos a (V-39)
    assert geometry.white_borders(cal)[0] == pytest.approx(
        rx + cal.white_borders[0] * math.cos(a), abs=1e-6
    )


def test_widening_keys_are_read_where_they_are_not_where_a_grid_puts_them() -> None:
    """Perspective: 7% wider at one end than the other, as `airplanes` is."""
    widths = [22.0 + 0.05 * i for i in range(36)]
    image, borders = draw_keyboard(white_count=36, first_pc=0, widths=widths)
    cal = finder.find_overlay(image, rect_for())
    assert cal.white_borders == pytest.approx(borders, abs=1.5)
    grid_last = borders[0] + 36 * WHITE
    assert (
        abs(cal.white_borders[-1] - grid_last) > 5
    ), "a grid would be off by more than five px at the far end"


def test_a_rectangle_with_no_keyboard_is_refused_with_a_reason() -> None:
    image = np.full((400, 1280, 3), 30.0, dtype=np.float32)
    with pytest.raises(NoKeyboard):
        finder.find_overlay(image, rect_for(top=100))
    image[100:300] = 220.0
    with pytest.raises(NoKeyboard):
        finder.find_overlay(image, rect_for(top=100))
