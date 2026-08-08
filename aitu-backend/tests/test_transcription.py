"""Transcription: the engine interface, events -> raw matrix, and the pipeline.

The engines themselves are not exercised — they need multi-hundred-megabyte
models. What is pinned here is everything *we* wrote: the interface contract,
event placement including the appendix's rounding examples, the five-step chain,
artifact persistence, and the recompute-from-raw guarantee.
"""

import struct
import time
import wave
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from aitu_backend.audio import formats, ingest
from aitu_backend.main import create_app
from aitu_backend.matrix.keys import note_to_row
from aitu_backend.matrix.time_grid import DEFAULT_FRAME_MS
from aitu_backend.progress import CallbackProgress, ProgressEvent
from aitu_backend.schemas.metadata import AudioSource
from aitu_backend.storage import paths
from aitu_backend.transcription import engine as engine_module
from aitu_backend.transcription import jobs, pipeline
from aitu_backend.transcription.engine import (
    ENGINES,
    EngineUnavailable,
    NoteEvent,
    SilentEngine,
    TranscriptionEngine,
    available_engines,
    create_engine,
)
from aitu_backend.transcription.events_to_matrix import shift_events

FFMPEG = formats.ffmpeg_available()
needs_ffmpeg = pytest.mark.skipif(not FFMPEG, reason="ffmpeg is not installed")

DO4, RE4, MI4 = note_to_row("Do-4"), note_to_row("Re-4"), note_to_row("Mi-4")
MIDI_C4 = 60


@pytest.fixture()
def temp_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(paths, "backend_root", lambda: tmp_path)
    paths.ensure_data_tree()
    return tmp_path / "data"


def sine_wav(path: Path, seconds: float = 1.0, rate: int = 8000) -> Path:
    samples = np.sin(2 * np.pi * 440 * np.arange(int(rate * seconds)) / rate)
    frames = b"".join(struct.pack("<h", int(value * 30000)) for value in samples)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(frames)
    return path


class ScaleEngine:
    """A stub engine that always returns Do Re Mi Fa Sol as slow negras.

    Stands in for a real model so the pipeline can be tested end to end without
    downloading one.
    """

    name = "scale-stub"

    def transcribe(self, wav_path: Path) -> list[NoteEvent]:
        return [
            NoteEvent(midi_note=MIDI_C4 + step, start=float(index), end=float(index) + 0.98)
            for index, step in enumerate([0, 2, 4, 5, 7])
        ]


# --------------------------------------------------------------- the interface


def test_note_events_reject_a_backwards_span() -> None:
    with pytest.raises(ValueError, match="end after it starts"):
        NoteEvent(midi_note=60, start=1.0, end=0.5)


def test_note_event_duration() -> None:
    assert NoteEvent(midi_note=60, start=1.0, end=2.5).duration == pytest.approx(1.5)


def test_the_stub_engines_satisfy_the_protocol() -> None:
    assert isinstance(SilentEngine(), TranscriptionEngine)
    assert isinstance(ScaleEngine(), TranscriptionEngine)


def test_the_silent_engine_still_checks_the_file_exists(tmp_path: Path) -> None:
    assert SilentEngine().transcribe(sine_wav(tmp_path / "t.wav")) == []
    with pytest.raises(FileNotFoundError):
        SilentEngine().transcribe(tmp_path / "absent.wav")


def test_an_unknown_engine_name_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown transcription engine"):
        create_engine("wishful-thinking")


def test_a_missing_engine_package_names_the_install_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The failure has to tell you what to run, not just that it failed."""
    import builtins
    from typing import Any

    real_import = builtins.__import__

    def blocked(name: str, *args: Any, **kwargs: Any) -> Any:
        if name.startswith("piano_transcription_inference"):
            raise ImportError("blocked for this test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked)

    with pytest.raises(EngineUnavailable) as caught:
        create_engine("bytedance")
    assert "uv sync --extra transcription" in str(caught.value)


def test_engine_availability_is_reportable() -> None:
    """Every registered engine is reported, and the stub is always there.

    Derived from ``ENGINES`` rather than written out: registering an engine is
    meant to be a one-line change, and a hardcoded set here would make it two.
    """
    status = available_engines()
    assert status["silent"] is True
    assert set(status) == set(ENGINES)
    assert {"bytedance", "silent"} <= set(status)


def test_availability_does_not_load_a_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """Probing must not pull a 165 MB checkpoint into memory."""

    def explode(*args: object, **kwargs: object) -> None:
        raise AssertionError("available_engines() must not construct an engine")

    monkeypatch.setattr(engine_module, "ByteDanceEngine", explode)
    monkeypatch.setattr(engine_module, "BasicPitchEngine", explode)
    assert "bytedance" in available_engines()


# ------------------------------------------------------------- the checkpoint


def test_the_checkpoint_lives_where_the_package_looks_for_it() -> None:
    """Mirrors the hardcoded path inside `piano_transcription_inference`."""
    assert engine_module.checkpoint_path().parent.name == "piano_transcription_inference_data"
    assert engine_module.checkpoint_path().name.endswith(".pth")


def test_an_existing_checkpoint_is_not_re_downloaded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(engine_module, "checkpoint_present", lambda: True)
    monkeypatch.setattr(engine_module, "download_checkpoint", engine_module.download_checkpoint)

    def explode(*args: object, **kwargs: object) -> None:
        raise AssertionError("should not download when the checkpoint is present")

    monkeypatch.setattr("urllib.request.urlretrieve", explode)
    assert engine_module.download_checkpoint() == engine_module.checkpoint_path()


def test_a_truncated_download_is_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A half-file is worse than no file: torch.load's error explains nothing."""
    target = tmp_path / "checkpoint.pth"
    monkeypatch.setattr(engine_module, "checkpoint_path", lambda: target)
    monkeypatch.setattr(engine_module, "checkpoint_present", lambda: False)

    def tiny(url: str, filename: object, reporthook: object = None) -> None:
        Path(str(filename)).write_bytes(b"not a real checkpoint")

    monkeypatch.setattr("urllib.request.urlretrieve", tiny)

    with pytest.raises(RuntimeError, match="too small to be valid"):
        engine_module.download_checkpoint()
    assert not target.exists()


def test_a_good_download_is_moved_into_place(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "checkpoint.pth"
    monkeypatch.setattr(engine_module, "checkpoint_path", lambda: target)
    monkeypatch.setattr(engine_module, "checkpoint_present", lambda: False)
    monkeypatch.setattr(engine_module, "CHECKPOINT_MIN_BYTES", 10)

    def fake(url: str, filename: object, reporthook: object = None) -> None:
        Path(str(filename)).write_bytes(b"x" * 64)
        if callable(reporthook):
            reporthook(1, 32, 64)
            reporthook(2, 32, 64)

    monkeypatch.setattr("urllib.request.urlretrieve", fake)

    events: list[ProgressEvent] = []
    assert engine_module.download_checkpoint(CallbackProgress(events.append)) == target
    assert target.read_bytes() == b"x" * 64
    assert not target.with_suffix(".partial").exists()
    assert any(event.stage == "download model" for event in events)


# ----------------------------------------------------------------- the events


def test_shifting_events_rebases_and_drops_what_falls_before_zero() -> None:
    events = [
        NoteEvent(midi_note=60, start=0.0, end=1.0),
        NoteEvent(midi_note=62, start=5.0, end=6.0),
    ]
    shifted = shift_events(events, 5.0)
    assert len(shifted) == 1
    assert shifted[0].midi_note == 62
    assert shifted[0].start == 0.0


# ------------------------------------------------------------------ pipeline
#
# The pipeline persists one file, ``events.json``, and builds everything else
# while a request is being answered. What is asserted here is therefore what was
# heard and what was written down, not what a grid looked like afterwards. The
# grid itself is covered in ``test_time_matrix_build.py`` and the hand split in
# ``test_time_pipeline.py``.


@pytest.fixture()
def scale_audio(temp_store: Path, tmp_path: Path) -> str:
    """An ingested five-second audio, ready for the stub engine."""
    if not FFMPEG:
        pytest.skip("ffmpeg is not installed")
    source = sine_wav(tmp_path / "scale.wav", seconds=5.0, rate=44100)
    with source.open("rb") as handle:
        return ingest.ingest_file(handle, "scale.wav", AudioSource.RECORDING).uuid


@needs_ffmpeg
def test_a_run_stores_the_recorded_notes_and_nothing_else(scale_audio: str) -> None:
    hands = pipeline.run_pipeline(scale_audio, engine=ScaleEngine())

    assert hands.frame_ms == DEFAULT_FRAME_MS
    assert hands.frame_count == round(5.0 * 1000 / DEFAULT_FRAME_MS)

    written = sorted(path.name for path in pipeline.matrices_dir(scale_audio).iterdir())
    assert written == ["events.json"]


@needs_ffmpeg
def test_the_stored_notes_are_the_times_the_engine_reported(scale_audio: str) -> None:
    pipeline.run_pipeline(scale_audio, engine=ScaleEngine())

    stored = pipeline.load_note_events(scale_audio)
    assert stored is not None
    assert [event.start for event in stored.events] == [0.0, 1.0, 2.0, 3.0, 4.0]
    assert stored.duration_seconds == pytest.approx(5.0, abs=0.05)


@needs_ffmpeg
def test_a_second_run_reuses_the_stored_notes(scale_audio: str) -> None:
    """The model is expensive and its answer does not change. Only ``force`` re-runs it."""

    class CountingEngine(ScaleEngine):
        calls = 0

        def transcribe(self, wav_path: Path) -> list[NoteEvent]:
            CountingEngine.calls += 1
            return super().transcribe(wav_path)

    pipeline.run_pipeline(scale_audio, engine=CountingEngine())
    pipeline.run_pipeline(scale_audio, engine=CountingEngine())
    assert CountingEngine.calls == 1

    pipeline.run_pipeline(scale_audio, engine=CountingEngine(), reuse_events=False)
    assert CountingEngine.calls == 2


@needs_ffmpeg
def test_the_frame_length_changes_the_grid_and_not_the_notes(scale_audio: str) -> None:
    """A different frame length is a different question, not a different transcription."""
    coarse = pipeline.run_pipeline(scale_audio, engine=ScaleEngine(), frame_ms=40)
    fine = pipeline.run_pipeline(scale_audio, engine=ScaleEngine(), frame_ms=20)

    assert fine.frame_count == coarse.frame_count * 2
    assert len(fine.right.active_rows()) == len(coarse.right.active_rows())


@needs_ffmpeg
def test_no_entry_point_of_the_pipeline_accepts_a_tempo(scale_audio: str) -> None:
    """D-01, asserted against the signatures rather than against one result."""
    import inspect

    for name in ("run_pipeline", "transcribe_audio"):
        parameters = inspect.signature(getattr(pipeline, name)).parameters
        forbidden = [p for p in parameters if "tempo" in p or "bpm" in p or "granularity" in p]
        assert forbidden == [], f"{name} still accepts {forbidden}"


@needs_ffmpeg
def test_a_range_limited_run_only_covers_the_range(scale_audio: str) -> None:
    hands = pipeline.run_pipeline(
        scale_audio,
        engine=ScaleEngine(),
        start_seconds=1.0,
        end_seconds=3.0,
    )
    # Two seconds at 40 ms per column.
    assert hands.frame_count == 50


@needs_ffmpeg
def test_the_pipeline_reports_every_stage(scale_audio: str) -> None:
    events: list[ProgressEvent] = []
    pipeline.run_pipeline(
        scale_audio,
        engine=ScaleEngine(),
        reporter=CallbackProgress(events.append),
    )
    stages = {event.stage for event in events}
    assert {"transcribe", "events"} <= stages


@needs_ffmpeg
def test_a_progressive_engine_reports_its_real_model_segments(scale_audio: str) -> None:
    class ProgressiveScaleEngine(ScaleEngine):
        def transcribe_with_progress(self, wav_path: Path, reporter) -> list[NoteEvent]:
            with reporter.stage("transcribe", total=3) as stage:
                stage.advance(message="model segment 1/3")
                stage.advance(message="model segment 2/3")
                stage.advance(message="model segment 3/3")
            return super().transcribe(wav_path)

    events: list[ProgressEvent] = []
    pipeline.run_pipeline(
        scale_audio,
        engine=ProgressiveScaleEngine(),
        reporter=CallbackProgress(events.append),
    )

    model_ticks = [
        event
        for event in events
        if event.stage == "transcribe" and event.message.startswith("model segment")
    ]
    assert [event.current for event in model_ticks] == [1, 2, 3]
    assert [event.fraction for event in model_ticks] == pytest.approx([1 / 3, 2 / 3, 1.0])


# ---------------------------------------------------------------------- jobs


def test_a_job_runs_and_reports_done() -> None:
    job = jobs.submit(lambda reporter: 42, mirror_to_terminal=False)
    frames = list(jobs.stream(job.id))

    assert job.result == 42
    assert job.status == "done"
    assert any("event: done" in frame for frame in frames)


def test_a_failing_job_carries_its_message() -> None:
    def explode(reporter: object) -> None:
        raise RuntimeError("the model fell over")

    job = jobs.submit(explode, mirror_to_terminal=False)
    frames = list(jobs.stream(job.id))

    assert job.status == "error"
    assert job.error == "the model fell over"
    assert any("the model fell over" in frame for frame in frames)


def test_streaming_an_unknown_job_still_terminates() -> None:
    frames = list(jobs.stream("nope"))
    assert any("No job" in frame for frame in frames)
    assert any("event: done" in frame for frame in frames)


def test_a_late_subscriber_catches_up_on_the_history() -> None:
    def work(reporter) -> str:
        with reporter.stage("collapse", total=2) as stage:
            stage.advance()
            stage.advance()
        return "ok"

    job = jobs.submit(work, mirror_to_terminal=False)
    while not job.finished:
        time.sleep(0.01)

    frames = list(jobs.stream(job.id))
    assert any('"stage": "collapse"' in frame for frame in frames)


# ----------------------------------------------------------------- endpoints


@pytest.fixture()
def client(temp_store: Path) -> TestClient:
    return TestClient(create_app())


def uploaded(client: TestClient, tmp_path: Path, seconds: float = 1.0) -> str:
    source = sine_wav(tmp_path / "t.wav", seconds=seconds, rate=44100)
    with source.open("rb") as handle:
        return client.post("/audio/upload", files={"file": ("t.wav", handle, "audio/wav")}).json()[
            "uuid"
        ]


def test_the_engines_endpoint_reports_availability(client: TestClient) -> None:
    body = client.get("/matrix/engines").json()
    assert body["silent"] is True


def test_transcribing_an_unknown_audio_is_a_404(client: TestClient) -> None:
    response = client.post("/matrix/transcribe", json={"audioUuid": "nope"})
    assert response.status_code == 404


@needs_ffmpeg
def test_reading_the_notes_before_transcription_is_a_409(
    client: TestClient, tmp_path: Path
) -> None:
    uuid = uploaded(client, tmp_path)

    response = client.get(f"/matrix/{uuid}/events")
    assert response.status_code == 409
    assert "transcribe" in response.json()["detail"].lower()


def test_an_unknown_job_is_a_404(client: TestClient) -> None:
    assert client.get("/matrix/jobs/nope").status_code == 404


@needs_ffmpeg
def test_the_transcribe_endpoint_returns_a_job_and_then_the_notes(
    client: TestClient, tmp_path: Path
) -> None:
    uuid = uploaded(client, tmp_path)

    response = client.post(
        "/matrix/transcribe",
        json={"audioUuid": uuid, "frameMs": 40, "engine": "silent"},
    )
    assert response.status_code == 202
    job_id = response.json()["jobId"]

    for _ in range(200):
        status = client.get(f"/matrix/jobs/{job_id}").json()
        if status["status"] != "running":
            break
        time.sleep(0.02)
    assert status["status"] == "done", status

    body = client.get(f"/matrix/{uuid}/events").json()
    assert body["audioUuid"] == uuid
    assert body["events"] == []


def test_the_transcribe_request_has_no_tempo_and_no_granularity() -> None:
    """The wire contract, not just the Python signature (D-01)."""
    from aitu_backend.api.matrix import TranscribeRequest

    fields = set(TranscribeRequest.model_fields)
    assert not {name for name in fields if "tempo" in name or "granularity" in name}
    assert "frame_ms" in fields
