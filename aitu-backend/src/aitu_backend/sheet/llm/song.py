"""The window chain over a whole song (phase 7; product core since phase 15): windows, what an accepted answer
decides, and the join of the kept bars.

A song has no score and no barlines, so windows are cut in frames. Window 1 starts at the first onset; its target holds
about 8 bars of the quarter and meter known so far (the algorithm's estimate for window 1, then the tempo of the kept
bars of the last answer), at most ``MAX_ONSETS`` onsets. When an answer is accepted, its **last bar is not kept** (the
target may end inside it): the next window starts at the first onset of that bar and decides it again, now with what
follows. The kept bars of all windows, joined, are the song's sheet (:func:`join`). The chain itself is
:mod:`aitu_backend.sheet.llm.chain`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from fractions import Fraction

import numpy as np

from aitu_backend.sheet.proposal.pipeline import number_grace_slots
from aitu_backend.sheet.sheet.data import Bar, Note, Sheet, meter_quarters

__all__ = [
    "Decided",
    "decided",
    "frame_of_time",
    "frames_per_quarter",
    "join",
    "quarter_of",
    "snap",
    "target_window",
    "next_window",
]

WINDOW_BARS = 8
LOOKAHEAD_BARS = 2
MAX_ONSETS = 200


def target_window(
    frames: Sheet, start: int, quarter_frames: float, meter: str
) -> tuple[Sheet, Sheet, int]:
    """The target (frames ``start``..end, about 8 bars, at most ``MAX_ONSETS`` onsets) and the look-ahead (the next 2
    bars) of a song's frames sheet (every onset cell, no hand), with song columns; and ``end`` (exclusive).
    """
    last_frame = max(n.frame for n in frames.notes)
    bar_frames = float(meter_quarters(meter)) * quarter_frames
    end = int(round(start + WINDOW_BARS * bar_frames))
    cols = sorted({n.frame for n in frames.notes if n.frame >= start})
    count = 0
    for c in cols:  # cut at a column: at most MAX_ONSETS onsets
        count += sum(1 for n in frames.notes if n.frame == c)
        if count > MAX_ONSETS and c < end:
            end = c
            break
    if end >= last_frame:
        end = last_frame + 1
    look_end = int(round(end + LOOKAHEAD_BARS * bar_frames))

    def part(a: int, b: int) -> Sheet:
        return Sheet(
            notes=[replace(n) for n in frames.notes if a <= n.frame < b],
            clefs={1: "G2", 2: "F4"},
            key=frames.key,
        )

    return part(start, end), part(end, look_end), end


QUARTER_LINE = re.compile(r"#\s*quarter\s*=\s*([0-9.]+)\s*frames.*?meter\s*=\s*([0-9]+/[0-9]+)")


def quarter_of(answer: str) -> tuple[float, str] | None:
    m = QUARTER_LINE.search(answer)
    return (float(m.group(1)), m.group(2)) if m else None


@dataclass
class Decided:
    kept: Sheet  # the answer without its last bar (all of it for the last window)
    next_start: int | None  # first frame of the next window (None: the song is done)
    next_bar: int  # label of the first bar of the next window
    kept_text: str  # F1 bars text of the kept bars (the context of the next window)


def _drop_last_bar_text(text: str) -> str:
    lines = text.strip().splitlines()
    idx = [i for i, ln in enumerate(lines) if ln.startswith("bar ")]
    return "\n".join(lines[: idx[-1]]) if len(idx) > 1 else text.strip()


def decided(text: str, sheet: Sheet, *, start: int, end: int, last: bool) -> Decided:
    """What an accepted answer decides. The last bar is dropped (decided again by the next window) unless this is the
    song's last window or the last bar starts in the first half of the window (then all is kept: progress).
    """
    bars = sheet.bars
    label = int(bars[-1].label) if bars and bars[-1].label.lstrip("-").isdigit() else len(bars)
    if last or len(bars) < 2:
        return Decided(
            kept=sheet, next_start=None if last else end, next_bar=label + 1, kept_text=text
        )
    t_last = bars[-1].start
    in_last = [n for n in sheet.notes if n.time is not None and n.time >= t_last]
    first = min((n.frame for n in in_last if n.frame is not None), default=end)
    if first - start < (end - start) / 2:
        return Decided(kept=sheet, next_start=end, next_bar=label + 1, kept_text=text)
    kept = Sheet(
        notes=[n for n in sheet.notes if n.frame is not None and n.frame < first],
        bars=bars[:-1],
        clefs=dict(sheet.clefs),
        clef_changes=[c for c in sheet.clef_changes if c[0] < t_last],
    )
    return Decided(kept=kept, next_start=first, next_bar=label, kept_text=_drop_last_bar_text(text))


def join(parts: list[Sheet]) -> Sheet:
    """The kept bars of every window as one bars sheet: times shifted so that each part starts where the previous
    one ends, beam and tuplet numbers made unique, clef changes kept (the first part gives the first clefs).
    """
    notes: list[Note] = []
    bars: list[Bar] = []
    changes = []
    t0 = Fraction(0)
    clefs: dict[int, str] = {}
    for i, p in enumerate(parts):
        if not p.notes:
            continue
        base = 10000 * (i + 1)
        if not clefs:
            clefs = dict(p.clefs)
        else:  # a part that starts with another clef than the one in force: a change at its start
            now = dict(clefs)
            for _, st, c in sorted(changes):
                now[st] = c
            for st, c in p.clefs.items():
                if now.get(st) != c:
                    changes.append((t0, st, c))
        start = p.bars[0].start if p.bars else min(n.time for n in p.notes)
        for n in p.notes:
            notes.append(
                replace(
                    n,
                    time=n.time - start + t0,
                    beam=n.beam + base if n.beam is not None else None,
                    tgroup=n.tgroup + base if n.tgroup is not None else None,
                )
            )
        for b in p.bars:
            bars.append(replace(b, start=b.start - start + t0))
        changes += [(t - start + t0, st, c) for t, st, c in p.clef_changes]
        t0 = (bars[-1].start + bars[-1].dur) if p.bars else max(n.time for n in notes) + 1
    return Sheet(
        notes=notes, bars=bars, clefs=clefs or {1: "G2", 2: "F4"}, clef_changes=sorted(changes)
    ).sort()


def frame_of_time(sheet: Sheet, t: Fraction) -> int | None:
    """The column of a time of a bars sheet whose notes carry frames: the first note at or after ``t``."""
    timed = sorted((n.time, n.frame) for n in sheet.notes if n.frame is not None and not n.grace)
    return next((f for tt, f in timed if tt >= t), None)


def frames_per_quarter(sheet: Sheet) -> float | None:
    """Median frames per quarter of a bars sheet with frames (from consecutive onset times)."""
    pts = sorted({(n.time, n.frame) for n in sheet.notes if n.frame is not None and not n.grace})
    r = [(f2 - f1_) / float(t2 - t1) for (t1, f1_), (t2, f2) in zip(pts, pts[1:]) if t2 > t1]
    return float(np.median(r)) if r else None


def snap(sheet: Sheet, frames: Sheet) -> Sheet:
    """The same sheet with each note moved to the matrix cell of its key in ``frames`` (the song's onset cells; nearest
    column within 2). Today's backend
    puts the notes of a chord in one column (chords grouped on raw times), while the cells of the matrix round each
    note alone, so some notes of today and of the algorithm are one column off. Each cell is used once.
    """
    free: dict[int, list[int]] = {}
    for n in frames.notes:
        free.setdefault(n.midi, []).append(n.frame)
    out = []
    for n in sorted(sheet.notes, key=lambda n: (n.frame, n.midi)):
        cands = free.get(n.midi, [])
        best = min(
            (c for c in cands if abs(c - n.frame) <= 2),
            key=lambda c: (abs(c - n.frame), c),
            default=None,
        )
        if best is None:
            out.append(n)
            continue
        cands.remove(best)
        out.append(replace(n, frame=best))
    number_grace_slots(out)  # a grace moved to another column is a grace of its own slot
    return replace(sheet, notes=out).sort()


@dataclass
class NextWindow:
    start: int  # first frame
    first_bar: int  # label of its first bar
    bar_frame: int | None  # the frame near which that bar starts (from the tempo of the kept bars)
    quarter_frames: float  # tempo and meter to cut the window
    meter: str


def next_window(
    win: NextWindow, dec: Decided | None, end: int, answer: str | None, *, last_frame: int
) -> NextWindow | None:
    """The window after ``win`` (``None``: the song is done). ``dec`` is what the accepted answer decided (``None``
    for a failed window: the next one starts at ``end``, eight bars later, without context)."""
    nxt = dec.next_start if dec is not None else end
    if nxt is None or nxt > last_frame:
        return None
    q, meter = win.quarter_frames, win.meter
    bar_frame = None
    if dec is not None and answer is not None:
        got = quarter_of(answer)
        fpq = frames_per_quarter(dec.kept)
        if fpq:
            q = fpq
        elif got:
            q = got[0]
        if dec.kept.bars:
            meter = dec.kept.bars[-1].meter or meter
            last = dec.kept.bars[-1]
            ns = [n for n in dec.kept.notes if not n.grace and n.frame is not None]
            ref = max(ns, key=lambda n: n.time) if ns else None
            if ref is not None and fpq:
                bar_frame = int(round(ref.frame + float(last.start + last.dur - ref.time) * fpq))
    return NextWindow(
        start=nxt,
        first_bar=dec.next_bar if dec else win.first_bar + 8,
        bar_frame=bar_frame,
        quarter_frames=q,
        meter=meter,
    )
