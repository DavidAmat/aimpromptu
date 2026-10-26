"""The marks of an old sheet (``sheet.json``, vexflow-v2) on the new sheet (implementation 03, Phase 9): a part with no
stored sheet is drawn with them, the migration stores them once, and a sheet the AI wrote gets only the user's marks.
The old clefs and octave lines are dropped (the user's answer of 2026-10-26). Sonnet is a stand-in.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from aitu_backend.part_sheet import build, job, legacy
from aitu_backend.part_sheet import store as sheet_store
from aitu_backend.transcription import pipeline
from scripts.migrate_sheets import migrate
import test_part_sheet
from test_part_sheet import SECONDS, finish, sheet
from test_sheet_llm_frames import oracle, song
from test_sheet_reading import notes_of

client = test_part_sheet.client
part = test_part_sheet.part

#: The right hand's run of the second bar of the stand-in song starts at 2 s: its onset cells.
RUN = [50, 56, 63, 69, 75, 81, 88, 94]


def old_sheet(part: str, **marks) -> None:
    body = {
        "anchorFigure": "negra",
        "anchorMs": 250.0,
        "frameMs": 40.0,
        "keySignature": "C",
        **marks,
    }
    pipeline.rhythm_path(part).write_text(json.dumps(body))


def beamed_in_run(body: dict) -> int:
    """A note of the right hand's run in the middle of a beam group: the cell a break would cut at."""
    run = [n for n in body["notes"] if n["hand"] == "right" and int(n["ref"].split(":")[0]) in RUN]
    for before, note in zip(run, run[1:]):
        if note["beam"] is not None and note["beam"] == before["beam"]:
            return int(note["ref"].split(":")[0])
    raise AssertionError("no beam group in the run")


def test_a_part_with_an_old_sheet_is_drawn_with_its_marks_and_without_its_clefs(
    client: TestClient, part: str
) -> None:
    plain = sheet(client, part)
    cut = beamed_in_run(plain)
    old_sheet(
        part,
        title="Old title",
        lineSpacing=36.0,
        lyrics=[
            {
                "fromColumn": 50,
                "toColumn": 94,
                "text": "words over the run",
                "offsetY": -8.57,
                "width": 85.7,
            },
            {"fromColumn": 60, "toColumn": 70, "text": "over the piece before"},
        ],
        overrides=[{"hand": "left", "row": 0, "startFrame": 0, "figure": "negra"}],
        fingers=[{"hand": "right", "startFrame": 0, "row": 64 - 21, "finger": 2}],
        beamBreaks=[{"hand": "right", "startFrame": cut}],
        clefChanges=[{"hand": "left", "fromColumn": 0, "clef": "treble"}],
        ottavas=[{"kind": "8vb", "hand": "left", "fromColumn": 0, "toColumn": 200}],
    )
    body = sheet(client, part)
    assert body["titles"] == {"title": "Old title"}
    # 36 px against the old default of 72: half of the new default of 5 staff spaces.
    assert body["lineSpace"] == 2.5
    # The second piece was over the frames of the first: the new sheet never lets two pieces share one.
    assert [(one["start"], one["end"], one["text"]) for one in body["lyrics"]] == [
        (50, 94, "words over the run")
    ]
    assert body["lyrics"][0]["lift"] == 1.0 and body["lyrics"][0]["width"] == 10.0
    notes = notes_of(body)
    left = [note for ref, note in notes.items() if ref.startswith("0:") and note["hand"] == "left"]
    assert left and all(note["figure"] == 4 and note["fixed"] for note in left)
    assert notes["0:64"]["finger"] == 2
    run = [n for n in body["notes"] if n["hand"] == "right" and int(n["ref"].split(":")[0]) in RUN]
    at = [int(n["ref"].split(":")[0]) for n in run].index(cut)
    assert run[at]["beam"] != run[at - 1]["beam"]
    # The new clef rules: the old treble clef and 8vb of the left hand are not drawn.
    assert body["reading"] == plain["reading"]
    assert all(n["ottava"] == 0 for n in body["notes"] if n["hand"] == "left")
    # Nothing is stored by drawing it.
    assert sheet_store.load(part) is None


def test_the_migration_stores_the_marks_once_and_the_drawing_does_not_change(
    client: TestClient, part: str
) -> None:
    old_sheet(
        part,
        anchorFigure="corchea",
        lyrics=[{"fromColumn": 50, "toColumn": 94, "text": "words"}],
        overrides=[{"hand": "left", "row": 0, "startFrame": 0, "figure": "blanca"}],
        ottavas=[{"kind": "8va", "hand": "right", "fromColumn": 0, "toColumn": 100}],
    )
    drawn = build.current(part).text
    what, carried, dropped = migrate(part, write=False)
    assert what == "algorithm sheet: would store" and sheet_store.load(part) is None
    assert carried == {"lyrics": 1, "figures": 1} and dropped == {"octave lines": 1}
    what, _, _ = migrate(part, write=True)
    assert what == "algorithm sheet: stored"
    kept = sheet_store.load(part)
    assert (
        kept is not None
        and kept.record.edited
        and kept.record.legacy == {"lyrics": 1, "figures": 1}
    )
    # The old sheet named the pile of gaps a corchea: a new AI run keeps that name.
    assert kept.record.reference == "user"
    assert build.current(part).text == drawn
    assert migrate(part, write=True)[0] == "migrated already"
    # Without the old sheet the marks stay: they are in sheet.f1 now.
    pipeline.rhythm_path(part).unlink()
    assert build.current(part).text == drawn


def test_a_sheet_the_ai_wrote_gets_only_the_users_marks(client: TestClient, part: str) -> None:
    finish(job_start(part))
    ai = sheet(client, part)
    assert ai["llm"]["enhanced"]
    cut = beamed_in_run(ai)
    old_sheet(
        part,
        lyrics=[{"fromColumn": 0, "toColumn": 40, "text": "words"}],
        overrides=[{"hand": "left", "row": 0, "startFrame": 0, "figure": "negra"}],
        beamBreaks=[{"hand": "right", "startFrame": cut}],
        clefChanges=[{"hand": "left", "fromColumn": 0, "clef": "treble"}],
    )
    # A stored sheet is drawn as stored: the old marks reach it only through the migration.
    assert sheet(client, part)["lyrics"] == []
    what, carried, dropped = migrate(part, write=True)
    assert what == "llm sheet: stored"
    assert carried == {"lyrics": 1, "figures": 1}
    assert dropped == {"clefs": 1, "beam marks (the AI's)": 1}
    body = sheet(client, part)
    assert body["llm"]["enhanced"] and [one["text"] for one in body["lyrics"]] == ["words"]

    # The AI's beams and clefs stay as it wrote them (the left hand's first chord, now a negra, leaves its group).
    def right(drawing: dict) -> list:
        return [(n["ref"], n["beam"]) for n in drawing["notes"] if n["hand"] == "right"]

    assert right(body) == right(ai)
    assert body["reading"] == ai["reading"]
    kept = sheet_store.load(part)
    assert kept is not None and kept.record.source == "llm" and kept.record.legacy == carried


def test_a_beam_join_follows_the_chord_before_and_marks_that_already_hold_change_nothing(
    client: TestClient, part: str
) -> None:
    plain = sheet(client, part)
    run = [n for n in plain["notes"] if n["hand"] == "right" and int(n["ref"].split(":")[0]) in RUN]
    starts = [
        int(b["ref"].split(":")[0])
        for a, b in zip(run, run[1:])
        if a["beam"] is not None and b["beam"] is not None and a["beam"] != b["beam"]
    ]
    inside = beamed_in_run(plain)
    old_sheet(
        part,
        beamJoins=[{"hand": "right", "startFrame": f} for f in starts]
        + [{"hand": "right", "startFrame": inside}],
    )
    notes = pipeline.starting_hands(part)
    carried = legacy.carry(
        build.algorithm(part, notes).sheet, pipeline.load_rhythm(part), notes, ai=False
    )
    assert carried["beam joins held"] >= 1
    assert carried["beam joins"] + carried["beam joins lost"] == len(starts)


def job_start(part: str):
    return job.start(part, complete=lambda: oracle(song(SECONDS)))
