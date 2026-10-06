"""**Read notes** of the Video step (implementation 02, Phase 5, plan section 10.2): the reader's
steps in one job, each run only when it is not done yet for this piano overlay."""

from __future__ import annotations

from pathlib import Path

import pytest

from aitu_backend.pieces.status import piece_status
from aitu_backend.transcription import pipeline
from aitu_backend.video import piece, reading, sampling, store

from video_fixtures import UUID, Drawn, calibration, make_video, measurement

DRAWN = [
    Drawn(key_index=1, tip_at_frame_zero=-60.0, height=40),
    Drawn(key_index=4, tip_at_frame_zero=-180.0, height=60),
]


@pytest.fixture()
def counted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    """A drawn video, with sampling and the measurement counted instead of run."""
    make_video(tmp_path, monkeypatch, DRAWN)
    calls = {"sample": 0, "measure": 0}

    def sample(audio_uuid: str, *args: object, **kwargs: object) -> None:
        calls["sample"] += 1

    def measure(audio_uuid: str, **kwargs: object):  # type: ignore[no-untyped-def]
        calls["measure"] += 1
        found = measurement()
        store.save_measurement(audio_uuid, found)
        return found

    monkeypatch.setattr(sampling, "sample", sample)
    monkeypatch.setattr(reading, "measure_video", measure)
    return calls


def test_read_notes_measures_once_per_overlay_and_writes_the_notes(counted: dict[str, int]) -> None:
    written = piece.read_and_write(UUID)
    assert written.notes == 2
    assert pipeline.has_events(UUID)
    assert counted == {"sample": 0, "measure": 1}  # frames exist; never measured for this overlay

    piece.read_and_write(UUID)
    assert counted["measure"] == 1  # the same overlay: not measured again

    moved = calibration().model_copy(update={"upper_line": calibration().upper_line + 2})
    store.save_calibration(UUID, moved)
    piece.read_and_write(UUID)
    assert counted["measure"] == 2  # the piano was fitted again


def test_a_video_with_no_frames_is_sampled_first(counted: dict[str, int]) -> None:
    store.clear_frames(UUID)
    with pytest.raises(Exception):
        piece.read_and_write(UUID)  # the counted sampling writes no frame
    assert counted["sample"] == 1


def test_read_notes_needs_the_piano_fitted(counted: dict[str, int]) -> None:
    from aitu_backend.storage import paths  # noqa: PLC0415

    paths.video_calibration_path(UUID).unlink()
    with pytest.raises(piece.NotFitted):
        piece.read_and_write(UUID)


def test_an_unstable_speed_stops_before_the_notes(
    counted: dict[str, int], monkeypatch: pytest.MonkeyPatch
) -> None:
    def unstable(audio_uuid: str, **kwargs: object):  # type: ignore[no-untyped-def]
        found = measurement()
        found.scroll_speed.stable = False
        found.scroll_speed.reason = "two speeds"
        return found

    monkeypatch.setattr(reading, "measure_video", unstable)
    with pytest.raises(piece.NotStable, match="two speeds"):
        piece.read_and_write(UUID)
    assert not pipeline.has_events(UUID)


def test_the_notes_step_of_a_video_part_speaks_of_the_video(counted: dict[str, int]) -> None:
    from aitu_backend.storage import bundle  # noqa: PLC0415
    from aitu_backend.storage.bundle import AudioEntry, Segment, Timeline  # noqa: PLC0415

    import io  # noqa: PLC0415

    from aitu_backend.storage import audio_files  # noqa: PLC0415

    # A part with a measured audio file, as a downloaded video has.
    content_hash = audio_files.add_stream(io.BytesIO(b"an mp3"), "mp3")
    bundle.write_timeline(
        UUID,
        Timeline(
            audio={content_hash: AudioEntry(format="mp3", frames=400)},
            segments=[Segment(audio=content_hash, from_ms=0, to_ms=4000)],
        ),
    )
    notes = piece_status(UUID).step("notes")
    assert notes.state == "missing"
    assert notes.reason == "Read the notes of the video to see them."
    piece.read_and_write(UUID)
    assert piece_status(UUID).step("notes").state == "ready"
