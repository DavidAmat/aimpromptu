"""The three `/time` routes, end to end: transcribe, look at the peaks, name one, get the score.

This is the whole product path over HTTP. Nothing here mocks the pipeline: an audio is ingested, the
stub engine transcribes it, and the routes derive everything from the stored `events.json` on each
request, which is what makes the frame length a query parameter rather than a migration.
"""

import shutil
import struct
import wave
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from aitu_backend.audio import ingest
from aitu_backend.main import create_app
from aitu_backend.schemas.metadata import AudioSource
from aitu_backend.storage import paths
from aitu_backend.transcription import pipeline
from aitu_backend.transcription.engine import NoteEvent

FFMPEG = shutil.which("ffmpeg")


@pytest.fixture()
def temp_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(paths, "backend_root", lambda: tmp_path)
    paths.ensure_data_tree()
    return tmp_path / "data"


MIDI_C4 = 60
SHUFFLE_LONG_MS, SHUFFLE_SHORT_MS = 211.0, 125.0


def sine_wav(path: Path, seconds: float = 6.0, rate: int = 44100) -> Path:
    samples = np.sin(2 * np.pi * 440 * np.arange(int(rate * seconds)) / rate)
    frames = b"".join(struct.pack("<h", int(value * 30000)) for value in samples)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(frames)
    return path


class ShuffleEngine:
    """A stub engine that plays a shuffle: long, short, long, short, over a held bass.

    The same shape the real recording has, so the peaks come out where the plot is supposed to show
    them and a ladder named from one of them can be checked.
    """

    name = "shuffle-stub"

    def transcribe(self, wav_path: Path):
        from aitu_backend.transcription.engine import NoteEvent

        events, clock = [], 0.0
        for index in range(20):
            events.append(
                NoteEvent(
                    midi_note=MIDI_C4 + 12 + (index % 4),
                    start=clock / 1000.0,
                    end=(clock + 100.0) / 1000.0,
                )
            )
            clock += SHUFFLE_LONG_MS if index % 2 == 0 else SHUFFLE_SHORT_MS
        events.append(NoteEvent(midi_note=MIDI_C4 - 24, start=0.0, end=1.6))
        events.append(NoteEvent(midi_note=MIDI_C4 - 24, start=1.7, end=3.2))
        return events


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture()
def transcribed(temp_store: Path, tmp_path: Path) -> str:
    """An ingested audio with a stored transcription, which is all the routes need."""
    if not FFMPEG:
        pytest.skip("ffmpeg is not installed")
    source = sine_wav(tmp_path / "shuffle.wav", seconds=6.0)
    with source.open("rb") as handle:
        audio_uuid = ingest.ingest_file(handle, "shuffle.wav", AudioSource.RECORDING).uuid
    events = ShuffleEngine().transcribe(source)
    pipeline.save_note_events(audio_uuid, events, 6.0, title="Shuffle stub")
    return audio_uuid


@pytest.fixture()
def machine_perfect(temp_store: Path, tmp_path: Path) -> str:
    """A piece whose every gap is an exact multiple of the column length, as a MIDI file's would be."""
    if not FFMPEG:
        pytest.skip("ffmpeg is not installed")
    source = sine_wav(tmp_path / "exact.wav", seconds=6.0)
    with source.open("rb") as handle:
        audio_uuid = ingest.ingest_file(handle, "exact.wav", AudioSource.RECORDING).uuid
    events = [
        NoteEvent(midi_note=72 + index % 3, start=index * 0.24, end=index * 0.24 + 0.2)
        for index in range(24)
    ]
    pipeline.save_note_events(audio_uuid, events, 6.0, title="Exact stub")
    return audio_uuid


# --------------------------------------------------------------------------- peaks


def test_the_peaks_route_finds_the_two_halves_of_the_shuffle(client, transcribed):
    response = client.get(f"/time/{transcribed}/peaks", params={"hand": "right"})
    assert response.status_code == 200
    body = response.json()

    assert body["audioUuid"] == transcribed
    assert body["frameMs"] == 40.0
    assert body["gapCount"] == body["attackCount"] - 1
    centres = [peak["centreMs"] for peak in body["peaks"]]
    assert any(abs(centre - SHUFFLE_SHORT_MS) < 10 for centre in centres)
    assert any(abs(centre - SHUFFLE_LONG_MS) < 10 for centre in centres)
    assert sum(peak["share"] for peak in body["peaks"]) == pytest.approx(1.0, abs=0.05)


def test_the_peaks_route_can_be_limited_to_a_stretch_of_the_piece(client, transcribed):
    whole = client.get(f"/time/{transcribed}/peaks").json()
    part = client.get(
        f"/time/{transcribed}/peaks", params={"startSeconds": 0.0, "endSeconds": 1.0}
    ).json()
    assert part["attackCount"] < whole["attackCount"]
    assert part["endSeconds"] == 1.0


def test_each_hand_is_measured_on_its_own(client, transcribed):
    """Gaps between the hands are not a rhythm, so `both` still measures them separately."""
    right = client.get(f"/time/{transcribed}/peaks", params={"hand": "right"}).json()
    left = client.get(f"/time/{transcribed}/peaks", params={"hand": "left"}).json()
    both = client.get(f"/time/{transcribed}/peaks", params={"hand": "both"}).json()
    assert both["gapCount"] == right["gapCount"] + left["gapCount"]
    assert both["attackCount"] == right["attackCount"] + left["attackCount"]


def test_the_frame_length_is_a_query_parameter_and_the_peaks_do_not_move(client, transcribed):
    """The peaks are measured on the raw times, so the grid cannot shift them."""
    coarse = client.get(f"/time/{transcribed}/peaks", params={"frameMs": 40}).json()
    fine = client.get(f"/time/{transcribed}/peaks", params={"frameMs": 20}).json()
    assert [round(p["centreMs"]) for p in coarse["peaks"]] == [
        round(p["centreMs"]) for p in fine["peaks"]
    ]


def test_an_unknown_audio_says_so(client):
    assert client.get("/time/not-a-uuid/peaks").status_code == 404


# --------------------------------------------------------------------------- ladder preview


def test_naming_one_peak_labels_the_others(client, transcribed):
    response = client.post(
        f"/time/{transcribed}/ladder-preview",
        json={"anchorFigure": "negra", "anchorMs": 337.0, "hand": "right"},
    )
    assert response.status_code == 200
    body = response.json()

    assert body["headerLabel"] == "negra = 337 ms · ≈178 BPM"
    assert body["bpm"] == pytest.approx(178.0, abs=0.5)
    assert len(body["ladder"]["msByFigure"]) == 9
    assert body["ladder"]["msByFigure"]["corchea"] == pytest.approx(168.5)

    named = {round(item["peak"]["centreMs"]): item["figure"] for item in body["labelled"]}
    assert all(figure == "corchea" for figure in named.values()), named


def test_the_preview_says_how_badly_each_peak_fits(client, transcribed):
    body = client.post(f"/time/{transcribed}/ladder-preview", json={"anchorMs": 337.0}).json()
    assert all(item["percentOff"] >= 0 for item in body["labelled"])
    assert any(item["percentOff"] > 10 for item in body["labelled"])


# --------------------------------------------------------------------------- the score


def test_the_score_route_returns_something_the_renderer_can_draw(client, transcribed):
    response = client.get(f"/time/{transcribed}/score", params={"anchorMs": 337.0})
    assert response.status_code == 200
    score = response.json()

    assert score["schemaVersion"] == "2.0"
    assert score["envelope"]["frameMs"] == 40.0
    assert score["envelope"]["matrixProcessingStep"] == "two-hands"
    assert score["envelope"]["rMatrix"]["shape"][0] == 88
    assert score["envelope"]["lMatrix"]["shape"][1] == score["envelope"]["frameCount"]
    assert score["passages"][0]["headerLabel"] == "negra = 337 ms · ≈178 BPM"
    assert score["notes"], "a transcribed piece should print some notes"
    assert score["layout"]["frameGroup"] == 25
    # The recording is six seconds; the playing stops well before that, and the sheet stops with it.
    assert score["envelope"]["frameCount"] < 150


def test_every_printed_note_is_complete(client, transcribed):
    notes = client.get(f"/time/{transcribed}/score", params={"anchorMs": 337.0}).json()["notes"]
    for note in notes:
        assert note["hand"] in {"right", "left"}
        assert 0 <= note["row"] < 88
        assert note["printedFrames"] >= 1
        assert note["printedMsExact"] > 0
        assert note["fitError"] >= 0
        assert note["figure"] in {
            "redonda",
            "blanca",
            "dottedBlanca",
            "negra",
            "dottedNegra",
            "corchea",
            "semicorchea",
            "fusa",
            "semifusa",
        }


def test_both_halves_of_the_shuffle_print_as_corcheas(client, transcribed):
    """The point of the whole refactor, over HTTP."""
    notes = client.get(f"/time/{transcribed}/score", params={"anchorMs": 337.0}).json()["notes"]
    melody = [note for note in notes if note["hand"] == "right"]
    assert len(melody) >= 15
    assert {note["figure"] for note in melody[:-1]} == {"corchea"}


def test_a_finer_grid_moves_the_columns_but_not_the_figures(client, transcribed):
    """`frameMs` is a layout parameter: the same music, drawn on a finer grid."""
    coarse = client.get(
        f"/time/{transcribed}/score", params={"anchorMs": 337.0, "frameMs": 40}
    ).json()
    fine = client.get(
        f"/time/{transcribed}/score", params={"anchorMs": 337.0, "frameMs": 20}
    ).json()

    # Twice as many columns, give or take the one the trim lands on.
    assert abs(fine["envelope"]["frameCount"] - 2 * coarse["envelope"]["frameCount"]) <= 1

    # The same notes with the same figures. Only the order in the list can differ, because two
    # notes that shared a column at 40 ms can sit in neighbouring columns at 20 ms.
    def signature(score):
        return sorted((n["hand"], n["row"], n["figure"]) for n in score["notes"])

    assert signature(fine) == signature(coarse)

    melody_coarse = [n for n in coarse["notes"] if n["hand"] == "right"]
    melody_fine = [n for n in fine["notes"] if n["hand"] == "right"]
    assert melody_fine[0]["startFrame"] in (
        2 * melody_coarse[0]["startFrame"],
        2 * melody_coarse[0]["startFrame"] + 1,
    )


def test_passages_can_be_drawn_from_the_query(client, transcribed):
    score = client.get(
        f"/time/{transcribed}/score",
        params={"anchorMs": 337.0, "boundaries": "40", "boundaryMs": "337,674"},
    ).json()
    assert score["passages"][0]["startFrame"] == 0
    assert [(p["startFrame"], p["endFrame"]) for p in score["passages"]][0] == (0, 40)
    assert score["passages"][1]["headerLabel"].startswith("negra = 674 ms")
    assert score["passages"][-1]["endFrame"] == score["envelope"]["frameCount"]


def test_a_passage_list_that_does_not_add_up_is_refused(client, transcribed):
    response = client.get(
        f"/time/{transcribed}/score",
        params={"anchorMs": 337.0, "boundaries": "40", "boundaryMs": "337"},
    )
    assert response.status_code == 422
    assert "boundaryMs" in response.json()["detail"]


def test_a_machine_perfect_piece_gets_its_plot_and_a_warning_rather_than_an_error(
    client, machine_perfect
):
    """D-07's guard catches a mistake, not a piece.

    Gaps that are all exact multiples of the column length are the signature of measuring on
    snapped columns — and also of a MIDI file, which is exact because a machine played it. Refusing
    to draw the plot would answer a real question with a 500.
    """
    response = client.get(f"/time/{machine_perfect}/peaks", params={"hand": "right", "frameMs": 40})

    assert response.status_code == 200
    body = response.json()
    assert body["peaks"], "the piles are still measured"
    assert "exact multiple" in (body["warning"] or "")


def test_an_ordinary_piece_carries_no_warning(client, transcribed):
    body = client.get(f"/time/{transcribed}/peaks", params={"hand": "right"}).json()
    assert body["warning"] is None
