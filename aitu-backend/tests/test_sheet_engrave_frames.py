"""The engine of the new sheet, without compases (implementation 03, Phase 3).

The frames engine draws an F1 frames sheet: one x per column for both hands, grace notes before their note,
the signs of ``frames.printed_signs``, armadura and clef changes inside a line, empty time drawn shorter than its
time, line breaks that do not cut beam groups, and one segment drawn with the line breaks of the whole sheet.
"""

from __future__ import annotations

import re
from collections import Counter

from aitu_backend.sheet.engrave import frames as engine
from aitu_backend.sheet.engrave import layout
from aitu_backend.sheet.engrave.spacing import load
from aitu_backend.sheet.sheet import f1
from aitu_backend.sheet.sheet.frames import printed_signs

SHEET = """F1 frames frameMs=40 quarterMs=500
key=1# clefs: R=treble L=bass
f0       L: G2,D3,G3:2  R: B4:8 b1
f6       R: C5:8 b1
f12      R: D5:8 b1
f18      R: G5:4 tr
f30      L: C3:4  R: A5:16 grace/
f31      R: B5,E6:8 8va
f40      R: G4,B4:16 grace/
f42      R: clef=bass G2,G3:4
f60      L: clef=treble C4,E4:4  R: clef=treble D5:4
f120 key=0
f120     L: clef=bass C3:4  R: C#5:4
f300     L: Bb2:4  R: D5:8 b2
f306     L: G3:8 b2
f312     R: E5:1
"""


def heads(eng, ref: str) -> list:
    """The noteheads of one note (``data-note``) in the drawing: (system, staff, x, y)."""
    return [
        (si, p.staff, p.data[1], p.data[2])
        for si, s in enumerate(eng.systems)
        for p in s.prims
        if p.kind == "g" and p.ref == ref
    ]


def glyphs(eng, name: str) -> list:
    return [
        (p.staff, p.data[1], p.data[2])
        for s in eng.systems
        for p in s.prims
        if p.kind == "g" and p.data[0] == name
    ]


def stream(columns: int, gap: int = 6) -> str:
    """A long sheet: corcheas in beam groups of four in the right hand, a negra every group in the left hand."""
    lines = ["F1 frames frameMs=40 quarterMs=500", "key=0 clefs: R=treble L=bass"]
    for k in range(columns):
        f = k * gap + (k // 4) * 4  # a little pause after each group
        left = "  L: C3:4" if k % 4 == 0 else ""
        lines.append(f"f{f}{left}  R: {'CDEFGAB'[k % 7]}5:8 b{k // 4 + 1}")
    return "\n".join(lines) + "\n"


def test_every_note_is_drawn_once_and_both_hands_share_the_column_x() -> None:
    sheet = f1.read(SHEET)
    rendered = engine.render_frames(SHEET)
    drawn = Counter(re.findall(r'data-note="([^"]+)"', rendered.svg))
    assert drawn == Counter(f"{n.frame}:{n.midi}" for n in sheet.notes)
    # columns: the frames of the main notes only (the grace notes of f30 and f40 are drawn before their note)
    assert [c["frame"] for c in rendered.columns] == [
        0,
        6,
        12,
        18,
        30,
        31,
        42,
        60,
        120,
        300,
        306,
        312,
    ]
    eng = engine.engrave_frames(sheet)
    for ref_r, ref_l in (("0:71", "0:43"), ("60:74", "60:60"), ("120:73", "120:48")):
        (_, sr, xr, _), (_, sl, xl, _) = heads(eng, ref_r)[0], heads(eng, ref_l)[0]
        assert (sr, sl) == (1, 2) and abs(xr - xl) < 1e-9


def test_the_printed_signs_are_rules_1_and_7() -> None:
    sheet = f1.read(SHEET)
    lay = engine.plan(sheet)
    signs = printed_signs(lay.sheet)
    for col in lay.columns:
        for c in col.chords:
            for h in c.heads + [h for slot in c.grace_heads for h in slot]:
                want = signs.get(id(h.note))
                assert h.acc == (engine.SIGN_ALTER[want] if want else None)
    assert {
        (h.note.step, h.acc)
        for col in lay.columns
        for c in col.chords
        for h in c.heads
        if h.acc is not None
    } == {
        ("C", 1),
        ("B", -1),
    }


def test_a_grace_note_keeps_the_clef_it_sounds_in() -> None:
    # the right hand plays G4-B4 as grace notes (treble clef), then changes to the bass clef for G2-G3
    eng = engine.engrave_frames(f1.read(SHEET))
    _, _, xg, yg = heads(eng, "40:67")[0]
    _, _, xm, _ = heads(eng, "42:43")[0]
    assert yg == layout.y_of(
        2
    )  # G4 on the second line of the treble staff, not above the bass staff
    clefs = [x for staff, x, _ in glyphs(eng, "fClefChange") if staff == 1]
    assert len(clefs) == 1 and xg < clefs[0] < xm


def test_a_grace_note_between_two_clef_changes_overlaps_neither() -> None:
    # Superestrella (cover), Phase 4: the left hand changes to the bass clef for a grace note B3, then back to the
    # treble clef for its chord; the two clefs and the grace note stand apart, in that order
    sheet = f1.read(
        "F1 frames frameMs=40 quarterMs=500\nkey=5# clefs: R=treble L=treble\n"
        "f0       L: B4,D#5:4  R: F#5:4\n"
        "f19      L: clef=bass B3:8 grace/\n"
        "f20      L: clef=treble B4,D#5:2  R: B5:4\n"
    )
    eng = engine.engrave_frames(sheet)
    bass = [x for staff, x, _ in glyphs(eng, "fClefChange") if staff == 2]
    treble = [x for staff, x, _ in glyphs(eng, "gClefChange") if staff == 2]
    _, _, xg, _ = heads(eng, "19:59")[0]
    _, _, xm, _ = heads(eng, "20:71")[0]
    assert len(bass) == 1 and len(treble) == 1
    width = engine.box("fClefChange").width
    assert bass[0] + width <= xg and xg < treble[0] < xm


def test_clef_changes_where_the_hand_plays_nothing_are_one_clef_or_none() -> None:
    # 7 Years, the user's copy (2026-10-26): the left hand changes to the treble clef where it plays nothing and back
    # to the bass clef at its next chord; both clefs were drawn on one spot. They give back the clef in force: none.
    back = engine.engrave_frames(
        f1.read(
            "F1 frames frameMs=40 quarterMs=500\nkey=0 clefs: R=treble L=bass\n"
            "f0       L: C3:4  R: E5:4\n"
            "f10      L: clef=treble  R: F5:4\n"
            "f20      L: clef=bass E3,G3:4  R: G5:4\n"
        )
    )
    assert not glyphs(back, "gClefChange") and not glyphs(back, "fClefChange")
    # Two changes that lead somewhere else are one clef, the last.
    on = engine.engrave_frames(
        f1.read(
            "F1 frames frameMs=40 quarterMs=500\nkey=0 clefs: R=treble L=bass\n"
            "f0       L: C3:4  R: E5:4\n"
            "f10      L: clef=treble  R: F5:4\n"
            "f15      L: clef=bass  R: A5:4\n"
            "f20      L: clef=treble E4,G4:4  R: G5:4\n"
        )
    )
    assert len([g for g in glyphs(on, "gClefChange") if g[0] == 2]) == 1 and not glyphs(
        on, "fClefChange"
    )


def test_an_armadura_change_cancels_the_old_signs_on_both_staves() -> None:
    lay = engine.plan(f1.read(SHEET))
    col = next(c for c in lay.columns if c.frame == 120)
    assert col.key_change == (1, 0)
    eng = engine.draw(lay)
    naturals = glyphs(eng, "accidentalNatural")
    assert {s for s, _, _ in naturals} == {1, 2} and len({round(x, 6) for _, x, _ in naturals}) == 1
    lined = engine.draw(engine.plan(f1.read(SHEET), engine.Options(key_line=True)))
    assert len(lined.systems[0].prims) == len(eng.systems[0].prims) + 2  # the thin double line


def test_empty_time_is_drawn_shorter_than_its_time() -> None:
    # 7.2 s from f120 to the next column, 14.4 reference negras: the time beyond a blanca keeps 30 % of its width
    model = load()
    lay = engine.plan(f1.read(SHEET))
    i = next(k for k, c in enumerate(lay.columns) if c.frame == 120)
    full = engine.plan(f1.read(SHEET), engine.Options(silence=1.0)).nat[i]
    assert (
        abs(full - (model.gap(7.2 / 0.5) + model.accidental)) < 1e-9
    )  # the next column prints a bemol
    assert (
        model.gap(2.0) < lay.nat[i] < 0.65 * full
    )  # more than a blanca's gap: the pause is still seen
    # the figures are not read: the same gap after a redonda
    held = f1.read(SHEET.replace("C3:4  R: C#5:4", "C3:1  R: C#5:1"))
    assert engine.plan(held).nat[i] == lay.nat[i]


def test_line_breaks_keep_beam_groups_whole_and_fill_the_width() -> None:
    text = stream(160)
    opts = engine.Options(width=60)
    lay = engine.plan(f1.read(text), opts)
    assert len(lay.lines) > 3
    group_of = {}
    for bid, members in lay.beams.items():
        for c in members:
            group_of[(c.staff, int(c.time))] = bid
    for i, j, _ in lay.lines[1:]:
        before = group_of.get((1, lay.columns[i - 1].frame))
        assert before is None or before != group_of.get((1, lay.columns[i].frame))
    eng = engine.draw(lay)
    for s in eng.systems[:-1]:
        assert abs(s.width - opts.width) < 1e-6


def test_one_segment_is_drawn_with_the_line_breaks_of_the_whole_sheet() -> None:
    text = stream(160)
    opts = engine.Options(width=60)
    lay = engine.plan(f1.read(text), opts)
    whole = engine.draw(lay)
    k = 2
    i, j, _ = lay.lines[k]
    part = engine.render_frames(
        text, opts, segment=(lay.columns[i].frame, lay.columns[i].frame + 1)
    )
    assert [s["index"] for s in part.systems] == [k]
    alone = engine.draw(engine.plan(f1.read(text), opts), [k])
    assert [p.data for p in alone.systems[0].prims] == [p.data for p in whole.systems[k].prims]
    assert [c["frame"] for c in part.columns] == [c.frame for c in lay.columns[i:j]]


def test_a_beam_across_the_hands_and_the_ornaments_draw() -> None:
    eng = engine.engrave_frames(f1.read(SHEET))
    assert any(
        p.kind == "p" and p.staff == 0 and p.cls == "beam" for s in eng.systems for p in s.prims
    )
    assert glyphs(eng, "ornamentTrill") and glyphs(eng, "ottava")


def test_a_bars_sheet_is_refused() -> None:
    bars = f1.read("F1 bars\nclefs: R=treble L=bass\nbar 1 meter=4/4 key=0\n1 R: C5:1\n")
    try:
        engine.plan(bars)
    except ValueError:
        return
    raise AssertionError("a bars sheet must be refused")
