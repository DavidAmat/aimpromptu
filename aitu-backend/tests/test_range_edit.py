"""Range editing splice: exact-width replacement, marks inside the window dropped, cancel is a no-op."""

import struct
import wave
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from aitu_backend.audio import formats
from aitu_backend.editing.history import current_version
from aitu_backend.editing.session import accept, cancel, patch, start, take_peaks, transcribe_take
from aitu_backend.editing.splice import (
    drop_marks_in_window,
    events_in_window,
    factor_for_slowdown,
    scale_take,
    splice_events,
    trim_take_events,
    window_from_frames,
)
from aitu_backend.main import create_app
from aitu_backend.schemas.rhythm import Fingering, HiddenNote, KeyChange, SavedRhythm, SpeedChange
from aitu_backend.schemas.time_matrix import BeamBreak, FigureName, FigureOverride
from aitu_backend.storage import paths, staging
from aitu_backend.transcription import pipeline
from aitu_backend.transcription.engine import NoteEvent


@pytest.fixture()
def temp_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(paths, "backend_root", lambda: tmp_path)
    paths.ensure_data_tree()
    return tmp_path / "data"


@pytest.fixture()
def client(temp_store: Path) -> TestClient:
    return TestClient(create_app())


def _note(midi: int, start: float, end: float, hand: str | None = None) -> NoteEvent:
    return NoteEvent(midi_note=midi, start=start, end=end, hand=hand)


def transcribed_piece() -> str:
    from aitu_backend.audio import store
    from aitu_backend.schemas.metadata import AudioSource

    entry = store.create("Piece", AudioSource.UPLOAD, "wav")
    pipeline.save_note_events(
        entry.uuid,
        [
            _note(60, 0.0, 0.4),
            _note(62, 1.0, 1.4),
            _note(64, 2.0, 2.4),
            _note(65, 3.0, 3.4),
            _note(67, 4.0, 4.4),
        ],
        duration_seconds=6.0,
        title="Piece",
    )
    return entry.uuid


# ---------------------------------------------------------------- the splice rule


def test_window_from_frames_freezes_seconds() -> None:
    window = window_from_frames(25, 100, 40.0)
    assert window.start_seconds == pytest.approx(1.0)
    assert window.end_seconds == pytest.approx(4.0)
    assert window.window_seconds == pytest.approx(3.0)


def test_membership_is_onset_only() -> None:
    """A note that started before the window and still sounds into it is not removed."""
    events = [_note(60, 0.5, 2.5), _note(62, 1.0, 1.2), _note(64, 2.0, 2.2)]
    inside = events_in_window(events, 1.0, 2.0)
    assert [event.midi_note for event in inside] == [62]


def test_scale_take_compresses_and_cuts_at_the_window_end() -> None:
    take = [_note(60, 0.0, 1.0), _note(62, 5.5, 6.5)]
    scaled = scale_take(take, factor=0.5, start_seconds=1.0, end_seconds=4.0, frame_ms=40)
    assert scaled[0].start == pytest.approx(1.0)
    assert scaled[0].end == pytest.approx(1.5)
    # 1 + 5.5*0.5 = 3.75, 1 + 6.5*0.5 = 4.25 → cut at 4.0
    assert scaled[1].start == pytest.approx(3.75)
    assert scaled[1].end == pytest.approx(4.0)


def test_notes_shorter_than_one_frame_are_dropped() -> None:
    take = [_note(60, 0.0, 0.05)]
    scaled = scale_take(take, factor=0.5, start_seconds=0.0, end_seconds=3.0, frame_ms=40)
    assert scaled == []


def test_splice_leaves_events_outside_the_window_byte_identical() -> None:
    original = [_note(60, 0.0, 0.4), _note(62, 1.2, 1.5), _note(64, 4.0, 4.3)]
    take = [_note(67, 0.0, 1.0)]
    result, removed, arriving = splice_events(
        original, take, start_seconds=1.0, end_seconds=4.0, factor=0.5, frame_ms=40
    )
    assert [event.midi_note for event in removed] == [62]
    assert len(arriving) == 1
    outside = [event for event in result if event.midi_note in (60, 64)]
    assert outside[0].model_dump() == original[0].model_dump()
    assert outside[1].model_dump() == original[2].model_dump()


def test_two_times_slower_is_a_factor_of_half() -> None:
    assert factor_for_slowdown(2, take_seconds=6.0, window_seconds=3.0) == 0.5
    assert factor_for_slowdown(None, take_seconds=5.0, window_seconds=2.5) == 0.5


def test_trim_from_first_onset() -> None:
    events = [_note(60, 0.4, 0.8), _note(62, 1.4, 1.8), _note(64, 7.0, 7.4)]
    trimmed = trim_take_events(events, first_onset=0.4, length_seconds=6.0)
    assert trimmed[0].start == pytest.approx(0.0)
    assert trimmed[1].start == pytest.approx(1.0)
    assert all(event.start < 6.0 for event in trimmed)
    assert 64 not in [event.midi_note for event in trimmed]


def test_marks_inside_the_window_are_dropped_and_counted() -> None:
    rhythm = SavedRhythm(
        hand="right",
        frame_ms=40,
        anchor_figure=FigureName.NEGRA,
        anchor_ms=480,
        speed_changes=[SpeedChange(start_frame=50, anchor_ms=600)],
        overrides=[
            FigureOverride(hand="right", row=39, start_frame=30, figure=FigureName.CORCHEA),
            FigureOverride(hand="right", row=39, start_frame=120, figure=FigureName.CORCHEA),
        ],
        beam_breaks=[BeamBreak(hand="right", start_frame=35)],
        hidden_notes=[HiddenNote(start_frame=40, row=10)],
        fingers=[Fingering(hand="right", start_frame=200, row=10, finger=1)],
        key_changes=[KeyChange(from_column=30, key_signature="D")],
    )
    cleaned = drop_marks_in_window(rhythm, 25, 100)
    assert cleaned.overrides == [
        FigureOverride(hand="right", row=39, start_frame=120, figure=FigureName.CORCHEA)
    ]
    assert cleaned.beam_breaks == []
    assert cleaned.hidden_notes == []
    assert cleaned.fingers == [Fingering(hand="right", start_frame=200, row=10, finger=1)]
    # A boundary inside the window is kept.
    assert cleaned.speed_changes == rhythm.speed_changes
    assert cleaned.key_changes == rhythm.key_changes


# ---------------------------------------------------------------- session lifecycle


def test_cancel_leaves_the_piece_untouched(temp_store: Path) -> None:
    uuid = transcribed_piece()
    before = pipeline.events_path(uuid).read_bytes()
    record = start(uuid, start_frame=25, end_frame=100, frame_ms=40, slowdown=2)
    assert staging.exists(uuid, record.session_uuid)
    cancel(uuid, record.session_uuid)
    assert not staging.exists(uuid, record.session_uuid)
    assert pipeline.events_path(uuid).read_bytes() == before


def test_accept_keeps_duration_and_outside_events(temp_store: Path) -> None:
    uuid = transcribed_piece()
    stored = pipeline.load_note_events(uuid)
    assert stored is not None
    outside_before = [
        event.model_dump() for event in stored.events if event.start < 1.0 or event.start >= 4.0
    ]
    record = start(uuid, start_frame=25, end_frame=100, frame_ms=40, slowdown=2)
    take = [_note(72, 0.0, 1.0), _note(74, 2.0, 3.0)]
    staging.write_take_events(uuid, record.session_uuid, take)
    record.first_onset_seconds = 0.0
    staging.write(record)

    result = accept(uuid, record.session_uuid)
    assert result.duration_seconds == pytest.approx(6.0)
    after = pipeline.load_note_events(uuid)
    assert after is not None
    assert after.duration_seconds == pytest.approx(6.0)
    outside_after = [
        event.model_dump() for event in after.events if event.start < 1.0 or event.start >= 4.0
    ]
    assert outside_after == outside_before
    arriving = [event for event in after.events if 1.0 <= event.start < 4.0]
    assert [event.midi_note for event in arriving] == [72, 74]
    assert arriving[0].start == pytest.approx(1.0)
    assert arriving[1].start == pytest.approx(2.0)
    assert current_version(uuid) == 2
    assert not staging.exists(uuid, record.session_uuid)


def test_accept_drops_marks_inside_the_window(temp_store: Path) -> None:
    uuid = transcribed_piece()
    pipeline.save_rhythm(
        uuid,
        SavedRhythm(
            hand="right",
            frame_ms=40,
            anchor_figure=FigureName.NEGRA,
            anchor_ms=480,
            overrides=[
                FigureOverride(hand="right", row=0, start_frame=50, figure=FigureName.CORCHEA),
                FigureOverride(hand="right", row=0, start_frame=120, figure=FigureName.CORCHEA),
            ],
        ),
    )
    record = start(uuid, start_frame=25, end_frame=100, frame_ms=40, slowdown=1)
    staging.write_take_events(uuid, record.session_uuid, [_note(72, 0.0, 0.5)])
    record.first_onset_seconds = 0.0
    staging.write(record)
    result = accept(uuid, record.session_uuid)
    assert result.dropped_marks.figure_overrides == 1
    saved = pipeline.load_rhythm(uuid)
    assert saved is not None
    assert [item.start_frame for item in saved.overrides] == [120]


def test_api_start_and_cancel(client: TestClient, temp_store: Path) -> None:
    uuid = transcribed_piece()
    before = pipeline.events_path(uuid).read_bytes()
    created = client.post(
        f"/audio/{uuid}/edits",
        json={"startFrame": 25, "endFrame": 100, "frameMs": 40, "slowdown": 2},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["windowSeconds"] == pytest.approx(3.0)
    assert body["factor"] == pytest.approx(0.5)
    assert body["expectedTakeSeconds"] == pytest.approx(6.0)
    session = body["sessionUuid"]
    cancelled = client.delete(f"/audio/{uuid}/edits/{session}")
    assert cancelled.status_code == 200
    assert pipeline.events_path(uuid).read_bytes() == before


def test_atempo_chain_stays_inside_one_pass() -> None:
    from aitu_backend.editing.audio_splice import atempo_chain

    assert atempo_chain(2.0) == ["atempo=2"]
    assert atempo_chain(0.5) == ["atempo=0.5"]
    assert atempo_chain(4.0) == ["atempo=2", "atempo=2"]


def test_api_typed_timestamps(client: TestClient, temp_store: Path) -> None:
    uuid = transcribed_piece()
    created = client.post(
        f"/audio/{uuid}/edits",
        json={"startSeconds": 1.0, "endSeconds": 4.0, "frameMs": 40},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["startFrame"] == 25
    assert body["endFrame"] == 100


def test_api_preview_and_accept(client: TestClient, temp_store: Path) -> None:
    uuid = transcribed_piece()
    created = client.post(
        f"/audio/{uuid}/edits",
        json={"startFrame": 25, "endFrame": 100, "frameMs": 40, "slowdown": 2},
    )
    session = created.json()["sessionUuid"]
    staging.write_take_events(
        uuid,
        session,
        [_note(72, 0.0, 1.0), _note(74, 2.0, 2.8), _note(76, 4.0, 4.8)],
    )
    record = staging.read(uuid, session)
    record.first_onset_seconds = 0.0
    staging.write(record)

    preview = client.post(
        f"/audio/{uuid}/edits/{session}/preview",
        json={"anchorFigure": "negra", "anchorMs": 480},
    )
    assert preview.status_code == 200, preview.text
    payload = preview.json()
    assert payload["scaledNoteCount"] == 3
    assert payload["confirmation"]["lengthUnchanged"] is True
    assert "score" in payload
    assert payload["score"]["envelope"]["durationSeconds"] == pytest.approx(3.0)

    accepted = client.post(f"/audio/{uuid}/edits/{session}/accept")
    assert accepted.status_code == 200, accepted.text
    body = accepted.json()
    assert body["durationSeconds"] == pytest.approx(6.0)
    assert body["notesRemoved"] == 3  # 1.0, 2.0, 3.0
    after = pipeline.load_note_events(uuid)
    assert after is not None
    assert after.duration_seconds == pytest.approx(6.0)
    onsets = [round(event.start, 4) for event in after.events if event.midi_note >= 72]
    assert onsets[0] == pytest.approx(1.0)
    # 2.0 * 0.5 + 1.0 = 2.0
    assert onsets[1] == pytest.approx(2.0)


def sine_wav(path: Path, seconds: float = 1.0, rate: int = 8000, freq: float = 440.0) -> Path:
    samples = np.sin(2 * np.pi * freq * np.arange(int(rate * seconds)) / rate)
    frames = b"".join(struct.pack("<h", int(value * 30000)) for value in samples)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(frames)
    return path


def test_preview_without_events_asks_to_transcribe(client: TestClient, temp_store: Path) -> None:
    uuid = transcribed_piece()
    created = client.post(
        f"/audio/{uuid}/edits",
        json={"startFrame": 25, "endFrame": 100, "frameMs": 40, "slowdown": 2},
    )
    session = created.json()["sessionUuid"]
    preview = client.post(f"/audio/{uuid}/edits/{session}/preview", json={})
    assert preview.status_code == 409
    assert "Transcribe the take" in preview.json()["detail"]


def test_preview_empty_take_explains_itself(client: TestClient, temp_store: Path) -> None:
    uuid = transcribed_piece()
    created = client.post(
        f"/audio/{uuid}/edits",
        json={"startFrame": 25, "endFrame": 100, "frameMs": 40, "slowdown": 2},
    )
    session = created.json()["sessionUuid"]
    staging.write_take_events(uuid, session, [])
    preview = client.post(f"/audio/{uuid}/edits/{session}/preview", json={})
    assert preview.status_code == 409
    assert "No notes" in preview.json()["detail"]


def test_take_waveform_and_selected_range_before_transcribe(
    temp_store: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    uuid = transcribed_piece()
    record = start(uuid, start_frame=25, end_frame=100, frame_ms=40, slowdown=2)
    sine_wav(staging.untrimmed_path(uuid, record.session_uuid), seconds=2.0)
    record.untrimmed_duration_seconds = 2.0
    staging.write(record)

    peaks = take_peaks(uuid, record.session_uuid, 50)
    assert peaks.duration_seconds == pytest.approx(2.0, abs=0.05)

    patched = patch(
        uuid, record.session_uuid, take_start_seconds=0.5, take_end_seconds=1.5
    )
    assert patched.take_start_seconds == pytest.approx(0.5)
    assert patched.take_end_seconds == pytest.approx(1.5)

    captured: dict[str, float] = {}

    def fake_transcribe(path: Path, **kwargs: object) -> list:
        captured["seconds"] = formats.duration_seconds(path)
        return [_note(60, 0.0, 0.2)]

    monkeypatch.setattr(pipeline, "transcribe_file", fake_transcribe)
    transcribe_take(uuid, record.session_uuid)
    assert captured["seconds"] == pytest.approx(1.0, abs=0.05)
    assert staging.selected_path(uuid, record.session_uuid).is_file()


def test_waveform_without_a_take_is_a_conflict(client: TestClient, temp_store: Path) -> None:
    uuid = transcribed_piece()
    created = client.post(
        f"/audio/{uuid}/edits",
        json={"startFrame": 25, "endFrame": 100, "frameMs": 40},
    )
    session = created.json()["sessionUuid"]
    response = client.get(f"/audio/{uuid}/edits/{session}/waveform")
    assert response.status_code == 409
    assert "take" in response.json()["detail"].lower()


def test_api_take_waveform(client: TestClient, temp_store: Path) -> None:
    uuid = transcribed_piece()
    created = client.post(
        f"/audio/{uuid}/edits",
        json={"startFrame": 25, "endFrame": 100, "frameMs": 40},
    )
    session = created.json()["sessionUuid"]
    sine_wav(staging.untrimmed_path(uuid, session), seconds=1.5)
    record = staging.read(uuid, session)
    record.untrimmed_duration_seconds = 1.5
    staging.write(record)
    response = client.get(f"/audio/{uuid}/edits/{session}/waveform?points=20")
    assert response.status_code == 200, response.text
    assert response.json()["durationSeconds"] == pytest.approx(1.5, abs=0.05)
    assert len(response.json()["min"]) == 20
