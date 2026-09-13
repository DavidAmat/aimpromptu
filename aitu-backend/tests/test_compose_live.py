"""Composing live: an empty piece, a passage stage, and the three ways to place a passage.

Epic 13 is the one place a length change is allowed, so what these tests pin is the two halves of
that permission. The piece **does** get longer, by exactly the passage — and everything the
insertion pushed later moves by exactly the same number of columns, notes and editorial marks
together, so a fingering is never left pointing at a note that is no longer under it.
"""

import struct
import wave
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from aitu_backend.audio import formats, store
from aitu_backend.editing import compose
from aitu_backend.editing.audio_splice import insert_wav
from aitu_backend.editing.session import accept, patch, start, transcribe_take
from aitu_backend.main import create_app
from aitu_backend.schemas.metadata import AudioSource
from aitu_backend.schemas.rhythm import (
    CueRange,
    Fingering,
    KeyChange,
    Lyric,
    Ottava,
    SavedRhythm,
    SpeedChange,
)
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


def piece_with_notes() -> str:
    """Five notes a second apart in a six-second piece."""
    entry = store.create("Piece", AudioSource.UPLOAD, "wav")
    pipeline.save_note_events(
        entry.uuid,
        [_note(60 + step, float(step), step + 0.4) for step in range(5)],
        duration_seconds=6.0,
        title="Piece",
    )
    return entry.uuid


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


# --------------------------------------------------------------- 13.1.1.1 empty piece


def test_an_empty_piece_is_an_empty_events_json_and_a_frame_ms(temp_store: Path) -> None:
    metadata = compose.create_empty_piece("Nocturne in progress", 40.0)
    assert metadata.source is AudioSource.COMPOSED
    assert metadata.frame_ms == 40.0
    assert metadata.duration_seconds == 0.0
    stored = pipeline.load_note_events(metadata.uuid)
    assert stored is not None
    assert stored.events == []
    assert stored.duration_seconds == 0.0


def test_creating_a_piece_asks_only_for_a_name(client: TestClient, temp_store: Path) -> None:
    created = client.post("/audio/compose", json={"name": "Study", "frameMs": 20})
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["frameMs"] == 20
    assert body["alias"] == "Study"
    listed = client.get("/audio/").json()
    assert [item["uuid"] for item in listed] == [body["uuid"]]
    # It can be drawn: empty staves and no ladder, not an error.
    assert listed[0]["hasNotes"] is True


def test_an_empty_piece_draws_empty_staves(client: TestClient, temp_store: Path) -> None:
    uuid = client.post("/audio/compose", json={"name": "Study"}).json()["uuid"]
    score = client.get(f"/time/{uuid}/score", params={"anchorMs": 500, "frameMs": 40})
    assert score.status_code == 200, score.text
    payload = score.json()
    assert payload["notes"] == []
    assert payload["envelope"]["frameCount"] >= 1


def test_a_piece_needs_a_name(client: TestClient, temp_store: Path) -> None:
    assert client.post("/audio/compose", json={"name": "   "}).status_code == 422


# ------------------------------------------------------------ where a passage lands


def test_the_first_passage_starts_the_piece(temp_store: Path) -> None:
    """No leading silence nobody asked for: a gap is a distance between two passages."""
    assert compose.append_anchor([], 1.0, 40.0) == pytest.approx(0.0)


def test_append_leaves_the_silence_that_was_asked_for(temp_store: Path) -> None:
    events = [_note(60, 0.0, 0.4), _note(62, 1.0, 1.42)]
    assert compose.append_anchor(events, 1.0, 40.0) == pytest.approx(2.44)


def test_the_last_note_does_not_count_notes_taken_off_the_page(temp_store: Path) -> None:
    events = [_note(60, 0.0, 0.4), NoteEvent(midi_note=62, start=5.0, end=5.4, removed=True)]
    assert compose.append_anchor(events, 1.0, 40.0) == pytest.approx(1.4)


def test_a_passage_occupies_a_whole_number_of_columns(temp_store: Path) -> None:
    """The reason an insertion is exact rather than nearly exact — see the compose module note."""
    prepared = [_note(60, 0.0, 0.2), _note(62, 0.5, 0.73)]
    length, arriving = compose.passage_bounds(prepared, at_seconds=1.0, factor=1.0, frame_ms=40.0)
    assert length == pytest.approx(0.76)
    assert round(length * 1000 / 40.0, 6) == 19
    # Nothing the take played is cut: the length rounds up, never down.
    assert max(event.end for event in arriving) <= 1.0 + length + 1e-9
    assert len(arriving) == 2


# --------------------------------------------------------------------- the splice


def test_append_moves_nothing(temp_store: Path) -> None:
    original = [_note(60, 0.0, 0.4), _note(62, 1.0, 1.4)]
    arriving = [_note(72, 2.4, 2.8)]
    result, moved, duration = compose.insert_events(
        original,
        arriving,
        at_seconds=2.4,
        passage_seconds=0.8,
        duration_seconds=3.0,
        placement="append",
    )
    assert moved == 0
    assert [round(event.start, 4) for event in result] == [0.0, 1.0, 2.4]
    assert duration == pytest.approx(3.2)


def test_append_never_shortens_a_piece_with_trailing_silence(temp_store: Path) -> None:
    _, _, duration = compose.insert_events(
        [_note(60, 0.0, 0.4)],
        [_note(72, 1.4, 1.8)],
        at_seconds=1.4,
        passage_seconds=0.4,
        duration_seconds=10.0,
        placement="append",
    )
    assert duration == pytest.approx(10.0)


def test_insert_moves_everything_after_the_moment(temp_store: Path) -> None:
    original = [_note(60, 0.0, 0.4), _note(62, 1.0, 1.4), _note(64, 2.0, 2.4)]
    arriving = [_note(72, 1.0, 1.4)]
    result, moved, duration = compose.insert_events(
        original,
        arriving,
        at_seconds=1.0,
        passage_seconds=0.8,
        duration_seconds=3.0,
        placement="insert",
    )
    assert moved == 2
    assert [round(event.start, 4) for event in result] == [0.0, 1.0, 1.8, 2.8]
    assert duration == pytest.approx(3.8)


def test_a_note_sounding_across_the_moment_is_cut_there(temp_store: Path) -> None:
    """It was not played against the passage now arriving; letting it ring over it invents a sustain."""
    original = [_note(60, 0.5, 2.5)]
    result, moved, _ = compose.insert_events(
        original,
        [_note(72, 1.0, 1.4)],
        at_seconds=1.0,
        passage_seconds=0.8,
        duration_seconds=3.0,
        placement="insert",
    )
    assert moved == 0
    held = next(event for event in result if event.midi_note == 60)
    assert held.start == pytest.approx(0.5)
    assert held.end == pytest.approx(1.0)


def test_a_passage_with_no_notes_cannot_be_placed(temp_store: Path) -> None:
    with pytest.raises(ValueError):
        compose.insert_events(
            [], [], at_seconds=0.0, passage_seconds=0.0, duration_seconds=0.0, placement="append"
        )


# ---------------------------------------------------- 13.1.1.3 the editorial marks


def marked_rhythm() -> SavedRhythm:
    return SavedRhythm(
        anchor_ms=500.0,
        frame_ms=40.0,
        key_changes=[
            KeyChange(from_column=10, key_signature="C"),
            KeyChange(from_column=60, key_signature="G"),
        ],
        speed_changes=[SpeedChange(start_frame=80, anchor_ms=400.0)],
        overrides=[FigureOverride(hand="right", row=40, start_frame=5, figure=FigureName.NEGRA)],
        beam_breaks=[BeamBreak(hand="right", start_frame=70)],
        fingers=[
            Fingering(hand="right", start_frame=5, row=40, finger=1),
            Fingering(hand="right", start_frame=90, row=44, finger=3),
        ],
        lyrics=[Lyric(from_column=0, to_column=100, text="over the join")],
        cue_ranges=[CueRange(from_column=60, to_column=80)],
        ottavas=[Ottava(kind="8va", hand="right", from_column=60, to_column=80)],
    )


def test_marks_after_an_insertion_move_by_the_passage(temp_store: Path) -> None:
    shifted, moved = compose.shift_marks(
        marked_rhythm(), at_seconds=1.0, passage_seconds=0.8, placement="insert"
    )
    assert shifted is not None
    assert moved.frames == 20  # 0.8 s at 40 ms a column
    # Everything from column 25 on: one key change, the speed change, the beam break,
    # one fingering, the cue range, the octave bracket, and the lyric (whose end moves).
    assert moved.total == 7
    assert [item.from_column for item in shifted.key_changes] == [10, 80]
    assert [item.start_frame for item in shifted.speed_changes] == [100]
    assert [item.start_frame for item in shifted.beam_breaks] == [90]
    assert [item.start_frame for item in shifted.fingers] == [5, 110]
    assert [item.start_frame for item in shifted.overrides] == [5]


def test_a_range_across_the_moment_widens_rather_than_tears(temp_store: Path) -> None:
    """It still covers exactly the notes it covered before."""
    shifted, _ = compose.shift_marks(
        marked_rhythm(), at_seconds=1.0, passage_seconds=0.8, placement="insert"
    )
    assert shifted is not None
    lyric = shifted.lyrics[0]
    assert (lyric.from_column, lyric.to_column) == (0, 120)


def test_an_octave_bracket_moves_with_the_notes_it_is_over(temp_store: Path) -> None:
    """A bracket left where it was would sit over notes it was never about.

    It is the last mark to reach `SavedRhythm`, and until 2026-09-13 it did not reach it at all:
    the page sent it and the model had nowhere to put it, so brackets were dropped on save and an
    insertion had nothing to move.
    """
    shifted, _ = compose.shift_marks(
        marked_rhythm(), at_seconds=1.0, passage_seconds=0.8, placement="insert"
    )
    assert shifted is not None
    assert shifted.ottavas is not None
    bracket = shifted.ottavas[0]
    assert (bracket.from_column, bracket.to_column) == (80, 100)


def test_never_asked_about_brackets_stays_never_asked(temp_store: Path) -> None:
    """An insertion moves columns; it does not answer a question the reader was never put."""
    rhythm = SavedRhythm(anchor_ms=500.0, frame_ms=40.0)
    assert rhythm.ottavas is None
    shifted, _ = compose.shift_marks(
        rhythm, at_seconds=1.0, passage_seconds=0.8, placement="insert"
    )
    assert shifted is not None
    assert shifted.ottavas is None


def test_appending_moves_no_marks(temp_store: Path) -> None:
    rhythm = marked_rhythm()
    shifted, moved = compose.shift_marks(
        rhythm, at_seconds=1.0, passage_seconds=0.8, placement="append"
    )
    assert moved.total == 0
    assert shifted == rhythm


def test_a_mark_is_counted_once_however_many_of_its_columns_move(temp_store: Path) -> None:
    rhythm = SavedRhythm(
        anchor_ms=500.0,
        frame_ms=40.0,
        lyrics=[Lyric(from_column=50, to_column=60, text="after")],
    )
    shifted, moved = compose.shift_marks(
        rhythm, at_seconds=1.0, passage_seconds=0.8, placement="insert"
    )
    assert moved.total == 1
    assert shifted is not None
    assert (shifted.lyrics[0].from_column, shifted.lyrics[0].to_column) == (70, 80)


# ------------------------------------------------------------- the session and accept


def staged(uuid: str, take: list[NoteEvent], **kwargs):
    """A session with a take already transcribed into it, skipping the recorder."""
    record = start(uuid, **kwargs)
    staging.write_take_events(uuid, record.session_uuid, take)
    record.first_onset_seconds = min(event.start for event in take)
    staging.write(record)
    return patch(uuid, record.session_uuid, slowdown=record.slowdown or 1)


def test_append_a_passage_to_an_empty_piece(temp_store: Path) -> None:
    uuid = compose.create_empty_piece("Study", 40.0).uuid
    record = staged(
        uuid,
        [_note(60, 0.0, 0.4), _note(62, 0.5, 0.9)],
        placement="append",
        gap_seconds=1.0,
        frame_ms=40.0,
        slowdown=1,
        splice_audio=False,
    )
    assert record.start_seconds == pytest.approx(0.0)
    assert record.window_seconds == pytest.approx(0.92)

    result = accept(uuid, record.session_uuid)
    assert result.placement == "append"
    assert result.notes_arriving == 2
    assert result.notes_moved == 0
    assert result.duration_seconds == pytest.approx(0.92)

    stored = pipeline.load_note_events(uuid)
    assert stored is not None
    assert [round(event.start, 4) for event in stored.events] == [0.0, 0.5]
    assert store.read_metadata(uuid).duration_seconds == pytest.approx(0.92)


def test_a_second_passage_lands_after_the_silence_asked_for(temp_store: Path) -> None:
    uuid = compose.create_empty_piece("Study", 40.0).uuid
    first = staged(
        uuid,
        [_note(60, 0.0, 0.4)],
        placement="append",
        gap_seconds=1.0,
        slowdown=1,
        splice_audio=False,
    )
    accept(uuid, first.session_uuid)

    second = staged(
        uuid,
        [_note(72, 0.0, 0.4)],
        placement="append",
        gap_seconds=1.0,
        slowdown=1,
        splice_audio=False,
    )
    # The first passage ends at 0.4; a one-second silence puts the second at 1.4.
    assert second.start_seconds == pytest.approx(1.4)
    accept(uuid, second.session_uuid)

    stored = pipeline.load_note_events(uuid)
    assert stored is not None
    assert [round(event.start, 4) for event in stored.events] == [0.0, 1.4]


def test_half_speed_puts_the_passage_in_half_the_time_it_took_to_play(temp_store: Path) -> None:
    """Subtask 13.1.1.4: with no window to fit, the factor is the whole answer."""
    uuid = compose.create_empty_piece("Study", 40.0).uuid
    record = staged(
        uuid,
        [_note(60, 0.0, 0.4), _note(62, 2.0, 2.4)],
        placement="append",
        slowdown=2,
        splice_audio=False,
    )
    assert record.factor == pytest.approx(0.5)
    assert record.window_seconds == pytest.approx(1.2)
    accept(uuid, record.session_uuid)
    stored = pipeline.load_note_events(uuid)
    assert stored is not None
    assert [round(event.start, 4) for event in stored.events] == [0.0, 1.0]


def test_insert_moves_the_notes_and_the_marks_in_one_operation(temp_store: Path) -> None:
    uuid = piece_with_notes()
    pipeline.save_rhythm(
        uuid,
        SavedRhythm(
            anchor_ms=500.0,
            frame_ms=40.0,
            fingers=[
                Fingering(hand="right", start_frame=0, row=40, finger=1),
                Fingering(hand="right", start_frame=75, row=44, finger=3),
            ],
        ),
    )
    record = staged(
        uuid,
        [_note(80, 0.0, 0.4)],
        placement="insert",
        start_seconds=2.0,
        frame_ms=40.0,
        slowdown=1,
        splice_audio=False,
    )
    passage = record.window_seconds
    assert passage == pytest.approx(0.4)

    result = accept(uuid, record.session_uuid)
    assert result.placement == "insert"
    assert result.notes_moved == 3  # the notes at 2, 3 and 4 seconds
    assert result.moved_marks.total == 1
    assert result.moved_marks.frames == 10
    assert result.duration_seconds == pytest.approx(6.4)

    stored = pipeline.load_note_events(uuid)
    assert stored is not None
    assert [round(event.start, 4) for event in stored.events] == [0.0, 1.0, 2.0, 2.4, 3.4, 4.4]
    saved = pipeline.load_rhythm(uuid)
    assert saved is not None
    assert [item.start_frame for item in saved.fingers] == [0, 85]


def test_a_mark_lands_on_the_column_its_note_landed_on(temp_store: Path) -> None:
    """The insertion is exact: the fingering and the note it was put on move together."""
    uuid = piece_with_notes()
    pipeline.save_rhythm(
        uuid,
        SavedRhythm(
            anchor_ms=500.0,
            frame_ms=40.0,
            fingers=[Fingering(hand="right", start_frame=100, row=44, finger=3)],
        ),
    )
    record = staged(
        uuid,
        [_note(80, 0.0, 0.33)],
        placement="insert",
        start_seconds=1.0,
        frame_ms=40.0,
        slowdown=1,
        splice_audio=False,
    )
    accept(uuid, record.session_uuid)
    stored = pipeline.load_note_events(uuid)
    saved = pipeline.load_rhythm(uuid)
    assert stored is not None and saved is not None
    # The note that was at 4.0 s, column 100, is the one the fingering was on.
    moved_note = max(event.start for event in stored.events)
    assert round(moved_note * 1000 / 40.0) == saved.fingers[0].start_frame


def test_notes_outside_an_append_are_byte_identical(temp_store: Path) -> None:
    uuid = piece_with_notes()
    before = [
        (event.midi_note, event.start, event.end)
        for event in pipeline.load_note_events(uuid).events
    ]
    record = staged(
        uuid,
        [_note(80, 0.0, 0.4)],
        placement="append",
        gap_seconds=1.0,
        slowdown=1,
        splice_audio=False,
    )
    accept(uuid, record.session_uuid)
    after = pipeline.load_note_events(uuid)
    assert after is not None
    assert [
        (event.midi_note, event.start, event.end) for event in after.events[: len(before)]
    ] == before


def test_composing_has_no_window_to_fit_to(temp_store: Path) -> None:
    uuid = compose.create_empty_piece("Study", 40.0).uuid
    with pytest.raises(Exception, match="no window to fit"):
        start(uuid, placement="append", slowdown=None)


def test_a_moment_past_the_end_is_refused(temp_store: Path) -> None:
    uuid = piece_with_notes()
    with pytest.raises(Exception, match="past the end"):
        start(uuid, placement="insert", start_seconds=99.0)


def test_a_marked_stretch_cannot_be_moved(temp_store: Path) -> None:
    uuid = piece_with_notes()
    record = start(uuid, start_frame=25, end_frame=100, frame_ms=40, slowdown=2)
    with pytest.raises(Exception, match="cannot be moved"):
        patch(uuid, record.session_uuid, gap_seconds=2.0)


def test_moving_a_passage_keeps_the_take(temp_store: Path) -> None:
    uuid = piece_with_notes()
    record = staged(
        uuid,
        [_note(80, 0.0, 0.4)],
        placement="append",
        gap_seconds=1.0,
        slowdown=1,
        splice_audio=False,
    )
    assert record.start_seconds == pytest.approx(5.4)
    moved = patch(uuid, record.session_uuid, gap_seconds=3.0)
    assert moved.start_seconds == pytest.approx(7.4)
    assert moved.window_seconds == pytest.approx(0.4)
    assert staging.has_events(uuid, record.session_uuid)


def test_cancel_leaves_an_empty_piece_empty(client: TestClient, temp_store: Path) -> None:
    uuid = client.post("/audio/compose", json={"name": "Study"}).json()["uuid"]
    created = client.post(
        f"/audio/{uuid}/edits", json={"placement": "append", "gapSeconds": 1.0, "frameMs": 40}
    )
    assert created.status_code == 201, created.text
    session = created.json()["sessionUuid"]
    assert client.delete(f"/audio/{uuid}/edits/{session}").status_code == 200
    stored = pipeline.load_note_events(uuid)
    assert stored is not None and stored.events == []


# ------------------------------------------------------------------- the whole flow


def test_two_passages_one_at_half_speed_read_as_one_piece(
    client: TestClient, temp_store: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The epic's exit criteria, without a browser or a microphone."""
    uuid = client.post("/audio/compose", json={"name": "Duet", "frameMs": 40}).json()["uuid"]

    def play(session: str, take: list[NoteEvent], seconds: float) -> None:
        sine_wav(staging.untrimmed_path(uuid, session), seconds=seconds)
        record = staging.read(uuid, session)
        record.untrimmed_duration_seconds = seconds
        staging.write(record)
        monkeypatch.setattr(pipeline, "transcribe_file", lambda path, **kw: take)
        transcribe_take(uuid, session)

    first = client.post(
        f"/audio/{uuid}/edits",
        json={"placement": "append", "gapSeconds": 1.0, "frameMs": 40, "slowdown": 1},
    ).json()
    play(first["sessionUuid"], [_note(60, 0.0, 0.4), _note(64, 0.5, 0.9)], 1.0)
    accepted = client.post(f"/audio/{uuid}/edits/{first['sessionUuid']}/accept")
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["durationSeconds"] == pytest.approx(0.92)

    # The second passage is played at half speed and takes half the time it took to play.
    second = client.post(
        f"/audio/{uuid}/edits",
        json={"placement": "append", "gapSeconds": 1.0, "frameMs": 40, "slowdown": 2},
    ).json()
    # The first passage's last note released at 0.9 s; a one-second silence lands on column 48.
    assert second["startSeconds"] == pytest.approx(1.92)
    play(second["sessionUuid"], [_note(67, 0.0, 0.8), _note(72, 1.0, 1.8)], 2.0)
    confirmation = client.get(f"/audio/{uuid}/edits/{second['sessionUuid']}/confirmation").json()
    assert confirmation["placement"] == "append"
    assert confirmation["lengthUnchanged"] is False
    assert confirmation["notesArriving"] == 2
    result = client.post(f"/audio/{uuid}/edits/{second['sessionUuid']}/accept").json()
    assert result["durationSeconds"] == pytest.approx(2.84)

    # And it reads as one sheet.
    score = client.get(f"/time/{uuid}/score", params={"anchorMs": 500, "frameMs": 40})
    assert score.status_code == 200, score.text
    assert len(score.json()["notes"]) == 4

    events = pipeline.load_note_events(uuid)
    assert events is not None
    assert [round(event.start, 4) for event in events.events] == [0.0, 0.5, 1.92, 2.42]


def test_the_recording_grows_with_the_piece(
    temp_store: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A composed piece has no audio until its first passage creates one."""
    uuid = compose.create_empty_piece("Study", 40.0).uuid
    record = start(uuid, placement="append", gap_seconds=1.0, frame_ms=40.0, slowdown=1)
    session = record.session_uuid
    sine_wav(staging.untrimmed_path(uuid, session), seconds=1.0)
    record.untrimmed_duration_seconds = 1.0
    staging.write(record)
    monkeypatch.setattr(pipeline, "transcribe_file", lambda path, **kw: [_note(60, 0.0, 0.9)])
    transcribe_take(uuid, session)

    result = accept(uuid, session)
    assert result.audio_spliced is True
    entry = store.get(uuid)
    assert entry.has_normalized()
    assert formats.duration_seconds(entry.normalized_path) == pytest.approx(
        result.duration_seconds, abs=0.05
    )


def test_insert_wav_opens_the_recording_rather_than_overwriting_it(tmp_path: Path) -> None:
    source = sine_wav(tmp_path / "source.wav", seconds=2.0, rate=16000)
    patch_wav = sine_wav(tmp_path / "patch.wav", seconds=0.5, rate=16000, freq=880.0)
    grown = insert_wav(source, patch_wav, tmp_path / "out.wav", 1.0, 0.5, keep_tail=True)
    assert formats.duration_seconds(grown) == pytest.approx(2.5, abs=0.01)


def test_insert_wav_pads_silence_up_to_an_append(tmp_path: Path) -> None:
    missing = tmp_path / "nothing.wav"
    patch_wav = sine_wav(tmp_path / "patch.wav", seconds=0.5, rate=16000)
    grown = insert_wav(missing, patch_wav, tmp_path / "out.wav", 1.0, 0.5, keep_tail=False)
    assert formats.duration_seconds(grown) == pytest.approx(1.5, abs=0.01)


def test_a_sustain_that_outruns_the_recording_does_not_stretch_the_passage(
    temp_store: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pedalled chord is heard ringing long after the recording stops.

    With a window that never matters, because the window decides the length. While composing the
    take decides it, so a four-second take that comes back with a note "ending" ten seconds in must
    still be a four-second passage. Found on a real engine run, not in theory.
    """
    uuid = compose.create_empty_piece("Study", 40.0).uuid
    record = start(uuid, placement="append", gap_seconds=1.0, frame_ms=40.0, slowdown=1)
    session = record.session_uuid
    sine_wav(staging.untrimmed_path(uuid, session), seconds=4.0)
    record.untrimmed_duration_seconds = 4.0
    staging.write(record)
    blurred = [_note(60, 0.1, 0.5), _note(65, 3.0, 9.8)]
    monkeypatch.setattr(pipeline, "transcribe_file", lambda path, **kw: blurred)
    refreshed = transcribe_take(uuid, session)

    # 4.0 s of recording less the 0.1 s before the first onset, rounded up to a whole column.
    assert refreshed.window_seconds == pytest.approx(3.92)
    result = accept(uuid, session)
    assert result.duration_seconds == pytest.approx(3.92)
    stored = pipeline.load_note_events(uuid)
    assert stored is not None
    assert max(event.end for event in stored.events) <= 3.92 + 1e-9


def test_a_note_that_rounds_into_the_insertion_column_moves_with_it(temp_store: Path) -> None:
    """Notes and marks are both decided by the column, so neither is left behind by the other.

    A note at 1.99 s is drawn in column 50 at 40 ms a column, and so is the moment 2.0 s. Under an
    onset test in seconds that note would stay put and end up inside the passage the reader just
    opened, with its fingering gone on ahead without it.
    """
    original = [_note(60, 1.99, 2.1), _note(62, 1.9, 2.0)]
    result, moved, _ = compose.insert_events(
        original,
        [_note(80, 2.0, 2.4)],
        at_seconds=2.0,
        passage_seconds=0.8,
        duration_seconds=4.0,
        placement="insert",
        frame_ms=40.0,
    )
    assert moved == 1
    stayed = next(event for event in result if event.midi_note == 62)
    assert stayed.start == pytest.approx(1.9)
    went = next(event for event in result if event.midi_note == 60)
    assert went.start == pytest.approx(2.79)
    # 1.99 s was column 50; 2.79 s is column 70, which is 50 plus the 20-column passage.
    assert round(went.start * 1000 / 40.0) == 50 + 20
