"""Copy and paste of a passage, and From scratch (implementation 02, Phase 8, plan section 12).

A paste is the one write that puts another part's notes, marks and audio into a part and moves
everything after the insertion point by the passage's length. These tests pin the three halves of
it together: the notes and the marks land on the same columns, the audio plays the copied range at
exactly the moment the notes are, and an undo gives the part back to the byte.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from scipy.io import wavfile

from aitu_backend.audio import formats, sources, store, timeline as audio_timeline
from aitu_backend.audio.frames import SAMPLE_RATE
from aitu_backend.main import create_app
from aitu_backend.schemas.metadata import AudioSource
from aitu_backend.schemas.rhythm import (
    Fingering,
    KeyChange,
    Lyric,
    Ottava,
    SavedRhythm,
)
from aitu_backend.storage import bundle, paths
from aitu_backend.storage.bundle import AudioEntry, Timeline
from aitu_backend.transcription import pipeline
from aitu_backend.transcription.engine import NoteEvent

FRAME_MS = 40.0


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app())


def tone(folder: Path, seconds: float, pitch: float, name: str) -> Path:
    samples = 0.3 * np.sin(2 * np.pi * pitch * np.arange(int(SAMPLE_RATE * seconds)) / SAMPLE_RATE)
    path = folder / name
    wavfile.write(path, SAMPLE_RATE, (samples * 32767).astype(np.int16))
    return path


def note(midi: int, start: float, end: float, hand: str = "right") -> NoteEvent:
    return NoteEvent(midi_note=midi, start=start, end=end, hand=hand)


def tone_part(
    folder: Path, title: str, seconds: float, pitch: float, notes: list[NoteEvent]
) -> str:
    """A part whose audio is one tone (so a stretch of it is recognised by its pitch), with notes."""
    part = store.create(title, AudioSource.UPLOAD, "wav").uuid
    source = tone(folder, seconds, pitch, f"{title}.wav")
    store.replace_original(part, source, "wav", keep_cuts=False)
    shutil.copyfile(source, paths.part_cache_dir(part) / "normalized.wav")
    store.update(part, duration_seconds=seconds, sample_rate=SAMPLE_RATE)
    pipeline.save_note_events(part, notes, seconds, title)
    return part


def pitch_at(samples: np.ndarray, rate: int, seconds: float, width: float = 0.1) -> float:
    """The strongest frequency of a short window, in Hz."""
    first = int(seconds * rate)
    window = np.asarray(samples[first : first + int(width * rate)], dtype=np.float64)
    if window.ndim == 2:
        window = window.mean(axis=1)
    spectrum = np.abs(np.fft.rfft(window * np.hanning(len(window))))
    return float(np.fft.rfftfreq(len(window), 1 / rate)[int(np.argmax(spectrum))])


def sheet(**fields) -> SavedRhythm:
    return SavedRhythm.model_validate({"anchorMs": 500.0, "frameMs": FRAME_MS, **fields})


# ------------------------------------------------------------------ the timeline


def one_file(frames: int = 600, cuts: list[tuple[int, int]] | None = None) -> Timeline:
    return Timeline(
        audio_revision=1,
        audio={"x": AudioEntry(format="wav", frames=frames)},
        segments=bundle.segments_for_cuts("x", cuts or [], frames),
    )


def piece(name: str, start: int, end: int, frames: int = 1000) -> audio_timeline.Piece:
    return audio_timeline.Piece(audio=name, format="wav", file_frames=frames, start=start, end=end)


def test_a_passage_put_in_the_middle_of_a_file_splits_it_and_keeps_its_cuts() -> None:
    timeline = one_file(600, [(100, 150)])
    # Piece frame 200 is axis frame 250: the 50 frames cut before it are not in the piece.
    assert audio_timeline.axis_at(timeline, 200) == 250
    done = audio_timeline.insert(timeline, 200, [piece("y", 300, 400)])
    assert done.joined
    assert done.items() == [("x", 0, 250), ("y", 300, 400), ("x", 250, 600)]
    assert done.ranges == [[0, 250], [300, 400], [250, 600]]
    assert bundle.cuts_of(done) == [(100, 150)]
    assert audio_timeline.kept_frames(done) == 550 + 100
    assert done.audio_revision == 2
    # What the piece plays from frame 200 for 100 frames is the passage, and nothing else.
    assert audio_timeline.passage_pieces(done, 200, 300) == [piece("y", 300, 400)]
    assert audio_timeline.passage_pieces(done, 150, 250) == [
        audio_timeline.Piece("x", "wav", 600, 200, 250),
        piece("y", 300, 350),
    ]


def test_a_cut_across_the_insertion_point_is_split_around_the_passage() -> None:
    timeline = one_file(600, [(500, 600)])
    # The end of the piece is the end of its last kept range: a passage put there comes before the
    # frames cut away, which stay cut.
    done = audio_timeline.insert(timeline, 500, [piece("y", 0, 40)])
    assert done.items() == [("x", 0, 500), ("y", 0, 40), ("x", 500, 600)]
    assert bundle.cuts_of(done) == [(540, 640)]


def test_a_stretch_taken_out_becomes_cuts_that_can_be_restored() -> None:
    timeline = audio_timeline.insert(one_file(600), 300, [piece("y", 0, 100)])
    done = audio_timeline.remove(timeline, 250, 350)
    assert bundle.cuts_of(done) == [(250, 350)]
    assert audio_timeline.kept_frames(done) == 600
    assert audio_timeline.passage_pieces(done, 240, 260) == [
        audio_timeline.Piece("x", "wav", 600, 240, 250),
        audio_timeline.Piece("y", "wav", 1000, 50, 60),
    ]


def test_a_moment_past_the_end_of_the_audio_is_reached_with_silence(tmp_path: Path) -> None:
    done = audio_timeline.insert(one_file(100), 150, [piece("y", 0, 20)])
    entries = done.items()
    assert [entry[0] for entry in entries][0] == "x"
    assert entries[1][2] - entries[1][1] == 50  # the silence
    assert entries[2] == ("y", 0, 20)
    assert audio_timeline.kept_frames(done) == 170


def test_reorder_and_remove_keep_the_range_each_file_stands_for() -> None:
    timeline = audio_timeline.insert(one_file(600), 300, [piece("y", 0, 100)])
    assert timeline.axis() == [("x", 300), ("y", 100), ("x", 300)]
    # The segments read back to the same cuts (none), so the Audio step shows the axis unchanged.
    assert bundle.segments_with_cuts(timeline, []) == timeline.segments


# ------------------------------------------------------------------ the paste


@pytest.fixture()
def two_parts(tmp_path: Path) -> tuple[str, str]:
    """A source in Bb major, 8 s at 440 Hz, and a target in C, 6 s at 220 Hz."""
    source = tone_part(
        tmp_path,
        "Source",
        8.0,
        440.0,
        [note(72 + step, step * 1.0, step * 1.0 + 0.5) for step in range(8)],
    )
    pipeline.save_rhythm(
        source,
        sheet(
            keySignature="Bb",
            fingers=[Fingering(hand="right", startFrame=75, row=74 - 21, finger=3)],
            ottavas=[Ottava(kind="8va", hand="right", fromColumn=60, toColumn=90)],
            lyrics=[Lyric(fromColumn=50, toColumn=70, text="words")],
        ),
    )
    target = tone_part(
        tmp_path,
        "Target",
        6.0,
        220.0,
        [note(60 + step, step * 1.0, step * 1.0 + 0.5) for step in range(6)],
    )
    pipeline.save_rhythm(
        target,
        sheet(
            keySignature="C",
            fingers=[Fingering(hand="right", startFrame=100, row=64 - 21, finger=1)],
            keyChanges=[KeyChange(fromColumn=125, keySignature="G")],
        ),
    )
    return source, target


def paste_body(source: str, from_ms: float, to_ms: float, at_ms: float, **more) -> dict:
    return {"source": {"part": source, "fromMs": from_ms, "toMs": to_ms}, "atMs": at_ms, **more}


def test_a_paste_puts_the_notes_the_marks_and_the_audio_in_and_moves_what_follows(
    client: TestClient, two_parts: tuple[str, str]
) -> None:
    source, target = two_parts
    answer = client.post(f"/time/{target}/paste", json=paste_body(source, 2000, 4000, 3000))
    assert answer.status_code == 200, answer.text
    done = answer.json()
    assert done["atMs"] == 3000 and done["lengthMs"] == 2000
    assert done["notesIn"] == 2 and done["notesMoved"] == 3
    assert done["durationSeconds"] == pytest.approx(8.0)

    events = pipeline.load_note_events(target)
    assert events is not None
    starts = [(event.midi_note, round(event.start, 3)) for event in events.events]
    # The target's notes before 3 s stay, its notes from 3 s on are 2 s later, and the passage's
    # two notes (2 s and 3 s of the source) are at 3 s and 4 s.
    assert starts == [
        (60, 0.0),
        (61, 1.0),
        (62, 2.0),
        (74, 3.0),
        (75, 4.0),
        (63, 5.0),
        (64, 6.0),
        (65, 7.0),
    ]
    assert len({event.id for event in events.events}) == 8

    saved = pipeline.load_rhythm(target)
    assert saved is not None
    # The target's fingering at column 100 (4 s) moved by 50 columns; the source's at 75 (3 s) is
    # 25 columns into the passage, so at 75 + 25 = 100.
    assert {(f.start_frame, f.row) for f in saved.fingers} == {(150, 64 - 21), (100, 74 - 21)}
    # The passage reads in Bb, and the target goes back to C after it; its own G at 125 moved.
    assert [(c.from_column, c.key_signature) for c in saved.key_changes] == [
        (75, "Bb"),
        (125, "C"),
        (175, "G"),
    ]
    # The bracket and the words of the source are clipped to the copied stretch.
    assert [(o.from_column, o.to_column) for o in saved.ottavas or []] == [(85, 115)]
    assert [(line.from_column, line.to_column) for line in saved.lyrics] == [(75, 95)]
    # Saved for the notes now on disk: the Sheet step stays ready.
    status = client.get(f"/pieces/{target}/status").json()
    assert {step["step"]: step["state"] for step in status["steps"]}["sheet"] == "ready"
    assert {step["step"]: step["state"] for step in status["steps"]}["notes"] == "ready"

    timeline = bundle.read_timeline(target)
    source_hash = bundle.read_timeline(source).single_audio
    target_hash = timeline.items()[0][0]
    assert target_hash != source_hash
    assert timeline.items() == [
        (target_hash, 0, 300),
        (source_hash, 200, 400),
        (target_hash, 300, 600),
    ]
    project = bundle.read_project(target)
    assert [file.name for file in project.part(target).source.files] == [
        "Target",
        "Source 0:02–0:04",
        "Target",
    ]


def test_the_audio_plays_the_copied_stretch_where_its_notes_are(
    client: TestClient, two_parts: tuple[str, str]
) -> None:
    """Checked at every join, on the engine's audio and on the audio the page plays."""
    source, target = two_parts
    assert client.post(
        f"/time/{target}/paste", json=paste_body(source, 2000, 4000, 3000)
    ).is_success
    entry = store.get(target)
    rate, normalized = formats.read_wav(entry.normalized_path)
    assert len(normalized) == 8 * SAMPLE_RATE
    for seconds, pitch in [(2.85, 220), (3.05, 440), (4.85, 440), (5.05, 220), (7.8, 220)]:
        assert pitch_at(normalized, rate, seconds) == pytest.approx(pitch, abs=12), seconds
    listen = sources.ensure_listen(target, entry.timeline)
    decoded_rate, channels = 44_100, 1
    decoded = sources._decode(listen, decoded_rate, channels)[:, 0]
    assert len(decoded) == 8 * decoded_rate
    for seconds, pitch in [(2.85, 220), (3.05, 440), (4.85, 440), (5.05, 220)]:
        assert pitch_at(decoded, decoded_rate, seconds) == pytest.approx(pitch, abs=12), seconds


def test_undo_gives_the_part_back_exactly_and_redo_pastes_again(
    client: TestClient, two_parts: tuple[str, str]
) -> None:
    source, target = two_parts
    files = ("notes.pmn", "sheet.json", "timeline.json")
    before = {name: (paths.part_dir(target) / name).read_bytes() for name in files}
    done = client.post(f"/time/{target}/paste", json=paste_body(source, 2000, 4000, 3000)).json()
    after = {name: (paths.part_dir(target) / name).read_bytes() for name in files}

    undone = client.post(f"/time/{target}/versions/{done['beforeVersion']}/restore")
    assert undone.status_code == 200, undone.text
    assert {name: (paths.part_dir(target) / name).read_bytes() for name in files} == before
    assert bundle.read_project(target).part(target).source.files == []
    assert undone.json()["sheet"]["keyChanges"] == [{"fromColumn": 125, "keySignature": "G"}]

    redone = client.post(f"/time/{target}/versions/{undone.json()['keptVersion']}/restore")
    assert redone.status_code == 200
    assert {name: (paths.part_dir(target) / name).read_bytes() for name in files} == after
    assert len(bundle.read_project(target).part(target).source.files) == 3
    assert client.post(f"/time/{target}/versions/99/restore").status_code == 404


def test_a_paste_over_a_marked_stretch_replaces_it(
    client: TestClient, two_parts: tuple[str, str]
) -> None:
    source, target = two_parts
    done = client.post(
        f"/time/{target}/paste",
        json=paste_body(source, 2000, 3000, 1000, replaceToMs=3000),
    ).json()
    assert done["notesRemoved"] == 2 and done["notesIn"] == 1
    assert done["durationSeconds"] == pytest.approx(5.0)
    events = pipeline.load_note_events(target)
    assert [(e.midi_note, round(e.start, 3)) for e in events.events] == [
        (60, 0.0),
        (74, 1.0),
        (63, 2.0),
        (64, 3.0),
        (65, 4.0),
    ]
    saved = pipeline.load_rhythm(target)
    # The fingering at 4 s and the key change at 5 s are 2 s - 1 s = 1 s earlier.
    assert {f.start_frame for f in saved.fingers} == {75}
    assert ("G", 100) in {(c.key_signature, c.from_column) for c in saved.key_changes}
    # The two seconds pasted over are cuts of the audio (after the passage, which went in where
    # they start), so the Audio step can restore them.
    timeline = bundle.read_timeline(target)
    assert bundle.cuts_of(timeline) == [(200, 400)]
    assert audio_timeline.kept_frames(timeline) == 500


def test_the_page_sends_its_unsaved_sheet_and_gets_it_back_saved(
    client: TestClient, two_parts: tuple[str, str]
) -> None:
    source, target = two_parts
    unsaved = sheet(keySignature="D", title="My title").model_dump(by_alias=True, mode="json")
    done = client.post(
        f"/time/{target}/paste", json=paste_body(source, 0, 1000, 0, sheet=unsaved)
    ).json()
    assert done["sheet"]["title"] == "My title"
    # Pasted at the start: the passage's Bb is the key of the sheet, and D comes back after it.
    assert done["sheet"]["keySignature"] == "Bb"
    assert done["sheet"]["keyChanges"] == [{"fromColumn": 25, "keySignature": "D"}]
    assert pipeline.load_rhythm(target).title == "My title"


def test_a_copied_stretch_is_whole_columns(client: TestClient, two_parts: tuple[str, str]) -> None:
    source, target = two_parts
    done = client.post(f"/time/{target}/paste", json=paste_body(source, 1990, 2510, 1010)).json()
    assert done["atMs"] == 1000 and done["lengthMs"] == 520


def test_an_empty_stretch_is_refused(client: TestClient, two_parts: tuple[str, str]) -> None:
    source, target = two_parts
    assert (
        client.post(f"/time/{target}/paste", json=paste_body(source, 1000, 1010, 0)).status_code
        == 409
    )


# ------------------------------------------------------------------ From scratch


def test_from_scratch_opens_on_a_blank_sheet_and_a_paste_fills_it(
    client: TestClient, two_parts: tuple[str, str]
) -> None:
    source, _ = two_parts
    made = client.post("/projects", json={"scratch": True})
    assert made.status_code == 201, made.text
    blank = made.json()["parts"][0]
    status = client.get(f"/pieces/{blank}/status").json()
    assert status["scratch"] is True and status["resume"] == "sheet"
    enabled = {step["step"]: step["enabled"] for step in status["steps"]}
    assert enabled["audio"] is False and enabled["sheet"] is True

    done = client.post(f"/time/{blank}/paste", json=paste_body(source, 2000, 4000, 0)).json()
    assert done["notesIn"] == 2 and done["durationSeconds"] == pytest.approx(2.0)
    # The blank sheet takes the source's settings: its key, from the start.
    assert done["sheet"]["keySignature"] == "Bb" and done["sheet"]["keyChanges"] == []
    status = client.get(f"/pieces/{blank}/status").json()
    assert status["scratch"] is False
    states = {step["step"]: step["state"] for step in status["steps"]}
    assert states == {
        "source": "ready",
        "audio": "ready",
        "notes": "ready",
        "sheet": "ready",
    }
    timeline = bundle.read_timeline(blank)
    assert timeline.joined and audio_timeline.kept_frames(timeline) == 200
    # The audio a project of one passage plays is that passage.
    rate, samples = formats.read_wav(store.get(blank).normalized_path)
    assert len(samples) == 2 * SAMPLE_RATE
    assert pitch_at(samples, rate, 1.0) == pytest.approx(440, abs=12)


def test_a_project_without_a_scratch_flag_still_waits_for_its_source(client: TestClient) -> None:
    made = client.post("/projects", json={}).json()
    status = client.get(f"/pieces/{made['parts'][0]}/status").json()
    assert status["scratch"] is False and status["resume"] == "source"


def test_save_to_library_writes_a_pasted_range_as_its_own_file(
    client: TestClient, two_parts: tuple[str, str]
) -> None:
    from aitu_backend.audio import compact

    source, target = two_parts
    client.post(f"/time/{target}/paste", json=paste_body(source, 2000, 4000, 3000))
    plan = compact.prepare(target, bundle.read_project(target))
    assert plan is not None
    try:
        # Three files of their own lengths, with no cut: nothing the user hears moves.
        assert [frames for _, frames in plan.timeline.axis()] == [300, 200, 300]
        assert plan.timeline.ranges is None and bundle.cuts_of(plan.timeline) == []
    finally:
        compact.discard(plan)


def test_a_pasted_project_exports_and_imports_with_its_ranges(
    client: TestClient, two_parts: tuple[str, str]
) -> None:
    source, target = two_parts
    client.post(f"/time/{target}/paste", json=paste_body(source, 2000, 4000, 3000))
    exported = client.get(f"/projects/{target}/export")
    assert exported.status_code == 200
    imported = client.post(
        "/projects/import", files={"file": ("piece.aitu", exported.content, "application/zip")}
    )
    assert imported.status_code == 201, imported.text
    copy = imported.json()["parts"][0]
    assert bundle.read_timeline(copy).items() == bundle.read_timeline(target).items()
