"""What the LLM step checks and reads back (phase 6; product core since phase 15): the checker of an answer, the
decided context lines (the last bars and the hand ranges), and the bars of a sheet between two columns.

:func:`check` lists what is wrong with an answer for a window (parse error, onsets lost or added, a position that goes
back in time); ``strict`` adds the rules made for small models. :mod:`aitu_backend.sheet.llm.guards` holds the phase 14 rules
that the product chain adds to every check.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import replace

from aitu_backend.sheet.sheet import f1
from aitu_backend.sheet.sheet.common import spn
from aitu_backend.sheet.sheet.data import Note, Sheet, beat_unit

__all__ = [
    "answer_text",
    "check",
    "cut_bars",
    "last_bars_text",
    "range_lines",
    "strip_answer",
    "style_errors",
]


def _cut_bars(sheet: Sheet, lo: int, hi: int, offset: int) -> Sheet:
    """Notes of a bars sheet with a column in [lo, hi) and the bars that hold them; columns made relative."""
    notes = [
        replace(n, frame=n.frame - offset)
        for n in sheet.notes
        if n.frame is not None and lo <= n.frame < hi
    ]
    if not notes:
        return Sheet(notes=[], bars=[])
    t0, t1 = min(n.time for n in notes), max(n.time for n in notes)
    bars = [b for b in sheet.bars if b.start + b.dur > t0 and b.start <= t1]
    tg = {n.tgroup for n in notes}
    keep = Sheet(
        notes=notes,
        bars=bars,
        clefs=dict(sheet.clefs),
        clef_changes=[c for c in sheet.clef_changes if t0 <= c[0] <= t1],
    )
    # the clef at the window start
    for t, st, c in sorted(sheet.clef_changes):
        if t < t0:
            keep.clefs[st] = c
    del tg
    return keep


cut_bars = _cut_bars


# ------------------------------------------------------------------ context


def range_lines(sheet: Sheet, last_bars: int = 2) -> list[str]:
    """One line per hand and bar for the last bars of a decided sheet: ``bar 7 LH range: Bb2–F4, jumps: 1``
    (a jump is a move of more than an octave between consecutive onsets of the hand)."""
    out = []
    bars = sheet.bars[-last_bars:]
    for b in bars:
        for st, name in ((2, "LH"), (1, "RH")):
            ns = sorted(
                (
                    n
                    for n in sheet.notes
                    if n.staff == st and b.start <= n.time < b.start + b.dur and not n.grace
                ),
                key=lambda n: (n.time, n.midi),
            )
            if not ns:
                out.append(f"bar {b.label} {name}: no notes")
                continue
            lo, hi = min(ns, key=lambda n: n.midi), max(ns, key=lambda n: n.midi)
            tops = [max(m.midi for m in ns if m.time == t) for t in sorted({n.time for n in ns})]
            jumps = sum(abs(x - y) > 12 for x, y in zip(tops, tops[1:]))
            out.append(
                f"bar {b.label} {name} range: {spn(lo.step, lo.alter, lo.octave)}-"
                f"{spn(hi.step, hi.alter, hi.octave)}, jumps: {jumps}"
            )
    return out


def last_bars_text(text: str, n: int = 2) -> str:
    """The header and the last ``n`` bars of an F1-bars text (with their meter and key repeated)."""
    lines = text.strip().splitlines()
    bar_idx = [i for i, ln in enumerate(lines) if ln.startswith("bar ")]
    if len(bar_idx) <= n:
        return text.strip()
    meter = key = None
    for i in bar_idx[:-n]:
        for w in lines[i].split()[2:]:
            if w.startswith("meter="):
                meter = w
            elif w.startswith("key="):
                key = w
    # the clefs in force at the first bar shown (a clef change in the bars left out moves the header; phase 7 fix)
    clefs = (
        dict(re.findall(r"\b([RL])=(treble|bass)\b", lines[1]))
        if lines[1].startswith("clefs:")
        else {}
    )
    for ln in lines[2 : bar_idx[-n]]:
        for hand, c in re.findall(r"\b([RL]):\s*clef=(treble|bass)", ln):
            clefs[hand] = c
    if clefs:
        lines[1] = "clefs: " + " ".join(f"{h}={clefs[h]}" for h in ("R", "L") if h in clefs)
    first = lines[bar_idx[-n]]
    words = first.split()
    if meter and not any(w.startswith("meter=") for w in words):
        words.insert(2, meter)
    if key and not any(w.startswith("key=") for w in words):
        words.insert(3 if meter else 2, key)
    return "\n".join(lines[:2] + [" ".join(words)] + lines[bar_idx[-n] + 1 :])


# ------------------------------------------------------------------ check


def answer_text(reply: str) -> str:
    """The answer inside a model's reply: the fenced blocks joined, else the whole reply (phase 12 ``llm.driver``).
    The product chain checks this text: the prompt asks for one fenced block that starts with the ``# quarter=``
    comment line, which :func:`check` alone does not unwrap."""
    blocks = re.findall(r"```[a-zA-Z0-9_-]*\n(.*?)```", reply, re.S)
    if blocks:
        return "\n".join(b.rstrip("\n") for b in blocks) + "\n"
    return reply.strip() + "\n"


def _strip(text: str) -> str:
    """The F1 text inside an answer (a ```f1 block if any; else the lines from 'F1 bars')."""
    m = re.search(r"```[a-zA-Z0-9]*\n(F1 bars.*?)```", text, re.S)
    if m:
        return m.group(1)
    i = text.find("F1 bars")
    return text[i:] if i >= 0 else text


WIDE_UNROLLED = (
    16  # one hand reaches a tenth; a wider chord must be marked arp (phase 7 §9, enrich.check)
)


def style_errors(sheet: Sheet) -> list[str]:
    """Checker rules for small models (phase 7 §9, phase 12): a one-hand chord wider than a tenth not marked
    ``arp``, and two short notes (eighth or shorter) of one hand in one beat without a beam."""
    errs: list[str] = []
    cols: dict[tuple, list[Note]] = {}
    for n in sheet.notes:
        if not n.grace and n.time is not None:
            cols.setdefault((n.staff, n.time), []).append(n)
    wide = [
        (st, t, ns)
        for (st, t), ns in cols.items()
        if max(n.midi for n in ns) - min(n.midi for n in ns) > WIDE_UNROLLED
        and not any("arpeggio" in n.ornaments for n in ns)
    ]
    if wide:
        st, t, ns = min(wide, key=lambda x: x[1])
        lo, hi = min(ns, key=lambda n: n.midi), max(ns, key=lambda n: n.midi)
        errs.append(
            f"{len(wide)} one-hand chords wider than a tenth are not marked arp (one hand reaches a tenth: "
            f"mark the chord 'arp' or give its low notes to the other hand), first {'R' if st == 1 else 'L'}: "
            f"{_name(lo.midi)}..{_name(hi.midi)} at f{ns[0].frame}"
        )
    loose = []
    for st in (1, 2):
        els = sorted((t, ns) for (s, t), ns in cols.items() if s == st)
        for (t0, a), (t1, b) in zip(els, els[1:]):
            if not all(n.figure and n.figure >= 8 and n.beam is None for n in a + b):
                continue
            bar = next((x for x in sheet.bars if x.start <= t0 < x.start + x.dur), None)
            if bar is None or t1 >= bar.start + bar.dur:
                continue
            unit = beat_unit(bar.meter)
            if (t0 - bar.start) // unit == (t1 - bar.start) // unit:
                loose.append((st, a[0]))
    if loose:
        st, n = loose[0]
        errs.append(
            f"{len(loose)} places where two short notes (eighth or shorter) of one hand in one beat have no "
            f"beam (give them one beam number), first {'R' if st == 1 else 'L'}: at f{n.frame}"
        )
    return errs


def check(
    answer: str, target: Sheet, *, allow_changes: bool = False, strict: bool = False
) -> tuple[list[str], Sheet | None]:
    """Problems of an answer for a window (empty list = accepted) and the parsed sheet. ``strict`` adds the
    checker rules for small models (:func:`style_errors`)."""
    text = _strip(answer)
    try:
        sheet = f1.read(text)
    except f1.F1Error as exc:
        return [f"parse error: {exc}"], None
    if not text.startswith("F1 bars"):
        return ["the answer must be F1 bars (first line 'F1 bars')"], None
    errs: list[str] = []
    if not sheet.bars:
        errs.append("no bar lines")
    no_anchor = [n for n in sheet.notes if n.frame is None]
    if no_anchor:
        errs.append(
            f"{len(no_anchor)} notes without a frame anchor (write 'POSITION fN' at the start of each line)"
        )
    no_fig = [n for n in sheet.notes if n.figure is None]
    if no_fig:
        errs.append(
            f"{len(no_fig)} notes without a figure, e.g. {spn(no_fig[0].step, no_fig[0].alter, no_fig[0].octave)}"
        )
    no_hand = [n for n in sheet.notes if n.staff not in (1, 2)]
    if no_hand:
        errs.append(f"{len(no_hand)} notes without a hand (use L: or R:)")
    for b in sheet.bars:
        bad = [
            n
            for n in sheet.notes
            if n.time is not None
            and b.start <= n.time
            and n.time >= b.start + b.dur
            and b is sheet.bars[-1]
        ]
        if bad:
            errs.append(f"bar {b.label}: a position beyond the end of the bar")
            break
    want = Counter((n.frame, n.midi) for n in target.notes)
    got = Counter((n.frame, n.midi) for n in sheet.notes if n.frame is not None)
    missing = want - got
    extra = got - want
    if not allow_changes and (missing or extra):

        def show(c: Counter) -> str:
            items = sorted(c.elements())[:8]
            return ", ".join(f"f{f} {_name(m)}" for f, m in items) + (
                " ..." if sum(c.values()) > 8 else ""
            )

        if missing:
            errs.append(f"{sum(missing.values())} onsets of the input are missing: {show(missing)}")
        if extra:
            errs.append(
                f"{sum(extra.values())} onsets are not in the input (wrong frame or pitch): {show(extra)}"
            )
    # positions must follow the frames (a grace note may share the time of a later column)
    pts = sorted({(n.frame, n.time) for n in sheet.notes if n.frame is not None and not n.grace})
    back = [(a, b) for a, b in zip(pts, pts[1:]) if b[1] < a[1]]
    if back:
        (f0, t0), (fb, tb) = back[0]
        errs.append(
            f"{len(back)} places where a later frame gets an earlier position, first at f{fb}"
        )
    if strict:
        errs += style_errors(sheet)
    return errs, sheet


def _name(midi: int) -> str:
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    return f"{names[midi % 12]}{midi // 12 - 1}"


strip_answer = _strip
