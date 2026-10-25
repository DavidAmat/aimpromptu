"""The engine of the new sheet: an F1 frames sheet -> SVG, without compases (implementation 03, Phase 3).

The bars engine (:mod:`aitu_backend.sheet.engrave.layout`) needs compases for its voices, rests, accidentals,
spacing and line breaks. The new sheet has none (plan section 3.1), so this module lays it out again and reuses the
bars engine for the look of every element (noteheads, stems, flags, beams, grace notes, ornaments, 8va, ledger
lines, clefs, armaduras, the brace: Verovio's drawing rules and the Leipzig glyphs).

* **Columns.** One x per drawn column (``Note.frame``) for both hands: what sounds together is on one vertical line.
  A grace note is drawn before the next note of its hand, not at its own column. Notes ``covered`` by an ornament
  (``orn``) are not drawn. One hand has one voice: no rests, no voices, no compás lines, no meter, no bar numbers.
* **Spacing** (plan section 3.2). The gap after a column comes from the time to the next column in either hand,
  through the measured spacing model (``spacing_model.json``) with the reference figure as its negra: many short
  notes in one hand widen the stretch for both hands. When no hand starts a note for longer than a blanca, the time
  beyond the blanca keeps only ``Options.silence`` of the width it would add (empty time, also after a redonda).
  Figures are not durations and are not read by the spacing.
* **Accidentals**: the signs of :func:`aitu_backend.sheet.sheet.frames.printed_signs` (rule 1, every note outside
  the armadura every time; rule 7, the courtesy sign after a becuadro). An armadura change prints the cancelling
  becuadros and the new armadura before its column; a clef change prints a small clef before its column.
* **Line breaks** only where no beam group is cut; from the columns that fill a line to at least ``Options.fill``,
  the one after the longest pause (time between two columns). A line starts at a pause again when a change moved
  the lines before it, so a changed segment moves the rest of the sheet little (Phase 5 redraws one segment).

:func:`render_frames` draws a whole song or the systems of one segment, with the cursor map and note ids.
"""

from __future__ import annotations

import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from fractions import Fraction

from aitu_backend.sheet.engrave import layout as L
from aitu_backend.sheet.engrave.glyphs import box
from aitu_backend.sheet.engrave.layout import Chord, Engraving, Head, Pen, System
from aitu_backend.sheet.engrave.spacing import SpacingModel, load
from aitu_backend.sheet.engrave.svg import to_svg
from aitu_backend.sheet.sheet import f1
from aitu_backend.sheet.sheet import frames as frames_mod
from aitu_backend.sheet.sheet.data import FRAME_MS, Note, Sheet

__all__ = ["Options", "Layout", "Rendered", "draw", "engrave_frames", "plan", "render_frames"]

SIGN_ALTER = {"#": 1, "b": -1, "n": 0}
KEY_PAD = (
    1.5  # staff spaces before an armadura change inside a line: it must not read as an accidental
)
KEY_AFTER = 1.0
LONG_GAP = 2.0  # reference negras (a blanca): time beyond it between two columns is empty time
CLEF_PAD = 0.3  # staff spaces before a clef change inside a line
CLEF_AFTER = 0.6  # and between it and the notes it changes
DEFAULT_QUARTER_MS = 500.0


@dataclass
class Options:
    width: float = 130.0  # staff width in staff spaces
    model: SpacingModel | None = None
    clearance: float | None = None  # override model.clearance
    min_staff_gap: float = 6.0
    system_gap: float = 5.0
    justify_last: bool = False
    silence: float = (
        0.3  # share of its width that empty time keeps (time beyond a blanca between two columns)
    )
    fill: float = 0.8  # a line breaks at its longest pause once it is this full
    merge_unisons: bool = True
    quarter_ms: float | None = None  # the reference figure (default: the sheet's)
    key_line: bool = False  # a thin double line before an armadura change inside a line


@dataclass
class Column:
    frame: int
    chords: list[Chord]
    lefts: dict[int, float] = field(
        default_factory=dict
    )  # per staff, clef and armadura changes included
    rights: dict[int, float] = field(default_factory=dict)
    note_left: dict[int, float] = field(default_factory=dict)  # per staff: accidentals, grace notes
    clef_changes: list[tuple[int, str]] = field(
        default_factory=list
    )  # (staff, clef) drawn before the column
    key_change: tuple[int, int] | None = None  # (old, new) armadura drawn before the column
    key_w: float = 0.0
    accidental: bool = False
    x: float = 0.0

    @property
    def ms(self) -> float:
        return self.frame * FRAME_MS

    @property
    def left(self) -> float:
        return max(self.lefts.values(), default=0.0)

    @property
    def right(self) -> float:
        return max(self.rights.values(), default=L.HEAD_W)


@dataclass
class Layout:
    """Everything before the drawing: the columns with their room, the gaps, the systems (column ranges)."""

    sheet: Sheet
    columns: list[Column]
    nat: list[float]  # natural gap after each column (the last column: to the end of the line)
    mins: list[float]  # the least gap the glyphs need
    ends: list[tuple[float, float]]  # (natural, least) room after a column that ends a line
    lines: list[tuple[int, int, float]]  # (first column, end column, justification e)
    beams: dict[int, list[Chord]]
    clefs_at: dict[int, list[tuple[int, str]]]  # staff -> [(frame, clef)]
    key_at: object
    opts: Options


# ------------------------------------------------------------------ the chords


def merge_unisons(sheet: Sheet) -> Sheet:
    """One notehead for one pitch in one column of one hand (the user's rule, research phase 11): the note of the
    larger beam group is kept, else the shorter figure. Grace notes and ``orn`` notes stay as they are.
    """
    size = Counter(n.beam for n in sheet.notes if n.beam is not None)
    best: dict[tuple, tuple] = {}
    for i, n in enumerate(sheet.notes):
        if n.grace or n.covered:
            continue
        k = (n.frame, n.staff, n.midi)
        rank = (size.get(n.beam, 0), n.figure or 0)
        if k not in best or rank > best[k][0]:
            best[k] = (rank, i)
    keep = {i for _, i in best.values()}
    drop = [i for i, n in enumerate(sheet.notes) if not (n.grace or n.covered) and i not in keep]
    if not drop:
        return sheet
    dropped = set(drop)
    return replace(sheet, notes=[n for i, n in enumerate(sheet.notes) if i not in dropped])


def _clef_timeline(sheet: Sheet) -> dict[int, list[tuple[int, str]]]:
    tl = {s: [(-(10**9), sheet.clefs.get(s, L.DEFAULT_CLEF[s]))] for s in (1, 2)}
    for f, s, c in sorted(sheet.clef_changes, key=lambda c: c[0]):
        if s in tl:
            tl[s].append((int(f), c))
    return tl


def _clef_at(tl: dict[int, list[tuple[int, str]]], staff: int, frame: int) -> str:
    clef = tl[staff][0][1]
    for f, c in tl[staff]:
        if f <= frame:
            clef = c
        else:
            break
    return clef


def _chords(sheet: Sheet, signs: dict[int, str], tl) -> list[Chord]:
    """One chord per hand and drawn column; grace notes join the next chord of their hand (one slot per column)."""
    out: list[Chord] = []
    for staff in (1, 2):
        mains: dict[int, list[Note]] = defaultdict(list)
        graces: dict[int, list[Note]] = defaultdict(list)
        for n in sheet.notes:
            if n.staff != staff or n.covered or n.frame is None:
                continue
            (graces if n.grace else mains)[n.frame].append(n)
        last = max(mains, default=None)
        for g in sorted(graces):  # a grace note with no note after it is drawn as a note
            if last is None or g > last:
                mains[g] = graces.pop(g)
        order = sorted(mains)
        chords: dict[int, Chord] = {}
        for f in order:
            notes = sorted(mains[f], key=lambda n: n.midi)
            figs = Counter(n.figure or 4 for n in notes)
            fig = min(figs, key=lambda k: (-figs[k], k))
            beam = next((n.beam for n in notes if n.beam is not None), None) if fig >= 8 else None
            orn: set[str] = set()
            for n in notes:
                orn.update(n.ornaments)
            c = Chord(
                staff,
                0,
                0,
                Fraction(f),
                Fraction(1),
                fig,
                0,
                None,
                beam,
                None,
                notes,
                clef=_clef_at(tl, staff, f),
                ornaments=orn,
                ottava=notes[0].ottava or 0,
            )
            c.heads = [_head(n, c.clef, signs) for n in notes]
            chords[f] = c
        for g in sorted(graces):
            target = next(f for f in order if f > g)
            c = chords[target]
            slot = sorted(graces[g], key=lambda n: n.midi)
            c.graces.append(slot)
            c.grace_heads.append([_head(n, _clef_at(tl, staff, g), signs) for n in slot])
            c.grace_frames = getattr(c, "grace_frames", []) + [g]
        out += chords.values()
    return out


def _graces_before(col: "Column", staff: int, frame: int) -> bool:
    return any(
        g < frame for c in col.chords if c.staff == staff for g in getattr(c, "grace_frames", [])
    )


def _main_left(c: Chord) -> float:
    """The room a chord needs on its left without its grace notes."""
    bare = replace(c, graces=[], grace_heads=[])
    L._extents(bare)
    return bare.left


def _clef_w(clef: str) -> float:
    return box("gClefChange" if clef != "F4" else "fClefChange").width + CLEF_PAD + CLEF_AFTER


def _head(n: Note, clef: str, signs: dict[int, str]) -> Head:
    s = signs.get(id(n))
    return Head(n, L.pos_of(n, clef), acc=SIGN_ALTER[s] if s else None)


# ------------------------------------------------------------------ armadura changes


def _key_steps(fifths: int) -> list[str]:
    """The altered steps of an armadura, in the order they are printed."""
    if fifths > 0:
        return list(L.SHARP_ORDER[:fifths])
    return list(L.SHARP_ORDER[::-1][:-fifths]) if fifths < 0 else []


def _cancelled(old: int, new: int) -> list[str]:
    """The steps of the old armadura that the new one does not alter the same way: they print a becuadro."""
    keep = L.key_alters(new)
    sign = 1 if old > 0 else -1
    return [s for s in _key_steps(old) if keep[s] != sign]


def _key_change_width(old: int, new: int) -> float:
    nat = box("accidentalNatural").width + 0.2
    return len(_cancelled(old, new)) * nat + L._key_sig_width(new) + KEY_PAD + KEY_AFTER


def _draw_key_change(pen: Pen, staff: int, clef: str, old: int, new: int, x: float) -> None:
    shift = -2 if clef == "F4" else 0
    old_pos = L.SHARP_POS if old > 0 else L.FLAT_POS
    steps = _key_steps(old)
    for s in _cancelled(old, new):
        pen.g(staff, "accidentalNatural", x, L.y_of(old_pos[steps.index(s)] + shift))
        x += box("accidentalNatural").width + 0.2
    L._draw_key(pen, staff, clef, new, x)


# ------------------------------------------------------------------ the plan: columns, gaps, lines


def plan(sheet: Sheet, opts: Options | None = None) -> Layout:
    """The columns of a frames sheet with their room, the natural and least gaps, and the line breaks."""
    opts = opts or Options()
    L._metrics()
    if sheet.bars:
        raise ValueError("engrave_frames draws a frames sheet (no compases)")
    if opts.merge_unisons:
        sheet = merge_unisons(sheet)
    model = opts.model or load()
    clearance = opts.clearance if opts.clearance is not None else model.clearance
    quarter = opts.quarter_ms or sheet.quarter_ms or DEFAULT_QUARTER_MS
    signs = frames_mod.printed_signs(sheet)
    tl = _clef_timeline(sheet)
    key_at = frames_mod.key_at(sheet)
    chords = _chords(sheet, signs, tl)
    by_staff: dict[tuple[int, int], list[Chord]] = {(0, 1): [], (0, 2): []}
    for c in chords:
        by_staff[(0, c.staff)].append(c)
    for cs in by_staff.values():
        cs.sort(key=lambda c: c.time)
    beams = L._stems(by_staff)
    for c in chords:
        L._extents(c)
    cols_of: dict[int, list[Chord]] = defaultdict(list)
    for c in chords:
        cols_of[int(c.time)].append(c)
    columns = []
    for f in sorted(cols_of):
        col = Column(f, cols_of[f])
        for c in col.chords:
            col.note_left[c.staff] = max(col.note_left.get(c.staff, 0.0), c.left - c.shift)
            col.rights[c.staff] = max(col.rights.get(c.staff, 0.0), c.right + c.shift)
        col.accidental = any(h.acc is not None for c in col.chords for h in c.heads)
        columns.append(col)
    frames = [col.frame for col in columns]
    # clef changes: before the first column of that hand at or after the change; when grace notes of that column
    # sound before the change, the clef goes between them and their note (they keep the clef they sound in)
    for f, s, clef in sorted(sheet.clef_changes, key=lambda c: c[0]):
        target = next((col for col in columns if col.frame >= f and s in col.note_left), None)
        if target is None or (target is columns[0] and not _graces_before(target, s, f)):
            continue
        chord = next(c for c in target.chords if c.staff == s)
        if _graces_before(target, s, f):
            chord.inner_clef = clef
            chord.main_left = _main_left(chord)
            chord.left += 0.3
        target.clef_changes.append((s, clef))
    # armadura changes: before the first column at or after the change
    for f, k in sorted(sheet.key_changes):
        target = next((col for col in columns if col.frame >= f), None)
        old = key_at(f - 1)
        if target is not None and target is not columns[0] and k != old:
            target.key_change = (old, k)
            target.key_w = _key_change_width(old, k)
    for col in columns:
        note_left = max(col.note_left.values(), default=0.0)
        for s in (1, 2):
            base = col.note_left.get(s, 0.0)
            if col.key_change:
                base = note_left + col.key_w
            # every clef change of the hand at this column: two when a grace note sounds in one clef and its
            # note in another (one before the grace notes, one between them and their note)
            base += sum(_clef_w(c) for st, c in col.clef_changes if st == s)
            if base or s in col.note_left:
                col.lefts[s] = base
    # the gaps: the time to the next column in either hand (figures are not read); a long gap is shortened
    nat, mins, ends = [], [], []
    for i, col in enumerate(columns):
        nxt = columns[i + 1] if i + 1 < len(columns) else None
        g = _gap(model, ((nxt.ms - col.ms) if nxt else quarter) / quarter, opts.silence)
        ends.append((model.to_barline * g + L.HEAD_W / 2, col.right + 0.6))
        if nxt is not None:
            need = max(col.rights.get(s, 0.0) + nxt.lefts.get(s, 0.0) for s in (1, 2))
            nat.append(g + (model.accidental if nxt.accidental else 0.0))
            mins.append(max(need, L.HEAD_W) + clearance)
        else:
            nat.append(ends[-1][0])
            mins.append(ends[-1][1])
    lay = Layout(sheet, columns, nat, mins, ends, [], beams, tl, key_at, opts)
    lay.lines = _break_lines(lay, frames)
    return lay


def _gap(model: SpacingModel, quarters: float, silence: float) -> float:
    """The natural gap after a column whose next column comes ``quarters`` reference negras later: the measured
    spacing up to a blanca, then ``silence`` of the width the rest of the time would add (empty time, plan section
    3.2: no hand starts a note in it, whatever still sounds)."""
    if quarters <= LONG_GAP:
        return model.gap(quarters)
    return model.gap(LONG_GAP) + silence * (model.gap(quarters) - model.gap(LONG_GAP))


def _header(lay: Layout, i: int) -> float:
    return L.header_width({}, lay.key_at(lay.columns[i].frame), None)


def _first_lead(col: Column) -> float:
    return max(1.2, max(col.note_left.values(), default=0.0) + 0.8)


def _line_width(lay: Layout, i: int, j: int, e: float = 0.0) -> float:
    """Width of the line of columns [i, j): header, lead, the gaps inside, the room after its last column."""
    w = _header(lay, i) + _first_lead(lay.columns[i])
    for k in range(i, j - 1):
        w += max(lay.nat[k] + e, lay.mins[k])
    end_nat, end_min = lay.ends[j - 1]
    return w + max(end_nat + e, end_min)


def _break_lines(lay: Layout, frames: list[int]) -> list[tuple[int, int, float]]:
    n = len(lay.columns)
    if not n:
        return []
    index = {f: i for i, f in enumerate(frames)}
    # a break before column j: (beam groups it cuts, of which with a part of one note)
    cost = [[0, 0] for _ in range(n + 1)]
    for members in lay.beams.values():
        idx = sorted({index[int(c.time)] for c in members})
        for k, j in enumerate(idx[1:], start=1):
            for jj in range(idx[k - 1] + 1, j + 1):
                cost[jj][0] += 1
                cost[jj][1] += k == 1 or k == len(idx) - 1
    width = lay.opts.width
    room = [max(a, b) for a, b in zip(lay.nat, lay.mins)]  # gaps at their natural width
    end = [max(a, b) for a, b in lay.ends]
    out = []
    i = 0
    while i < n:
        start = _header(lay, i) + _first_lead(lay.columns[i])
        widths = {i + 1: start + end[i]}  # line [i, k) -> natural width
        inner = start
        j = i + 1
        while j < n:
            inner += room[j - 1]
            if inner + end[j] > width:
                break
            j += 1
            widths[j] = inner + end[j - 1]
        if j < n:
            cand = range(i + 1, j + 1)
            full = [k for k in cand if widths[k] >= lay.opts.fill * width] or [j]
            least = min((cost[k][1], cost[k][0]) for k in full)
            if least != (0, 0):  # no free place in the full part: the latest free one if any
                free = [k for k in cand if cost[k] == [0, 0]]
                if free and widths[free[-1]] >= 0.5 * width:
                    full, least = free[-1:], (0, 0)
            full = [k for k in full if (cost[k][1], cost[k][0]) == least]
            j = max(full, key=lambda k: (lay.columns[k].ms - lay.columns[k - 1].ms, k))
        last = j >= n
        natural = widths[j]
        if last and not lay.opts.justify_last and natural < 0.8 * width:
            e = 0.0
        else:
            lo, hi = -10.0, 60.0
            if _line_width(lay, i, j, lo) > width:
                e = lo
            else:
                for _ in range(50):
                    mid = (lo + hi) / 2
                    if _line_width(lay, i, j, mid) > width:
                        hi = mid
                    else:
                        lo = mid
                e = lo
        out.append((i, j, e))
        i = j
    return out


# ------------------------------------------------------------------ drawing


def _draw_system(lay: Layout, si: int) -> tuple[System, list[dict]]:
    i, j, e = lay.lines[si]
    opts = lay.opts
    cols = lay.columns[i:j]
    first = cols[0]
    key = lay.key_at(first.frame)
    header = _header(lay, i)
    sysm = System([], opts.width, header)
    pen = Pen()
    for staff in (1, 2):
        clef = _clef_at(lay.clefs_at, staff, first.frame)
        if staff in first.note_left:  # a clef change at the first column is the header's clef
            clef = next((c.clef for c in first.chords if c.staff == staff), clef)
        if clef == "F4":
            pen.g(staff, "fClef", 0.8, L.y_of(6))
        else:
            pen.g(staff, "gClef", 0.8, L.y_of(2))
        L._draw_key(pen, staff, clef, key, 0.8 + box("gClef").width + 0.8)
    x = header + _first_lead(first)
    for k, col in enumerate(cols):
        col.x = x
        for c in col.chords:
            c.x = x
        if k + 1 < len(cols):
            x += max(lay.nat[i + k] + e, lay.mins[i + k])
        else:
            x += max(lay.ends[i + k][0] + e, lay.ends[i + k][1])
    last = j == len(lay.columns)
    end_x = x if (e == 0.0 and last and not opts.justify_last) else max(x, opts.width)
    sysm.width = end_x
    sys_chords = [c for col in cols for c in col.chords]
    # armadura and clef changes inside the line
    key_lines = []
    for col in cols[1:]:
        note_left = max(col.note_left.values(), default=0.0)
        if col.key_change:
            old, new = col.key_change
            for staff in (1, 2):
                clef = _clef_at(lay.clefs_at, staff, col.frame)
                _draw_key_change(
                    pen, staff, clef, old, new, col.x - note_left - col.key_w + KEY_PAD
                )
            if opts.key_line:
                key_lines.append(col.x - note_left - col.key_w + 0.3)
        for s, clef in col.clef_changes:
            name = "gClefChange" if clef != "F4" else "fClefChange"
            inner = next(
                (c for c in col.chords if c.staff == s and getattr(c, "inner_clef", None)), None
            )
            last = [c for st, c in col.clef_changes if st == s][-1] == clef
            if inner is not None and last:  # between the grace notes and their note
                left = inner.main_left
            elif inner is not None:  # before the grace notes, which moved left of the inner clef
                left = col.note_left.get(s, 0.0) + _clef_w(inner.inner_clef) + 0.3
            else:
                left = note_left + col.key_w if col.key_change else col.note_left.get(s, 0.0)
            pen.g(
                s,
                name,
                col.x - left - box(name).width - CLEF_AFTER,
                L.y_of(2 if clef != "F4" else 6),
            )
    for c in sys_chords:
        if getattr(c, "inner_clef", None) and c.graces:
            graces, heads = c.graces, c.grace_heads
            c.graces, c.grace_heads = [], []
            L._draw_chord(pen, c)
            c.graces, c.grace_heads = graces, heads
            x = c.x
            c.x -= _clef_w(c.inner_clef) + 0.3
            L._draw_graces(pen, c)
            c.x = x
        else:
            L._draw_chord(pen, c)
        if not c.beamed:
            L._draw_unbeamed_stem(pen, c)
    L._vrv_ledgers(pen, sys_chords)
    here = {id(c) for c in sys_chords}
    cross_groups = []
    for bid in sorted({c.beam for c in sys_chords if c.beamed}):
        members = [c for c in lay.beams.get(bid, []) if id(c) in here]
        if len(members) < 2:
            for c in members:
                c.beamed = False
                L._extents(c)
                L._draw_unbeamed_stem(pen, c)
            continue
        if members[0].cross:
            cross_groups.append(members)
            continue
        L._draw_beam_group(pen, members, lambda c: None, [])
    for c in sys_chords:
        if not c.cross:
            L._ornaments(pen, c)
            L._fingers(pen, c)
    L._ottavas(pen, sys_chords)
    below, above = 4.0, 0.0
    for p in pen.prims:
        lo, hi = L._prim_yrange(p)
        if p.staff == 1:
            below = max(below, hi)
        elif p.staff == 2:
            above = min(above, lo)
    gap = max(opts.min_staff_gap, (below - 4.0) + (-above) + 2.0)
    for members in cross_groups:
        gap = max(gap, L._cross_need(members))
    sysm.gap = gap
    for members in cross_groups:
        L._draw_cross_beam(pen, members, 4 + gap, lambda c: None)
    for c in sys_chords:
        if c.cross:
            L._ornaments(pen, c)
            L._fingers(pen, c)
    for staff in (1, 2):
        for k in range(5):
            pen.l(staff, 0.0, k * 1.0, end_x + L.BAR_W / 2, k * 1.0, L.STAFF_LINE_W)
    bass_bottom = 4 + gap + 4
    pen.l(0, L.BAR_W / 2, 0.0, L.BAR_W / 2, bass_bottom, L.BAR_W)  # the line that joins the staves
    for kx in key_lines:
        for dx in (0.0, 0.45):
            pen.l(0, kx + dx, 0.0, kx + dx, bass_bottom, L.BAR_W * 0.6)
    L._vrv_brace(pen, bass_bottom)
    sysm.prims = pen.prims
    ys = []
    for p in pen.prims:
        lo, hi = L._prim_yrange(p)
        off = 4 + gap if p.staff == 2 else 0.0
        ys += [lo + off, hi + off]
    sysm.ymin, sysm.ymax = min(ys + [0.0]), max(ys + [bass_bottom])
    rows = [{"system": si, "frame": col.frame, "x": col.x, "ms": col.ms} for col in cols]
    return sysm, rows


def draw(lay: Layout, systems: list[int] | None = None) -> Engraving:
    """The systems of a plan (all, or the given ones, stacked from the top) as an :class:`Engraving`; its
    ``columns`` are one row per drawn column: system, frame, x (notehead left edge), ms."""
    picked = range(len(lay.lines)) if systems is None else systems
    drawn, rows = [], []
    for si in picked:
        sysm, r = _draw_system(lay, si)
        drawn.append(sysm)
        rows += r
    margin = 3.0
    y = margin
    for sysm in drawn:
        sysm.top = y - sysm.ymin
        y = sysm.top + sysm.ymax + lay.opts.system_gap
    height = y - lay.opts.system_gap + margin if drawn else 2 * margin
    width = max((s.width for s in drawn), default=lay.opts.width) + 2 * margin + 2.0
    return Engraving(drawn, width, height, rows, [], margin)


def engrave_frames(sheet: Sheet, opts: Options | None = None) -> Engraving:
    return draw(plan(sheet, opts))


# ------------------------------------------------------------------ the render step


@dataclass
class Rendered:
    svg: str
    columns: list[dict]  # system, frame, x (SVG units, margin included), ms
    systems: list[
        dict
    ]  # index, first and last frame, top, bottom, staff_top, staff_bottom, left, right
    width: float
    height: float
    lines: int  # systems of the whole song
    timings: dict


def render_frames(
    text: str | Sheet,
    opts: Options | None = None,
    *,
    segment: tuple[int, int] | None = None,
    px_per_space: float = 10.0,
    note_ids: bool = True,
) -> Rendered:
    """F1 frames text (or its sheet) -> :class:`Rendered`. ``segment=(a, b)``: only the systems that hold a column
    in [a, b), with the line breaks of the whole song, so that they replace the same systems of a page.
    """
    t0 = time.perf_counter()
    sheet = f1.read(text) if isinstance(text, str) else text
    t1 = time.perf_counter()
    lay = plan(sheet, opts)
    t2 = time.perf_counter()
    picked = None
    if segment is not None:
        a, b = segment
        picked = [
            si
            for si, (i, j, _) in enumerate(lay.lines)
            if lay.columns[i].frame < b and lay.columns[j - 1].frame >= a
        ]
    eng = draw(lay, picked)
    t3 = time.perf_counter()
    svg = to_svg(eng, px_per_space=px_per_space, note_ids=note_ids)
    t4 = time.perf_counter()
    m = eng.margin
    cols = [{**r, "x": round(r["x"] + m, 3), "ms": round(r["ms"], 1)} for r in eng.columns]
    indices = list(range(len(lay.lines))) if picked is None else picked
    systems = [
        {
            "index": si,
            "first": lay.columns[lay.lines[si][0]].frame,
            "last": lay.columns[lay.lines[si][1] - 1].frame,
            "top": round(s.top + s.ymin, 3),
            "bottom": round(s.top + s.ymax, 3),
            "staff_top": round(s.top, 3),
            "staff_bottom": round(s.top + s.bass_top + 4, 3),
            "left": round(m, 3),
            "right": round(m + s.width, 3),
        }
        for si, s in zip(indices, eng.systems)
    ]
    t5 = time.perf_counter()
    ms = {
        "parse_ms": (t1 - t0) * 1e3,
        "plan_ms": (t2 - t1) * 1e3,
        "draw_ms": (t3 - t2) * 1e3,
        "svg_ms": (t4 - t3) * 1e3,
        "cursor_ms": (t5 - t4) * 1e3,
        "total_ms": (t5 - t0) * 1e3,
    }
    return Rendered(
        svg=svg,
        columns=cols,
        systems=systems,
        width=eng.width,
        height=eng.height,
        lines=len(lay.lines),
        timings={k: round(v, 2) for k, v in ms.items()},
    )
