"""`/video` — the HTTP surface of Phase 3, in the order of the work.

Download, sample, calibrate, measure, detect. The download itself is not tested
here because it fetches from YouTube; everything after it is, on a video drawn on
the spot.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from aitu_backend.audio import store as audio_store
from aitu_backend.main import create_app
from aitu_backend.schemas.metadata import AudioSource
from aitu_backend.schemas.video import VideoMetadata
from aitu_backend.storage import paths
from aitu_backend.video import images, store

client = TestClient(create_app())

UUID = "http-video"
WIDTH, HEIGHT = 200, 160


@pytest.fixture()
def one_video(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """One piece with a video and four sampled frames, and nothing else."""
    monkeypatch.setattr(paths, "backend_root", lambda: tmp_path)
    monkeypatch.setattr(images, "WORK_WIDTH", WIDTH)
    paths.ensure_data_tree()

    entry = audio_store.create(
        alias="a drawn video", source=AudioSource.YOUTUBE, extension="mp3", audio_uuid=UUID
    )
    paths.video_source_path(entry.uuid).parent.mkdir(parents=True, exist_ok=True)
    paths.video_source_path(entry.uuid).write_bytes(b"not read by anything in this test")

    folder = paths.video_frames_dir(UUID)
    folder.mkdir(parents=True, exist_ok=True)
    for index in range(1, 5):
        frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        frame[20 * index : 20 * index + 12, 40:60] = 220
        Image.fromarray(frame).save(folder / f"f{index:06d}.jpg", "JPEG", quality=95)

    store.save_metadata(
        VideoMetadata(
            audio_uuid=UUID,
            title="a drawn video",
            sample_ms=100.0,
            frame_count=4,
            frame_width=WIDTH,
            frame_height=HEIGHT,
            duration_seconds=0.4,
        )
    )
    return UUID


def test_a_piece_with_no_video_is_a_404(one_video: str) -> None:
    assert client.get("/video/not-a-piece").status_code == 404
    assert client.get("/video/not-a-piece/frames/0").status_code == 404


def test_the_list_and_the_summary_say_what_we_have(one_video: str) -> None:
    listed = client.get("/video").json()
    assert [row["metadata"]["audioUuid"] for row in listed] == [UUID]

    summary = client.get(f"/video/{UUID}").json()
    assert summary["metadata"]["frameCount"] == 4
    assert summary["metadata"]["sampleMs"] == 100.0
    assert summary["calibration"] is None
    assert summary["measurement"] is None
    assert summary["detected"] is False


def test_a_sampled_frame_is_served_as_an_image(one_video: str) -> None:
    """V-35: the picture the browser draws is the picture the detector reads."""
    response = client.get(f"/video/{UUID}/frames/0")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert client.get(f"/video/{UUID}/frames/99").status_code == 404


def test_measuring_needs_a_piano_overlay_before_it_can_answer(one_video: str) -> None:
    """There is no upper line until the user has fitted the piano (V-11), and
    without one there is no roll band to align."""
    response = client.post(f"/video/{UUID}/measure")
    assert response.status_code == 409
    assert "no piano overlay" in response.json()["detail"]


def test_reading_needs_a_piano_overlay_too(one_video: str) -> None:
    response = client.post(f"/video/{UUID}/detect")
    assert response.status_code == 202  # the job starts, and fails inside itself
    status = client.get(f"/video/{UUID}/report")
    assert status.status_code == 404


def test_the_detection_of_a_video_nobody_has_read_is_empty(one_video: str) -> None:
    assert client.get(f"/video/{UUID}/detection").json() == []
    assert client.get(f"/video/{UUID}/calibration").status_code == 404


def test_the_sampling_granularity_is_never_the_frame_length(one_video: str) -> None:
    """V-04. `sampleMs` is how often we look at the video; `frameMs` is the
    column length the sheet is read at. Nothing on this router takes `frameMs`."""
    schema = client.get("/openapi.json").json()
    video_paths = {p: v for p, v in schema["paths"].items() if p.startswith("/video")}
    names = {
        parameter["name"]
        for operations in video_paths.values()
        for operation in operations.values()
        for parameter in operation.get("parameters", [])
    }
    assert "sampleMs" in names
    assert "frameMs" not in names
