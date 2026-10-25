"""F1, frame lines: one line per onset time, both hands on the line, notes from low to high.

Two variants of the same writing:

* **bars**: ``bar`` lines carry the bar number, meter and key; each line starts with its position in
  the bar in beats (``1``, ``2+1/2`` = half a beat after beat 2);
* **frames**: no bars and no beats, as the piano matrix notation; each line starts with its 40 ms
  column (``f57``) and runs of empty columns are written ``[]x10`` (10 empty columns).

A note is ``<pitch>:<figure>`` (``C#4:16``, ``E4:8.`` dotted), or only the pitch when the figure is
not known (a matrix note). Notes of one hand that share everything but the pitch are written as one
chord, ``A2,C#3,E3:8``. Lower-case tags after a note describe it: ``b3`` beam group 3 (every note of a
beam carries the number of its group), ``t3`` triplet (``t5:4`` = 5 in the time of 4; ``(t3`` on the first note of each tuplet group, as
ABC's ``(3``), ``grace`` /
``grace/`` (slashed) grace note, ``arp`` rolled chord, ``tr`` trill, ``trem``, ``ferm``, ``mord``,
``turn``, ``8va`` / ``8vb`` (written an octave lower / higher than it sounds), ``orn`` (an onset played inside
the ornament of the note before it: kept for the matrix, not drawn). ``clef=treble`` before the notes of a hand
changes the clef of that hand at this time. The frames header may carry the reference figure of the new sheet,
``F1 frames frameMs=40 quarterMs=500`` (one negra lasts 500 ms; implementation 03, Phase 2). Example::

    F1 bars
    clefs: R=treble L=bass
    bar 1 meter=4/4 key=3#
    1        L: A2:16 b1
    1+1/4    L: C#3:16 b1
    2        L: A2,E3:8 b2  R: C#4:16 t3 b3
"""

from __future__ import annotations

import re
from fractions import Fraction

from aitu_backend.sheet.sheet.common import (
    ORN_CODES,
    ORN_NAMES,
    key_text,
    parse_key,
    parse_spn,
    renumber_beams,
    spn,
)
from aitu_backend.sheet.sheet.data import (
    CLEF_CODES,
    CLEF_NAMES,
    Bar,
    Note,
    Sheet,
    meter_quarters,
    parse_pos,
    pos_text,
)

__all__ = ["write", "read"]

HAND = {1: "R", 2: "L", 0: "?"}
STAFF = {"R": 1, "L": 2, "?": 0}
_OTTAVA = {1: "8va", -1: "8vb", 2: "15ma", -2: "15mb"}
_OTTAVA_CODES = {v: k for k, v in _OTTAVA.items()}
_FIG = {0: "breve", -1: "long"}
_FIG_CODES = {v: k for k, v in _FIG.items()}


def _tuplet_tag(ratio: str) -> str:
    return "t3" if ratio == "3/2" else f"t{ratio.replace('/', ':')}"


def _note_text(pitches: list[str], n: Note, beam_no: dict[int, int], tstart: bool = False) -> str:
    head = ",".join(pitches)
    if n.figure is not None:
        head += ":" + _FIG.get(n.figure, str(n.figure)) + "." * n.dots
    tags = []
    if n.tuplet:
        tags.append(("(" if tstart else "") + _tuplet_tag(n.tuplet))
    if n.beam is not None:
        tags.append(f"b{beam_no[n.beam]}")
    if n.grace:
        tags.append("grace/" if n.grace == "acc" else "grace")
    tags += [ORN_NAMES.get(o, o) for o in n.ornaments]
    if n.covered:
        tags.append("orn")
    if n.ottava:
        tags.append(_OTTAVA[n.ottava])
    return " ".join([head] + tags)


def _attrs(n: Note, starts: set[int]) -> tuple:
    return (
        n.figure,
        n.dots,
        n.tuplet,
        n.beam,
        n.grace,
        n.gslot,
        n.ornaments,
        n.ottava,
        n.tgroup,
        n.covered,
        id(n) in starts,
    )


def _tuplet_starts(notes: list[Note], anchors: bool = False) -> set[int]:
    """ids of the notes of the first element of each tuplet group (they get ``(t3``). With ``anchors`` one time
    can have several lines (one per column): only the first line of the group's first time is marked, and the
    later lines of that time join the group it opens."""

    def where(n: Note) -> tuple:
        if n.time is None:
            return (n.frame,)
        return (n.time, n.frame if n.frame is not None else -1) if anchors else (n.time,)

    first: dict[int, tuple] = {}
    for n in notes:
        if n.tgroup is not None and (n.tgroup not in first or where(n) < first[n.tgroup][0]):
            first[n.tgroup] = (where(n), n.staff)
    return {id(n) for n in notes if n.tgroup is not None and (where(n), n.staff) == first[n.tgroup]}


def _hand_text(
    notes: list[Note], clef: str | None, beam_no: dict[int, int], starts: set[int]
) -> str:
    parts = [f"clef={CLEF_NAMES.get(clef, clef)}"] if clef else []
    opened: set[int] = set()
    # graces first (in their order), then the main notes, low to high; equal attributes -> one chord
    ordered = sorted(notes, key=lambda n: (0 if n.grace else 1, n.gslot, n.midi))
    group: list[Note] = []
    for n in ordered + [None]:
        if group and (n is None or _attrs(n, starts) != _attrs(group[0], starts)):
            first = id(group[0]) in starts and group[0].tgroup not in opened
            if first:
                opened.add(group[0].tgroup)
            parts.append(
                _note_text(
                    [spn(m.step, m.alter, m.octave) for m in group], group[0], beam_no, first
                )
            )
            group = []
        if n is not None:
            group.append(n)
    return " ".join(parts)


def _slices(sheet: Sheet, key) -> dict:
    out: dict = {}
    for n in sheet.notes:
        out.setdefault(key(n), {}).setdefault(n.staff, []).append(n)
    return out


def write(sheet: Sheet, *, mode: str = "bars", anchors: bool = False) -> str:
    """The sheet as F1 text. ``mode`` is ``"bars"`` (needs bars) or ``"frames"`` (needs frames).

    ``anchors`` (bars only, phase 6): each line also carries the 40 ms column of its notes after the position
    (``2+1/2 f57  L: ...``); notes of one time with different columns (grace notes) get one line each.
    """
    if mode == "bars":
        return _write_bars(sheet, anchors)
    if mode == "frames":
        return _write_frames(sheet)
    raise ValueError(mode)


def _line(
    lead: str, by_staff: dict[int, list[Note]], clefs: dict[int, str], beam_no, starts
) -> str:
    hands = []
    for staff in (2, 1, 0):  # left hand first, as in the prompt's example
        if by_staff.get(staff) or clefs.get(staff):
            hands.append(
                f"{HAND[staff]}: "
                + _hand_text(by_staff.get(staff, []), clefs.get(staff), beam_no, starts)
            )
    return f"{lead:<{14 if ' f' in lead else 8}} " + "  ".join(hands)


def _write_bars(sheet: Sheet, anchors: bool = False) -> str:
    notes = sorted(sheet.notes, key=lambda n: (n.time, n.staff))
    beam_no = renumber_beams(
        sorted(sheet.notes, key=lambda n: (n.time, -n.staff, 0 if n.grace else 1, n.gslot, n.midi))
    )
    # a line is one time (and one column when anchored)
    slices = _slices(
        sheet,
        (
            (lambda n: (n.time, n.frame if n.frame is not None else -1))
            if anchors
            else (lambda n: (n.time, None))
        ),
    )
    starts = _tuplet_starts(sheet.notes, anchors)
    clef_at: dict[Fraction, dict[int, str]] = {}
    for t, staff, clef in sheet.clef_changes:
        clef_at.setdefault(t, {})[staff] = clef
    keys = sorted(
        set(slices) | {(t, None) for t in clef_at if not any(k[0] == t for k in slices)},
        key=lambda k: (k[0], -1 if k[1] is None else k[1]),
    )
    clef_line: dict[Fraction, tuple] = {}
    for k in keys:  # a clef change goes on the last line of its time (after the grace notes)
        if k[0] in clef_at:
            clef_line[k[0]] = k
    lines = [
        "F1 bars",
        f"clefs: R={CLEF_NAMES.get(sheet.clefs.get(1), sheet.clefs.get(1))} "
        f"L={CLEF_NAMES.get(sheet.clefs.get(2), sheet.clefs.get(2))}",
    ]
    bars = sheet.bars
    bi = -1
    meter = key = None
    ti = 0
    for bi, bar in enumerate(bars):
        head = [f"bar {bar.label}"]
        if bar.meter != meter:
            head.append(f"meter={bar.meter}")
            meter = bar.meter
        if bar.key != key:
            head.append(f"key={key_text(bar.key)}")
            key = bar.key
        if bar.dur != meter_quarters(bar.meter):
            head.append(f"len={bar.dur}")
        lines.append(" ".join(head))
        end = bar.start + bar.dur if bi + 1 < len(bars) else None
        while ti < len(keys) and (end is None or keys[ti][0] < end):
            k = keys[ti]
            t = k[0]
            lead = pos_text(t - bar.start, bar.meter)
            if anchors and k[1] is not None and k[1] >= 0:
                lead += f" f{k[1]}"
            clefs = clef_at.get(t, {}) if clef_line.get(t) == k else {}
            lines.append(_line(lead, slices.get(k, {}), clefs, beam_no, starts))
            ti += 1
    del notes
    return "\n".join(lines) + "\n"


def _write_frames(sheet: Sheet) -> str:
    beam_no = renumber_beams(
        sorted(sheet.notes, key=lambda n: (n.frame, -n.staff, 0 if n.grace else 1, n.gslot, n.midi))
    )
    slices = _slices(sheet, lambda n: n.frame)
    starts = _tuplet_starts(sheet.notes)
    clef_at: dict[int, dict[int, str]] = {}
    for f, staff, clef in sheet.clef_changes:
        clef_at.setdefault(f, {})[staff] = clef
    key_at = dict(sheet.key_changes)
    frames = sorted(set(slices) | set(clef_at) | set(key_at))
    head = "F1 frames frameMs=40"
    if sheet.quarter_ms is not None:
        head += f" quarterMs={round(sheet.quarter_ms, 1):g}"
    lines = [
        head,
        f"key={key_text(sheet.key or 0)} clefs: R={CLEF_NAMES.get(sheet.clefs.get(1), sheet.clefs.get(1))} "
        f"L={CLEF_NAMES.get(sheet.clefs.get(2), sheet.clefs.get(2))}",
    ]
    prev = -1
    for f in frames:
        if f - prev - 1 > 0:
            lines.append(f"[]x{f - prev - 1}")
        if f in key_at:
            lines.append(f"f{f} key={key_text(key_at[f])}")
        if slices.get(f) or clef_at.get(f):
            lines.append(_line(f"f{f}", slices.get(f, {}), clef_at.get(f, {}), beam_no, starts))
        prev = f
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ reading

_HAND_SPLIT = re.compile(r"(?:(?<=\s)|^)([LR?]):")
_POS = re.compile(r"^\d+(\+\d+/\d+)?$")


class F1Error(ValueError):
    pass


def read(text: str) -> Sheet:
    """Parse F1 text (either variant) into a sheet. Raises ``F1Error`` with the line on bad input."""
    lines = [ln.rstrip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln.strip() and not ln.lstrip().startswith("#")]
    if not lines or not lines[0].startswith("F1"):
        raise F1Error("the text must start with 'F1 bars' or 'F1 frames'")
    mode = "frames" if "frames" in lines[0] else "bars"
    sheet = Sheet(notes=[])
    for word in lines[0].split()[2:]:
        name, _, value = word.partition("=")
        if name == "quarterMs":
            sheet.quarter_ms = float(value)
    bar: Bar | None = None
    meter: str | None = None
    key: int | None = None
    grace_slots: dict[tuple, int] = {}
    starts: dict[int, int] = {}  # id(note) -> token number, for the notes of a "(t3" token
    for no, ln in enumerate(lines[1:], start=2):
        s = ln.strip()
        try:
            if s.startswith("clefs:") or (s.startswith("key=") and "clefs:" in s):
                if s.startswith("key="):
                    sheet.key = parse_key(s.split()[0][4:])
                for part in s.split("clefs:")[1].split():
                    hand, _, name = part.partition("=")
                    sheet.clefs[STAFF[hand]] = CLEF_CODES.get(name, name)
                continue
            if s.startswith("[]x"):
                int(s[3:])
                continue
            if s.startswith("bar "):
                words = s.split()
                label = words[1]
                length = None
                for w in words[2:]:
                    k, _, v = w.partition("=")
                    if k == "meter":
                        meter = v
                    elif k == "key":
                        key = parse_key(v)
                    elif k == "len":
                        length = Fraction(v)
                    else:
                        raise F1Error(f"unknown bar field {w!r}")
                if meter is None or key is None:
                    raise F1Error("the first bar needs meter= and key=")
                start = bar.start + bar.dur if bar else Fraction(0)
                bar = Bar(
                    label=label,
                    start=start,
                    dur=length if length is not None else meter_quarters(meter),
                    meter=meter,
                    key=key,
                )
                sheet.bars.append(bar)
                continue
            lead, _, rest = s.partition(" ")
            if mode == "frames":
                if not re.fullmatch(r"f\d+", lead):
                    raise F1Error(f"a frames line starts with f<column>, not {lead!r}")
                time, frame = None, int(lead[1:])
                if rest.strip().startswith("key="):
                    sheet.key_changes.append((frame, parse_key(rest.strip()[4:])))
                    continue
            else:
                if bar is None:
                    raise F1Error("a note line before the first bar line")
                if not _POS.match(lead):
                    raise F1Error(f"bad position {lead!r}")
                time, frame = bar.start + parse_pos(lead, bar.meter), None
                anchor, _, after = rest.strip().partition(" ")
                if re.fullmatch(r"f\d+", anchor):  # frame anchor (phase 6)
                    frame, rest = int(anchor[1:]), after
            _read_hands(rest, time, frame, sheet, grace_slots, starts)
        except F1Error as exc:
            raise F1Error(f"line {no}: {exc} :: {ln}") from None
        except (ValueError, KeyError, IndexError) as exc:
            raise F1Error(f"line {no}: {exc} :: {ln}") from None
    _tuplet_groups(sheet.notes, starts)
    return sheet.sort()


def _read_hands(rest: str, time, frame, sheet: Sheet, grace_slots: dict, starts: dict) -> None:
    parts = _HAND_SPLIT.split(rest.strip())
    if parts[0].strip():
        raise F1Error(f"text before the first hand: {parts[0].strip()!r}")
    for hand, body in zip(parts[1::2], parts[2::2]):
        staff = STAFF[hand]
        current: list[Note] = []
        for tok in body.split():
            if tok.startswith("clef="):
                name = tok[5:]
                sheet.clef_changes.append(
                    (time if time is not None else frame, staff, CLEF_CODES.get(name, name))
                )
                continue
            if tok[0] in "ABCDEFG":
                head, _, fig = tok.partition(":")
                figure, dots = None, 0
                if fig:
                    dots = len(fig) - len(fig.rstrip("."))
                    fig = fig.rstrip(".")
                    figure = _FIG_CODES[fig] if fig in _FIG_CODES else int(fig)
                current = []
                for p in head.split(","):
                    step, alter, octave = parse_spn(p)
                    n = Note(
                        time=time,
                        staff=staff,
                        step=step,
                        alter=alter,
                        octave=octave,
                        figure=figure,
                        dots=dots,
                        frame=frame,
                        hand_known=staff != 0,
                    )
                    current.append(n)
                    sheet.notes.append(n)
                continue
            if not current:
                raise F1Error(f"tag {tok!r} before any note")
            if tok.startswith("(t"):
                tok = tok[1:]
                number = len(set(starts.values()))
                for n in current:
                    starts[id(n)] = number
            for n in current:
                _apply_tag(n, tok)
            if tok in ("grace", "grace/"):
                k = (time, staff) if time is not None else (frame, staff)
                slot = grace_slots.get(k, -1) + 1
                grace_slots[k] = slot
                for n in current:
                    n.gslot = slot


def _tuplet_groups(notes: list[Note], starts: dict[int, int]) -> None:
    """Tuplet groups from the ``(t3`` marks, in text order: a mark opens a group (one per token); a
    later tuplet note joins the open group of its beam (or of its hand and ratio when unbeamed)."""
    open_: dict[tuple, int] = {}
    token_group: dict[int, int] = {}
    counter = 0
    for n in notes:  # text order
        if not n.tuplet or n.grace:
            continue
        hand_key = ("hand", n.staff, n.tuplet)
        keys = [("beam", n.beam), hand_key] if n.beam is not None else [hand_key]
        if id(n) in starts:
            tok = starts[id(n)]
            if tok not in token_group:
                counter += 1
                token_group[tok] = counter
            n.tgroup = token_group[tok]
        else:
            found = next((open_[k] for k in keys if k in open_), None)
            if found is None:  # a tuplet note without an opening mark: a group of its own
                counter += 1
                found = counter
            n.tgroup = found
        for k in keys:
            open_[k] = n.tgroup


def _apply_tag(n: Note, tok: str) -> None:
    if re.fullmatch(r"b\d+", tok):
        n.beam = int(tok[1:])
    elif tok == "t3":
        n.tuplet = "3/2"
    elif re.fullmatch(r"t\d+:\d+", tok):
        n.tuplet = tok[1:].replace(":", "/")
    elif tok in ("grace", "grace/"):
        n.grace = "acc" if tok == "grace/" else "unacc"
    elif tok in ORN_CODES:
        n.ornaments = tuple(sorted(n.ornaments + (ORN_CODES[tok],)))
    elif tok in _OTTAVA_CODES:
        n.ottava = _OTTAVA_CODES[tok]
    elif tok == "orn":
        n.covered = True
    else:
        raise F1Error(f"unknown tag {tok!r}")
