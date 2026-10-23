"""The algorithm of the new sheet: notes with hands -> F1 frames sheet, no compases, no LLM (implementation 03, Phase 2).

The product path when the LLM has not run, and the fallback of the LLM step. Every note is drawn at the column of
its chord (:func:`aitu_backend.sheet.sheet.frames.from_notes`); then, per hand:

1. **Reference figure**: one negra lasts ``quarter_ms``, the pulse estimate of the bars algorithm (``beat.estimate``)
   unless it is given (the LLM's choice, or the user's "transpose figures").
2. **Figures** (plan section 3.3): a note's own length, but not past the next onset of its hand (Phase 2 measured the
   lengths under the pedal: without this cap 37 % of the notes of a run of even gaps changed figure inside the run),
   as the nearest plain figure (:func:`figures.figure_of_ms`); one figure per chord, the one most of its notes have
   (ties: the longer); and one figure per run of three or more even gaps, the one most of the run has.
3. **Grace notes**: one or two notes, each two figures or more shorter than the note after them, played as quickly
   and at most ``GRACE_MS`` before the next onset of the hand, become grace notes of that note (a longer run of such
   notes stays written). A note with the name of a note of the main chord is an octave played unevenly or a repeated
   note, not a grace note.
4. **Beam groups** (plan section 3.11, the simple rules): consecutive corcheas or shorter of one hand, not farther
   apart than a corchea; cut at a jump of more than an octave, where the direction turns after a run of three steps,
   and into near-equal parts of at most 8.
5. **Armadura** of each passage: the armadura that prints the fewest signs, with a cost for each change
   (:func:`choose_keys`), unless the armadura is given; then every note is spelled by the user's rules
   (:mod:`aitu_backend.sheet.sheet.spelling`).
6. **Clefs and 8va** (the left-hand rules of the frozen prompt, version 4): fewest ledger lines with a cost for each
   change; the left hand prefers the bass clef, then the treble clef, then the treble clef with 8va, and never stays
   in the bass clef four ledger lines or more above the staff; the right hand prefers the treble clef, then 8va,
   then the bass clef.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

import numpy as np

from aitu_backend.pmn.notes import Notes
from aitu_backend.sheet.proposal import beat
from aitu_backend.sheet.sheet import frames as frames_mod
from aitu_backend.sheet.sheet.data import Note, Sheet
from aitu_backend.sheet.sheet.figures import SPLIT, figure_of_ms
from aitu_backend.sheet.sheet.pitch import STEPS
from aitu_backend.sheet.sheet.spelling import sign, spell, spell_pc

__all__ = [
    "FramesProposal",
    "assign_figures",
    "beam_groups",
    "choose_keys",
    "clefs_and_ottavas",
    "find_graces",
    "propose_frames",
    "respell",
]

RUN_TOLERANCE = 0.12  # gaps within 12 % of the run's first gap are even
RUN_MIN = 3  # columns
MAX_GRACES = 2
GRACE_MS = (
    100.0  # a grace note is played quickly: at most this long before the next onset of its hand
)
JUMP = 12  # semitones: a beam is cut at a jump of more than an octave
TURN_RUN = 3  # steps in one direction before a turn cuts the beam
KEY_SWITCH = 12.0  # signs: the cost of one armadura change
KEY_STAY = 48  # columns (both hands) at least between two armadura changes
KEY_SIGN_COST = 0.01  # per column and per sign of the armadura (printed on every line): breaks ties
CLEF_SWITCH = 3.0  # ledger lines: the cost of one clef or 8va change (clef.L6)
CLEF_IN_BEAM = 3.0  # more for a change inside a beam group
CLEF_PREFER = 0.25  # per column, for the second clef of a hand
OTTAVA_COST = (
    2.5  # per column under an 8va line: E6 alone (3 ledger lines) rarely pays it, G6 does (clef.6)
)
BASS_LIMIT = 4  # ledger lines above the bass staff that the left hand never reads (clef.L3)


@dataclass
class FramesProposal:
    sheet: Sheet  # frames sheet: hands, figures, graces, beams, armaduras, spelling, clefs, 8va
    quarter_ms: float
    info: dict = field(default_factory=dict)


def _columns(sheet: Sheet, staff: int, *, graces: bool = True) -> list[tuple[int, list[Note]]]:
    cols: dict[int, list[Note]] = defaultdict(list)
    for n in sheet.notes:
        if n.staff == staff and not n.covered and (graces or not n.grace):
            cols[n.frame].append(n)
    return sorted(cols.items())


def _mode(figs: list[int]) -> int:
    c = Counter(figs)
    return min(c, key=lambda f: (-c[f], f))  # most common, ties: the longer figure


def assign_figures(
    sheet: Sheet, quarter_ms: float, split: float = SPLIT, *, cap: bool = True
) -> None:
    """Step 2: the figure of every note from its measured length (``Note.len_ms``) and onset (``Note.on_ms``).
    ``cap=False`` takes the raw length (the gallery's comparison)."""
    for staff in (1, 2):
        cols = _columns(sheet, staff)
        starts = [ns[0].on_ms for _, ns in cols]
        gaps = [b - a for a, b in zip(starts, starts[1:])] + [None]
        figs = []
        for (_, ns), gap in zip(cols, gaps):
            figs.append(
                _mode(
                    [
                        figure_of_ms(
                            n.len_ms if gap is None or not cap else min(n.len_ms, gap),
                            quarter_ms,
                            split,
                        )
                        for n in ns
                    ]
                )
            )
        i = 0
        while i < len(cols) - 1:  # runs of even gaps share one figure
            j = i
            while (
                j + 1 < len(cols)
                and gaps[j + 1] is not None
                and abs(gaps[j + 1] - gaps[i]) <= RUN_TOLERANCE * gaps[i]
            ):
                j += 1
            if gaps[i] is not None and j - i + 1 >= RUN_MIN:
                figs[i : j + 1] = [_mode(figs[i : j + 1])] * (j - i + 1)
                i = j + 1
            else:
                i += 1
        for (_, ns), fig in zip(cols, figs):
            for n in ns:
                n.figure, n.dots, n.tuplet, n.tgroup = fig, 0, None, None


def find_graces(
    sheet: Sheet, quarter_ms: float, split: float = SPLIT, grace_ms: float = GRACE_MS
) -> int:
    """Step 3: grace notes by the two-step rule (plan section 3.3). Returns how many columns became grace notes."""
    count = 0
    for staff in (1, 2):
        cols = _columns(sheet, staff)
        starts = [ns[0].on_ms for _, ns in cols]
        fig = [ns[0].figure for _, ns in cols]
        k = 1
        while k < len(cols):
            main = fig[k]
            names = {n.midi % 12 for n in cols[k][1]}
            chain = []
            j = k - 1
            while j >= 0 and fig[j] >= 4 * main and not cols[j][1][0].grace:
                gap = starts[j + 1] - starts[j]
                if gap > grace_ms or figure_of_ms(gap, quarter_ms, split) < 4 * main:
                    break
                if names & {
                    n.midi % 12 for n in cols[j][1]
                }:  # an octave or a repeated note, not a grace
                    break
                chain.append(j)
                j -= 1
            if 1 <= len(chain) <= MAX_GRACES:
                for j in chain:
                    for n in cols[j][1]:
                        n.grace = "acc" if len(chain) == 1 else "unacc"
                        n.figure = 8 if len(chain) == 1 else 16
                        n.gslot = 0
                count += len(chain)
            k += 1
    return count


def _outer(ns: list[Note], staff: int) -> int:
    return max(n.midi for n in ns) if staff == 1 else min(n.midi for n in ns)


def _split(chain: list[int], pitch: list[int], why: Counter) -> list[list[int]]:
    """Cut one chain of beamable columns: jumps, turns after a run, then parts of at most ``MAX_BEAM``. ``why``
    counts the cuts by reason."""
    parts, cur = [], [chain[0]]
    run_dir, run_len = 0, 0
    for a, b in zip(chain, chain[1:]):
        step = pitch[b] - pitch[a]
        d = (step > 0) - (step < 0)
        jump = abs(step) > JUMP
        turn = d != 0 and run_dir != 0 and d != run_dir and run_len >= TURN_RUN
        if jump or turn:
            why["cut at a jump" if jump else "cut at a turn"] += 1
            parts.append(cur)
            cur = [b]
            run_dir, run_len = 0, 0
            continue
        cur.append(b)
        if d != 0:
            run_len = run_len + 1 if d == run_dir else 1
            run_dir = d
    parts.append(cur)
    out = []
    for p in parts:
        k = -(-len(p) // frames_mod.MAX_BEAM)
        size = -(-len(p) // k)
        out += [p[i : i + size] for i in range(0, len(p), size)]
        why["cut at 8"] += k - 1
    return out


def beam_groups(sheet: Sheet, quarter_ms: float, split: float = SPLIT) -> dict:
    """Step 4: beam groups by the simple rules of plan section 3.11. Returns the counts (groups, cuts by reason)."""
    for n in sheet.notes:
        n.beam = None
    counter = 0
    why: Counter = Counter()
    for staff in (1, 2):
        cols = _columns(sheet, staff, graces=False)
        starts = [ns[0].on_ms for _, ns in cols]
        pitch = [_outer(ns, staff) for _, ns in cols]
        chains, cur = [], []
        for i, (_, ns) in enumerate(cols):
            beamable = ns[0].figure >= 8
            joined = (
                cur
                and beamable
                and figure_of_ms(starts[i] - starts[cur[-1]], quarter_ms, split) >= 8
            )
            if joined:
                cur.append(i)
                continue
            if len(cur) > 1:
                chains.append(cur)
            cur = [i] if beamable else []
        if len(cur) > 1:
            chains.append(cur)
        for chain in chains:
            for part in _split(chain, pitch, why):
                if len(part) < 2:
                    continue
                counter += 1
                for i in part:
                    for n in cols[i][1]:
                        n.beam = counter
    return {"beam groups": counter, **why}


# ------------------------------------------------------------------ the shortest path with a minimum stay


def _path(
    cost: np.ndarray,
    switch: float,
    stay: int,
    *,
    start: np.ndarray | None = None,
    extra: np.ndarray | None = None,
) -> np.ndarray:
    """The state of each column that minimises the summed ``cost`` (columns x states) plus ``switch`` per change
    (``extra[i]`` more for a change into column ``i``); two changes are at least ``stay`` columns apart. ``start`` is
    the cost of each first state."""
    n, s = cost.shape
    m = max(1, stay)
    best = np.full((s, m), np.inf)
    best[:, m - 1] = cost[0] + (0 if start is None else start)
    back = np.zeros((n, s, m, 2), dtype=np.int32)  # previous (state, counter)
    for i in range(1, n):
        new = np.full((s, m), np.inf)
        bk = np.zeros((s, m, 2), dtype=np.int32)
        # stay: counter + 1, capped
        if m > 1:
            new[:, 1:] = best[:, :-1]
            bk[:, 1:, 0] = np.arange(s)[:, None]
            bk[:, 1:, 1] = np.arange(m - 1)[None, :]
        hold = best[:, m - 1] <= new[:, m - 1]
        new[hold, m - 1] = best[hold, m - 1]
        bk[hold, m - 1, 0] = np.flatnonzero(hold)
        bk[hold, m - 1, 1] = m - 1
        # change: from another state at the cap, into counter 0
        cap = best[:, m - 1]
        order = np.argsort(cap)
        first, second = order[0], order[1] if s > 1 else order[0]
        src = np.where(np.arange(s) == first, second, first)
        change = cap[src] + switch + (0 if extra is None else extra[i])
        better = change < new[:, 0]
        new[better, 0] = change[better]
        bk[better, 0, 0] = src[better]
        bk[better, 0, 1] = m - 1
        best = new + cost[i][:, None]
        back[i] = bk
    st, k = (int(x) for x in np.unravel_index(np.argmin(best), best.shape))
    out = np.zeros(n, dtype=np.int64)
    for i in range(n - 1, -1, -1):
        out[i] = st
        st, k = (int(x) for x in back[i, st, k]) if i else (st, k)
    return out


# ------------------------------------------------------------------ armadura and spelling

KEYS = np.arange(-7, 8)
_SIGNS = np.array(
    [[sign(*spell_pc(pc, int(k)), int(k)) is not None for pc in range(12)] for k in KEYS]
)


def choose_keys(sheet: Sheet) -> tuple[int, list[tuple[int, int]], dict]:
    """Step 5: the armadura of each passage, fewest signs printed (rule 6 of plan section 3.4). Returns the first
    armadura, the changes (column, armadura) and the counts."""
    cols: dict[int, list[int]] = defaultdict(list)
    for n in sheet.notes:
        if not n.covered:
            cols[n.frame].append(n.midi % 12)
    frames = sorted(cols)
    if not frames:
        return 0, [], {}
    counts = np.zeros((len(frames), 12))
    for i, f in enumerate(frames):
        for pc in cols[f]:
            counts[i, pc] += 1
    cost = counts @ _SIGNS.T.astype(float) + KEY_SIGN_COST * np.abs(KEYS)[None, :]
    cost += 1e-6 * (KEYS < 0)[None, :]  # a tie between two names of one armadura: the sostenidos
    path = _path(cost, KEY_SWITCH, KEY_STAY)
    keys = [int(KEYS[s]) for s in path]
    changes = [(frames[i], keys[i]) for i in range(1, len(keys)) if keys[i] != keys[i - 1]]
    signs = int(sum(counts[i] @ _SIGNS[path[i]] for i in range(len(frames))))
    return keys[0], changes, {"signs": signs, "key changes": len(changes)}


def respell(sheet: Sheet) -> None:
    """Every note by the spelling rules, in the armadura in force at its column."""
    at = frames_mod.key_at(sheet)
    for n in sheet.notes:
        n.step, n.alter, n.octave = spell(n.midi, at(n.frame))


# ------------------------------------------------------------------ clefs and 8va

_LINES = {
    "G2": (4 * 7 + 2, 5 * 7 + 3),
    "F4": (2 * 7 + 4, 3 * 7 + 5),
}  # E4..F5, G2..A3 (diatonic index)
#: (clef, ottava, cost per column) of each state; the first one is the hand's own clef
STATES = {
    1: [("G2", 0, 0.0), ("G2", 1, OTTAVA_COST), ("F4", 0, CLEF_PREFER)],
    2: [("F4", 0, 0.0), ("G2", 0, CLEF_PREFER), ("G2", 1, CLEF_PREFER + OTTAVA_COST)],
}


def _ledger(n: Note, clef: str, ottava: int) -> tuple[int, int]:
    """Ledger lines (below, above) of a note written ``ottava`` octaves lower than it sounds."""
    d = (n.octave - ottava) * 7 + STEPS.index(n.step)
    low, high = _LINES[clef]
    return max(0, (low - d) // 2), max(0, (d - high) // 2)


def clefs_and_ottavas(sheet: Sheet) -> dict:
    """Step 6: clef changes and 8va of each hand. Returns the counts."""
    sheet.clefs = {1: "G2", 2: "F4"}
    sheet.clef_changes = []
    for n in sheet.notes:
        n.ottava = 0
    info = {"clef changes": 0, "8va notes": 0}
    for staff in (1, 2):
        cols = _columns(sheet, staff)
        if not cols:
            continue
        states = STATES[staff]
        cost = np.zeros((len(cols), len(states)))
        extra = np.zeros(len(cols))
        seen: set[int] = set()
        for i, (_, ns) in enumerate(cols):
            for s, (clef, ottava, penalty) in enumerate(states):
                below_above = [_ledger(n, clef, ottava) for n in ns]
                c = sum(a + b for a, b in below_above) + penalty
                if staff == 2 and clef == "F4" and max(b for _, b in below_above) >= BASS_LIMIT:
                    c = np.inf
                cost[i, s] = c
            beams = {n.beam for n in ns if n.beam is not None}
            if beams & seen:
                extra[i] = CLEF_IN_BEAM
            seen |= beams
        start = np.array([0.0] + [CLEF_SWITCH] * (len(states) - 1))
        path = _path(cost, CLEF_SWITCH, 1, start=start, extra=extra)
        prev_clef = None
        for i, (f, ns) in enumerate(cols):
            clef, ottava, _ = states[path[i]]
            if i == 0:
                sheet.clefs[staff] = clef
            elif clef != prev_clef:
                sheet.clef_changes.append((f, staff, clef))
                info["clef changes"] += 1
            prev_clef = clef
            for n in ns:
                n.ottava = ottava
            info["8va notes"] += len(ns) if ottava else 0
        # ornament onsets take the 8va of the note before them
        last = 0
        for n in sorted((n for n in sheet.notes if n.staff == staff), key=lambda n: n.frame):
            if n.covered:
                n.ottava = last
            else:
                last = n.ottava
    sheet.clef_changes.sort(key=lambda c: (c[0], c[1]))
    return info


# ------------------------------------------------------------------ the whole algorithm


def propose_frames(
    notes: Notes,
    *,
    key: int | None = None,
    key_changes: list[tuple[int, int]] | None = None,
    quarter_ms: float | None = None,
    split: float = SPLIT,
) -> FramesProposal:
    """The new sheet of a part. ``notes`` carry the starting hands (the saved hands and the hand split; a note with
    no hand gets one by middle C). ``key`` (and ``key_changes``) fixes the armadura; without it the algorithm chooses
    the armadura of each passage. ``quarter_ms`` fixes the reference figure."""
    sheet = frames_mod.from_notes(notes)
    info: dict = {}
    if quarter_ms is None:
        cols = np.array([n.frame for n in sheet.notes])
        midi = np.array([n.midi for n in sheet.notes])
        quarter_ms = float(beat.estimate(cols, midi)[0][0])
    sheet.quarter_ms = float(quarter_ms)
    assign_figures(sheet, quarter_ms, split)
    info["grace columns"] = find_graces(sheet, quarter_ms, split)
    info.update(beam_groups(sheet, quarter_ms, split))
    if key is None:
        sheet.key, sheet.key_changes, kinfo = choose_keys(sheet)
        info.update(kinfo)
    else:
        sheet.key, sheet.key_changes = key, sorted(key_changes or [])
    respell(sheet)
    info.update(clefs_and_ottavas(sheet))
    return FramesProposal(sheet=sheet.sort(), quarter_ms=float(quarter_ms), info=info)
