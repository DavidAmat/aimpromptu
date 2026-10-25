"""The rule baselines of the rulebook (§8), as functions on a sheet (phase 5; product core since phase 15).

Each function changes one topic of a **bars sheet** in place (notes with ``time``; bars, meters and keys
known), so that it can replace that topic of any proposal: of the score itself (to measure the rule
alone, every other topic true), of today's sheet, or of an LLM output in phase 6. Rules were tuned on the
train split in phase 3 (research ``patterns.*``); the functions here re-implement them on the sheet content:

* :func:`beams_classical` (``beam.1``–``beam.6``, ``patterns.beaming.predict_bars``) and
  :func:`beams_beat` (break at every beat, ``predict_beat``);
* :func:`clefs_ledger`: fewest ledger lines with a switch cost (``patterns.clefs.predict``);
* :func:`spell_local`: the key signature's names, then the local key (± 2 quarters) and the degree and
  direction table learnt on train (``patterns.spelling``, rule ``sig_then_local2``);
* :func:`hands_envelope`: the hand whose envelope in the previous bar holds the note, using the rule's
  **own** previous decisions (``patterns.hand_range.envelope_rule`` used the true previous bar);
  :func:`hands_middle_c`.
"""

from __future__ import annotations

import json
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

import numpy as np

from aitu_backend.sheet.proposal.theory import (
    LEVELS,
    STEP_PC,
    Meter,
    Params,
    diatonic,
    key_spelling,
    ledger_lines,
    metric_level,
    parse_meter,
    predict,
    spell,
    step_dir,
    tonic_pc,
)
from aitu_backend.sheet.sheet.common import figure_quarters
from aitu_backend.sheet.sheet.data import Note, Sheet
from aitu_backend.sheet.sheet.pitch import STEPS

__all__ = [
    "beams_beat",
    "beams_classical",
    "clefs_ledger",
    "hands_envelope",
    "hands_middle_c",
    "spell_local",
    "spelling_tables",
]

RANK = {lvl: i for i, lvl in enumerate(LEVELS)}
C4 = 60


# ----------------------------------------------------------------------------- bars


def _bar_of(sheet: Sheet):
    starts = [b.start for b in sheet.bars]

    def at(t: Fraction) -> int:
        return max(0, int(np.searchsorted(starts, t, side="right")) - 1)

    return at


def _offsets(sheet: Sheet) -> list[Fraction]:
    """Shift of each short bar so that positions count from the real barline (``beaming._bar_offsets``)."""
    out, prev_short = [], None
    for i, b in enumerate(sheet.bars):
        m = parse_meter(b.meter)
        off = Fraction(0)
        if m and b.dur < m.bar:
            if i == 0:
                off = m.bar - b.dur
            elif prev_short is not None and prev_short + b.dur == m.bar:
                off = prev_short
            prev_short = b.dur if prev_short is None or off == 0 else None
        else:
            prev_short = None
        out.append(off)
    return out


def _dur(n: Note) -> Fraction:
    q = figure_quarters(n.figure, n.dots)
    if n.tuplet:
        a, b = (int(x) for x in n.tuplet.split("/"))
        q = q * b / a
    return q


# ----------------------------------------------------------------------------- beams


def beams_classical(sheet: Sheet) -> None:
    """Rules beam.1–beam.6 with bars and beats (``predict_bars``)."""
    _beam(sheet, _break_classical)


def beams_beat(sheet: Sheet) -> None:
    """Break at every beat and stronger (``predict_beat``): what a format with beats but no bars allows."""
    _beam(sheet, lambda level, meter, fig, change: RANK[level] <= RANK["beat"])


def _break_classical(level: str, meter: Meter | None, fig: int, change: bool) -> bool:
    if meter is None:
        limit = RANK["beat"]
    elif fig <= 8:
        if not meter.compound and meter.nbeats >= 4 and meter.nbeats % 2 == 0:
            limit = RANK["half"]
        elif not meter.compound and meter.den == 4 and meter.num in (2, 3):
            limit = RANK["beat"] if change else RANK["bar"]
        else:
            limit = RANK["beat"]
    elif fig == 16:
        limit = RANK["sub"] if (meter.num, meter.den) == (2, 2) else RANK["beat"]
    else:
        limit = RANK["sub"]
    return RANK[level] <= limit


def _beam(sheet: Sheet, breaks) -> None:
    """Join consecutive beamable elements of each staff (an eighth or shorter that ends where the next
    element starts) unless the barline, a tuplet border or ``breaks(level, meter, figure, change)`` cuts.
    """
    for n in sheet.notes:
        n.beam = None
    bar_of, offsets = _bar_of(sheet), _offsets(sheet)
    counter = 0
    for staff in (1, 2):
        el: dict[Fraction, list[Note]] = defaultdict(list)
        for n in sheet.notes:
            if n.staff == staff and not n.grace and n.figure is not None and n.figure >= 8:
                el[n.time].append(n)
        times = sorted(el)
        chain: list[Fraction] = []

        def close() -> None:
            nonlocal counter
            if len(chain) > 1:
                counter += 1
                for t in chain:
                    for n in el[t]:
                        n.beam = counter

        for t in times:
            if chain:
                a, b = el[chain[-1]], el[t]
                ta = chain[-1]
                join = any(x.time + _dur(x) == t for x in a)
                ia, ib = bar_of(ta), bar_of(t)
                if join and ia != ib:
                    join = False
                if join and {x.tgroup for x in a} != {x.tgroup for x in b}:
                    join = False
                if join:
                    bar = sheet.bars[ib]
                    meter = parse_meter(bar.meter)
                    level = metric_level(t - bar.start + offsets[ib], meter) if meter else "other"
                    fig = min(min(x.figure for x in a), min(x.figure for x in b))
                    change = _dur(a[0]) != _dur(b[0])
                    join = not breaks(level, meter, fig, change)
                if not join:
                    close()
                    chain = []
            chain.append(t)
        close()


# ----------------------------------------------------------------------------- clefs


def clefs_ledger(
    sheet: Sheet, *, switch: float = 3, stay: int = 1, between_beams: bool = True
) -> None:
    """Clef per onset slice of each staff by fewest ledger lines (sum over the chord) with a switch cost;
    with ``between_beams`` a change is only allowed at the first note of a beam group or outside beams
    (phase 3: switch 3, stay 1; without beams the best setting is switch 4)."""
    usual = {1: "G2", 2: "F4"}
    other = {1: "F4", 2: "G2"}
    sheet.clefs = dict(usual)
    changes = []
    for staff in (1, 2):
        sl: dict[Fraction, list[Note]] = defaultdict(list)
        for n in sheet.notes:
            if n.staff == staff:
                sl[n.time].append(n)
        times = sorted(sl)
        if not times:
            continue
        d = [[diatonic(n.step, n.octave) for n in sl[t]] for t in times]
        cost = np.array(
            [
                [
                    sum(int(ledger_lines(x, usual[staff])) for x in ds),
                    sum(int(ledger_lines(x, other[staff])) for x in ds),
                ]
                for ds in d
            ],
            dtype=float,
        )
        allowed = None
        if between_beams:
            seen: set[int] = set()
            allowed = np.ones(len(times), dtype=bool)
            for i, t in enumerate(times):
                beams = {n.beam for n in sl[t] if n.beam is not None}
                allowed[i] = not (beams & seen)
                seen |= beams
        pred = predict(cost, staff, Params(switch, stay, "sum"), allowed)
        if pred[0]:
            sheet.clefs[staff] = other[staff]
        for i in range(1, len(times)):
            if pred[i] != pred[i - 1]:
                changes.append((times[i], staff, other[staff] if pred[i] else usual[staff]))
    sheet.clef_changes = sorted(changes, key=lambda c: (c[0], c[1]))


# ----------------------------------------------------------------------------- spelling

TABLES = Path(__file__).with_name(
    "spelling_tables.json"
)  # learnt on train (research: ``baseline.rules.learn_tables``)


def spelling_tables() -> tuple[dict, dict]:
    """The degree and degree + direction tables of ``sig_then_local2``, learnt on train (frozen file)."""
    body = json.loads(TABLES.read_text())
    return (
        {(m, int(d)): bool(v) for m, d, v in body["deg"]},
        {(m, int(d), s): bool(v) for m, d, s, v in body["deg_dir"]},
    )


def _mode(sheet: Sheet) -> str:
    """From the last bass note, as ``patterns.spelling._modes``."""
    last = max(n.time for n in sheet.notes)
    bass = min(n.midi for n in sheet.notes if n.time == last) % 12
    t = tonic_pc(sheet.bars[-1].key)
    return "major" if bass == t else "minor" if bass == (t + 9) % 12 else "other"


def spell_local(
    sheet: Sheet, tables: tuple[dict, dict] | None = None, *, window: float = 2
) -> None:
    deg, deg_dir = tables or spelling_tables()
    if not sheet.notes:
        return
    bar_of = _bar_of(sheet)
    mode = _mode(sheet)
    member = np.zeros((15, 12))
    for j, f in enumerate(range(-7, 8)):
        member[j, list(key_spelling(f))] = 1
    order = sorted(sheet.notes, key=lambda n: n.time)
    on = np.array([float(n.time) for n in order])
    onehot = np.zeros((len(order) + 1, 12))
    onehot[np.arange(1, len(order) + 1), [n.midi % 12 for n in order]] = 1
    cum = onehot.cumsum(axis=0)
    slices: dict[int, dict[Fraction, list[int]]] = {1: defaultdict(list), 2: defaultdict(list)}
    for n in order:
        if n.staff in (1, 2):
            slices[n.staff][n.time].append(n.midi)
    stimes = {s: sorted(v) for s, v in slices.items()}
    fifths = np.arange(-7, 8)
    for i, n in enumerate(order):
        pc, sig = n.midi % 12, sheet.bars[bar_of(n.time)].key
        if pc in key_spelling(sig):
            si, alter = key_spelling(sig)[pc]
        else:
            lo, hi = np.searchsorted(on, on[i] - window), np.searchsorted(
                on, on[i] + window, side="right"
            )
            score = (cum[hi] - cum[lo]) @ member.T
            score = score - 1e-3 * np.abs(fifths - sig) + 1e-2 * (fifths == sig)
            local = int(fifths[np.argmax(score)])
            d = _direction(n, slices, stimes)
            degree = (pc - tonic_pc(local)) % 12
            raise_ = deg_dir.get((mode, degree, d), deg.get((mode, degree)))
            si, alter = spell(pc, local, raise_)
        midi = n.midi
        n.step, n.alter = STEPS[si], int(alter)
        n.octave = (midi - int(STEP_PC[si]) - n.alter) // 12 - 1


def _direction(n: Note, slices, stimes) -> str:
    if n.staff not in (1, 2):
        return "other"
    ts = stimes[n.staff]
    k = ts.index(n.time)
    nxt = prv = np.nan
    if k + 1 < len(ts):
        c = np.array(slices[n.staff][ts[k + 1]])
        nxt = float(c[np.argmin(np.abs(c - n.midi))] - n.midi)
    if k > 0:
        c = np.array(slices[n.staff][ts[k - 1]])
        prv = float(n.midi - c[np.argmin(np.abs(c - n.midi))])
    return step_dir(nxt, prv)


# ----------------------------------------------------------------------------- hands


def hands_middle_c(sheet: Sheet) -> None:
    for n in sheet.notes:
        n.staff = 1 if n.midi >= C4 else 2


def hands_envelope(sheet: Sheet) -> None:
    """Bar by bar: a note goes to the hand whose envelope (lowest to highest note) in the previous bar
    holds it or is nearest; ties by the nearer median; middle C when a hand has no notes there. The
    previous bar is the rule's own decision. Inside one slice the left hand takes the lowest notes.
    """
    bar_of = _bar_of(sheet)
    by_bar: dict[int, list[Note]] = defaultdict(list)
    for n in sheet.notes:
        by_bar[bar_of(n.time)].append(n)
    prev: list[Note] = []
    for m in sorted(by_bar):
        env = {}
        for s in (1, 2):
            p = [n.midi for n in prev if n.staff == s]
            if p:
                env[s] = (min(p), max(p), float(np.median(p)))
        notes = by_bar[m]
        for n in notes:
            if len(env) < 2:
                n.staff = 1 if n.midi >= C4 else 2
                continue
            d = {s: max(0, lo - n.midi, n.midi - hi) for s, (lo, hi, _) in env.items()}
            if d[1] != d[2]:
                n.staff = 1 if d[1] < d[2] else 2
            else:
                n.staff = 1 if abs(n.midi - env[1][2]) < abs(n.midi - env[2][2]) else 2
        sl: dict[Fraction, list[Note]] = defaultdict(list)
        for n in notes:
            sl[n.time].append(n)
        for group in sl.values():
            group.sort(key=lambda n: n.midi)
            k = sum(n.staff == 2 for n in group)
            for i, n in enumerate(group):
                n.staff = 2 if i < k else 1
        prev = notes
