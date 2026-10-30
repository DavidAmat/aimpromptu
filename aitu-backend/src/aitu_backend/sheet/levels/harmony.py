"""The harmony of the song (implementation 04-3, Phase 3, plan sections 5.1 and 5.4): the chord of each stretch.

A level changes the way a chord is played, never the chord ("the harmony of the recording is kept"). The plan of the
song needs the chords of each passage in a few words, and the check of an answer needs to know where the harmony
changes and which bass it has there. Both come from the notes of the sheet, with no AI:

1. Each **negra** of the grid gets a weight per pitch class: every note sounding in it (from its onset to the next
   onset of its hand, at most its figure) adds the time it sounds there; the lowest note of the left hand adds
   ``BASS_WEIGHT`` more (the bass says much of the chord).
2. Each negra is matched with the **templates** (major and minor triads, the dominant seventh, the diminished
   triad, on the 12 roots): the score is the weight on the chord's notes minus ``OUTSIDE`` times the weight
   outside it, plus ``ROOT_BONUS`` when the bass is the root. A seventh or a diminished chord must win by
   ``RICH_MARGIN`` over the best triad.
3. Negras with the same chord are joined into a **stretch**; a chord shorter than ``MIN_BEATS`` negras is joined to
   the stretch before it when its score there is within ``STAY`` of its own (passing notes do not make a new chord).

Names are given with letters (``E``, ``C#m``, ``B7``, ``D#dim``), as the sheet text writes notes.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from aitu_backend.sheet.levels.grid import Grid
from aitu_backend.sheet.sheet.data import FRAME_MS, Sheet
from aitu_backend.sheet.sheet.figures import nominal_ms

__all__ = ["Chord", "chords", "pitch_name"]

BASS_WEIGHT = 1.0
OUTSIDE = 0.6
ROOT_BONUS = 0.15
RICH_MARGIN = 0.12
MIN_BEATS = 2
STAY = 0.2

_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
#: name suffix -> intervals over the root
KINDS = {"": (0, 4, 7), "m": (0, 3, 7), "7": (0, 4, 7, 10), "dim": (0, 3, 6)}


def pitch_name(pc: int, key: int = 0) -> str:
    """The letter name of a pitch class: sharps with a key of sharps (or none), flats with a key of flats."""
    return (_FLAT if key < 0 else _SHARP)[pc % 12]


@dataclass
class Chord:
    start: int  # frame of its first negra
    end: int  # frame after its last negra
    root: int  # pitch class
    kind: str  # "", "m", "7", "dim"
    bass: int | None  # pitch class of the lowest left-hand note at its start (None: no left hand there)
    score: float

    def name(self, key: int = 0) -> str:
        return pitch_name(self.root, key) + self.kind

    @property
    def tones(self) -> set[int]:
        return {(self.root + i) % 12 for i in KINDS[self.kind]}


def _score(w: np.ndarray, bass: int | None, root: int, kind: str) -> float:
    total = w.sum()
    if total <= 0:
        return 0.0
    tones = [(root + i) % 12 for i in KINDS[kind]]
    inside = w[tones].sum()
    return (inside - OUTSIDE * (total - inside)) / total + (ROOT_BONUS if bass == root else 0.0)


def _best(w: np.ndarray, bass: int | None) -> tuple[int, str, float]:
    best = {k: max(((r, _score(w, bass, r, k)) for r in range(12)), key=lambda t: t[1]) for k in KINDS}
    triad = max((best[""], ""), (best["m"], "m"), key=lambda t: t[0][1])
    out = (triad[0][0], triad[1], triad[0][1])
    for k in ("7", "dim"):
        if best[k][1] > out[2] + RICH_MARGIN:
            out = (best[k][0], k, best[k][1])
    return out


def chords(sheet: Sheet, grid: Grid, start: int | None = None, end: int | None = None) -> list[Chord]:
    """The chords of the sheet in ``[start, end)`` (the whole song by default), one per stretch of negras."""
    notes = [n for n in sheet.notes if not n.covered and n.frame is not None]
    if not notes:
        return []
    lo = min(n.frame for n in notes) if start is None else start
    hi = max(n.frame for n in notes) + 1 if end is None else end
    negras = [f for f in grid.points(lo - 1, hi + 1, "negra")]
    if not negras or negras[0] > lo:
        negras = [lo] + negras
    edges = [f for f in negras if f < hi] + [hi]
    q = grid.quarter_ms
    # each note sounds from its onset to the next onset of its hand, at most its figure
    by_hand: dict[int, list] = defaultdict(list)
    for n in notes:
        by_hand[n.staff].append(n)
    spans: list[tuple[float, float, int, int]] = []  # start, end (frames), midi, staff
    for staff, ns in by_hand.items():
        frames = sorted({n.frame for n in ns})
        nxt = {f: (frames[i + 1] if i + 1 < len(frames) else f + 50) for i, f in enumerate(frames)}
        for n in ns:
            length = nominal_ms(n.figure, q) / FRAME_MS if n.figure else nxt[n.frame] - n.frame
            spans.append((n.frame, min(n.frame + max(length, 1.0), nxt[n.frame]), n.midi, staff))
    beats: list[tuple[int, int, np.ndarray, int | None]] = []
    for a, b in zip(edges, edges[1:]):
        if b <= a:
            continue
        w = np.zeros(12)
        for s, e, m, _ in spans:
            o = min(e, b) - max(s, a)
            if o > 0:
                w[m % 12] += o
        low = [(m, s) for s, e, m, st in spans if st == 2 and a <= s < b]
        if not low:
            low = [(m, s) for s, e, m, st in spans if st == 2 and s < a < e]
        bass = min(low)[0] % 12 if low else None
        if bass is not None:
            w[bass] += BASS_WEIGHT * (b - a)
        beats.append((a, b, w, bass))
    out: list[Chord] = []
    for a, b, w, bass in beats:
        if w.sum() <= 0:
            if out:
                out[-1].end = b
            continue
        root, kind, sc = _best(w, bass)
        if out and (out[-1].root, out[-1].kind) == (root, kind):
            out[-1].end = b
            continue
        out.append(Chord(a, b, root, kind, bass, sc))
    # a short chord whose notes fit the chord before it nearly as well joins it (passing notes)
    merged: list[Chord] = []
    beat_frames = q / FRAME_MS
    for c in out:
        if merged and (c.end - c.start) < MIN_BEATS * beat_frames * 0.9:
            w = sum((bw for a, b, bw, _ in beats if c.start <= a < c.end), np.zeros(12))
            prev = merged[-1]
            if _score(w, c.bass, prev.root, prev.kind) >= c.score - STAY:
                prev.end = c.end
                continue
        if merged and (merged[-1].root, merged[-1].kind) == (c.root, c.kind):
            merged[-1].end = c.end
            continue
        merged.append(c)
    return merged
