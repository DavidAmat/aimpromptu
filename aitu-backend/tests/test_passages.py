"""Recording in Sheet (implementation 02, Phase 9, plan section 13).

A passage is a copy of the marked frames of a part (the Current) and the takes recorded for it; a
take is read into a Proposal (transcription, hands, a first sheet in the passage's key and figure);
**Promote** writes it into the part in one write. These tests pin what each step writes, the three
promotions (the window with the original audio, the window with the recording at another speed,
the whole take that changes the length), and that the sheet's undo gives the part back to the byte.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aitu_backend.audio import formats, piece_audio, store, timeline as audio_timeline
from aitu_backend.db import users
from aitu_backend.editing import passages
from aitu_backend.main import create_app
from aitu_backend.schemas.rhythm import Fingering
from aitu_backend.schemas.time_matrix import FigureName
from aitu_backend.storage import bundle, locate, paths
from aitu_backend.transcription import pipeline
from aitu_backend.transcription.engine import NoteEvent

from test_paste import note, pitch_at, sheet, tone, tone_part

needs_ffmpeg = pytest.mark.skipif(not formats.ffmpeg_available(), reason="needs ffmpeg")


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app())


class Stub:
    """An engine that hears what the test says it hears."""

    name = "stub"

    def __init__(self, notes: list[NoteEvent]) -> None:
        self.notes = notes

    def transcribe(self, wav_path: Path) -> list[NoteEvent]:
        return [event.model_copy() for event in self.notes]


def heard(monkeypatch: pytest.MonkeyPatch, notes: list[NoteEvent]) -> None:
    monkeypatch.setattr(pipeline, "shared_engine", lambda name, reporter=None: Stub(notes))


def song(tmp_path: Path) -> str:
    """Ten seconds at 220 Hz, a note every second, a saved sheet in Bb with a fingering inside the
    passage (2 to 4 s, columns 50 to 100) and one at 7 s."""
    notes = [note(60 + index, index + 0.0, index + 0.5) for index in range(10)]
    part = tone_part(tmp_path, "Song", 10.0, 220.0, notes)
    stored = pipeline.load_note_events(part)
    assert stored is not None
    pipeline.save_rhythm(
        part,
        sheet(
            keySignature="Bb",
            handsRevision=stored.header.hands_revision,
            fingers=[
                Fingering(start_frame=75, row=39, finger=2, hand="right"),
                Fingering(start_frame=175, row=46, finger=3, hand="right"),
            ],
        ),
    )
    return part


def recording(folder: Path, seconds: float, pitch: float) -> bytes:
    path = tone(folder, seconds, pitch, f"take-{pitch:g}.wav")
    return path.read_bytes()


def open_and_record(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    part: str,
    take_notes: list[NoteEvent],
    *,
    seconds: float = 4.0,
    span: tuple[float, float] = (2000, 4000),
) -> tuple[str, str]:
    """A passage of ``part`` and one take read into a Proposal."""
    opened = client.post("/passages", json={"part": part, "fromMs": span[0], "toMs": span[1]})
    assert opened.status_code == 201, opened.text
    passage = opened.json()["id"]
    sent = client.post(
        f"/passages/{passage}/takes",
        files={"file": ("take.wav", io.BytesIO(recording(tmp_path, seconds, 440.0)), "audio/wav")},
    )
    assert sent.status_code == 201, sent.text
    take = sent.json()["take"]
    heard(monkeypatch, take_notes)
    passages.read_take(passage, take, 0.0, seconds)
    return passage, take


def piece_samples(part: str) -> tuple[int, object]:
    """The audio of the piece as the engine hears it: the kept frames joined, 16 kHz."""
    made = piece_audio.ensure(part)
    return formats.read_wav(made.normalized if made else store.get(part).normalized_path)


def snapshot(part: str) -> dict[str, bytes]:
    return {
        path.name: path.read_bytes()
        for path in (
            pipeline.events_path(part),
            pipeline.rhythm_path(part),
            paths.part_timeline_path(part),
        )
    }


# ------------------------------------------------------------------ the passage


def test_a_passage_is_a_copy_of_the_marked_frames_hidden_from_every_list(
    client: TestClient, tmp_path: Path
) -> None:
    part = song(tmp_path)
    answer = client.post("/passages", json={"part": part, "fromMs": 2010, "toMs": 3990})
    assert answer.status_code == 201, answer.text
    body = answer.json()
    # Snapped to whole columns of the song's sheet.
    assert (body["fromMs"], body["toMs"]) == (2000, 4000)
    assert body["anchorMs"] == 500.0 and body["anchorFigure"] == "negra"
    assert body["takes"] == [] and body["take"] is None
    current = body["current"]
    copied = pipeline.load_note_events(current)
    assert copied is not None
    assert [(event.midi_note, event.start) for event in copied.events] == [(62, 0.0), (63, 1.0)]
    # Its marks and its key came with it; its audio is ranges of the song's stored file.
    current_sheet = pipeline.load_rhythm(current)
    assert current_sheet is not None and current_sheet.key_signature == "Bb"
    assert [finger.start_frame for finger in current_sheet.fingers] == [25]
    timeline = bundle.read_timeline(current)
    assert set(timeline.audio) == set(bundle.read_timeline(part).audio)
    # Not on the Projects page, not in the list of audio.
    assert body["id"] not in [row["id"] for row in client.get("/projects").json()]
    assert current not in [row["uuid"] for row in client.get("/audio/").json()]
    assert client.get(f"/passages/{body['id']}").json()["part"] == part


def test_the_same_stretch_of_an_unchanged_song_opens_the_passage_again(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    part = song(tmp_path)
    passage, take = open_and_record(client, monkeypatch, tmp_path, part, [note(70, 0.1, 0.6)])
    again = client.post("/passages", json={"part": part, "fromMs": 2000, "toMs": 4000}).json()
    assert again["id"] == passage and [one["id"] for one in again["takes"]] == [take]
    # Another stretch is another passage; a changed song opens a new one.
    other = client.post("/passages", json={"part": part, "fromMs": 0, "toMs": 1000}).json()
    assert other["id"] != passage
    stored = pipeline.load_rhythm(part)
    assert stored is not None
    pipeline.save_rhythm(part, stored.model_copy(update={"key_signature": "F"}))
    changed = client.post("/passages", json={"part": part, "fromMs": 2000, "toMs": 4000}).json()
    assert changed["id"] != passage and changed["takes"] == []


def test_deleting_the_song_deletes_its_passages_and_their_takes(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    part = song(tmp_path)
    passage, take = open_and_record(client, monkeypatch, tmp_path, part, [note(70, 0.1, 0.6)])
    assert client.delete(f"/audio/{part}").status_code in (200, 204)
    for gone in (passage, take):
        with pytest.raises(locate.NotFound):
            locate.project(gone)


def test_discarding_a_passage_leaves_the_song_as_it_was(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    part = song(tmp_path)
    before = snapshot(part)
    passage, take = open_and_record(client, monkeypatch, tmp_path, part, [note(70, 0.1, 0.6)])
    assert client.delete(f"/passages/{passage}").status_code == 204
    assert snapshot(part) == before
    with pytest.raises(locate.NotFound):
        locate.project(take)


# ------------------------------------------------------------------ the takes


@needs_ffmpeg
def test_a_take_is_read_with_the_passages_key_and_figure(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    part = song(tmp_path)
    passage, take = open_and_record(
        client,
        monkeypatch,
        tmp_path,
        part,
        [note(70, 0.2, 0.7), note(72, 1.2, 1.7)],
        seconds=4.0,
    )
    # Twice as slow as the song: a negra of the take lasts twice as long.
    assert client.patch(f"/passages/{passage}", json={"speed": 2.0}).status_code == 200
    passages.read_take(passage, take, 0.5, 3.5)
    body = client.get(f"/passages/{passage}").json()
    (described,) = body["takes"]
    assert described["state"] == "ready" and described["name"] == "Take 1"
    assert (described["fromSeconds"], described["toSeconds"]) == (0.5, 3.5)
    assert body["takeMs"] == 3000
    written = pipeline.load_rhythm(take)
    assert written is not None
    assert written.key_signature == "Bb" and written.anchor_figure.value == "negra"
    assert written.anchor_ms == 1000.0
    assert written.fingers == [] and written.ottavas is None
    # Hands for every note, so the sheet of the take is ready, not stale.
    status = client.get(f"/pieces/{take}/status").json()
    assert {step["step"]: step["state"] for step in status["steps"]}["sheet"] == "ready"
    stored = pipeline.load_note_events(take)
    assert stored is not None and all(event.hand for event in stored.events)


# ------------------------------------------------------------------ the promotions


def test_the_window_with_the_original_audio_changes_only_the_notes(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    part = song(tmp_path)
    timeline_before = paths.part_timeline_path(part).read_bytes()
    before = snapshot(part)
    passage, _ = open_and_record(
        client,
        monkeypatch,
        tmp_path,
        part,
        # The take starts with a second of silence; the window is put after it.
        [note(70, 1.0, 1.4), note(71, 1.5, 1.9), note(72, 2.5, 2.9), note(73, 3.2, 3.6)],
    )
    client.patch(f"/passages/{passage}", json={"windowMs": 1000})
    request = {"mode": "window", "audio": "original"}
    facts = client.post(f"/passages/{passage}/promotion", json=request).json()
    assert facts["notesOut"] == 2 and facts["notesIn"] == 3
    assert facts["lengthChangeMs"] == 0
    assert facts["marksDropped"] == {"fingers": 1}
    done = client.post(f"/passages/{passage}/promote", json=request)
    assert done.status_code == 200, done.text
    result = done.json()
    assert result["part"] == part and result["atMs"] == 2000 and result["lengthMs"] == 2000
    # The audio is the song's own, to the byte; the notes of the window are in its place.
    assert paths.part_timeline_path(part).read_bytes() == timeline_before
    stored = pipeline.load_note_events(part)
    assert stored is not None and stored.duration_seconds == 10.0
    inside = [(e.midi_note, round(e.start, 3)) for e in stored.events if 2.0 <= e.start < 4.0]
    assert inside == [(70, 2.0), (71, 2.5), (72, 3.5)]
    assert not pipeline.notes_are_stale(part, stored)
    # The fingering after the passage stays on its column; the one inside it went.
    saved = pipeline.load_rhythm(part)
    assert saved is not None and [f.start_frame for f in saved.fingers] == [175]
    # The passage is closed, and the sheet's undo gives the part back to the byte.
    with pytest.raises(locate.NotFound):
        locate.project(passage)
    back = client.post(f"/time/{part}/versions/{result['beforeVersion']}/restore")
    assert back.status_code == 200
    assert snapshot(part) == before


@needs_ffmpeg
def test_the_window_with_the_recording_plays_the_take_faster_at_its_place(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    part = song(tmp_path)
    # Played twice as slowly: four seconds for the passage's two.
    passage, _ = open_and_record(
        client, monkeypatch, tmp_path, part, [note(70, 0.0, 0.9), note(72, 2.0, 2.9)]
    )
    client.patch(f"/passages/{passage}", json={"speed": 2.0, "windowMs": 0})
    done = client.post(
        f"/passages/{passage}/promote", json={"mode": "window", "audio": "recording"}
    )
    assert done.status_code == 200, done.text
    stored = pipeline.load_note_events(part)
    assert stored is not None and stored.duration_seconds == 10.0
    inside = [(e.midi_note, round(e.start, 3)) for e in stored.events if 2.0 <= e.start < 4.0]
    assert inside == [(70, 2.0), (72, 3.0)]
    after = [(e.midi_note, e.start) for e in stored.events if e.start >= 4.0]
    assert after == [(60 + index, float(index)) for index in range(4, 10)]
    # The audio: the song, the take (440 Hz) at the passage, the song again, the same length.
    rate, samples = piece_samples(part)
    assert len(samples) == pytest.approx(10.0 * rate, abs=rate * 0.02)
    assert pitch_at(samples, rate, 1.0) == pytest.approx(220, abs=15)
    assert pitch_at(samples, rate, 3.0) == pytest.approx(440, abs=15)
    assert pitch_at(samples, rate, 5.0) == pytest.approx(220, abs=15)
    assert not pipeline.notes_are_stale(part, stored)


@needs_ffmpeg
def test_the_whole_take_changes_the_length_and_moves_what_follows(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    part = song(tmp_path)
    before = snapshot(part)
    passage, _ = open_and_record(
        client,
        monkeypatch,
        tmp_path,
        part,
        [note(70, 0.0, 0.5), note(71, 1.0, 1.5), note(72, 2.0, 2.5)],
        seconds=3.0,
    )
    request = {"mode": "whole", "audio": "recording"}
    facts = client.post(f"/passages/{passage}/promotion", json=request).json()
    assert facts["lengthChangeMs"] == 1000 and facts["durationSeconds"] == 11.0
    assert (
        client.post(
            f"/passages/{passage}/promotion", json={"mode": "whole", "audio": "original"}
        ).status_code
        == 409
    )
    done = client.post(f"/passages/{passage}/promote", json=request)
    assert done.status_code == 200, done.text
    stored = pipeline.load_note_events(part)
    assert stored is not None and stored.duration_seconds == 11.0
    starts = [(event.midi_note, round(event.start, 3)) for event in stored.events]
    assert starts[:2] == [(60, 0.0), (61, 1.0)]
    assert starts[2:5] == [(70, 2.0), (71, 3.0), (72, 4.0)]
    assert starts[5:] == [(60 + index, index + 1.0) for index in range(4, 10)]
    # The mark after the passage moved with its note, by 25 columns of 40 ms.
    saved = pipeline.load_rhythm(part)
    assert saved is not None and [f.start_frame for f in saved.fingers] == [200]
    # The audio is as long as the notes, and the take sounds at the passage.
    timeline = bundle.read_timeline(part)
    assert audio_timeline.kept_frames(timeline) == 1100
    rate, samples = piece_samples(part)
    assert pitch_at(samples, rate, 3.5) == pytest.approx(440, abs=15)
    assert pitch_at(samples, rate, 6.0) == pytest.approx(220, abs=15)
    back = client.post(f"/time/{part}/versions/{done.json()['beforeVersion']}/restore")
    assert back.status_code == 200 and snapshot(part) == before


def test_a_proposal_named_with_other_figures_keeps_them_in_the_song(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The reader called the take's figures one step shorter (Transpose → Figures on the
    Proposal): what a negra lasts there doubles, which the song keeps as a speed change."""
    part = song(tmp_path)
    passage, take = open_and_record(
        client, monkeypatch, tmp_path, part, [note(70, 0.0, 0.4), note(71, 1.0, 1.4)]
    )
    proposal = pipeline.load_rhythm(take)
    assert proposal is not None
    edited = proposal.model_copy(update={"anchor_figure": FigureName.CORCHEA})
    done = client.post(
        f"/passages/{passage}/promote",
        json={
            "mode": "window",
            "audio": "original",
            "sheet": edited.model_dump(by_alias=True, mode="json"),
        },
    )
    assert done.status_code == 200, done.text
    saved = pipeline.load_rhythm(part)
    assert saved is not None
    changes = [(change.start_frame, change.anchor_ms) for change in saved.speed_changes]
    assert changes == [(50, 1000.0), (100, 500.0)]


# ------------------------------------------------------------------ a new passage


@needs_ffmpeg
def test_a_new_passage_on_a_blank_sheet_brings_the_first_audio(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    blank = client.post("/projects", json={"scratch": True}).json()["id"]
    passage, _ = open_and_record(
        client,
        monkeypatch,
        tmp_path,
        blank,
        [note(64, 0.0, 0.5), note(67, 1.0, 1.5)],
        seconds=2.0,
        span=(0, 0),
    )
    body = client.get(f"/passages/{passage}").json()
    assert body["anchorMs"] is None and body["fromMs"] == body["toMs"] == 0
    assert (
        client.post(
            f"/passages/{passage}/promotion", json={"mode": "window", "audio": "original"}
        ).status_code
        == 409
    )
    done = client.post(f"/passages/{passage}/promote", json={"mode": "whole"})
    assert done.status_code == 200, done.text
    stored = pipeline.load_note_events(blank)
    assert stored is not None and [e.midi_note for e in stored.events] == [64, 67]
    assert stored.duration_seconds == 2.0
    status = client.get(f"/pieces/{blank}/status").json()
    assert status["scratch"] is False


# ------------------------------------------------------------------ rights


def test_a_version_of_the_library_cannot_be_re_recorded(client: TestClient) -> None:
    made = bundle.create_project(owner_id=users.ensure_master_user(), title="Kept", layer="private")
    pipeline.save_note_events(made.id, [note(60, 0.0, 0.5)], 2.0, "Kept")
    answer = client.post("/passages", json={"part": made.id, "fromMs": 0, "toMs": 1000})
    assert answer.status_code == 403


def test_a_project_of_the_kind_passage_is_in_no_list() -> None:
    owner = users.ensure_master_user()
    bundle.create_project(owner_id=owner, title="Hidden", kind=bundle.PASSAGE_KIND)
    assert bundle.list_parts(owner) == []
    assert store.list_all() == []


def test_a_take_of_another_passage_is_not_found(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    part = song(tmp_path)
    first, take = open_and_record(client, monkeypatch, tmp_path, part, [note(70, 0.1, 0.6)])
    second = client.post("/passages", json={"part": part, "fromMs": 0, "toMs": 1000}).json()["id"]
    answer = client.post(
        f"/passages/{second}/takes/{take}/read", json={"fromSeconds": 0, "toSeconds": 1}
    )
    assert answer.status_code == 404
    assert client.patch(f"/passages/{second}", json={"take": take}).status_code == 404
    assert client.patch(f"/passages/{first}", json={"speed": 8}).status_code == 409
