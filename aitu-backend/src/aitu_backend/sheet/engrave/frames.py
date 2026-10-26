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
* **Lyrics** (implementation 03, Phase 8): each piece is drawn above the upper staff of the line that holds its first
  column, from the x of that column (between two drawn columns, by time, as the cursor), on one line of words per
  system just above the highest ink of the upper staff under the pieces; ``Lyric.lift`` raises a piece further.
  The text carries ``data-lyric`` (its place in the sheet's lyrics, by start), so a page can pick and light it.
* **The sheet's own settings** (Phase 8): ``Sheet.space_ms`` is the reference figure of the spacing when Transpose
  figures renamed the figures (the page keeps its widths), ``Sheet.line_space`` the space between lines.
* **Line breaks** only where no beam group is cut; from the columns that fill a line to at least ``Options.fill``,
  the one after the longest pause (time between two columns). A line starts at a pause again when a change moved
  the lines before it, so a changed segment moves the rest of the sheet little (Phase 5 redraws one segment).

:func:`render_frames` draws a whole song or the systems of one segment, with the cursor map and note ids.
"""

from __future__ import annotations

import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from fractions import Fraction

from aitu_backend.sheet.engrave import layout as L
from aitu_backend.sheet.engrave.glyphs import box
from aitu_backend.sheet.engrave.layout import Chord, Engraving, Head, Pen, System
from aitu_backend.sheet.engrave.lyric_text import text_width, wrap
from aitu_backend.sheet.engrave.spacing import SpacingModel, load
from aitu_backend.sheet.engrave.svg import to_svg
from aitu_backend.sheet.sheet import f1
from aitu_backend.sheet.sheet import frames as frames_mod
from aitu_backend.sheet.sheet.data import FRAME_MS, LYRIC_SIZE, Lyric, Note, Sheet

__all__ = [
    "Options",
    "Layout",
    "Rendered",
    "draw",
    "engrave_frames",
    "plan",
    "render_frames",
    "render_pages",
]

SIGN_ALTER = {"#": 1, "b": -1, "n": 0}
KEY_PAD = (
    1.5  # staff spaces before an armadura change inside a line: it must not read as an accidental
)
KEY_AFTER = 1.0
LONG_GAP = 2.0  # reference negras (a blanca): time beyond it between two columns is empty time
LYRIC_BASE = (
    -2.0
)  # the highest baseline of a line of words: this far above the top staff line, in staff spaces
LYRIC_CLEAR = 0.8  # and at least this far above the ink of the upper staff under the pieces
LYRIC_LEADING = 1.2  # the distance between two lines of one piece, in its size
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
    parts: dict | None = (
        None  # the lyrics parts of each line (lyric_parts), made when the first line is drawn
    )


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
    quarter = opts.quarter_ms or sheet.space_ms or sheet.quarter_ms or DEFAULT_QUARTER_MS
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
    xs, end_x = _column_xs(lay, si)
    for col, x in zip(cols, xs):
        col.x = x
        for c in col.chords:
            c.x = x
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
    _lyrics(lay, si, cols, end_x, pen)
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


def _column_xs(lay: Layout, si: int) -> tuple[list[float], float]:
    """The x of each column of a line and the x where the line ends, without drawing it."""
    i, j, e = lay.lines[si]
    x = _header(lay, i) + _first_lead(lay.columns[i])
    xs = []
    for k in range(i, j):
        xs.append(x)
        if k + 1 < j:
            x += max(lay.nat[k] + e, lay.mins[k])
        else:
            x += max(lay.ends[k][0] + e, lay.ends[k][1])
    last = j == len(lay.columns)
    end_x = x if (e == 0.0 and last and not lay.opts.justify_last) else max(x, lay.opts.width)
    return xs, end_x


def _x_of(lay: Layout, si: int, cols: list[Column], end_x: float, frame: int) -> float:
    """The x of a frame in a system: the column's own, or between two columns by time (the cursor's rule); after the
    last column, towards the end of the line by the time to the next line's first column."""
    if frame <= cols[0].frame:
        return cols[0].x
    for a, b in zip(cols, cols[1:]):
        if a.frame <= frame < b.frame:
            return a.x + (b.x - a.x) * (frame - a.frame) / (b.frame - a.frame)
    last = cols[-1]
    i, j, _ = lay.lines[si]
    nxt = lay.columns[j].frame if j < len(lay.columns) else None
    if nxt is None or nxt <= last.frame:
        return last.x
    return last.x + (end_x - last.x) * min(1.0, (frame - last.frame) / (nxt - last.frame))


def _ink_x(p: L.Prim) -> tuple[float, float] | None:
    if p.kind == "g":
        name, x, _, s, _ = p.data
        return x, x + box(name).width * s
    if p.kind == "l":
        return min(p.data[0], p.data[2]), max(p.data[0], p.data[2])
    if p.kind == "p":
        xs = [pt[0] for pt in p.data]
        return min(xs), max(xs)
    return None


@dataclass
class _LyricPart:
    """The words of a lyrics piece drawn in one line: the whole piece, or its share of the words when its frames
    cross a line break (the user's request of Phase 8A++)."""

    index: int  # the piece's place in the sheet's lyrics, by start (the drawing's ``data-lyric``)
    piece: Lyric
    text: str
    part: int  # 0 for the piece's first part (the one moved by hand), then 1, 2 ...


def _line_of(lay: Layout, frame: int) -> int:
    """The line that holds a frame: the last line starting at or before it (the first line for an earlier one)."""
    found = 0
    for si, (i, _, _) in enumerate(lay.lines):
        if lay.columns[i].frame <= frame:
            found = si
    return found


def _x_in(lay: Layout, si: int, xs: list[float], end_x: float, frame: int) -> float:
    """``_x_of`` for a line that is not drawn now (its column x from :func:`_column_xs`)."""
    i, j, _ = lay.lines[si]
    frames = [c.frame for c in lay.columns[i:j]]
    if frame <= frames[0]:
        return xs[0]
    for (fa, xa), (fb, xb) in zip(zip(frames, xs), zip(frames[1:], xs[1:])):
        if fa <= frame < fb:
            return xa + (xb - xa) * (frame - fa) / (fb - fa)
    nxt = lay.columns[j].frame if j < len(lay.columns) else None
    if nxt is None or nxt <= frames[-1]:
        return xs[-1]
    return xs[-1] + (end_x - xs[-1]) * min(1.0, (frame - frames[-1]) / (nxt - frames[-1]))


def _share_words(text: str, shares: list[float]) -> list[str]:
    """The words of ``text`` dealt in order into parts of about ``shares`` (fractions summing to 1) of its letters:
    each cut at the space nearest to its share."""
    words = [(m.start(), m.end()) for m in re.finditer(r"\S+", text)]
    if len(shares) == 1 or len(words) < 2:
        return [text] + [""] * (len(shares) - 1)
    total = sum(b - a + 1 for a, b in words)
    cuts, done, at = [], 0.0, 0
    for share in shares[:-1]:
        done += share * total
        # The word boundary whose letters before it come nearest to the share so far.
        best, best_d, run = at, abs(done), 0
        for w, (a, b) in enumerate(words):
            run += b - a + 1
            if w + 1 >= at and abs(run - done) < best_d:
                best, best_d = w + 1, abs(run - done)
        at = max(at, best)
        cuts.append(at)
    parts, prev = [], 0
    for cut in cuts + [len(words)]:
        if cut <= prev:
            parts.append("")
            continue
        parts.append(text[words[prev][0] : words[cut - 1][1]])
        prev = cut
    return parts


def lyric_parts(lay: Layout) -> dict[int, list[_LyricPart]]:
    """The parts of the lyrics pieces each line draws. A piece whose frames cross line breaks is drawn in one part
    per line, its words shared by the width its frames take in each line (60 % of the width, about 60 % of the
    letters); a block moved by hand to another line than its first frame's stays whole there."""
    out: dict[int, list[_LyricPart]] = {}
    if not lay.lines:
        return out
    xs_of: dict[int, tuple[list[float], float]] = {}

    def x_at(si: int, frame: int) -> float:
        if si not in xs_of:
            xs_of[si] = _column_xs(lay, si)
        xs, end_x = xs_of[si]
        return _x_in(lay, si, xs, end_x, frame)

    lyrics = sorted(lay.sheet.lyrics, key=lambda one: (one.start, one.end))
    for k, one in enumerate(lyrics):
        first = _line_of(lay, one.start)
        if one.free and _line_of(lay, one.at if one.at is not None else one.start) != first:
            out.setdefault(_line_of(lay, one.at), []).append(_LyricPart(k, one, one.text, 0))
            continue
        last = _line_of(lay, max(one.start, one.end - 1))
        if last == first:
            out.setdefault(first, []).append(_LyricPart(k, one, one.text, 0))
            continue
        widths = []
        for si in range(first, last + 1):
            i, j, _ = lay.lines[si]
            a = one.start if si == first else lay.columns[i].frame
            nxt = lay.columns[j].frame if j < len(lay.columns) else one.end
            b = min(one.end, nxt)
            if si < last and b >= nxt:
                left = x_at(si, a)
                widths.append(max(0.0, xs_of[si][1] - left))
            else:
                widths.append(max(0.0, x_at(si, b) - x_at(si, a)))
        total = sum(widths) or 1.0
        texts = _share_words(one.text, [w / total for w in widths])
        part = 0
        for si, text in zip(range(first, last + 1), texts):
            if text.strip():
                out.setdefault(si, []).append(_LyricPart(k, one, text, part))
                part += 1
    return out


def _lyrics(lay: Layout, si: int, cols: list[Column], end_x: float, pen: L.Pen) -> None:
    """The lyrics of this line, above the upper staff (module notes): the pieces in the line of words share one
    baseline above the ink under them; a block moved by hand sits where it was put (``Lyric.at``, ``dx``, ``dy``).
    A block with a width has its words wrapped to it (:mod:`lyric_text`); no block passes the end of its line.
    """
    if not lay.sheet.lyrics:
        return
    if lay.parts is None:
        lay.parts = lyric_parts(lay)
    mine = lay.parts.get(si, [])
    if not mine:
        return
    placed = []
    for p in mine:
        one = p.piece
        size = one.size or LYRIC_SIZE
        lines = wrap(p.text, one.width, size, one.font, one.bold, one.italic)
        wide = max(
            1.0, max(text_width(line, size, one.font, one.bold, one.italic) for line in lines)
        )
        if p.part == 0 and one.free:
            x = _x_of(lay, si, cols, end_x, one.at if one.at is not None else one.start) + one.dx
        elif p.part == 0:
            x = _x_of(lay, si, cols, end_x, one.start)
        else:
            x = cols[0].x
        x = max(0.0, min(x, end_x - wide))
        placed.append((p, size, tuple(lines), x, x + wide))
    tops = []
    in_line = [(x, right) for p, _, _, x, right in placed if not p.piece.free]
    for prim in pen.prims:
        if prim.staff != 1:
            continue
        span = _ink_x(prim)
        if span is None or not any(span[1] >= a and span[0] <= b for a, b in in_line):
            continue
        tops.append(L._prim_yrange(prim)[0])
    base = min([LYRIC_BASE] + [t - LYRIC_CLEAR for t in tops])
    for p, size, lines, x, _ in placed:
        one = p.piece
        last = one.dy if one.free else base - one.lift
        style = {
            "font": one.font,
            "bold": one.bold,
            "italic": one.italic,
            "width": one.width,
            "part": p.part,
        }
        y = last - (len(lines) - 1) * size * LYRIC_LEADING
        pen.prims.append(
            L.Prim("t", 1, (x, y, lines, size, p.index, one.start, one.end, style), "lyric")
        )


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
    gap = lay.sheet.line_space if lay.sheet.line_space is not None else lay.opts.system_gap
    y = margin
    for sysm in drawn:
        sysm.top = y - sysm.ymin
        y = sysm.top + sysm.ymax + gap
    height = y - gap + margin if drawn else 2 * margin
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


def render_pages(
    text: str | Sheet,
    opts: Options,
    *,
    page_height: float,
    first_height: float | None = None,
    gap: float | None = None,
    px_per_space: float = 10.0,
) -> list[dict]:
    """The sheet on paper (Print to PDF, implementation 03, Phase 8): drawn once at the paper's staff width
    (``opts.width``), then dealt out as whole lines onto pages ``page_height`` staff spaces high (the first page
    ``first_height``, under its title). A line never splits across a page turn; a line taller than a page has a page
    of its own. ``gap`` is the space between two lines on paper (default: the sheet's own). Returns one
    ``{"svg", "width", "height", "first", "last"}`` per page (the frames of its first and last columns).
    """
    sheet = f1.read(text) if isinstance(text, str) else text
    lay = plan(sheet, opts)
    eng = draw(lay)
    between = (
        gap
        if gap is not None
        else (sheet.line_space if sheet.line_space is not None else opts.system_gap)
    )
    margin = eng.margin
    pages: list[list[int]] = []
    room = first_height if first_height is not None else page_height
    used = 0.0
    for si, sysm in enumerate(eng.systems):
        tall = sysm.ymax - sysm.ymin
        need = tall if not pages or not pages[-1] or used == 0.0 else tall + between
        if pages and pages[-1] and used + need > room - 2 * margin:
            pages.append([])
            room, used, need = page_height, 0.0, tall
        if not pages:
            pages.append([])
        pages[-1].append(si)
        used += need
    out = []
    for picked in pages:
        drawn = [eng.systems[si] for si in picked]
        y = margin
        for sysm in drawn:
            sysm.top = y - sysm.ymin
            y = sysm.top + sysm.ymax + between
        height = y - between + margin
        page = Engraving(drawn, eng.width, height, [], [], margin)
        i, j = lay.lines[picked[0]][0], lay.lines[picked[-1]][1]
        out.append(
            {
                "svg": to_svg(page, px_per_space=px_per_space, note_ids=False),
                "width": round(eng.width, 3),
                "height": round(height, 3),
                "first": lay.columns[i].frame,
                "last": lay.columns[j - 1].frame,
            }
        )
    return out
