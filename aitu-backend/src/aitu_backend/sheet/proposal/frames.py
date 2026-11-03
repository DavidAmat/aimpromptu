"""The algorithm of the new sheet: notes with hands -> F1 frames sheet, no compases, no LLM (implementation 03, Phase 2).

The product path when the LLM has not run, and the fallback of the LLM step. Every note is drawn at the column of
its chord (:func:`aitu_backend.sheet.sheet.frames.from_notes`); then, per hand:

1. **Reference figure**: one negra lasts ``quarter_ms``, the pulse estimate of the bars algorithm (``beat.estimate``)
   unless it is given (the LLM's choice, or the user's "transpose figures").
2. **Figures** (plan section 3.3): a note's own length, but not past the next onset of its hand (Phase 2 measured the
   lengths under the pedal: without this cap 37 % of the notes of a run of even gaps changed figure inside the run),
   as the nearest plain figure (:func:`figures.figure_of_ms`); one figure per chord, the one most of its notes have
   (ties: the longer); and one figure per run of three or more even gaps, the one most of the run has.
3. **Grace notes** (implementation 04, Phase 2: the user's rule): one or two fusas or shorter, each two figures or
   more shorter than the note after them and sounding just before it (the gap is shorter than the main note's
   figure), become acciaccaturas of that note; a run of three or more semicorcheas or shorter stays written. An
   octave played unevenly or a quick repeated note is an acciaccatura too. **Lone short notes**: one or two notes
   more than two figures shorter than the note after them, sounding just before it and not grace notes, are written
   two figures shorter than that note (a semicorchea before a blanca is a corchea); the last note of a longer run
   keeps its figure.
4. **Beam groups** (plan section 3.11, the simple rules): consecutive corcheas or shorter of one hand, not farther
   apart than a corchea, of one figure (a single note one figure away may open or close a group); cut at a jump of
   more than an octave, where the direction turns after a run of three steps, and into near-equal parts of at most 8.
5. **Armadura** of each passage: the armadura that prints the fewest signs, with a cost for each change
   (:func:`choose_keys`), unless the armadura is given; then every note is spelled by the user's rules
   (:mod:`aitu_backend.sheet.sheet.spelling`).
6. **Clefs and 8va** (the left-hand rules of the frozen prompt, version 4, and the user's rule of implementation
   04-7): fewest ledger lines with a cost for each change; the left hand prefers the bass clef, then the treble clef,
   then the bass clef under 8va or the treble clef with 8va, and never reads a note four ledger lines or more above
   the bass staff; the right hand prefers the treble clef, then 8va, then the bass clef or the treble clef under
   8vb, and never reads a note four ledger lines or more below the treble staff without a line. Then **the shortest
   stretch** (:func:`short_clefs`, the user, 2026-11-03): a hand changes to its other clef only for a whole passage,
   ``CLEF_MIN`` of its columns or more; a shorter stretch goes back to the hand's own clef, with ledger lines, and an
   octave line (left 8va, right 8vb) for the notes too far for them. A clef the user set by hand stays.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

import numpy as np

from aitu_backend.pmn.notes import Notes
from aitu_backend.sheet.proposal import beat
from aitu_backend.sheet.sheet import frames as frames_mod
from aitu_backend.sheet.sheet.data import Note, Sheet
from aitu_backend.sheet.sheet.figures import FIGURES, SPLIT, figure_of_ms, steps
from aitu_backend.sheet.sheet.pitch import STEPS
from aitu_backend.sheet.sheet.spelling import sign, spell, spell_pc

__all__ = [
    "FramesProposal",
    "assign_figures",
    "beam_groups",
    "choose_keys",
    "clefs_and_ottavas",
    "find_graces",
    "lengthen_lone",
    "propose_frames",
    "respell",
    "short_clefs",
]

RUN_TOLERANCE = 0.12  # gaps within 12 % of the run's first gap are even
RUN_MIN = 3  # columns
MAX_GRACES = 2
RUN_FIGURE = 16  # the notes of a quick run before a note: semicorcheas or shorter
GRACE_FIGURE = 32  # a grace note is a fusa or shorter (implementation 04, Phase 2)
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
BASS_LIMIT = 4  # ledger lines above the bass staff that the left hand never reads (clef.L3); below the treble staff
#: for the right hand without an octave line (04-7)
CLEF_MIN = 5  # columns of a hand: a stretch of its other clef shorter than this goes back to its own clef (04-7)
READABLE = 1  # ledger lines on the far side of an octave line: the notes between two marked columns that may join it


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
    ``cap=False`` takes the raw length (the gallery's comparison). A chord whose figure the user set (``fix``,
    implementation 03, Phase 7) keeps it: rule 5 of the time model, the reader's answer beats the rule.
    """
    for staff in (1, 2):
        cols = _columns(sheet, staff)
        fixed = [
            next((n.figure for n in ns if n.fixed and n.figure in FIGURES), None) for _, ns in cols
        ]
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
        figs = [own if own is not None else fig for own, fig in zip(fixed, figs)]
        for (_, ns), fig in zip(cols, figs):
            for n in ns:
                n.figure, n.dots, n.tuplet, n.tgroup = fig, 0, None, None


def find_graces(sheet: Sheet, quarter_ms: float, split: float = SPLIT) -> int:
    """Step 3: grace notes by the two-step rule (plan section 3.3; the user, Phase 2 review), only for fusas or
    shorter (implementation 04, Phase 2). The user's switch (implementation 03, Phase 7) wins: a column marked
    ``asgrace`` is a grace note of the next note of its hand whatever its figure, one marked ``nograce`` or with a
    figure the user set (``fix``) never is. Returns how many columns became grace notes."""
    count = 0
    for staff in (1, 2):
        cols = _columns(sheet, staff)
        starts = [ns[0].on_ms for _, ns in cols]
        fig = [ns[0].figure for _, ns in cols]
        never = [any(n.fixed or n.grace_rule == "off" for n in ns) for _, ns in cols]
        forced = [
            not never[i] and any(n.grace_rule == "on" for n in ns) for i, (_, ns) in enumerate(cols)
        ]
        k = 1
        while k < len(cols):
            if forced[k]:  # a grace note is never the main note of another one
                k += 1
                continue
            main = fig[k]
            chain = []
            j = k - 1
            while j >= 0 and not cols[j][1][0].grace:
                if forced[j]:
                    chain.append(j)
                    j -= 1
                    continue
                if never[j] or fig[j] < max(RUN_FIGURE, 4 * main):
                    break
                # it sounds just before the next note: the gap is shorter than the main note's figure
                if figure_of_ms(starts[j + 1] - starts[j], quarter_ms, split) <= main:
                    break
                chain.append(j)
                j -= 1
            quick = len(chain) <= MAX_GRACES and all(fig[j] >= GRACE_FIGURE for j in chain)
            if chain and (quick or any(forced[j] for j in chain)):
                for j in chain:
                    for n in cols[j][1]:
                        n.grace = "acc" if len(chain) == 1 else "unacc"
                        n.figure = 8 if len(chain) == 1 else 16
                        n.gslot = 0
                count += len(chain)
            k += 1
    return count


def lengthen_lone(
    sheet: Sheet,
    quarter_ms: float,
    split: float = SPLIT,
    *,
    pairs: list[tuple[list[Note], list[Note]]] | None = None,
) -> int:
    """Step 3, after :func:`find_graces` (implementation 04, Phase 2; the user's rule): one or two notes more than two
    figures shorter than the note after them, sounding just before it (as for a grace note), are written two figures
    shorter than that note: a semicorchea before a blanca is a corchea, a semicorchea or a corchea before a redonda a
    negra. The sheet has no compases, so the space between the notes already shows how quick they are; a grace note
    is for quick ornaments only. A run of three or more stays as it is, its last note too, so its beam group stays
    whole. A figure the user set (``fix``) is never changed. Returns how many columns were lengthened; ``pairs``
    gets the notes of each two such columns before one note, in order (the AI's sheet beams them together,
    :func:`aitu_backend.sheet.llm.frames.beam_pairs`)."""
    count = 0
    for staff in (1, 2):
        cols = _columns(sheet, staff)
        starts = [ns[0].on_ms for _, ns in cols]
        fig = [ns[0].figure for _, ns in cols]
        grace = [ns[0].grace is not None for _, ns in cols]
        fixed = [any(n.fixed for n in ns) for _, ns in cols]

        def before(k: int, short: int) -> list[int]:
            """The columns just before column ``k`` with a figure of ``short`` or shorter, each sounding before the
            next one by less than the figure of column ``k``."""
            chain = []
            j = k - 1
            while j >= 0 and not grace[j] and not fixed[j] and fig[j] >= short:
                if figure_of_ms(starts[j + 1] - starts[j], quarter_ms, split) <= fig[k]:
                    break
                chain.append(j)
                j -= 1
            return chain

        for k in range(1, len(cols)):
            if grace[k]:
                continue
            longest = 4 * fig[k]  # two figures shorter than the note
            chain = before(k, 2 * longest)
            # the end of a quick run (semicorcheas or shorter, as for the grace notes) is not a lone note
            run = before(k, max(RUN_FIGURE, longest))
            if len(chain) > MAX_GRACES or len(run) > MAX_GRACES:
                continue
            two = run if len(run) == 2 else chain if len(chain) == 2 else []
            if two and pairs is not None:
                pairs.append((cols[two[1]][1], cols[two[0]][1]))
            for j in chain:
                for n in cols[j][1]:
                    n.figure = longest
                fig[j] = longest
            count += len(chain)
    return count


def _outer(ns: list[Note], staff: int) -> int:
    return max(n.midi for n in ns) if staff == 1 else min(n.midi for n in ns)


def _split(chain: list[int], pitch: list[int], why: Counter) -> list[list[int]]:
    """Cut one chain of beamable columns: jumps, turns after a run, then near-equal parts of at most ``MAX_BEAM``.
    Only a jump may leave a note alone: a note that a turn would leave alone stays with the group before it (or after
    it). ``why`` counts the cuts by reason."""
    parts, cur = [], [chain[0]]
    cut_by: list[str] = []  # the reason of the cut before each part after the first
    run_dir, run_len = 0, 0
    for a, b in zip(chain, chain[1:]):
        step = pitch[b] - pitch[a]
        d = (step > 0) - (step < 0)
        jump = abs(step) > JUMP
        turn = d != 0 and run_dir != 0 and d != run_dir and run_len >= TURN_RUN
        if jump or turn:
            parts.append(cur)
            cut_by.append("jump" if jump else "turn")
            cur = [b]
            run_dir, run_len = 0, 0
            continue
        cur.append(b)
        if d != 0:
            run_len = run_len + 1 if d == run_dir else 1
            run_dir = d
    parts.append(cur)
    i = 0
    while i < len(parts):  # a lone note after or before a turn joins its neighbour
        if len(parts[i]) == 1 and i > 0 and cut_by[i - 1] == "turn":
            parts[i - 1] += parts.pop(i)
            cut_by.pop(i - 1)
            continue
        if len(parts[i]) == 1 and i + 1 < len(parts) and cut_by[i] == "turn":
            parts[i] += parts.pop(i + 1)
            cut_by.pop(i)
            continue
        i += 1
    for reason in cut_by:
        why["cut at a jump" if reason == "jump" else "cut at a turn"] += 1
    out = []
    for p in parts:
        k = -(-len(p) // frames_mod.MAX_BEAM)
        sizes = [len(p) // k + (1 if j < len(p) % k else 0) for j in range(k)]
        at = 0
        for size in sizes:
            out.append(p[at : at + size])
            at += size
        why["cut at 8"] += k - 1
    return out


def _uniform(chain: list[int], fig: list[int], why: Counter) -> list[list[int]]:
    """Cut a chain into groups of one figure (the user, Phase 2 review). A single note one figure away may close a
    group or open the next one when the group has two notes or more of its own figure, never sit inside it, so a
    group never holds two sub-groups of another figure."""
    runs: list[list[int]] = []
    for i in chain:
        if runs and fig[runs[-1][0]] == fig[i]:
            runs[-1].append(i)
        else:
            runs.append([i])
    groups: list[tuple[list[int], int, bool]] = (
        []
    )  # (columns, figure of the group, holds an odd note)
    for run in runs:
        f = fig[run[0]]
        if groups:
            members, gf, odd = groups[-1]
            near = abs(steps(f, gf)) == 1
            if (
                not odd and near and len(run) == 1 and len(members) >= 2
            ):  # one odd note closes the group
                groups[-1] = (members + run, gf, True)
                continue
            if (
                not odd and near and len(members) == 1 and len(run) >= 2
            ):  # one odd note opens this run
                groups[-1] = (members + run, f, True)
                continue
            why["cut at a figure change"] += 1
        groups.append((run, f, False))
    return [g[0] for g in groups]


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
        fig = [ns[0].figure for _, ns in cols]
        for chain in chains:
            for part in (p for u in _uniform(chain, fig, why) for p in _split(u, pitch, why)):
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
    """Every note by the spelling rules, in the armadura in force at its column, but a note the user spelled."""
    at = frames_mod.key_at(sheet)
    for n in sheet.notes:
        if not n.spelled:
            n.step, n.alter, n.octave = spell(n.midi, at(n.frame))


# ------------------------------------------------------------------ clefs and 8va

_LINES = {
    "G2": (4 * 7 + 2, 5 * 7 + 3),
    "F4": (2 * 7 + 4, 3 * 7 + 5),
}  # E4..F5, G2..A3 (diatonic index)
#: (clef, ottava, cost per column) of each state; the first one is the hand's own clef. Implementation 04-7 ends the
#: rule of 03 "never 8va in the bass clef": the left hand may read a short high stretch in the bass clef under 8va,
#: and the right hand a short low one in the treble clef under 8vb.
STATES = {
    1: [("G2", 0, 0.0), ("G2", 1, OTTAVA_COST), ("F4", 0, CLEF_PREFER), ("G2", -1, OTTAVA_COST)],
    2: [
        ("F4", 0, 0.0),
        ("G2", 0, CLEF_PREFER),
        ("G2", 1, CLEF_PREFER + OTTAVA_COST),
        ("F4", 1, OTTAVA_COST),
    ],
}
#: The hand's own clef, its other clef, and the octave line a short stretch takes in its own clef.
OWN = {1: "G2", 2: "F4"}
OTHER = {1: "F4", 2: "G2"}
LINE = {1: -1, 2: 1}


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
                if clef == OWN[staff] and not _fits(below_above, staff, ottava):
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
            prev_clef = clef
            for n in ns:
                n.ottava = ottava
        _ornament_lines(sheet, staff)
    sheet.clef_changes.sort(key=lambda c: (c[0], c[1]))
    info.update(short_clefs(sheet))
    drawn = [n for n in sheet.notes if not n.covered]
    info["clef changes"] = len(sheet.clef_changes)
    info["8va notes"] = sum(1 for n in drawn if n.ottava > 0)
    info["8vb notes"] = sum(1 for n in drawn if n.ottava < 0)
    return info


def _fits(below_above: list[tuple[int, int]], staff: int, ottava: int) -> bool:
    """The notes of a column in the hand's own clef are readable: the left hand never ``BASS_LIMIT`` ledger lines
    or more above the bass staff, the right hand never that far below the treble staff; under the octave line of
    the hand's own clef (left 8va, right 8vb) no note that far on the other side either (a wide chord)."""
    below = max(b for b, _ in below_above)
    above = max(a for _, a in below_above)
    far = above if staff == 2 else below
    if far >= BASS_LIMIT:
        return False
    if ottava and ottava == LINE[staff] and max(below, above) >= BASS_LIMIT:
        return False
    return True


def _ornament_lines(sheet: Sheet, staff: int) -> None:
    """Ornament onsets take the octave line of the note before them."""
    last = 0
    for n in sorted((n for n in sheet.notes if n.staff == staff), key=lambda n: n.frame):
        if n.covered:
            n.ottava = last
        else:
            last = n.ottava


def _track(sheet: Sheet, staff: int, frames: list[int]) -> list[str]:
    """The clef of ``staff`` in force at each of ``frames`` (sorted)."""
    changes = sorted((f, c) for f, st, c in sheet.clef_changes if st == staff)
    clef, k, out = sheet.clefs.get(staff, OWN[staff]), 0, []
    for frame in frames:
        while k < len(changes) and changes[k][0] <= frame:
            clef, k = changes[k][1], k + 1
        out.append(clef)
    return out


def short_clefs(sheet: Sheet) -> dict:
    """The shortest stretch of a clef (implementation 04-7, the user's rule of 2026-11-03): a hand changes to its
    other clef only for a whole passage. Each stretch of a hand in its other clef with fewer than ``CLEF_MIN`` of the
    hand's columns (grace notes do not count) goes back to the hand's own clef: its two clef changes go, and each of
    its columns takes the octave line of the own clef (left 8va, right 8vb) when a note would otherwise stand
    ``BASS_LIMIT`` ledger lines or more outside the staff; the columns between two marked columns join the line when
    their notes stay readable under it (at most ``READABLE`` ledger lines on its far side). A stretch stays as it is
    when one of its columns is readable neither way (a chord too wide for the line), or when it holds a clef the user
    set by hand (``Sheet.user_clefs``). Every other clef stays: the rule's, the AI's and the user's. Changes only
    clefs and octave lines; returns the counts."""
    info = {"short clef stretches": 0, "short stretches kept": 0, "notes under a new line": 0}
    for staff in (1, 2):
        cols = _columns(sheet, staff)
        if not cols:
            continue
        frames = [f for f, _ in cols]
        track = _track(sheet, staff, frames)
        own, other, line = OWN[staff], OTHER[staff], LINE[staff]
        marks = [(a, b) for a, b, st, c in sheet.user_clefs if st == staff and c == other]
        i, changed = 0, False
        while i < len(cols):
            if track[i] != other:
                i += 1
                continue
            j = i
            while j + 1 < len(cols) and track[j + 1] == other:
                j += 1
            a, b, i = i, j, j + 1
            main = sum(1 for k in range(a, b + 1) if any(not n.grace for n in cols[k][1]))
            if main >= CLEF_MIN:
                continue
            if any(lo <= frames[k] < hi for k in range(a, b + 1) for lo, hi in marks):
                info["short stretches kept"] += 1
                continue
            choice = []
            for k in range(a, b + 1):
                ns = cols[k][1]
                pick = next(
                    (o for o in (0, line) if _fits([_ledger(n, own, o) for n in ns], staff, o)), None
                )
                choice.append(pick)
            if None in choice:
                info["short stretches kept"] += 1
                continue
            marked = [k for k, o in enumerate(choice) if o]
            for p, q in zip(marked, marked[1:]):
                between = [n for k in range(p + 1, q) for n in cols[a + k][1]]
                far = [_ledger(n, own, line)[0 if staff == 2 else 1] for n in between]
                if all(x <= READABLE for x in far):
                    for k in range(p + 1, q):
                        choice[k] = line
            lo = frames[a - 1] if a > 0 else None
            hi = frames[b + 1] if b + 1 < len(frames) else None
            sheet.clef_changes = [
                c
                for c in sheet.clef_changes
                if not (c[1] == staff and (lo is None or c[0] > lo) and (hi is None or c[0] <= hi))
            ]
            if a == 0:
                sheet.clefs[staff] = own
            for k, o in enumerate(choice):
                for n in cols[a + k][1]:
                    if o and n.ottava != o:
                        info["notes under a new line"] += 1
                    n.ottava = o
            info["short clef stretches"] += 1
            changed = True
        if changed:
            _ornament_lines(sheet, staff)
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
    info["lengthened columns"] = lengthen_lone(sheet, quarter_ms, split)
    info.update(beam_groups(sheet, quarter_ms, split))
    if key is None:
        sheet.key, sheet.key_changes, kinfo = choose_keys(sheet)
        info.update(kinfo)
    else:
        sheet.key, sheet.key_changes = key, sorted(key_changes or [])
    respell(sheet)
    info.update(clefs_and_ottavas(sheet))
    return FramesProposal(sheet=sheet.sort(), quarter_ms=float(quarter_ms), info=info)
