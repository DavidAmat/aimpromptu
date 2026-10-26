"""The sheet toolbox of the new sheet (implementation 03, Phase 8A): the title lines, the armadura of the piece, the
space between lines, the lyrics pieces, Transpose figures and Transpose notes (with their previews), a note added on
the keyboard panel, and the sheet on paper. Each edit is one step of undo; Sonnet is a stand-in.
"""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from aitu_backend.part_sheet import build
from aitu_backend.sheet.engrave.frames import Options, render_frames
from aitu_backend.sheet.sheet import f1
from aitu_backend.sheet.sheet.data import Lyric, Sheet, carry_extras
from aitu_backend.transcription import pipeline
import test_part_sheet
from test_part_sheet import sheet
from test_sheet_edits import enhance, walk
from test_sheet_reading import edit, notes_of, right_run, stored_sheet

client = test_part_sheet.client
part = test_part_sheet.part

SHEET = """F1 frames frameMs=40 quarterMs=500
key=0 clefs: R=treble L=bass
f0       L: C3:4  R: E4,G4:8 b1
[]x5
f6       R: A4:8 b1
[]x5
f12      L: G2:4  R: C5:4
"""


# ------------------------------------------------------------------ the format and the engine


def test_titles_lyrics_and_settings_round_trip_and_leave_other_sheets_unchanged() -> None:
    plain = f1.read(SHEET)
    assert f1.write(plain, mode="frames") == SHEET
    plain.titles = {"title": 'Super "estrella"', "artist": "Aitana"}
    plain.lyrics = [Lyric(12, 30, "two\nlines", 2.0, 0.5), Lyric(0, 10, "Me ve")]
    plain.space_ms, plain.line_space = 480.0, 7.5
    text = f1.write(plain, mode="frames")
    assert text.splitlines()[0] == "F1 frames frameMs=40 quarterMs=500 spaceMs=480 lineSpace=7.5"
    assert 'lyric f0 f10 "Me ve"' in text and 'lyric f12 f30 "two\\nlines" size=2 lift=0.5' in text
    again = f1.read(text)
    assert again.titles == plain.titles and again.space_ms == 480.0 and again.line_space == 7.5
    assert [(one.start, one.text) for one in again.lyrics] == [(0, "Me ve"), (12, "two\nlines")]
    assert f1.write(again, mode="frames") == text
    # Laid again or written again by the AI, a sheet keeps them.
    other = carry_extras(again, Sheet(notes=[]))
    assert other.titles == again.titles and other.lyrics == again.lyrics and other.line_space == 7.5


def test_the_engine_draws_lyrics_above_the_staff_and_keeps_widths_with_the_spacing_figure() -> None:
    plain = f1.read(SHEET)
    before = render_frames(plain, Options(width=80))
    plain.lyrics = [Lyric(0, 10, "Me ve"), Lyric(12, 30, "two\nlines", lift=1.0)]
    drawn = render_frames(plain, Options(width=80))
    texts = re.findall(
        r'<text class="lyric" data-lyric="(\d)" data-start="(\d+)"[^>]*>(.*?)</text>', drawn.svg
    )
    assert [(k, start) for k, start, _ in texts] == [("0", "0"), ("1", "12")]
    assert texts[1][2].count("<tspan") == 2
    # Above the top staff line (y of the system's staff top), so the system grew upwards.
    ys = [float(y) for y in re.findall(r'<tspan x="[\d.]+" y="([\d.]+)"', drawn.svg)]
    assert max(ys) < drawn.systems[0]["staff_top"]
    assert drawn.height > before.height
    # The columns do not move: the words take no width.
    assert [c["x"] for c in drawn.columns] == [c["x"] for c in before.columns]
    # Transpose figures doubles the negra; with the spacing's figure kept, nothing moves (D-18).
    renamed = f1.read(SHEET)
    renamed.space_ms, renamed.quarter_ms = 500.0, 1000.0
    assert [c["x"] for c in render_frames(renamed, Options(width=80)).columns] == [
        c["x"] for c in before.columns
    ]
    # The space between lines moves the lines apart, nothing else.
    spaced = f1.read(SHEET)
    spaced.line_space = 12.0
    assert render_frames(spaced, Options(width=80)).columns == before.columns


# ------------------------------------------------------------------ the sheet toolbox


def test_title_lines_armadura_and_line_space_are_steps_of_undo(
    client: TestClient, part: str
) -> None:
    before = sheet(client, part)
    assert before["titles"] == {} and before["lineSpace"] is None
    titled = edit(client, part, action="titles", value={"title": "  My   song ", "artist": "Me"})
    assert (
        titled["titles"] == {"title": "My song", "artist": "Me"}
        and titled["edited"] == "Title lines"
    )
    assert stored_sheet(part).record.edited
    cleared = edit(client, part, action="titles", value={"artist": ""})
    assert cleared["titles"] == {"title": "My song"}

    key = edit(client, part, action="piece-key", value=-3)
    assert key["reading"]["key"] == -3 and key["edited"] == "Armadura of the piece: 3 bemoles"
    assert edit(client, part, 400, action="piece-key", value=9)["detail"].startswith("An armadura")

    spaced = edit(client, part, action="line-space", value=10)
    assert spaced["lineSpace"] == 10 and spaced["height"] > key["height"]
    assert edit(client, part, 400, action="line-space", value=40)["detail"].startswith("The space")

    assert walk(client, part, "undo")["lineSpace"] is None
    assert walk(client, part, "undo")["reading"]["key"] == before["reading"]["key"]
    assert walk(client, part, "undo")["titles"] == {"title": "My song", "artist": "Me"}
    assert walk(client, part, "undo")["svg"] == before["svg"]


def test_lyrics_pieces_are_placed_refused_over_another_and_drawn(
    client: TestClient, part: str
) -> None:
    sheet(client, part)
    pieces = [
        {"start": 50, "end": 80, "text": "first words"},
        {"start": 100, "end": 130, "text": "more"},
    ]
    placed = edit(
        client, part, action="lyrics", value={"pieces": pieces, "label": "Place a lyrics piece"}
    )
    assert placed["edited"] == "Place a lyrics piece"
    assert [(one["start"], one["text"]) for one in placed["lyrics"]] == [
        (50, "first words"),
        (100, "more"),
    ]
    assert placed["svg"].count('class="lyric"') == 2 and 'data-lyric="1"' in placed["svg"]
    over = [*pieces, {"start": 70, "end": 90, "text": "clash"}]
    refused = edit(client, part, 400, action="lyrics", value={"pieces": over})
    assert refused["detail"] == "Another lyrics piece is already over those frames."
    sized = [{**pieces[0], "size": 99, "lift": 2}, pieces[1]]
    big = edit(client, part, action="lyrics", value={"pieces": sized, "label": "Larger"})
    assert big["lyrics"][0]["size"] == 4.2 and big["lyrics"][0]["lift"] == 2
    # A hand moved later keeps the words (the sheet laid again on the new hands).
    ref = right_run(big)[0]
    moved = client.post(
        f"/sheet/{part}/hands", params={"width": 120}, json={"notes": [ref], "hand": "left"}
    )
    assert moved.status_code == 200 and len(moved.json()["lyrics"]) == 2


def test_transpose_figures_renames_keeps_widths_and_a_new_ai_run_keeps_the_name(
    client: TestClient, part: str
) -> None:
    before = sheet(client, part)
    quarter = before["quarterMs"]
    ref = right_run(before)[0]
    fixed = edit(client, part, action="figure", notes=[ref], value=8)
    preview = client.post(
        f"/sheet/{part}/reading",
        params={"width": 120, "preview": True},
        json={"action": "figures", "value": 1},
    )
    assert preview.status_code == 200, preview.text
    shown = preview.json()
    assert shown["edited"] == "Every figure 1 step shorter" and shown["quarterMs"] == 2 * quarter
    # The preview stores nothing.
    assert sheet(client, part)["quarterMs"] == quarter

    renamed = edit(client, part, action="figures", value=1)
    assert renamed["quarterMs"] == 2 * quarter and renamed["spaceMs"] == quarter
    assert [c["x"] for c in renamed["columns"]] == [c["x"] for c in fixed["columns"]]
    figures = {r: n["figure"] for r, n in notes_of(fixed).items()}
    assert all(notes_of(renamed)[r]["figure"] in (f * 2, f) for r, f in figures.items() if f < 64)
    assert notes_of(renamed)[ref]["figure"] == 16 and notes_of(renamed)[ref]["fixed"]
    record = stored_sheet(part).record
    assert record.reference == "user" and record.quarter_ms == 2 * quarter

    # The AI run again keeps the user's name of the figures (no reference request).
    enhance(part)
    after = sheet(client, part)
    assert after["quarterMs"] == 2 * quarter and stored_sheet(part).record.reference == "user"

    back = edit(client, part, action="figures", value=-1)
    assert back["quarterMs"] == quarter and back["spaceMs"] is None


def test_transpose_notes_moves_the_notes_and_the_sheet_and_undo_puts_them_back(
    client: TestClient, part: str
) -> None:
    enhance(part)
    before = sheet(client, part)
    keys_before = sorted(e.midi_note for e in pipeline.load_note_events(part).events)
    text_before = stored_sheet(part).text
    preview = client.post(
        f"/sheet/{part}/transpose", params={"width": 120, "preview": True}, json={"semitones": 2}
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["edited"] == "Transpose 2 semitones up" and preview.json()["outside"] == 0
    assert sorted(e.midi_note for e in pipeline.load_note_events(part).events) == keys_before

    done = client.post(f"/sheet/{part}/transpose", params={"width": 120}, json={"semitones": 2})
    assert done.status_code == 200, done.text
    body = done.json()
    assert sorted(e.midi_note for e in pipeline.load_note_events(part).events) == [
        k + 2 for k in keys_before
    ]
    assert body["reading"]["key"] == before["reading"]["key"] + 2 or body["reading"][
        "key"
    ] in range(-6, 7)
    # The AI's decisions stayed on their notes: every beam group of before is still one group.
    moved = {
        f"{r.split(':')[0]}:{int(r.split(':')[1]) + 2}": n for r, n in notes_of(before).items()
    }
    for ref, note in moved.items():
        assert notes_of(body)[ref]["hand"] == note["hand"]
    groups_before = len({n["beam"] for n in before["notes"] if n["beam"] is not None})
    groups_after = len({n["beam"] for n in body["notes"] if n["beam"] is not None})
    assert groups_after == groups_before
    assert body["llm"]["enhanced"] is True

    back = walk(client, part, "undo")
    assert back["walked"] == "Transpose 2 semitones up"
    assert sorted(e.midi_note for e in pipeline.load_note_events(part).events) == keys_before
    assert stored_sheet(part).text == text_before and back["svg"] == before["svg"]


def test_a_note_added_on_the_keyboard_is_a_step(client: TestClient, part: str) -> None:
    before = sheet(client, part)
    first = before["notes"][0]
    frame = int(first["ref"].split(":")[0])
    assert first["end"] is not None and first["end"] > frame
    added = client.post(
        f"/sheet/{part}/add",
        params={"width": 120},
        json={"frame": frame, "midi": 96, "hand": "right"},
    )
    assert added.status_code == 200, added.text
    assert f"{frame}:96" in notes_of(added.json())
    twice = client.post(
        f"/sheet/{part}/add",
        params={"width": 120},
        json={"frame": frame, "midi": 96, "hand": "right"},
    )
    assert twice.status_code == 400
    assert f"{frame}:96" not in notes_of(walk(client, part, "undo"))


def test_the_sheet_on_paper_is_whole_lines_on_pages(client: TestClient, part: str) -> None:
    sheet(client, part)
    edit(
        client, part, action="lyrics", value={"pieces": [{"start": 50, "end": 80, "text": "words"}]}
    )
    answer = client.get(f"/sheet/{part}/pages", params={"width": 96, "height": 60, "first": 50})
    assert answer.status_code == 200, answer.text
    pages = answer.json()["pages"]
    assert len(pages) >= 2
    assert all(p["svg"].startswith("<svg") and "data-note" not in p["svg"] for p in pages)
    # The pages hold every line once, in order.
    assert all(a["last"] < b["first"] for a, b in zip(pages, pages[1:]))
    drawn = build.draw(build.current(part).text, 96)
    assert pages[0]["first"] == drawn["columns"][0]["frame"]
    assert pages[-1]["last"] == drawn["columns"][-1]["frame"]
    assert 'class="lyric"' in "".join(p["svg"] for p in pages)
    assert answer.json()["lyrics"][0]["text"] == "words"
