"""Bringing a video in: the store under `video/`, and sampling its frames.

Task 3.2.1. The video is the source and the sampled frames are a cache (V-01),
so sampling again at another granularity throws the folder away and writes it
again — and everything derived from the old frames goes with it, because an
answer about frames that no longer exist is wrong without saying so.

The video these tests sample is made on the spot with ffmpeg, so they need no
download and no network.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from aitu_backend.audio import formats
from aitu_backend.schemas.video import VideoMetadata
from aitu_backend.storage import paths
from aitu_backend.video import images, sampling, store

UUID = "test-video"

needs_ffmpeg = pytest.mark.skipif(
    not formats.ffmpeg_available(), reason="ffmpeg is a local prerequisite and is not on PATH"
)


@pytest.fixture()
def temp_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(paths, "backend_root", lambda: tmp_path)
    paths.ensure_data_tree()
    return tmp_path / "data"


def _make_video(destination: Path, seconds: float = 2.0, width: int = 640) -> Path:
    """A real video file, two seconds of ffmpeg's own test pattern."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"testsrc=size={width}x{int(width * 9 / 16)}:rate=30:duration={seconds}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(destination),
        ],
        check=True,
        capture_output=True,
    )
    return destination


@needs_ffmpeg
def test_sampling_writes_one_frame_per_sampling_granularity(temp_store: Path) -> None:
    _make_video(paths.video_source_path(UUID))
    metadata = sampling.sample(UUID, 100.0)

    assert metadata.sample_ms == 100.0
    assert metadata.frame_count == 20  # two seconds at ten frames per second
    assert metadata.duration_seconds == pytest.approx(2.0, abs=0.05)
    assert store.frame_count(UUID) == 20


@needs_ffmpeg
def test_the_first_sampled_frame_is_the_start_of_the_video(temp_store: Path) -> None:
    """ffmpeg's `fps` filter emits its first frame at t = 0, so the index and the
    time line up with nothing to correct for: frame 0 is 0.0 s and frame 7 is
    0.7 s at a sampling granularity of 100 ms."""
    _make_video(paths.video_source_path(UUID))
    sampling.sample(UUID, 100.0)

    assert store.frame_time(0, 100.0) == 0.0
    assert store.frame_time(7, 100.0) == pytest.approx(0.7)
    assert store.frame_path(UUID, 0).name == "f000001.jpg"


@needs_ffmpeg
def test_every_sampled_frame_is_written_at_the_working_resolution(temp_store: Path) -> None:
    """V-35. The picture the browser draws is the picture the detector reads, so
    a coordinate the user places in the calibration UI needs no scaling."""
    _make_video(paths.video_source_path(UUID), width=640)
    metadata = sampling.sample(UUID, 200.0)

    assert metadata.frame_width == images.WORK_WIDTH
    assert metadata.frame_height == images.WORK_WIDTH * 9 // 16
    assert store.load_frame(UUID, 0).shape[1] == images.WORK_WIDTH


@needs_ffmpeg
def test_sampling_again_replaces_the_frames_and_everything_derived_from_them(
    temp_store: Path,
) -> None:
    """V-01: the video is the source and the frames are a cache. The plate and
    the reading are answers about the frames that were there, so they go too."""
    _make_video(paths.video_source_path(UUID))
    sampling.sample(UUID, 100.0)
    paths.video_plate_path(UUID).write_bytes(b"not a plate")
    paths.video_frames_jsonl_path(UUID).write_text('{"t": 0.0, "onsets": [], "sustains": []}\n')

    metadata = sampling.sample(UUID, 500.0)

    assert metadata.frame_count == 4  # two seconds at two frames per second
    assert not paths.video_plate_path(UUID).exists()
    assert not paths.video_frames_jsonl_path(UUID).exists()
    assert store.load_frame_lines(UUID) == []


@needs_ffmpeg
def test_the_disk_cost_of_the_frames_is_reported(temp_store: Path) -> None:
    """The number V-01 rests on: the frames cost several times the video, so
    keeping the video and treating them as a cache costs less disk, not more."""
    _make_video(paths.video_source_path(UUID))
    metadata = sampling.sample(UUID, 100.0)

    assert metadata.frames_bytes == store.frames_bytes(UUID) > 0
    assert metadata.size_bytes == paths.video_source_path(UUID).stat().st_size


def test_a_piece_with_no_video_is_said_to_have_none(temp_store: Path) -> None:
    assert not store.exists(UUID)
    with pytest.raises(store.VideoNotFound):
        store.require(UUID)
    assert store.uuids() == []


def test_the_metadata_and_the_measurement_are_kept_beside_the_video(temp_store: Path) -> None:
    """V-12: the calibration is kept beside the video, never inside rhythm.json."""
    store.save_metadata(VideoMetadata(audio_uuid=UUID, title="a piece", sample_ms=100.0))

    assert store.load_metadata(UUID).title == "a piece"
    assert paths.video_metadata_path(UUID).parent == paths.video_dir(UUID)
    assert store.load_calibration(UUID) is None
    assert store.load_measurement(UUID) is None


@needs_ffmpeg
def test_a_sampling_granularity_must_be_positive(temp_store: Path) -> None:
    _make_video(paths.video_source_path(UUID), seconds=0.5)
    with pytest.raises(ValueError):
        sampling.sample(UUID, 0.0)
