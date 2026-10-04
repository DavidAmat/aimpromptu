"""MuScriptor in the backend, and the live stream (implementation 08, Phase 4).

Every test but the last uses a fake MuScriptor model, so nothing here needs the GPU or the weights:
:class:`ReplayModel` replays the real events of the first 20 seconds of Superestrella, saved by
Phase 1 as they came out of MuScriptor ``large`` on the GPU (``tests/fixtures/pmn``). The last test
runs the real model, and only when a GPU and the cached weights are present.
"""

from __future__ import annotations

import json
import math
import threading
import time
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient
from scipy.io import wavfile

from aitu_backend.audio import formats, ingest, store
from aitu_backend.main import create_app
from aitu_backend.pmn import events_file
from aitu_backend.pmn.muscriptor import MuScriptorAssembler
from aitu_backend.schemas.metadata import AudioSource
from aitu_backend.storage import paths
from aitu_backend.transcription import engine as engine_module
from aitu_backend.transcription import lag, models, pipeline, split_cache, time_pipeline
from aitu_backend.transcription.engine import (
    DEFAULT_ENGINE,
    ENGINES,
    MuScriptorEngine,
    create_engine,
)
from aitu_backend.transcription.live import LiveNotes

FIXTURES = Path(__file__).parent / "fixtures" / "pmn"
EVENTS_20S = FIXTURES / "superestrella-20s-large-cuda.events.jsonl"
SUPERESTRELLA = "a585f9eb-36a1-49a0-9f0c-2626f3d292da"
LIBRARY_WAV = paths.backend_root() / "data" / "audio" / SUPERESTRELLA / "normalized.wav"
PHASE_1_FULL = (
    paths.repo_root()
    / "pocs"
    / "poc-muscriptor"
    / "out"
    / "full"
    / "large-float16-b1-prelude"
    / "notes.json"
)

needs_ffmpeg = pytest.mark.skipif(not formats.ffmpeg_available(), reason="ffmpeg is not installed")


def fixture_events() -> list[dict[str, Any]]:
    return [json.loads(line) for line in EVENTS_20S.read_text().splitlines()]


class ReplayModel:
    """Stands for ``muscriptor.TranscriptionModel``: same call, same events, no weights."""

    def __init__(self, events: list[dict[str, Any]] | None = None, pause: float = 0.0) -> None:
        self.events = fixture_events() if events is None else events
        self.pause = pause
        self.calls: list[dict[str, Any]] = []

    def transcribe(self, audio: tuple[Any, int], **options: Any):
        signal, rate = audio
        self.calls.append({"samples": int(signal.shape[-1]), "rate": rate, **options})
        for event in self.events:
            if self.pause:
                time.sleep(self.pause)
            yield dict(event)


@pytest.fixture(autouse=True)
def _fresh_models():
    models.clear()
    split_cache.forget()
    yield
    models.clear()
    split_cache.forget()


@pytest.fixture()
def replay(monkeypatch: pytest.MonkeyPatch) -> ReplayModel:
    model = ReplayModel()
    monkeypatch.setattr(models, "_load_muscriptor", lambda *args: model)
    monkeypatch.setattr(engine_module, "engine_installed", lambda name: True)
    return model


@pytest.fixture()
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(paths, "backend_root", lambda: tmp_path)
    paths.ensure_data_tree()
    return tmp_path / "data"


def ingested(tmp_path: Path, seconds: float = 20.0) -> str:
    rate = 16_000
    tone = 0.3 * np.sin(2 * np.pi * 220 * np.arange(int(rate * seconds)) / rate)
    source = tmp_path / "tone.wav"
    wavfile.write(source, rate, (tone * 32767).astype(np.int16))
    with source.open("rb") as handle:
        return ingest.ingest_file(handle, "tone.wav", AudioSource.UPLOAD).uuid


# ------------------------------------------------------------------ the engine


def test_muscriptor_is_forced_and_the_other_engines_are_kept() -> None:
    assert DEFAULT_ENGINE == "muscriptor"
    assert list(ENGINES)[0] == "muscriptor"
    assert {"bytedance", "transkun", "silent"} <= set(ENGINES)
    assert engine_module.selectable_engines() == {
        "muscriptor": engine_module.engine_installed("muscriptor")
    }


def test_the_engine_runs_with_the_settings_phase_1_chose(replay: ReplayModel) -> None:
    engine = create_engine("muscriptor", device="cpu")
    assert isinstance(engine, MuScriptorEngine)
    assert engine.name == "muscriptor-large"
    engine.run_signal(np.zeros(20 * 16_000, dtype=np.float32), 16_000)
    call = replay.calls[0]
    assert call["instruments"] == ["acoustic_piano"]
    assert call["batch_size"] == 1 and call["prelude_forcing"] is True
    assert call["samples"] == 20 * 16_000 and call["rate"] == 16_000


def test_the_model_is_loaded_once_per_size_device_and_dtype(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loads: list[tuple[str, ...]] = []

    def load(*key: str) -> ReplayModel:
        loads.append(key)
        return ReplayModel()

    monkeypatch.setattr(models, "_load_muscriptor", load)
    monkeypatch.setattr(engine_module, "engine_installed", lambda name: True)
    for _ in range(3):
        MuScriptorEngine(device="cuda")
    MuScriptorEngine(device="cuda", dtype="float32")
    assert loads == [("large", "cuda", "float16"), ("large", "cuda", "float32")]
    assert models.loaded() == [
        "muscriptor-large (cuda, float16)",
        "muscriptor-large (cuda, float32)",
    ]


def test_the_notes_are_the_phase_2_notes_with_ids_from_the_piece(replay: ReplayModel) -> None:
    engine = MuScriptorEngine(device="cpu")
    run = engine.run_signal(np.zeros(20 * 16_000, dtype=np.float32), 16_000, first_id=40)
    expected = MuScriptorAssembler(first_id=40).add_all(fixture_events()).notes(end_ms=20_000)
    assert [event.id for event in run.events] == expected.id.tolist()
    assert [event.midi_note for event in run.events] == expected.midi.tolist()
    assert [round(event.start * 1000) for event in run.events] == expected.on_ms.tolist()
    assert all(event.velocity == 64 for event in run.events)
    # 102 distinct onsets are too few to measure the lag (lag.MIN_ONSETS), so none is applied.
    assert run.lag_correction_ms == 0.0
    assert run.details["chunks"] == 4


def test_a_missing_package_names_the_install_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(engine_module, "engine_installed", lambda name: False)
    with pytest.raises(engine_module.EngineUnavailable, match="uv sync --extra muscriptor"):
        MuScriptorEngine(device="cpu")


def test_a_load_failure_says_to_check_the_token_and_the_licence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Gated:
        @staticmethod
        def load_model(*args: Any, **kwargs: Any) -> None:
            raise RuntimeError("401 Client Error")

    import muscriptor.transcription_model as real

    monkeypatch.setattr(real, "TranscriptionModel", Gated)
    with pytest.raises(models.LoadError, match="HF_TOKEN"):
        models.muscriptor("large", "cpu", "float16")


def test_the_preload_reads_its_spec(monkeypatch: pytest.MonkeyPatch) -> None:
    loads: list[tuple[str, ...]] = []

    def load(*key: str) -> object:
        loads.append(key)
        return object()

    monkeypatch.setattr(models, "_load_muscriptor", load)
    monkeypatch.setenv("AITU_DEVICE", "cpu")
    models.preload("muscriptor-medium")
    assert loads == [("medium", "cpu", "float16")]
    with pytest.raises(ValueError):
        models.preload("bytedance")
    models.preload_in_background("muscriptor-huge").join(5)
    assert "Unknown MuScriptor size" in (models.preload_error() or "")


# -------------------------------------------------------------------- the stream


def messages_of(events: list[dict[str, Any]], duration_ms: float, **options: Any) -> list[dict]:
    sent: list[dict] = []
    assembler = MuScriptorAssembler(first_id=0)
    live = LiveNotes(assembler, lambda name, payload: sent.append(payload), duration_ms, **options)
    for event in events:
        assembler.add(event)
        live.observe(event)
    live.finish()
    return sent


def test_every_rectangle_arrives_once_closed_with_its_saved_id() -> None:
    sent = messages_of(fixture_events(), 20_000, flush_seconds=0.0)
    closed = {}
    for message in sent:
        rows = message["closed"]
        for note_id, key, on_ms, len_ms in zip(
            rows["id"], rows["key"], rows["onMs"], rows["lenMs"]
        ):
            assert note_id not in closed, "a rectangle is closed twice"
            closed[note_id] = (key, on_ms, len_ms)
    expected = MuScriptorAssembler().add_all(fixture_events()).notes(end_ms=20_000)
    assert closed == {
        int(i): (int(k), int(o), int(n))
        for i, k, o, n in zip(expected.id, expected.key, expected.on_ms, expected.len_ms)
    }
    assert sent[-1]["open"] == {"id": [], "key": [], "onMs": []}


def test_the_messages_move_forward_and_count_whole_chunks() -> None:
    sent = messages_of(fixture_events(), 20_000, flush_seconds=0.0)
    assert [m["type"] for m in sent] == ["chunk"] * len(sent)
    assert all(m["total"] == 4 and m["durationMs"] == 20_000 for m in sent)
    dones = [m["done"] for m in sent]
    ups = [m["upToMs"] for m in sent]
    assert dones == sorted(dones) and ups == sorted(ups)
    assert dones[0] == 0 and dones[-1] == 4 and ups[-1] == 20_000
    # An open rectangle never starts after the time the message says it covers.
    for message in sent:
        assert all(on <= message["upToMs"] for on in message["open"]["onMs"])


def test_inside_a_chunk_the_messages_are_at_most_every_quarter_second() -> None:
    """With a slow clock, one message per chunk; with a fast one, more than one per chunk."""
    events = fixture_events()
    ticks = iter(range(10_000))
    per_chunk = messages_of(events, 20_000, clock=lambda: 0.0)
    assert len(per_chunk) == 6  # the start, one per chunk, and the end
    often = messages_of(events, 20_000, clock=lambda: next(ticks) * 0.1)
    assert len(often) > 5


# ------------------------------------------------------------------ the pipeline


@needs_ffmpeg
def test_a_new_transcription_is_stored_with_its_header_and_the_old_one_goes_to_history(
    data_dir: Path, tmp_path: Path, replay: ReplayModel
) -> None:
    uuid = ingested(tmp_path)
    first = pipeline.transcribe_audio(uuid)
    assert first.header.engine == "muscriptor-large"
    assert first.header.notes_revision == 1
    assert first.header.audio_revision == 0
    assert first.header.lag_correction_ms == 0.0
    count = len(first.events)
    assert [event.id for event in first.events] == list(range(count))
    before = pipeline.events_path(uuid).read_bytes()
    pipeline.rhythm_path(uuid).write_text("{}", encoding="utf-8")

    second = pipeline.transcribe_audio(uuid)
    assert second.header.notes_revision == 2
    # Never reused in a piece: the new ids continue after the old ones.
    assert [event.id for event in second.events] == list(range(count, 2 * count))
    snapshot = paths.history_version_dir(uuid, 1)
    assert (snapshot / "events.json").read_bytes() == before
    assert (snapshot / "rhythm.json").read_text() == "{}"
    assert not (snapshot / "normalized.wav").exists()  # the audio did not change
    assert not pipeline.rhythm_path(uuid).exists()


@needs_ffmpeg
def test_the_engine_hears_the_piece_without_the_cuts(
    data_dir: Path, tmp_path: Path, replay: ReplayModel
) -> None:
    uuid = ingested(tmp_path, seconds=20.0)
    store.set_cuts(uuid, [(500, 1000)])  # 5 s out of 20
    stored = pipeline.transcribe_audio(uuid)
    assert replay.calls[-1]["samples"] == 1500 * 160
    assert stored.duration_seconds == pytest.approx(15.0)
    assert stored.header.audio_revision == 1


@needs_ffmpeg
def test_the_filters_are_off_for_muscriptor_and_on_for_the_others(
    data_dir: Path, tmp_path: Path, replay: ReplayModel, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert pipeline.filters_for("muscriptor-large") == {"leakage": None, "artifacts": None}
    assert pipeline.filters_for("bytedance") == {}
    assert pipeline.filters_for(None) == {}

    seen: list[dict[str, Any]] = []
    real = time_pipeline.impose_granularity_and_split

    def spy(*args: Any, **kwargs: Any):
        seen.append(kwargs)
        return real(*args, **kwargs)

    monkeypatch.setattr(pipeline, "impose_granularity_and_split", spy)
    uuid = ingested(tmp_path)
    pipeline.transcribe_audio(uuid)
    pipeline.split_of(uuid, 40)
    assert seen[-1]["leakage"] is None and seen[-1]["artifacts"] is None


# ---------------------------------------------------------------- the split cache


@needs_ffmpeg
def test_the_split_is_computed_once_for_every_reader(
    data_dir: Path, tmp_path: Path, replay: ReplayModel, monkeypatch: pytest.MonkeyPatch
) -> None:
    computed: list[float] = []
    real = time_pipeline.impose_granularity_and_split

    def slow(*args: Any, **kwargs: Any):
        computed.append(kwargs["frame_ms"])
        time.sleep(0.1)
        return real(*args, **kwargs)

    monkeypatch.setattr(pipeline, "impose_granularity_and_split", slow)
    uuid = ingested(tmp_path)
    pipeline.transcribe_audio(uuid)

    # The job warms it, and a reader that arrives meanwhile waits instead of computing again.
    warming = pipeline.warm_split(uuid, 40)
    client = TestClient(create_app())
    readers = [
        threading.Thread(target=lambda: client.get(f"/time/{uuid}/score?frameMs=40"))
        for _ in range(2)
    ]
    for reader in readers:
        reader.start()
    warming.join(5)
    for reader in readers:
        reader.join(10)
    assert computed == [40]

    # The old piano roll used to compute it on every call.
    for _ in range(3):
        assert client.get(f"/matrix/{uuid}/events?frameMs=40").status_code == 200
    assert computed == [40]

    # A new transcription is a new events.json, so a new split.
    pipeline.transcribe_audio(uuid)
    pipeline.split_of(uuid, 40)
    assert computed == [40, 40]


# ---------------------------------------------------------------------- the route


@needs_ffmpeg
def test_the_route_streams_the_live_notes_and_ends_with_the_revision(
    data_dir: Path, tmp_path: Path, replay: ReplayModel
) -> None:
    client = TestClient(create_app())
    uuid = ingested(tmp_path)
    handle = client.post("/matrix/transcribe", json={"audioUuid": uuid, "force": True}).json()
    body = client.get(f"/matrix/progress/{handle['jobId']}").text

    frames = [frame for frame in body.split("\n\n") if frame.startswith(("event", "id", "data"))]
    chunks = [f for f in frames if f.startswith("event: chunk")]
    assert len(chunks) >= 5
    done = json.loads(frames[-1].split("data: ", 1)[1])
    assert done["type"] == "done" and done["status"] == "done"
    assert done["revision"] == 1 and done["audioUuid"] == uuid

    saved = events_file.read_piece(uuid)
    assert saved is not None
    streamed_ids = set()
    for frame in chunks:
        streamed_ids |= set(json.loads(frame.split("data: ", 1)[1])["closed"]["id"])
    assert streamed_ids == set(saved.notes.id.tolist())
    # Finished: no transcription of this piece is running any more.
    assert client.get(f"/matrix/{uuid}/job").status_code == 404


@needs_ffmpeg
def test_a_second_request_for_the_same_piece_joins_the_running_job(
    data_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = ReplayModel(pause=0.002)
    monkeypatch.setattr(models, "_load_muscriptor", lambda *args: model)
    monkeypatch.setattr(engine_module, "engine_installed", lambda name: True)
    client = TestClient(create_app())
    uuid = ingested(tmp_path)

    first = client.post("/matrix/transcribe", json={"audioUuid": uuid, "force": True}).json()
    second = client.post("/matrix/transcribe", json={"audioUuid": uuid, "force": True}).json()
    assert second["jobId"] == first["jobId"]
    assert client.get(f"/matrix/{uuid}/job").json()["jobId"] == first["jobId"]

    # A page that reloads and reconnects gets every frame from the start.
    late = client.get(f"/matrix/progress/{first['jobId']}").text
    assert late.count("event: chunk") >= 5
    assert len(model.calls) == 1


def test_the_engine_status_route(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AITU_DEVICE", "cpu")
    body = TestClient(create_app()).get("/matrix/engine").json()
    assert body["name"] == "muscriptor"
    assert body["device"] == "cpu"
    assert body["loaded"] == [] and body["waiting"] == 0 and body["error"] is None


# ------------------------------------------------------------------------ the lag


@pytest.mark.skipif(
    not (LIBRARY_WAV.is_file() and PHASE_1_FULL.is_file()),
    reason="needs the library copy of Superestrella and the Phase 1 notes",
)
def test_the_lag_of_superestrella_is_the_phase_1_answer() -> None:
    """Phase 1 measured +15 ms on the whole song: the notes move 15 ms earlier."""
    rate, samples = formats.read_wav(LIBRARY_WAV)
    notes = json.loads(PHASE_1_FULL.read_text())
    onsets = np.array([note["start"] * 1000.0 for note in notes])
    assert lag.lag_correction_ms(samples, rate, onsets) == 15.0
    # Too few onsets: no correction rather than a noisy one.
    assert lag.lag_correction_ms(samples[: 20 * rate], rate, onsets[onsets < 20_000]) == 0.0


# ------------------------------------------------------------------------ the GPU


def _gpu_and_weights() -> bool:
    try:
        import torch
        from huggingface_hub import try_to_load_from_cache
    except ImportError:
        return False
    if not torch.cuda.is_available() or not engine_module.engine_installed("muscriptor"):
        return False
    cached = try_to_load_from_cache("MuScriptor/muscriptor-large", "model.safetensors")
    return isinstance(cached, str)


@pytest.mark.skipif(not LIBRARY_WAV.is_file(), reason="needs the library copy of Superestrella")
@pytest.mark.skipif(not _gpu_and_weights(), reason="needs a GPU and the cached MuScriptor weights")
def test_the_real_model_on_the_gpu_gives_the_phase_1_notes() -> None:
    """The first 20 s of Superestrella, MuScriptor large in float16, against Phase 1's events."""
    rate, samples = formats.read_wav(LIBRARY_WAV)
    sent: list[dict] = []
    from aitu_backend.progress import CallbackProgress

    reporter = CallbackProgress(lambda event: None, on_message=lambda n, p: sent.append(p))
    engine = MuScriptorEngine(device="cuda", size="large", dtype="float16")
    started = time.perf_counter()
    run = engine.run_signal(samples[: 20 * rate], rate, reporter, first_id=1000)
    seconds = time.perf_counter() - started

    expected = MuScriptorAssembler().add_all(fixture_events()).notes(end_ms=20_000)
    got = {(event.midi_note, round(event.start * 1000)) for event in run.events}
    wanted = set(zip(expected.midi.tolist(), expected.on_ms.astype(int).tolist()))
    assert len(got & wanted) >= 0.95 * len(wanted)
    assert min(event.id or 0 for event in run.events) == 1000
    assert len(sent) >= 5 and sent[-1]["done"] == math.ceil(20 / 5)
    assert seconds < 20, f"20 s of audio took {seconds:.1f} s"
