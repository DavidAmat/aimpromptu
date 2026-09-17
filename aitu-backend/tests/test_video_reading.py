"""Reading a whole video: the plate, every sampled frame, and `frames.jsonl`.

Task 3.5.1, and the first caller the momentum rule has ever had. Phase 2 could
only unit test V-33 and V-34 on made-up runs, because one screenshot has no
neighbouring frame to ask. Here there is a whole video, so the rule finally does
what it was written to do: keep the rectangle that fell and refuse the title
drawn across the roll that did not.

The video is drawn rather than downloaded — a black roll, one white rectangle
falling down one key at a known speed, and one white blob of lettering that never
moves — so the right answer is known to the pixel.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from aitu_backend.schemas.video import (
    WHITE_PITCH_CLASSES,
    WHITE_WITH_BLACK_AFTER,
    BlackBorder,
    Calibration,
    PianoRect,
    VideoMetadata,
)
from aitu_backend.storage import paths
from aitu_backend.video import geometry, images, reading, store

UUID = "drawn-video"

#: The picture. Narrow and short on purpose: the test is about the rules, and a
#: frame of the working width would make it a benchmark instead.
WIDTH, HEIGHT, UPPER = 260, 320, 300
#: One white key of the drawn keyboard.
KEY = 26.0
#: Which white key the falling rectangle is drawn on, and which the lettering is.
NOTE_KEY, BLOB_KEY = 3, 7
#: The frames the lettering is drawn in: fewer than half of the frames the roll
#: moves in, so the plate — the median of what stands still (V-44) — cannot
#: hold it, and enough of them that it has a neighbour to be asked about.
BLOB_FRAMES = range(8, 15)
#: How far the rectangle falls between one sampled frame and the next.
TRAVEL = 17
#: Ten frames per second, which is the plan's sampling granularity.
SAMPLE_MS = 100.0


def _calibration() -> Calibration:
    """Ten white keys of 26 px, from A0, with the upper line at row 300."""
    borders = [i * KEY for i in range(11)]
    # One black key on every white key border the pattern of twos and threes puts
    # one on, built from the pattern rather than spelt out, so the count can
    # never disagree with the pitch class the overlay starts on.
    first = WHITE_PITCH_CLASSES.index(9)
    black = [
        BlackBorder(left=(i + 1) * KEY - 0.29 * KEY, right=(i + 1) * KEY + 0.29 * KEY)
        for i in range(len(borders) - 2)
        if WHITE_PITCH_CLASSES[(first + i) % 7] in WHITE_WITH_BLACK_AFTER
    ]
    return Calibration(
        image_width=WIDTH,
        image_height=HEIGHT,
        piano_rect=PianoRect(x=0.0, y=float(UPPER), width=float(WIDTH), height=20.0),
        upper_line=float(UPPER),
        white_borders=borders,
        black_borders=black,
        black_depth=12.0,
        first_white_pitch_class=9,
        first_white_octave=0,
        roll_top=0.0,
        guard_band=1.0,
    )


def _white_midi(index: int) -> int:
    """The MIDI pitch of the ``index``-th white key of the drawn keyboard."""
    whites = [key for key in geometry.keys(_calibration()) if key.kind == "white"]
    return whites[index].midi


def _frame(
    rectangle_top: int, blob: bool, height: int = 40, key_index: int = NOTE_KEY
) -> np.ndarray:
    """One picture: a black roll, one falling rectangle, and maybe the lettering."""
    frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    left = int(key_index * KEY) + 2
    right = int((key_index + 1) * KEY) - 2
    top = max(0, rectangle_top)
    bottom = min(UPPER, rectangle_top + height)
    if bottom > top:
        frame[top:bottom, left:right] = 230
    # The lettering: the same shape and the same brightness as the rectangle, on
    # another key, that never moves. It is drawn for part of the video and not
    # all of it, because a title that is in **every** frame is in the background
    # plate and the plate removes it before anything looks at it (V-15) — which
    # is the first line of defence and not the one being tested here. The
    # momentum rule is what catches the decoration the plate cannot: anything
    # that comes and goes (V-33).
    if blob:
        frame[120:160, int(BLOB_KEY * KEY) + 2 : int((BLOB_KEY + 1) * KEY) - 2] = 230
    # The keyboard below the upper line, so the picture looks like what it is.
    frame[UPPER:, :] = 200
    return frame


def _write(uuid: str, frames: list[np.ndarray]) -> None:
    folder = paths.video_frames_dir(uuid)
    folder.mkdir(parents=True, exist_ok=True)
    for index, frame in enumerate(frames, start=1):
        Image.fromarray(frame).save(folder / f"f{index:06d}.jpg", "JPEG", quality=95)


@pytest.fixture()
def drawn(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """A video of 24 frames whose rectangle crosses the upper line at frame 15.

    The rectangle starts above the roll and falls one travel per frame, so where
    its tip is in every frame is arithmetic rather than a guess.
    """
    monkeypatch.setattr(paths, "backend_root", lambda: tmp_path)
    monkeypatch.setattr(images, "WORK_WIDTH", WIDTH)
    paths.ensure_data_tree()

    tops = [-40 + index * TRAVEL for index in range(24)]
    _write(UUID, [_frame(top, index in BLOB_FRAMES) for index, top in enumerate(tops)])
    paths.video_source_path(UUID).write_bytes(b"not read by anything in this test")
    store.save_metadata(
        VideoMetadata(
            audio_uuid=UUID,
            sample_ms=SAMPLE_MS,
            frame_count=24,
            frame_width=WIDTH,
            frame_height=HEIGHT,
        )
    )
    store.save_calibration(UUID, _calibration())
    return tops


def test_the_reading_is_one_line_per_sampled_frame(drawn: list[int]) -> None:
    report = reading.read_video(UUID, offset_px=TRAVEL, travel=TRAVEL, workers=1)
    lines = store.load_frame_lines(UUID)

    assert report.frame_count == 24
    assert len(lines) == 24
    assert [line.t for line in lines[:3]] == [0.0, 0.1, 0.2]


def test_the_onset_is_reported_in_the_one_frame_the_tip_crosses_in(drawn: list[int]) -> None:
    """V-18 and V-25 together. The window is the measured travel and nothing
    else, so the tip is inside it in exactly one frame — set it wider and the
    same onset is reported in five frames in a row."""
    reading.read_video(UUID, offset_px=TRAVEL, travel=TRAVEL, workers=1)
    lines = store.load_frame_lines(UUID)

    with_onset = [index for index, line in enumerate(lines) if line.onsets]
    assert len(with_onset) == 1
    # The tip is at `top + 40`, so it lands inside [upper - travel, upper) once.
    index = with_onset[0]
    assert UPPER - TRAVEL <= drawn[index] + 40 < UPPER
    assert lines[index].onsets == [_white_midi(NOTE_KEY)]


def test_the_note_is_sustained_while_the_rectangle_crosses_and_then_released(
    drawn: list[int],
) -> None:
    """V-16: a run cut by the upper line has not got a tip there, so it is
    sounding. V-19: released is the default and is never written down."""
    reading.read_video(UUID, offset_px=TRAVEL, travel=TRAVEL, workers=1)
    lines = store.load_frame_lines(UUID)

    sustained = [index for index, line in enumerate(lines) if line.sustains]
    onset = next(index for index, line in enumerate(lines) if line.onsets)
    assert sustained, "a rectangle crossing the upper line is a sustained note"
    assert min(sustained) > onset
    assert all(line.onsets == [] for line in lines[onset + 1 :])
    assert lines[-1].onsets == [] and lines[-1].sustains == []


def test_the_lettering_never_reaches_the_reading(drawn: list[int]) -> None:
    """V-33, on a video, for the first time. The blob is the same shape and the
    same brightness as the rectangle and it sits on a key; the only thing that
    tells them apart is that one of them fell."""
    reading.read_video(UUID, offset_px=TRAVEL, travel=TRAVEL, workers=1)
    lines = store.load_frame_lines(UUID)

    every_key = {midi for line in lines for midi in line.onsets + line.sustains}
    assert _white_midi(BLOB_KEY) not in every_key

    detection = reading.detect_frame(UUID, 10, offset_px=TRAVEL, travel=TRAVEL)
    refused = [run for run in detection.refused if run.momentum == "static"]
    assert refused and all(run.midi == _white_midi(BLOB_KEY) for run in refused)
    assert any(run.momentum == "fell" for run in detection.runs)


def test_a_video_with_no_overlay_is_refused_rather_than_guessed_at(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(paths, "backend_root", lambda: tmp_path)
    paths.ensure_data_tree()
    _write("bare", [_frame(0, False)])
    with pytest.raises(reading.NotCalibrated):
        reading.read_video("bare", offset_px=TRAVEL, travel=TRAVEL, workers=1)


def test_frame_to_frame_agreement_is_the_score_when_there_is_no_ground_truth(
    drawn: list[int],
) -> None:
    """V-31. A rectangle falls by exactly the scroll speed between one sampled
    frame and the next, so a run that does not reappear one travel lower is a run
    the detector cut two ways on two pictures of the same rectangle.

    It is counted over **every** run the pixels gave, before the momentum rule
    refuses any, because it is a score for the detector and not for the rule. So
    decoration drags it down: on this drawn video the lettering is half of what
    is on the screen and agreement sits near 0.55, while on a real 4.5 minute
    video, where it is a handful of sparkles, it reads 0.97.
    """
    report = reading.read_video(UUID, offset_px=TRAVEL, travel=TRAVEL, workers=1)
    assert report.runs_refused == len(BLOB_FRAMES)
    assert 0.4 < report.agreement < 0.7
    assert store.load_report(UUID) == report
