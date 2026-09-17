"""The piano overlay: per-key borders become every key and its lane (V-38).

The fixture these assert against is the same file the frontend's
`scripts/check-geometry.ts` reads, so the two implementations cannot drift.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from aitu_backend.schemas.video import BlackBorder, Calibration, PianoRect, expected_black_count
from aitu_backend.video import geometry
from aitu_backend.video.upgrade import grid_to_borders

FIXTURE = Path(__file__).parent / "fixtures" / "video" / "geometry-fixture.json"


@pytest.fixture(scope="module")
def fixture() -> dict:
    return json.loads(FIXTURE.read_text())


def _even(**overrides: object) -> Calibration:
    """A whole piano as an even grid of 24 px keys, spelt out into borders."""
    grid: dict[str, object] = dict(
        imageWidth=1280,
        imageHeight=720,
        upperLine=561.0,
        leftBorder=0.0,
        whiteWidth=24.0,
        whiteCount=52,
        whiteHeight=110.0,
        blackHeight=68.0,
        firstWhitePitchClass=9,
        firstWhiteOctave=0,
    )
    grid.update(overrides)
    return Calibration.model_validate(grid_to_borders(grid))


def _uneven(
    widths: list[float], first_pc: int = 0, angle: float = 0.0, x: float = 0.0
) -> Calibration:
    """White keys of the given widths, black keys centred on their boundaries."""
    borders = [0.0]
    for w in widths:
        borders.append(borders[-1] + w)
    blacks = []
    pcs = [0, 2, 4, 5, 7, 9, 11]
    first = pcs.index(first_pc)
    for i in range(len(widths) - 1):
        if pcs[(first + i) % 7] in (4, 11):
            continue
        blacks.append(BlackBorder(left=borders[i + 1] - 7.0, right=borders[i + 1] + 7.0))
    return Calibration(
        image_width=1280,
        image_height=720,
        piano_rect=PianoRect(x=x, y=500.0, width=1200.0, height=200.0, angle=angle),
        upper_line=500.0,
        white_borders=borders,
        black_borders=blacks,
        black_depth=60.0,
        first_white_pitch_class=first_pc,
        first_white_octave=2,
    )


def test_the_fixture_is_what_this_module_builds(fixture: dict) -> None:
    """The committed fixture is not stale — regenerate it if this fails."""
    assert [case["name"] for case in fixture["cases"]] == ["straight", "angled"]
    for case in fixture["cases"]:
        cal = Calibration.model_validate(case["calibration"])
        built = geometry.geometry(cal, case["margin"])
        assert [k.model_dump(by_alias=True) for k in built.keys] == case["keys"], case["name"]
        assert [lane.model_dump(by_alias=True) for lane in built.lanes] == case["lanes"], case[
            "name"
        ]


def test_fifty_two_white_keys_from_a0_are_the_whole_piano() -> None:
    keys = geometry.keys(_even())
    assert len(keys) == 88
    assert [k.midi for k in keys] == list(range(21, 109))
    assert keys[0].name_en == "A0" and keys[0].name_es == "La-0"
    assert keys[-1].name_en == "C8" and keys[-1].name_es == "Do-8"


def test_no_black_key_between_mi_and_fa_or_si_and_do() -> None:
    """The pattern of two and three black keys is the whole rule (V-10)."""
    keys = geometry.keys(_even())
    blacks = [k.midi for k in keys if k.kind == "black"]
    assert len(blacks) == 36
    assert all(midi % 12 in {1, 3, 6, 8, 10} for midi in blacks)
    assert expected_black_count(9, 52) == 36
    assert expected_black_count(0, 36) == 25  # a 61 key keyboard from C2


def test_white_keys_tile_their_borders_with_no_gap() -> None:
    cal = _uneven([20.0, 22.0, 24.0, 26.0, 28.0, 30.0, 32.0, 34.0])
    whites = [k for k in geometry.keys(cal) if k.kind == "white"]
    assert len(whites) == 8
    for left, right in zip(whites, whites[1:]):
        assert left.right == pytest.approx(right.left)
    assert [k.right - k.left for k in whites] == pytest.approx([20, 22, 24, 26, 28, 30, 32, 34])


def test_a_black_key_keeps_the_borders_the_picture_gave_it() -> None:
    """No offset table, no replication: each black key's own borders (V-38)."""
    cal = _uneven([24.0] * 8)
    cal.black_borders[0] = BlackBorder(left=15.0, right=29.0)  # C#2, pushed right of its boundary
    keys = {k.midi: k for k in geometry.keys(cal)}
    assert keys[37].kind == "black"
    assert (keys[37].left, keys[37].right, keys[37].mid) == (15.0, 29.0, 22.0)
    assert keys[39].mid == pytest.approx(48.0), "the other black keys did not move"


def test_a_wrong_count_of_black_borders_is_refused() -> None:
    with pytest.raises(ValueError):
        cal = _uneven([24.0] * 8)
        Calibration(**{**cal.model_dump(), "black_borders": cal.black_borders[:-1]})


def test_borders_must_increase_and_hold_at_least_one_key() -> None:
    cal = _uneven([24.0] * 8)
    with pytest.raises(ValueError):
        Calibration(**{**cal.model_dump(), "white_borders": [0.0]})
    with pytest.raises(ValueError):
        Calibration(**{**cal.model_dump(), "white_borders": [0.0, 24.0, 20.0]})


def test_the_top_edge_of_an_angled_rectangle_projects_onto_the_horizontal() -> None:
    """A lane is a vertical strip of the picture (V-39): x = rect.x + u · cos(angle)."""
    cal = _uneven([24.0] * 8, angle=10.0, x=100.0)
    borders = geometry.white_borders(cal)
    assert borders[0] == pytest.approx(100.0)
    assert borders[1] == pytest.approx(100.0 + 24.0 * math.cos(math.radians(10.0)))
    assert geometry.top_edge_u(cal, borders[3]) == pytest.approx(72.0)


def test_the_local_white_key_width_is_the_keys_own():
    """V-38: a white key's own width, a black key the mean of its two neighbours."""
    cal = _uneven([20.0, 30.0, 24.0, 24.0, 24.0, 24.0, 24.0, 24.0])
    widths = geometry.local_widths(cal)
    assert widths[36] == pytest.approx(20.0)  # C2
    assert widths[38] == pytest.approx(30.0)  # D2
    assert widths[37] == pytest.approx(25.0)  # C#2, between them


def test_a_lane_is_the_key_widened_by_the_margin_in_its_own_width() -> None:
    """V-13 word for word, with the margin in the local width (V-38)."""
    cal = _uneven([20.0, 30.0, 24.0, 24.0, 24.0, 24.0, 24.0, 24.0])
    keys = {k.midi: k for k in geometry.keys(cal)}
    lanes = {lane.midi: lane for lane in geometry.lanes(cal, margin=0.25)}
    assert set(keys) == set(lanes)
    assert lanes[36].x0 == pytest.approx(keys[36].left - 0.25 * 20.0)
    assert lanes[38].x1 == pytest.approx(keys[38].right + 0.25 * 30.0)
    assert lanes[37].x0 == pytest.approx(keys[37].left - 0.25 * 25.0)


def test_the_median_white_key_width_is_derived_and_never_set_by_hand() -> None:
    cal = _uneven([20.0, 22.0, 24.0, 26.0, 28.0, 30.0, 32.0, 34.0])
    assert cal.white_width == pytest.approx(28.0)
    assert geometry.guard_band_px(cal) == pytest.approx(1.75 * 28.0)
    assert geometry.guard_band_px(Calibration(**{**cal.model_dump(), "guard_band": 39.0})) == 39.0


def test_a_grid_spelt_out_is_the_grid_04_built() -> None:
    """The upgrade of Task 2.1.3: the 21 seeded calibrations mean what they meant.

    The straight case of the fixture is 04's test video spelt out, and its keys
    are the numbers 04's own fixture carried: A#0 at 22.14 to 36.39.
    """
    keys = {k.midi: k for k in geometry.keys(_even(leftBorder=1.5, whiteWidth=24.571428571428573))}
    assert keys[21].left == pytest.approx(1.5)
    assert keys[22].left == pytest.approx(22.140000000000004)
    assert keys[22].right == pytest.approx(36.39142857142858)
    assert keys[61].mid < keys[63].mid


def test_the_pitch_class_of_the_leftmost_white_key_shifts_every_name() -> None:
    """A 61 key keyboard starts at C2, and nothing about that is a colour (V-10)."""
    cal = _even(whiteCount=36, firstWhitePitchClass=0, firstWhiteOctave=2)
    keys = geometry.keys(cal)
    assert keys[0].midi == 36 and keys[0].name_en == "C2"
    assert len(keys) == 61


def test_the_octave_offered_follows_how_many_keys_there_are() -> None:
    assert geometry.default_octave_for(52) == 0
    assert geometry.default_octave_for(36) == 2
