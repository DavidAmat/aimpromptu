"""How hard a passage is to play, per hand (implementation 04-3, Phase 3, plan section 5.6).

The user's principle: difficulty is a matter of hand movement, of keeping patterns, and of how many notes each hand
plays; a hand that stays in one position, or that repeats one shape, plays many notes easily. The research measured
this with a hand tracker (``poc-aitu-research``, ``aitu_research/difficulty/hands.py``, phase 11), per compás. This
module is the same tracker on the app's frames, with the measures per second and per negra of the grid:

* **The tracker** (:func:`track`): an open hand (finger 1 to finger 5 over one octave, ``SPAN`` semitones; a wider
  chord stretches it to its own span) is placed over the notes of each column of the hand, by dynamic programming,
  so that every note is covered with the least movement: a change of placement costs its distance in semitones plus
  ``SHIFT`` (a hand prefers to stay). A **move** is a change of placement; a move inside a repeated shape (the
  intervals of the hand's top line repeat every 2 to 4 notes around it) is **regular** and counts
  ``REGULAR_WEIGHT`` of its distance in the **effort**.
* **The measures** (:func:`measure`) of one hand over a passage: notes and columns per second, notes per column
  (the most and the mean), the widest column (``span``, semitones), the widest range of the hand inside two negras
  (``reach``: the jump from a low note to its chord counts here), moves per second and per negra (``moves_q``: a
  pattern moves as often per negra at any tempo), semitones moved per second, big
  moves (more than ``BIG`` semitones) and fast moves (less than ``FAST`` seconds to get there) per second, the share
  of regular moves, the effort per second, notes per position, and the **pattern**: the share of negras whose shape
  (the places of the onsets in the negra, the intervals from the first top note, the notes per column) repeats one
  of the two negras before (the measure of the gallery's right-hand study, Phase 2 section 4.4).

A **decoration note** joins the column of the next note of its hand (it is played with it, as the research did);
an ornament onset (``orn``) is not counted.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field

import numpy as np

from aitu_backend.sheet.levels.grid import Grid
from aitu_backend.sheet.sheet.data import FRAME_MS, Note, Sheet

__all__ = [
    "BIG",
    "FAST",
    "SPAN",
    "HandTrack",
    "Measures",
    "columns",
    "measure",
    "melody",
    "track",
]

SPAN = 12  # an open hand: finger 1 to finger 5 over one octave
SHIFT = 3.0  # fixed cost of any move, in semitones (a hand prefers to stay)
FAST = 0.25  # seconds: a move with less time than this is a fast move
BIG = 7  # semitones: a move of more than a fifth is a big move
REGULAR_WEIGHT = 0.3  # a move inside a regular sequence costs 30 % of its distance
LO, HI = 21, 108
NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def name(midi: int) -> str:
    return f"{NAMES[midi % 12]}{midi // 12 - 1}"


def columns(
    sheet: Sheet, staff: int, start: int | None = None, end: int | None = None
) -> list[tuple[int, list[int]]]:
    """The columns of one hand in ``[start, end)``: ``(frame, sorted midis)``. A decoration note joins the next
    column of its hand; ornament onsets are left out."""
    notes = sorted(
        (n for n in sheet.notes if n.staff == staff and not n.covered and n.frame is not None),
        key=lambda n: n.frame,
    )
    cols: dict[int, list[int]] = defaultdict(list)
    waiting: list[int] = []
    for f in sorted({n.frame for n in notes}):
        here = [n for n in notes if n.frame == f]
        if all(n.grace for n in here):
            waiting += [n.midi for n in here]
            continue
        cols[f] += [n.midi for n in here] + waiting
        waiting = []
    return [
        (f, sorted(set(ms)))
        for f, ms in sorted(cols.items())
        if (start is None or f >= start) and (end is None or f < end)
    ]


def melody(sheet: Sheet, start: int | None = None, end: int | None = None) -> list[Note]:
    """The right hand's top line: the highest right-hand note of each column (decoration notes and ornament onsets
    apart), in ``[start, end)``."""
    top: dict[int, Note] = {}
    for n in sheet.notes:
        if n.staff != 1 or n.grace or n.covered or n.frame is None:
            continue
        if (start is not None and n.frame < start) or (end is not None and n.frame >= end):
            continue
        if n.frame not in top or n.midi > top[n.frame].midi:
            top[n.frame] = n
    return [top[f] for f in sorted(top)]


@dataclass
class HandTrack:
    times: list[float]  # column onsets (s)
    lows: list[int]  # lowest key of the hand at each column
    widths: list[int]  # span covered at each column (SPAN, or a stretched chord)
    notes: list[int]  # notes in each column
    moves: list[int] = field(default_factory=list)  # column indices where the hand moved
    regular: set[int] = field(default_factory=set)  # moves that belong to a regular sequence
    tops: list[int] = field(default_factory=list)  # top note of each column

    def dist(self, i: int) -> int:
        return abs(self.lows[i] - self.lows[i - 1])

    def effort(self) -> float:
        return sum(self.dist(i) * (REGULAR_WEIGHT if i in self.regular else 1.0) for i in self.moves)


def track(times: list[float], slices: list[list[int]], span: int = SPAN) -> HandTrack:
    """Placements of one hand for its columns (``times`` sorted, in seconds; ``slices`` the keys of each column)."""
    if not slices:
        return HandTrack([], [], [], [])
    keys = np.arange(LO, HI + 1)
    n = len(slices)
    big = 1e9
    widths = [max(span, max(s) - min(s)) for s in slices]
    feas = [(keys <= min(s)) & (keys + w >= max(s)) for s, w in zip(slices, widths)]
    cost = np.where(feas[0], 0.0, big)
    back = []
    dist = np.abs(keys[:, None] - keys[None, :]).astype(float)
    move = dist + SHIFT * (dist > 0)
    for t in range(1, n):
        tot = cost[:, None] + move  # previous key -> current key
        arg = tot.argmin(axis=0)
        cost = tot[arg, np.arange(len(keys))] + np.where(feas[t], 0.0, big)
        back.append(arg)
    j = int(cost.argmin())
    path = [j]
    for arg in reversed(back):
        j = int(arg[j])
        path.append(j)
    path.reverse()
    lows = [int(keys[j]) for j in path]
    # a lazy hand: among placements of equal cost the path may sit anywhere in the window; keep it still
    for t in range(1, n):
        lo_ok, hi_ok = max(slices[t]) - widths[t], min(slices[t])
        if lo_ok <= lows[t - 1] <= hi_ok:
            lows[t] = lows[t - 1]
    for t in range(n - 2, -1, -1):  # move as late as needed, from the end backwards
        lo_ok, hi_ok = max(slices[t]) - widths[t], min(slices[t])
        if lows[t] != lows[t + 1] and lo_ok <= lows[t + 1] <= hi_ok:
            lows[t] = lows[t + 1]
    moves = [t for t in range(1, n) if lows[t] != lows[t - 1]]
    tr = HandTrack(list(times), lows, widths, [len(s) for s in slices], moves, tops=[max(s) for s in slices])
    tr.regular = _regular(tr)
    return tr


def _regular(tr: HandTrack) -> set[int]:
    """Moves inside a repeated shape: around the move, the line of the hand's top notes has intervals that repeat
    every 2, 3 or 4 notes (within 2 semitones) for at least two periods on each side (a broken chord sliding up in
    inversions, a sequence). An arpeggio wave up and down (period 6 to 8) is not regular."""
    out: set[int] = set()
    tops = tr.tops
    for i in tr.moves:
        for p in (2, 3, 4):
            lo, hi = i - 2 * p, i + 2 * p
            if lo < 0 or hi > len(tops):
                continue
            iv = np.diff(tops[lo:hi])
            if len(iv) > p and np.all(np.abs(iv[p:] - iv[:-p]) <= 2):
                out.add(i)
                break
    return out


@dataclass
class Measures:
    """The measures of one hand over a passage (see the module's text)."""

    seconds: float = 0.0
    notes: int = 0
    columns: int = 0
    notes_s: float = 0.0
    columns_s: float = 0.0
    chord_max: int = 0
    chord_mean: float = 0.0
    span: int = 0
    reach: int = 0
    moves: int = 0
    moves_s: float = 0.0
    #: Moves per negra of the reference figure (the same pattern moves as often per negra at any tempo).
    moves_q: float = 0.0
    moved_s: float = 0.0
    big_moves_s: float = 0.0
    fast_moves_s: float = 0.0
    regular: float = 0.0
    effort_s: float = 0.0
    notes_per_position: float = 0.0
    pattern: float = 0.0

    def row(self) -> dict:
        return {k: (round(v, 2) if isinstance(v, float) else v) for k, v in asdict(self).items()}


def _reach(cols: list[tuple[int, list[int]]], frames: float) -> int:
    """The widest range (semitones) of the notes of the columns that start inside any ``frames`` long window."""
    best, j = 0, 0
    for i, (f, ms) in enumerate(cols):
        while cols[j][0] <= f - frames:
            j += 1
        lo = min(min(m) for _, m in cols[j : i + 1])
        hi = max(max(m) for _, m in cols[j : i + 1])
        best = max(best, hi - lo)
    return best


def _pattern(cols: list[tuple[int, list[int]]], grid: Grid | None, quarter_ms: float) -> float:
    """The share of negras (with two columns or more) whose shape repeats one of the two negras before: the places
    of the onsets in the negra (in semicorcheas of the grid), the top notes from the first one, the notes per
    column."""
    if len(cols) < 2:
        return 0.0
    shapes: dict[int, list[tuple]] = defaultdict(list)
    for f, ms in cols:
        b = grid.beat_of(f) if grid is not None else f * FRAME_MS / quarter_ms
        i = int(np.floor(b + 0.05))
        shapes[i].append((round((b - i) * 4), max(ms), len(ms)))
    sh = []
    for i in sorted(shapes):
        ev = shapes[i]
        if len(ev) < 2:
            continue
        sh.append(tuple((o, top - ev[0][1], s) for o, top, s in ev))
    if len(sh) < 2:
        return 0.0
    rep = sum(1 for j in range(1, len(sh)) if sh[j] == sh[j - 1] or (j > 1 and sh[j] == sh[j - 2]))
    return rep / (len(sh) - 1)


def measure(
    sheet: Sheet,
    staff: int,
    start: int | None = None,
    end: int | None = None,
    grid: Grid | None = None,
) -> Measures:
    """The measures of one hand of ``sheet`` in ``[start, end)``. The seconds are the passage's (``end - start``) when
    both are given, else from the hand's first to its last column (1 s at least). ``grid`` places the negras of the
    pattern measure (without it, negras of the sheet's reference figure from frame 0)."""
    cols = columns(sheet, staff, start, end)
    q = (grid.quarter_ms if grid is not None else None) or sheet.quarter_ms or 500.0
    if start is not None and end is not None:
        seconds = max((end - start) * FRAME_MS / 1000.0, 1.0)
    elif cols:
        seconds = max((cols[-1][0] - cols[0][0]) * FRAME_MS / 1000.0, 1.0)
    else:
        seconds = 1.0
    m = Measures(seconds=round(seconds, 2))
    if not cols:
        return m
    tr = track([f * FRAME_MS / 1000.0 for f, _ in cols], [ms for _, ms in cols])
    sizes = [len(ms) for _, ms in cols]
    gaps = [tr.times[t] - tr.times[t - 1] for t in tr.moves]
    dists = [tr.dist(t) for t in tr.moves]
    m.notes, m.columns = sum(sizes), len(cols)
    m.notes_s, m.columns_s = m.notes / seconds, m.columns / seconds
    m.chord_max, m.chord_mean = max(sizes), float(np.mean(sizes))
    m.span = max(max(ms) - min(ms) for _, ms in cols)
    m.reach = _reach(cols, 2 * q / FRAME_MS)
    m.moves = len(tr.moves)
    m.moves_s = m.moves / seconds
    m.moves_q = m.moves / (seconds * 1000.0 / q)
    m.moved_s = sum(dists) / seconds
    m.big_moves_s = sum(d > BIG for d in dists) / seconds
    m.fast_moves_s = sum(g < FAST for g in gaps) / seconds
    m.regular = len(tr.regular) / max(len(tr.moves), 1)
    m.effort_s = tr.effort() / seconds
    m.notes_per_position = m.notes / (m.moves + 1)
    m.pattern = _pattern(cols, grid, q)
    return m


def place_line(sheet: Sheet, staff: int, start: int, end: int, *, most: int = 6) -> str:
    """Where the hand is over ``[start, end)``, for a prompt: the placements of the tracker in order
    (``E2-E3 > A2-A3``), at most ``most``."""
    cols = columns(sheet, staff, start, end)
    if not cols:
        return "no notes"
    tr = track([f * FRAME_MS / 1000.0 for f, _ in cols], [ms for _, ms in cols])
    places: list[str] = []
    for lo, w in zip(tr.lows, tr.widths):
        p = f"{name(lo)}-{name(lo + w)}"
        if not places or places[-1] != p:
            places.append(p)
    return " > ".join(places[:most]) + (" > ..." if len(places) > most else "")
