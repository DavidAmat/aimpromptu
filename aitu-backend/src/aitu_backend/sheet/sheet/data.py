"""The sheet content: what F1 carries (phase 4; product core since phase 15).

Following the philosophy of the research plan (sustains and releases are not important, each onset has a figure),
a sheet keeps:

* every **onset** the pianist plays, with its time, hand (drawn staff), spelled sounding pitch, figure and dots,
  tuplet ratio, beam group, tuplet group, grace kind and order, ornaments and ottava;
* the **bars** (label, length, meter, key signature);
* the **clefs** (first clef of each staff and every change).

Left out by design: rests, ties, voices, stems, printed accidentals (the engine derives them from the spelling and
the bars). Fingering (``Note.finger``) is drawn; implementation 03, Phase 7 writes it in F1 (``fg3``) with the
user's two other marks of the new sheet (``fix``, ``asgrace`` / ``nograce``).

Times are quarters from the start of the sheet (exact fractions). A frames sheet (the matrix as text) has no bars
and no beats: its notes carry ``frame`` (40 ms columns of the piano matrix notation) and ``time`` is ``None``.
The research package adds the score side (``aitu_research.formats.sheet``: IR -> sheet).
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from fractions import Fraction
from typing import Any, Iterable

from aitu_backend.sheet.sheet.pitch import STEPS, pitch_to_midi  # noqa: F401 (re-exported)

__all__ = [
    "Bar",
    "LYRIC_FONTS",
    "LYRIC_MAX",
    "LYRIC_MIN",
    "LYRIC_SIZE",
    "Lyric",
    "Note",
    "Sheet",
    "TITLE_FIELDS",
    "beat_unit",
    "carry_extras",
    "compare",
    "frame_of_ms",
    "frames_from_times",
    "meter_quarters",
    "pos_text",
    "parse_pos",
    "to_frames_sheet",
    "FRAME_MS",
]

FRAME_MS = 40.0
GRACE_MS = 60.0
CLEF_NAMES = {"G2": "treble", "F4": "bass", "C3": "alto", "C4": "tenor"}
CLEF_CODES = {v: k for k, v in CLEF_NAMES.items()}


@dataclass
class Note:
    time: Fraction | None  # quarters from the start (None in a frames sheet)
    staff: int  # 1 right hand (upper staff), 2 left hand (lower staff)
    step: str
    alter: int
    octave: int  # sounding octave (written octave + ottava)
    figure: int | None = None  # 1 whole ... 128; 0 breve; None = unknown (a matrix note)
    dots: int = 0
    tuplet: str | None = None  # "3/2" = 3 in the time of 2
    beam: int | None = None  # beam group number, unique in the sheet
    tgroup: int | None = None  # tuplet group number, unique in the sheet
    grace: str | None = None  # "acc" (slashed) | "unacc"
    gslot: int = 0  # order of a grace note before its main note (0 first); chord graces share it
    ornaments: tuple[str, ...] = ()
    ottava: int = 0
    frame: int | None = None  # 40 ms column (frames sheets, and filled by sheet_frames)
    hand_known: bool = True  # False for a matrix note without hand
    eid: str | None = field(
        default=None, compare=False
    )  # IR event id (not part of the sheet content)
    finger: int | None = field(
        default=None, compare=False
    )  # 1-5, drawn by the engine (phase 10; not in F1)
    finger_mark: str | None = field(
        default=None, compare=False
    )  # gallery colour class of the finger
    mark: str | None = field(
        default=None, compare=False
    )  # gallery colour class of the notehead (phase 11)
    ref: str | None = field(
        default=None, compare=False
    )  # engine: SVG ids of the note and of unisons merged into it
    covered: bool = (
        False  # played inside the ornament of the note before it (``orn``): kept, not drawn
    )
    on_ms: float | None = field(
        default=None, compare=False
    )  # measured onset (new sheet; not in F1)
    len_ms: float | None = field(
        default=None, compare=False
    )  # measured length (new sheet; not in F1)
    fixed: bool = (
        False  # the figure was set by the user (``fix``): the figure rule keeps it (implementation 03, Phase 7)
    )
    grace_rule: str | None = (
        None  # the user's grace note switch: "on" (``asgrace``) or "off" (``nograce``)
    )
    spelled: bool = (
        False  # the spelling (letter and alteration) was set by the user (``sp``): the spelling rule keeps it
    )

    @property
    def midi(self) -> int:
        return pitch_to_midi(self.step, self.alter, self.octave)


@dataclass
class Bar:
    label: str
    start: Fraction
    dur: Fraction
    meter: str
    key: int


#: The size of a lyrics piece, in staff spaces: the default and the limits (the old sheet's 12 px, 7 to 36 px, at
#: about 8.5 px a staff space).
LYRIC_SIZE, LYRIC_MIN, LYRIC_MAX = 1.4, 0.8, 4.2
#: The fonts of a lyrics piece (the user's answer of Phase 8A++); the PDF prints Lora as Times, the others as
#: Helvetica.
LYRIC_FONTS = ("lora", "geist", "montserrat")


@dataclass
class Lyric:
    """A lyrics piece on the new sheet (implementation 03, Phase 8): its words (``\\n`` breaks a line) over the
    columns ``[start, end)``, drawn above the upper staff from ``start``; ``size`` in staff spaces (``None``: the
    sheet's own), ``lift`` in staff spaces above where the line of words of its system would put it.

    A block moved by hand (Phase 8A++, the user's request) is drawn where it was put, whatever its frames: ``at`` is
    the frame of the column under its left edge (its line, and the music it stays with when the lines change),
    ``dx`` how far right of that column it starts and ``dy`` the baseline of its last line below the top line of the
    upper staff, in staff spaces (``dy`` ``None``: the block sits in the line of words, as before). ``width`` in
    staff spaces wraps the words (the engine wraps them with the widths of the fonts, ``engrave.lyric_text``);
    ``font``, ``bold`` and ``italic`` are its style. The frames say only when the words sound.
    """

    start: int
    end: int
    text: str
    size: float | None = None
    lift: float = 0.0
    at: int | None = None
    dx: float = 0.0
    dy: float | None = None
    width: float | None = None
    font: str = "lora"
    bold: bool = False
    italic: bool = True

    @property
    def free(self) -> bool:
        """Moved by hand: drawn at ``at``, ``dx``, ``dy``."""
        return self.dy is not None


#: The title lines of the new sheet (implementation 03, Phase 8).
TITLE_FIELDS = ("title", "subtitle", "artist")


@dataclass
class Sheet:
    notes: list[Note]
    bars: list[Bar] = field(default_factory=list)  # empty in a frames sheet
    clefs: dict[int, str] = field(default_factory=dict)  # first clef per staff: {1: "G2", 2: "F4"}
    clef_changes: list[tuple[Any, int, str]] = field(
        default_factory=list
    )  # (time or frame, staff, clef)
    key: int | None = None  # key signature of a frames sheet (bars carry it otherwise)
    key_changes: list[tuple[int, int]] = field(default_factory=list)  # frames sheet: (frame, key)
    tempo: float | None = None  # quarter notes per minute (frames sheets; for the matrix)
    quarter_ms: float | None = None  # the reference figure of the new sheet: one negra, in ms
    # What the user writes about the whole sheet (implementation 03, Phase 8; frames sheets, never in an LLM
    # prompt): the title lines, the lyrics pieces, the reference figure of the spacing when Transpose figures
    # renamed the figures (``None``: ``quarter_ms``; the page keeps its widths, D-18), and the space between lines
    # in staff spaces (``None``: the engine's own). :func:`carry_extras` copies them onto a sheet made from this one.
    titles: dict[str, str] = field(default_factory=dict)
    lyrics: list[Lyric] = field(default_factory=list)
    space_ms: float | None = None
    line_space: float | None = None

    def sort(self) -> "Sheet":
        self.notes.sort(key=note_order)
        return self


def carry_extras(source: Sheet, target: Sheet) -> Sheet:
    """``target`` with what the user wrote about the whole of ``source`` (its titles, lyrics, the reference figure
    of the spacing and the space between lines): a sheet laid again on the notes, or written again by the AI,
    keeps them."""
    target.titles = dict(source.titles)
    target.lyrics = [replace(lyric) for lyric in source.lyrics]
    target.space_ms = source.space_ms
    target.line_space = source.line_space
    return target


def note_order(n: Note) -> tuple:
    t = n.time if n.time is not None else Fraction(n.frame or 0)
    return (t, n.staff, 0 if n.grace else 1, n.gslot, n.midi, n.figure or 0)


# ------------------------------------------------------------------ meters and beat positions


def meter_quarters(meter: str) -> Fraction:
    num, den = meter.split("/")
    return Fraction(4 * int(num), int(den))


def beat_unit(meter: str) -> Fraction:
    """Length of one beat in quarters: compound meters (6, 9, 12 over anything) count dotted beats."""
    num, den = (int(x) for x in meter.split("/"))
    if num in (6, 9, 12) and den >= 8:
        return Fraction(12, den)
    return Fraction(4, den)


def pos_text(beat_q: Fraction, meter: str) -> str:
    """Position in the bar as beats from 1: ``1``, ``2+1/2`` (half a beat after beat 2)."""
    unit = beat_unit(meter)
    index = beat_q // unit
    rest = (beat_q - index * unit) / unit
    return f"{index + 1}" + (f"+{rest.numerator}/{rest.denominator}" if rest else "")


def parse_pos(text: str, meter: str) -> Fraction:
    unit = beat_unit(meter)
    whole, _, frac = text.partition("+")
    value = Fraction(int(whole) - 1) + (Fraction(frac) if frac else 0)
    return value * unit


# ------------------------------------------------------------------ clefs


def collapse_clefs(changes: list[tuple], first: dict[int, str]) -> list[tuple]:
    """One clef per staff and time (the last one written there), and no change to the clef in use:
    a format line shows one clef state per hand and time."""
    last: dict[tuple, str] = {}
    for t, staff, clef in sorted(
        changes, key=lambda c: c[0]
    ):  # stable: written order inside one time
        last[(t, staff)] = clef
    out = []
    current = dict(first)
    for (t, staff), clef in sorted(last.items(), key=lambda kv: kv[0][0]):
        if current.get(staff) != clef:
            out.append((t, staff, clef))
            current[staff] = clef
    return out


def frames_from_times(sheet: Sheet, tempo: float, *, grace_ms: float = GRACE_MS) -> list[int]:
    """The 40 ms column of each note of a bars sheet at ``tempo``, with the rule of ``score_to_notes``:
    the k-th of n grace slots before a beat starts (n - k) * 60 ms earlier (the research IR -> matrix rule).
    """
    ms_q = 60000.0 / tempo
    slots: dict[tuple[int, Fraction], int] = defaultdict(int)
    for n in sheet.notes:
        if n.grace:
            k = (n.staff, n.time)
            slots[k] = max(slots[k], n.gslot + 1)
    out = []
    for n in sheet.notes:
        shift = (slots[(n.staff, n.time)] - n.gslot) * grace_ms if n.grace else 0.0
        out.append(frame_of_ms(max(0.0, float(n.time) * ms_q - shift)))
    return out


def frame_of_ms(ms: float, frame_ms: float = FRAME_MS) -> int:
    """Nearest column, halves up: the rule of ``pmn.dense`` (``_round_half_up``)."""
    return int(math.floor(round(float(ms) / frame_ms, 9) + 0.5))


def to_frames_sheet(sheet: Sheet, *, tempo: float, offset: int = 0) -> Sheet:
    """The frames view of a sheet: no bars, no times. Note frames must be filled already
    (``from_ir(..., frames=...)``); clef and key changes get the column of their time at ``tempo``.
    ``offset`` (the column of the passage start) is subtracted from the note columns, which come from
    the whole piece; clef and key changes are computed from the sheet's own (relative) times."""
    ms_q = 60000.0 / tempo

    def col(t: Fraction) -> int:  # times of a sheet are relative to its start already
        return frame_of_ms(float(t) * ms_q)

    notes = [
        replace(
            n, time=None, frame=max(0, n.frame - offset) if n.frame is not None else col(n.time)
        )
        for n in sheet.notes
    ]
    # grace slots count inside one column (graces of one beat can fall in different columns)
    slots: dict[tuple[int, int], dict[tuple, int]] = defaultdict(dict)
    for old, n in sorted(zip(sheet.notes, notes), key=lambda p: (p[0].time, p[0].gslot)):
        if n.grace:
            seen = slots[(n.frame, n.staff)]
            n.gslot = seen.setdefault((old.time, old.gslot), len(seen))
    key = sheet.bars[0].key if sheet.bars else sheet.key
    kchanges = []
    prev = key
    for b in sheet.bars[1:]:
        if b.key != prev:
            kchanges.append((col(b.start), b.key))
            prev = b.key
    return Sheet(
        notes=notes,
        clefs=dict(sheet.clefs),
        clef_changes=collapse_clefs(
            [(col(t), s, c) for t, s, c in sheet.clef_changes], sheet.clefs
        ),
        key=key,
        key_changes=kchanges,
        tempo=tempo,
    ).sort()


# ------------------------------------------------------------------ comparison

FIELDS = ("pitch", "figure", "tuplet", "grace", "ornaments", "ottava")


def _key(n: Note, by_frame: bool) -> tuple:
    return (n.frame if by_frame else n.time, n.staff, n.midi, 0 if n.grace else 1)


def compare(
    ref: Sheet, got: Sheet, *, by_frame: bool = False, fields: Iterable[str] = FIELDS
) -> dict[str, Any]:
    """Agreement of ``got`` with ``ref`` (the IR sheet): notes, each field, beam and tuplet groups,
    bars and clefs. Notes are matched by (time or frame, staff, midi, grace) with their order."""
    fields = tuple(fields)
    buckets: dict[tuple, list[Note]] = defaultdict(list)
    for n in got.notes:
        buckets[_key(n, by_frame)].append(n)
    pairs: list[tuple[Note, Note]] = []
    missing = 0
    ref_size, got_size = _group_sizes(ref.notes), _group_sizes(got.notes)
    for n in ref.notes:
        b = buckets.get(_key(n, by_frame))
        if not b:
            missing += 1
            continue
        # unisons of two voices (same time, hand and pitch): prefer the candidate that looks most like
        # the note (figure, then beam and tuplet group sizes), whatever the order of the voices
        j = max(
            range(len(b)),
            key=lambda i: (
                (b[i].figure, b[i].dots) == (n.figure, n.dots),
                got_size(b[i]) == ref_size(n),
                b[i].tuplet == n.tuplet,
                -i,
            ),
        )
        pairs.append((n, b.pop(j)))
    extra = sum(len(b) for b in buckets.values())
    res: dict[str, Any] = {
        "notes": len(ref.notes),
        "matched": len(pairs),
        "missing": missing,
        "extra": extra,
    }
    for f in fields:
        res[f] = sum(_field_eq(a, b, f) for a, b in pairs)
    for f, attr in (("beams", "beam"), ("tuplet groups", "tgroup")):
        ok, total = _groups_equal(ref.notes, pairs, attr)
        res[f] = ok
        res[f + " total"] = total
    if ref.bars or got.bars:
        res["bars ok"] = int(
            [(b.label, b.start, b.dur, b.meter, b.key) for b in ref.bars]
            == [(b.label, b.start, b.dur, b.meter, b.key) for b in got.bars]
        )
    res["clefs ok"] = int(
        ref.clefs == got.clefs and sorted(ref.clef_changes) == sorted(got.clef_changes)
    )
    return res


def _group_sizes(notes: list[Note]):
    beams = Counter(n.beam for n in notes if n.beam is not None)
    tups = Counter(n.tgroup for n in notes if n.tgroup is not None)
    return lambda n: (
        beams[n.beam] if n.beam is not None else 0,
        tups[n.tgroup] if n.tgroup is not None else 0,
    )


def _field_eq(a: Note, b: Note, f: str) -> bool:
    if f == "pitch":
        return (a.step, a.alter, a.octave) == (b.step, b.alter, b.octave)
    if f == "figure":
        return (a.figure, a.dots) == (b.figure, b.dots)
    if f == "tuplet":
        return a.tuplet == b.tuplet
    if f == "grace":
        return (a.grace, a.gslot) == (b.grace, b.gslot)
    if f == "ornaments":
        return a.ornaments == b.ornaments
    if f == "ottava":
        return a.ottava == b.ottava
    if f == "hand":
        return a.staff == b.staff
    raise KeyError(f)


def _groups_equal(
    ref_notes: list[Note], pairs: list[tuple[Note, Note]], attr: str
) -> tuple[int, int]:
    """How many groups of ``ref`` (beams or tuplets) come back as exactly the same set of notes."""
    partner = {id(a): b for a, b in pairs}
    ref_groups: dict[int, list[Note]] = defaultdict(list)
    for n in ref_notes:
        g = getattr(n, attr)
        if g is not None:
            ref_groups[g].append(n)
    got_members: dict[Any, set[int]] = defaultdict(set)
    for a, b in pairs:
        g = getattr(b, attr)
        if g is not None:
            got_members[g].add(id(a))
    ok = 0
    for g, members in ref_groups.items():
        ids = {id(n) for n in members}
        bs = [partner.get(id(n)) for n in members]
        if any(b is None for b in bs):
            continue
        gs = {getattr(b, attr) for b in bs}
        if len(gs) == 1 and None not in gs and got_members[gs.pop()] == ids:
            ok += 1
    return ok, len(ref_groups)
