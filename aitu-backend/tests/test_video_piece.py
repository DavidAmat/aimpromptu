"""A video becomes the piece, and the piece is a piece like any other (Story 4.1, 4.2).

Task 4.1.3, Task 4.2.1 and Task 4.3.1. Reading a video produces `events.json` and
nothing else (V-02): everything after that point — the hand split, the matrix, the
peaks, the ladder, the payload — reads the same file the model writes and is never
told where the notes came from. If any of them needed to know, that would be a
defect in this phase and not a feature of theirs, so the test that says so is here.

The video is the one `test_video_stitch.py` draws, so the notes it reads are known
to the pixel.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aitu_backend.audio import store as audio_store
from aitu_backend.editing import history
from aitu_backend.main import create_app
from aitu_backend.schemas.metadata import AudioSource
from aitu_backend.schemas.video import NoteCorrection, NoteCorrections
from aitu_backend.storage import paths
from aitu_backend.transcription import pipeline
from aitu_backend.video import notes as notes_module, piece, store

from video_fixtures import FRAMES, SAMPLE_MS, UUID, Drawn, make_video, white_midi

client = TestClient(create_app())

#: Three notes on three keys, at three different heights, so the piece has
#: something for the hand split and the matrix to chew on.
DRAWN = [
    Drawn(key_index=1, tip_at_frame_zero=-60.0, height=40),
    Drawn(key_index=4, tip_at_frame_zero=-180.0, height=60),
    Drawn(key_index=8, tip_at_frame_zero=-320.0, height=40),
]


@pytest.fixture()
def a_video_piece(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """One ordinary audio piece (V-03) with a drawn video inside it, read."""
    monkeypatch.setattr(paths, "backend_root", lambda: tmp_path)
    audio_store.create(alias="drawn", source=AudioSource.YOUTUBE, extension="mp3", audio_uuid=UUID)
    make_video(tmp_path, monkeypatch, DRAWN)
    notes_module.read_notes(UUID)
    return UUID


# ------------------------------------------------------- writing the piece --


def test_the_stitched_roll_finds_every_rectangle_that_was_drawn(a_video_piece: str) -> None:
    read = store.load_notes(UUID)
    assert read is not None
    assert sorted(note.midi for note in read.notes) == sorted(
        white_midi(one.key_index) for one in DRAWN
    )
    for one in DRAWN:
        note = next(n for n in read.notes if n.midi == white_midi(one.key_index))
        assert note.start == pytest.approx(one.onset_seconds(), abs=0.02)
        assert note.end == pytest.approx(one.release_seconds(), abs=0.02)


def test_it_writes_events_json_through_the_writer_that_already_exists(
    a_video_piece: str,
) -> None:
    written = piece.write(UUID)
    stored = pipeline.load_note_events(UUID)
    assert stored is not None

    assert written.notes == len(stored.events) == len(DRAWN)
    assert stored.title == "Drawn"
    assert stored.duration_seconds == pytest.approx(FRAMES * SAMPLE_MS / 1000.0, abs=0.5)


def test_no_hand_is_written_on_any_event(a_video_piece: str) -> None:
    """V-17. Many of these videos colour the two hands differently and the app
    already has a way to split hands; a hint from a colour is what V-17 refuses.
    The check is on the file, not on the model, because `hand` is left out of the
    JSON entirely unless somebody has said so."""
    piece.write(UUID)
    raw = pipeline.events_path(UUID).read_text()

    stored = pipeline.load_note_events(UUID)
    assert stored is not None
    assert '"hand"' not in raw
    assert all(event.hand is None for event in stored.events)


def test_writing_the_piece_advances_the_music_version(a_video_piece: str) -> None:
    """Reading a video again replaces the piece, so it moves the version exactly
    as any other change to the music does — nothing is invented for a video."""
    assert history.current_version(UUID) == 1
    piece.write(UUID)
    # Nothing was there the first time, so there was nothing to snapshot.
    assert history.current_version(UUID) == 1

    piece.write(UUID)
    assert history.current_version(UUID) == 2
    assert (paths.history_version_dir(UUID, 1) / "events.json").is_file()


def test_a_saved_reading_is_cleared_because_it_points_at_other_notes(
    a_video_piece: str,
) -> None:
    pipeline.rhythm_path(UUID).parent.mkdir(parents=True, exist_ok=True)
    pipeline.rhythm_path(UUID).write_text("{}")
    piece.write(UUID)
    assert not pipeline.rhythm_path(UUID).is_file()


def test_an_unread_video_is_refused_rather_than_written_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(paths, "backend_root", lambda: tmp_path)
    audio_store.create(alias="drawn", source=AudioSource.YOUTUBE, extension="mp3", audio_uuid=UUID)
    make_video(tmp_path, monkeypatch, DRAWN)
    with pytest.raises(piece.NotRead):
        piece.write(UUID)


def test_a_video_whose_speed_is_not_stable_is_not_written_quietly(
    a_video_piece: str,
) -> None:
    """V-06. A row is a distance and a distance is only a time while the speed
    holds, so the last door before the piece changes refuses it in words."""
    measurement = store.load_measurement(UUID)
    assert measurement is not None
    measurement.scroll_speed.stable = False
    measurement.scroll_speed.reason = "the quartiles sit 40% apart"
    store.save_measurement(UUID, measurement)

    with pytest.raises(piece.NotStable) as caught:
        piece.write(UUID)
    assert "40% apart" in str(caught.value)


# ----------------------------------------------- corrections before the write --


def test_a_note_can_be_taken_off_and_a_missed_one_put_on_before_it_is_written(
    a_video_piece: str,
) -> None:
    """Task 4.3.1. The corrections are a person's decision, so they are kept
    beside the video and never rebuilt (V-12)."""
    read = store.load_notes(UUID)
    assert read is not None
    victim = read.notes[0]
    store.save_corrections(
        UUID,
        NoteCorrections(
            removed=[NoteCorrection(midi=victim.midi, start=victim.start)],
            added=[NoteCorrection(midi=60, start=1.0, end=1.4)],
        ),
    )

    written = piece.write(UUID)
    assert written.removed == 1 and written.added == 1 and written.unmatched == 0
    stored = pipeline.load_note_events(UUID)
    assert stored is not None
    assert len(stored.events) == len(DRAWN)
    assert not any(
        event.midi_note == victim.midi and event.start == pytest.approx(victim.start)
        for event in stored.events
    )
    assert any(
        event.midi_note == 60 and event.start == pytest.approx(1.0) for event in stored.events
    )


def test_a_correction_that_names_a_note_the_reading_no_longer_holds_is_reported(
    a_video_piece: str,
) -> None:
    """Reported rather than dropped in silence: a correction made against an
    older reading is a thing the person will want to know about."""
    store.save_corrections(UUID, NoteCorrections(removed=[NoteCorrection(midi=127, start=99.0)]))
    written = piece.write(UUID)
    assert written.removed == 0 and written.unmatched == 1


def test_corrections_survive_the_video_being_read_again(a_video_piece: str) -> None:
    """The frames, the plate, `frames.jsonl` and `notes.json` are all a cache
    (V-01). What a person decided is not."""
    store.save_corrections(UUID, NoteCorrections(added=[NoteCorrection(midi=64, start=2.0)]))
    store.clear_frames(UUID)

    assert store.load_notes(UUID) is None
    assert store.load_corrections(UUID).added[0].midi == 64


# ---------------------------------------------- it is a piece like any other --


def test_the_piece_goes_straight_through_everything_downstream(a_video_piece: str) -> None:
    """Task 4.2.1. The hand split, the matrix, the peaks, the ladder and the
    payload, with no special case anywhere: every one of them is asked over HTTP
    for the uuid a video wrote, and none of them is told that it was a video."""
    piece.write(UUID)

    events = client.get(f"/matrix/{UUID}/events")
    assert events.status_code == 200
    assert len(events.json()["events"]) == len(DRAWN)

    peaks = client.get(f"/time/{UUID}/peaks", params={"frameMs": 40, "hand": "right"})
    assert peaks.status_code == 200

    score = client.get(
        f"/time/{UUID}/score", params={"frameMs": 40, "anchorMs": 250, "anchorFigure": "negra"}
    )
    assert score.status_code == 200
    payload = score.json()
    assert payload["notes"], "the ladder printed something"
    # Every printed note carries a hand, and the split is what decided it — not
    # the colour of a rectangle, which the video never showed anyone (V-17).
    assert {note["hand"] for note in payload["notes"]} <= {"left", "right"}


# ---------------------------------------------------------- over the wire ---


def test_the_http_surface_reads_corrects_and_writes(a_video_piece: str) -> None:
    """The four routes Phase 4 adds, in the order a person uses them."""
    read = client.get(f"/video/{UUID}/notes")
    assert read.status_code == 200
    body = read.json()
    assert len(body["notes"]) == len(DRAWN)
    assert body["report"]["rows"] > 0
    assert body["notes"][0]["startsBefore"] is False

    saved = client.put(
        f"/video/{UUID}/corrections",
        json={"removed": [], "added": [{"midi": 60, "start": 1.0, "end": 1.3}]},
    )
    assert saved.status_code == 200
    assert client.get(f"/video/{UUID}/corrections").json()["added"][0]["midi"] == 60

    written = client.post(f"/video/{UUID}/events")
    assert written.status_code == 200
    assert written.json()["notes"] == len(DRAWN) + 1
    assert written.json()["musicVersion"] == 1

    summary = client.get(f"/video/{UUID}").json()
    assert summary["noteCount"] == len(DRAWN)
    assert summary["hasPiece"] is True


def test_writing_a_video_nobody_has_read_is_a_409_with_the_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(paths, "backend_root", lambda: tmp_path)
    audio_store.create(alias="drawn", source=AudioSource.YOUTUBE, extension="mp3", audio_uuid=UUID)
    make_video(tmp_path, monkeypatch, DRAWN)

    assert client.get(f"/video/{UUID}/notes").status_code == 404
    refused = client.post(f"/video/{UUID}/events")
    assert refused.status_code == 409
    assert "has not been read" in refused.json()["detail"]
