"""Disposable staged edit sessions under ``data/audio/<uuid>/staging/<session>/``.

Nothing outside this folder changes until the user accepts. Cancel deletes the
folder and that is the whole of it.
"""

from __future__ import annotations

import json
import shutil
import uuid as uuid_module
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from aitu_backend.storage import paths
from aitu_backend.transcription.engine import NoteEvent

SESSION_FILE = "session.json"
UNTRIMMED_WAV = "untrimmed.wav"
TRIMMED_WAV = "trimmed.wav"
SCALED_WAV = "scaled.wav"
TAKE_EVENTS_FILE = "take_events.json"
WINDOW_WAV = "window.wav"
WINDOW_SLOW_WAV = "window_slow.wav"


class SessionNotFound(KeyError):
    def __init__(self, audio_uuid: str, session_uuid: str) -> None:
        super().__init__(f"No edit session '{session_uuid}' for audio '{audio_uuid}'")
        self.audio_uuid = audio_uuid
        self.session_uuid = session_uuid


class SessionRecord(BaseModel):
    """What a session folder remembers about the window and the take."""

    model_config = ConfigDict(populate_by_name=True)

    session_uuid: str = Field(..., alias="sessionUuid")
    audio_uuid: str = Field(..., alias="audioUuid")
    start_frame: int = Field(..., alias="startFrame")
    end_frame: int = Field(..., alias="endFrame")
    start_seconds: float = Field(..., alias="startSeconds")
    end_seconds: float = Field(..., alias="endSeconds")
    frame_ms: float = Field(..., alias="frameMs")
    #: 1, 2, 4, or ``None`` for Fit to the window.
    slowdown: int | None = None
    factor: float = 1.0
    splice_audio: bool = Field(True, alias="spliceAudio")
    click_interval_ms: float | None = Field(None, alias="clickIntervalMs")
    first_onset_seconds: float | None = Field(None, alias="firstOnsetSeconds")
    trim_length_seconds: float | None = Field(None, alias="trimLengthSeconds")
    untrimmed_duration_seconds: float | None = Field(None, alias="untrimmedDurationSeconds")

    @property
    def window_seconds(self) -> float:
        return self.end_seconds - self.start_seconds

    @property
    def expected_take_seconds(self) -> float | None:
        if self.slowdown is None:
            return None
        return self.window_seconds * float(self.slowdown)


def new_session_uuid() -> str:
    return str(uuid_module.uuid4())


def session_dir(audio_uuid: str, session_uuid: str) -> Path:
    return paths.staging_session_dir(audio_uuid, session_uuid)


def session_path(audio_uuid: str, session_uuid: str) -> Path:
    return session_dir(audio_uuid, session_uuid) / SESSION_FILE


def exists(audio_uuid: str, session_uuid: str) -> bool:
    return session_path(audio_uuid, session_uuid).is_file()


def create(record: SessionRecord) -> SessionRecord:
    directory = session_dir(record.audio_uuid, record.session_uuid)
    directory.mkdir(parents=True, exist_ok=False)
    write(record)
    return record


def write(record: SessionRecord) -> Path:
    path = session_path(record.audio_uuid, record.session_uuid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(record.model_dump_json(by_alias=True, indent=2) + "\n", encoding="utf-8")
    return path


def read(audio_uuid: str, session_uuid: str) -> SessionRecord:
    path = session_path(audio_uuid, session_uuid)
    if not path.is_file():
        raise SessionNotFound(audio_uuid, session_uuid)
    return SessionRecord.model_validate_json(path.read_text(encoding="utf-8"))


def delete(audio_uuid: str, session_uuid: str) -> None:
    directory = session_dir(audio_uuid, session_uuid)
    if not directory.is_dir():
        raise SessionNotFound(audio_uuid, session_uuid)
    shutil.rmtree(directory)


def untrimmed_path(audio_uuid: str, session_uuid: str) -> Path:
    return session_dir(audio_uuid, session_uuid) / UNTRIMMED_WAV


def trimmed_path(audio_uuid: str, session_uuid: str) -> Path:
    return session_dir(audio_uuid, session_uuid) / TRIMMED_WAV


def scaled_path(audio_uuid: str, session_uuid: str) -> Path:
    return session_dir(audio_uuid, session_uuid) / SCALED_WAV


def take_events_path(audio_uuid: str, session_uuid: str) -> Path:
    return session_dir(audio_uuid, session_uuid) / TAKE_EVENTS_FILE


def window_path(audio_uuid: str, session_uuid: str) -> Path:
    return session_dir(audio_uuid, session_uuid) / WINDOW_WAV


def window_slow_path(audio_uuid: str, session_uuid: str) -> Path:
    return session_dir(audio_uuid, session_uuid) / WINDOW_SLOW_WAV


def has_take(audio_uuid: str, session_uuid: str) -> bool:
    return untrimmed_path(audio_uuid, session_uuid).is_file()


def has_events(audio_uuid: str, session_uuid: str) -> bool:
    return take_events_path(audio_uuid, session_uuid).is_file()


def write_take_events(audio_uuid: str, session_uuid: str, events: list[NoteEvent]) -> Path:
    path = take_events_path(audio_uuid, session_uuid)
    payload = {
        "schemaVersion": "1.0",
        "events": [
            {
                "midiNote": event.midi_note,
                "start": round(event.start, 4),
                "end": round(event.end, 4),
                "velocity": event.velocity,
                **({"hand": event.hand} if event.hand else {}),
            }
            for event in events
        ],
    }
    path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    return path


def read_take_events(audio_uuid: str, session_uuid: str) -> list[NoteEvent]:
    path = take_events_path(audio_uuid, session_uuid)
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [
        NoteEvent(
            midi_note=int(item["midiNote"]),
            start=float(item["start"]),
            end=float(item["end"]),
            velocity=int(item.get("velocity", 64)),
            hand=item.get("hand"),
        )
        for item in payload.get("events", [])
    ]
