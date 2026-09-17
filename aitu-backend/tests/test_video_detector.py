"""The detector: one picture and one calibration in, onsets and sustains out.

Everything here is drawn on purpose rather than photographed, so a failure says
which rule broke. The real pictures are scored by `tests/test_video_examples.py`
against the readings Phase 1 made by hand.
"""

from __future__ import annotations

import numpy as np
import pytest

from aitu_backend.schemas.video import Calibration, DetectedRun
from aitu_backend.video import detector, geometry
from aitu_backend.video.detector import DetectorSettings
from aitu_backend.video.upgrade import grid_to_borders

WHITE = 24.0
UPPER = 400


def _calibration(**overrides: object) -> Calibration:
    """A whole piano drawn as an even grid, spelt out into borders (V-38).

    The detector's own tests draw their rectangles on an even keyboard on
    purpose: what they test is the rules about rows, and an even grid is the
    case the two white key widths of V-38 agree on.
    """
    grid: dict[str, object] = dict(
        imageWidth=1280,
        imageHeight=600,
        upperLine=float(UPPER),
        leftBorder=0.0,
        whiteWidth=WHITE,
        whiteCount=52,
        whiteHeight=110.0,
        blackHeight=68.0,
        firstWhitePitchClass=9,
        firstWhiteOctave=0,
    )
    raw = grid_to_borders(grid)
    raw.update(
        {"rollTop": overrides.pop("roll_top", 0.0), "guardBand": overrides.pop("guard_band", 0.0)}
    )
    assert not overrides, f"unknown overrides {overrides}"
    return Calibration.model_validate(raw)


def _blank(cal: Calibration) -> np.ndarray:
    """A dark roll with a keyboard under it — nothing falling."""
    image = np.full((cal.image_height, cal.image_width, 3), 20.0, dtype=np.float32)
    image[int(cal.upper_line) :] = 200.0
    return image


def _draw(image: np.ndarray, cal: Calibration, midi: int, y_top: int, y_bottom: int) -> None:
    """A solid rectangle on one key, the way these animations draw a note."""
    key = next(k for k in geometry.keys(cal) if k.midi == midi)
    x0, x1 = int(round(key.left)), int(round(key.right))
    image[y_top : y_bottom + 1, x0 : x1 + 1] = np.array([230.0, 120.0, 60.0])


# --------------------------------------------------------- the window rule ---


def _run(y_top: int, y_bottom: int, clipped: bool = False, midi: int = 60) -> DetectedRun:
    return DetectedRun(
        midi=midi,
        y_top=y_top,
        y_bottom=y_bottom,
        x0=0.0,
        x1=WHITE,
        mid=WHITE / 2,
        width_keys=1.0,
        clipped=clipped,
        tip_trusted=True,
        entering=False,
    )


def test_the_window_rule_is_v18_word_for_word() -> None:
    """`U - d <= yBottom < U` is an onset; one pixel either side is not."""
    d = 40.0
    onsets, sustains = detector.window_rule([_run(300, UPPER - 1)], UPPER, d)
    assert onsets == [60] and sustains == []

    onsets, _ = detector.window_rule([_run(300, UPPER - int(d))], UPPER, d)
    assert onsets == [60], "the offset line itself is inside the window"

    onsets, sustains = detector.window_rule([_run(300, UPPER - int(d) - 1)], UPPER, d)
    assert onsets == [] and sustains == [], "above the offset line it has not arrived yet"


def test_a_run_that_already_crossed_is_a_sustain_not_an_onset() -> None:
    d = 40.0
    onsets, sustains = detector.window_rule([_run(200, UPPER + 5)], UPPER, d)
    assert onsets == [] and sustains == [60]


def test_a_run_cut_by_the_upper_line_is_sounding_not_tipped_there() -> None:
    """V-16: reading that edge as a tip is the easiest way to invent an onset."""
    d = 40.0
    cut = _run(200, UPPER - 1, clipped=True)
    onsets, sustains = detector.window_rule([cut], UPPER, d)
    assert onsets == [] and sustains == [60]
    assert cut.verdict == "sustain"


def test_a_key_with_an_onset_is_not_also_reported_as_a_sustain() -> None:
    d = 40.0
    onsets, sustains = detector.window_rule([_run(200, UPPER + 5), _run(330, UPPER - 1)], UPPER, d)
    assert onsets == [60] and sustains == []


def test_released_is_the_default_and_is_never_written_down() -> None:
    """V-19: there are two labels, not three."""
    run = _run(100, 200)
    onsets, sustains = detector.window_rule([run], UPPER, 40.0)
    assert onsets == [] and sustains == []
    assert run.verdict == "released"


# ------------------------------------------------------------- the pixels ---


def test_one_rectangle_high_in_the_roll_is_found_on_its_own_key() -> None:
    cal = _calibration()
    image = _blank(cal)
    _draw(image, cal, 60, 100, 140)
    result = detector.detect(image, cal, offset_px=2 * WHITE)

    assert [run.midi for run in result.runs] == [60]
    run = result.runs[0]
    assert (run.y_top, run.y_bottom) == (100, 140)
    assert run.width_keys == pytest.approx(1.0, abs=0.15)
    assert result.onsets == [] and result.sustains == []


def test_a_rectangle_inside_the_window_is_an_onset() -> None:
    cal = _calibration()
    image = _blank(cal)
    _draw(image, cal, 64, UPPER - 60, UPPER - 20)
    result = detector.detect(image, cal, offset_px=2 * WHITE)
    assert result.onsets == [64]


def test_two_rectangles_touching_are_two_notes() -> None:
    """V-26. They are drawn with nothing between them but their own borders."""
    cal = _calibration()
    image = _blank(cal)
    _draw(image, cal, 60, 100, 160)
    _draw(image, cal, 60, 165, 225)
    # The border between them: dark, and four rows, which is inside the 3 to 7
    # rows Phase 1 measured and wider than anything `gapClose` may close.
    image[161:165] = 20.0

    result = detector.detect(image, cal, offset_px=2 * WHITE)
    assert len(result.runs) == 2, "the gap between two rectangles must never be closed"
    assert [(r.y_top, r.y_bottom) for r in result.runs] == [(100, 160), (165, 225)]


def test_gap_close_closes_two_rows_and_never_three() -> None:
    """The other half of V-26, as the rule itself.

    Measured over sixty sampled frames: 927 gaps of 1 to 2 rows, which are
    texture inside one rectangle and have to be closed, and 1351 gaps of 3 to 7
    rows, which are two rectangles and have to be kept. `binary_closing` with a
    structure of length L closes every gap shorter than L, so the structure is
    `gapClose + 1` — the first version used `2 * gap + 1` and closed six.
    """
    flags = np.ones(40, dtype=bool)
    flags[10:12] = False  # texture
    flags[25:28] = False  # the border between two rectangles
    closed = detector._close_gaps(flags, 2)
    assert closed[10:12].all(), "a gap of two rows is texture and is closed"
    assert not closed[25:28].any(), "a gap of three rows is a border and is kept"


def test_texture_inside_one_rectangle_does_not_split_it() -> None:
    """Two rows that dim but do not go dark are one rectangle, not two."""
    cal = _calibration()
    image = _blank(cal)
    _draw(image, cal, 60, 100, 200)
    image[150:152] *= 0.89  # a ripple of 11%; a real border drops 75 to 80%
    result = detector.detect(image, cal, offset_px=2 * WHITE)
    assert len(result.runs) == 1 and result.runs[0].y_bottom == 200


def test_sparkles_are_too_small_and_too_narrow_to_be_notes() -> None:
    """The width gate and the minimum height, which a halo blob fails anyway."""
    cal = _calibration()
    image = _blank(cal)
    key = next(k for k in geometry.keys(cal) if k.midi == 60)
    x = int(key.mid)
    image[300:303, x - 2 : x + 2] = 240.0  # three rows of shining particle
    result = detector.detect(image, cal, offset_px=2 * WHITE)
    assert result.runs == []


def test_something_wider_than_a_white_key_is_not_a_note() -> None:
    cal = _calibration()
    image = _blank(cal)
    image[150:200, 200:400] = 240.0  # a title band drawn across the roll
    result = detector.detect(image, cal, offset_px=2 * WHITE)
    assert result.runs == []


def test_nothing_above_the_roll_top_is_music() -> None:
    """V-28: a toolbar or a progress bar over the top of the picture."""
    cal = _calibration(roll_top=60.0)
    image = _blank(cal)
    _draw(image, cal, 60, 10, 50)  # inside the chrome
    _draw(image, cal, 67, 100, 140)  # inside the roll
    result = detector.detect(image, cal, offset_px=2 * WHITE)
    assert [run.midi for run in result.runs] == [67]


def test_a_tip_inside_the_guard_band_is_flagged_and_not_deleted() -> None:
    """V-30: a rule may flag a run, it may not quietly delete one."""
    cal = _calibration(guard_band=40.0)
    image = _blank(cal)
    _draw(image, cal, 60, UPPER - 35, UPPER - 10)
    result = detector.detect(image, cal, offset_px=2 * WHITE)
    assert len(result.runs) == 1
    assert result.runs[0].tip_trusted is False
    assert result.onsets == [60], "the run still answers the window rule"


def test_two_runs_on_one_key_can_never_overlap() -> None:
    """V-27: one key, one lane, one answer — they come from one profile."""
    cal = _calibration()
    image = _blank(cal)
    for midi, y in ((60, 100), (62, 100), (64, 100)):
        _draw(image, cal, midi, y, y + 40)
    result = detector.detect(image, cal, offset_px=2 * WHITE)
    by_key: dict[int, list[DetectedRun]] = {}
    for run in result.runs:
        by_key.setdefault(run.midi, []).append(run)
    for runs in by_key.values():
        runs.sort(key=lambda r: r.y_top)
        for first, second in zip(runs, runs[1:]):
            assert first.y_bottom < second.y_top


def test_the_split_cuts_a_run_at_a_border_and_not_at_texture() -> None:
    """Prominence, because a share of the median cannot separate the two."""
    settings = DetectorSettings()
    plateau = np.full(120, 140.0)
    plateau[58:62] = 30.0  # a real border: it drops 0.79 of the plateau
    pieces = detector.split_run(plateau, 0, 119, settings, min_height=6)
    assert len(pieces) == 2

    rippled = np.full(120, 140.0)
    rippled[58:62] = 125.0  # texture inside one rectangle: 0.11
    assert detector.split_run(rippled, 0, 119, settings, min_height=6) == [(0, 119)]


def test_the_single_row_watcher_calls_every_lit_key_on() -> None:
    """The baseline to beat, and why it loses: it reads the row the halo lights."""
    cal = _calibration()
    image = _blank(cal)
    image[UPPER - 4 : UPPER] = 200.0  # the glow line across the whole width
    assert len(detector.detect_single_row(image, cal)) == 88
    assert detector.detect(image, cal, offset_px=2 * WHITE).onsets == []
