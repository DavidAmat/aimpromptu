"""Layout of an F1-bars sheet: voices, rests, accidentals, stems, columns, spacing, lines, beams.

Input is a bars :class:`~aitu_backend.sheet.sheet.data.Sheet` (``f1.read`` of an F1-bars text, or
``from_ir``). The sheet content has no rests, no voices, no stems and no printed accidentals (phase 4),
so this module derives them:

* voices: per staff and bar, chords (same time, figure and tags) and whole beam groups go into the
  first voice that is free; with two or more voices the highest voice stems up, the others down;
* rests: times when the staff is silent (no note of any voice sounds) get visible rests (split on the beat), a
  staff with no note in a bar gets a whole-bar rest; ``Options.voice_rests`` gives the classical rule instead (every
  gap of the first voice, also over the notes of another voice);
* printed accidentals: rule ``spell.10`` with bars (an accidental is printed when the spelled alter
  differs from the key signature or from the last alter of the same step and octave in the bar);
* stems: single voice by the note furthest from the middle line; a beam group shares one direction;
  a beam group with notes in both staves is drawn between the staves (right-hand stems down,
  left-hand stems up).

Spacing follows ``engrave.spacing`` (duration, not content; no compression inside beams; no extra gap
between beam groups; additive justification). All lengths are in staff spaces, y grows downward; y of a
staff element is relative to the top line of its staff.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from fractions import Fraction

from aitu_backend.sheet.engrave import glyphs, vrv
from aitu_backend.sheet.engrave.glyphs import box
from aitu_backend.sheet.engrave.spacing import SpacingModel, load
from aitu_backend.sheet.sheet.common import figure_quarters
from aitu_backend.sheet.sheet.data import Note, Sheet, beat_unit

__all__ = ["Options", "Engraving", "engrave"]

STEPS = "CDEFGAB"
BOTTOM_LINE = {"G2": 30, "F4": 18, "C3": 24, "C4": 22}  # diatonic index of the bottom line per clef
DEFAULT_CLEF = {1: "G2", 2: "F4"}
HEAD_W = box(
    "noteheadBlack"
).width  # Leland 1.30 (Bravura 1.18); refreshed by _metrics() for the active font
WHOLE_W = box("noteheadWhole").width
STEM_W = 0.12
STAFF_LINE_W = 0.13
BAR_W = 0.16
LEDGER_W = 0.16
LEDGER_EXT = 0.4
BEAM_T = 0.65  # Chopin first editions: single beams 0.71 ss on the scans (other editions 0.55, ink included); E09 §9
BEAM_PITCH = 0.75
STEM_LEN = 3.5
ACC_GAP = 0.16
DOT_GAP = 0.3
GRACE_SCALE = 0.65
FINGER_SCALE = 0.6  # finger digits (the tuplet digits, smaller)
FINGER_GAP = 0.2  # between the finger column of a chord and its accidentals / noteheads
FINGER_STEP = 0.95  # minimum distance between two finger digits of one chord (a second apart: 0.5)
CHANGE_CLEF_W = 2.0
SHARP_POS = [8, 5, 9, 6, 3, 7, 4]  # treble staff positions of the key signature (bass: 2 lower)
FLAT_POS = [4, 7, 3, 6, 2, 5, 1]
SHARP_ORDER = "FCGDAEB"
ACC_GLYPH = {
    -2: "accidentalDoubleFlat",
    -1: "accidentalFlat",
    0: "accidentalNatural",
    1: "accidentalSharp",
    2: "accidentalDoubleSharp",
}
# Beam slant (user feedback 2026-10-20; measured on the Chopin first editions, E09 README §9): the beam rises about
# two thirds of the interval between its end notes (second 0.37 ss, third 0.63, fifth 1.06, octave 2.4; flat in
# only 9 % of seconds), also when an inner note goes past the ends (flat in 5 %); it stays flat only when the end
# notes are the same. Replaces phase 9's table (flat for a second, at most 1 ss, flat when concave).
BEAM_RISE = 0.65  # rise / interval between the end notes (staff spaces)
BEAM_MAX_RISE = 3.0
BEAM_MAX_SLOPE = 0.33  # staff spaces of rise per staff space of length (prints: 0.11 for seconds, 0.33 beyond octave)
REST_GLYPH = {
    0: "restDoubleWhole",
    1: "restWhole",
    2: "restHalf",
    4: "restQuarter",
    8: "rest8th",
    16: "rest16th",
    32: "rest32nd",
    64: "rest64th",
    128: "rest128th",
}
FLAGS = {8: "8th", 16: "16th", 32: "32nd", 64: "64th", 128: "64th"}
DOT_R = 0.0  # > 0: augmentation dots drawn as circles of this radius (Verovio), centre DOT_GAP after the head

# Drawing styles (phase 10B). "verovio" (default since 2026-10-20, the user's choice): Verovio 6.3's look, measured on
# its SVG and ported from its code (``vrv``): Leipzig glyphs, staff lines 0.072, stems 0.10, ledger lines 0.12
# extending 0.27, barlines 0.15, beams 0.5 thick and 0.75 apart, round dots of radius 0.2 at 0.5 after the head,
# grace notes x 0.75, Verovio's stem lengths, beam places, slopes and stubs, Verovio's brace. "op62": the phase 10
# engraving after the user's second review (E09 README §9): heads drawn from the Op. 62 first edition, Leland,
# Leipzig flat, beams 0.65 thick slanting 0.65 x the interval, left-hand beams below.
STYLES = {
    "verovio": dict(
        font="Leipzig",
        engraved=False,
        glyph_font={},
        STAFF_LINE_W=13 / 180,
        STEM_W=18 / 180,
        BAR_W=27 / 180,
        LEDGER_W=22 / 180,
        LEDGER_EXT=48 / 180,
        BEAM_T=0.5,
        BEAM_PITCH=0.75,
        DOT_GAP=0.5,
        DOT_R=0.2,
        GRACE_SCALE=0.75,
    ),
    "op62": dict(
        font="Leland",
        engraved=True,
        glyph_font={"accidentalFlat": "Leipzig", "accidentalDoubleFlat": "Leipzig"},
        STAFF_LINE_W=0.13,
        STEM_W=0.12,
        BAR_W=0.16,
        LEDGER_W=0.16,
        LEDGER_EXT=0.4,
        BEAM_T=0.65,
        BEAM_PITCH=0.75,
        DOT_GAP=0.3,
        DOT_R=0.0,
        GRACE_SCALE=0.65,
    ),
}
STYLE = {"name": "verovio"}


def set_style(name: str) -> None:
    """Switch the drawing style (glyphs and the drawing constants and rules of this module)."""
    st = STYLES[name]
    glyphs.GLYPH_FONT.clear()
    glyphs.GLYPH_FONT.update(st["glyph_font"])
    glyphs.set_engraved(st["engraved"])
    glyphs.set_font(st["font"])
    globals().update({k: v for k, v in st.items() if k.isupper()})
    STYLE["name"] = name
    _metrics()


def _vrv() -> bool:
    return STYLE["name"] == "verovio"


@dataclass
class Options:
    width: float = 130.0  # staff width in staff spaces (Breitkopf line: 120-132)
    model: SpacingModel | None = None
    min_staff_gap: float = 6.0  # treble bottom line -> bass top line
    system_gap: float = 5.0  # paper between the lowest ink of a system and the highest of the next
    bar_numbers: bool = True
    justify_last: bool = False
    breaks: list[int] | None = None  # bar indices that start a system (None: fill lines greedily)
    clearance: float | None = None  # override model.clearance
    first_meter: bool = (
        True  # print the meter at the first bar (False: a passage from inside a piece)
    )
    auto_ottava: bool = True  # 8va over high treble runs when the sheet has no ottava of its own
    merge_unisons: bool = (
        True  # one notehead for the same pitch at the same time in one staff (user, phase 11)
    )
    # rests of the upper voice over the notes of another voice (classical two-voice writing); off: a rest only where
    # the hand is silent (user, phase 14: F1 has no voices, a rest over a chord the hand plays makes no sense)
    voice_rests: bool = False
    # comparisons only (phase 10B): x positions taken from a Verovio render of the same content, in staff spaces from
    # the staff start: {"chords": {chord_id: x of the notehead's left edge}, "bars": {bar index: closing barline x},
    # "clef": x, "key": [x, ...], "meter": x, "gap": staff gap}; the engine's own spacing is not used where given
    align: dict | None = None


# ------------------------------------------------------------------ model of the music


@dataclass
class Head:
    note: Note
    pos: int  # staff step, 0 = bottom line
    side: int = 0  # 1 = on the other side of the stem (a second in a chord)
    acc: int | None = None  # printed accidental (alter), None = none
    acc_off: float = 0.0  # left edge of the accidental, distance to the left of the chord x


@dataclass
class Chord:
    staff: int
    voice: int
    bar: int
    time: Fraction
    dur: Fraction
    figure: int
    dots: int
    tuplet: str | None
    beam: int | None
    tgroup: int | None
    notes: list[Note]  # empty: a rest
    graces: list[list[Note]] = field(default_factory=list)
    clef: str = "G2"
    heads: list[Head] = field(default_factory=list)
    grace_heads: list[list[Head]] = field(default_factory=list)
    stem: int = 0  # +1 up, -1 down, 0 none
    beamed: bool = False
    cross: bool = False  # member of a beam group drawn between the staves
    shift: float = 0.0
    left: float = 0.0
    right: float = field(default_factory=lambda: HEAD_W)
    x: float = 0.0
    measure_rest: bool = False
    nvoices: int = 1
    rpos: float | None = None  # staff step of a rest
    stem_end: float | None = None  # y of the stem end (staff-relative; cross-staff: system y)
    ornaments: set[str] = field(default_factory=set)
    ottava: int = 0
    finger_off: float | None = (
        None  # chords with 2+ fingers: distance from x to the right edge of the finger column
    )
    ink_top: float | None = (
        None  # highest ink of ornaments / fingers above the chord (staff y), for tuplets and 8va
    )
    ink_bot: float | None = None  # lowest ink of fingers below the chord
    grace_boxes: list[tuple[int, int, int, int]] | None = (
        None  # Verovio style: grace stems and flags (vrv units)
    )
    grace_x: list[float] | None = None  # comparisons only: x of each grace slot (Options.align)
    beam_line: tuple | None = None
    dot_locs: set[int] | None = None  # Verovio style: staff steps of the dots
    dot_x: float = (
        0.0  # Verovio style: x of the first dot's centre  # Verovio style: (x, y, slope, above) of the drawn beam's outer edge (staff y)
    )

    @property
    def rest(self) -> bool:
        return not self.notes

    @property
    def head_w(self) -> float:
        return WHOLE_W if self.figure in (0, 1) else HEAD_W

    @property
    def levels(self) -> int:
        return {8: 1, 16: 2, 32: 3, 64: 4, 128: 5}.get(self.figure, 0)


@dataclass
class Column:
    bar: int
    time: Fraction
    chords: list[Chord]
    left: float = 0.0
    right: float = field(default_factory=lambda: HEAD_W)
    accidental: bool = False
    rest_only: bool = False
    clef_changes: list[tuple[int, str]] = field(
        default_factory=list
    )  # (staff, clef) drawn before the column
    x: float = 0.0
    lefts: dict[int, float] = field(default_factory=dict)  # per staff
    rights: dict[int, float] = field(default_factory=dict)


@dataclass
class BarLayout:
    index: int
    start: Fraction
    end: Fraction
    columns: list[Column]
    lead: float = 0.0  # barline -> first column x (after the start items)
    start_items: float = 0.0  # width of key / meter changes drawn after the barline
    trail: float = 0.0  # width of clef changes drawn before the closing barline
    trail_clefs: list[tuple[int, str]] = field(default_factory=list)
    nat: list[float] = field(default_factory=list)  # natural gaps (columns, then column -> barline)
    mins: list[float] = field(default_factory=list)
    x0: float = 0.0
    x1: float = 0.0
    key_change: bool = False
    meter_change: bool = False
    measure_rests: list[Chord] = field(default_factory=list)


@dataclass
class Prim:
    kind: str  # "g" glyph (name, x, y, scale, rotate), "l" line (x1, y1, x2, y2, w, dash), "p" polygon (points)
    staff: int  # 1 / 2: y relative to that staff's top line; 0: system y (treble top line = 0)
    data: tuple
    cls: str = ""
    ref: str = (
        ""  # a notehead: "<frame>:<midi>" of its note (``note_ref``), for the player to light it
    )


def note_ref(n: Note) -> str:
    """The identifier of a note in the SVG (``data-note``): its matrix column and MIDI pitch, ``"412:64"``; a notehead
    that also stands for unisons merged into it (``merge_unisons``) names them all, ``"29:82 31:82"``.
    """
    if n.ref is not None:
        return n.ref
    return f"{n.frame}:{n.midi}" if n.frame is not None else ""


@dataclass
class System:
    bars: list[BarLayout]
    width: float  # staff line length
    header: float
    prims: list[Prim] = field(default_factory=list)
    gap: float = 6.0
    top: float = 0.0  # page y of the treble top line
    ymin: float = 0.0
    ymax: float = 0.0

    @property
    def bass_top(self) -> float:
        return 4 + self.gap


@dataclass
class Engraving:
    systems: list[System]
    width: float
    height: float
    columns: list[
        dict
    ]  # for metrics: system, bar, label, time, x (notehead left edge), staves, ioi
    beams: list[dict]  # drawn beam groups: id, system, staves, members
    margin: float = 3.0


# ------------------------------------------------------------------ helpers


def _dur(n: Note) -> Fraction:
    q = figure_quarters(n.figure, n.dots)
    if n.tuplet:
        a, b = (int(x) for x in n.tuplet.split("/"))
        q = q * b / a
    return q


def _written_octave(n: Note) -> int:
    return n.octave - (n.ottava or 0)


def pos_of(n: Note, clef: str) -> int:
    return 7 * _written_octave(n) + STEPS.index(n.step) - BOTTOM_LINE.get(clef, 30)


def y_of(pos: float) -> float:
    return (8 - pos) * 0.5


def key_alters(fifths: int) -> dict[str, int]:
    out = {s: 0 for s in STEPS}
    if fifths > 0:
        for s in SHARP_ORDER[:fifths]:
            out[s] = 1
    elif fifths < 0:
        for s in SHARP_ORDER[::-1][:-fifths]:
            out[s] = -1
    return out


def _compound(meter: str) -> bool:
    num, den = (int(x) for x in meter.split("/"))
    return num in (6, 9, 12) and den >= 8


REST_VALUES = [
    (Fraction(4), 1, 0),
    (Fraction(3), 2, 1),
    (Fraction(2), 2, 0),
    (Fraction(3, 2), 4, 1),
    (Fraction(1), 4, 0),
    (Fraction(3, 4), 8, 1),
    (Fraction(1, 2), 8, 0),
    (Fraction(1, 4), 16, 0),
    (Fraction(1, 8), 32, 0),
    (Fraction(1, 16), 64, 0),
]


def rest_split(start: Fraction, end: Fraction, bar_start: Fraction, meter: str) -> list[tuple]:
    """Rests that fill ``start..end``: the longest value that fits and starts on a multiple of itself
    (dotted values only in compound meters); a gap that no value fits is filled with triplet rests.
    """
    out = []
    t = start
    comp = _compound(meter)
    unit = beat_unit(meter)
    triplet = any((x - bar_start).denominator % 3 == 0 for x in (start, end))
    while end - t >= Fraction(1, 32):
        rem, off = end - t, t - bar_start
        choice = None
        if (
            triplet
        ):  # a gap on the triplet grid: triplet rests (inside the tuplet bracket of their notes)
            for v, fig, dots in REST_VALUES:
                tv = v * Fraction(2, 3)
                if not dots and tv <= rem and (off % unit) % tv == 0 and (off % unit) + tv <= unit:
                    choice = (tv, fig, 0, "3/2")
                    break
            if choice is not None:
                out.append((t, *choice))
                t += choice[0]
                continue
        for v, fig, dots in REST_VALUES:
            if dots and not comp:
                continue
            if v > rem:
                continue
            whole_beats = v % unit == 0 and off % unit == 0 and off % v == 0
            in_beat = v <= unit and (off % unit) + v <= unit and (off % unit) % v == 0
            if whole_beats or in_beat:
                choice = (v, fig, dots, None)
                break
        if choice is None:
            for v, fig, dots in REST_VALUES:
                if not dots and v * Fraction(2, 3) <= rem:
                    choice = (v * Fraction(2, 3), fig, 0, "3/2")
                    break
        if choice is None:
            break
        out.append((t, *choice))
        t += choice[0]
    return out


# ------------------------------------------------------------------ building the chords


def _clef_timeline(sheet: Sheet) -> dict[int, list[tuple[Fraction, str]]]:
    tl = {s: [(Fraction(-(10**6)), sheet.clefs.get(s, DEFAULT_CLEF[s]))] for s in (1, 2)}
    for t, s, c in sorted(sheet.clef_changes, key=lambda c: c[0]):
        if s in tl:
            tl[s].append((Fraction(t), c))
    return tl


def _clef_at(tl, staff: int, t: Fraction) -> str:
    c = tl[staff][0][1]
    for when, clef in tl[staff]:
        if when <= t:
            c = clef
        else:
            break
    return c


def build_chords(
    sheet: Sheet, voice_rests: bool = False
) -> tuple[dict[tuple[int, int], list[Chord]], list[Chord]]:
    """Chords and rests per (bar, staff), and the whole-bar rests. Rests fill the gaps of the first voice
    (``voice_rests``) or only the times when no voice of the staff sounds."""
    bars = sheet.bars
    tl = _clef_timeline(sheet)
    by_bar: dict[tuple[int, int], list[Note]] = defaultdict(list)
    starts = [b.start for b in bars]
    for n in sheet.notes:
        if n.time is None or n.staff not in (1, 2):
            continue
        bi = max(0, sum(1 for s in starts if s <= n.time) - 1)
        by_bar[(bi, n.staff)].append(n)
    # a beam group with notes on both staves fills its time span in both staves
    spans: dict[int, list[Note]] = defaultdict(list)
    for n in sheet.notes:
        if n.beam is not None and n.time is not None and not n.grace and (n.figure or 0) >= 8:
            spans[n.beam].append(n)
    occupied: dict[int, list[tuple[Fraction, Fraction]]] = {1: [], 2: []}
    for ns in spans.values():
        if len({n.time for n in ns}) < 2:
            continue
        span = (min(n.time for n in ns), max(n.time + _dur(n) for n in ns))
        for st in {n.staff for n in ns} if len({n.staff for n in ns}) == 1 else (1, 2):
            occupied[st].append(span)
    out: dict[tuple[int, int], list[Chord]] = {}
    for bi, bar in enumerate(bars):
        end = bar.start + bar.dur
        for staff in (1, 2):
            ns = by_bar.get((bi, staff), [])
            mains = [n for n in ns if not n.grace and n.figure is not None]
            graces = [n for n in ns if n.grace]
            groups: dict[tuple, list[Note]] = defaultdict(list)
            for n in mains:
                groups[
                    (n.time, n.figure, n.dots, n.tuplet, n.beam if (n.figure or 0) >= 8 else None)
                ].append(n)
            chords = []
            for (t, fig, dots, tup, beam), notes in groups.items():
                notes.sort(key=lambda n: n.midi)
                orn = set()
                for n in notes:
                    orn.update(n.ornaments)
                chords.append(
                    Chord(
                        staff,
                        0,
                        bi,
                        t,
                        _dur(notes[0]),
                        fig,
                        dots,
                        tup,
                        beam,
                        notes[0].tgroup,
                        notes,
                        clef=_clef_at(tl, staff, t),
                        ornaments=orn,
                        ottava=notes[0].ottava or 0,
                    )
                )
            # grace notes: attached to the earliest chord at their time (slots in order)
            for t in sorted({g.time for g in graces}):
                gs = [g for g in graces if g.time == t]
                slots = defaultdict(list)
                for g in gs:
                    slots[g.gslot].append(g)
                target = [c for c in chords if c.time == t]
                if target:
                    target.sort(key=lambda c: -c.notes[-1].midi)
                    target[0].graces = [
                        sorted(slots[k], key=lambda n: n.midi) for k in sorted(slots)
                    ]
            _assign_voices(chords)
            nv = 1 + max((c.voice for c in chords), default=0)
            for c in chords:
                c.nvoices = nv
            # rests of the first voice, or of the whole staff
            v0 = sorted(
                (c for c in chords if c.voice == 0 or not voice_rests), key=lambda c: c.time
            )
            rests = []
            if not chords:
                rests.append(
                    Chord(
                        staff,
                        0,
                        bi,
                        bar.start,
                        bar.dur,
                        1,
                        0,
                        None,
                        None,
                        None,
                        [],
                        clef=_clef_at(tl, staff, bar.start),
                        measure_rest=True,
                    )
                )
            else:
                cursor = bar.start
                v0 = sorted(
                    v0
                    + [
                        Chord(
                            staff,
                            0,
                            bi,
                            max(a, bar.start),
                            min(b, end) - max(a, bar.start),
                            4,
                            0,
                            None,
                            None,
                            None,
                            [],
                            measure_rest=True,
                        )
                        for a, b in occupied[staff]
                        if a < end and b > bar.start
                    ],
                    key=lambda c: c.time,
                )
                for c in v0 + [None]:
                    t = c.time if c else end
                    if t > cursor:
                        for rt, length, fig, dots, tup in rest_split(
                            cursor, t, bar.start, bar.meter
                        ):
                            rests.append(
                                Chord(
                                    staff,
                                    0,
                                    bi,
                                    rt,
                                    length,
                                    fig,
                                    dots,
                                    tup,
                                    None,
                                    None,
                                    [],
                                    clef=_clef_at(tl, staff, rt),
                                    nvoices=nv,
                                )
                            )
                    if c:
                        cursor = max(cursor, c.time + c.dur)
            unit = beat_unit(bar.meter)
            for r in rests:
                if not r.tuplet:
                    continue
                beat = (r.time - bar.start) // unit
                same = [
                    c
                    for c in v0
                    if c.tuplet and c.tgroup is not None and (c.time - bar.start) // unit == beat
                ]
                if same:
                    r.tgroup = min(same, key=lambda c: abs(c.time - r.time)).tgroup
            out[(bi, staff)] = sorted(chords + rests, key=lambda c: (c.time, c.voice))
    return out, []


def _assign_voices(chords: list[Chord]) -> None:
    """Units (a whole beam group, or one chord) go into the first voice that is free at their start;
    with several voices the highest one (mean pitch) becomes voice 0."""
    units: dict[object, list[Chord]] = defaultdict(list)
    for c in chords:
        units[("b", c.beam) if c.beam is not None else ("c", id(c))].append(c)
    ordered = sorted(units.values(), key=lambda u: (min(c.time for c in u), -max(c.dur for c in u)))
    ends: list[Fraction] = []
    members: list[list[Chord]] = []
    for u in ordered:
        u.sort(key=lambda c: c.time)
        # a beam unit whose chords overlap each other is split into chords
        ok = all(a.time + a.dur <= b.time for a, b in zip(u, u[1:]))
        parts = [u] if ok else [[c] for c in u]
        for part in parts:
            start = part[0].time
            stop = max(c.time + c.dur for c in part)
            for i, e in enumerate(ends):
                if e <= start:
                    members[i].extend(part)
                    ends[i] = stop
                    break
            else:
                members.append(list(part))
                ends.append(stop)
    order = sorted(
        range(len(members)),
        key=lambda i: -sum(n.midi for c in members[i] for n in c.notes)
        / max(1, sum(len(c.notes) for c in members[i])),
    )
    for v, i in enumerate(order):
        for c in members[i]:
            c.voice = v


# ------------------------------------------------------------------ accidentals, heads, stems


def _accidentals(sheet: Sheet, chords: dict[tuple[int, int], list[Chord]]) -> None:
    for (bi, staff), cs in chords.items():
        key = key_alters(sheet.bars[bi].key)
        state: dict[tuple[str, int], int] = {}
        events = []
        for c in cs:
            for k, slot in enumerate(c.graces):
                events.append((c.time, 0, k, slot, c, True, k))
            if c.notes:
                events.append((c.time, 1, 0, c.notes, c, False, 0))
        events.sort(key=lambda e: (e[0], e[1], e[2]))
        for _, _, _, notes, c, is_grace, k in events:
            heads = []
            for n in notes:
                h = Head(n, pos_of(n, c.clef))
                wk = (n.step, _written_octave(n))
                cur = state.get(wk, key[n.step])
                if n.alter != cur:
                    h.acc = n.alter
                state[wk] = n.alter
                heads.append(h)
            if is_grace:
                while len(c.grace_heads) <= k:
                    c.grace_heads.append([])
                c.grace_heads[k] = heads
            else:
                c.heads = heads


def _sides(heads: list[Head], stem: int) -> None:
    order = sorted(heads, key=lambda h: h.pos, reverse=(stem < 0))
    prev = None
    for h in order:
        h.side = 0
        # a second; Verovio also moves a unison of two spellings (e.g. B and Bb) to the other side
        if (
            prev is not None
            and prev.side == 0
            and (abs(h.pos - prev.pos) == 1 or (_vrv() and h.pos == prev.pos))
        ):
            h.side = 1
        prev = h


# Left-hand beam groups (lower staff): the beam goes below the notes unless the group sits high above the staff
# (Chopin first editions: beam below in 82.5 % of 378 lower-staff groups, 92 % of wide arpeggios; above only when the
# mean is > 6 steps above the middle line). The farthest-note rule predicts these prints in 61 %; this rule in 83 %.
# User choice 2026-10-20 (E09 README §9). The upper staff keeps the farthest-note rule.
LH_BEAM_ABOVE_FROM = 6  # staff steps of the group's mean above the middle line


def _stem_by_position(positions: list[int]) -> int:
    hi, lo = max(positions) - 4, 4 - min(positions)
    return -1 if hi > lo else 1 if lo > hi else -1


def _stems(chords: dict[tuple[int, int], list[Chord]]) -> dict[int, list[Chord]]:
    groups: dict[int, list[Chord]] = defaultdict(list)
    for cs in chords.values():
        for c in cs:
            if c.notes and c.beam is not None and c.figure >= 8:
                groups[c.beam].append(c)
    beams = {}
    for bid, members in groups.items():
        if len({c.time for c in members}) < 2:
            continue
        members.sort(key=lambda c: (c.time, c.staff))
        beams[bid] = members
        staves = {c.staff for c in members}
        for c in members:
            c.beamed = True
        if len(staves) == 2:
            for c in members:
                c.cross = True
                c.stem = -1 if c.staff == 1 else 1
            continue
        multi = [c for c in members if c.nvoices > 1]
        if multi and _vrv():
            cs = chords[(members[0].bar, members[0].staff)]
            if (
                _sounding_voices(
                    members[0], cs, members[0].time, max(c.time + c.dur for c in members)
                )
                < 2
            ):
                multi = []
        if multi:
            d = 1 if multi[0].voice == 0 else -1
        elif _vrv():
            d = (
                1
                if vrv._place([vrv.Coord(0, [h.pos for h in c.heads], 3) for c in members], None)
                else -1
            )
        elif members[0].staff == 2:
            ps = [h.pos for c in members for h in c.heads]
            d = 1 if sum(ps) / len(ps) - 4 > LH_BEAM_ABOVE_FROM else -1
        else:
            d = _stem_by_position([h.pos for c in members for h in c.heads])
        for c in members:
            c.stem = d
    for cs in chords.values():
        for c in cs:
            if not c.notes:
                continue
            if not c.beamed:
                if c.figure in (0, 1):
                    c.stem = 0
                elif c.nvoices > 1 and (
                    not _vrv() or _sounding_voices(c, chords[(c.bar, c.staff)]) > 1
                ):
                    c.stem = 1 if c.voice == 0 else -1
                elif _vrv():
                    c.stem = 1 if vrv.chord_stem_up([h.pos for h in c.heads]) else -1
                else:
                    c.stem = _stem_by_position([h.pos for h in c.heads])
            _sides(c.heads, c.stem if c.stem else 1)
    return beams


def _plan_accidentals(heads: list[Head], scale: float = 1.0) -> float:
    """vexflow-v2's rule: top-down, each accidental in the innermost column where its box does not
    overlap another (Bravura boxes + 0.16 clearance). Returns the total width; sets ``acc_off``."""
    written = sorted((h for h in heads if h.acc is not None), key=lambda h: -h.pos)
    if not written:
        return 0.0
    cols: list[list[tuple[float, float]]] = []
    widths: list[float] = []
    which: dict[int, int] = {}
    for h in written:
        b = box(ACC_GLYPH[h.acc])
        base = -h.pos * 0.5
        ext = (base - b.top * scale, base - b.bottom * scale)
        k = 0
        while k < len(cols) and any(
            ext[0] < e[1] + ACC_GAP and e[0] < ext[1] + ACC_GAP for e in cols[k]
        ):
            k += 1
        if k == len(cols):
            cols.append([])
            widths.append(0.0)
        cols[k].append(ext)
        widths[k] = max(widths[k], b.width * scale)
        which[id(h)] = k
    for h in written:
        k = which[id(h)]
        h.acc_off = ACC_GAP * scale * (k + 1) + sum(widths[: k + 1])
    return sum(widths) + ACC_GAP * scale * len(widths)


def _head_dx(c: Chord, h: Head) -> float:
    """x of a head relative to the chord x (a head on the other side of the stem: a second in a chord)."""
    return (c.head_w - STEM_W if c.stem > 0 else -(c.head_w - STEM_W)) * h.side


def _column_accidentals_vrv(cs: list[Chord], aligned: bool = False) -> None:
    """Verovio places the accidentals of every voice at one time of a staff together (``AdjustAccidXFunctor`` runs
    per alignment): redo the chords of a column that has two or more voices."""
    k = vrv.VU
    by_time: dict[tuple[int, Fraction], list[Chord]] = defaultdict(list)
    for c in cs:
        if c.notes:
            by_time[(c.staff, c.time)].append(c)
    for group in by_time.values():
        if len(group) < 2 or not any(h.acc is not None for c in group for h in c.heads):
            continue
        heads, owner, stems = [], [], []
        base = min(c.x for c in group)
        for c in group:
            if aligned:  # comparisons: voices at Verovio's x (Options.align), no engine voice shift
                c.shift = c.x - base
            glyph = (
                "noteheadWhole"
                if c.figure in (0, 1)
                else "noteheadHalf" if c.figure == 2 else "noteheadBlack"
            )
            for h in c.heads:
                heads.append(
                    (
                        round((c.shift + _head_dx(c, h)) * k),
                        h.pos,
                        ACC_GLYPH[h.acc] if h.acc is not None else None,
                        glyph,
                    )
                )
                owner.append((c, h))
            if c.figure >= 2 and c.stem:
                locs = [h.pos for h in c.heads]
                if c.stem < 0:
                    stems.append(
                        (
                            round(c.shift * k) + vrv.STEM_W // 2,
                            vrv.note_y(max(locs)) - 28,
                            vrv.note_y(min(locs)) - 630,
                        )
                    )
                else:
                    sx = round((c.shift + c.head_w) * k) - vrv.STEM_W // 2
                    stems.append((sx, vrv.note_y(min(locs)) + 28, vrv.note_y(max(locs)) + 630))
        for (c, h), lx in zip(owner, vrv.place_accidentals(heads, stems)):
            if lx is not None:
                h.acc_off = (c.shift * k - lx) / k
                c.left = max(c.left, h.acc_off)
        if aligned:
            for c in group:
                c.shift = 0.0


def _plan_accidentals_vrv(c: Chord) -> float:
    """Verovio's accidental placement (``vrv.place_accidentals``); ``acc_off`` = distance from the chord x to the
    accidental's left edge. Returns the room needed on the left."""
    if not any(h.acc is not None for h in c.heads):
        return 0.0
    k = vrv.VU
    glyph = (
        "noteheadWhole"
        if c.figure in (0, 1)
        else "noteheadHalf" if c.figure == 2 else "noteheadBlack"
    )
    heads = [
        (round(_head_dx(c, h) * k), h.pos, ACC_GLYPH[h.acc] if h.acc is not None else None)
        for h in c.heads
    ]
    stem = None
    if c.stem < 0 and c.figure >= 2:
        locs = [h.pos for h in c.heads]
        stem = (vrv.STEM_W // 2, vrv.note_y(max(locs)) - 28, vrv.note_y(min(locs)) - 630)
    lefts = vrv.place_accidentals(heads, stem, glyph)
    out = 0.0
    for h, lx in zip(c.heads, lefts):
        if lx is not None:
            h.acc_off = -lx / k
            out = max(out, h.acc_off)
    return out


def _extents(c: Chord) -> None:
    """Room the chord needs left and right of its x (the left edge of a normal notehead)."""
    if c.rest:
        g = box(REST_GLYPH.get(c.figure, "restQuarter"))
        c.left, c.right = 0.0, max(g.width, 1.0) + (DOT_GAP + 0.45 * c.dots if c.dots else 0)
        return
    hw = c.head_w
    left = 0.0
    if c.stem < 0 and any(h.side for h in c.heads):
        left += hw
    if _vrv():
        left = max(left, _plan_accidentals_vrv(c))
    else:
        left += _plan_accidentals(c.heads)
    c.finger_off = None
    if (
        sum(1 for n in c.notes if n.finger) >= 2
    ):  # chord fingers: one column left of the accidentals (as printed)
        c.finger_off = left + FINGER_GAP
        left += FINGER_GAP + _finger_w()
    if "arpeggio" in c.ornaments:
        left += 1.2
    for slot in c.grace_heads:
        acc = _plan_accidentals(slot, GRACE_SCALE)
        left += HEAD_W * GRACE_SCALE + 0.5 + acc
    c.left = left
    right = hw + (hw if c.stem > 0 and any(h.side for h in c.heads) else 0)
    if c.dots:
        right += DOT_GAP + 0.4 + 0.5 * (c.dots - 1)
    if c.stem > 0 and not c.beamed and c.figure >= 8:
        right = max(right, hw + box(f"flag{FLAGS[c.figure]}Up").width - 0.1)
    c.right = right


def _finger_w() -> float:
    return max(box(f"tuplet{d}").width for d in range(1, 6)) * FINGER_SCALE


def _voice_shifts(cs: list[Chord]) -> None:
    by_time: dict[Fraction, list[Chord]] = defaultdict(list)
    for c in cs:
        if c.notes:
            by_time[c.time].append(c)
    for group in by_time.values():
        if len(group) < 2:
            continue
        group.sort(key=lambda c: c.voice)
        up = group[0]
        for other in group[1:]:
            lo = min(h.pos for h in up.heads)
            hi = max(h.pos for h in other.heads)
            if lo - hi <= 1:
                other.shift = up.head_w + (up.head_w if any(h.side for h in up.heads) else 0)


# ------------------------------------------------------------------ columns and widths


def _key_sig_width(fifths: int) -> float:
    fifths = max(-7, min(7, fifths))
    if not fifths:
        return 0.0
    g = box("accidentalSharp" if fifths > 0 else "accidentalFlat")
    return abs(fifths) * (g.width + 0.2)


def _meter_width(meter: str) -> float:
    num, den = meter.split("/")
    return max(len(num), len(den)) * box("timeSig0").width + 0.2


def header_width(clefs: dict[int, str], fifths: int, meter: str | None) -> float:
    w = 0.8 + box("gClef").width + 0.8 + _key_sig_width(fifths)
    if meter:
        w += 0.6 + _meter_width(meter)
    return w + 0.6


def build_bars(
    sheet: Sheet, chords: dict[tuple[int, int], list[Chord]], model: SpacingModel, clearance: float
) -> list[BarLayout]:
    tl_changes = defaultdict(list)  # bar -> [(time, staff, clef)]
    starts = [b.start for b in sheet.bars]
    for t, s, c in sheet.clef_changes:
        t = Fraction(t)
        bi = max(0, sum(1 for x in starts if x <= t) - 1)
        tl_changes[bi].append((t, s, c))
    out = []
    for bi, bar in enumerate(sheet.bars):
        end = bar.start + bar.dur
        cs = chords[(bi, 1)] + chords[(bi, 2)]
        for staff in (1, 2):
            _voice_shifts(chords[(bi, staff)])
        for c in cs:
            _extents(c)
        if _vrv():
            _column_accidentals_vrv(cs)
        times = sorted({c.time for c in cs if not c.measure_rest})
        cols = []
        for t in times:
            members = [c for c in cs if c.time == t and not c.measure_rest]
            col = Column(bi, t, members)
            for c in members:
                col.lefts[c.staff] = max(col.lefts.get(c.staff, 0.0), c.left - c.shift)
                col.rights[c.staff] = max(col.rights.get(c.staff, 0.0), c.right + c.shift)
            col.left = max(col.lefts.values())
            col.right = max(col.rights.values())
            col.accidental = any(h.acc is not None for c in members for h in c.heads)
            col.rest_only = all(c.rest for c in members)
            cols.append(col)
        bl = BarLayout(bi, bar.start, end, cols, measure_rests=[c for c in cs if c.measure_rest])
        # clef changes: at the bar start -> before the previous barline; else before their column
        for t, s, c in tl_changes.get(bi, []):
            if t == bar.start and bi > 0:
                out[-1].trail_clefs.append((s, c))
                continue
            target = next((col for col in cols if col.time >= t), cols[-1] if cols else None)
            if target is not None:
                target.clef_changes.append((s, c))
                w = box("gClefChange" if c != "F4" else "fClefChange").width + 0.2
                target.lefts[s] = target.lefts.get(s, 0.0) + w
                target.left = max(target.lefts.values())
        if bi > 0:
            prev = sheet.bars[bi - 1]
            bl.key_change = bar.key != prev.key
            bl.meter_change = bar.meter != prev.meter
            if bl.key_change:
                bl.start_items += max(_key_sig_width(bar.key), _key_sig_width(prev.key) * 0.5) + 1.0
            if bl.meter_change:
                bl.start_items += _meter_width(bar.meter) + 1.0
        out.append(bl)
    for bl in out:
        cols = bl.columns
        bl.nat, bl.mins = [], []
        for i, col in enumerate(cols):
            nxt = cols[i + 1] if i + 1 < len(cols) else None
            t_next = nxt.time if nxt else bl.end
            ioi = float(t_next - col.time)
            g = model.gap(ioi) * (model.rest if col.rest_only else 1.0)
            if nxt:
                g += model.accidental if nxt.accidental else 0.0
                bl.nat.append(g)
                need = max(col.rights.get(st, 0.0) + nxt.lefts.get(st, 0.0) for st in (1, 2))
                need = max(need, HEAD_W)  # two columns never share x
                bl.mins.append(need + clearance)
            else:
                bl.nat.append(model.to_barline * g + HEAD_W / 2)
                bl.mins.append(col.right + 0.6)
        if bl.trail_clefs:
            bl.trail = CHANGE_CLEF_W + 0.4
        first_left = cols[0].left if cols else 0.0
        bl.lead = (
            max(model.lead - HEAD_W / 2, first_left + (1.0 if first_left > 0.5 else 0.6))
            + bl.start_items
        )
        if not cols:
            bl.nat, bl.mins = [model.gap(float(bl.end - bl.start))], [4.0]
    return out


def _bar_width(bl: BarLayout, e: float) -> float:
    return bl.lead + bl.trail + sum(max(n + e, m) for n, m in zip(bl.nat, bl.mins))


def _first_lead(bl: BarLayout) -> float:
    """At a system start the lead is counted from the end of the header."""
    first_left = bl.columns[0].left if bl.columns else 0.0
    return max(1.2, first_left + 0.8)


def _system_width(bars: list[BarLayout], e: float, header: float) -> float:
    w = header
    for k, bl in enumerate(bars):
        w += _bar_width(bl, e) - (bl.lead - _first_lead(bl) if k == 0 else 0)
    return w


def _solve_e(bars: list[BarLayout], header: float, target: float) -> float:
    lo, hi = -10.0, 60.0
    if _system_width(bars, lo, header) > target:
        return lo
    for _ in range(60):
        mid = (lo + hi) / 2
        if _system_width(bars, mid, header) > target:
            hi = mid
        else:
            lo = mid
    return lo


def break_lines(
    sheet: Sheet, bars: list[BarLayout], opts: Options
) -> list[tuple[list[BarLayout], float, float]]:
    """Systems as (bars, header width, justification e)."""
    systems = []
    i = 0
    breaks = set(opts.breaks or [])
    while i < len(bars):
        b0 = sheet.bars[i]
        show = (i == 0 and opts.first_meter) or (i > 0 and b0.meter != sheet.bars[i - 1].meter)
        header = header_width({}, b0.key, b0.meter if show else None)
        j = i + 1
        if opts.breaks is not None:
            while j < len(bars) and j not in breaks:
                j += 1
        else:
            while j < len(bars):
                b = sheet.bars[j]
                if b.meter != b0.meter and False:
                    break
                if _system_width(bars[i : j + 1], 0.0, header) > opts.width:
                    break
                j += 1
        group = bars[i:j]
        last = j >= len(bars)
        natural = _system_width(group, 0.0, header)
        if last and not opts.justify_last and natural < 0.8 * opts.width and opts.breaks is None:
            e = 0.0
        else:
            e = _solve_e(group, header, opts.width)
        systems.append((group, header, e))
        i = j
    return systems


# ------------------------------------------------------------------ drawing


class Pen:
    def __init__(self):
        self.prims: list[Prim] = []

    def g(self, staff, name, x, y, scale=1.0, rot=0.0, cls="", ref=""):
        self.prims.append(Prim("g", staff, (name, x, y, scale, rot), cls, ref))

    def l(self, staff, x1, y1, x2, y2, w, dash=None, cls=""):
        self.prims.append(Prim("l", staff, (x1, y1, x2, y2, w, dash), cls))

    def p(self, staff, pts, cls=""):
        self.prims.append(Prim("p", staff, tuple(pts), cls))

    def e(self, staff, x, y, r, cls=""):
        """A filled circle (Verovio's augmentation dots)."""
        self.prims.append(Prim("e", staff, (x, y, r), cls))

    def z(self, staff, segs, w, cls=""):
        """A filled and stroked path: ``segs`` = [("M", x, y), ("C", x1, y1, x2, y2, x, y), ...] (Verovio's brace)."""
        self.prims.append(Prim("z", staff, (tuple(segs), w), cls))


def _prim_yrange(p: Prim) -> tuple[float, float]:
    if p.kind == "g":
        name, x, y, s, rot = p.data
        b = box(name)
        if rot:
            return y - b.width * s, y + 0.3
        return y - b.top * s, y - b.bottom * s
    if p.kind == "l":
        return min(p.data[1], p.data[3]) - p.data[4] / 2, max(p.data[1], p.data[3]) + p.data[4] / 2
    if p.kind == "b":
        return p.data[1], p.data[2]
    if p.kind == "e":
        return p.data[1] - p.data[2], p.data[1] + p.data[2]
    if p.kind == "z":
        ys = [v for seg in p.data[0] for v in seg[2::2]]
        return min(ys), max(ys)
    ys = [pt[1] for pt in p.data]
    return min(ys), max(ys)


def _draw_header(
    pen: Pen,
    sheet: Sheet,
    bi: int,
    clefs: dict[int, str],
    meter: str | None,
    align: dict | None = None,
) -> None:
    fifths = sheet.bars[bi].key
    align = align or {}
    for staff in (1, 2):
        clef = clefs[staff]
        cx = align.get("clef", 0.8)
        if clef == "F4":
            pen.g(staff, "fClef", cx, y_of(6))
        else:
            pen.g(staff, "gClef", cx, y_of(2))
        x = 0.8 + box("gClef").width + 0.8
        x = _draw_key(pen, staff, clef, fifths, x, align.get("key"))
        if meter:
            _draw_meter(pen, staff, meter, align.get("meter", x + 0.6))


def _draw_key(
    pen: Pen, staff: int, clef: str, fifths: int, x: float, xs: list[float] | None = None
) -> float:
    fifths = max(-7, min(7, fifths))
    if not fifths:
        return x
    name = "accidentalSharp" if fifths > 0 else "accidentalFlat"
    positions = SHARP_POS if fifths > 0 else FLAT_POS
    shift = -2 if clef == "F4" else 0
    for k in range(abs(fifths)):
        if xs and k < len(xs):
            x = xs[k]
        pen.g(staff, name, x, y_of(positions[k] + shift))
        x += box(name).width + 0.2
    return x


def _draw_meter(pen: Pen, staff: int, meter: str, x: float) -> None:
    num, den = meter.split("/")
    w = _meter_width(meter) - 0.2
    for text, pos in ((num, 6), (den, 2)):
        tw = len(text) * box("timeSig0").width
        xx = x + (w - tw) / 2
        for ch in text:
            pen.g(staff, f"timeSig{ch}", xx, y_of(pos))
            xx += box("timeSig0").width


def _draw_number(
    pen: Pen, staff: int, text: str, x: float, y: float, scale: float = 0.75, center=True
) -> None:
    w = sum(box(f"tuplet{ch}").width for ch in text) * scale
    xx = x - w / 2 if center else x
    for ch in text:
        pen.g(staff, f"tuplet{ch}", xx, y, scale)
        xx += box(f"tuplet{ch}").width * scale


def _rest_pos(c: Chord) -> float:
    if c.rpos is not None:
        return c.rpos
    return {1: 6, 0: 4, 2: 4}.get(c.figure, 4)


def _sounding_voices(c: Chord, cs: list[Chord], start=None, end=None) -> int:
    """Voices with a note or a rest during the chord (or [start, end)): Verovio's ``GetLayerCountForTimeSpanOf``,
    which decides whether voice stems (up / down) are used."""
    a = c.time if start is None else start
    b = c.time + c.dur if end is None else end
    return len({o.voice for o in cs if o.time < b and o.time + o.dur > a})


def _rest_positions(chords: dict[tuple[int, int], list[Chord]]) -> None:
    """A rest of the upper voice sits above the notes of the other voices that sound at its time."""
    if _vrv():
        return _rest_positions_vrv(chords)
    for cs in chords.values():
        for r in cs:
            if not r.rest or r.measure_rest or r.nvoices < 2:
                continue
            base = {1: 6, 0: 4, 2: 4}.get(r.figure, 4)
            end = r.time + r.dur
            hi = max(
                (
                    h.pos
                    for c in cs
                    if c.notes and c.voice > 0 and c.time < end and c.time + c.dur > r.time
                    for h in c.heads
                ),
                default=None,
            )
            if hi is None:
                r.rpos = base
                continue
            b = box(REST_GLYPH.get(r.figure, "restQuarter"))
            r.rpos = max(base, hi + 2 - math.floor(2 * b.bottom))


def _rest_positions_vrv(chords: dict[tuple[int, int], list[Chord]]) -> None:
    """Verovio's rest heights in a staff with two voices (``vrv.rest_loc``); the engine's rests are in voice 0."""
    for cs in chords.values():
        for r in cs:
            if not r.rest or r.measure_rest or r.nvoices < 2:
                continue
            end = r.time + r.dur
            others = [
                c
                for c in cs
                if c.notes and c.voice != r.voice and c.time < end and c.time + c.dur > r.time
            ]
            if not others:
                continue
            top = r.voice < min(c.voice for c in others)
            locs = [
                ((max if top else min)(h.pos for h in c.heads), c.time == r.time) for c in others
            ]
            own = sorted((c for c in cs if c.notes and c.voice == r.voice), key=lambda c: c.time)
            prev = next((c for c in reversed(own) if c.time < r.time), None)
            nxt = next((c for c in own if c.time > r.time), None)
            near = (
                (lambda c: min(h.pos for h in c.heads))
                if top
                else (lambda c: max(h.pos for h in c.heads))
            )
            r.rpos = vrv.rest_loc(
                r.figure,
                top,
                locs,
                near(prev) if prev else None,
                near(nxt) if nxt else None,
                rest_overlap=all(len(c.notes) > 1 for c in others),
            )


def _draw_chord(pen: Pen, c: Chord, cls: str = "") -> None:
    staff = c.staff
    x = c.x + c.shift
    if c.rest:
        name = REST_GLYPH.get(c.figure, "restQuarter")
        pen.g(staff, name, x, y_of(_rest_pos(c)), cls="rest")
        if c.dots:
            for k in range(c.dots):
                if DOT_R:
                    pen.e(staff, x + box(name).width + DOT_GAP + 0.5 * k, y_of(5), DOT_R)
                else:
                    pen.g(
                        staff, "augmentationDot", x + box(name).width + DOT_GAP + 0.5 * k, y_of(5)
                    )
        return
    hw = c.head_w
    head = (
        "noteheadWhole"
        if c.figure in (0, 1)
        else "noteheadHalf" if c.figure == 2 else "noteheadBlack"
    )
    # ledger lines (Verovio style: per measure and staff, ``_vrv_ledgers``)
    for h in ([] if _vrv() else c.heads):
        hx = x + (hw - STEM_W if c.stem > 0 else -(hw - STEM_W)) * h.side
        if h.pos <= -2:
            for p in range(-2, h.pos - 1, -2):
                pen.l(staff, hx - LEDGER_EXT, y_of(p), hx + hw + LEDGER_EXT, y_of(p), LEDGER_W)
        if h.pos >= 10:
            for p in range(10, h.pos + 1, 2):
                pen.l(staff, hx - LEDGER_EXT, y_of(p), hx + hw + LEDGER_EXT, y_of(p), LEDGER_W)
    rightmost = x + hw
    for h in c.heads:
        hx = x + (hw - STEM_W if c.stem > 0 else -(hw - STEM_W)) * h.side
        rightmost = max(rightmost, hx + hw)
        pen.g(
            staff,
            head,
            hx,
            y_of(h.pos),
            cls=f"{cls or 'nh'} {h.note.mark}" if h.note.mark else cls or "nh",
            ref=note_ref(h.note),
        )
        if h.acc is not None:
            if _vrv():
                pen.g(staff, ACC_GLYPH[h.acc], x - h.acc_off, y_of(h.pos))
            else:
                pen.g(
                    staff,
                    ACC_GLYPH[h.acc],
                    x - (hw if c.stem < 0 and any(k.side for k in c.heads) else 0) - h.acc_off,
                    y_of(h.pos),
                )
    if (
        c.dots and c.dot_locs is not None
    ):  # Verovio style (``_vrv_dots``): spaces and x chosen per column
        for p in sorted(c.dot_locs):
            for k in range(c.dots):
                pen.e(staff, c.dot_x + 0.75 * k, y_of(p), DOT_R)
    elif c.dots:
        done = set()
        for h in c.heads:
            p = h.pos + 1 if h.pos % 2 == 0 else h.pos
            if p in done:
                p -= 2
            done.add(p)
            for k in range(c.dots):
                if DOT_R:
                    pen.e(staff, rightmost + DOT_GAP + 0.5 * k, y_of(p), DOT_R)
                else:
                    pen.g(staff, "augmentationDot", rightmost + DOT_GAP + 0.5 * k, y_of(p))
    if "arpeggio" in c.ornaments and _vrv():  # View::DrawArpeg + AdjustArpegFunctor
        lo, hi = min(h.pos for h in c.heads), max(h.pos for h in c.heads)
        left = min(
            [_head_dx(c, h) for h in c.heads] + [-h.acc_off for h in c.heads if h.acc is not None]
        )
        ax = x + left - 0.5
        adv = 142 / vrv.VU
        length = (y_of(lo) - y_of(hi)) + 1.0
        y = y_of(lo) + 0.5
        for _ in range(int((length + adv / 2) / adv)):
            pen.g(staff, "wiggleArpeggiatoUp", ax, y, 1.0, -90.0)
            y -= adv
    elif "arpeggio" in c.ornaments:
        lo, hi = min(h.pos for h in c.heads), max(h.pos for h in c.heads)
        acc_w = max((h.acc_off for h in c.heads if h.acc is not None), default=0.0)
        ax = x - acc_w - 0.9
        y = y_of(lo) + 0.6
        top = y_of(hi) - 0.6
        seg = box("wiggleArpeggiatoUp").width * 0.78
        while y > top:
            pen.g(staff, "wiggleArpeggiatoUp", ax, y, 1.0, -90.0)
            y -= seg
    if c.graces:
        _draw_graces(pen, c)


def chord_id(c: Chord) -> str:
    """Stable name of a chord or rest (staff, voice, bar, time); measure rests: ``mr<staff>b<bar>``."""
    if c.measure_rest:
        return f"mr{c.staff}b{c.bar}"
    return f"s{c.staff}v{c.voice}b{c.bar}t{c.time.numerator}-{c.time.denominator}"


def _stem_x(c: Chord) -> float:
    x = c.x + c.shift
    return x + c.head_w - STEM_W / 2 if c.stem > 0 else x + STEM_W / 2


def _stem_base(c: Chord) -> float:
    """y where the stem leaves the chord (staff-relative): the head furthest from the stem end."""
    if c.stem > 0:
        return y_of(min(h.pos for h in c.heads)) - 0.17
    return y_of(max(h.pos for h in c.heads)) + 0.17


def _stem_tip_head(c: Chord) -> float:
    """y of the head nearest the stem end."""
    return y_of(max(h.pos for h in c.heads)) if c.stem > 0 else y_of(min(h.pos for h in c.heads))


def _draw_unbeamed_stem(pen: Pen, c: Chord) -> None:
    if c.rest or c.stem == 0 or c.figure in (0, 1):
        return
    if _vrv():
        st = vrv.unbeamed_stem(
            0, [h.pos for h in c.heads], c.stem > 0, c.figure, 2 if c.figure == 2 else 4
        )
        sx = c.x + c.shift + st.x / vrv.VU
        end = -st.y_end / vrv.VU
        pen.l(c.staff, sx, -st.y_start / vrv.VU, sx, end, STEM_W)
        c.stem_end = end
        if c.figure >= 8:
            pen.g(
                c.staff,
                f"flag{FLAGS[c.figure]}{'Up' if c.stem > 0 else 'Down'}",
                sx - STEM_W / 2,
                end,
            )
        _draw_tremolo(pen, c, sx, (_stem_tip_head(c) + end) / 2)
        return
    tip = _stem_tip_head(c)
    length = STEM_LEN + max(0, c.levels - 2) * 0.5
    end = tip - length if c.stem > 0 else tip + length
    if c.stem > 0 and end > 2.0 and c.nvoices == 1:
        end = 2.0
    if c.stem < 0 and end < 2.0 and c.nvoices == 1:
        end = 2.0
    sx = _stem_x(c)
    pen.l(c.staff, sx, _stem_base(c), sx, end, STEM_W)
    c.stem_end = end
    if c.figure >= 8:
        name = f"flag{FLAGS[c.figure]}{'Up' if c.stem > 0 else 'Down'}"
        pen.g(c.staff, name, sx - STEM_W / 2, end)
    _draw_tremolo(pen, c, sx, (tip + end) / 2)


def _draw_tremolo(pen: Pen, c: Chord, sx: float, y: float) -> None:
    if "tremolo" not in c.ornaments:
        return
    if c.stem == 0:
        sx, y = c.x + c.head_w / 2, _stem_tip_head(c) - 2.0
    pen.g(c.staff, "tremolo3" if c.figure <= 4 else "tremolo1", sx, y + 0.5)


def _draw_graces_vrv(pen: Pen, c: Chord, xs: list[tuple[float, list[Head]]]) -> None:
    """Grace notes in Verovio's style: heads, ledger lines, accidentals at 0.75; stems by ``vrv.grace_stem`` or
    ``vrv.beam(cue=True)``; the slash of an acciaccatura as Verovio draws it."""
    s = GRACE_SCALE
    k = vrv.VU
    hw = vrv.HEAD_W / k * s
    ext = vrv.LEDGER_EXT / k * s
    for x, heads in xs:
        for h in heads:
            if h.pos <= -2:
                for p in range(-2, h.pos - 1, -2):
                    pen.l(c.staff, x - ext, y_of(p), x + hw + ext, y_of(p), LEDGER_W)
            if h.pos >= 10:
                for p in range(10, h.pos + 1, 2):
                    pen.l(c.staff, x - ext, y_of(p), x + hw + ext, y_of(p), LEDGER_W)
            pen.g(c.staff, "noteheadBlack", x, y_of(h.pos), s, cls="grace", ref=note_ref(h.note))
            if h.acc is not None:
                pen.g(c.staff, ACC_GLYPH[h.acc], x - h.acc_off, y_of(h.pos), s)
    if len(xs) == 1:
        x, heads = xs[0]
        st = vrv.grace_stem(0, [h.pos for h in heads])
        sx, end = x + st.x / k, -st.y_end / k
        pen.l(c.staff, sx, -st.y_start / k, sx, end, STEM_W)
        pen.g(c.staff, "flag8thUp", sx - STEM_W / 2, end, s)
        fb = box("flag8thUp")
        X = round(sx * k)
        c.grace_boxes = [
            (X - vrv.STEM_W // 2, X + vrv.STEM_W // 2, st.y_end, st.y_start),
            (
                X - vrv.STEM_W // 2,
                X + round(fb.width * s * k),
                st.y_end,
                st.y_end - round((fb.top - fb.bottom) * s * k),
            ),
        ]
        if (
            c.graces[0] and c.graces[0][0].grace == "acc"
        ):  # Verovio's slash (MEI grace="unacc"), measured on its SVG
            pen.l(c.staff, sx - 67 / k, end + 268 / k, sx + 134 / k, end + 67 / k, 21 / k)
        return
    figs = [max(8, g[0].figure or 8) for g in c.graces]
    coords = [
        vrv.Coord(round(x * k), [h.pos for h in heads], vrv.dur_index(f))
        for (x, heads), f in zip(xs, figs)
    ]
    b = vrv.beam(coords, True, cue=True)
    for poly in b.polys:
        pen.p(c.staff, [(px / k, -py / k) for px, py in poly], cls="beam")
    for co in b.coords:
        pen.l(c.staff, co.x / k, -co.stem_start / k, co.x / k, -co.stem_end / k, STEM_W)


def _draw_graces(pen: Pen, c: Chord) -> None:
    s = GRACE_SCALE
    hw = HEAD_W * s
    n = len(c.grace_heads)
    acc_main = max((h.acc_off for h in c.heads if h.acc is not None), default=0.0)
    arp = 1.2 if "arpeggio" in c.ornaments else 0.0
    right = c.x + c.shift - acc_main - arp - 0.4
    xs = []
    for heads in reversed(c.grace_heads):
        acc = _plan_accidentals(heads, s)
        x = right - hw
        xs.append((x, heads))
        right = x - acc - 0.5
    xs.reverse()
    if c.grace_x and len(c.grace_x) == len(xs):
        xs = [(gx, heads) for gx, (_, heads) in zip(c.grace_x, xs)]
    if _vrv():
        return _draw_graces_vrv(pen, c, xs)
    tips = []
    for x, heads in xs:
        for h in heads:
            if h.pos <= -2:
                for p in range(-2, h.pos - 1, -2):
                    pen.l(c.staff, x - 0.25, y_of(p), x + hw + 0.25, y_of(p), LEDGER_W * s)
            if h.pos >= 10:
                for p in range(10, h.pos + 1, 2):
                    pen.l(c.staff, x - 0.25, y_of(p), x + hw + 0.25, y_of(p), LEDGER_W * s)
            pen.g(c.staff, "noteheadBlack", x, y_of(h.pos), s, cls="grace", ref=note_ref(h.note))
            if h.acc is not None:
                pen.g(c.staff, ACC_GLYPH[h.acc], x - h.acc_off, y_of(h.pos), s)
        top = y_of(max(h.pos for h in heads))
        tips.append((x + hw - STEM_W * s / 2, y_of(min(h.pos for h in heads)) - 0.12, top - 2.4))
    if n == 1:
        sx, base, end = tips[0]
        pen.l(c.staff, sx, base, sx, end, STEM_W * s)
        pen.g(c.staff, "flag8thUp", sx - STEM_W * s / 2, end, s)
        if c.graces[0] and c.graces[0][0].grace == "acc":
            pen.l(c.staff, sx - 0.7, end + 1.5, sx + 0.8, end + 0.6, STEM_W)
    else:
        end = min(t[2] for t in tips)
        for sx, base, _ in tips:
            pen.l(c.staff, sx, base, sx, end, STEM_W * s)
        pen.p(
            c.staff,
            [
                (tips[0][0], end),
                (tips[-1][0], end),
                (tips[-1][0], end + BEAM_T * s),
                (tips[0][0], end + BEAM_T * s),
            ],
        )
        levels = max({8: 1, 16: 2, 32: 3}.get(g[0].figure or 8, 1) for g in c.graces)
        for lv in range(1, levels):
            yy = end + BEAM_PITCH * s * lv
            pen.p(
                c.staff,
                [
                    (tips[0][0], yy),
                    (tips[-1][0], yy),
                    (tips[-1][0], yy + BEAM_T * s),
                    (tips[0][0], yy + BEAM_T * s),
                ],
            )


def _slope(first_y: float, last_y: float, steps: int, dx: float) -> float:
    if dx <= 0 or steps == 0:
        return 0.0
    rise = min(BEAM_RISE * abs(last_y - first_y), BEAM_MAX_RISE)
    k = math.copysign(rise, last_y - first_y) / dx
    return max(-BEAM_MAX_SLOPE, min(BEAM_MAX_SLOPE, k))


def _beam_geometry(members: list[Chord]) -> tuple[float, float, float]:
    """(x of first stem, y at the first stem, slope) of the primary beam of a one-staff group;
    y is the outer edge (furthest from the notes)."""
    d = members[0].stem
    xs = [_stem_x(c) for c in members]
    tips = [_stem_tip_head(c) for c in members]
    levels = max(c.levels for c in members)
    min_stem = 3.0 + 0.75 * (levels - 1) if levels else 3.0
    first, last = tips[0], tips[-1]
    steps = round(abs(last - first) * 2)
    # the slant follows the end notes even when an inner note goes past them (the stems of the group stay long
    # enough: y0 below is set by the note that needs the most room)
    k = _slope(first, last, steps, xs[-1] - xs[0])
    x0 = xs[0]
    if d > 0:
        y0 = min(t - min_stem - k * (x - x0) for x, t in zip(xs, tips))
        xc = (xs[0] + xs[-1]) / 2
        if members[0].nvoices == 1:
            y0 = min(y0, 2.0 - k * (xc - x0))
    else:
        y0 = max(t + min_stem - k * (x - x0) for x, t in zip(xs, tips))
        xc = (xs[0] + xs[-1]) / 2
        if members[0].nvoices == 1:
            y0 = max(y0, 2.0 - k * (xc - x0))
    return x0, y0, k


def _beam_polys(
    pen: Pen, staff: int, members: list[Chord], x0: float, y0: float, k: float, sdir: int, beat_of
) -> None:
    """Primary and secondary beams; ``sdir`` = +1 when the levels stack downward from the primary."""
    xs = [_stem_x(c) for c in members]

    def seg(level, xa, xb):
        off = sdir * BEAM_PITCH * (level - 1)
        ya, yb = y0 + k * (xa - x0) + off, y0 + k * (xb - x0) + off
        pts = [
            (xa - STEM_W / 2, ya),
            (xb + STEM_W / 2, yb),
            (xb + STEM_W / 2, yb + sdir * BEAM_T),
            (xa - STEM_W / 2, ya + sdir * BEAM_T),
        ]
        pen.p(staff, pts, cls="beam")

    seg(1, xs[0], xs[-1])
    top = max(c.levels for c in members)
    for level in range(2, top + 1):
        i = 0
        while i < len(members):
            if members[i].levels < level:
                i += 1
                continue
            j = i
            while j + 1 < len(members) and members[j + 1].levels >= level:
                j += 1
            if j > i:
                seg(level, xs[i], xs[j])
            else:
                stub = min(
                    1.1, 0.6 * ((xs[i + 1] - xs[i]) if i + 1 < len(xs) else (xs[i] - xs[i - 1]))
                )
                left = (i == len(members) - 1) or (
                    i > 0
                    and beat_of(members[i]) != 0
                    and members[i - 1].levels < level
                    and beat_of(members[i - 1]) is not None
                )
                if i == 0:
                    left = False
                if left:
                    seg(level, xs[i] - stub, xs[i])
                else:
                    seg(level, xs[i], xs[i] + stub)
            i = j + 1


def _beam_obstacles(members: list[Chord], others: list[Chord]) -> list[tuple[int, int, int, int]]:
    """Boxes (Verovio units, Y up from the top line) that a beam must clear: grace notes and accidentals inside the
    group, and the notes of another voice of the staff during the group (``AdjustBeamsFunctor``)."""
    k = vrv.VU
    above = members[0].stem > 0
    out = []
    for c in members:
        x = c.x + c.shift
        for h in c.heads:
            if h.acc is not None:
                g = box(ACC_GLYPH[h.acc])
                ax = x - h.acc_off
                out.append(
                    (
                        round(ax * k),
                        round((ax + g.width) * k),
                        round((g.top - y_of(h.pos)) * k),
                        round((g.bottom - y_of(h.pos)) * k),
                    )
                )
        for gb in c.grace_boxes or []:
            out.append(gb)
    t0, t1 = members[0].time, members[-1].time + members[-1].dur
    for o in others:
        if o in members or o.time >= t1 or o.time + o.dur <= t0 or not o.notes:
            continue
        if (o.stem > 0) == above:
            continue
        x = o.x + o.shift
        for h in o.heads:
            y = vrv.note_y(h.pos)
            hx = round((x + _head_dx(o, h)) * k)
            out.append((hx, hx + vrv.HEAD_W, y + 95, y - 95))
    return out


def _draw_vrv_beam(
    pen: Pen, members: list[Chord], others: list[Chord] | None = None
) -> tuple[float, float]:
    """A one-staff beam group drawn by Verovio's rules (``vrv.beam``); ``others``: chords of the staff that the beam
    must clear."""
    k = vrv.VU

    def coords():
        return [
            vrv.Coord(round((c.x + c.shift) * k), [h.pos for h in c.heads], vrv.dur_index(c.figure))
            for c in members
        ]

    above = members[0].stem > 0
    b = vrv.beam(coords(), above)
    obstacles = _beam_obstacles(members, others or [])
    if obstacles:
        lift = vrv.beam_overlap(b, obstacles)
        if lift:
            b = vrv.beam(coords(), above, overlap=lift)
    staff = members[0].staff
    for poly in b.polys:
        pen.p(staff, [(x / k, -y / k) for x, y in poly], cls="beam")
    for c, co in zip(members, b.coords):
        sx = co.x / k
        end = -co.stem_end / k
        pen.l(staff, sx, -co.stem_start / k, sx, end, STEM_W)
        c.stem_end = -co.y_beam / k
        _draw_tremolo(pen, c, sx, (end + _stem_tip_head(c)) / 2)
    f, l = b.coords[0], b.coords[-1]
    line = ((f.x - vrv.STEM_W // 2) / k, -f.y_beam / k, -b.slope, b.above)
    for c in members:
        c.beam_line = line
    xc = (f.x + l.x) / 2
    return xc / k, -(f.y_beam + b.slope * (xc - f.x)) / k


def _draw_beam_group(
    pen: Pen, members: list[Chord], beat_of, others: list[Chord] | None = None
) -> tuple[float, float]:
    if _vrv():
        return _draw_vrv_beam(pen, members, others)
    d = members[0].stem
    x0, y0, k = _beam_geometry(members)
    sdir = 1 if d > 0 else -1
    _beam_polys(pen, members[0].staff, members, x0, y0, k, sdir, beat_of)
    for c in members:
        sx = _stem_x(c)
        end = y0 + k * (sx - x0)
        pen.l(c.staff, sx, _stem_base(c), sx, end, STEM_W)
        c.stem_end = end
        _draw_tremolo(pen, c, sx, (end + _stem_tip_head(c)) / 2)
    xc = (_stem_x(members[0]) + _stem_x(members[-1])) / 2
    return xc, y0 + k * (xc - x0)


def _draw_cross_beam_vrv(pen: Pen, members: list[Chord], bass_top: float) -> tuple[float, float]:
    """Beam between the staves by Verovio's mixed-beam rules (``vrv.mixed_beam``), system y."""
    k = vrv.VU
    coords = [
        vrv.Coord(round((c.x + c.shift) * k), [h.pos for h in c.heads], vrv.dur_index(c.figure))
        for c in members
    ]
    tops = [0 if c.staff == 1 else -round(bass_top * k) for c in members]
    b = vrv.mixed_beam(coords, tops, [c.staff == 2 for c in members])
    for poly in b.polys:
        pen.p(0, [(x / k, -y / k) for x, y in poly], cls="beam")
    for c, co in zip(members, b.coords):
        pen.l(0, co.x / k, -co.stem_start / k, co.x / k, -co.stem_end / k, STEM_W)
        c.stem_end = -co.stem_end / k
    f, l = b.coords[0], b.coords[-1]
    xc = (f.x + l.x) / 2
    return xc / k, -(f.y_beam + b.slope * (xc - f.x)) / k


def _draw_cross_beam(
    pen: Pen, members: list[Chord], bass_top: float, beat_of
) -> tuple[float, float]:
    """Beam between the staves: right-hand stems down to it, left-hand stems up (system y)."""
    if _vrv():
        return _draw_cross_beam_vrv(pen, members, bass_top)
    off = {1: 0.0, 2: bass_top}
    xs = [_stem_x(c) for c in members]
    tips = [_stem_tip_head(c) + off[c.staff] for c in members]
    levels = max(c.levels for c in members)
    min_stem = 2.5
    thick = BEAM_T + BEAM_PITCH * (levels - 1)
    k = _slope(tips[0], tips[-1], round(abs(tips[-1] - tips[0]) * 2), xs[-1] - xs[0]) * 0.5
    x0 = xs[0]
    lo = max(
        (t + min_stem - k * (x - x0) for x, t, c in zip(xs, tips, members) if c.staff == 1),
        default=-1e9,
    )
    hi = min(
        (t - min_stem - thick - k * (x - x0) for x, t, c in zip(xs, tips, members) if c.staff == 2),
        default=1e9,
    )
    if lo <= hi:
        y0 = (lo + hi) / 2 if lo > -1e8 and hi < 1e8 else (lo if hi > 1e8 else hi)
    else:
        y0 = (lo + hi) / 2
    _beam_polys(pen, 0, members, x0, y0, k, 1, beat_of)
    for c in members:
        sx = _stem_x(c)
        yb = y0 + k * (sx - x0)
        lv = c.levels
        end = yb + BEAM_PITCH * (lv - 1) + BEAM_T if c.staff == 1 else yb
        base = _stem_base(c) + off[c.staff]
        pen.l(0, sx, base, sx, end, STEM_W)
        c.stem_end = end
    xc = (xs[0] + xs[-1]) / 2
    return xc, y0 + k * (xc - x0)


def _tuplet_marks_vrv(pen: Pen, sys_chords: list[Chord]) -> None:
    """Tuplet numbers and brackets by Verovio's rules (``Tuplet::CalcDrawingBracketAndNumPos``,
    ``AdjustTupletsYFunctor``, ``TupletNum::GetDrawingXMid``, ``View::DrawTupletBracket``)."""
    groups: dict[int, list[Chord]] = defaultdict(list)
    for c in sys_chords:
        if c.tgroup is not None and c.tuplet:
            groups[c.tgroup].append(c)
    r = vrv.HEAD_W / vrv.VU / 2  # drawing radius of a notehead
    half_h = 133 * 0.72 / vrv.VU  # half height of a Leipzig notehead
    for cs in groups.values():
        cs.sort(key=lambda c: c.time)
        notes = [c for c in cs if not c.rest]
        if not notes or any(c.cross for c in cs):
            continue
        num = cs[0].tuplet.split("/")[0]
        staff = cs[0].staff
        above = sum(1 for c in notes if c.stem > 0) > sum(1 for c in notes if c.stem <= 0)
        first, last = cs[0], cs[-1]
        xl = first.x + first.shift + min((_head_dx(first, h) for h in first.heads), default=0.0)
        xr = last.x + last.shift + max((_head_dx(last, h) for h in last.heads), default=0.0) + 2 * r
        w = sum(box(f"tuplet{ch}").width for ch in num)
        gh = box(f"tuplet{num[-1]}").top - box(f"tuplet{num[-1]}").bottom
        line = cs[0].beam_line if len({c.beam for c in cs}) == 1 and cs[0].beamed else None
        if line is not None and line[3] == above:
            xm = (xl + (r if above else 0.0) + xr - (0.0 if above else r)) / 2
            yb = line[1] + line[2] * (xm - line[0])
            y = yb - 1.0 if above else yb + 1.0
            y = min(y, 0.0) if above else max(y, 4.0)
            _draw_number(pen, staff, num, xm - w / 2, y + gh / 2, 1.0, center=False)
            continue
        # bracket: clear the notes, stems and rests of the group; try a tilt along the melody
        obstacles = []
        for c in cs:
            x = c.x + c.shift
            if c.rest:
                g = box(REST_GLYPH.get(c.figure, "restQuarter"))
                yr = y_of(_rest_pos(c))
                obstacles.append((x, yr - g.top if above else yr - g.bottom))
                continue
            ys = [y_of(h.pos) for h in c.heads]
            obstacles.append((x, min(ys) - half_h if above else max(ys) + half_h))
            if c.stem_end is not None and (c.stem > 0) == above:
                obstacles.append((_stem_x(c), c.stem_end - 0.05 if above else c.stem_end + 0.05))
            # fingers and ornaments (phase 10 review: the bracket stays clear of the finger digits; Verovio does
            # not look at fingerings here)
            ink = c.ink_top if above else c.ink_bot
            if ink is not None:
                obstacles.append((x, ink - 0.25 if above else ink + 0.25))
        edge = 0.0 if above else 4.0
        sign = -1.0 if above else 1.0  # away from the staff, in y down
        xmid = (xl + xr) / 2

        def shift_for(slope: float) -> float:
            return max([0.0] + [sign * ((oy - slope * (ox - xmid)) - edge) for ox, oy in obstacles])

        flat = shift_for(0.0)
        best, tilt_best = flat, 0
        width = xr - xl
        tops = [max(h.pos for h in c.heads) for c in (notes[0], notes[-1])]
        direction = 1 if tops[0] < tops[1] else -1 if tops[0] > tops[1] else 0
        for tilt in (-4, -2, 2, 4):
            if width <= 0 or (direction == 1 and tilt < 0) or (direction == -1 and tilt > 0):
                continue
            slope = -tilt * 0.5 / width  # y down: a positive tilt rises to the right
            sh = shift_for(slope)
            if sh < abs(tilt) * 0.25 or sh > flat - abs(tilt) * 0.125:
                continue
            if sh < best:
                best, tilt_best = sh, tilt
        ym = edge + sign * (best + 1.0)
        yl, yr = ym + tilt_best * 0.25, ym - tilt_best * 0.25
        lw = 0.1
        xa, xb = xl + lw / 2, xr - lw / 2
        nx = xmid - w / 2
        xnl, xnr = nx - 0.25, nx + w + 0.25
        slope = (yr - yl) / (xb - xa) if xb > xa else 0.0
        hook = -sign * gh / 2
        for x0, y0, x1, y1 in (
            (xa, yl, xnl, yl + slope * (xnl - xa)),
            (xb, yr, xnr, yr - slope * (xb - xnr)),
        ):
            pen.l(staff, x0, y0 + hook, x0, y0 + sign * lw / 2, lw)
            pen.l(staff, x0, y0, x1, y1, lw)
        _draw_number(pen, staff, num, nx, (yl + yr) / 2 + gh / 2, 1.0, center=False)


def _tuplet_marks(
    pen: Pen, sys_chords: list[Chord], beam_centres: dict[int, tuple], bass_top: float
) -> None:
    if _vrv():
        return _tuplet_marks_vrv(pen, sys_chords)
    groups: dict[int, list[Chord]] = defaultdict(list)
    for c in sys_chords:
        if c.tgroup is not None and c.tuplet:
            groups[c.tgroup].append(c)
    for gid, cs in groups.items():
        cs.sort(key=lambda c: c.time)
        num = cs[0].tuplet.split("/")[0]
        notes_only = [c for c in cs if not c.rest]
        if not notes_only:
            continue
        beams = {c.beam for c in cs}
        staff = cs[0].staff
        if len(beams) == 1 and None not in beams and cs[0].beam in beam_centres:
            xc, yb, d, cross = beam_centres[cs[0].beam]
            if cross:
                continue
            y = yb - 0.9 if d > 0 else yb + 1.9
            if d > 0:
                y = min([y] + [c.ink_top - 0.3 for c in cs if c.ink_top is not None])
            else:
                y = max([y] + [c.ink_bot + 1.4 for c in cs if c.ink_bot is not None])
            _draw_number(pen, staff, num, xc, y)
            continue
        # bracket above (stems up) or below
        up = notes_only[0].stem >= 0 if not notes_only[0].cross else True
        xa, xb = cs[0].x + cs[0].shift, cs[-1].x + cs[-1].shift + cs[-1].head_w
        ys = []
        for c in notes_only:
            ys.append(
                c.stem_end
                if c.stem_end is not None and c.stem == (1 if up else -1)
                else (
                    y_of(max(h.pos for h in c.heads)) if up else y_of(min(h.pos for h in c.heads))
                )
            )
            ink = c.ink_top if up else c.ink_bot
            if ink is not None:
                ys.append(ink + (0.6 if up else -0.6))
        y = (min(ys + [0.0]) - 1.6) if up else (max(ys + [4.0]) + 1.6)
        xc = (xa + xb) / 2
        h = 0.6 if up else -0.6
        pen.l(staff, xa, y + h, xa, y, 0.12)
        pen.l(staff, xa, y, xc - 0.8, y, 0.12)
        pen.l(staff, xc + 0.8, y, xb, y, 0.12)
        pen.l(staff, xb, y, xb, y + h, 0.12)
        _draw_number(pen, staff, num, xc, y + 0.45)


def _prim_xrange(p: Prim) -> tuple[float, float]:
    if p.kind == "g":
        name, x, y, s, rot = p.data
        b = box(name)
        if rot:
            return x - (b.top - b.bottom) * s, x
        return x + b.left * s, x + b.right * s
    if p.kind == "l":
        return min(p.data[0], p.data[2]), max(p.data[0], p.data[2])
    if p.kind == "e":
        return p.data[0] - p.data[2], p.data[0] + p.data[2]
    if p.kind == "p":
        xs = [pt[0] for pt in p.data]
        return min(xs), max(xs)
    return 0.0, 0.0


def _ink_edge(pen: Pen, staff: int, x0: float, x1: float, above: bool) -> float:
    """Highest (``above``) or lowest ink of a staff between x0 and x1, staff lines excluded (staff top / bottom line
    at least): what a floating sign must clear (Verovio's ``AdjustFloatingPositioners``)."""
    edge = 0.0 if above else 4.0
    for p in pen.prims:
        if p.staff != staff or p.kind in ("b", "z"):
            continue
        if p.kind == "l" and p.data[1] == p.data[3] and p.data[0] <= 0.01 and p.cls == "":
            if (
                abs(p.data[1] - round(p.data[1])) < 1e-9
                and 0 <= p.data[1] <= 4
                and p.data[2] - p.data[0] > 5
            ):
                continue  # a staff line
        a, b = _prim_xrange(p)
        if b < x0 or a > x1:
            continue
        lo, hi = _prim_yrange(p)
        edge = min(edge, lo) if above else max(edge, hi)
    return edge


def _ornaments_vrv(pen: Pen, c: Chord) -> None:
    """Trill, mordent, turn, fermata above the chord, centred on the notehead, stacked 0.25 staff space above the
    ink under them (``defaultBottomMargin``)."""
    xc = c.x + c.shift + c.head_w / 2
    drawn = False
    for orn, name in (
        ("trill", "ornamentTrill"),
        ("mordent", "ornamentMordent"),
        ("turn", "ornamentTurn"),
        ("fermata", "fermataAbove"),
    ):
        if orn in c.ornaments:
            g = box(name)
            x = xc - g.width / 2
            y = (
                _ink_edge(pen, c.staff, x, x + g.width, True) - 0.25 + g.bottom
            )  # baseline: glyph bottom on the edge
            pen.g(c.staff, name, x, y, cls="ornament")
            drawn = True
    if drawn:
        c.ink_top = _ink_edge(pen, c.staff, xc - 0.5, xc + 0.5, True)


def _ornaments(pen: Pen, c: Chord) -> None:
    if c.rest:
        return
    if _vrv():
        return _ornaments_vrv(pen, c)
    top = min(
        y_of(max(h.pos for h in c.heads)) - 0.6,
        (c.stem_end if c.stem > 0 and c.stem_end is not None and not c.cross else 99),
        -0.5,
    )
    y = top - 0.8
    xc = c.x + c.shift + c.head_w / 2
    drawn = False
    for orn, name in (
        ("trill", "ornamentTrill"),
        ("mordent", "ornamentMordent"),
        ("turn", "ornamentTurn"),
        ("fermata", "fermataAbove"),
    ):
        if orn in c.ornaments:
            pen.g(c.staff, name, xc - box(name).width / 2, y)
            y -= box(name).top - box(name).bottom + 0.4
            drawn = True
    if drawn:
        c.ink_top = y + 0.4


def _fingers(pen: Pen, c: Chord) -> None:
    """Finger numbers (phase 10). A chord with two or more fingers: one column to the left of its accidentals, each
    digit at the height of its note (the order finger, accidental, note of printed editions; user feedback
    2026-10-20). A single finger: above the note on the upper staff, below it on the lower staff. Records the ink
    extent (``ink_top`` / ``ink_bot``) so that tuplet marks and 8va lines clear it."""
    if c.rest or not any(n.finger for n in c.notes):
        return

    def cls(n: Note) -> str:
        return "finger " + n.finger_mark if n.finger_mark else "finger"

    def digit(n: Note, x_left: float, y: float) -> None:
        pen.g(c.staff, f"tuplet{n.finger}", x_left, y, FINGER_SCALE, cls=cls(n))

    half = box("tuplet1").top * FINGER_SCALE / 2  # digit height / 2
    if c.finger_off is not None:
        right = c.x + c.shift - c.finger_off
        items = sorted(
            ((h.pos, h.note) for h in c.heads if h.note.finger), key=lambda t: -t[0]
        )  # top first
        ys: list[float] = []
        for pos, n in items:
            y = y_of(pos) + half  # baseline: the digit centred on its notehead
            if ys and y < ys[-1] + FINGER_STEP:
                y = ys[-1] + FINGER_STEP
            ys.append(y)
        # keep the block centred on the notes when seconds pushed it down
        want = sum(y_of(p) + half for p, _ in items) / len(items)
        ys = [y - (sum(ys) / len(ys) - want) for y in ys]
        for (pos, n), y in zip(items, ys):
            digit(n, right - box(f"tuplet{n.finger}").width * FINGER_SCALE, y)
        c.ink_top = min(([c.ink_top] if c.ink_top is not None else []) + [ys[0] - 2 * half])
        c.ink_bot = max(ys)
        return
    xc = c.x + c.shift + c.head_w / 2
    n = next(n for n in c.notes if n.finger)
    w = box(f"tuplet{n.finger}").width * FINGER_SCALE
    if c.staff == 1:
        top = min(
            y_of(max(h.pos for h in c.heads)) - 0.7,
            (c.stem_end - 0.3 if c.stem > 0 and c.stem_end is not None and not c.cross else 99),
            -0.6,
        )
        if c.ink_top is not None:
            top = min(top, c.ink_top - 0.3)
        digit(n, xc - w / 2, top)
        c.ink_top = top - 2 * half
    else:
        bot = max(
            y_of(min(h.pos for h in c.heads)) + 1.5,
            (c.stem_end + 1.2 if c.stem < 0 and c.stem_end is not None and not c.cross else -99),
            5.4,
        )
        digit(n, xc - w / 2, bot)
        c.ink_bot = bot


def _ottavas(pen: Pen, cs: list[Chord]) -> None:
    for staff in (1, 2):
        seq = sorted((c for c in cs if c.staff == staff and c.notes), key=lambda c: c.time)
        i = 0
        while i < len(seq):
            o = seq[i].ottava
            if not o:
                i += 1
                continue
            j = i
            while j + 1 < len(seq) and seq[j + 1].ottava == o:
                j += 1
            run = seq[i : j + 1]
            name = {
                1: "ottavaAlta",
                2: "quindicesima",
                -1: "ottavaBassaVb",
                -2: "quindicesimaBassaMb",
            }.get(o, "ottavaAlta")
            xa = run[0].x + run[0].shift
            xb = run[-1].x + run[-1].shift + run[-1].head_w
            if (
                _vrv()
            ):  # Verovio: "8" (or "15") right-aligned on the first head's centre, dashed line, 1-space hook
                name = "ottava" if abs(o) == 1 else "quindicesima"
                g = box(name)
                gx = xa + run[0].head_w / 2 - g.width
                lw = 18 / vrv.VU
                # the sign and its line clear the ink of the whole span (user, phase 14: the dashed line never
                # crosses a note; Verovio measures under the "8" only)
                x1 = max(xb, gx + g.width)
                if o > 0:
                    gy = _ink_edge(pen, staff, gx, x1, True) - 0.5  # bottomMarginOctave
                    ly, hook = gy - g.top + lw / 2, 1.0
                else:
                    gy = _ink_edge(pen, staff, gx, x1, False) + 0.5 + g.top
                    ly, hook = gy - lw / 2, -1.0
                pen.g(staff, name, gx, gy, cls="ottava")
                x0 = gx + g.width + 19 / vrv.VU
                if xb > x0:
                    pen.l(staff, x0 - lw / 2, ly, xb, ly, lw, dash=(54 / vrv.VU, 54 / vrv.VU))
                    pen.l(staff, xb, ly + hook, xb, ly - (lw / 2 if hook > 0 else -lw / 2), lw)
                    pen.l(staff, xb - 0.5, ly, xb + lw / 2, ly, lw)
                i = j + 1
                continue
            if o > 0:
                tops = [y_of(max(h.pos for h in c.heads)) for c in run] + [
                    c.stem_end for c in run if c.stem_end is not None and c.stem > 0 and not c.cross
                ]
                tops += [c.ink_top + 0.4 for c in run if c.ink_top is not None]
                y = min(tops + [-0.5]) - 1.2
                hook = 0.8
            else:
                bots = [y_of(min(h.pos for h in c.heads)) for c in run] + [
                    c.stem_end for c in run if c.stem_end is not None and c.stem < 0 and not c.cross
                ]
                bots += [c.ink_bot + 0.6 for c in run if c.ink_bot is not None]
                y = max(bots + [4.5]) + 2.0
                hook = -0.8
            pen.g(staff, name, xa, y, 0.8)
            start = xa + box(name).width * 0.8 + 0.3
            if xb > start + 0.5:
                pen.l(staff, start, y - 0.5, xb, y - 0.5, 0.12, dash=(0.6, 0.4))
                pen.l(staff, xb, y - 0.5, xb, y - 0.5 + hook, 0.12)
            i = j + 1


# ------------------------------------------------------------------ main


OTTAVA_TOP = 15  # sounding treble step that starts an 8va run (F6: 51 % under 8va in the corpus)
OTTAVA_FLOOR = 6  # a run stays under 8va while its lowest note is at or above D5


def auto_ottava(sheet: Sheet) -> Sheet:
    """Right-hand treble runs that reach F6 or higher and stay at or above D5 are written an octave
    lower under 8va (measured: 51 % of treble notes at F6 are under 8va, 85 % at A6, 97 % at C7)."""
    if any(
        n.ottava for n in sheet.notes if n.staff == 1
    ):  # left-hand marks do not stop it (phase 14)
        return sheet
    tl = _clef_timeline(sheet)
    notes = [replace(n) for n in sheet.notes]
    by_time: dict[Fraction, list[Note]] = defaultdict(list)
    for n in notes:
        if n.staff == 1 and n.time is not None:
            by_time[n.time].append(n)
    times = sorted(by_time)

    def spos(n):
        return 7 * n.octave + STEPS.index(n.step) - 30

    def treble(t):
        return _clef_at(tl, 1, t) == "G2"

    i = 0
    while i < len(times):
        j = i
        run = []
        while (
            j < len(times)
            and treble(times[j])
            and min(spos(n) for n in by_time[times[j]]) >= OTTAVA_FLOOR
        ):
            run.append(times[j])
            j += 1
        if run and max(spos(n) for t in run for n in by_time[t]) >= OTTAVA_TOP:
            for t in run:
                for n in by_time[t]:
                    n.ottava = 1
        i = max(j, i + 1)
    return replace(sheet, notes=notes)


def _metrics() -> None:
    """Notehead widths of the active font (``glyphs.set_font``)."""
    global HEAD_W, WHOLE_W
    HEAD_W = box("noteheadBlack").width
    WHOLE_W = box("noteheadWhole").width


def merge_unisons(sheet: Sheet) -> Sheet:
    """A copy without duplicate notes: the same pitch at the same time in the same staff (two voices sharing a note,
    e.g. a melody note written also as the start of its decoration, ``Gb5:8 Gb5:16``) is drawn once. The user (phase
    11): a duplicated notehead is never wanted; inside a beam the length of a note does not matter. Kept: the note
    inside the larger beam group, else the shorter figure; graces are left as they are."""
    size = Counter(n.beam for n in sheet.notes if n.beam is not None)
    best: dict = {}
    for i, n in enumerate(sheet.notes):
        if n.grace:
            continue
        key = (n.time, n.staff, n.midi)
        rank = (size.get(n.beam, 0), n.figure or 0)
        if key not in best or rank > best[key][0]:
            best[key] = (rank, i)
    keep = {i for _, i in best.values()}
    if len(keep) + sum(1 for n in sheet.notes if n.grace) == len(sheet.notes):
        return sheet
    merged: dict[int, list[Note]] = defaultdict(list)  # kept index -> the notes it stands for
    for i, n in enumerate(sheet.notes):
        if not n.grace:
            merged[best[(n.time, n.staff, n.midi)][1]].append(n)
    notes = []
    for i, n in enumerate(sheet.notes):
        if n.grace or i not in keep:
            if n.grace:
                notes.append(n)
            continue
        group = merged[i]
        refs = [
            f"{m.frame}:{m.midi}"
            for m in sorted(group, key=lambda m: m.frame or 0)
            if m.frame is not None
        ]
        notes.append(replace(n, ref=" ".join(dict.fromkeys(refs))) if len(group) > 1 else n)
    return replace(sheet, notes=notes)


def engrave(sheet: Sheet, opts: Options | None = None) -> Engraving:
    opts = opts or Options()
    _metrics()
    if opts.merge_unisons:
        sheet = merge_unisons(sheet)
    if opts.auto_ottava:
        sheet = auto_ottava(sheet)
    model = opts.model or load()
    clearance = opts.clearance if opts.clearance is not None else model.clearance
    if not sheet.bars:
        raise ValueError("engrave needs a bars sheet (F1-bars)")
    chords, _ = build_chords(sheet, opts.voice_rests)
    _accidentals(sheet, chords)
    beams = _stems(chords)
    _rest_positions(chords)
    bars = build_bars(sheet, chords, model, clearance)
    tl = _clef_timeline(sheet)
    systems = []
    columns_out = []
    beams_out = []
    for si, (group, header, e) in enumerate(break_lines(sheet, bars, opts)):
        b0 = group[0].index
        show = (b0 == 0 and opts.first_meter) or (
            b0 > 0 and sheet.bars[b0].meter != sheet.bars[b0 - 1].meter
        )
        meter = sheet.bars[b0].meter if show else None
        sysm = System(group, opts.width, header)
        pen = Pen()
        clefs = {s: _clef_at(tl, s, sheet.bars[b0].start) for s in (1, 2)}
        align = opts.align or {}
        _draw_header(pen, sheet, b0, clefs, meter, align)
        # x positions
        x = header
        barlines = []
        for k, bl in enumerate(group):
            bl.x0 = x
            lead = _first_lead(bl) if k == 0 else bl.lead
            if k > 0 and bl.start_items:
                xi = x + 0.8
                if bl.key_change:
                    for staff in (1, 2):
                        _draw_key(
                            pen,
                            staff,
                            _clef_at(tl, staff, bl.start),
                            sheet.bars[bl.index].key,
                            xi,
                            align.get("keys", {}).get(bl.index),
                        )
                    xi += max(_key_sig_width(sheet.bars[bl.index].key), 0.5) + 0.6
                if bl.meter_change:
                    for staff in (1, 2):
                        _draw_meter(
                            pen,
                            staff,
                            sheet.bars[bl.index].meter,
                            align.get("meters", {}).get(bl.index, xi),
                        )
            x += lead
            for i, col in enumerate(bl.columns):
                col.x = x
                for c in col.chords:
                    c.x = x
                    if chord_id(c) in align.get("chords", {}):
                        c.x, c.shift = align["chords"][chord_id(c)], 0.0
                    c.grace_x = align.get("graces", {}).get(chord_id(c))
                if align.get("chords"):
                    col.x = min((c.x for c in col.chords if c.notes), default=x)
                    if _vrv():
                        for st in (1, 2):
                            _column_accidentals_vrv(
                                [c for c in col.chords if c.staff == st], aligned=True
                            )
                x += max(bl.nat[i] + e, bl.mins[i])
            if not bl.columns:
                x += max(bl.nat[0] + e, bl.mins[0])
            xa = align.get("bars", {}).get(bl.index)
            if xa is not None:
                x = xa - bl.trail
            if bl.trail_clefs:
                for s, c in bl.trail_clefs:
                    cx = align.get("trail_clefs", {}).get((bl.index, s), x + 0.1)
                    pen.g(
                        s,
                        "gClefChange" if c != "F4" else "fClefChange",
                        cx,
                        y_of(2 if c != "F4" else 6),
                    )
                x += bl.trail
            bl.x1 = x
            barlines.append(x)
        end_x = (
            x
            if (
                e == 0.0
                and group[-1].index == len(bars) - 1
                and not opts.justify_last
                and opts.breaks is None
            )
            else max(x, opts.width)
        )
        sysm.width = end_x
        # chords of this system
        sys_chords = [c for bl in group for col in bl.columns for c in col.chords]
        for bl in group:
            for r in bl.measure_rests:
                r.x = (
                    bl.x0 + (bl.lead if bl is not group[0] else _first_lead(bl)) + bl.x1
                ) / 2 - 0.6
                if bl is group[0]:
                    r.x = (bl.x0 + bl.x1) / 2 - 0.6
                r.x = align.get("chords", {}).get(chord_id(r), r.x)
                sys_chords.append(r)
        # clef changes inside bars
        for bl in group:
            for col in bl.columns:
                for s, c in col.clef_changes:
                    acc = max(
                        (ch.left - ch.shift for ch in col.chords if ch.staff == s), default=0.0
                    )
                    name = "gClefChange" if c != "F4" else "fClefChange"
                    cx = align.get("mid_clefs", {}).get(
                        (bl.index, col.time, s), col.x - acc - box(name).width - 0.15
                    )
                    pen.g(s, name, cx, y_of(2 if c != "F4" else 6))
        if _vrv():
            _vrv_dots(sys_chords)
        for c in sys_chords:
            _draw_chord(pen, c)
            if not c.beamed:
                _draw_unbeamed_stem(pen, c)
        if _vrv():
            _vrv_ledgers(pen, sys_chords)
        # beams (one-staff groups; cross-staff later)
        ids_here = {c.beam for c in sys_chords if c.beamed}
        centres = {}
        cross_groups = []
        bar_of = {bl.index: sheet.bars[bl.index] for bl in group}

        def beat_of(c: Chord):
            bar = bar_of.get(c.bar)
            if bar is None:
                return None
            unit = beat_unit(bar.meter)
            return (c.time - bar.start) % unit

        for bid in ids_here:
            members = [c for c in beams[bid] if c in sys_chords] if bid in beams else []
            members = [c for c in members if any(c is s for s in sys_chords)]
            if len(members) < 2:
                for c in members:
                    c.beamed = False
                    _extents(c)
                    _draw_unbeamed_stem(pen, c)
                continue
            if members[0].cross:
                cross_groups.append((bid, members))
                continue
            xc, yc = _draw_beam_group(
                pen,
                members,
                beat_of,
                [c for c in sys_chords if c.staff == members[0].staff and c.bar == members[0].bar],
            )
            centres[bid] = (xc, yc, members[0].stem, False)
            beams_out.append(
                {"id": bid, "system": si, "staves": [members[0].staff], "members": len(members)}
            )
        cross_ids = {bid for bid, _ in cross_groups}
        for (
            c
        ) in sys_chords:  # ornaments and fingers first: tuplet marks and 8va lines clear their ink
            if not c.cross:
                _ornaments(pen, c)
                _fingers(pen, c)
        _tuplet_marks(pen, [c for c in sys_chords if c.beam not in cross_ids], centres, 0.0)
        _ottavas(pen, sys_chords)
        # staff gap from the ink between the staves
        below = 4.0
        above = 0.0
        for p in pen.prims:
            lo, hi = _prim_yrange(p)
            if p.staff == 1:
                below = max(below, hi)
            elif p.staff == 2:
                above = min(above, lo)
        gap = max(opts.min_staff_gap, (below - 4.0) + (-above) + 2.0)
        for bid, members in cross_groups:
            need = _cross_need(members)
            gap = max(gap, need)
        sysm.gap = align.get("gap", gap)
        gap = sysm.gap
        for bid, members in cross_groups:
            xc, yc = _draw_cross_beam(pen, members, 4 + gap, beat_of)
            centres[bid] = (xc, yc, 1, True)
            beams_out.append({"id": bid, "system": si, "staves": [1, 2], "members": len(members)})
        for c in sys_chords:
            if c.cross:
                _ornaments(pen, c)
                _fingers(pen, c)
        _tuplet_marks(pen, [c for c in sys_chords if c.beam in cross_ids], centres, 4 + gap)
        # staff lines, barlines, brace, bar number
        vr = _vrv()
        for staff in (1, 2):
            for k in range(5):
                pen.l(
                    staff, 0.0, k * 1.0, end_x + (BAR_W / 2 if vr else 0.0), k * 1.0, STAFF_LINE_W
                )
        bass_bottom = 4 + gap + 4
        pen.l(0, BAR_W / 2 if vr else 0.0, 0.0, BAR_W / 2 if vr else 0.0, bass_bottom, BAR_W)
        for k, xb in enumerate(barlines):
            last_bar = group[k].index == len(bars) - 1
            if k == len(barlines) - 1:
                xb = end_x
            nxt = group[k + 1] if k + 1 < len(group) else None
            if nxt is not None and nxt.key_change and not vr:
                pen.l(0, xb - 0.5, 0.0, xb - 0.5, bass_bottom, BAR_W)
            if last_bar and opts.breaks is None and False:
                pen.l(0, xb - 0.6, 0.0, xb - 0.6, bass_bottom, BAR_W)
                pen.l(0, xb - 0.25, 0.0, xb - 0.25, bass_bottom, 0.5)
            else:
                pen.l(0, xb, 0.0, xb, bass_bottom, BAR_W)
        if vr:
            _vrv_brace(pen, bass_bottom)
        else:
            pen.prims.append(Prim("b", 0, (-1.4, 0.0, bass_bottom)))
        if opts.bar_numbers:
            label = sheet.bars[b0].label
            if label and label.isdigit() and label not in ("0", "1"):
                _draw_number(pen, 1, label, 0.2, -2.3, 0.7, center=False)
        sysm.prims = pen.prims
        ys = []
        for p in pen.prims:
            lo, hi = _prim_yrange(p)
            off = 4 + gap if p.staff == 2 else 0.0
            ys += [lo + off, hi + off]
        sysm.ymin, sysm.ymax = min(ys + [0.0]), max(ys + [bass_bottom])
        systems.append(sysm)
        # metrics: one row per column
        for bl in group:
            bar = sheet.bars[bl.index]
            for i, col in enumerate(bl.columns):
                nxt_t = bl.columns[i + 1].time if i + 1 < len(bl.columns) else bl.end
                columns_out.append(
                    {
                        "system": si,
                        "bar": bl.index,
                        "label": bar.label,
                        "time": col.time,
                        "rel_time": col.time - bl.start,
                        "x": col.x,
                        "ioi": nxt_t - col.time,
                        "staves": sorted({c.staff for c in col.chords if not c.rest}),
                        "rest_only": col.rest_only,
                        "accidental": col.accidental,
                        "beams": {c.staff: c.beam for c in col.chords if c.beamed},
                        "barline_left": bl.x0,
                        "barline_right": bl.x1,
                        "first_bar": bl is group[0],
                        "last_col": i + 1 == len(bl.columns),
                        "e": e,
                    }
                )
    margin = 3.0
    y = margin
    for sysm in systems:
        sysm.top = y - sysm.ymin
        y = sysm.top + sysm.ymax + opts.system_gap
    height = y - opts.system_gap + margin
    width = max(s.width for s in systems) + 2 * margin + 2.0
    return Engraving(systems, width, height, columns_out, beams_out, margin)


def _vrv_dots(chords: list[Chord]) -> None:
    """Dots by Verovio's rules: spaces from ``vrv.optimal_dot_locs`` (a dot of a lower voice goes down), x half a
    staff space after the rightmost head of the chord (after the flag of an up-stem chord), and the dots of two
    voices that meet at one time aligned on the rightmost (``AdjustDotsFunctor``)."""
    cols: dict[tuple[int, int, Fraction], list[Chord]] = defaultdict(list)
    for c in chords:
        if c.notes:
            cols[(c.bar, c.staff, c.time)].append(c)
    by_bar: dict[tuple[int, int], list[Chord]] = defaultdict(list)
    for c in chords:
        by_bar[(c.bar, c.staff)].append(c)
    r = vrv.HEAD_W / vrv.VU / 2
    for group in cols.values():
        dotted = [c for c in group if c.dots]
        if not dotted:
            continue
        for c in dotted:
            locs = [h.pos for h in c.heads]
            layers = min(2, _sounding_voices(c, by_bar[(c.bar, c.staff)]))
            other = next(
                ((sorted(h.pos for h in o.heads), o.stem > 0) for o in group if o.voice != c.voice),
                None,
            )
            c.dot_locs = vrv.optimal_dot_locs(locs, c.stem > 0, layers, other)
            right = max(_head_dx(c, h) for h in c.heads) + 2 * r
            if c.stem > 0 and c.figure >= 8 and not c.beamed:
                top = max(c.heads, key=lambda h: h.pos)
                if len(c.heads) > 1 and not top.side:
                    right += 0.8 * box("flag8thUp").width
            c.dot_x = c.x + c.shift + right + DOT_GAP
        # dots that would touch another voice's dotted note move to the rightmost dot column (AdjustDotsFunctor)
        for c in dotted:
            for o in dotted:
                if o is c:
                    continue
                ox0 = o.x + o.shift + min(_head_dx(o, h) for h in o.heads)
                ox1 = o.x + o.shift + max(_head_dx(o, h) for h in o.heads) + 2 * r
                near = any(
                    abs(y_of(p) - y_of(h.pos)) < 0.5 + 0.33 + DOT_R
                    for p in c.dot_locs
                    for h in o.heads
                )
                if ox0 - 0.17 < c.dot_x + DOT_R and ox1 + 0.17 > c.dot_x - DOT_R and near:
                    c.dot_x = max(c.dot_x, o.dot_x)


def _vrv_ledgers(pen: Pen, chords: list[Chord]) -> None:
    """Ledger lines of every note, per measure and staff, by Verovio's rule (``vrv.ledger_dashes``)."""
    k = vrv.VU
    groups: dict[tuple[int, int], list[tuple[int, int, int]]] = defaultdict(list)
    for c in chords:
        if c.rest:
            continue
        w = round(c.head_w * k) if c.figure in (0, 1) else vrv.HEAD_W
        for h in c.heads:
            groups[(c.bar, c.staff)].append((round((c.x + c.shift + _head_dx(c, h)) * k), w, h.pos))
    for (_, staff), notes in groups.items():
        for (side, i), dashes in vrv.ledger_dashes(notes).items():
            y = y_of(10 + 2 * i) if side == "above" else y_of(-2 - 2 * i)
            for a, b in dashes:
                pen.l(staff, a / k, y, b / k, y, LEDGER_W)


def _vrv_brace(pen: Pen, bottom: float) -> None:
    """``View::DrawBrace`` (Verovio's default, not the font glyph): two filled Bézier halves, stroked 0.1."""
    pw = STEM_W
    x = -0.5 + pw
    y1, y2 = 0.0 + pw, bottom - pw
    ym = (y1 + y2) / 2
    dec = 0.25 + STEM_W
    for y0, s in ((y2, -1), (y1, 1)):  # lower half, upper half
        p1 = (x - 2.0, y0 + 3.0 * s)
        p2 = (x + 0.5, ym - 1.0 * s)
        p3 = (x - 1.0, ym)
        pen.z(
            0,
            [
                ("M", x, y0),
                ("C", *p1, *p2, *p3),
                ("C", p2[0] + dec, p2[1], p1[0] + dec, p1[1], x, y0),
            ],
            pw,
        )


def _cross_need(members: list[Chord]) -> float:
    """Staff gap a cross-staff beam needs: right-hand notes above, left-hand notes below, stems of at
    least 2.5 staff spaces on both sides of the beam."""
    rh = [_stem_tip_head(c) for c in members if c.staff == 1]
    lh = [_stem_tip_head(c) for c in members if c.staff == 2]
    if not rh or not lh:
        return 0.0
    levels = max(c.levels for c in members)
    thick = BEAM_T + BEAM_PITCH * (levels - 1)
    # bass_top + min(lh) - 2.5 - thick >= max(rh) + 2.5
    need_top = max(rh) + 2.5 + thick + 2.5 - min(lh)
    return max(0.0, need_top - 4.0)


set_style(STYLE["name"])
