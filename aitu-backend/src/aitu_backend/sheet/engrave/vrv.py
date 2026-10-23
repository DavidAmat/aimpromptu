"""Verovio's rules for stems and beams (phase 10B: the user asked for Verovio's look).

Ported from Verovio 6.3 (``calcstemfunctor.cpp``, ``note.cpp`` ``CalcStemLenInThirdUnits``, ``beam.cpp``
``BeamSegment``, ``drawinginterface.cpp`` ``IsHorizontal``, ``view_beam.cpp`` partial beams; Verovio is LGPL-3.0, the
port is for the research prototype). The computation keeps Verovio's integer drawing units so the results match
its SVG: 180 per staff space (``UNIT`` = 90 is half a staff space), Y grows upward, Y = 0 is the top staff line,
a note's ``loc`` is its staff step (0 = bottom line, as ``Head.pos``).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

VU = 180  # Verovio drawing units per staff space (unit 9, x10)
UNIT = 90
CENTER = -360  # middle line
STAFF_TOP, STAFF_BOTTOM = 0, -720
STEM_W = 18  # stemWidth 0.2 unit
BEAM_BLACK = 90  # one unit
BEAM_WHITE = 45
BEAM_W = BEAM_BLACK + BEAM_WHITE
HEAD_W = 226  # Leipzig black / half notehead, 314 font units x 0.72
ANCHOR_UP = (226, 28)  # Leipzig stemUpSE (1.26, 0.16) staff spaces
ANCHOR_DOWN = {4: (0, -28), 2: (0, -25)}  # stemDownNW: black (0, -0.16), half (0, -0.14)
STANDARD_STEM = 7  # units (3.5 staff spaces)
D8 = 3  # duration index: log2(figure); 8th = 3, 16th = 4, 32nd = 5


def dur_index(figure: int) -> int:
    return {1: 0, 2: 1, 4: 2, 8: 3, 16: 4, 32: 5, 64: 6, 128: 7}.get(figure, 2)


def note_y(loc: int) -> int:
    return (loc - 8) * UNIT // 1


def _trunc_div(a: int, b: int) -> int:
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def ledger_lines(loc: int) -> tuple[int, int]:
    """(lines above, lines below) of a note."""
    return (max(0, (loc - 8) // 2), max(0, (-loc) // 2))


# ------------------------------------------------------------------ stems of single notes and chords


def chord_stem_up(locs: list[int]) -> bool:
    """``CalcStemDirection``: pair the highest note above the middle line with the lowest note at or below it, then
    the next pair inwards, until a pair is not centred on the middle line; a single note: up below the middle line.
    """
    if len(locs) == 1:
        return locs[0] < 4
    top = sorted((l for l in locs if l > 4), reverse=True)
    bottom = sorted(l for l in locs if l <= 4)
    for t, b in zip(top, bottom):
        if t + b == 8:
            continue
        return t + b < 8
    k = min(len(top), len(bottom))
    return k < len(bottom) and bottom[k] != 4


def stem_len_thirds(loc: int, up: bool, flagged_unbeamed: bool = False) -> int:
    """``Note::CalcStemLenInThirdUnits``: 21 thirds of a unit (3.5 staff spaces), shortened when the stem points
    away from a note near the outer line."""
    base = STANDARD_STEM * 3
    to_line = 8 - loc if up else loc
    shortening = 0
    if to_line < 5:
        shortening = {4: 1, 3: 2, 2: 3, 1: 4, 0: 5}.get(to_line, 6)
    if flagged_unbeamed:
        shortening = min(4 if up else 3, shortening)
    return base - shortening


@dataclass
class Stem:
    x: int  # stem centre
    y_start: int  # at the note (the far note's anchor)
    y_end: int  # free end (the flag hangs here)


FLAG_H = {
    (3, True): 499,
    (3, False): 499,
    (4, True): 560,
}  # glyph heights (Leipzig x 0.72); layout refreshes them


def unbeamed_stem(x: int, locs: list[int], up: bool, figure: int, head: int = 4) -> Stem:
    """``CalcStemFunctor::VisitStem`` + ``AdjustFlagPlacement`` for a note or chord that is not beamed (``x`` =
    left edge of the normal notehead column). Verovio keeps a stem as a start Y and a length; end = start - length.
    """
    ys = [note_y(l) for l in locs]
    y_max, y_min = max(ys), min(ys)
    d = dur_index(figure)
    flagged = d >= D8
    third = UNIT // 3
    if up:
        base = -stem_len_thirds(max(locs), True, flagged) * third
        ay = ANCHOR_UP[1]
        start = y_min + ay
        length = base + (y_min - y_max) + ay
        sx = x + ANCHOR_UP[0] - STEM_W // 2
    else:
        base = -stem_len_thirds(min(locs), False, flagged) * third
        ay = ANCHOR_DOWN.get(head, ANCHOR_DOWN[4])[1]
        start = y_max + ay
        length = -(base + (y_min - y_max) - ay)
        sx = x + ANCHOR_DOWN.get(head, ANCHOR_DOWN[4])[0] + STEM_W // 2
    end = start - length
    if (up and end < CENTER) or (not up and end > CENTER):
        length += end - CENTER
    if flagged:
        length = _adjust_flag(start, length, locs, up, d)
    return Stem(sx, start, start - length)


def _adjust_flag(start: int, length: int, locs: list[int], up: bool, d: int) -> int:
    """``AdjustFlagPlacement``: a down flag of a 32nd or shorter clears the notehead; a flag clears the first ledger
    line on its side."""
    gh = FLAG_H.get((d, up), FLAG_H[(4, True)]) if d < 4 else FLAG_H[(4, True)]
    step = UNIT
    if not up:
        margin = length - (gh + HEAD_W // 2)
        if d > 4 and margin < 0:
            off = step // 2 if _cmod(margin, step) < -step // 3 * 2 else 0
            length -= _trunc_div(margin, step) * step - off
    above, below = ledger_lines(max(locs))
    if (up and not below) or (not up and not above):
        return length
    bias = 1 if up else -1
    position = start - length - bias * gh
    ledger = CENTER - 6 * bias * step
    disp = (position - ledger) * bias
    if disp < 0:
        off = step // 2 if (not up and _cmod(disp, step) > -step // 3) else 0
        length += (_trunc_div(disp, step) - 1) * step * bias - off
    return length


def _cmod(a: int, b: int) -> int:
    """C++ remainder (sign of the dividend)."""
    return a - _trunc_div(a, b) * b


# ------------------------------------------------------------------ beams


@dataclass
class Coord:
    x: int  # left edge of the normal notehead column (drawing X); becomes the stem x
    locs: list[int]
    dur: int  # duration index (8th = 3)
    head: int = 4  # 4 black, 2 half (for the stem anchor)
    closest: int = 0  # loc of the note nearest the beam
    y_beam: int = 0
    centered: bool = False
    stem_start: int = 0
    stem_end: int = 0
    partial: dict[int, str] = field(default_factory=dict)


@dataclass
class Beam:
    above: bool
    coords: list[Coord]
    slope: float
    shortest: int
    polys: list[list[tuple[int, int]]] = field(default_factory=list)


def _place(coords: list[Coord], forced: bool | None) -> bool:
    """``CalcBeamPlace`` (True = above, stems up): voices first, then ledger lines, then the weighted extremes."""
    if forced is not None:
        return forced
    y_max = y_min = CENTER
    above_l = below_l = 0
    for c in coords:
        lo, hi = min(c.locs), max(c.locs)
        y_max, y_min = max(y_max, note_y(hi)), min(y_min, note_y(lo))
        if len(c.locs) == 1:
            a, b = ledger_lines(lo)
            above_l, below_l = above_l + a, below_l + b
        else:
            below_l += ledger_lines(lo)[1]
            above_l += ledger_lines(hi)[0]
    if below_l != above_l:
        return below_l > above_l
    return (CENTER - y_min) > (y_max - CENTER)


def _is_horizontal(coords: list[Coord], above: bool, shortest: int) -> bool:
    items = [note_y(c.closest) for c in coords]
    n = len(items)
    # repeated pattern
    if n >= 4:
        keys = [(note_y(c.closest), c.dur) for c in coords]
        if any(k != keys[0] for k in keys[1:]):
            for div in range(2, n // 2 + 1):
                if n % div:
                    continue
                if all(keys[j * div : (j + 1) * div] == keys[:div] for j in range(1, n // div)):
                    return True
    # one step height (32nds and shorter)
    if shortest >= 5:
        locs = [c.closest for c in coords]
        if max(locs) - min(locs) <= 1:
            return True
    if n < 2:
        return True
    first, last = items[0], items[-1]
    if first == last:
        return True
    first_step, last_step = first != items[1], last != items[-2]
    if n > 2 and (first_step or last_step):
        for i in range(1, n - 1):
            if above and items[i] >= first and items[i] >= last:
                return True
            if not above and items[i] <= first and items[i] <= last:
                return True
        pitches = [items[0]] + [b for a, b in zip(items, items[1:]) if b != a]
        if len(pitches) == 2:
            asc = all(a <= b for a, b in zip(items, items[1:]))
            desc = all(a >= b for a, b in zip(items, items[1:]))
            if above:
                if first_step and asc:
                    return True
                if last_step and desc:
                    return True
            else:
                if last_step and asc:
                    return True
                if first_step and desc:
                    return True
    return False


def _stem_length(c: Coord, up: bool, horizontal: bool, preferred: int) -> int:
    """``BeamElementCoord::CalculateStemLength`` in half units (signed)."""
    loc = c.closest
    on_space = loc % 2 != 0
    half_units = stem_len_thirds(loc, up) * 2 // 3
    extend = on_space and half_units == 14
    sign = 1 if up else -1
    if preferred == D8:
        if half_units != 14:
            n = half_units
        else:
            n = 14 if (on_space or not horizontal) else 13
    else:
        odd = extend or not horizontal
        n = {4: (14, 13), 5: (18, 16), 6: (22, 20), 7: (26, 24)}.get(c.dur, (14, 14))[
            0 if odd else 1
        ]
    return sign * n


def _defining_note(coords: list[Coord], above: bool) -> tuple[int, int, int | None]:
    shortest_d = relevant_d = 2
    shortest_l = relevant_l = None
    for c in coords:
        cur = c.closest
        if relevant_l is None:
            relevant_l = shortest_l = cur
            relevant_d = shortest_d = c.dur
            continue
        if above and cur > relevant_l:
            relevant_l, relevant_d = cur, c.dur
        elif not above and cur < relevant_l:
            relevant_l, relevant_d = cur, c.dur
        if c.dur > shortest_d:
            shortest_d, shortest_l = c.dur, cur
        elif c.dur == shortest_d:
            if (above and cur > shortest_l) or (not above and cur < shortest_l):
                shortest_d, shortest_l = c.dur, cur
    adjusted = None
    if shortest_d - relevant_d > abs(relevant_l - shortest_l) + 1:
        relevant_l, relevant_d = shortest_l, shortest_d
    elif shortest_d - relevant_d == abs(relevant_l - shortest_l) + 1:
        if (above and relevant_l > 4) or (not above and relevant_l < 4):
            relevant_l, relevant_d = shortest_l, shortest_d
    elif shortest_d - relevant_d == abs(relevant_l - shortest_l):
        adjusted = (relevant_d + shortest_d) // 2
    return relevant_l, relevant_d, adjusted


def _slope(a: Coord, b: Coord) -> float:
    return 0.0 if b.x == a.x else (b.y_beam - a.y_beam) / (b.x - a.x)


class _Seg:
    def __init__(self, coords: list[Coord], above: bool, shortest: int):
        self.c = coords
        self.above = above
        self.shortest = shortest
        self.slope = 0.0
        self.first, self.last = coords[0], coords[-1]

    def set_values(self) -> None:
        f = self.first
        for c in self.c:
            c.y_beam = math.floor(f.y_beam + self.slope * (c.x - f.x))

    def adjust_position(self) -> None:
        start, end = self.first.y_beam, self.last.y_beam
        height = abs(end - start)
        adjust = 0
        if STAFF_BOTTOM <= start <= STAFF_TOP:
            pos = abs(_cmod(STAFF_TOP - start, 2 * UNIT))
            if self.above:
                if (pos == UNIT and self.slope > 0 and height != UNIT) or (
                    pos == UNIT // 2 and self.slope < 0
                ):
                    adjust = -UNIT // 2
            else:
                if (pos == UNIT and self.slope < 0 and height != UNIT) or (
                    pos == 3 * UNIT // 2 and self.slope > 0
                ):
                    adjust = UNIT // 2
        self.first.y_beam += adjust
        self.set_values()

    def slope_step(self, note_step: int) -> tuple[int, bool]:
        step, short = 4 * UNIT, False
        dist = self.last.x - self.first.x
        n = len(self.c)
        if n == 2:
            step = 2 * UNIT
            if dist <= 6 * UNIT:
                step, short = UNIT // 2, True
        elif n == 3:
            if dist <= 12 * UNIT or note_step <= 4 * UNIT:
                step = 2 * UNIT
        else:
            if note_step < 3 * UNIT:
                step, short = UNIT // 2, True
            elif note_step <= 4 * UNIT:
                step = 2 * UNIT
            elif n == 4:
                c1, c2 = self.c[1], self.c[2]
                if c1.y_beam == c2.y_beam and (
                    self.first.y_beam == c1.y_beam or self.last.y_beam == c2.y_beam
                ):
                    step = 2 * UNIT
        if short and self.shortest >= 5:
            step, short = 2 * UNIT, False
        return step, short

    def calc_slope(self) -> tuple[bool, int]:
        f, l = self.first, self.last
        self.slope = _slope(f, l)
        note_slope = 0.0 if l.x == f.x else (note_y(l.closest) - note_y(f.closest)) / (l.x - f.x)
        note_step = abs(note_y(f.closest) - note_y(l.closest))
        if self.slope == 0.0:
            self.slope = note_slope
        if self.slope == 0.0:
            return False, 0
        step, short = self.slope_step(note_step)
        cur = abs(f.y_beam - l.y_beam)
        if cur != 0 and cur < step:
            return False, step
        if cur == 0:
            if self.above:
                if self.slope > 0:
                    l.y_beam += step
                else:
                    f.y_beam += step
            else:
                if self.slope < 0:
                    l.y_beam -= step
                else:
                    f.y_beam -= step
        if self.above:
            if self.slope > 0:
                f.centered = l.centered
                if short and not l.centered:
                    l.y_beam += step
                    l.centered = True
                f.y_beam = l.y_beam - step
            else:
                l.centered = f.centered
                if short and not f.centered:
                    f.y_beam += step
                    f.centered = True
                l.y_beam = f.y_beam - step
        else:
            if self.slope < 0:
                f.centered = l.centered
                if short and not l.centered:
                    l.y_beam -= step
                    l.centered = True
                f.y_beam = l.y_beam + step
            else:
                l.centered = f.centered
                if short and not f.centered:
                    f.y_beam -= step
                    f.centered = True
                l.y_beam = f.y_beam + step
        self.slope = _slope(f, l)
        if len(self.c) == 2:
            return False, step
        return True, step

    def adjust_slope(self, step: int) -> None:
        self.adjust_position()
        f, l = self.first, self.last
        if self.above:
            ref = (
                (l.y_beam - note_y(l.closest)) if self.slope > 0 else (f.y_beam - note_y(f.closest))
            )
        else:
            ref = (
                (note_y(l.closest) - l.y_beam) if self.slope < 0 else (note_y(f.closest) - f.y_beam)
            )
        ref -= UNIT
        lengthen = False
        for c in self.c:
            ln = abs(c.y_beam - note_y(c.closest))
            if ln < ref:
                lengthen = True
                break
            if c.dur > D8 and int(ln - 0.9 * UNIT) < ref:
                lengthen = True
                break
        if not lengthen:
            return
        if step >= 4 * UNIT:
            step = 2 * UNIT
            if self.above:
                if self.slope > 0:
                    f.y_beam += 2 * UNIT
                else:
                    l.y_beam += 2 * UNIT
            else:
                if self.slope < 0:
                    f.y_beam -= 2 * UNIT
                else:
                    l.y_beam -= 2 * UNIT
            self.slope = _slope(f, l)
            self.adjust_position()
            self.adjust_slope(step)
            return
        if self.above:
            if self.slope > 0:
                f.y_beam = l.y_beam
            else:
                l.y_beam = f.y_beam
        else:
            if self.slope < 0:
                f.y_beam = l.y_beam
            else:
                l.y_beam = f.y_beam
        self.slope = _slope(f, l)
        self.adjust_position()

    def horizontal(self) -> None:
        ys = [c.y_beam for c in self.c]
        self.first.y_beam = max(ys) if self.above else min(ys)
        self.slope = 0.0
        self.adjust_position()

    def ledger_adjust(self, horizontal: bool) -> None:
        total = BEAM_BLACK + (self.shortest - D8) * BEAM_W
        margin = UNIT if horizontal else 0
        adjust = 0
        for c in self.c:
            if not self.above:
                top = c.y_beam + total
                if top > STAFF_TOP - margin:
                    adjust = (_trunc_div(top - STAFF_TOP, 2 * UNIT) + 1) * 2 * UNIT
                    break
            else:
                bottom = c.y_beam - total
                if bottom < STAFF_BOTTOM + margin:
                    adjust = (_trunc_div(bottom - STAFF_BOTTOM, 2 * UNIT) - 1) * 2 * UNIT
                    break
        if adjust:
            for c in self.c:
                c.y_beam -= adjust


CUE = 0.75  # graceFactor


def _cue(v: int) -> int:
    return int(v * CUE)


def grace_stem(x: int, locs: list[int]) -> Stem:
    """Stem of a single grace note or chord: always up, the cue size of a flagged stem, never extended to the
    middle line (``CalcStemFunctor::VisitStem`` with ``m_isGraceNote``)."""
    ys = [note_y(l) for l in locs]
    base = _cue(stem_len_thirds(max(locs), True, True) * (UNIT // 3))
    start = min(ys) + _cue(ANCHOR_UP[1])
    return Stem(x + _cue(ANCHOR_UP[0]) - STEM_W // 2, start, max(ys) + base)


def beam_overlap(b: Beam, obstacles: list[tuple[int, int, int, int]]) -> int:
    """``AdjustBeamsFunctor::VisitLayerElement``: how far to move a one-staff beam away from the notes so that it
    clears ``obstacles`` (left, right, top, bottom; Y up) under it: grace notes, accidentals, the other voice. The
    result is added to every stem end before the beam is computed again (``m_overlapMargin``)."""
    f = b.coords[0]
    x1, y1 = f.x, f.y_beam
    bias = 1 if b.above else -1
    margin = 0
    for left, right, top, bottom in obstacles:
        if left < x1:
            continue
        yl, yr = y1 + b.slope * (left - x1), y1 + b.slope * (right - x1)
        if bias > 0:
            ml, mr = top - yl + BEAM_BLACK, top - yr + BEAM_BLACK
        else:
            ml, mr = bottom - yl - BEAM_BLACK, bottom - yr - BEAM_BLACK
        om = int(max(ml * bias, mr * bias))
        if om >= bias * margin:
            margin = int((((om + UNIT - 1) // UNIT) + 0.5) * UNIT) * bias
    return margin


def beam(
    coords: list[Coord], forced_above: bool | None = None, cue: bool = False, overlap: int = 0
) -> Beam:
    """Place, slope and stems of a one-staff beam (``BeamSegment::CalcBeam`` for ``above`` / ``below``), and its
    polygons (``View::DrawBeamSegment``), all in Verovio units. ``cue``: grace notes (sizes x 0.75, always above,
    stems not extended to the middle line)."""
    global BEAM_BLACK, BEAM_WHITE, BEAM_W, HEAD_W
    if cue:
        saved = BEAM_BLACK, BEAM_WHITE, BEAM_W, HEAD_W
        BEAM_BLACK, BEAM_WHITE, HEAD_W = _cue(90), _cue(45), _cue(226)
        BEAM_W = BEAM_BLACK + BEAM_WHITE
        try:
            return _beam(coords, True, True)
        finally:
            BEAM_BLACK, BEAM_WHITE, BEAM_W, HEAD_W = saved
    return _beam(coords, forced_above, False, overlap)


def _beam(coords: list[Coord], forced_above: bool | None, cue: bool, overlap: int = 0) -> Beam:
    above = _place(coords, forced_above)
    shortest = max(c.dur for c in coords)
    for c in coords:
        c.closest = max(c.locs) if above else min(c.locs)
    horizontal = _is_horizontal(coords, above, shortest)
    # uniform stem length from the defining note
    note_loc, note_dur, preferred = _defining_note(coords, above)
    uniform = 0
    for c in coords:
        if c.dur < note_dur:
            continue
        ln = _stem_length(c, above, horizontal, preferred if preferred is not None else c.dur)
        if c.closest == note_loc:
            uniform = ln
    if cue:
        uniform = int(uniform * CUE)
    seg = _Seg(coords, above, shortest)
    aup = (_cue(ANCHOR_UP[0]), _cue(ANCHOR_UP[1])) if cue else ANCHOR_UP
    for c in coords:
        c.centered = uniform % 2 != 0 or cue
        if above:
            c.x += aup[0] - STEM_W // 2
        else:
            c.x += ANCHOR_DOWN.get(c.head, ANCHOR_DOWN[4])[0] + STEM_W // 2
        c.y_beam = note_y(c.closest) + uniform * UNIT // 2
        if cue:
            continue
        if (above and c.y_beam <= CENTER) or (not above and CENTER <= c.y_beam):
            c.y_beam = CENTER
            c.centered = False
        c.y_beam += overlap
    if not horizontal:
        ok, step = seg.calc_slope()
        if ok:
            seg.adjust_slope(step)
        else:
            seg.adjust_position()
    else:
        seg.horizontal()
    seg.ledger_adjust(horizontal)
    # stems
    for c in coords:
        ys = [note_y(l) for l in c.locs]
        if above:
            c.stem_start = min(ys) + aup[1]
            c.stem_end = c.y_beam - STEM_W
        else:
            c.stem_start = max(ys) + ANCHOR_DOWN.get(c.head, ANCHOR_DOWN[4])[1]
            c.stem_end = c.y_beam + STEM_W
    b = Beam(above, coords, seg.slope, shortest)
    b.polys = _polygons(seg)
    return b


def _poly(x1: int, y1: int, x2: int, y2: int, h: int) -> list[tuple[int, int]]:
    return [(x1, y1), (x2, y2), (x2, y2 + h), (x1, y1 + h)]


def _polygons(seg: _Seg) -> list[list[tuple[int, int]]]:
    cs = seg.c
    shift = 1 if not seg.above else -1
    h = BEAM_BLACK * shift
    xs = [c.x for c in cs]
    xs[0] -= STEM_W // 2
    xs[-1] += STEM_W // 2
    ys = [c.y_beam for c in cs]
    out = [_poly(xs[0], ys[0], xs[-1], ys[-1], h)]
    fx, fy = xs[0], ys[0]
    n = len(cs)
    bar_y = 0
    partial: dict[tuple[int, int], str] = {}
    for test in range(4, seg.shortest + 1):
        bar_y += BEAM_W
        start = True
        for i in range(n - 1):
            partial[(i, test)] = ""
            if cs[i].dur >= test:
                if cs[i + 1].dur >= test:
                    partial[(i, test)] = "through"
                else:
                    if start:
                        partial[(i, test)] = "right"
                    elif cs[i - 1].dur < test:
                        if test == 4:
                            partial[(i, test)] = "left"
                        elif partial.get((i - 1, test - 1)) == "through":
                            partial[(i, test)] = "left"
                        elif partial.get((i, test - 1)) != "left":
                            partial[(i, test)] = "right"
                        else:
                            partial[(i, test)] = "left"
            start = False
        i = n - 1
        partial[(i, test)] = ""
        if cs[i].dur >= test and (n == 1 or cs[i - 1].dur < test or start):
            partial[(i, test)] = "left"
        pos = shift * bar_y
        for i in range(n):
            kind = partial[(i, test)]
            if kind == "through":
                out.append(_poly(xs[i], ys[i] + pos, xs[i + 1], ys[i + 1] + pos, h))
            elif kind == "right":
                x2 = xs[i] + HEAD_W
                out.append(
                    _poly(xs[i], ys[i] + pos, x2, math.floor(fy + pos + seg.slope * (x2 - fx)), h)
                )
            elif kind == "left":
                x1 = xs[i] - HEAD_W
                out.append(
                    _poly(x1, math.floor(fy + pos + seg.slope * (x1 - fx)), xs[i], ys[i] + pos, h)
                )
    return out


# ------------------------------------------------------------------ accidentals of a chord


FS = 720  # font size in drawing units (units per em 1000 = 4 staff spaces)
# Leipzig boxes (font units: x, y, w, h) and cut-out anchors (staff spaces), from verovio/data/Leipzig.xml
ACC_DATA = {
    "accidentalFlat": ((0, -175, 198, 644), {"NE": (0.1, 0.56), "SE": (0.43, -0.34)}),
    "accidentalNatural": ((0, -351, 157, 702), {"NE": (0.08, 0.74), "SW": (0.55, -0.76)}),
    "accidentalSharp": (
        (0, -339, 197, 694),
        {"NE": (0.62, 0.84), "NW": (0.16, 0.64), "SE": (0.62, -0.64), "SW": (0.16, -0.82)},
    ),
    "accidentalDoubleSharp": ((0, -120, 257, 240), {}),
    "accidentalDoubleFlat": ((0, -175, 388, 644), {"NE": (0.86, 0.56), "SE": (1.23, -0.3)}),
}
HEAD_DATA = {
    "noteheadBlack": ((0, -133, 314, 266), {"NW": (0.14, 0.24), "SE": (1.09, -0.24)}),
    "noteheadHalf": ((0, -132, 314, 270), {"NW": (0.14, 0.24), "SE": (1.08, -0.24)}),
    "noteheadWhole": ((0, -133, 405, 266), {"NW": (0.06, 0.24), "SE": (1.57, -0.23)}),
}
ACC_MARGIN = UNIT // 2  # rightMarginAccid 0.5 unit
LEDGER_EXT_U = 0.54  # ledgerLineExtension in units


def _fu(v: float) -> int:
    return _trunc_div(int(round(v)) * FS, 1000)


class _Box:
    """A glyph or stem box in drawing units (Y up) with Verovio's cut-out rectangles."""

    def __init__(
        self, kind: str, x: int, y: int, glyph: str | None = None, rect=None, ledger: bool = False
    ):
        self.kind, self.x, self.y, self.glyph, self.ledger = kind, x, y, glyph, ledger
        if glyph is not None:
            (gx, gy, gw, gh), self.anchors = ACC_DATA.get(glyph) or HEAD_DATA[glyph]
            self.gx, self.gy, self.gw, self.gh = _fu(gx), _fu(gy), _fu(gw), _fu(gh)
        else:
            self.anchors = {}
            l, b, r, t = rect
            self.gx, self.gy, self.gw, self.gh = l - x, b - y, r - l, t - b

    left = property(lambda s: s.x + s.gx)
    right = property(lambda s: s.x + s.gx + s.gw)
    bottom = property(lambda s: s.y + s.gy)
    top = property(lambda s: s.y + s.gy + s.gh)

    def _pt(self, a: str) -> tuple[int, int]:
        ax, ay = self.anchors[a]
        return self.x + _fu(ax * 250), self.y + _fu(ay * 250)

    def rects(self, a1: str, a2: str) -> list[tuple[int, int, int, int]]:
        """(left, top, right, bottom) rectangles, as ``GetRectangles(anchor1, anchor2)``."""
        L, T, R, B = self.left, self.top, self.right, self.bottom
        has1, has2 = a1 in self.anchors, a2 in self.anchors
        if has1 and has2:
            (p1x, p1y), (p2x, p2y) = self._pt(a1), self._pt(a2)
            if all(L <= px <= R and B <= py <= T for px, py in ((p1x, p1y), (p2x, p2y))):
                if (a1, a2) == ("NE", "SE"):
                    return [(L, T, p1x, p1y), (L, p1y, R, p2y), (L, p2y, p2x, B)]
                if (a1, a2) == ("NW", "SW"):
                    return [(p1x, T, R, p1y), (L, p1y, R, p2y), (p2x, p2y, R, B)]
        elif has1 or has2:
            a = a1 if has1 else a2
            px, py = self._pt(a)
            if L <= px <= R and B <= py <= T:
                if a == "NE":
                    return [(L, T, px, py), (L, py, R, B)]
                if a == "SE":
                    return [(L, T, R, py), (L, py, px, B)]
                if a == "SW":
                    return [(L, T, R, py), (px, py, R, B)]
                if a == "NW":
                    return [(px, T, R, py), (L, py, R, B)]
        return [(L, T, R, B)]

    def v_overlap(self, o: "_Box", m: int) -> bool:
        return not (self.top <= o.bottom - m or self.bottom >= o.top + m)

    def right_overlap(self, o: "_Box", m: int, vm: int) -> int:
        best = 0
        for r1 in self.rects("NE", "SE"):
            for r2 in o.rects("NW", "SW"):
                if r1[1] < r2[3] - vm or r1[3] > r2[1] + vm:
                    continue
                best = max(best, r1[2] - r2[0] + m)
        return best

    def left_overlap(self, o: "_Box", m: int, vm: int) -> int:
        best = 0
        for r1 in self.rects("NW", "SW"):
            for r2 in o.rects("NE", "SE"):
                if r1[1] < r2[3] - vm or r1[3] > r2[1] + vm:
                    continue
                best = max(best, r2[2] - r1[0] + m)
        return best


def place_accidentals(
    heads: list[tuple], stem=None, head_glyph: str = "noteheadBlack"
) -> list[int | None]:
    """``AdjustAccidXFunctor`` for one column of one staff (all voices). ``heads``: (x of the head, loc, accidental
    glyph or None[, head glyph]) per note; ``stem``: (x centre, Y start, Y end), a list of them, or None. Returns the
    left edge X of each accidental."""
    heads = [h if len(h) == 4 else (*h, head_glyph) for h in heads]
    notes = [
        _Box("note", x, note_y(loc), hg, ledger=any(ledger_lines(loc))) for x, loc, _, hg in heads
    ]
    elements: list[_Box] = list(notes)
    for st in ([stem] if isinstance(stem, tuple) else (stem or [])):
        sx, y0, y1 = st
        elements.append(
            _Box(
                "stem", sx, y0, rect=(sx - STEM_W // 2, min(y0, y1), sx + STEM_W // 2, max(y0, y1))
            )
        )
    accs = []
    x0 = min(x for x, _, _, _ in heads)
    heads3 = [(x, loc, g) for x, loc, g, _ in heads]
    for (x, loc, g), nb in zip(heads3, notes):
        if g is not None:
            a = _Box("accid", x0 if x >= x0 else x, note_y(loc), g)
            a.note = nb
            accs.append(a)
    elements += accs
    order = sorted(accs, key=lambda a: -a.y)
    done: set[int] = set()

    def adjust_x(a: _Box, e: _Box, left_accs: list[_Box]) -> None:
        if a is e:
            return
        m = ACC_MARGIN
        if e.kind == "accid":
            m = int(m * 0.66)
        elif e.kind == "note" and e.ledger:
            m = max(m, int(LEDGER_EXT_U * UNIT + 0.5 * m))
        vm = UNIT // 4
        if not a.v_overlap(e, vm):
            return
        if e.kind == "accid" and a.y == e.y and a.glyph == e.glyph:
            return
        if e.kind == "accid":
            if not a.left_overlap(e, m, vm):
                left_accs.append(e)
                return
            if id(e) not in done:
                return
        shift = (a.right - e.left + m) if e.kind == "stem" else a.right_overlap(e, m, vm)
        if shift > 0:
            a.x -= shift
            done.add(id(a))
            if left_accs:
                sub: list[_Box] = []
                for la in list(left_accs):
                    adjust_x(a, la, sub)

    def with_space(a: _Box) -> None:
        left: list[_Box] = []
        for e in elements:
            adjust_x(a, e, left)
        done.add(id(a))

    n = len(order)
    i, j = 0, n - 1
    while i < n:
        if id(order[i]) not in done:
            with_space(order[i])
        if j >= 0 and id(order[j]) not in done:
            with_space(order[j])
        i += 1
        j -= 1
    out = []
    k = 0
    for x, loc, g in heads3:
        if g is None:
            out.append(None)
        else:
            out.append(accs[k].left)
            k += 1
    return out


# ------------------------------------------------------------------ ledger lines


LEDGER_EXT = 48  # ledgerLineExtension 0.54 unit
LEDGER_MIN_EXT = 18  # its minimum, 0.2 unit


def ledger_dashes(
    notes: list[tuple[int, int, int]], ext: int = LEDGER_EXT, min_ext: int = LEDGER_MIN_EXT
) -> dict[tuple[str, int], list[tuple[int, int]]]:
    """``CalcLedgerLinesFunctor`` for one staff of one measure. ``notes``: (x of the head, head width, loc).
    Returns {("above"|"below", line index from the staff): [(x1, x2), ...]}: dashes of one chord merge, dashes of
    neighbouring notes are shortened so that a gap of about one extension remains between them."""
    lines: dict[str, list[list[list[int]]]] = {"above": [], "below": []}
    for x, w, loc in notes:
        above, below = ledger_lines(loc)
        side, count = ("above", above) if above else ("below", below)
        if not count:
            continue
        ls = lines[side]
        while len(ls) < count:
            ls.append([])
        for i in range(count):
            dashes = ls[i]
            dashes.append([x - ext, x + w + ext])
            dashes.sort(key=lambda d: d[0])
            k = 1
            while k < len(dashes):
                if dashes[k - 1][1] > dashes[k][0] + 1.5 * ext:
                    dashes[k - 1][1] = max(dashes[k - 1][1], dashes[k][1])
                    del dashes[k]
                else:
                    k += 1
    out = {}
    for side, ls in lines.items():
        if not ls:
            continue
        inner = sorted(ls[0], key=lambda d: (d[0], d[1]))
        deltas = []
        left_gap = 100 * ext
        for i, d in enumerate(inner):
            right_gap = inner[i + 1][0] - d[1] if i + 1 < len(inner) else 100 * ext
            right_part = int(0.5 * right_gap)
            next_left = int(0.5 * right_gap)
            m = min(left_gap, right_part)
            delta = 0
            if m < ext / 2.0:
                total = m + ext
                delta = ext - max(int(2 * total / 3), min_ext)
            deltas.append((d[0], d[1], delta))
            left_gap = next_left
        for i, dashes in enumerate(ls):
            res = []
            for a, b in dashes:
                dl = next((dd for l0, r0, dd in deltas if a >= l0 and b <= r0), 0)
                res.append((a + dl, b - dl))
            out[(side, i)] = res
    return out


# ------------------------------------------------------------------ rests in a staff with two voices

# g_defaultRests (rest.cpp), accidental "none": offsets by duration index (whole 0 ... 128th 7), for a rest above /
# below the other voice and the note of reference on a line / in a space
_REST_OTHER = {
    (True, False): [3, 3, 5, 5, 7, 7, 9, 9],
    (True, True): [2, 4, 6, 4, 6, 6, 8, 8],
    (False, False): [-5, -5, -5, -5, -5, -7, -7, -9],
    (False, True): [-6, -6, -6, -4, -4, -6, -6, -8],
}
_REST_SAME = {
    (True, False): [-1, 1, 1, 1, 3, 3, 5, 5],
    (True, True): [0, 0, 2, 2, 2, 2, 4, 4],
    (False, False): [-3, -1, -1, -1, -1, -3, -3, -5],
    (False, True): [-2, -2, -2, -2, -2, -4, -4, -6],
}


def rest_loc(
    figure: int,
    top: bool,
    others: list[tuple[int, bool]],
    prev_loc: int | None,
    next_loc: int | None,
    rest_overlap: bool,
) -> int:
    """``Rest::GetOptimalLayerLocation`` for a rest of a staff with two voices. ``others``: (loc, same onset) of the
    other voice's notes sounding during the rest (the top note when the rest is above); ``prev_loc``/``next_loc``:
    the nearest notes of the rest's own voice (the note nearest the other voice)."""
    d = dur_index(figure)
    di = max(0, min(7, d))
    default = 6 if figure == 1 else 4
    other = None
    for loc, same in others:
        if not same and ((top and loc > 12) or (not top and loc < -4)):
            if other is not None:
                continue
            loc = 12 if top else -4
        if other is None or (top and loc > other) or (not top and loc < other):
            other = loc
    cand = [default]
    if other is not None:
        cand.append(other + _REST_OTHER[(top, other % 2 == 0)][di])
    cur = None
    if prev_loc is not None and next_loc is not None:
        cur = (
            (prev_loc + next_loc) // 2
            if prev_loc + next_loc >= 0
            else -((-(prev_loc + next_loc)) // 2)
        )
    elif prev_loc is not None or next_loc is not None:
        cur = prev_loc if prev_loc is not None else next_loc
    if cur is not None:
        cur = min(cur, 10) if top else max(cur, -2)
        cand.append(cur + _REST_SAME[(top, cur % 2 == 0)][di])
    margin = 6 if top else 2
    if figure == 4 and rest_overlap:
        margin = 8 if top else 0
    elif d >= D8:
        margin = 6 + (d - 2) // 2 * 2 if top else 2 - (d - 3) // 2 * 2
    cand.append(margin)
    return max(cand) if top else min(cand)


# ------------------------------------------------------------------ beams between the staves (mixed)


def mixed_beam(coords: list[Coord], tops: list[int], above_rel: list[bool]) -> Beam:
    """A beam whose notes are in both staves (``BEAMPLACE_mixed``: ``CalcMixedBeamPlace``,
    ``CalcPartialFlagPlace``, ``CalcMixedBeamPosition``, mixed stems and partial beams). ``tops``: Y of each
    note's staff top line (system Y, up); ``above_rel``: True when the beam is above the note (its stem up: the
    lower staff's notes)."""
    shortest = max(c.dur for c in coords)
    for c, rel in zip(coords, above_rel):
        c.closest = max(c.locs) if rel else min(c.locs)
    ys = lambda c, t: t + note_y(c.closest)  # noqa: E731
    # partial beams: one side for the whole group (``CalcPartialFlagPlace``)
    partial_above: list[bool | None] = [None] * len(coords)
    i = 0
    n = len(coords)
    while i < n:
        if coords[i].dur < 4:
            i += 1
            continue
        start, place = i, above_rel[i]
        j = i
        done = False
        while True:
            k = next((m for m in range(j, n) if above_rel[m] != place or coords[m].dur <= D8), n)
            j = k
            if k == n or coords[k].dur <= D8:
                break
            if k == n - 1:
                j = n
                done = True
                break
            place = above_rel[k]
        for m in range(start, j):
            partial_above[m] = (
                not place
            )  # (place % 2) + 1: the side opposite the subdivision's last place
        if done:
            break
        i = j + 1 if j < n else n
    top_beams = max([coords[m].dur - D8 for m in range(n) if partial_above[m] is True] + [0])
    bottom_beams = max([coords[m].dur - D8 for m in range(n) if partial_above[m] is False] + [0])
    # uniform stem length from the first note (no above / below preference in a mixed beam)
    rel_l, rel_d = coords[0].closest, coords[0].dur
    sh_l, sh_d = rel_l, rel_d
    for c, rel in zip(coords[1:], above_rel[1:]):
        if c.dur > sh_d:
            sh_d, sh_l = c.dur, c.closest
        elif c.dur == sh_d and ((rel and c.closest > sh_l) or (not rel and c.closest < sh_l)):
            sh_l = c.closest
    preferred = None
    if sh_d - rel_d > abs(rel_l - sh_l) + 1:
        rel_l, rel_d = sh_l, sh_d
    elif sh_d - rel_d == abs(rel_l - sh_l) + 1:
        if (above_rel[0] and rel_l > 4) or (not above_rel[0] and rel_l < 4):
            rel_l, rel_d = sh_l, sh_d
    elif sh_d - rel_d == abs(rel_l - sh_l):
        preferred = (rel_d + sh_d) // 2
    uniform = 0
    for c, rel in zip(coords, above_rel):
        if c.dur < rel_d:
            continue
        ln = _stem_length(c, rel, False, preferred if preferred is not None else c.dur)
        if c.closest == rel_l:
            uniform = ln
    for c, rel, t in zip(coords, above_rel, tops):
        ln = abs(uniform) if rel else -abs(uniform)
        c.x += (
            (ANCHOR_UP[0] - STEM_W // 2)
            if rel
            else (ANCHOR_DOWN.get(c.head, ANCHOR_DOWN[4])[0] + STEM_W // 2)
        )
        c.y_beam = ys(c, t) + ln * UNIT // 2
    f, l = coords[0], coords[-1]
    slope = _slope(f, l)
    note_step = abs(ys(f, tops[0]) - ys(l, tops[-1]))
    if slope == 0.0 and l.x != f.x:
        slope = (ys(l, tops[-1]) - ys(f, tops[0])) / (l.x - f.x)
    seg = _Seg(coords, True, shortest)
    seg.slope = slope
    if slope != 0.0:
        step, _ = seg.slope_step(note_step)
        if step <= UNIT or step > 2 * UNIT:
            step = 2 * UNIT
    else:
        step = 0
    # CalcMixedBeamPosition / CalcMixedBeamCenterY
    up = (slope > 0) if above_rel[0] == above_rel[-1] else (not above_rel[-1])
    dist = l.x - f.x
    target = (step if up else -step) / dist if dist else 0.0
    hb = [c.y_beam - target * (c.x - f.x) for c, rel in zip(coords, above_rel) if rel]
    la = [c.y_beam - target * (c.x - f.x) for c, rel in zip(coords, above_rel) if not rel]
    center = (f.y_beam + l.y_beam) // 2
    if hb and la:
        center = int((max(hb) + min(la)) / 2 + target * dist / 2)
    center += _cmod(f.y_beam - center, UNIT // 2)
    center += (BEAM_BLACK + bottom_beams * BEAM_W - top_beams * BEAM_W) // 2
    f.y_beam = center - step // 2 if up else center + step // 2
    l.y_beam = f.y_beam + step if up else f.y_beam - step
    seg.slope = _slope(f, l)
    seg.set_values()
    # stems (CalcSetStemValues, mixed)
    for c, rel, t, pa in zip(coords, above_rel, tops, partial_above):
        cys = [t + note_y(x) for x in c.locs]
        off = (c.dur - D8) * BEAM_W if pa is not None and pa == rel else 0
        if rel:
            c.stem_start = min(cys) + ANCHOR_UP[1]
            c.stem_end = c.y_beam + off
        else:
            c.stem_start = max(cys) + ANCHOR_DOWN.get(c.head, ANCHOR_DOWN[4])[1]
            c.stem_end = c.y_beam - (BEAM_BLACK + off)
    b = Beam(True, coords, seg.slope, shortest)
    # polygons: the primary hangs below the beam line; partial beams on their side
    xs = [c.x for c in coords]
    xs[0] -= STEM_W // 2
    xs[-1] += STEM_W // 2
    yb = [c.y_beam for c in coords]
    h = -BEAM_BLACK
    polys = [_poly(xs[0], yb[0], xs[-1], yb[-1], h)]
    for test in range(4, shortest + 1):
        bar_y = (test - D8) * BEAM_W
        kinds = {}
        st = True
        for i in range(n - 1):
            kinds[i] = ""
            if coords[i].dur >= test:
                if coords[i + 1].dur >= test:
                    kinds[i] = "through"
                elif st:
                    kinds[i] = "right"
                elif coords[i - 1].dur < test:
                    kinds[i] = "left"
            st = False
        kinds[n - 1] = (
            "left"
            if coords[n - 1].dur >= test and (n == 1 or coords[n - 2].dur < test or st)
            else ""
        )
        for i in range(n):
            pa = partial_above[i]
            if pa is None:
                if i == 0 or i == n - 1 or partial_above[i - 1] == partial_above[i + 1]:
                    continue
                pa = partial_above[i - 1]
            pos = bar_y if pa else -bar_y
            if kinds[i] == "through":
                polys.append(_poly(xs[i], yb[i] + pos, xs[i + 1], yb[i + 1] + pos, h))
            elif kinds[i] == "right":
                x2 = xs[i] + HEAD_W
                polys.append(
                    _poly(
                        xs[i],
                        yb[i] + pos,
                        x2,
                        math.floor(yb[0] + pos + seg.slope * (x2 - xs[0])),
                        h,
                    )
                )
            elif kinds[i] == "left":
                x1 = xs[i] - HEAD_W
                polys.append(
                    _poly(
                        x1,
                        math.floor(yb[0] + pos + seg.slope * (x1 - xs[0])),
                        xs[i],
                        yb[i] + pos,
                        h,
                    )
                )
    b.polys = polys
    return b


# ------------------------------------------------------------------ augmentation dots


def _dot_set(locs: list[int], reverse: bool) -> set[int]:
    """``CalculateDotLocations`` (chord.cpp): one dot per note, in a free space near it."""
    adjust = [0, 1, -1, -2, 2]
    if reverse:
        adjust = [-a for a in adjust]
        locs = sorted(locs, reverse=True)
    else:
        locs = sorted(locs)
    out: set[int] = set()
    prev = None
    for loc in locs:
        for a in adjust:
            if (loc + a) % 2 == 0:
                continue
            if prev is not None and prev == loc and a == (2 if reverse else -2):
                continue
            if loc + a not in out:
                out.add(loc + a)
                break
        prev = loc
    return out


def dot_locs(locs: list[int], up: bool, layers: int, primary: bool) -> set[int]:
    """``Note::CalcDotLocations`` / ``Chord::CalcDotLocations``: dots go up from the notes when the stem is up or
    the voice is alone, down otherwise (``primary``); the secondary choice is the other direction.
    """
    upward = up or layers == 1
    if len(locs) == 1:
        loc = locs[0]
        if loc % 2 == 0:
            loc += 1 if upward == primary else -1
        return {loc}
    return _dot_set(locs, upward != primary)


def optimal_dot_locs(
    locs: list[int], up: bool, layers: int, other: tuple[list[int], bool] | None
) -> set[int]:
    """``LayerElement::CalcOptimalDotLocations``: with two voices, the choice that collides least with the dots of the
    other voice's note at the same time (``other``: its locs and stem direction; ties: the upper voice keeps its
    primary choice)."""
    d1, d2 = dot_locs(locs, up, layers, True), dot_locs(locs, up, layers, False)
    if layers == 2 and other is not None:
        o1, o2 = dot_locs(other[0], other[1], layers, True), dot_locs(
            other[0], other[1], layers, False
        )
        c11, c12, c21, c22 = len(d1 & o1), len(d1 & o2), len(d2 & o1), len(d2 & o2)
        if max(c11, c12, c21, c22) > 0:
            m = min(c11, c12, c21, c22)
            if c11 == m:
                return d1
            if c12 == m:
                return d1 if c21 != m or up else d2
            return d2
    return d1 if len(d1) >= len(d2) else d2
