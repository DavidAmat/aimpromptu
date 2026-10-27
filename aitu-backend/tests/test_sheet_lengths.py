"""The new sheet through a change of a part's length (implementation 03, Phase 8B): ``sheet.f1`` moved, cut out, copied
and put in with the notes by a paste, a split and a join, so the decisions after the change stay on their notes
(before, the stored sheet was laid again on the moved notes, and they were lost). Sonnet is the stand-in ``oracle``.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from aitu_backend.audio import store as audio_store
from aitu_backend.editing import history, parts, paste
from aitu_backend.part_sheet import build, lengths
from aitu_backend.part_sheet import store as sheet_store
from aitu_backend.pmn import events_file
from aitu_backend.schemas.metadata import AudioSource
from aitu_backend.sheet.sheet import f1
from aitu_backend.sheet.sheet.data import Lyric
from aitu_backend.storage import locate
from aitu_backend.transcription import pipeline
from aitu_backend.transcription.engine import NoteEvent
import test_part_sheet
from test_part_sheet import SECONDS
from test_sheet_edits import enhance
from test_sheet_llm_frames import song

client = test_part_sheet.client
part = test_part_sheet.part

SHEET = """F1 frames frameMs=40 quarterMs=500
key=2# clefs: R=treble L=bass
f0       L: C3:8 b1  R: E4:8 b2
f6       L: G3:8 b1  R: F#4:8 b2
f12      L: C4:8 b1  R: G4:8 b2
f18      L: G3:8 b1  R: A4:8 b2
f30      R: B4:4
"""


def _frames(sheet, staff: int) -> list[int]:
    return [n.frame for n in sheet.notes if n.staff == staff]


def _groups(sheet) -> set[frozenset[int]]:
    out: dict[int, set[int]] = {}
    for n in sheet.notes:
        if n.beam is not None:
            out.setdefault(n.beam, set()).add(n.frame)
    return {frozenset(g) for g in out.values()}


# ------------------------------------------------------------------ the four moves


def test_shift_cuts_a_beam_group_and_ends_a_lyrics_piece_at_the_frame() -> None:
    sheet = f1.read(SHEET)
    sheet.lyrics = [Lyric(0, 20, "across"), Lyric(25, 35, "after", at=30, dx=1.0, dy=2.0)]
    sheet.key_changes = [(30, 0)]
    moved = lengths.shift(sheet, 12, 100)
    assert _frames(moved, 2) == [0, 6, 112, 118] and _frames(moved, 1)[-1] == 130
    # Each group is cut at the frame: two notes before, two after, in each hand.
    assert _groups(moved) == {frozenset({0, 6}), frozenset({112, 118})}
    assert moved.key_changes == [(130, 0)]
    assert [(one.start, one.end, one.at) for one in moved.lyrics] == [
        (0, 12, None),
        (125, 135, 130),
    ]
    # The sheet given is not changed.
    assert _frames(sheet, 2) == [0, 6, 12, 18]


def test_cut_out_keeps_the_armadura_and_clefs_in_force_after_the_stretch() -> None:
    sheet = f1.read(SHEET)
    sheet.key_changes = [(10, -3)]
    sheet.clef_changes = [(8, 2, "G2")]
    cut = lengths.cut_out(sheet, 4, 14)
    assert _frames(cut, 2) == [0, 8] and _frames(cut, 1) == [0, 8, 20]
    # The changes inside the stretch are gone, but what they set is in force from where it was.
    assert cut.key_changes == [(4, -3)] and cut.clef_changes == [(4, 2, "G2")]
    # A group whose middle is taken out is cut there, and a part of one note is no group.
    assert _groups(cut) == set()
    # From the first note: the header changes.
    head = lengths.cut_out(sheet, 0, 14)
    assert head.key == -3 and head.clefs[2] == "G2" and head.key_changes == []


def test_extract_and_put_in_carry_the_armadura_and_clefs_of_both_sides() -> None:
    source = f1.read(SHEET)
    source.key_changes = [(12, -1)]
    source.clef_changes = [(12, 2, "G2")]
    passage = lengths.extract(source, 12, 24)
    assert passage.key == -1 and passage.clefs == {1: "G2", 2: "G2"}
    assert [n.frame for n in passage.notes] == [0, 0, 6, 6] and _groups(passage) == {
        frozenset({0, 6})
    }
    target = f1.read(SHEET)
    placed = lengths.put_in(target, passage, 12, 12, music_after=True)
    assert _frames(placed, 2) == [0, 6, 12, 18, 24, 30]
    # The passage reads in its own armadura and clef, and the target's come back after it.
    assert placed.key_changes == [(12, -1), (24, 2)]
    assert placed.clef_changes == [(12, 2, "G2"), (24, 2, "F4")]
    # Beam numbers stay unique: the passage's group, and the target's group cut in two around it.
    assert _groups(placed) == {frozenset({0, 6}), frozenset({12, 18}), frozenset({24, 30})}
    # Into an empty part: the passage's own armadura and clefs are the sheet's.
    alone = lengths.put_in(None, passage, 0, 12, music_after=False)
    assert alone.key == -1 and alone.clefs[2] == "G2" and alone.key_changes == []


# ------------------------------------------------------------------ the stored sheet through a paste


def _marked(uuid: str) -> str:
    """The AI's sheet of the part with decisions the rules never compute: fingers from 28 s and in [10.4 s, 12 s),
    an armadura from 32 s to 36 s, a lyrics piece at 24 s, settled by the rules as an edit stores it (the page draws
    a stored sheet laid again on its notes). Returns the stored text."""
    stored = sheet_store.load(uuid)
    assert stored is not None and stored.record.enhanced
    sheet = f1.read(stored.text)
    for n in sheet.notes:
        if not n.covered and n.grace is None and (700 <= n.frame < 800 or 260 <= n.frame < 300):
            n.finger = 3 if n.frame >= 700 else 2
    sheet.key_changes = [(800, 2), (900, 0)]
    sheet.lyrics = [Lyric(600, 650, "after the paste")]
    text = f1.write(build.reapply(sheet, pipeline.starting_hands(uuid)), mode="frames")
    sheet_store.save(uuid, text, stored.record)
    return text


def _fingers(sheet, lo: int, hi: int) -> set[tuple[int, int, int]]:
    return {(n.frame, n.midi, n.finger) for n in sheet.notes if n.finger and lo <= n.frame < hi}


def _stored(uuid: str):
    stored = sheet_store.load(uuid)
    assert stored is not None
    header = events_file.read_header(pipeline.events_path(uuid))
    assert stored.record.hands_revision == header.hands_revision, "stored for the notes as they are"
    return stored, f1.read(stored.text)


def test_a_paste_moves_the_ais_sheet_with_the_notes_and_undo_puts_it_back(
    client: TestClient, part: str
) -> None:
    enhance(part)
    text = _marked(part)
    before = f1.read(text)
    windows = sheet_store.load(part).record.windows
    done = paste.paste(part, paste.read_passage(part, 10_000.0, 14_000.0), at_ms=20_000.0)

    stored, after = _stored(part)
    assert stored.record.source == "llm" and stored.record.enhanced
    # Everything from 20 s is 4 s (100 frames) later: the fingers, the armadura changes, the lyrics piece.
    assert _fingers(after, 800, 900) == {(f + 100, m, k) for f, m, k in _fingers(before, 700, 800)}
    assert after.key_changes == [(900, 2), (1000, 0)]
    assert [(one.start, one.end, one.text) for one in after.lyrics] == [
        (700, 750, "after the paste")
    ]
    # The copied stretch brought its own decisions: the fingers of [10.4 s, 12 s) are also at [20.4 s, 22 s).
    assert _fingers(after, 510, 550) == {(f + 250, m, k) for f, m, k in _fingers(before, 260, 300)}
    assert _fingers(after, 260, 300) == _fingers(before, 260, 300)
    # The segments of the AI moved too: the one across 20 s is cut around the passage.
    assert stored.record.windows[0] == windows[0]
    assert max(b for _, b, _ in stored.record.windows) == max(b for _, b, _ in windows) + 100

    history.restore(part, done.before_version)
    assert sheet_store.load(part).text == text


def test_a_split_gives_each_part_its_stretch_of_the_sheet(client: TestClient, part: str) -> None:
    enhance(part)
    before = f1.read(_marked(part))
    project = locate.part(part).project_id
    second = parts.split(project, part, 20_000.0)

    first_stored, first = _stored(part)
    assert max(n.frame for n in first.notes) < 500
    assert _fingers(first, 260, 300) == _fingers(before, 260, 300)
    assert first_stored.record.source == "llm"

    new_stored, new = _stored(second)
    assert new_stored.record.source == "llm" and new_stored.record.enhanced
    assert _fingers(new, 200, 300) == {(f - 500, m, k) for f, m, k in _fingers(before, 700, 800)}
    assert new.key_changes == [(300, 2), (400, 0)]
    assert [(one.start, one.text) for one in new.lyrics] == [(100, "after the paste")]
    assert all(a >= 0 for a, _, _ in new_stored.record.windows)

    # Joined again, the second part's sheet comes back after the first's.
    parts.join(project, second)
    _, joined = _stored(part)
    assert _fingers(joined, 700, 800) == _fingers(before, 700, 800)
    assert joined.key_changes == [(800, 2), (900, 0)]


def test_an_ai_passage_pasted_into_an_algorithm_sheet_makes_it_mixed(
    client: TestClient, part: str
) -> None:
    enhance(part)
    before = f1.read(_marked(part))
    other = audio_store.create("Other", AudioSource.UPLOAD, "wav").uuid
    audio_store.update(other, duration_seconds=SECONDS + 4)
    notes = song(SECONDS)
    pipeline.save_note_events(
        other,
        sorted(
            (
                NoteEvent(midi_note=int(k) + 21, start=on / 1000, end=(on + n) / 1000)
                for k, on, n in zip(notes.key, notes.on_ms, notes.len_ms)
            ),
            key=lambda e: (e.start, e.midi_note),
        ),
        SECONDS + 4,
    )
    assert sheet_store.load(other) is None
    paste.paste(other, paste.read_passage(part, 10_000.0, 14_000.0), at_ms=20_000.0)
    stored, after = _stored(other)
    assert stored.record.source == "mixed" and stored.record.enhanced
    assert _fingers(after, 510, 550) == {(f + 250, m, k) for f, m, k in _fingers(before, 260, 300)}
    # The pasted notes carry the hands the AI gave them.
    pasted = [e for e in pipeline.load_note_events(other).events if 20.0 <= e.start < 24.0]
    assert pasted and all(e.hand in ("right", "left") and not e.hand_guessed for e in pasted)


def test_two_algorithm_sheets_store_nothing(client: TestClient, part: str) -> None:
    paste.paste(part, paste.read_passage(part, 10_000.0, 14_000.0), at_ms=20_000.0)
    assert sheet_store.load(part) is None


# ------------------------------------------------------------------ the paste of the new sheet, one step of undo


def test_a_paste_on_the_new_sheet_is_one_step_that_undo_and_redo_walk(
    client: TestClient, part: str
) -> None:
    from test_sheet_edits import move, walk

    enhance(part)
    text = _marked(part)
    first = test_part_sheet.sheet(client, part)
    # A step before the paste stays valid through it.
    moved = move(
        client,
        part,
        [first["notes"][0]["ref"]],
        "left" if first["notes"][0]["hand"] == "right" else "right",
    )
    assert moved["history"]["undo"].startswith("Move")
    answer = client.post(
        f"/sheet/{part}/paste",
        params={"width": 120},
        json={"source": {"part": part, "fromMs": 10_000, "toMs": 14_000}, "atMs": 20_000},
    )
    assert answer.status_code == 200, answer.text
    pasted = answer.json()
    assert pasted["edited"] == "Paste 4.0 s" and pasted["history"]["undo"] == "Paste 4.0 s"
    assert pasted["atMs"] == 20_000 and pasted["lengthMs"] == 4_000
    assert max(c["ms"] for c in pasted["columns"]) > max(c["ms"] for c in moved["columns"]) + 3_000
    assert pasted["llm"]["enhanced"] is True

    back = walk(client, part, "undo")
    assert back["walked"] == "Paste 4.0 s" and back["history"]["redo"] == "Paste 4.0 s"
    assert back["svg"] == moved["svg"]
    again = walk(client, part, "redo")
    assert again["svg"] == pasted["svg"] and again["history"]["undo"] == "Paste 4.0 s"
    # Undo twice: the paste, then the hand moved before it.
    walk(client, part, "undo")
    assert walk(client, part, "undo")["svg"] == first["svg"]
    assert sheet_store.load(part).text == text

    # Over a marked stretch, and a source nobody has: refused.
    over = client.post(
        f"/sheet/{part}/paste",
        params={"width": 120},
        json={
            "source": {"part": part, "fromMs": 0, "toMs": 2_000},
            "atMs": 4_000,
            "replaceToMs": 8_000,
        },
    )
    assert over.status_code == 200 and over.json()["edited"] == "Paste 2.0 s over a stretch"
    gone = client.post(
        f"/sheet/{part}/paste",
        json={"source": {"part": "nope", "fromMs": 0, "toMs": 2_000}, "atMs": 0},
    )
    assert gone.status_code == 404


# ------------------------------------------------------------------ Record in Sheet


def test_a_passage_reads_with_the_songs_figure_and_a_promotion_carries_the_takes_sheet(
    tmp_path, monkeypatch
) -> None:
    from aitu_backend.main import create_app
    from aitu_backend.part_sheet import build
    from test_paste import note
    from test_passages import open_and_record, song as tone_song

    client = TestClient(create_app())
    part = tone_song(tmp_path)
    # The song's sheet holds a decision of the user's: a finger on the note at 7 s.
    drawn = build.current(part)
    marked = f1.read(drawn.text)
    for n in marked.notes:
        if n.frame == 175:
            n.finger = 4
    header = events_file.read_header(pipeline.events_path(part))
    sheet_store.save(
        part,
        f1.write(marked, mode="frames"),
        sheet_store.Record(
            edited=True, hands_revision=header.hands_revision, quarter_ms=drawn.quarter_ms
        ),
    )
    quarter = f1.read(sheet_store.load(part).text).quarter_ms
    passage, take = open_and_record(
        client, monkeypatch, tmp_path, part, [note(70, 0.0, 0.9), note(72, 2.0, 2.9)]
    )
    current = client.get(f"/passages/{passage}").json()["current"]
    # The Current is the song's stretch, the take is written with the song's figure: they read alike.
    assert sheet_store.load(current).record.decided
    took = sheet_store.load(take)
    assert took.record.reference == "song" and took.record.quarter_ms == quarter
    # And with the song's armadura where the passage starts.
    assert took.record.key == f1.read(sheet_store.load(part).text).key == f1.read(took.text).key
    assert not sheet_store.asked(take), "the AI only on the button"
    # Played twice as slowly: the take's figure follows the speed.
    client.patch(f"/passages/{passage}", json={"speed": 2.0, "windowMs": 0})
    assert sheet_store.load(take).record.quarter_ms == quarter * 2

    # A finger on the take's second note (at 2 s of the take), then the promotion at the speed: 1 s into the passage.
    take_sheet = f1.read(build.current(take).text)
    second = next(n for n in take_sheet.notes if n.midi == 72)
    second.finger = 1
    header = events_file.read_header(pipeline.events_path(take))
    sheet_store.save(
        take,
        f1.write(take_sheet, mode="frames"),
        sheet_store.Record(
            edited=True, hands_revision=header.hands_revision, quarter_ms=quarter * 2
        ),
    )
    done = client.post(
        f"/passages/{passage}/promote", json={"mode": "window", "audio": "recording"}
    )
    assert done.status_code == 200, done.text
    stored, after = _stored(part)
    fingers = {(n.frame, n.midi, n.finger) for n in after.notes if n.finger}
    assert fingers == {(75, 72, 1), (175, 67, 4)}
    assert after.quarter_ms == quarter
    # The sheet opens with the promotion as its last step: undo takes it back.
    from aitu_backend.part_sheet import edits

    assert edits.history(part)["undo"] == "Promote the passage"
    assert edits.undo(part) == "Promote the passage"
    _, back = _stored(part)
    assert {(n.frame, n.midi, n.finger) for n in back.notes if n.finger} == {(175, 67, 4)}
