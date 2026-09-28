"""Shared paths and helpers for the MuScriptor PoC.

Two environments use this file, so it imports neither package at module level:

* the **model** scripts (``0*_*.py``) run in MuScriptor's own venv, cloned beside
  the project (``../muscriptor``), because the backend does not depend on it yet;
* the **analysis** scripts (``1*_*.py``) run in the backend venv, because they need
  ``librosa``, ``matplotlib`` and the app's filters, and only read what the model
  scripts wrote to ``out/``.

Nothing here writes where the app reads.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

POC = Path(__file__).resolve().parent.parent
REPO = POC.parents[1]
OUT = POC / "out"
DATA = POC / "data"

AUDIO_ROOT = REPO / "aitu-backend" / "data" / "audio"
SUPERESTRELLA = "a585f9eb-36a1-49a0-9f0c-2626f3d292da"

#: The plan keeps large downloads on the second disk. Set before huggingface_hub
#: is imported, which is why every model script imports this module first.
os.environ.setdefault("HF_HUB_CACHE", "/mnt/ssd2/hf/data/hub")

SAMPLE_RATE = 16_000
CHUNK_SECONDS = 5.0
LOWEST_MIDI = 21
KEY_COUNT = 88


def wav_path(uuid: str = SUPERESTRELLA) -> Path:
    return AUDIO_ROOT / uuid / "normalized.wav"


def events_json_path(uuid: str = SUPERESTRELLA) -> Path:
    return AUDIO_ROOT / uuid / "matrices" / "events.json"


def load_wav(uuid: str = SUPERESTRELLA, start_s: float = 0.0, seconds: float | None = None):
    """The stored 16 kHz mono ``normalized.wav`` as a ``[1, T]`` float32 tensor."""
    import soundfile as sf  # noqa: PLC0415
    import torch  # noqa: PLC0415

    data, rate = sf.read(str(wav_path(uuid)), dtype="float32", always_2d=True)
    assert rate == SAMPLE_RATE, rate
    mono = data.mean(axis=1)
    a = int(round(start_s * SAMPLE_RATE))
    b = len(mono) if seconds is None else a + int(round(seconds * SAMPLE_RATE))
    return torch.from_numpy(mono[a:b].copy()).unsqueeze(0)


@dataclass
class Note:
    pitch: int
    start: float
    end: float
    instrument: str

    def as_dict(self) -> dict:
        return {
            "pitch": self.pitch,
            "start": round(self.start, 4),
            "end": round(self.end, 4),
            "instrument": self.instrument,
        }


def load_model(size: str = "large", device: str = "cuda", dtype: str | None = None):
    """Load a MuScriptor model and return it with the seconds the load took."""
    import torch  # noqa: PLC0415
    from muscriptor.transcription_model import TranscriptionModel  # noqa: PLC0415

    t0 = time.perf_counter()
    model = TranscriptionModel.load_model(size, device=device, dtype=dtype)
    if device.startswith("cuda"):
        torch.cuda.synchronize()
    return model, time.perf_counter() - t0


def run_stream(model, wav, *, log_events: bool = False, **kwargs) -> dict:
    """Run ``model.transcribe`` and record what arrives, and when.

    Returns the notes, the wall-clock time of every progress event (one per
    chunk), the time to the first note, and, with ``log_events``, every event
    exactly as the generator yielded it, with its arrival time.
    """
    import torch  # noqa: PLC0415
    from muscriptor.events import NoteEndEvent, NoteStartEvent, ProgressEvent  # noqa: PLC0415

    cuda = model._device.type == "cuda"
    if cuda:
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
    t0 = time.perf_counter()
    log: list[dict] = []
    progress: list[dict] = []
    notes: list[Note] = []
    open_: dict[int, NoteStartEvent] = {}
    first_note_at: float | None = None

    for ev in model.transcribe((wav, SAMPLE_RATE), **kwargs):
        t = time.perf_counter() - t0
        if isinstance(ev, NoteStartEvent):
            open_[ev.index] = ev
            if first_note_at is None:
                first_note_at = t
            if log_events:
                log.append(
                    {
                        "t": round(t, 4),
                        "type": "NoteStartEvent",
                        "pitch": ev.pitch,
                        "start_time": ev.start_time,
                        "index": ev.index,
                        "instrument": ev.instrument,
                    }
                )
        elif isinstance(ev, NoteEndEvent):
            s = open_.pop(ev.start_event_index)
            notes.append(Note(s.pitch, s.start_time, ev.end_time, s.instrument))
            if log_events:
                log.append(
                    {
                        "t": round(t, 4),
                        "type": "NoteEndEvent",
                        "end_time": ev.end_time,
                        "start_event_index": ev.start_event_index,
                    }
                )
        elif isinstance(ev, ProgressEvent):
            progress.append({"t": round(t, 4), "completed": ev.completed, "total": ev.total})
            if log_events:
                log.append(
                    {
                        "t": round(t, 4),
                        "type": "ProgressEvent",
                        "completed": ev.completed,
                        "total": ev.total,
                    }
                )
    if cuda:
        torch.cuda.synchronize()
    wall = time.perf_counter() - t0
    audio_s = wav.shape[-1] / SAMPLE_RATE
    notes.sort(key=lambda n: (n.start, n.pitch))
    return {
        "audio_seconds": round(audio_s, 3),
        "wall_seconds": round(wall, 3),
        "audio_per_wall": round(audio_s / wall, 2),
        "first_note_seconds": None if first_note_at is None else round(first_note_at, 3),
        "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2) if cuda else None,
        "note_count": len(notes),
        "progress": progress,
        "notes": [n.as_dict() for n in notes],
        "events": log,
    }


def write_json(path: Path, obj) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False))
    return path


def write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    return path


def read_json(path: Path):
    return json.loads(path.read_text())


def load_bytedance(uuid: str = SUPERESTRELLA) -> list[dict]:
    """The stored ByteDance notes, as ``{pitch, start, end, velocity}``."""
    data = read_json(events_json_path(uuid))
    return [
        {"pitch": e["midiNote"], "start": e["start"], "end": e["end"], "velocity": e["velocity"]}
        for e in data["events"]
        if not e.get("removed")
    ]


def run_dir(config: str, uuid: str = SUPERESTRELLA) -> Path:
    """Where ``04_full_song.py`` writes one run. Superestrella keeps the short path."""
    return OUT / "full" / (config if uuid == SUPERESTRELLA else f"{uuid[:8]}/{config}")


def result_name(config: str, uuid: str = SUPERESTRELLA) -> str:
    """File stem of an analysis result for one run."""
    return config if uuid == SUPERESTRELLA else f"{uuid[:8]}-{config}"


def full_uuid(prefix: str) -> str:
    """Resolve the first characters of a piece uuid to the full uuid."""
    found = [p.name for p in AUDIO_ROOT.iterdir() if p.name.startswith(prefix)]
    assert len(found) == 1, (prefix, found)
    return found[0]
