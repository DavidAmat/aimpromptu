"""`notes.pmn`, the portable `.pmn` version 2: the stored notes of a part (implementation 02,
Phase 3, plan P-5)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from aitu_backend.pmn import events_file, notes_file, portable
from aitu_backend.pmn.events_file import PieceHeader

#: An `events.json` with everything a part can hold: ids, a removed note, a guessed hand, a pin,
#: times with four decimals of seconds, and a header.
FULL = {
    "schemaVersion": "1.1",
    "durationSeconds": 189.56,
    "title": "Superestrella",
    "notesRevision": 3,
    "handsRevision": 12,
    "handsNotesRevision": 3,
    "audioRevision": 1,
    "engine": "muscriptor-large",
    "lagCorrectionMs": -12.5,
    "nextId": 9,
    "events": [
        {"id": 0, "midiNote": 60, "start": 3.0701, "end": 4.2904, "velocity": 64, "hand": "right"},
        {"id": 4, "midiNote": 48, "start": 3.07, "end": 3.9, "velocity": 70, "hand": "left",
         "handGuessed": True},
        {"id": 2, "midiNote": 72, "start": 0.0001, "end": 0.0123, "velocity": 64, "removed": True},
        {"id": 8, "midiNote": 21, "start": 188.9999, "end": 189.56, "velocity": 1},
    ],
}  # fmt: skip


def test_the_body_has_the_header_and_the_columns_in_the_order_of_the_part() -> None:
    body = notes_file.to_pmn(FULL)
    assert body["format"] == "aimpromptu-pmn" and body["version"] == 2
    assert body["durationMs"] == 189560
    assert body["id"] == [0, 4, 2, 8]
    assert body["key"] == [39, 27, 51, 0]
    assert body["onMs"] == [3070.1, 3070, 0.1, 188999.9]
    assert body["hand"] == "rl--"
    assert body["removed"] == [2] and body["handGuessed"] == [4]
    assert (
        body["notesRevision"] == 3
        and body["nextId"] == 9
        and body["lagCorrectionMs"] == -12.5
    )
    assert "outside" not in body


def test_every_number_comes_back_equal() -> None:
    assert notes_file.from_pmn(notes_file.to_pmn(FULL)) == FULL


def test_an_old_file_with_no_ids_reads_the_same_after_the_conversion() -> None:
    old = {
        "schemaVersion": "1.0",
        "durationSeconds": 8.0,
        "events": [
            {"midiNote": 60, "start": 0.25, "end": 0.45, "velocity": 64},
            {"midiNote": 62, "start": 0.5, "end": 0.7, "velocity": 64, "hand": "left"},
        ],
    }
    before = events_file.piece_from_payload(old)
    after = events_file.piece_from_payload(notes_file.from_pmn(notes_file.to_pmn(old)))
    assert after.notes.id.tolist() == before.notes.id.tolist() == [0, 1]
    assert np.array_equal(after.notes.on_ms, before.notes.on_ms)
    assert np.array_equal(after.notes.hand, before.notes.hand)
    assert after.header == before.header == PieceHeader(next_id=2)


def test_a_note_outside_the_keyboard_survives() -> None:
    outside = {"id": 9, "midiNote": 110, "start": 1.0, "end": 2.0, "velocity": 64}
    payload = {**FULL, "events": [*FULL["events"], outside]}
    body = notes_file.to_pmn(payload)
    assert body["outside"] == [
        {"id": 9, "midiNote": 110, "start": 1.0, "end": 2.0, "velocity": 64}
    ]
    assert notes_file.from_pmn(body)["events"][-1]["midiNote"] == 110


def test_the_file_boundary_writes_pmn_and_reads_it_back(tmp_path: Path) -> None:
    path = tmp_path / "notes.pmn"
    events_file.write_payload(path, FULL)
    assert json.loads(path.read_text())["format"] == "aimpromptu-pmn"
    assert events_file.read_payload(path) == FULL
    old = tmp_path / "events.json"
    events_file.write_payload(old, FULL)
    assert json.loads(old.read_text()) == FULL


def test_the_portable_reader_reads_it_as_an_export_without_the_removed_notes() -> None:
    notes, duration_ms, title = portable.from_portable(notes_file.to_pmn(FULL))
    assert notes.id.tolist() == [0, 4, 8]
    assert (duration_ms, title) == (189560.0, "Superestrella")
