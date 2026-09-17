"""The stitched roll: the whole video rebuilt as one tall picture (V-32).

Task 4.1.1 and Task 4.1.2. The video is drawn rather than downloaded — a black
roll and rectangles falling at a known speed down known keys — so where every
note starts and how long it lasts is arithmetic, not a guess.

The three awkward cases the frame to frame tracker had are tested here as
ordinary shapes, which is the whole of V-32's claim: a rectangle that appears
already crossing is a shape touching the bottom edge, two notes on the same key
with a small gap are two shapes with a gap between them, and a rectangle taller
than the roll band is one shape because the stitched roll has no band.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from aitu_backend.schemas.video import ScrollSpeed
from aitu_backend.storage import paths
from aitu_backend.video import notes as notes_module, stitch
from video_fixtures import (
    FRAMES,
    GUARD,
    KEY,
    SPEED,
    TRAVEL,
    UPPER,
    WIDTH,
    UUID,
    Drawn,
    calibration,
    draw_frame,
    make_video,
    measurement,
    white_midi,
)

ONE = [Drawn(key_index=3, tip_at_frame_zero=-60.0, height=40)]


@pytest.fixture()
def one_note(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[Drawn]:
    make_video(tmp_path, monkeypatch, ONE)
    return ONE


# ------------------------------------------------------------- the geometry --


def test_every_row_of_the_roll_lands_in_the_picture_exactly_once(one_note) -> None:
    """The strips tile the picture: no gap and no row read twice.

    This is what stops the stitch drifting. Stepping by a whole number of rows
    would lose 0.11 px a frame on a video travelling 16.89, which over 2728
    sampled frames is 305 px — 1.8 seconds of music (V-32 rests on V-06).
    """
    geom = stitch.plan(calibration(), measurement(), FRAMES)
    spans = [stitch.rows_of(index, geom) for index in range(FRAMES)]

    assert spans[0][0] == 0
    assert spans[-1][1] == geom.rows - 1
    for (_, end), (start, _) in zip(spans, spans[1:]):
        assert start == end + 1


def test_a_row_of_the_picture_is_a_time_and_the_bottom_row_is_the_start(one_note) -> None:
    """V-05 for the whole piece: a row is a distance above the upper line, and a
    distance over the scroll speed is a time. The bottom row is the oldest
    content the picture holds, which is as early as the guard band lets us see."""
    geom = stitch.plan(calibration(), measurement(), FRAMES)

    assert geom.seconds(geom.rows - 1) == pytest.approx((GUARD + 1) / SPEED, abs=1e-6)
    # One row is one pixel of travel, and the picture reads downward in reverse.
    assert geom.seconds(geom.rows - 2) - geom.seconds(geom.rows - 1) == pytest.approx(1 / SPEED)
    assert geom.seconds(0) > geom.seconds(geom.rows - 1)


def test_the_picture_costs_what_the_plan_said_it_would(one_note) -> None:
    """V-32's price: about forty thousand rows for a four minute video, one byte
    a pixel. The plan states it here so the memory is a number, not a surprise."""
    roll, geom = stitch.build(UUID)

    assert roll.shape == (geom.rows, WIDTH)
    assert roll.dtype == np.uint8
    # 2728 sampled frames at 16.89 px of travel, 1280 px wide: 59.5 MB.
    real = stitch.plan(
        calibration().model_copy(
            update={"white_width": 24.6, "upper_line": 560.0, "roll_top": 62.0}
        ),
        measurement().model_copy(
            update={"scroll_speed": ScrollSpeed(px_per_frame=16.888, px_per_second=168.88)}
        ),
        2728,
    )
    assert 45000 <= real.rows <= 48000
    assert 55 <= real.rows * 1280 / 1e6 <= 65


# ---------------------------------------------------------------- the notes --


def test_one_rectangle_is_one_note_at_the_time_the_drawing_puts_it(one_note) -> None:
    """Task 4.1.2. The onset is the shape's lowest row and the release its
    highest, both turned into seconds with the measured scroll speed."""
    read = notes_module.read_notes(UUID)

    assert len(read.notes) == 1
    note = read.notes[0]
    assert note.midi == white_midi(3)
    assert note.start == pytest.approx(ONE[0].onset_seconds(), abs=0.02)
    assert note.end == pytest.approx(ONE[0].release_seconds(), abs=0.02)
    # A pixel is 5.9 ms on this drawing, so two pixels is the whole tolerance.
    assert note.end - note.start == pytest.approx(ONE[0].height / SPEED, abs=0.015)


def test_two_notes_on_one_key_with_a_gap_are_two_shapes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The second of the three awkward cases the tracker had. In the stitched
    roll it is not a case at all: they are two shapes with a gap between them."""
    drawn = [
        Drawn(key_index=3, tip_at_frame_zero=-60.0, height=40),
        Drawn(key_index=3, tip_at_frame_zero=-160.0, height=40),
    ]
    make_video(tmp_path, monkeypatch, drawn)
    read = notes_module.read_notes(UUID)

    assert len(read.notes) == 2
    assert {note.midi for note in read.notes} == {white_midi(3)}
    starts = sorted(note.start for note in read.notes)
    assert starts[1] - starts[0] == pytest.approx(100 / SPEED, abs=0.02)


def test_a_rectangle_already_crossing_is_a_shape_on_the_bottom_edge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The first awkward case. A note that was already sounding when the video
    started has no onset in the picture, so it is flagged rather than invented —
    which is the same fact `clipped` records about a run the upper line cut."""
    drawn = [Drawn(key_index=5, tip_at_frame_zero=float(UPPER) + 10, height=120)]
    make_video(tmp_path, monkeypatch, drawn)
    read = notes_module.read_notes(UUID)

    assert len(read.notes) == 1
    assert read.notes[0].starts_before is True
    assert read.report.notes_starting_before == 1


def test_a_rectangle_taller_than_the_roll_is_one_shape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The third awkward case. The roll band is 300 rows and this rectangle is
    450, so no single frame ever shows the whole of it; the stitched roll has no
    band, so it is one shape with a top and a bottom."""
    drawn = [Drawn(key_index=6, tip_at_frame_zero=-120.0, height=450)]
    make_video(tmp_path, monkeypatch, drawn)
    read = notes_module.read_notes(UUID)

    assert len(read.notes) == 1
    note = read.notes[0]
    assert note.end - note.start == pytest.approx(450 / SPEED, abs=0.05)


def test_a_shape_a_gate_threw_out_is_reported_and_never_rounded_onto_a_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Task 4.1.2: a shape whose width does not match a key is reported rather
    than rounded onto one, because that is a detection problem wearing the mask
    of a timing problem."""
    drawn = [
        Drawn(key_index=3, tip_at_frame_zero=-60.0, height=40),
        # Four keys wide: far past `max_width`, so it is not a note.
        Drawn(key_index=8, tip_at_frame_zero=-60.0, height=40),
    ]
    frame_drawn = list(drawn)
    make_video(tmp_path, monkeypatch, frame_drawn)
    # Widen the second one by hand: the drawing helper only draws one key wide.
    folder = paths.video_frames_dir(UUID)
    for index in range(FRAMES):
        picture = draw_frame(index, [drawn[0]])
        tip = drawn[1].tip_at_frame_zero + index * TRAVEL
        top, bottom = max(0, int(tip) - drawn[1].height), min(UPPER, int(tip))
        if bottom > top:
            picture[top:bottom, int(5.5 * KEY) : int(9.5 * KEY)] = 235
        Image.fromarray(picture).save(folder / f"f{index + 1:06d}.jpg", "JPEG", quality=95)

    read = notes_module.read_notes(UUID)

    assert [note.midi for note in read.notes] == [white_midi(3)]
    assert sum(read.report.rejected.values()) > 0
    assert read.rejected, "a rejection is something a person can look at"
    assert all(one.reason for one in read.rejected)
