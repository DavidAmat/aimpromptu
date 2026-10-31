"""The sheet toolbox of the new sheet (implementation 03, Phase 8A): the title lines, the armadura of the piece, the
space between lines, the lyrics pieces, Transpose figures and Transpose notes (with their previews), a note added on
the keyboard panel, and the sheet on paper; Phase 8A++: lyrics blocks put anywhere, wrapped to their width, styled,
and shared between lines when their frames cross a line break. Each edit is one step of undo; Sonnet is a stand-in.
"""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

import pytest

from aitu_backend.part_sheet import build, job, store
from aitu_backend.sheet.engrave.frames import Options, render_frames
from aitu_backend.sheet.engrave.lyric_text import text_width, wrap
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


def test_the_title_lines_are_replaced_in_the_text_and_nothing_else() -> None:
    text = "F1 frames frameMs=40 quarterMs=500\nkey=0 clefs: R=treble L=bass\ntitle \"Old\"\nartist \"A\"\nlyric f1 f2 \"la\"\nf1    R: C4:4\n"
    out = f1.with_titles(text, {"title": "Nuevo", "subtitle": "Sub"})
    assert out.splitlines()[2:5] == ['title "Nuevo"', 'subtitle "Sub"', 'lyric f1 f2 "la"']
    assert out.replace('title "Nuevo"\nsubtitle "Sub"\n', "") == text.replace('title "Old"\nartist "A"\n', "")
    assert f1.read(out).titles == {"title": "Nuevo", "subtitle": "Sub"}
    assert f1.with_titles("no header", {"title": "x"}) == "no header"


def test_the_titles_stay_editable_while_the_ai_writes_the_sheet(
    client: TestClient, part: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    sheet(client, part)
    running = type("Job", (), {"id": "j", "status": "running"})()
    with monkeypatch.context() as during:
        during.setattr(job, "job_of", lambda part_id: running)
        during.setattr(job, "live", lambda part_id: None)
        # Any other edit waits for the run; the title lines do not.
        assert edit(client, part, 409, action="piece-key", value=-3)["detail"].startswith("The AI is enhancing")
        titled = edit(client, part, action="titles", value={"title": "During the run", "artist": "Me"})
        assert titled["titles"] == {"title": "During the run", "artist": "Me"}
        # The run's own save, a sheet from before the edit (no titles), keeps them.
        kept = stored_sheet(part)
        store.save(part, f1.with_titles(kept.text, {}), kept.record)
        assert f1.read(stored_sheet(part).text).titles == {"title": "During the run", "artist": "Me"}
    # No run: the sheet's own titles hold again.
    edit(client, part, action="titles", value={"artist": ""})
    kept = stored_sheet(part)
    store.save(part, f1.with_titles(kept.text, {}), kept.record)
    assert f1.read(stored_sheet(part).text).titles == {}


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


# ------------------------------------------------------------------ lyrics blocks (Phase 8A++)


def _long_sheet(columns: int = 48) -> str:
    """One right-hand negra every 6 frames: enough columns for several lines at a narrow width."""
    rows = ["F1 frames frameMs=40 quarterMs=240", "key=0 clefs: R=treble L=bass"]
    for k in range(columns):
        rows.append(f"f{6 * k:<7d} R: {'CDEFGAB'[k % 7]}5:4")
        if k + 1 < columns:
            rows.append("[]x5")
    return "\n".join(rows) + "\n"


def test_a_lyrics_block_keeps_its_place_width_and_style_through_the_format() -> None:
    plain = f1.read(SHEET)
    plain.lyrics = [
        Lyric(
            0, 10, "Me ve", at=6, dx=1.5, dy=-3.0, width=12.0, font="geist", bold=True, italic=False
        ),
        Lyric(12, 30, "plain"),
    ]
    text = f1.write(plain, mode="frames")
    assert 'lyric f0 f10 "Me ve" at=f6 dx=1.5 dy=-3 width=12 font=geist bold=1 italic=0' in text
    # A piece nobody shaped writes as before.
    assert 'lyric f12 f30 "plain"\n' in text
    again = f1.read(text)
    assert again.lyrics == plain.lyrics and again.lyrics[0].free and not again.lyrics[1].free


def test_the_words_of_a_block_wrap_to_its_width_with_the_widths_of_its_font() -> None:
    words = "my mama told me go make yourself some friends"
    assert wrap(words, None, 1.4) == [words]
    lines = wrap(words, 10.0, 1.4)
    assert len(lines) > 1 and " ".join(lines) == words
    assert all(text_width(line, 1.4) <= 10.0 for line in lines)
    # A word wider than the block keeps a line of its own; a line break of the words stays.
    assert wrap("supercalifragilistic is long", 3.0, 1.4)[0] == "supercalifragilistic"
    assert wrap("one\ntwo three", 50.0, 1.4) == ["one", "two three"]
    # Each face has its own widths: Montserrat is wider than Geist, bold wider than normal.
    assert text_width("friends", 1.4, "montserrat") > text_width("friends", 1.4, "geist")
    assert text_width("friends", 1.4, "lora", bold=True, italic=False) > text_width(
        "friends", 1.4, "lora", italic=False
    )


def test_the_engine_draws_a_block_where_it_was_put_wrapped_and_styled() -> None:
    plain = f1.read(_long_sheet(12))
    before = render_frames(plain, Options(width=120))
    words = "my mama told me go make yourself some friends"
    plain.lyrics = [
        Lyric(0, 20, words, at=18, dx=0.5, dy=-4.0, width=8.0, font="montserrat", bold=True)
    ]
    drawn = render_frames(plain, Options(width=120))
    tag = re.search(r'<text class="lyric"[^>]*>', drawn.svg).group(0)
    assert (
        'font-family="Montserrat' in tag and 'font-weight="700"' in tag and 'data-width="8"' in tag
    )
    spans = re.findall(r'<tspan x="([\d.]+)" y="([\d.-]+)">([^<]*)</tspan>', drawn.svg)
    assert len(spans) > 2 and " ".join(s[2] for s in spans) == words
    # From the column of frame 18 plus dx; its last line's baseline 4 staff spaces above the top staff line.
    column = next(c for c in drawn.columns if c["frame"] == 18)
    assert abs(float(spans[0][0]) - (column["x"] + 0.5)) < 0.01
    last = float(spans[-1][1])
    assert abs(last - (drawn.systems[0]["staff_top"] - 4.0)) < 0.01
    assert 'data-base="' in tag
    # The words take no width: no column moves.
    assert [c["x"] for c in drawn.columns] == [c["x"] for c in before.columns]


def test_a_piece_over_a_line_break_shares_its_words_by_the_width_on_each_line() -> None:
    plain = f1.read(_long_sheet())
    words = "my mama told me go make yourself some friends or you will be lonely"
    plain.lyrics = [Lyric(60, 220, words)]
    narrow = render_frames(plain, Options(width=60))
    assert narrow.lines > 2
    parts = re.findall(r'<text class="lyric" data-lyric="0"[^>]*>(.*?)</text>', narrow.svg)
    texts = [" ".join(re.findall(r">([^<]*)</tspan>", one)) for one in parts]
    assert len(texts) > 1 and " ".join(texts) == words
    assert 'data-part="1"' in narrow.svg
    # Each part starts on its own line, and no part passes the end of its line.
    systems = {s["index"]: s for s in narrow.systems}
    for one in re.finditer(r'<tspan x="([\d.]+)"', narrow.svg):
        assert float(one.group(1)) < max(s["right"] for s in systems.values())
    wide = render_frames(plain, Options(width=320))
    assert wide.svg.count('data-lyric="0"') == 1 and "data-part" not in wide.svg


def test_a_lyrics_block_is_placed_through_the_toolbox_and_a_bad_font_refused(
    client: TestClient, part: str
) -> None:
    sheet(client, part)
    block = {"start": 50, "end": 80, "text": "first words here", "at": 60, "dx": 1, "dy": -5}
    shaped = {**block, "width": 6, "font": "geist", "bold": True, "italic": False}
    placed = edit(
        client, part, action="lyrics", value={"pieces": [shaped], "label": "Move a block"}
    )
    one = placed["lyrics"][0]
    assert (one["at"], one["dx"], one["dy"], one["width"]) == (60, 1, -5, 6)
    assert (one["font"], one["bold"], one["italic"]) == ("geist", True, False)
    assert 'font-family="Geist' in placed["svg"] and 'data-width="6"' in placed["svg"]
    bad = edit(client, part, 400, action="lyrics", value={"pieces": [{**block, "font": "comic"}]})
    assert bad["detail"] == "No lyrics font 'comic'."
    # Back in the line of words: no place, no width; the style stays.
    back = {**shaped, "dy": None, "width": None}
    again = edit(client, part, action="lyrics", value={"pieces": [back]})
    assert again["lyrics"][0]["dy"] is None and again["lyrics"][0]["font"] == "geist"


def test_the_pasted_words_and_the_pool_are_kept_with_the_part(
    client: TestClient, part: str
) -> None:
    """The Lyrics tab's **Save lyrics** (moved from ``/time/{uuid}/lyrics`` in implementation 03, Phase 10)."""
    assert client.get(f"/sheet/{part}/words").json() == {"text": None, "pool": None}
    saved = client.put(
        f"/sheet/{part}/words",
        json={"text": "  first line\nsecond line  ", "pool": [" one ", "", "two"]},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json() == {"text": "first line\nsecond line", "pool": ["one", "two"]}
    assert client.get(f"/sheet/{part}/words").json() == saved.json()
    # A save without a pool keeps the pool; an empty text removes the words.
    kept = client.put(f"/sheet/{part}/words", json={"text": ""}).json()
    assert kept == {"text": None, "pool": ["one", "two"]}
    assert client.get("/sheet/nope/words").status_code == 404


def test_duplicate_writes_a_note_again_at_a_shorter_figure_and_unite_joins_them_back(
    client: TestClient, part: str
) -> None:
    # The user, 2026-10-30: Duplicate a note into a shorter figure (a negra into two corcheas), and Unite the opposite.
    enhance(part)
    before = sheet(client, part)
    # The longest of the short figures (a corchea here), so the copies are beamed.
    note = max((n for n in before["notes"] if n["figure"] in (1, 2, 4, 8) and not n["grace"]), key=lambda n: n["figure"])
    frame, midi = (int(x) for x in note["ref"].split(":"))
    live = lambda: sorted(  # noqa: E731
        round(e.start, 2) for e in pipeline.load_note_events(part).events if e.midi_note == midi and not e.removed
    )
    keys_before = live()
    target = note["figure"] * 2
    done = client.post(f"/sheet/{part}/duplicate", params={"width": 120}, json={"notes": [note["ref"]], "figure": target})
    assert done.status_code == 200, done.text
    body = done.json()
    assert body["edited"].startswith("Duplicate a note into 2 ")
    copies = [n for n in body["notes"] if int(n["ref"].split(":")[1]) == midi and n["hand"] == note["hand"]
              and frame <= int(n["ref"].split(":")[0]) < frame + 200]
    assert len([n for n in copies if n["figure"] == target]) >= 2
    if target >= 8:  # the copies of one note are one beam group
        mine = [n for n in copies if n["figure"] == target]
        assert len({n["beam"] for n in mine}) == 1 and mine[0]["beam"] is not None
    assert len(live()) == len(keys_before) + 1  # the piano matrix notation has the note again
    refused = client.post(f"/sheet/{part}/duplicate", params={"width": 120}, json={"notes": [note["ref"]], "figure": 1})
    assert refused.status_code in (400, 422)  # not shorter than the note

    pair = sorted((n for n in copies if n["figure"] == target), key=lambda n: int(n["ref"].split(":")[0]))[:2]
    united = client.post(f"/sheet/{part}/unite", params={"width": 120}, json={"notes": [n["ref"] for n in pair]})
    assert united.status_code == 200, united.text
    assert united.json()["edited"].startswith("Unite 2 ")
    assert notes_of(united.json())[pair[0]["ref"]]["figure"] == note["figure"]
    assert len(live()) == len(keys_before)
    assert client.post(f"/sheet/{part}/unite", params={"width": 120}, json={"notes": [pair[0]["ref"]]}).status_code == 400

    assert walk(client, part, "undo")["walked"].startswith("Unite")
    assert walk(client, part, "undo")["walked"].startswith("Duplicate")
    assert live() == keys_before


def test_unite_takes_any_figures() -> None:
    # The user, 2026-10-30: a figure is never a reason to refuse Unite; the sheet has no puntillos.
    from aitu_backend.part_sheet.edits import united_figure

    assert united_figure(0.5 + 0.5, 1.0) == 4  # two corcheas: a negra
    assert united_figure(0.25 + 0.25 + 0.5, 0.9) == 4  # two semicorcheas and a corchea: a negra
    assert united_figure(0.5 + 1, 1.1) == 4  # a corchea and a negra, played short: a negra
    assert united_figure(0.5 + 1, 1.7) == 2  # played long: a blanca
    assert united_figure(4 + 4, 8) == 1  # longer than a redonda: a redonda


def test_the_alteration_of_a_note_is_written_as_the_user_chooses(client: TestClient, part: str) -> None:
    # The user, 2026-10-30: a La# in a key of sharps written as Sib, by hand; the key stays the same.
    from aitu_backend.part_sheet.reading import spelled_as

    assert spelled_as(70, 1) == ("A", 4) and spelled_as(70, -1) == ("B", 4)
    assert spelled_as(60, 1) == ("B", 3) and spelled_as(60, 0) == ("C", 4) and spelled_as(61, 0) is None
    enhance(part)
    before = sheet(client, part)
    note = before["notes"][0]
    midi = int(note["ref"].split(":")[1])
    sharp = client.post(f"/sheet/{part}/reading", params={"width": 120},
                        json={"action": "alter", "notes": [note["ref"]], "value": 1 if spelled_as(midi, 1) else -1})
    assert sharp.status_code == 200, sharp.text
    pitch = notes_of(sharp.json())[note["ref"]]["pitch"]
    assert ("#" in pitch) or ("b" in pitch[1:]), pitch
    assert client.post(f"/sheet/{part}/reading", params={"width": 120},
                       json={"action": "alter", "notes": [note["ref"]], "value": 7}).status_code == 400
    assert notes_of(walk(client, part, "undo"))[note["ref"]]["pitch"] == note["pitch"]
