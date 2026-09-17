"""What the motion of the roll says: the scroll speed and the two edges.

V-06 says the scroll speed is measured, never assumed, and V-45 says the
rectangles measure it themselves: every run of a frame is followed into the
next sampled frame and the fall of every free edge is collected. V-28 says the
roll is bounded above as well as below and both edges come from motion. All
three are tested here on runs and pictures built to fall by a known amount.
"""

from __future__ import annotations

import numpy as np
import pytest

from aitu_backend.schemas.video import DetectedRun
from aitu_backend.video import motion


def _run(midi: int, top: float, height: float = 40.0) -> DetectedRun:
    return DetectedRun(
        midi=midi,
        y_top=int(round(top)),
        y_bottom=int(round(top + height)),
        x0=0.0,
        x1=10.0,
        mid=5.0,
        width_keys=0.7,
        clipped=False,
        tip_trusted=True,
        entering=False,
    )


def _falling(travel: float, count: int, keys: tuple[int, ...] = (60, 62, 64, 65, 67)) -> list:
    """``count`` frames of rectangles, every one ``travel`` lower than in the last.

    Five keys with two rectangles each, staggered, so every pair of frames has
    twenty free edges to follow — well over :data:`motion.MIN_EDGES`.
    """
    frames = []
    for index in range(count):
        runs = []
        for slot, midi in enumerate(keys):
            for k in range(2):
                runs.append(_run(midi, 20 + slot * 30 + k * 150 + index * travel))
        frames.append(runs)
    return frames


def test_the_speed_is_the_fall_of_the_rectangles_followed_frame_to_frame() -> None:
    """V-45. Ten frames per second and 17 px per frame is 170 px per second."""
    speed = motion.scroll_speed(_falling(17.0, 40), sample_ms=100.0)
    assert speed.px_per_frame == pytest.approx(17.0, abs=0.05)
    assert speed.px_per_second == pytest.approx(170.0, abs=0.5)
    assert speed.stable and speed.reason == ""
    assert speed.usable_pairs == 39 and speed.total_pairs == 39


def test_the_part_of_a_pixel_survives_the_rounding_of_the_rows() -> None:
    """A travel of 16.4 rounds to 16 in some frames and 17 in others; the mean of
    the followed edges keeps the part of a pixel, which over a piece is seconds."""
    speed = motion.scroll_speed(_falling(16.4, 60), sample_ms=100.0)
    assert speed.px_per_frame == pytest.approx(16.4, abs=0.1)


def test_a_roll_that_never_moves_is_reported_and_not_averaged() -> None:
    """Rectangles in exactly the same place in every frame are a pause, not a
    measurement. They are counted as still and the speed is refused."""
    same = [[_run(60, 100), _run(64, 200)] for _ in range(12)]
    speed = motion.scroll_speed(same, sample_ms=100.0)
    assert speed.px_per_frame == 0.0
    assert not speed.stable
    assert "nothing in the roll fell" in speed.reason


def test_a_speed_that_is_not_stable_says_so_rather_than_answering_quietly() -> None:
    """V-06: a video whose scroll speed is not stable is reported as such and is
    not transcribed silently. A ritardando: the fall drifts from 20 px to 12."""
    frames = [_falling(1.0, 1)[0]]
    for index in range(40):
        step = 20.0 - 8.0 * index / 39
        frames.append([_run(r.midi, r.y_top + step) for r in frames[-1]])
    speed = motion.scroll_speed(frames, sample_ms=100.0)
    assert not speed.stable
    assert "varies by" in speed.reason


def test_a_roll_that_jumps_rather_than_scrolls_is_refused_too() -> None:
    """Half the pairs travel 20 px and half 8: the rectangles cannot be followed
    in the pairs that jump, and a majority of such pairs is not a steady roll."""
    frames = [_falling(1.0, 1)[0]]
    for index in range(40):
        step = 8.0 if index % 3 else 20.0
        frames.append([_run(r.midi, r.y_top + step) for r in frames[-1]])
    speed = motion.scroll_speed(frames, sample_ms=100.0)
    assert not speed.stable
    assert "could not be followed" in speed.reason


def test_a_scroll_speed_needs_two_sampled_frames() -> None:
    speed = motion.scroll_speed([_falling(17.0, 1)[0]], sample_ms=100.0)
    assert speed.px_per_frame == 0.0 and not speed.stable
    assert "at least two sampled frames" in speed.reason


def test_a_pair_with_too_few_rectangles_is_left_out_of_the_series() -> None:
    """A lone rectangle's two edges cannot outvote one detection's noise, so a
    pair that holds only it is reported as unusable rather than averaged in."""
    frames = _falling(17.0, 20)
    frames[10] = [frames[10][0]]  # one rectangle in the middle of the piece
    speed = motion.scroll_speed(frames, sample_ms=100.0)
    assert speed.usable_pairs == 17
    assert speed.series[9] == 0.0 and speed.series[10] == 0.0
    assert speed.px_per_frame == pytest.approx(17.0, abs=0.05)


def _scrolling_frames(
    count: int, travel: int, chrome_rows: int, upper: int, seed: int = 3
) -> list[np.ndarray]:
    """Pictures whose top rows never move and whose middle scrolls by ``travel``.

    That is a toolbar over a piano roll, which is what V-28 is about: a rectangle
    coming into view appears at the roll top and not at the top of the picture.
    """
    rng = np.random.default_rng(seed)
    roll = rng.uniform(0, 255, size=(upper * 4, 60))
    chrome = rng.uniform(0, 255, size=(chrome_rows, 60))
    out = []
    for index in range(count):
        frame = np.zeros((upper + 40, 60))
        frame[:chrome_rows] = chrome
        # The roll falls, so the window walks *backwards* through it as time
        # goes on: what sat at row y in one frame sits at row y + travel in the
        # next. Walking forwards makes the content rise, which is the same
        # picture upside down and answers a negative travel.
        start = (count - index) * travel
        frame[chrome_rows:upper] = roll[start : start + (upper - chrome_rows)]
        out.append(np.repeat(frame[:, :, None], 3, axis=2).astype(np.float32))
    return out


def test_the_roll_top_is_found_from_motion_and_not_from_what_the_chrome_looks_like() -> None:
    """V-28. The chrome is as busy as the roll and just as bright; the only thing
    that separates them is that one of them moved."""
    frames = _scrolling_frames(count=12, travel=17, chrome_rows=40, upper=300)
    top, bottom, score = motion.roll_bounds(lambda i: frames[i], list(range(10)), 300, 17)
    assert 38 <= top <= 44
    assert bottom > top + 100
    assert score[top + 50] > motion.ROLL_SCORE
    assert score[10] < motion.ROLL_SCORE


def test_the_guard_band_is_read_upward_from_the_upper_line() -> None:
    """The strike light at the line does not move either. Thirty rows of it,
    drawn still on every frame, are the guard band — and they are read on the
    difference against a plate, because on a photograph every raw row looks
    still (V-28 on the second rendering)."""
    upper, glow = 300, 30
    frames = _scrolling_frames(count=12, travel=17, chrome_rows=0, upper=upper)
    rng = np.random.default_rng(5)
    still = rng.uniform(0, 255, size=(glow, 60))
    plate = np.zeros_like(frames[0])
    for frame in frames:
        frame[upper - glow : upper] = np.repeat(still[:, :, None], 3, axis=2)
    top, bottom, _ = motion.roll_bounds(
        lambda i: frames[i], list(range(10)), upper, 17, plate=plate
    )
    assert top < 10
    # Up to one travel wider than the light, never narrower: a row whose content
    # falls into the light within one frame cannot be seen to move either.
    assert upper - glow - 17 - 6 <= bottom <= upper - glow + 6


def test_a_roll_the_bounds_cannot_see_leaves_the_guard_band_at_its_default() -> None:
    """A picture that never moves answers (0, 0), and `measure` then writes a
    guard band of zero, which the geometry reads as the measured default (V-24)
    rather than the whole roll."""
    same = np.repeat(np.random.default_rng(1).uniform(0, 255, size=(340, 60))[:, :, None], 3, 2)
    frames = [same.astype(np.float32)] * 12
    top, bottom, _ = motion.roll_bounds(lambda i: frames[i], list(range(10)), 300, 17)
    assert (top, bottom) == (0, 0)
    measurement = motion.measure(lambda i: frames[i], _falling(17.0, 12), 300, 100.0)
    assert measurement.scroll_speed.px_per_frame == pytest.approx(17.0, abs=0.05)
    assert measurement.guard_band == 0.0 and measurement.roll_top == 0.0
