"""The piano matrix notation module (implementation 08, Phase 2): the sparse form and its adapters.

Every adapter has a round trip here. The dense matrix is checked at 10 ms, where a MuScriptor note
is exactly whole columns, and at 40 ms, where the times snap. ``events.json`` is also checked on
every piece of the local library when ``data/audio`` is present: reading and writing through the
sparse form must give back exactly what the file holds.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from aitu_backend.audio import store
from aitu_backend.matrix.time_grid import frame_of_ms
from aitu_backend.pmn import HAND_LEFT, HAND_NONE, HAND_RIGHT, Notes
from aitu_backend.pmn import (
    columns,
    coo,
    dense,
    events_file,
    midi,
    muscriptor,
    portable,
)
from aitu_backend.schemas.matrix import ONSET, SUSTAIN, SparseCooMatrix
from aitu_backend.schemas.metadata import AudioSource
from aitu_backend.storage import paths
from aitu_backend.transcription import pipeline
from aitu_backend.transcription.engine import NoteEvent

FIXTURES = Path(__file__).parent / "fixtures" / "pmn"
EVENTS_20S = FIXTURES / "superestrella-20s-large-cuda.events.jsonl"
NOTES_20S = FIXTURES / "superestrella-20s-large-cuda.notes.json"
LIBRARY = Path(__file__).resolve().parents[1] / "data" / "audio"


def superestrella_20s() -> Notes:
    """The first 20 seconds of Superestrella as MuScriptor large streamed them (Phase 1)."""
    events = [json.loads(line) for line in EVENTS_20S.read_text().splitlines()]
    return muscriptor.from_muscriptor_events(events, end_ms=20_000)


def random_notes(count: int = 300, seed: int = 7) -> Notes:
    """Notes on whole milliseconds, some of them sharing a key, with every hand."""
    rng = np.random.default_rng(seed)
    return Notes.build(
        key=rng.integers(0, 88, count),
        on_ms=rng.integers(0, 60_000, count),
        len_ms=rng.integers(1, 3_000, count),
        hand=rng.integers(0, 3, count),
        velocity=rng.integers(1, 128, count),
    ).sorted()


def one_note_per_key(notes: Notes) -> Notes:
    """The same notes cut so that one key never sounds twice at once (the rule of the prompt)."""
    order = np.lexsort((notes.on_ms, notes.key))
    key, on, end = notes.key[order], notes.on_ms[order], notes.end_ms[order]
    following = np.full(key.size, np.inf)
    same = key[1:] == key[:-1]
    following[:-1][same] = on[1:][same]
    keep = (
        following > on
    )  # two onsets of one key at one instant: keep the later one only
    cut = np.minimum(end, following)
    return Notes(
        id=notes.id[order][keep],
        key=key[keep],
        on_ms=on[keep],
        len_ms=(cut - on)[keep],
        hand=notes.hand[order][keep],
        velocity=notes.velocity[order][keep],
    ).sorted()


@pytest.fixture()
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(paths, "backend_root", lambda: tmp_path)
    paths.ensure_database_tree()
    return tmp_path


# ------------------------------------------------------------------ the sparse form


def test_the_sparse_form_refuses_what_is_not_a_set_of_notes() -> None:
    with pytest.raises(ValueError, match="key"):
        Notes.build(key=[88], on_ms=[0], len_ms=[10])
    with pytest.raises(ValueError, match="lenMs"):
        Notes.build(key=[40], on_ms=[0], len_ms=[0])
    with pytest.raises(ValueError, match="negative"):
        Notes.build(key=[40], on_ms=[-10], len_ms=[10])
    with pytest.raises(ValueError, match="unique"):
        Notes(id=[3, 3], key=[40, 41], on_ms=[0, 0], len_ms=[10, 10])
    with pytest.raises(ValueError, match="parallel"):
        Notes(id=[0, 1], key=[40], on_ms=[0, 0], len_ms=[10, 10])


def test_removed_notes_stay_in_the_form_and_leave_every_view() -> None:
    notes = Notes.build(
        key=[40, 41], on_ms=[0, 100], len_ms=[50, 50], removed=[False, True]
    )
    assert len(notes) == 2 and len(notes.live()) == 1
    assert columns.to_columns(notes)["id"] == [0]
    grid = dense.to_dense(notes, 10)
    assert grid[41].sum() == 0


# ------------------------------------------------------------------------ events.json


OLD_FILE: dict[str, Any] = {
    "schemaVersion": "1.0",
    "durationSeconds": 3.5,
    "title": "Old piece",
    "events": [
        {"midiNote": 60, "start": 0.2501, "end": 0.7502, "velocity": 71},
        {
            "midiNote": 64,
            "start": 0.2503,
            "end": 0.9004,
            "velocity": 64,
            "hand": "left",
        },
        {"midiNote": 67, "start": 1.0, "end": 1.5, "velocity": 64, "removed": True},
    ],
}


def test_an_old_file_reads_with_ids_in_file_order_and_the_default_header() -> None:
    piece = events_file.piece_from_payload(OLD_FILE)

    assert piece.notes.id.tolist() == [0, 1, 2]
    assert piece.header == events_file.PieceHeader(next_id=3)
    assert piece.header.notes_revision == 1 and piece.header.hands_revision == 0
    assert piece.notes.hand.tolist() == [HAND_NONE, HAND_LEFT, HAND_NONE]
    assert piece.notes.removed.tolist() == [False, False, True]
    assert piece.duration_ms == 3500.0


def test_the_events_json_round_trip_is_exact_including_sub_millisecond_times() -> None:
    piece = events_file.piece_from_payload(OLD_FILE)
    written = events_file.piece_to_payload(piece)

    assert written["schemaVersion"] == events_file.EVENTS_SCHEMA_VERSION
    assert written["nextId"] == 3
    for before, after in zip(OLD_FILE["events"], written["events"]):
        assert {key: after[key] for key in before} == before
    again = events_file.piece_from_payload(written)
    assert again.notes.equals(piece.notes) and again.header == piece.header


def test_a_guessed_hand_and_the_hands_notes_revision_survive_a_save() -> None:
    """Phase 5: ``handGuessed`` on a note, ``handsNotesRevision`` in the header, and the wire's
    ``guessed`` list of ids."""
    payload = {
        **OLD_FILE,
        "handsNotesRevision": 4,
        "events": [
            {**OLD_FILE["events"][0], "hand": "right", "handGuessed": True},
            *OLD_FILE["events"][1:],
        ],
    }
    piece = events_file.piece_from_payload(payload)
    assert piece.header.hands_notes_revision == 4
    assert piece.notes.hand_guessed.tolist() == [True, False, False]
    written = events_file.piece_to_payload(piece)
    assert written["handsNotesRevision"] == 4
    assert written["events"][0]["handGuessed"] is True
    assert "handGuessed" not in written["events"][1]
    assert columns.to_columns(piece.notes)["guessed"] == [0]
    events = events_file.events_from_notes(piece.notes)
    assert events[0].hand_guessed is True
    assert events_file.notes_from_events(events).hand_guessed.tolist() == [
        True,
        False,
        False,
    ]


def test_reading_an_old_file_never_writes_it(data_dir: Path) -> None:
    uuid = store.create("Old", AudioSource.UPLOAD, "wav").uuid
    path = pipeline.events_path(uuid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(OLD_FILE), encoding="utf-8")
    before = path.read_bytes(), path.stat().st_mtime_ns

    first = pipeline.load_note_events(uuid)
    second = events_file.read_piece(uuid)

    assert (path.read_bytes(), path.stat().st_mtime_ns) == before
    assert first is not None and second is not None
    assert [event.id for event in first.events] == second.notes.id.tolist() == [0, 1, 2]


def test_ids_are_kept_by_a_save_and_never_reused(data_dir: Path) -> None:
    uuid = store.create("Ids", AudioSource.UPLOAD, "wav").uuid
    events = [
        NoteEvent(midi_note=60 + i, start=i * 0.5, end=i * 0.5 + 0.3) for i in range(4)
    ]
    pipeline.save_note_events(uuid, events, 3.0)
    assert [event.id for event in events] == [0, 1, 2, 3]

    stored = pipeline.load_note_events(uuid)
    assert stored is not None
    # Delete the note with the highest id, add a new one: the new one does not take id 3.
    kept = [event for event in stored.events if event.id != 3]
    kept.append(NoteEvent(midi_note=72, start=2.5, end=2.9))
    pipeline.save_note_events(uuid, kept, 3.0)

    again = pipeline.load_note_events(uuid)
    assert again is not None
    assert [event.id for event in again.events] == [0, 1, 2, 4]
    assert again.header.next_id == 5


def test_a_repeated_id_keeps_its_first_holder() -> None:
    ids, next_id = events_file.assign_ids([4, 4, None, 1], 0)
    assert ids == [4, 5, 6, 1] and next_id == 7


def test_a_writer_that_only_changes_notes_keeps_the_header(data_dir: Path) -> None:
    uuid = store.create("Header", AudioSource.UPLOAD, "wav").uuid
    header = events_file.PieceHeader(
        notes_revision=7,
        hands_revision=3,
        audio_revision=2,
        engine="muscriptor-large",
        lag_correction_ms=15.0,
    )
    pipeline.save_note_events(
        uuid, [NoteEvent(midi_note=60, start=0, end=1)], 2.0, header=header
    )

    stored = pipeline.load_note_events(uuid)
    assert stored is not None
    stored.events[0].hand = "right"
    # The way `PUT /time/{uuid}/hands` saves: no header given.
    pipeline.save_note_events(
        uuid, stored.events, stored.duration_seconds, stored.title
    )

    again = pipeline.load_note_events(uuid)
    assert again is not None and again.events[0].hand == "right"
    assert again.header == events_file.PieceHeader(
        notes_revision=7,
        hands_revision=3,
        audio_revision=2,
        engine="muscriptor-large",
        lag_correction_ms=15.0,
        next_id=1,
    )


def test_a_new_transcription_records_its_engine_and_continues_the_ids(
    data_dir: Path,
) -> None:
    uuid = store.create("Engine", AudioSource.UPLOAD, "wav").uuid
    pipeline.save_note_events(uuid, [NoteEvent(midi_note=60, start=0, end=1)], 2.0)

    class TwoNotes:
        name = "two-notes"

        def transcribe(self, wav_path: Path) -> list[NoteEvent]:
            return [
                NoteEvent(midi_note=62, start=0, end=1),
                NoteEvent(midi_note=64, start=1, end=2),
            ]

    entry = store.get(uuid)
    entry.normalized_path.parent.mkdir(parents=True, exist_ok=True)
    entry.normalized_path.write_bytes(b"")  # the fake engine never reads it
    result = pipeline.transcribe_audio(uuid, engine=TwoNotes())

    assert result.header.engine == "two-notes"
    assert [event.id for event in result.events] == [1, 2]
    stored = events_file.read_piece(uuid)
    assert stored is not None and stored.header.engine == "two-notes"


@pytest.mark.skipif(not LIBRARY.is_dir(), reason="no local library in data/audio")
def test_every_piece_of_the_library_round_trips_through_the_sparse_form() -> None:
    """Exact, at the 0.1 ms every save has always written.

    One synthetic demo piece ("Even and swung", written by a script and not by the app) holds 16
    times with a fifth decimal; any save of it, before this module or through it, keeps four.
    """

    def stored(item: dict) -> dict:
        return {
            key: round(value, 4) if key in ("start", "end") else value
            for key, value in item.items()
            if key != "id"
        }

    files = sorted(LIBRARY.glob("*/matrices/events.json"))
    assert files
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        piece = events_file.piece_from_payload(payload)
        assert piece.outside_keyboard == 0, path
        written = events_file.piece_to_payload(piece)
        for before, after in zip(payload["events"], written["events"], strict=True):
            assert stored(after) == stored(before), path
        again = events_file.piece_from_payload(written)
        assert again.notes.equals(piece.notes, atol_ms=0.051), path


# ------------------------------------------------------------------------ dense


def test_dense_to_sparse_to_dense_gives_the_same_cells() -> None:
    notes = one_note_per_key(random_notes())
    for frame_ms in (10, 40):
        grid = dense.to_dense(notes, frame_ms, 61_000)
        back = dense.to_dense(dense.from_dense(grid, frame_ms), frame_ms, 61_000)
        assert np.array_equal(back, grid), frame_ms


def test_sparse_to_dense_to_sparse_is_exact_for_muscriptor_notes_at_10_ms() -> None:
    notes = superestrella_20s()
    grid = dense.to_dense(notes, 10, 20_000)
    back = dense.from_dense(grid, 10)

    assert back.equals(one_note_per_key(notes), ids=False)


def test_at_40_ms_the_times_snap_to_the_nearest_column() -> None:
    notes = one_note_per_key(superestrella_20s())
    report = dense.to_dense_report(notes, 40, 20_000)
    back = dense.from_dense(report.grid, 40)

    snapped_on = np.array([frame_of_ms(value, 40) * 40 for value in notes.on_ms])
    # Some notes join a neighbour on their key once two onsets fall in one column.
    assert len(back) == len(notes) - report.merged
    assert set(back.on_ms.tolist()) <= set(snapped_on.tolist())
    assert np.all(back.on_ms % 40 == 0) and np.all(back.len_ms % 40 == 0)


def test_the_onset_column_follows_frame_of_ms() -> None:
    notes = random_notes(500, seed=3)
    start, _ = dense.columns_of(notes, 40)
    assert start.tolist() == [frame_of_ms(value, 40) for value in notes.on_ms]
    # A time exactly half a column in goes to the later column (D-02).
    halves = Notes.build(key=[40, 41], on_ms=[20, 60], len_ms=[40, 40])
    assert dense.columns_of(halves, 40)[0].tolist() == [1, 2]


def test_a_new_onset_of_a_key_ends_the_note_sounding_on_it() -> None:
    notes = Notes.build(key=[40, 40], on_ms=[0, 200], len_ms=[1000, 100])
    report = dense.to_dense_report(notes, 10, 2000)
    row = report.grid[40]

    assert row[0] == ONSET and row[1:20].tolist() == [SUSTAIN] * 19
    assert row[20] == ONSET and row[21:30].tolist() == [SUSTAIN] * 9
    assert not row[30:].any()
    assert report.shortened == 1


def test_notes_past_the_end_and_notes_sharing_a_column_are_counted() -> None:
    notes = Notes.build(key=[40, 40, 50], on_ms=[100, 110, 5000], len_ms=[50, 200, 100])
    report = dense.to_dense_report(notes, 40, 1000)
    assert report.past_end == 1 and report.merged == 1
    assert report.grid.shape == (88, 25)
    # The longer of the two notes in column 3 is the one kept.
    assert dense.from_dense(report.grid, 40).len_ms.tolist() == [200.0]


def test_an_orphan_sustain_is_read_as_an_onset() -> None:
    grid = np.zeros((88, 5), dtype=np.int8)
    grid[10, 0:3] = SUSTAIN
    notes = dense.from_dense(grid, 10)
    assert notes.key.tolist() == [10] and notes.len_ms.tolist() == [30.0]


def test_the_two_hand_matrices_are_two_masks_of_one_set_of_notes() -> None:
    notes = one_note_per_key(random_notes(400, seed=11)).copy()
    notes.hand[notes.hand == HAND_NONE] = HAND_RIGHT  # every note has a hand
    right, left = dense.to_hand_grids(notes, 10, 61_000)

    whole = dense.to_dense(notes, 10, 61_000)
    assert np.count_nonzero(right) + np.count_nonzero(left) >= np.count_nonzero(whole)
    back = dense.from_hand_grids(right, left, 10)
    assert back.id.tolist() == list(range(len(back)))
    assert np.array_equal(dense.to_hand_grids(back, 10, 61_000)[0], right)
    assert np.array_equal(dense.to_hand_grids(back, 10, 61_000)[1], left)

    # Moving one note to the other hand moves its whole rectangle, onset and sustain.
    moved = back.copy()
    first_right = int(np.nonzero(moved.hand == HAND_RIGHT)[0][0])
    moved.hand[first_right] = HAND_LEFT
    new_right, new_left = dense.to_hand_grids(moved, 10, 61_000)
    cells = np.count_nonzero(right) - np.count_nonzero(new_right)
    assert cells == int(moved.len_ms[first_right] // 10)
    assert np.count_nonzero(new_left) - np.count_nonzero(left) == cells


# -------------------------------------------------------------------------- COO


def coo_the_old_way(grid: np.ndarray) -> tuple[list[int], list[int], list[int]]:
    """The Python loop `PianoMatrix.to_coo_payload` used before Phase 2."""
    cols, rows = np.nonzero(grid.T)
    rows_list, cols_list = rows.astype(int).tolist(), cols.astype(int).tolist()
    onset = [
        row if grid[row, col] == ONSET else -1 for row, col in zip(rows_list, cols_list)
    ]
    return rows_list, cols_list, onset


def test_the_numpy_coo_payload_is_the_one_the_loop_built() -> None:
    grid = dense.to_dense(random_notes(), 40, 61_000)
    payload = coo.coo_from_grid(grid)

    assert (payload.rows, payload.cols, payload.onset) == coo_the_old_way(grid)
    assert payload.shape == [88, grid.shape[1]] and payload.format == "binary-coo"
    assert np.array_equal(coo.grid_from_coo(payload), grid)
    # What the builder skips, a payload read from outside still gets.
    SparseCooMatrix.model_validate(payload.model_dump())


def test_the_coo_check_still_refuses_bad_cells() -> None:
    with pytest.raises(ValueError, match="rows\\[1\\]"):
        SparseCooMatrix(shape=[88, 4], rows=[3, 88], cols=[0, 1], onset=[3, -1])
    with pytest.raises(ValueError, match="cols\\[0\\]"):
        SparseCooMatrix(shape=[88, 4], rows=[3], cols=[4], onset=[3])
    with pytest.raises(ValueError, match="onset\\[0\\]"):
        SparseCooMatrix(shape=[88, 4], rows=[3], cols=[0], onset=[5])


def test_coo_from_notes_is_the_coo_of_the_dense_matrix() -> None:
    notes = superestrella_20s()
    grid = dense.to_dense(notes, 40, 20_000, hand=None)
    assert coo.coo_from_notes(notes, 40, 20_000).rows == coo.coo_from_grid(grid).rows


# ----------------------------------------------------------------------- columns


def test_the_columns_round_trip() -> None:
    notes = random_notes()
    payload = columns.to_columns(
        notes, revision=7, hands_revision=3, duration_ms=61_000.4
    )

    assert payload["revision"] == 7 and payload["handsRevision"] == 3
    assert payload["durationMs"] == 61_000
    assert set(payload["hand"]) <= {"r", "l", "-"}
    back = columns.from_columns(json.loads(json.dumps(payload)))
    # Everything but the velocity travels; the browser does not need it.
    assert back.id.tolist() == notes.sorted().id.tolist()
    assert np.array_equal(back.key, notes.sorted().key)
    assert np.array_equal(back.on_ms, notes.sorted().on_ms)
    assert np.array_equal(back.len_ms, notes.sorted().len_ms)
    assert np.array_equal(back.hand, notes.sorted().hand)


def test_the_columns_are_whole_milliseconds_sorted_by_onset() -> None:
    notes = Notes.build(key=[50, 40], on_ms=[250.3, 250.3], len_ms=[0.2, 100.6])
    payload = columns.to_columns(notes)
    assert payload["key"] == [40, 50]
    assert payload["onMs"] == [250, 250]
    # The release is the rounded release: 250.3 + 100.6 = 350.9 -> 351. A note is at least 1 ms.
    assert payload["lenMs"] == [101, 1]


def test_the_hand_string_refuses_other_characters() -> None:
    with pytest.raises(ValueError, match="'x'"):
        columns.decode_hands("rlx")


# -------------------------------------------------------------------------- MIDI


def test_the_midi_round_trip_keeps_keys_times_hands_and_velocity() -> None:
    notes = one_note_per_key(random_notes(400, seed=5))
    back = midi.from_midi(midi.to_midi_bytes(notes, title="Round trip"))

    ordered = notes.sorted()
    assert back.equals(
        Notes.build(
            key=ordered.key,
            on_ms=ordered.on_ms,
            len_ms=ordered.len_ms,
            hand=ordered.hand,
            velocity=ordered.velocity,
        ),
        ids=False,
    )


def test_a_repeated_note_at_the_same_instant_survives_midi() -> None:
    # MuScriptor closes a note of a key at the instant the same key is struck again (gap 0 ms).
    notes = Notes.build(
        key=[50, 50], on_ms=[8400, 8840], len_ms=[440, 300], hand=[1, 1]
    )
    back = midi.from_midi(midi.to_midi_bytes(notes))
    assert back.on_ms.tolist() == [8400.0, 8840.0] and back.len_ms.tolist() == [
        440.0,
        300.0,
    ]


def test_a_midi_file_from_elsewhere_follows_its_tempo_map() -> None:
    import mido

    file = mido.MidiFile(type=1, ticks_per_beat=480)
    conductor = mido.MidiTrack()
    conductor.append(mido.MetaMessage("set_tempo", tempo=500_000, time=0))  # 120 BPM
    conductor.append(
        mido.MetaMessage("set_tempo", tempo=1_000_000, time=960)
    )  # 60 BPM after 1 s
    file.tracks.append(conductor)
    piano = mido.MidiTrack()
    piano.append(mido.Message("note_on", note=60, velocity=90, time=0))
    piano.append(mido.Message("note_on", note=60, velocity=0, time=480))  # 0.5 s
    piano.append(mido.Message("note_on", note=64, velocity=80, time=480))  # at 1.0 s
    piano.append(
        mido.Message("note_off", note=64, velocity=0, time=480)
    )  # 1.0 s later at 60 BPM
    piano.append(
        mido.Message("note_on", channel=9, note=40, velocity=90, time=0)
    )  # a drum
    file.tracks.append(piano)

    notes = midi.from_midi(file)
    assert notes.key.tolist() == [60 - 21, 64 - 21]
    assert notes.on_ms.tolist() == [0.0, 1000.0]
    assert notes.len_ms.tolist() == [500.0, 1000.0]
    assert notes.hand.tolist() == [HAND_NONE, HAND_NONE]
    assert notes.velocity.tolist() == [90, 80]


# -------------------------------------------------------------------- MuScriptor


def test_muscriptor_events_give_the_notes_muscriptor_itself_assembled() -> None:
    notes = superestrella_20s()
    theirs = json.loads(NOTES_20S.read_text())

    assert len(notes) == len(theirs) == 102
    ours = sorted(zip(notes.midi.tolist(), notes.on_ms.tolist(), notes.end_ms.tolist()))
    expected = sorted(
        (item["pitch"], round(item["start"] * 1000), round(item["end"] * 1000))
        for item in theirs
    )
    assert ours == expected
    # Whole milliseconds on MuScriptor's 10 ms grid, and no loudness.
    assert np.all(notes.on_ms % 10 == 0) and np.all(notes.len_ms % 10 == 0)
    assert set(notes.velocity.tolist()) == {64}


def test_ids_follow_the_order_the_starts_arrive_in() -> None:
    events = [json.loads(line) for line in EVENTS_20S.read_text().splitlines()]
    starts = [event for event in events if event["type"] == "NoteStartEvent"]
    notes = muscriptor.from_muscriptor_events(events, end_ms=20_000, first_id=100)

    by_id = {
        int(i): (int(m), float(o)) for i, m, o in zip(notes.id, notes.midi, notes.on_ms)
    }
    for position, event in enumerate(starts):
        assert by_id[100 + position] == (
            event["pitch"],
            round(event["start_time"] * 1000),
        )


@dataclass
class NoteStartEvent:
    pitch: int
    start_time: float
    index: int
    instrument: str = "acoustic_piano"


@dataclass
class NoteEndEvent:
    end_time: float
    start_event: NoteStartEvent

    @property
    def start_event_index(self) -> int:
        return self.start_event.index


@dataclass
class ProgressEvent:
    completed: int
    total: int


def test_the_assembler_tells_open_notes_from_closed_ones_while_it_streams() -> None:
    a = NoteStartEvent(60, 0.50, 0)
    b = NoteStartEvent(64, 0.50, 1)
    drum = NoteStartEvent(36, 0.60, 2, instrument="drums")
    assembler = muscriptor.MuScriptorAssembler()
    for event in (
        ProgressEvent(0, 4),
        a,
        b,
        drum,
        NoteEndEvent(0.80, a),
        ProgressEvent(1, 4),
    ):
        assembler.add(event)

    assert (assembler.completed, assembler.total) == (1, 4)
    assert assembler.closed_since(0) == [(0, 60 - 21, 500, 300)]
    assert assembler.open_notes == [(1, 64 - 21, 500)]
    assert assembler.skipped == 1

    # A new onset of the key ends the open note; the late end event of that note changes nothing.
    assembler.add(NoteStartEvent(64, 1.20, 3))
    assembler.add(NoteEndEvent(1.50, b))
    assert assembler.closed_since(1) == [(1, 64 - 21, 500, 700)]
    notes = assembler.notes(end_ms=2000)
    assert notes.id.tolist() == [0, 1, 2]
    assert notes.len_ms.tolist() == [
        300.0,
        700.0,
        800.0,
    ]  # the last one closed at the end


def test_the_lag_correction_moves_every_onset_and_release() -> None:
    events = [
        NoteStartEvent(60, 0.01, 0),
        NoteEndEvent(0.50, NoteStartEvent(60, 0.01, 0)),
    ]
    early = muscriptor.from_muscriptor_events(events, lag_correction_ms=15)
    late = muscriptor.from_muscriptor_events(events, lag_correction_ms=-17)

    assert (early.on_ms.tolist(), early.end_ms.tolist()) == (
        [0.0],
        [485.0],
    )  # never before 0
    assert (late.on_ms.tolist(), late.end_ms.tolist()) == ([27.0], [517.0])


# ---------------------------------------------------------------------- .pmn.json


def test_the_portable_file_round_trips(tmp_path: Path) -> None:
    notes = events_file.piece_from_payload(OLD_FILE).notes
    path = portable.write_portable(
        notes, tmp_path / "piece.pmn.json", duration_ms=3500, title="Old"
    )
    body = json.loads(path.read_text())

    assert (
        body["format"] == "aimpromptu-pmn"
        and body["lowestMidi"] == 21
        and body["keys"] == 88
    )
    assert body["onMs"] == [250.1, 250.3]  # the 0.1 ms of the old pieces survive
    back, duration, title = portable.read_portable(path)
    assert back.equals(notes.live().sorted())
    assert (duration, title) == (3500.0, "Old")


def test_the_portable_file_refuses_another_format() -> None:
    with pytest.raises(ValueError, match="Not a"):
        portable.from_portable({"format": "something-else"})
    body = portable.to_portable(superestrella_20s(), duration_ms=20_000)
    body["version"] = 99
    with pytest.raises(ValueError, match="newer"):
        portable.from_portable(body)
