"""The passages of a song like the reference (implementation 06, Phase 1, plan section 4.1). Code, no AI.

The user selects a stretch (the reference) and asks that every other place of the song that plays the same kind of
passage be written the way the reference is written. A song made from a clean transcription repeats key for key, and
``sheet.llm.frames.like_before`` finds those repeats; a cover played by a person almost never does (another tempo, a
note more, a chord played a little earlier, a last chorus a tone higher). So this matcher compares what stays when a
person plays a passage again:

1. **The grid.** Every column of the hands compared goes on the song's grid of negras (``levels.grid.song_grid``): its
   place in negras, in bins of a semicorchea (a sixth of the negra in a ternary song). A cover a little faster or
   slower keeps its places on the grid.
2. **The features of each negra**, per hand compared (the right hand, the left, or both):
   * the **rhythm**: the bins with an onset (a bin next to it counts half: a note played a little earlier);
   * the **contour**: the steps in semitones between the columns of the hand's line (the top note of each column of
     the right hand, the lowest of the left), the same in any key;
   * the **pitch classes** of the columns;
   * the **harmony**: the notes of the chord of the song there (``levels.harmony.chords``, both hands).
   The pitch classes and the harmony are compared with each ``shift`` of ``SHIFTS`` (semitones: the passage plays
   the reference that much higher); the rhythm and the contour do not depend on it.
3. **The alignment.** The negras of the reference are aligned along the whole song (a subsequence alignment: the
   passage may start anywhere), one negra to one negra, or one negra of either side left without a partner at the
   cost ``STEP_COST`` (a bar held longer, a beat less). The score of a place is the mean of the negras' similarity
   (``WEIGHTS``), less ``SHIFT_COST`` when it is in another key.
4. **The places.** The best places of about the reference's length (``LENGTHS``, in negras) that overlap neither the
   reference nor each other, the most similar first; :func:`similar` keeps those at ``THRESHOLD`` or more, at most
   ``STYLE_MAX``. A reference of fewer than ``REF_COLUMNS`` columns or ``REF_NEGRAS`` negras finds nothing.

**The reference as played.** The user's edits take notes off the reference (an octave made a third: the note is
marked removed in ``notes.pmn``, not deleted), while the other passages still play them. So the notes marked removed
count as played, in the reference and in every passage alike: the columns are the live sheet's and the removed notes
of ``notes`` (each joins a column of its hand within ``SNAP`` frames). A note the user added cannot be told from a
played one.

The alignment also gives the **column map** of each place: each column of the reference next to the column of the
passage it matches (the same hand, the same bin of an aligned negra, or the next one). Phase 2 sends it to the AI and
copies the user's marks through it (plan sections 4.3 and 4.4).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field, replace
from typing import Iterable

import numpy as np

from aitu_backend.matrix.keys import LOWEST_MIDI
from aitu_backend.pmn.notes import HAND_LEFT, HAND_RIGHT, Notes
from aitu_backend.sheet.levels.grid import Grid, song_grid
from aitu_backend.sheet.levels.harmony import KINDS, Chord, chords
from aitu_backend.sheet.sheet.data import FRAME_MS, Sheet

__all__ = [
    "FLOOR",
    "LENGTHS",
    "REF_COLUMNS",
    "REF_NEGRAS",
    "SHIFTS",
    "SHIFT_COST",
    "STEP_COST",
    "STYLE_MAX",
    "THRESHOLD",
    "WEIGHTS",
    "Match",
    "of_places",
    "ranked",
    "similar",
]

#: The weight of each part of the similarity of two negras (they add up to 1).
WEIGHTS = {"rhythm": 0.3, "contour": 0.25, "classes": 0.2, "harmony": 0.25}
#: A place this similar or more is a similar passage.
THRESHOLD = 0.6
#: :func:`ranked` goes down to this score (the gallery shows the best places under the threshold).
FLOOR = 0.3
#: The length of a place, in negras, against the reference's: from 80 % to 125 %.
LENGTHS = (0.8, 1.25)
#: At most this many similar passages (each is one request of the run).
STYLE_MAX = 12
#: The shifts searched, in semitones (the passage = the reference this much higher); -5 to +6 holds each key once.
SHIFTS = tuple(range(-5, 7))
#: Taken off the score of a place in another key (at a tie, the same key wins).
SHIFT_COST = 0.03
#: Taken off the alignment for each negra of either side left without a partner (before the mean).
STEP_COST = 0.3
#: Frames: a removed note joins a column of its hand this near (a chord's notes are not played at once).
SNAP = 2
#: A reference holds at least this many columns of the hands compared, over this many negras (a column or two match
#: anything).
REF_COLUMNS = 4
REF_NEGRAS = 2
#: Frames of grid kept around the first and the last column.
MARGIN = 200


@dataclass
class Match:
    """A place of the song like the reference."""

    start: int  # first frame (the first column of the hands compared)
    end: int  # the frame after its last column
    score: float  # 0 to 1
    shift: int  # semitones: the passage plays the reference this much higher
    #: The mean of each part along the alignment (``WEIGHTS``' names), and ``"steps"``: the negras left without a
    #: partner.
    parts: dict[str, float] = field(default_factory=dict)
    #: The alignment: (negra of the reference, negra of the passage), as indexes of the song's negras.
    beats: list[tuple[int, int]] = field(default_factory=list)
    #: The column map: (staff, reference frame, passage frame).
    columns: list[tuple[int, int, int]] = field(default_factory=list)

    def overlaps(self, start: int, end: int) -> bool:
        return self.start < end and start < self.end


# ------------------------------------------------------------------ the columns on the grid


def _columns(
    sheet: Sheet, notes: Notes | None, staffs: Iterable[int]
) -> dict[int, dict[int, list[int]]]:
    """``staff -> frame -> midis``: the columns as played. The live sheet's notes (not the decoration notes, which a
    person plays one way one time and another the next, nor the notes inside an ornament), and the notes of
    ``notes`` marked removed, each in the column of its hand within ``SNAP`` frames (or a column of its own)."""
    cols: dict[int, dict[int, list[int]]] = {st: defaultdict(list) for st in staffs}
    for n in sheet.notes:
        if n.staff in cols and not n.covered and not n.grace and n.frame is not None:
            cols[n.staff][n.frame].append(n.midi)
    if notes is not None and len(notes) and notes.removed.any():
        gone = notes.take(notes.removed)
        for key, on, hand in zip(gone.key, gone.on_ms, gone.hand):
            midi = int(key) + LOWEST_MIDI
            staff = 1 if hand == HAND_RIGHT else 2 if hand == HAND_LEFT else (1 if midi >= 60 else 2)
            if staff not in cols:
                continue
            frame = int(np.floor(float(on) / FRAME_MS + 0.5))
            near = [f for f in range(frame - SNAP, frame + SNAP + 1) if f in cols[staff]]
            at = min(near, key=lambda f: (abs(f - frame), f)) if near else frame
            if midi not in cols[staff][at]:
                cols[staff][at].append(midi)
    return cols


@dataclass
class _Column:
    frame: int
    beat: int  # index of its negra
    bin: int  # its bin in the negra
    midis: list[int]


@dataclass
class _Hand:
    """The bins of one hand over the whole song."""

    columns: list[_Column]
    onset: np.ndarray  # (negras, bins): 1 where a column starts
    classes: np.ndarray  # (negras, bins, 12): the pitch classes of the columns
    contour: np.ndarray  # (negras, bins): the step from the line's last column, NaN where no column


class _Song:
    """The song on its grid: the negras, the bins, each hand's features, the chord of each negra."""

    def __init__(
        self,
        sheet: Sheet,
        notes: Notes | None,
        staffs: tuple[int, ...],
        grid: Grid,
        harmony: list[Chord],
    ) -> None:
        cols = _columns(sheet, notes, staffs)
        frames = [f for st in staffs for f in cols[st]] or [0]
        lo, hi = min(frames), max(frames)
        negras = np.array(grid.points(lo - MARGIN, hi + MARGIN, "negra"), dtype=float)
        if len(negras) < 2:
            step = (grid.quarter_ms or 500.0) / FRAME_MS
            negras = np.arange(lo - MARGIN, hi + MARGIN + step, step)
        self.negras = negras
        self.bins = 2 * max(grid.division, 1)
        self.staffs = staffs
        self.hands = {st: self._hand(cols[st], st) for st in staffs}
        self.frames = np.array(sorted({c.frame for h in self.hands.values() for c in h.columns}), dtype=float)
        tones = np.zeros((len(negras), 12))
        for c in harmony:
            inside = (negras >= c.start - 0.5) & (negras < c.end - 0.5)
            for i in KINDS[c.kind]:
                tones[inside, (c.root + i) % 12] = 1.0
        self.tones = tones

    def beat_of(self, frame: float) -> float:
        return float(np.interp(frame, self.negras, np.arange(len(self.negras))))

    def frame_of(self, beat: float) -> float:
        return float(np.interp(beat, np.arange(len(self.negras)), self.negras))

    def _hand(self, cols: dict[int, list[int]], staff: int) -> _Hand:
        k, r = len(self.negras), self.bins
        onset = np.zeros((k, r))
        classes = np.zeros((k, r, 12))
        contour = np.full((k, r), np.nan)
        out: list[_Column] = []
        frames = sorted(cols)
        places = np.rint(np.interp(frames, self.negras, np.arange(k)) * r).astype(int)
        line = None
        for frame, place in zip(frames, places):
            midis = sorted(cols[frame])
            beat, b = divmod(int(place), r)
            beat = min(max(beat, 0), k - 1)
            out.append(_Column(frame, beat, b, midis))
            onset[beat, b] = 1.0
            for m in midis:
                classes[beat, b, m % 12] += 1.0
            # the line: the top note of the right hand, the lowest of the left
            here = midis[0] if staff == 2 else midis[-1]
            if line is not None and np.isnan(contour[beat, b]):
                contour[beat, b] = here - line
            line = here
        return _Hand(out, onset, classes, contour)


# ------------------------------------------------------------------ the similarity of two negras


def _near(x: np.ndarray) -> np.ndarray:
    """Each bin worth 1 where ``x`` has an onset, a half next to one (in the same negra), else 0."""
    side = np.zeros_like(x)
    side[:, 1:] = np.maximum(side[:, 1:], x[:, :-1])
    side[:, :-1] = np.maximum(side[:, :-1], x[:, 1:])
    return np.maximum(x, 0.5 * side)


def _rhythm(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """(m, k): each onset of a side matched by the other side's onset in its bin (1) or the next one (a half);
    two negras with no onset are the same."""
    num = a @ _near(b).T + _near(a) @ b.T
    den = a.sum(1)[:, None] + b.sum(1)[None, :]
    return np.where(den > 0, num / np.maximum(den, 1e-9), 1.0)


def _step_score(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Two steps of a line: 1 the same, a half the same way within 2 semitones, a quarter the same way; 0 else."""
    d = np.abs(x - y)
    same = np.sign(x) == np.sign(y)
    out = np.where(d == 0, 1.0, np.where(same & (d <= 2), 0.5, np.where(same, 0.25, 0.0)))
    return np.where(np.isnan(d), 0.0, out)


def _contour(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """(m, k): each step of a side matched with the best step of the other side in its bin or the next one."""
    m, r = a.shape
    k = b.shape[0]
    best_a = np.zeros((m, k, r))
    best_b = np.zeros((m, k, r))
    for ra in range(r):
        for rb in (ra - 1, ra, ra + 1):
            if 0 <= rb < r:
                g = _step_score(a[:, ra][:, None], b[:, rb][None, :])
                best_a[:, :, ra] = np.maximum(best_a[:, :, ra], g)
                best_b[:, :, rb] = np.maximum(best_b[:, :, rb], g)
    na = (~np.isnan(a)).sum(1)[:, None]
    nb = (~np.isnan(b)).sum(1)[None, :]
    den = na + nb
    return np.where(den > 0, (best_a.sum(2) + best_b.sum(2)) / np.maximum(den, 1), 1.0)


def _classes(a: np.ndarray, b: np.ndarray, shift: int) -> np.ndarray:
    """(m, k): the cosine of the pitch classes, the reference's raised by ``shift``; two empty negras are the same,
    one empty negra is not like a full one."""
    na = np.linalg.norm(a, axis=1)
    nb = np.linalg.norm(b, axis=1)
    an = np.roll(a / np.maximum(na, 1e-9)[:, None], shift, axis=1)
    bn = b / np.maximum(nb, 1e-9)[:, None]
    out = an @ bn.T
    ea, eb = (na == 0)[:, None], (nb == 0)[None, :]
    return np.where(ea & eb, 1.0, np.where(ea | eb, 0.0, out))


def _harmony(a: np.ndarray, b: np.ndarray, shift: int) -> np.ndarray:
    """(m, k): the shared notes of the two chords over all their notes, the reference's raised by ``shift``."""
    ar = np.roll(a, shift, axis=1)
    inter = ar @ b.T
    union = a.sum(1)[:, None] + b.sum(1)[None, :] - inter
    return np.where(union > 0, inter / np.maximum(union, 1e-9), 1.0)


# ------------------------------------------------------------------ the search


@dataclass
class _Reference:
    first: int  # its first negra
    size: int  # its negras
    head: int  # the bin of its first column
    tail: int  # the bin of its last column
    start: int
    end: int


def _reference(song: _Song, start: int, end: int) -> _Reference | None:
    inside = [c for st in song.staffs for c in song.hands[st].columns if start <= c.frame < end]
    if len({c.frame for c in inside}) < REF_COLUMNS:
        return None
    a = min(inside, key=lambda c: (c.beat, c.bin))
    b = max(inside, key=lambda c: (c.beat, c.bin))
    if b.beat - a.beat + 1 < REF_NEGRAS:
        return None
    return _Reference(a.beat, b.beat - a.beat + 1, a.bin, b.bin, start, end)


def _masks(song: _Song, ref: _Reference) -> list[np.ndarray]:
    """The bins of each negra of the reference that it holds (its first and last negras only in part)."""
    out = []
    for i in range(ref.size):
        m = np.ones(song.bins, dtype=bool)
        if i == 0:
            m[: ref.head] = False
        if i == ref.size - 1:
            m[ref.tail + 1 :] = False
        out.append(m)
    return out


def _parts(song: _Song, ref: _Reference, shifts: tuple[int, ...]) -> dict[str, np.ndarray]:
    """Each part of the similarity: ``rhythm`` and ``contour`` (m, k), ``classes`` and ``harmony`` (shifts, m, k)."""
    k, m = len(song.negras), ref.size
    masks = _masks(song, ref)
    rhythm = np.zeros((m, k))
    contour = np.zeros((m, k))
    classes = np.zeros((len(shifts), m, k))
    groups: dict[bytes, list[int]] = defaultdict(list)
    for i, mask in enumerate(masks):
        groups[mask.tobytes()].append(i)
    staffs = song.staffs
    for rows in groups.values():
        mask = masks[rows[0]]
        beats = [ref.first + i for i in rows]
        for st in staffs:
            h = song.hands[st]
            on = h.onset * mask
            cl = (h.classes * mask[None, :, None]).sum(1)
            co = np.where(mask[None, :], h.contour, np.nan)
            rhythm[rows] += _rhythm(on[beats], on) / len(staffs)
            contour[rows] += _contour(co[beats], co) / len(staffs)
            for t, s in enumerate(shifts):
                classes[t][rows] += _classes(cl[beats], cl, s) / len(staffs)
    tones = song.tones[ref.first : ref.first + m]
    harmony = np.stack([_harmony(tones, song.tones, s) for s in shifts])
    return {"rhythm": rhythm, "contour": contour, "classes": classes, "harmony": harmony}


def _align(sim: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The subsequence alignment of the reference's negras (rows) along the song's (columns), for each shift: the
    total at each cell, the negra of the song where its path starts, and the step taken into it (1: one negra each,
    2: a negra of the song left alone, 3: a negra of the reference left alone)."""
    t, m, k = sim.shape
    low = -1e9
    total = np.full((t, m, k), low)
    first = np.zeros((t, m, k), dtype=np.int64)
    step = np.zeros((t, m, k), dtype=np.int8)
    total[:, 0, :] = sim[:, 0, :]
    first[:, 0, :] = np.arange(k)
    for i in range(1, m):
        options = np.full((3, t, k), low)
        starts = np.zeros((3, t, k), dtype=np.int64)
        options[0, :, 1:] = total[:, i - 1, :-1]
        starts[0, :, 1:] = first[:, i - 1, :-1]
        options[1, :, 2:] = total[:, i - 1, :-2] - STEP_COST
        starts[1, :, 2:] = first[:, i - 1, :-2]
        if i >= 2:
            options[2, :, 1:] = total[:, i - 2, :-1] - STEP_COST
            starts[2, :, 1:] = first[:, i - 2, :-1]
        pick = np.argmax(options, axis=0)
        best = np.take_along_axis(options, pick[None], 0)[0]
        total[:, i, :] = np.where(best > low / 2, best + sim[:, i, :], low)
        first[:, i, :] = np.take_along_axis(starts, pick[None], 0)[0]
        step[:, i, :] = pick + 1
    return total, first, step


def _path(step: np.ndarray, t: int, end: int) -> list[tuple[int, int]]:
    """The cells of the alignment ending at the song's negra ``end``: (row of the reference, negra of the song)."""
    i, j = step.shape[1] - 1, end
    out = [(i, j)]
    while i > 0:
        s = step[t, i, j]
        i, j = (i - 1, j - 1) if s == 1 else (i - 1, j - 2) if s == 2 else (i - 2, j - 1)
        out.append((i, j))
    return out[::-1]


def _span(song: _Song, ref: _Reference, first: int, last: int) -> tuple[int, int] | None:
    """The frames of a place whose alignment runs from the song's negra ``first`` to ``last``: from the reference's
    first bin in the first negra to its last bin in the last one (half a bin around), cut to the columns there."""
    r = song.bins
    lo = song.frame_of((first * r + ref.head - 0.5) / r)
    hi = song.frame_of((last * r + ref.tail + 0.5) / r)
    a, b = np.searchsorted(song.frames, [lo, hi])
    if b <= a:
        return None
    return int(song.frames[a]), int(song.frames[b - 1]) + 1


def _column_map(
    song: _Song, ref: _Reference, cells: list[tuple[int, int]], span: tuple[int, int], shift: int
) -> list[tuple[int, int, int]]:
    """Each column of the reference next to the passage's column in the same bin of the aligned negra, or the next
    bin (the same hand, each column once; at a tie the one with more pitch classes in common)."""
    out = []
    masks = _masks(song, ref)
    for st in song.staffs:
        by_beat: dict[int, list[_Column]] = defaultdict(list)
        for c in song.hands[st].columns:
            by_beat[c.beat].append(c)
        for i, j in cells:
            mine = [
                c
                for c in by_beat.get(ref.first + i, [])
                if masks[i][c.bin] and ref.start <= c.frame < ref.end
            ]
            theirs = [c for c in by_beat.get(j, []) if span[0] <= c.frame < span[1]]
            pairs = []
            for a in mine:
                pa = {(m + shift) % 12 for m in a.midis}
                for b in theirs:
                    d = abs(a.bin - b.bin)
                    if d <= 1:
                        pairs.append((d, -len(pa & {m % 12 for m in b.midis}), a.frame, b.frame))
            used_a: set[int] = set()
            used_b: set[int] = set()
            for _, _, fa, fb in sorted(pairs):
                if fa not in used_a and fb not in used_b:
                    used_a.add(fa)
                    used_b.add(fb)
                    out.append((st, fa, fb))
    return sorted(out)


def ranked(
    sheet: Sheet,
    notes: Notes | None,
    start: int,
    end: int,
    staffs: Iterable[int],
    *,
    grid: Grid | None = None,
    harmony: list[Chord] | None = None,
    shifts: Iterable[int] = SHIFTS,
    floor: float = FLOOR,
    limit: int | None = None,
) -> list[Match]:
    """The places of the song like the reference ``[start, end)`` of the hands ``staffs`` (1 the right hand, 2 the
    left), the most similar first, none overlapping the reference or another, down to the score ``floor``, at most
    ``limit``. ``notes``: the part's notes with the removed ones (``None``: the live sheet alone). ``grid`` and
    ``harmony``: the song's (computed when not given; the grid takes about half a second on a song of 4 minutes)."""
    staffs = tuple(sorted(set(staffs)))
    shifts = tuple(shifts)
    grid = grid if grid is not None else song_grid(sheet)
    harmony = harmony if harmony is not None else chords(sheet, grid)
    song = _Song(sheet, notes, staffs, grid, harmony)
    ref = _reference(song, start, end)
    if ref is None:
        return []
    parts = _parts(song, ref, shifts)
    w = WEIGHTS
    sim = (
        w["rhythm"] * parts["rhythm"][None]
        + w["contour"] * parts["contour"][None]
        + w["classes"] * parts["classes"]
        + w["harmony"] * parts["harmony"]
    )
    total, first, step = _align(sim)
    m = ref.size
    score = total[:, m - 1, :] / m - np.array([SHIFT_COST if s else 0.0 for s in shifts])[:, None]
    length = np.arange(score.shape[1])[None, :] - first[:, m - 1, :] + 1
    fits = (length >= LENGTHS[0] * m - 0.5) & (length <= LENGTHS[1] * m + 0.5)
    score = np.where(fits, score, -1.0)
    order = np.argsort(-score, axis=None, kind="stable")
    out: list[Match] = []
    for flat in order:
        t, j = divmod(int(flat), score.shape[1])
        value = float(score[t, j])
        if value < floor or (limit is not None and len(out) >= limit):
            break
        span = _span(song, ref, int(first[t, m - 1, j]), j)
        if span is None or (span[0] < end and start < span[1]):
            continue
        if any(o.overlaps(*span) for o in out):
            continue
        cells = _path(step, t, j)
        rows = [i for i, _ in cells]
        names = ("rhythm", "contour", "classes", "harmony")
        means = {}
        for name in names:
            grid_part = parts[name] if parts[name].ndim == 2 else parts[name][t]
            means[name] = round(float(np.mean([grid_part[i, jj] for i, jj in cells])), 3)
        means["steps"] = float((m - len(set(rows))) + (cells[-1][1] - cells[0][1] + 1 - len(cells)))
        out.append(
            Match(
                start=span[0],
                end=span[1],
                score=round(value, 3),
                shift=shifts[t],
                parts=means,
                beats=[(ref.first + i, jj) for i, jj in cells],
                columns=_column_map(song, ref, cells, span, shifts[t]),
            )
        )
    return out


def similar(
    sheet: Sheet,
    notes: Notes | None,
    start: int,
    end: int,
    staffs: Iterable[int],
    *,
    grid: Grid | None = None,
    harmony: list[Chord] | None = None,
    shifts: Iterable[int] = SHIFTS,
    threshold: float = THRESHOLD,
    limit: int = STYLE_MAX,
) -> list[Match]:
    """The similar passages of the reference ``[start, end)``: :func:`ranked` at ``threshold`` or more, at most
    ``limit``, in the order of the song."""
    found = ranked(
        sheet,
        notes,
        start,
        end,
        staffs,
        grid=grid,
        harmony=harmony,
        shifts=shifts,
        floor=threshold,
        limit=limit,
    )
    return sorted(found, key=lambda m: m.start)


def of_places(found: list[Match], places: Iterable[tuple[int, int]]) -> list[Match | None]:
    """For each place ``(start, end)`` (a passage the user ticked in the dialog, or moved by the AI's check), the
    match of ``found`` (:func:`ranked` with a low floor) that overlaps it most, cut to the place: its frames, and its
    column map inside them. ``None``: no match overlaps the place (the notes changed since the dialog asked)."""
    out: list[Match | None] = []
    for a, b in places:
        best = max(found, key=lambda m: min(m.end, b) - max(m.start, a), default=None)
        if best is None or min(best.end, b) - max(best.start, a) <= 0:
            out.append(None)
            continue
        out.append(replace(best, start=a, end=b, columns=[c for c in best.columns if a <= c[2] < b]))
    return out
