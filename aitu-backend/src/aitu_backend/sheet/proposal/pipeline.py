"""The phase 6 algorithm: matrix -> F1-bars sheet without an LLM (the "algorithm alone" proposal).

Steps, each replaceable by the truth to measure its share of the error:

1. **Hands**: given (``hand_sheet``: the product's hand split, aimpromptu's beam search, the research
   ``baseline.today.run``), or the notes' own saved hands (:func:`hand_sheet_of`).
2. **Quarter**: ``proposal.beat.estimate`` (or ``quarter_ms``).
3. **Meter and downbeat**: ``proposal.meter.estimate`` (or ``meter`` + ``phase_ms``).
4. **Quantize**: each column becomes a position in quarters from the first downbeat; per beat the coarsest grid
   that holds its onsets (binary, or triplets in simple meters) is chosen; bars follow the meter (a pickup bar is
   as long as its content).
5. **Figures**: rule 5 of the plan, each onset gets the time to the next onset of its hand, cut at the barline
   (the format keeps the first note of a tie), as the longest written value that fits; triplet positions get
   ``t3`` and one tuplet group per beat and hand.
6. **Rulebook rules** (``baseline.rules``): beams ``beam.1``–``beam.6`` (or by beat), local-key spelling,
   ledger-line clefs.

Every note keeps the column it had in the matrix (``Note.frame``), so the sheet can be scored by
``metrics.score`` and written as F1-bars with frame anchors.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from fractions import Fraction

import numpy as np

from aitu_backend.sheet.proposal import beat, meter as meter_mod, rules
from aitu_backend.sheet.sheet.data import FRAME_MS, Bar, Note, Sheet
from aitu_backend.sheet.sheet.matrix import sheet_from_matrix
from aitu_backend.pmn.notes import Notes

__all__ = ["Proposal", "hand_sheet_of", "propose", "quantize", "figures"]

# written values in quarters -> (figure, dots)
VALUES = sorted(
    [
        (Fraction(4), (1, 0)),
        (Fraction(3), (2, 1)),
        (Fraction(2), (2, 0)),
        (Fraction(3, 2), (4, 1)),
        (Fraction(1), (4, 0)),
        (Fraction(3, 4), (8, 1)),
        (Fraction(1, 2), (8, 0)),
        (Fraction(3, 8), (16, 1)),
        (Fraction(1, 4), (16, 0)),
        (Fraction(1, 8), (32, 0)),
        (Fraction(1, 16), (64, 0)),
    ],
    reverse=True,
)


@dataclass
class Proposal:
    sheet: Sheet  # bars sheet; notes carry time and frame
    quarter_ms: float
    meter: str
    phase_ms: float
    info: dict = field(default_factory=dict)


SIGMA_MS = (
    14.0  # spread of an onset around its grid point (40 ms columns: uniform +-20 ms, sd 11.5 ms)
)
MISFIT_MS = 38.0  # farther than this from the grid: a grace note or a wrong grid
GRACE_COST = 3.0
RHYTHM_COST = (
    2.0  # per extra gap value inside one beat of one hand (a simple rhythm is more likely)
)
# penalty of each grid of ``_grids`` (finer and triplet grids need more evidence)
GRID_PENALTY = {False: (0.0, 2.0, 1.0, 3.5, 3.0), True: (0.0, 1.0, 2.5)}


def _grids(beat_q: Fraction, compound: bool) -> list[tuple[Fraction, bool]]:
    """(grid step in quarters, is a triplet grid), coarsest first."""
    if compound:  # the beat is a dotted quarter: eighths, sixteenths, 32nds
        return [(beat_q / 3, False), (beat_q / 6, False), (beat_q / 12, False)]
    return [
        (beat_q / 2, False),
        (beat_q / 3, True),
        (beat_q / 4, False),
        (beat_q / 6, True),
        (beat_q / 8, False),
    ]


def quantize(
    entries: list[tuple[int, int]],
    quarter_ms: float,
    meter: str,
    phase_ms: float,
    *,
    frame_ms: float = FRAME_MS,
    ms_of=None,
) -> tuple[dict[tuple[int, int], Fraction], set[tuple[int, int]], dict[tuple[int, int], int]]:
    """Positions of the onsets ``entries`` ((staff, column) of each onset).

    Returns the position of each (staff, column) in quarters from the downbeat at ``phase_ms`` (negative for a
    pickup), the onsets on a triplet grid, and the grace notes ((staff, column) -> column of the main note).
    Per beat and hand the grid with the lowest cost is chosen: squared distances of the onsets to the grid
    (in units of the 40 ms rounding noise) plus a penalty for finer and triplet grids (two hands may use two
    grids, e.g. 32nds against sextuplets). An onset farther than 38 ms from the grid is a grace note when an
    on-grid onset of the same hand follows within 80 ms (at most two per hand and beat).
    """
    bar_q, beat_q = (Fraction(x).limit_denominator(4) for x in meter_mod.METERS[meter])
    compound = beat_q != int(beat_q)
    frames = sorted({f for _, f in entries})
    if not frames:
        return {}, set(), {}
    ms_of = ms_of or (
        lambda f: f * frame_ms
    )  # column -> ms (warped to a constant tempo for a performance)
    bar_ms = float(bar_q) * quarter_ms
    t0 = phase_ms - np.ceil((phase_ms - ms_of(frames[0])) / bar_ms) * bar_ms
    # refine the grid offset: median residual of the onsets near a half-beat point
    half = float(beat_q) / 2 * quarter_ms
    res = [((ms_of(f) - t0 + half / 2) % half) - half / 2 for f in frames]
    near = [r for r in res if abs(r) <= 40]
    if near:
        t0 += float(np.median(near))
    pos = {f: (ms_of(f) - t0) / quarter_ms for f in frames}
    by_staff: dict[int, list[int]] = defaultdict(list)
    for st, f in entries:
        by_staff[st].append(f)
    nxt: dict[tuple[int, int], int | None] = {}
    for st, fs in by_staff.items():
        fs = sorted(set(fs))
        for i, f in enumerate(fs):
            nxt[(st, f)] = fs[i + 1] if i + 1 < len(fs) else None
    slack = 40.0 / quarter_ms  # an onset up to 40 ms early belongs to the next beat
    beat_of = {f: int(np.floor((pos[f] + slack) / float(beat_q))) for f in frames}
    out: dict[tuple[int, int], Fraction] = {}
    triplet: set[tuple[int, int]] = set()
    grace: dict[tuple[int, int], int] = {}
    for st, all_fs in by_staff.items():
        beats: dict[int, list[int]] = defaultdict(list)
        for f in sorted(set(all_fs)):
            beats[beat_of[f]].append(f)
        for b, fs in sorted(beats.items()):
            start = b * beat_q
            chosen = None
            for gi, (step, tri) in enumerate(_grids(beat_q, compound)):
                snapped = {
                    f: start + Fraction(round((pos[f] - float(start)) / float(step))) * step
                    for f in fs
                }
                r = {f: abs(float(snapped[f]) - pos[f]) * quarter_ms for f in fs}  # ms
                gr: dict[tuple[int, int], int] = {}
                cost = GRID_PENALTY[compound][gi]
                for f in fs:
                    if r[f] <= MISFIT_MS:
                        cost += (r[f] / SIGMA_MS) ** 2
                        continue
                    n = nxt.get((st, f))
                    if (
                        n is not None
                        and (n - f) * frame_ms <= 80
                        and r.get(n, 0.0) <= MISFIT_MS
                        and len(gr) < 2
                    ):
                        gr[(st, f)] = n
                        cost += GRACE_COST
                    else:
                        cost += (r[f] / SIGMA_MS) ** 2 + 10.0
                main = sorted({snapped[f] for f in fs if (st, f) not in gr})
                cost += RHYTHM_COST * max(0, len({b - a for a, b in zip(main, main[1:])}) - 1)
                if chosen is None or cost < chosen[3]:
                    chosen = (snapped, tri, gr, cost)
            snapped, tri, gr, _ = chosen
            for f in fs:
                out[(st, f)] = snapped[f]
                if tri:
                    triplet.add((st, f))
            grace.update(gr)
    # a grace note before a note of the next beat: resolve chains (grace -> grace -> main)
    for k, v in list(grace.items()):
        seen = 0
        while (k[0], v) in grace and seen < 4:
            v, seen = grace[(k[0], v)], seen + 1
        grace[k] = v
    return out, triplet, grace


def _binary(x: Fraction) -> bool:
    return any(v == x for v, _ in VALUES)


def figures(sheet: Sheet, triplet_times: set[Fraction], beat_q: Fraction) -> None:
    """Figure of each onset: the time to the next onset of the same hand, cut at the barline, as the longest
    written value that fits. A note is a triplet note when its column sits on a triplet grid and its own gap
    is not a plain written value (a quarter on the beat under right-hand triplets stays a quarter); it then
    takes 3/2 of its gap as value and ``t3``, with one tuplet group per beat and hand."""
    ends = [b.start + b.dur for b in sheet.bars]
    starts = [b.start for b in sheet.bars]
    tg = 0
    for staff in (1, 2):
        times = sorted({n.time for n in sheet.notes if n.staff == staff and not n.grace})
        groups: dict[tuple[int, int], int] = {}
        for i, t in enumerate(times):
            bi = max(0, int(np.searchsorted(starts, t, side="right")) - 1)
            gap = (times[i + 1] if i + 1 < len(times) else ends[bi]) - t
            gap = min(gap, ends[bi] - t, Fraction(4))
            off = (t - sheet.bars[bi].start) % beat_q
            on_third = (off * 3 / beat_q).denominator == 1 and off % (beat_q / 2) != 0
            tri = (
                (staff, t) in triplet_times
                and (on_third or not _binary(gap))
                and _binary(gap * Fraction(3, 2))
            )
            value = gap * Fraction(3, 2) if tri else gap
            fig, dots = next((fd for v, fd in VALUES if v <= value), (64, 0))
            key = None
            if tri:
                key = (bi, int((t - sheet.bars[bi].start) // beat_q))
                if key not in groups:
                    tg += 1
                    groups[key] = tg
            for n in sheet.notes:
                if n.staff == staff and n.time == t and not n.grace:
                    n.figure, n.dots = fig, dots
                    n.tuplet = "3/2" if tri else None
                    n.tgroup = groups[key] if tri else None
        for n in sheet.notes:  # grace notes: a slashed eighth
            if n.staff == staff and n.grace:
                n.figure, n.dots = 8, 0


def number_grace_slots(notes: list[Note]) -> None:
    """Grace notes of one hand and time in different columns are successive graces: one slot per column, in
    column order (graces in one column are one chord and share a slot)."""
    cols: dict[tuple, set[int]] = {}
    for n in notes:
        if n.grace:
            cols.setdefault((n.staff, n.time), set()).add(n.frame)
    for n in notes:
        if n.grace:
            n.gslot = sorted(cols[(n.staff, n.time)]).index(n.frame)


def build_sheet(
    notes: list[Note],
    quarter_ms: float,
    meter: str,
    phase_ms: float,
    key: int = 0,
    key_changes: list[tuple[int, int]] | None = None,
    ms_of=None,
) -> Sheet:
    """A bars sheet from matrix notes (frame, staff, pitch): positions, bars, figures. No beams yet."""
    pos, tri_frames, grace = quantize(
        [(n.staff, n.frame) for n in notes], quarter_ms, meter, phase_ms, ms_of=ms_of
    )
    bar_q, beat_q = (Fraction(x).limit_denominator(4) for x in meter_mod.METERS[meter])
    main = [k for k in pos if k not in grace]
    first, last = min(pos[k] for k in main), max(pos[k] for k in main)
    k0 = first // bar_q  # bar index of the first onset (downbeat at 0)
    # a pickup bar is as long as its content: from the first onset to the next downbeat
    pickup = first > k0 * bar_q
    origin = first if pickup else k0 * bar_q
    bars: list[Bar] = []
    keys = sorted(key_changes or [])

    def key_at(frame: int) -> int:
        k = key
        for f, kk in keys:
            if f <= frame:
                k = kk
        return k

    frame_at = sorted((p, f) for (_, f), p in pos.items())
    start = origin
    label = 0 if pickup else 1
    meter_text = meter
    while start <= last:
        end = (start // bar_q + 1) * bar_q
        f = next((fr for p, fr in frame_at if p >= start), frame_at[-1][1])
        bars.append(
            Bar(
                label=str(label),
                start=start - origin,
                dur=end - start,
                meter=meter_text,
                key=key_at(f),
            )
        )
        start, label = end, label + 1
    out = []
    for n in notes:
        g = grace.get((n.staff, n.frame))
        t = pos[(n.staff, g)] if g is not None else pos[(n.staff, n.frame)]
        out.append(
            Note(
                time=t - origin,
                staff=n.staff,
                step=n.step,
                alter=n.alter,
                octave=n.octave,
                frame=n.frame,
                eid=n.eid,
                grace="acc" if g is not None else None,
            )
        )
    number_grace_slots(out)
    sheet = Sheet(notes=out, bars=bars, clefs={1: "G2", 2: "F4"})
    figures(sheet, {(st, pos[(st, f)] - origin) for st, f in tri_frames}, beat_q)
    return sheet.sort()


def hand_sheet_of(notes: Notes, *, key: int = 0) -> Sheet:
    """A frames sheet with the notes' own hands (one note per onset cell). A note without a hand gets one by middle C
    (C4 and up: right hand); the product gives every note a hand before (aimpromptu's hand split).
    """
    hs = sheet_from_matrix(notes, key=key)
    for n in hs.notes:
        if n.staff == 0:
            n.staff, n.hand_known = (1 if n.midi >= 60 else 2), True
    return hs


def propose(
    notes: Notes,
    *,
    key: int = 0,
    key_changes: list[tuple[int, int]] | None = None,
    quarter_ms: float | None = None,
    meter: str | None = None,
    phase_ms: float | None = None,
    beams: str = "classical",
    hand_sheet: Sheet | None = None,
    track: bool = False,
) -> Proposal:
    """The whole algorithm. ``hand_sheet`` (a frames sheet with hands) gives step 1; without it the notes' own hands
    are used (:func:`hand_sheet_of`). ``track`` follows a moving tempo (a real performance, the pop songs): beats are
    tracked (``beat.track``) and the columns are warped to a constant tempo before the meter, the quantization and
    the figures."""
    hs = hand_sheet if hand_sheet is not None else hand_sheet_of(notes, key=key)
    cols = np.array([n.frame for n in hs.notes])
    midi = np.array([n.midi for n in hs.notes])
    info: dict = {}
    if quarter_ms is None:
        quarter_ms, info["quarter_prob"] = beat.estimate(cols, midi)[0]
    ms_of = None
    if track:
        beats = beat.track(cols, midi, quarter_ms) / FRAME_MS  # beat columns
        idx = np.arange(len(beats), dtype=float)
        ms_of = (
            lambda f: float(
                np.interp(
                    f,
                    beats,
                    idx,
                    left=(f - beats[0]) / (beats[1] - beats[0]) if len(beats) > 1 else 0,
                    right=None,
                )
            )
            * quarter_ms
        )  # noqa: E731
        cols = np.array([int(round(ms_of(f) / FRAME_MS)) for f in cols])
        info["beats"] = len(beats)
    if meter is None or phase_ms is None:
        g = meter_mod.estimate(cols, midi, quarter_ms)[0]
        meter, phase_ms, info["meter_prob"] = g.meter, g.phase_ms, g.prob
    sheet = build_sheet(hs.notes, quarter_ms, meter, phase_ms, key, key_changes, ms_of=ms_of)
    if beams == "classical":
        rules.beams_classical(sheet)
    elif beams == "beat":
        rules.beams_beat(sheet)
    rules.spell_local(sheet)
    rules.clefs_ledger(sheet)
    return Proposal(sheet=sheet, quarter_ms=quarter_ms, meter=meter, phase_ms=phase_ms, info=info)
