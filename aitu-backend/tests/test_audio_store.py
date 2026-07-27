"""Audio store CRUD, format handling and the `/audio` endpoints."""

import io
import struct
import subprocess
import wave
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from aitu_backend.audio import formats, ingest, store
from aitu_backend.audio.formats import UnsupportedFormat
from aitu_backend.audio.store import AudioNotFound
from aitu_backend.main import create_app
from aitu_backend.schemas.metadata import AudioSource
from aitu_backend.storage import paths

FFMPEG = formats.ffmpeg_available()
needs_ffmpeg = pytest.mark.skipif(not FFMPEG, reason="ffmpeg is not installed")


@pytest.fixture()
def temp_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the whole storage tree at a throwaway directory."""
    monkeypatch.setattr(paths, "backend_root", lambda: tmp_path)
    paths.ensure_data_tree()
    return tmp_path / "data"


def sine_wav(path: Path, seconds: float = 1.0, rate: int = 8000, freq: float = 440.0) -> Path:
    """A real, decodable WAV — a 440 Hz tone."""
    samples = np.sin(2 * np.pi * freq * np.arange(int(rate * seconds)) / rate)
    frames = b"".join(struct.pack("<h", int(value * 30000)) for value in samples)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(frames)
    return path


# --------------------------------------------------------------------- formats


@pytest.mark.parametrize(
    "name", ["a.mp3", "A.MP3", "song.aac", "x.m4a", "rec.wav", "take.webm", "take.ogg"]
)
def test_supported_suffixes_are_detected(name: str) -> None:
    assert formats.detect_extension(name) in {"mp3", "aac", "m4a", "wav", "webm", "ogg"}


def test_browser_recording_containers_are_accepted() -> None:
    """Chrome's MediaRecorder only produces webm/opus; ffmpeg converts it."""
    assert ".webm" in formats.SUPPORTED_SUFFIXES
    assert ".ogg" in formats.SUPPORTED_SUFFIXES


@pytest.mark.parametrize("name", ["a.flac", "a.aiff", "a.txt", "noextension"])
def test_unsupported_suffixes_are_rejected(name: str) -> None:
    with pytest.raises(UnsupportedFormat, match="unsupported extension"):
        formats.detect_extension(name)


def test_reading_a_wav_gives_normalized_floats(tmp_path: Path) -> None:
    rate, samples = formats.read_wav(sine_wav(tmp_path / "tone.wav"))
    assert rate == 8000
    assert len(samples) == 8000
    assert -1.0 <= samples.min() <= samples.max() <= 1.0


def test_duration_of_a_known_wav(tmp_path: Path) -> None:
    assert formats.duration_seconds(sine_wav(tmp_path / "t.wav", seconds=2.0)) == pytest.approx(2.0)


# -------------------------------------------------------------------- peaks


def test_peaks_have_the_requested_shape(tmp_path: Path) -> None:
    peaks = formats.compute_peaks(sine_wav(tmp_path / "t.wav"), points=100)
    assert peaks.points == 100
    assert len(peaks.min) == len(peaks.max) == 100
    assert peaks.duration_seconds == pytest.approx(1.0)
    assert peaks.sample_rate == 8000


def test_peaks_bracket_the_signal(tmp_path: Path) -> None:
    peaks = formats.compute_peaks(sine_wav(tmp_path / "t.wav"), points=50)
    assert min(peaks.min) < -0.5
    assert max(peaks.max) > 0.5
    assert all(low <= high for low, high in zip(peaks.min, peaks.max))


def test_peaks_never_exceed_the_sample_count(tmp_path: Path) -> None:
    """Asking for more buckets than samples returns one bucket per sample."""
    short = sine_wav(tmp_path / "short.wav", seconds=0.001, rate=8000)  # 8 samples
    peaks = formats.compute_peaks(short, points=1000)
    assert peaks.points == 8


def test_peaks_round_trip_through_their_dict() -> None:
    original = formats.WaveformPeaks(2, [-1.0, 0.0], [1.0, 0.5], 1.0, 8000)
    assert formats.WaveformPeaks.from_dict(original.to_dict()) == original


def test_zero_points_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="at least 1"):
        formats.compute_peaks(sine_wav(tmp_path / "t.wav"), points=0)


def test_slicing_a_wav_keeps_only_the_range(tmp_path: Path) -> None:
    source = sine_wav(tmp_path / "t.wav", seconds=2.0)
    target = formats.slice_wav(source, tmp_path / "clip.wav", 0.5, 1.5)
    assert formats.duration_seconds(target) == pytest.approx(1.0, abs=0.01)


def test_slicing_a_backwards_range_is_rejected(tmp_path: Path) -> None:
    source = sine_wav(tmp_path / "t.wav")
    with pytest.raises(ValueError, match="endSeconds must be after"):
        formats.slice_wav(source, tmp_path / "clip.wav", 1.0, 0.5)


# ---------------------------------------------------------------------- store


def test_create_makes_a_folder_with_metadata(temp_store: Path) -> None:
    entry = store.create("My tune", AudioSource.UPLOAD, "mp3")

    assert entry.directory.is_dir()
    assert paths.audio_metadata_path(entry.uuid).is_file()
    assert entry.metadata.alias == "My tune"
    assert entry.metadata.source is AudioSource.UPLOAD
    assert entry.metadata.format == "mp3"


def test_segment_metadata_requires_complete_lineage() -> None:
    with pytest.raises(ValueError, match="sourceAudioUuid"):
        store.create("Broken segment", AudioSource.SEGMENT, "wav")


def test_save_original_writes_the_bytes(temp_store: Path) -> None:
    entry = store.create("x", AudioSource.UPLOAD, "wav")
    store.save_original(entry.uuid, io.BytesIO(b"RIFFfake"), "wav")

    original = store.get(entry.uuid).original_path
    assert original is not None
    assert original.name == "original.wav"
    assert original.read_bytes() == b"RIFFfake"


def test_crud_round_trip(temp_store: Path) -> None:
    entry = store.create("First name", AudioSource.RECORDING, "wav")
    uuid = entry.uuid

    assert store.exists(uuid)
    assert store.read_metadata(uuid).alias == "First name"

    store.rename(uuid, "Second name")
    assert store.read_metadata(uuid).alias == "Second name"

    store.update(uuid, duration_seconds=12.5)
    assert store.read_metadata(uuid).duration_seconds == 12.5

    store.delete(uuid)
    assert not store.exists(uuid)
    with pytest.raises(AudioNotFound):
        store.read_metadata(uuid)


def test_listing_is_newest_first(temp_store: Path) -> None:
    first = store.create("one", AudioSource.UPLOAD, "wav")
    second = store.create("two", AudioSource.UPLOAD, "wav")
    store.update(second.uuid, alias="two")

    listed = [entry.metadata.alias for entry in store.list_all()]
    assert set(listed) == {"one", "two"}
    assert len(listed) == 2
    assert store.list_all()[0].metadata.created_at >= store.list_all()[1].metadata.created_at
    assert first.uuid != second.uuid


def test_a_half_written_folder_does_not_break_the_listing(temp_store: Path) -> None:
    store.create("good", AudioSource.UPLOAD, "wav")
    (paths.audio_root() / "broken").mkdir()

    assert [entry.metadata.alias for entry in store.list_all()] == ["good"]


def test_an_empty_alias_is_rejected(temp_store: Path) -> None:
    entry = store.create("x", AudioSource.UPLOAD, "wav")
    with pytest.raises(ValueError, match="cannot be empty"):
        store.rename(entry.uuid, "   ")


def test_the_uuid_cannot_be_changed(temp_store: Path) -> None:
    entry = store.create("x", AudioSource.UPLOAD, "wav")
    with pytest.raises(ValueError, match="cannot be changed"):
        store.update(entry.uuid, uuid="something-else")


def test_unknown_metadata_fields_are_rejected(temp_store: Path) -> None:
    entry = store.create("x", AudioSource.UPLOAD, "wav")
    with pytest.raises(ValueError, match="Unknown audio metadata field"):
        store.update(entry.uuid, colour="blue")


def test_deleting_a_missing_audio_raises(temp_store: Path) -> None:
    with pytest.raises(AudioNotFound):
        store.delete("nope")


# --------------------------------------------------------------------- ingest


@needs_ffmpeg
def test_ingest_normalizes_and_records_the_duration(temp_store: Path, tmp_path: Path) -> None:
    source = sine_wav(tmp_path / "scale.wav", seconds=1.5, rate=44100)

    with source.open("rb") as handle:
        entry = ingest.ingest_file(handle, "scale.wav", AudioSource.UPLOAD)

    assert entry.metadata.alias == "scale"  # filename stem
    assert entry.has_normalized()
    assert entry.metadata.duration_seconds == pytest.approx(1.5, abs=0.05)
    assert entry.metadata.sample_rate == formats.TRANSCRIPTION_SAMPLE_RATE

    rate, samples = formats.read_wav(entry.normalized_path)
    assert rate == formats.TRANSCRIPTION_SAMPLE_RATE
    assert samples.ndim == 1  # mono


@needs_ffmpeg
def test_an_explicit_alias_wins_over_the_filename(temp_store: Path, tmp_path: Path) -> None:
    source = sine_wav(tmp_path / "raw-take-3.wav")
    with source.open("rb") as handle:
        entry = ingest.ingest_file(handle, source.name, AudioSource.UPLOAD, alias="Levels - Avicii")
    assert entry.metadata.alias == "Levels - Avicii"


def test_a_failed_ingest_leaves_no_folder_behind(temp_store: Path) -> None:
    """A half-ingested audio in the library is worse than a failed upload."""
    before = set(paths.list_audio_uuids())
    with pytest.raises(Exception):
        ingest.ingest_file(io.BytesIO(b"not audio at all"), "junk.wav", AudioSource.UPLOAD)
    assert set(paths.list_audio_uuids()) == before


def test_an_unsupported_format_never_creates_a_folder(temp_store: Path) -> None:
    with pytest.raises(UnsupportedFormat):
        ingest.ingest_file(io.BytesIO(b"x"), "song.flac", AudioSource.UPLOAD)
    assert paths.list_audio_uuids() == []


@needs_ffmpeg
def test_waveform_is_cached_and_reused(temp_store: Path, tmp_path: Path) -> None:
    source = sine_wav(tmp_path / "t.wav", seconds=1.0, rate=44100)
    with source.open("rb") as handle:
        entry = ingest.ingest_file(handle, "t.wav", AudioSource.UPLOAD)

    first = ingest.waveform(entry.uuid, points=200)
    assert entry.waveform_path.is_file()
    assert ingest.waveform(entry.uuid, points=200) == first


@needs_ffmpeg
def test_a_different_point_count_recomputes(temp_store: Path, tmp_path: Path) -> None:
    """The cache must not hand back the wrong resolution."""
    source = sine_wav(tmp_path / "t.wav", seconds=1.0, rate=44100)
    with source.open("rb") as handle:
        entry = ingest.ingest_file(handle, "t.wav", AudioSource.UPLOAD)

    assert ingest.waveform(entry.uuid, points=100).points == 100
    assert ingest.waveform(entry.uuid, points=250).points == 250


# ------------------------------------------------------------------ endpoints


@pytest.fixture()
def client(temp_store: Path) -> TestClient:
    return TestClient(create_app())


def test_listing_is_empty_on_a_fresh_store(client: TestClient) -> None:
    assert client.get("/audio/").json() == []


@needs_ffmpeg
def test_upload_endpoint_round_trip(client: TestClient, tmp_path: Path) -> None:
    source = sine_wav(tmp_path / "take.wav", seconds=1.0, rate=44100)

    with source.open("rb") as handle:
        response = client.post(
            "/audio/upload",
            files={"file": ("take.wav", handle, "audio/wav")},
            data={"alias": "Do Re Mi"},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["alias"] == "Do Re Mi"
    assert body["source"] == "upload"
    assert body["durationSeconds"] == pytest.approx(1.0, abs=0.05)
    uuid = body["uuid"]

    assert client.get("/audio/").json()[0]["uuid"] == uuid
    assert client.get(f"/audio/{uuid}").json()["alias"] == "Do Re Mi"

    renamed = client.patch(f"/audio/{uuid}", json={"alias": "Scale"})
    assert renamed.json()["alias"] == "Scale"

    waveform = client.get(f"/audio/{uuid}/waveform", params={"points": 64}).json()
    assert waveform["points"] == 64
    assert len(waveform["min"]) == len(waveform["max"]) == 64

    assert client.get(f"/audio/{uuid}/file").status_code == 200
    assert client.get(f"/audio/{uuid}/file", params={"normalized": True}).status_code == 200

    assert client.delete(f"/audio/{uuid}").json()["status"] == "deleted"
    assert client.get(f"/audio/{uuid}").status_code == 404


@needs_ffmpeg
def test_the_recording_endpoint_tags_its_source(client: TestClient, tmp_path: Path) -> None:
    source = sine_wav(tmp_path / "mic.wav", rate=44100)
    with source.open("rb") as handle:
        response = client.post("/audio/recording", files={"file": ("mic.wav", handle, "audio/wav")})
    assert response.status_code == 201
    assert response.json()["source"] == "recording"


@needs_ffmpeg
def test_trim_endpoint_creates_a_physical_segment_with_root_lineage(
    client: TestClient, tmp_path: Path
) -> None:
    source = sine_wav(tmp_path / "long.wav", seconds=4.0, rate=44100)
    with source.open("rb") as handle:
        parent = client.post(
            "/audio/upload",
            files={"file": ("long.wav", handle, "audio/wav")},
            data={"alias": "Long take"},
        ).json()

    response = client.post(
        f"/audio/{parent['uuid']}/trim",
        json={"startSeconds": 1.0, "endSeconds": 3.25, "alias": "Long take — chorus"},
    )

    assert response.status_code == 201, response.text
    segment = response.json()
    assert segment["source"] == "segment"
    assert segment["alias"] == "Long take — chorus"
    assert segment["sourceAudioUuid"] == parent["uuid"]
    assert segment["sourceTimeRange"] == {"startSeconds": 1.0, "endSeconds": 3.25}
    assert segment["durationSeconds"] == pytest.approx(2.25, abs=0.01)

    waveform = client.get(f"/audio/{segment['uuid']}/waveform", params={"points": 80}).json()
    assert waveform["durationSeconds"] == pytest.approx(2.25, abs=0.01)
    assert client.get(f"/audio/{segment['uuid']}/file").status_code == 200
    assert (
        client.get(f"/audio/{segment['uuid']}/file", params={"normalized": True}).status_code == 200
    )
    assert client.get(f"/audio/{parent['uuid']}").json()["durationSeconds"] == pytest.approx(
        4.0, abs=0.05
    )


@needs_ffmpeg
def test_trimming_a_segment_keeps_absolute_root_times(client: TestClient, tmp_path: Path) -> None:
    source = sine_wav(tmp_path / "long.wav", seconds=5.0, rate=44100)
    with source.open("rb") as handle:
        root_uuid = client.post(
            "/audio/upload", files={"file": ("long.wav", handle, "audio/wav")}
        ).json()["uuid"]
    first = client.post(
        f"/audio/{root_uuid}/trim",
        json={"startSeconds": 1.0, "endSeconds": 4.0},
    ).json()

    second = client.post(
        f"/audio/{first['uuid']}/trim",
        json={"startSeconds": 0.5, "endSeconds": 2.0},
    ).json()

    assert second["sourceAudioUuid"] == root_uuid
    assert second["sourceTimeRange"] == {"startSeconds": 1.5, "endSeconds": 3.0}


@needs_ffmpeg
def test_trim_endpoint_rejects_the_whole_audio(client: TestClient, tmp_path: Path) -> None:
    source = sine_wav(tmp_path / "whole.wav", seconds=2.0, rate=44100)
    with source.open("rb") as handle:
        uuid = client.post(
            "/audio/upload", files={"file": ("whole.wav", handle, "audio/wav")}
        ).json()["uuid"]

    response = client.post(
        f"/audio/{uuid}/trim",
        json={"startSeconds": 0, "endSeconds": 2.0},
    )

    assert response.status_code == 422
    assert "smaller range" in response.json()["detail"]


@needs_ffmpeg
def test_a_chrome_style_webm_recording_is_ingested(client: TestClient, tmp_path: Path) -> None:
    """The Chrome case, end to end: webm/opus in, normalized mono WAV out."""
    webm = tmp_path / "take.webm"
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            "-c:a",
            "libopus",
            "-f",
            "webm",
            str(webm),
        ],
        check=True,
    )

    with webm.open("rb") as handle:
        response = client.post(
            "/audio/recording", files={"file": ("take.webm", handle, "audio/webm")}
        )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["format"] == "webm"
    assert body["source"] == "recording"
    assert body["sampleRate"] == formats.TRANSCRIPTION_SAMPLE_RATE
    assert body["durationSeconds"] == pytest.approx(1.0, abs=0.1)


def test_uploading_an_unsupported_format_is_a_422(client: TestClient) -> None:
    response = client.post(
        "/audio/upload", files={"file": ("song.flac", io.BytesIO(b"x"), "audio/flac")}
    )
    assert response.status_code == 422
    assert "unsupported extension" in response.json()["detail"]


def test_unknown_uuids_are_404(client: TestClient) -> None:
    for url in ("/audio/nope", "/audio/nope/waveform", "/audio/nope/file"):
        assert client.get(url).status_code == 404
    assert client.delete("/audio/nope").status_code == 404
    assert client.patch("/audio/nope", json={"alias": "x"}).status_code == 404


def test_waveform_is_404_when_a_matrix_import_has_no_audio(
    client: TestClient, temp_store: Path
) -> None:
    entry = store.create("Imported matrix", AudioSource.UPLOAD, "json")

    response = client.get(f"/audio/{entry.uuid}/waveform")

    assert response.status_code == 404
    assert "no original file" in response.json()["detail"]


@needs_ffmpeg
def test_the_range_endpoint_returns_only_that_slice(client: TestClient, tmp_path: Path) -> None:
    source = sine_wav(tmp_path / "long.wav", seconds=3.0, rate=44100)
    with source.open("rb") as handle:
        uuid = client.post(
            "/audio/upload", files={"file": ("long.wav", handle, "audio/wav")}
        ).json()["uuid"]

    response = client.get(f"/audio/{uuid}/range", params={"startSeconds": 1.0, "endSeconds": 2.0})
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"

    clip = tmp_path / "clip.wav"
    clip.write_bytes(response.content)
    assert formats.duration_seconds(clip) == pytest.approx(1.0, abs=0.05)


@needs_ffmpeg
def test_a_backwards_range_is_a_422(client: TestClient, tmp_path: Path) -> None:
    source = sine_wav(tmp_path / "t.wav", seconds=2.0, rate=44100)
    with source.open("rb") as handle:
        uuid = client.post("/audio/upload", files={"file": ("t.wav", handle, "audio/wav")}).json()[
            "uuid"
        ]
    response = client.get(f"/audio/{uuid}/range", params={"startSeconds": 1.5, "endSeconds": 0.5})
    assert response.status_code == 422


def test_the_waveform_point_count_is_bounded(client: TestClient) -> None:
    assert client.get("/audio/any/waveform", params={"points": 0}).status_code == 422
    assert client.get("/audio/any/waveform", params={"points": 999999}).status_code == 422


def test_ffmpeg_is_documented_as_a_prerequisite() -> None:
    """If this fails on the Mac, `brew install ffmpeg` — see the backend README."""
    if not FFMPEG:
        pytest.skip("ffmpeg absent in this environment")
    assert subprocess.run(["ffmpeg", "-version"], capture_output=True).returncode == 0
