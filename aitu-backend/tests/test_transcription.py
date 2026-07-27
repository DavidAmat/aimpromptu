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
from aitu_backend.progress import CallbackProgress, ProgressEvent
from aitu_backend.schemas.matrix import Granularity, MatrixProcessingStep
from aitu_backend.schemas.metadata import AudioSource
from aitu_backend.storage import paths
from aitu_backend.transcription import engine as engine_module
from aitu_backend.transcription import jobs, pipeline
from aitu_backend.transcription.engine import (
    EngineUnavailable,
    NoteEvent,
    SilentEngine,
    TranscriptionEngine,
    available_engines,
    create_engine,
)
from aitu_backend.transcription.events_to_matrix import (
    RAW_GRANULARITY,
    column_count,
    events_to_raw_matrix,
    shift_events,
)

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
    status = available_engines()
    assert status["silent"] is True
    assert set(status) == {"bytedance", "basic-pitch", "silent"}


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


# ------------------------------------------------------- events -> raw matrix


def test_the_grid_is_sized_from_the_audio() -> None:
    # Fusa at 60 BPM is 0.125 s per column, so 1 s is 8 columns.
    assert column_count(1.0, 60) == 8
    assert column_count(1.01, 60) == 9  # never truncates the tail
    assert column_count(0.01, 60) == 1  # never zero


def test_a_non_positive_duration_is_rejected() -> None:
    with pytest.raises(ValueError, match="positive"):
        column_count(0, 60)


def test_a_single_note_lands_where_it_was_played() -> None:
    events = [NoteEvent(midi_note=MIDI_C4, start=0.0, end=1.0)]
    report = events_to_raw_matrix(events, duration_seconds=2.0, tempo_bpm=60)

    assert report.placed == 1
    assert report.lossless
    assert report.matrix.granularity is RAW_GRANULARITY
    assert report.matrix.processing_step is MatrixProcessingStep.RAW
    # One second at fusa/60 BPM is 8 columns: one onset plus seven sustains.
    assert report.matrix.grid[DO4][:8].tolist() == [1, -1, -1, -1, -1, -1, -1, -1]
    assert report.matrix.grid[DO4][8:].tolist() == [0] * 8


def test_the_project_features_rounding_example() -> None:
    """From `project-features.md`:

        C3 -> onset at 00:00 (duration 1.1 seconds)
        C4 -> onset at 00:01.5 (duration 0.6 seconds)

    At 60 BPM and fusa granularity (0.125 s per column) the writable lengths
    are 1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48 columns — singles and dotted notes
    only, per the Appendix C adjacency rule.

    * 1.1 s = 8.8 columns -> **8** (a negra, 1.00 s); 12 would be 1.50 s.
    * 1.5 s onset lands exactly on column 12.
    * 0.6 s = 4.8 columns -> **4** (a corchea, 0.50 s); 6 would be 0.75 s.
    """
    events = [
        NoteEvent(midi_note=48, start=0.0, end=1.1),  # C3
        NoteEvent(midi_note=60, start=1.5, end=2.1),  # C4
    ]
    matrix = events_to_raw_matrix(events, duration_seconds=3.0, tempo_bpm=60).matrix

    c3, c4 = note_to_row("Do-3"), note_to_row("Do-4")
    assert matrix.grid[c3][:8].tolist() == [1] + [-1] * 7
    assert matrix.grid[c3][8] == 0
    assert matrix.cell(c4, 12) == 1
    assert matrix.grid[c4][12:16].tolist() == [1, -1, -1, -1]
    assert matrix.grid[c4][16] == 0


def test_notes_outside_the_88_keys_are_dropped_and_reported() -> None:
    events = [
        NoteEvent(midi_note=20, start=0.0, end=0.5),  # below A0
        NoteEvent(midi_note=109, start=0.0, end=0.5),  # above C8
        NoteEvent(midi_note=MIDI_C4, start=0.0, end=0.5),
    ]
    report = events_to_raw_matrix(events, duration_seconds=1.0, tempo_bpm=60)

    assert report.placed == 1
    assert sorted(report.dropped_out_of_range) == [20, 109]
    assert not report.lossless
    assert "outside the 88 keys" in report.describe()


def test_a_note_past_the_end_of_the_grid_is_dropped() -> None:
    events = [NoteEvent(midi_note=MIDI_C4, start=99.0, end=99.5)]
    report = events_to_raw_matrix(events, duration_seconds=1.0, tempo_bpm=60)
    assert report.placed == 0
    assert report.dropped_past_end == 1


def test_a_re_strike_shortens_the_previous_note() -> None:
    """The transition rule: a new onset always wins over a carried sustain."""
    events = [
        NoteEvent(midi_note=MIDI_C4, start=0.0, end=2.0),
        NoteEvent(midi_note=MIDI_C4, start=0.5, end=1.0),
    ]
    report = events_to_raw_matrix(events, duration_seconds=3.0, tempo_bpm=60)

    row = report.matrix.grid[DO4]
    assert row[0] == 1
    assert row[4] == 1  # 0.5 s = column 4 at fusa/60
    assert report.truncated == 1


def test_a_chord_places_every_note_in_the_same_column() -> None:
    events = [
        NoteEvent(midi_note=MIDI_C4, start=0.0, end=1.0),
        NoteEvent(midi_note=MIDI_C4 + 4, start=0.0, end=1.0),
        NoteEvent(midi_note=MIDI_C4 + 7, start=0.0, end=1.0),
    ]
    matrix = events_to_raw_matrix(events, duration_seconds=1.5, tempo_bpm=60).matrix
    assert matrix.onsets_in_column(0) == sorted([DO4, MI4, note_to_row("Sol-4")])


def test_an_empty_event_list_gives_a_silent_matrix() -> None:
    report = events_to_raw_matrix([], duration_seconds=2.0, tempo_bpm=60)
    assert report.matrix.is_empty()
    assert report.matrix.frame_count == 16
    assert report.placed == 0


def test_shifting_events_rebases_and_drops_what_falls_before_zero() -> None:
    events = [
        NoteEvent(midi_note=60, start=0.0, end=1.0),
        NoteEvent(midi_note=62, start=5.0, end=6.0),
    ]
    shifted = shift_events(events, 5.0)
    assert len(shifted) == 1
    assert shifted[0].midi_note == 62
    assert shifted[0].start == 0.0


def test_placement_reports_progress() -> None:
    events: list[ProgressEvent] = []
    events_to_raw_matrix(
        [NoteEvent(midi_note=MIDI_C4, start=0.0, end=1.0)],
        duration_seconds=1.0,
        tempo_bpm=60,
        reporter=CallbackProgress(events.append),
    )
    assert any(event.stage == "events" for event in events)


# ------------------------------------------------------------------ pipeline


@pytest.fixture()
def scale_audio(temp_store: Path, tmp_path: Path) -> str:
    """An ingested five-second audio, ready for the stub engine."""
    if not FFMPEG:
        pytest.skip("ffmpeg is not installed")
    source = sine_wav(tmp_path / "scale.wav", seconds=5.0, rate=44100)
    with source.open("rb") as handle:
        return ingest.ingest_file(handle, "scale.wav", AudioSource.RECORDING).uuid


@needs_ffmpeg
def test_the_five_steps_run_and_persist(scale_audio: str) -> None:
    result = pipeline.run_pipeline(scale_audio, 60, Granularity.NEGRA, engine=ScaleEngine())

    assert result.raw.granularity is RAW_GRANULARITY
    assert result.collapsed.granularity is Granularity.NEGRA
    assert result.clean.processing_step is MatrixProcessingStep.CLEAN
    assert result.hands.right.shape == result.clean.shape
    assert result.engine_name == "scale-stub"

    # Every artifact is on disk.
    assert pipeline.raw_path(scale_audio).is_file()
    for step in (MatrixProcessingStep.COLLAPSED, MatrixProcessingStep.CLEAN):
        assert pipeline.derived_path(scale_audio, step, Granularity.NEGRA).is_file()
    right, left = pipeline.hands_paths(scale_audio, Granularity.NEGRA)
    assert right.is_file() and left.is_file()


@needs_ffmpeg
def test_the_scale_lands_on_consecutive_beats(scale_audio: str) -> None:
    """Do Re Mi Fa Sol as negras at 60 BPM: one note per column, in order."""
    result = pipeline.run_pipeline(scale_audio, 60, Granularity.NEGRA, engine=ScaleEngine())

    for column, name in enumerate(["Do-4", "Re-4", "Mi-4", "Fa-4", "Sol-4"]):
        assert result.clean.cell(note_to_row(name), column) == 1
    # All above middle C, so the left hand is empty.
    assert result.hands.left.is_empty()
    assert not result.hands.right.is_empty()


@needs_ffmpeg
def test_recompute_reuses_the_raw_matrix(scale_audio: str) -> None:
    """A granularity change must never re-transcribe."""
    pipeline.run_pipeline(scale_audio, 60, Granularity.NEGRA, engine=ScaleEngine())

    class ExplodingEngine:
        name = "must-not-run"

        def transcribe(self, wav_path: Path) -> list[NoteEvent]:
            raise AssertionError("recompute must not re-transcribe")

    # Even asked to run the pipeline again, it reuses the stored raw matrix.
    again = pipeline.run_pipeline(scale_audio, 60, Granularity.CORCHEA, engine=ExplodingEngine())
    assert again.granularity is Granularity.CORCHEA
    assert again.build is None  # no transcription happened


@needs_ffmpeg
def test_recompute_is_fast(scale_audio: str) -> None:
    """The exit criterion behind instant granularity switching."""
    pipeline.run_pipeline(scale_audio, 60, Granularity.NEGRA, engine=ScaleEngine())

    started = time.perf_counter()
    pipeline.recompute(scale_audio, 72, Granularity.SEMICORCHEA)
    assert time.perf_counter() - started < 1.0


@needs_ffmpeg
def test_changing_the_bpm_reinterprets_the_same_grid(scale_audio: str) -> None:
    pipeline.run_pipeline(scale_audio, 60, Granularity.NEGRA, engine=ScaleEngine())
    slow = pipeline.recompute(scale_audio, 60, Granularity.NEGRA)
    fast = pipeline.recompute(scale_audio, 120, Granularity.NEGRA)

    assert slow.clean.frame_count == fast.clean.frame_count
    assert fast.clean.time_step_seconds == pytest.approx(slow.clean.time_step_seconds / 2)


@needs_ffmpeg
def test_recompute_without_a_raw_matrix_explains_itself(scale_audio: str) -> None:
    with pytest.raises(FileNotFoundError, match="run the pipeline once first"):
        pipeline.recompute(scale_audio, 60, Granularity.NEGRA)


@needs_ffmpeg
def test_stored_granularities_are_listed_coarsest_first(scale_audio: str) -> None:
    pipeline.run_pipeline(scale_audio, 60, Granularity.NEGRA, engine=ScaleEngine())
    pipeline.recompute(scale_audio, 60, Granularity.SEMICORCHEA)
    assert pipeline.stored_granularities(scale_audio) == [
        Granularity.NEGRA,
        Granularity.SEMICORCHEA,
    ]


@needs_ffmpeg
def test_a_range_limited_run_only_covers_the_range(scale_audio: str) -> None:
    result = pipeline.run_pipeline(
        scale_audio,
        60,
        Granularity.NEGRA,
        engine=ScaleEngine(),
        start_seconds=1.0,
        end_seconds=3.0,
    )
    # Two seconds at one negra per second.
    assert result.clean.frame_count == 2


@needs_ffmpeg
def test_the_pipeline_reports_every_stage(scale_audio: str) -> None:
    events: list[ProgressEvent] = []
    pipeline.run_pipeline(
        scale_audio,
        60,
        Granularity.NEGRA,
        engine=ScaleEngine(),
        reporter=CallbackProgress(events.append),
    )
    stages = {event.stage for event in events}
    assert {"transcribe", "events", "collapse", "clean", "two-hands"} <= stages


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
        60,
        Granularity.NEGRA,
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


def test_the_engines_endpoint_reports_availability(client: TestClient) -> None:
    body = client.get("/matrix/engines").json()
    assert body["silent"] is True


def test_transcribing_an_unknown_audio_is_a_404(client: TestClient) -> None:
    response = client.post("/matrix/transcribe", json={"audioUuid": "nope"})
    assert response.status_code == 404


def test_reading_a_matrix_before_transcription_is_a_409(client: TestClient, tmp_path: Path) -> None:
    if not FFMPEG:
        pytest.skip("ffmpeg is not installed")
    source = sine_wav(tmp_path / "t.wav", seconds=1.0, rate=44100)
    with source.open("rb") as handle:
        uuid = client.post("/audio/upload", files={"file": ("t.wav", handle, "audio/wav")}).json()[
            "uuid"
        ]

    response = client.get(f"/matrix/{uuid}")
    assert response.status_code == 409
    assert "transcribe" in response.json()["detail"]


def test_an_unknown_job_is_a_404(client: TestClient) -> None:
    assert client.get("/matrix/jobs/nope").status_code == 404


@needs_ffmpeg
def test_the_transcribe_endpoint_returns_a_job(client: TestClient, tmp_path: Path) -> None:
    source = sine_wav(tmp_path / "t.wav", seconds=1.0, rate=44100)
    with source.open("rb") as handle:
        uuid = client.post("/audio/upload", files={"file": ("t.wav", handle, "audio/wav")}).json()[
            "uuid"
        ]

    response = client.post(
        "/matrix/transcribe",
        json={"audioUuid": uuid, "tempoBpm": 60, "granularity": "negra", "engine": "silent"},
    )
    assert response.status_code == 202
    job_id = response.json()["jobId"]

    for _ in range(200):
        status = client.get(f"/matrix/jobs/{job_id}").json()
        if status["status"] != "running":
            break
        time.sleep(0.02)
    assert status["status"] == "done", status

    matrix = client.get(f"/matrix/{uuid}", params={"granularity": "negra"}).json()
    assert matrix["granularity"] == "negra"
    assert matrix["matrixProcessingStep"] == "clean"
