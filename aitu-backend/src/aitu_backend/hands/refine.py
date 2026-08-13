"""The second pass: repair what a group-by-group search structurally cannot see.

The beam is a dynamic program over onset groups. Its state is two hands and a little
memory, which is exactly right for the question it answers — what can these hands
physically and musically do next — and exactly wrong for two questions that are about
the *result* rather than the step:

**Where does this print?** The split decides which staff a note is drawn on, so a hand
parked four ledger lines onto the other staff is a typesetting mistake the ergonomic
terms cannot feel. Putting a ledger charge inside the search does not fix this; it makes
it worse. Measured on the 209-scenario research benchmark, an in-search charge moved 49
onsets away from the human labels against 34 towards, because a search that cares about
the page rewrites whole textures to tidy one chord.

**Is this a figure?** Accompaniment figuration repeats a shape, and a figure is one
hand's gesture. The search has no way to notice that the notes it is dividing are the
fourth turn of something it already assigned three times.

Both defects are cheap to detect after the fact and expensive to express step by step,
so they are repaired here: detect, propose a small set of targeted moves, replay the
full objective, accept only on strict improvement plus a physical guard.

The two rules disagree by construction — the register rule wants a high left hand moved
up, a figure that climbed there wants to be left alone — so they share one pass and one
objective:

    J  +  w_ledger * C_ledger(with pattern relief)  +  w_pattern * C_pattern

and the argument is settled inside ``C_ledger`` rather than by which pass ran last. A
note inside a confident figure, held by that figure's owner, has been *explained*, so
its register charge is relieved. A high note with no figure behind it keeps the full
charge and still gets moved.

Three disciplines, each of which was learned by watching the pass misbehave without it:

* **a move must improve its own term.** Otherwise the pass becomes a second
  general-purpose optimizer: on an alternating-triad toccata it found a fifteen-onset
  move worth 6.7 of ergonomic cost that made the page *worse* and destroyed the hand
  alternation the labels ask for. Re-optimizing J is the beam's job.
* **candidates are built against the live assignment, never precomputed.** A candidate
  map built before an earlier move was accepted silently reverts it. This turned 18
  corrections into 18 corrections plus 15 regressions the first time it was missed.
* **one decision per hotspot, in order.** Taking the globally best move each round lets
  a long run-level move win before the local fixes get a chance, with the same result.
"""

from __future__ import annotations

import time as _time
from collections import Counter
from dataclasses import dataclass, field, replace
from itertools import pairwise
from typing import Any

from aitu_backend.hands import beam as beam_module
from aitu_backend.hands.candidates import generate
from aitu_backend.hands.config import DEFAULT_CONFIG, HandInferenceConfig, RefineConfig
from aitu_backend.hands.costs import (
    HANDS,
    LEFT,
    RIGHT,
    PairState,
    transition,
)
from aitu_backend.hands.events import DecodedMatrix
from aitu_backend.hands.figuration import Figure, detect, owner_of
from aitu_backend.hands.result import Assignment, Diagnostics, HandInferenceResult, build_result
from aitu_backend.hands.staff import across_offenders, ledger_charge, ledger_lines

EPS = 1e-9

HandMap = dict[str, str]


# ======================================================================================
# scoring one assignment
# ======================================================================================


@dataclass
class Replay:
    """A whole assignment, evaluated group by group. Never estimated."""

    base: float
    ledger: float
    pattern: float
    infeasible: int
    group_base: list[float]
    group_ledger: list[float]
    group_infeasible: list[bool]
    states: list[PairState]
    _suffix: tuple[list[float], list[float], list[int]] | None = None

    def total(self, refine: RefineConfig) -> float:
        return (
            self.base
            + refine.ledger_weight * self.ledger
            + refine.pattern_weight * self.pattern
        )

    def suffix(self) -> tuple[list[float], list[float], list[int]]:
        """Cached ``(base, ledger, infeasible)`` totals of ``groups[i:]``."""
        if self._suffix is None:
            n = len(self.group_base)
            sb, sl, si = [0.0] * (n + 1), [0.0] * (n + 1), [0] * (n + 1)
            for i in range(n - 1, -1, -1):
                sb[i] = sb[i + 1] + self.group_base[i]
                sl[i] = sl[i + 1] + self.group_ledger[i]
                si[i] = si[i + 1] + int(self.group_infeasible[i])
            self._suffix = (sb, sl, si)
        return self._suffix


def partition_of(group, hand_map: HandMap) -> tuple[str, ...]:
    return tuple(hand_map[event.onset_id] for event in group.events)


def relief_map(
    figures: list[Figure], hand_map: HandMap, config: HandInferenceConfig
) -> dict[str, float]:
    """Per-onset multiplier on the register charge, keyed by onset id.

    A note earns relief only if it is inside a figure *and* held by the hand that owns
    that figure. A note the other hand took gets none: its ledger lines are not the
    pattern's fault, and leaving the charge on is what keeps arguing for putting it back.
    """
    out: dict[str, float] = {}
    floor = config.refine.pattern_ledger_relief
    for figure in figures:
        if figure.confidence < config.figures.min_confidence:
            continue
        owner = owner_of(figure, hand_map)
        for onset_id in figure.onset_ids:
            if hand_map[onset_id] != owner:
                continue
            factor = max(0.0, 1.0 - figure.confidence * (1.0 - floor))
            out[onset_id] = min(out.get(onset_id, 1.0), factor)
    return out


def pattern_cost(
    figures: list[Figure], hand_map: HandMap, config: HandInferenceConfig
) -> tuple[float, list[dict[str, Any]]]:
    """``C_pattern`` plus a per-figure account of why."""
    weights = config.refine.patterns
    total = 0.0
    parts: list[dict[str, Any]] = []
    for figure in figures:
        ids = figure.onset_ids
        if not ids:
            continue
        owner = owner_of(figure, hand_map)
        phase_of = figure.phase_of()
        by_phase: dict[int, list[str]] = {}
        for onset_id in ids:
            by_phase.setdefault(phase_of[onset_id], []).append(onset_id)

        off: list[str] = []
        for members in by_phase.values():
            modal = Counter(hand_map[o] for o in members).most_common(1)[0][0]
            off += [o for o in members if hand_map[o] != modal]

        n = len(ids)
        broken = len(off) / n
        split = sum(1 for o in ids if hand_map[o] != owner) / n
        switch = sum(1 for a, b in pairwise(ids) if hand_map[a] != hand_map[b]) / max(
            1, n - 1
        )
        confidence = (
            figure.confidence if figure.confidence >= config.figures.min_confidence else 0.0
        )
        cost = confidence * (
            weights.broken * broken + weights.split * split + weights.switch * switch
        )
        total += cost
        parts.append(
            {
                "figure": figure,
                "owner": owner,
                "cost": cost,
                "broken": broken,
                "offPattern": sorted(set(off)),
            }
        )
    return total, parts


def _group_ledger(
    decoded: DecodedMatrix,
    group,
    hand_map: HandMap,
    state: PairState,
    config: HandInferenceConfig,
    relief: dict[str, float],
) -> float:
    """``C_ledger`` for one group, with the per-note relief applied."""
    struck: dict[str, list[int]] = {LEFT: [], RIGHT: []}
    by_midi: dict[str, dict[int, float]] = {LEFT: {}, RIGHT: {}}
    for event in group.events:
        hand = hand_map[event.onset_id]
        struck[hand].append(event.midi)
        factor = relief.get(event.onset_id, 1.0)
        by_midi[hand][event.midi] = min(by_midi[hand].get(event.midi, 1.0), factor)
    held = {name: state.hand(name).active_held(group.time_seconds) for name in HANDS}

    total = 0.0
    for hand in HANDS:
        if not struck[hand]:
            continue
        other = RIGHT if hand == LEFT else LEFT
        charge, _lines = ledger_charge(
            hand,
            tuple(sorted(struck[hand])),
            tuple(sorted(struck[other])),
            held[other],
            config.hand,
            relief=by_midi[hand],
        )
        total += charge
    return total


def evaluate(
    decoded: DecodedMatrix,
    hand_map: HandMap,
    config: HandInferenceConfig,
    figures: list[Figure],
    *,
    reference: Replay | None = None,
    changed: tuple[int, int] | None = None,
) -> Replay:
    """Score an assignment. With ``reference``/``changed``, only replay what can differ.

    A move touching groups ``[first, last]`` cannot change anything before ``first``.
    After ``last`` the two solutions play identical partitions, so they reconverge the
    moment the joint state matches the reference's again — and ``PairState.key()`` is
    the same equivalence the beam already uses to merge states, which makes the shortcut
    exact rather than approximate. Without it the pass is unusable on real pieces: on a
    four-minute matrix it is the difference between roughly 2x and 16x the search.
    """
    relief = relief_map(figures, hand_map, config)
    patterns, _parts = pattern_cost(figures, hand_map, config)

    n = len(decoded.groups)
    incremental = reference is not None and changed is not None and changed[1] >= 0
    if incremental:
        assert reference is not None and changed is not None
        first, last = changed
        group_base = list(reference.group_base)
        group_ledger = list(reference.group_ledger)
        group_infeasible = list(reference.group_infeasible)
        states = list(reference.states)
        state = reference.states[first]
        start = first
    else:
        first = last = -1
        group_base = [0.0] * n
        group_ledger = [0.0] * n
        group_infeasible = [False] * n
        states = [PairState()] + [PairState()] * n
        state = PairState()
        start = 0

    for index in range(start, n):
        group = decoded.groups[index]
        partition = partition_of(group, hand_map)
        result = transition(state, group, partition, config.hand, config.weights)
        bad = result is None
        if result is None:
            result = transition(
                state, group, partition, config.hand, config.weights, allow_infeasible=True
            )
            assert result is not None
        group_base[index] = result.cost
        group_ledger[index] = _group_ledger(decoded, group, hand_map, state, config, relief)
        group_infeasible[index] = bad
        state = result.state
        states[index + 1] = state

        if incremental and index >= last and state.key() == reference.states[index + 1].key():
            assert reference is not None
            sb, sl, si = reference.suffix()
            for j in range(index + 1, n):
                group_base[j] = reference.group_base[j]
                group_ledger[j] = reference.group_ledger[j]
                group_infeasible[j] = reference.group_infeasible[j]
                states[j + 1] = reference.states[j + 1]
            return Replay(
                base=sum(group_base[: index + 1]) + sb[index + 1],
                ledger=sum(group_ledger[: index + 1]) + sl[index + 1],
                pattern=patterns,
                infeasible=sum(group_infeasible[: index + 1]) + si[index + 1],
                group_base=group_base,
                group_ledger=group_ledger,
                group_infeasible=group_infeasible,
                states=states,
            )

    return Replay(
        base=sum(group_base),
        ledger=sum(group_ledger),
        pattern=patterns,
        infeasible=sum(group_infeasible),
        group_base=group_base,
        group_ledger=group_ledger,
        group_infeasible=group_infeasible,
        states=states,
    )


# ======================================================================================
# moves
# ======================================================================================


def _other(hand: str) -> str:
    return RIGHT if hand == LEFT else LEFT


def _move(hand_map: HandMap, onset_ids: list[str]) -> HandMap:
    out = dict(hand_map)
    for onset_id in onset_ids:
        out[onset_id] = _other(out[onset_id])
    return out


def _set_hand(hand_map: HandMap, onset_ids: list[str], hand: str) -> HandMap:
    out = dict(hand_map)
    for onset_id in onset_ids:
        out[onset_id] = hand
    return out


def changed_span(
    decoded: DecodedMatrix, current: HandMap, candidate: HandMap
) -> tuple[int, int]:
    """``(first, last)`` onset-group indices a change touches; ``(n, -1)`` if none."""
    changed = {o for o in candidate if candidate[o] != current.get(o)}
    first, last = len(decoded.groups), -1
    for index, group in enumerate(decoded.groups):
        if any(event.onset_id in changed for event in group.events):
            first = min(first, index)
            last = index
    return first, last


def flagged(
    decoded: DecodedMatrix, hand_map: HandMap, config: HandInferenceConfig
) -> dict[tuple[int, str], list[str]]:
    """``{(group index, hand): onsets written too far onto the other staff}``."""
    threshold = config.hand.ledger_grace_across + config.refine.flag_slack
    out: dict[tuple[int, str], list[str]] = {}
    for index, group in enumerate(decoded.groups):
        for event in group.events:
            hand = hand_map[event.onset_id]
            if (
                ledger_lines(event.midi, hand) >= threshold
                and across_offenders((event.midi,), hand, config.hand.ledger_grace_across)
            ):
                out.setdefault((index, hand), []).append(event.onset_id)
    return out


def _runs(
    decoded: DecodedMatrix,
    hand_map: HandMap,
    flags: dict[tuple[int, str], list[str]],
    config: HandInferenceConfig,
) -> list[tuple[str, list[int]]]:
    """Flagged groups gathered into runs, with the shoulders of each excursion."""
    threshold = config.hand.ledger_grace_across + config.refine.flag_slack
    shoulder = max(1.0, threshold - config.refine.shoulder_slack)
    by_hand: dict[str, list[int]] = {}
    for index, hand in sorted(flags):
        by_hand.setdefault(hand, []).append(index)

    runs: list[tuple[str, list[int]]] = []
    for hand, indices in by_hand.items():
        blocks: list[list[int]] = []
        for index in indices:
            if blocks and index - blocks[-1][-1] <= config.refine.run_gap:
                blocks[-1].append(index)
            else:
                blocks.append([index])
        for block in blocks:
            low, high = block[0], block[-1]

            def reaches(index: int, hand: str = hand) -> bool:
                midis = [
                    e.midi
                    for e in decoded.groups[index].events
                    if hand_map[e.onset_id] == hand
                ]
                return bool(midis) and max(ledger_lines(m, hand) for m in midis) >= shoulder

            while low > 0 and reaches(low - 1):
                low -= 1
            while high + 1 < len(decoded.groups) and reaches(high + 1):
                high += 1
            runs.append((hand, list(range(low, high + 1))))
    return runs


def _hand_ids(decoded: DecodedMatrix, hand_map: HandMap, index: int, hand: str) -> list[str]:
    return [e.onset_id for e in decoded.groups[index].events if hand_map[e.onset_id] == hand]


def _beyond(
    decoded: DecodedMatrix, hand_map: HandMap, index: int, hand: str, threshold: float
) -> list[str]:
    return [
        e.onset_id
        for e in decoded.groups[index].events
        if hand_map[e.onset_id] == hand and ledger_lines(e.midi, hand) >= threshold
    ]


def _ledger_cuts(
    decoded: DecodedMatrix,
    hand_map: HandMap,
    indices: list[int],
    hand: str,
    config: HandInferenceConfig,
    prefix: str,
) -> list[tuple[str, list[str]]]:
    """Three nested cuts through one hand's notes, from surgical to wholesale.

    ``offenders`` moves only what is flagged, which is right for a lone spike but shears
    a chord in half when only its bottom notes cross the threshold. ``clef-cut`` moves
    everything that has left the hand's own staff, which is the cut an engraver would
    make. ``whole-hand`` moves the lot.

    In a group one hand owns outright the narrow cut is withheld, because there the two
    cases look alike and are not: a rising triad stranded below the treble staff is
    entirely below it, so the clef cut takes all three notes and the chord survives as
    one shape; an octave doubling straddles the gap, so the clef cut takes only its
    lower note and each staff keeps a voice.
    """
    threshold = config.hand.ledger_grace_across + config.refine.flag_slack
    offenders: list[str] = []
    clef: list[str] = []
    whole: list[str] = []
    for index in indices:
        offenders += _beyond(decoded, hand_map, index, hand, threshold)
        clef += _beyond(decoded, hand_map, index, hand, config.hand.ledger_grace_across)
        whole += _hand_ids(decoded, hand_map, index, hand)

    if config.refine.clef_cut_single_hand_groups and any(
        decoded.groups[i].events
        and all(hand_map[e.onset_id] == hand for e in decoded.groups[i].events)
        for i in indices
    ):
        offenders = []

    out: list[tuple[str, list[str]]] = []
    for kind, ids in (
        (f"{prefix}-offenders", offenders),
        (f"{prefix}-clef-cut", clef),
        (f"{prefix}-whole-hand", whole),
    ):
        if ids and not any(ids == seen for _k, seen in out):
            out.append((kind, ids))
    return out


def _pattern_cuts(
    figure: Figure, hand_map: HandMap, config: HandInferenceConfig
) -> list[tuple[str, HandMap]]:
    """Repairs for one broken figure, from the one-note wobble to the whole gesture."""
    ids = figure.onset_ids
    owner = owner_of(figure, hand_map)
    out: list[tuple[str, HandMap]] = []

    phase_of = figure.phase_of()
    by_phase: dict[int, list[str]] = {}
    for onset_id in ids:
        by_phase.setdefault(phase_of[onset_id], []).append(onset_id)
    fixed = dict(hand_map)
    for members in by_phase.values():
        modal = Counter(hand_map[o] for o in members).most_common(1)[0][0]
        for onset_id in members:
            fixed[onset_id] = modal
    if fixed != hand_map:
        out.append(("pattern-off-phase-notes", fixed))

    cycle_of = figure.cycle_of()
    by_cycle: dict[int, list[str]] = {}
    for onset_id in ids:
        by_cycle.setdefault(cycle_of[onset_id], []).append(onset_id)
    fixed = dict(hand_map)
    for members in by_cycle.values():
        if len({hand_map[o] for o in members}) < 2:
            continue
        modal = Counter(hand_map[o] for o in members).most_common(1)[0][0]
        for onset_id in members:
            fixed[onset_id] = modal
    if fixed != hand_map:
        out.append(("pattern-whole-turns", fixed))

    for kind, hand in (("pattern-to-owner", owner), ("pattern-to-other-hand", _other(owner))):
        candidate = _set_hand(hand_map, ids, hand)
        if candidate != hand_map:
            out.append((kind, candidate))
    return out


def _window_resolve(
    decoded: DecodedMatrix,
    hand_map: HandMap,
    states: list[PairState],
    config: HandInferenceConfig,
    start: int,
    end: int,
) -> list[HandMap]:
    """Unpruned DP over a small window from the exact prefix state.

    A source of ideas, not of decisions: the proposer optimizes the search objective —
    it knows nothing about pattern relief — and everything it suggests still has to pass
    the same acceptance test as any other move.
    """
    weights = replace(config.weights, ledger=config.refine.ledger_weight)
    frontier: list[tuple[float, PairState, list[tuple[str, ...]]]] = [(0.0, states[start], [])]
    for index in range(start, end):
        group = decoded.groups[index]
        candidates, relaxed = generate(group, config.hand, config.search)
        pool: dict[tuple, tuple[float, PairState, list[tuple[str, ...]]]] = {}
        for cost, state, path in frontier:
            for partition in candidates:
                result = transition(
                    state, group, partition, config.hand, weights, allow_infeasible=relaxed
                )
                if result is None:
                    continue
                key = result.state.key()
                total = cost + result.cost
                if key not in pool or total < pool[key][0] - 1e-12:
                    pool[key] = (total, result.state, path + [partition])
        if not pool:
            return []
        frontier = sorted(pool.values(), key=lambda item: item[0])[:64]

    out: list[HandMap] = []
    for _cost, _state, path in frontier[:6]:
        candidate = dict(hand_map)
        for offset, partition in enumerate(path):
            for event, hand in zip(decoded.groups[start + offset].events, partition):
                candidate[event.onset_id] = hand
        if candidate != hand_map and candidate not in out:
            out.append(candidate)
    return out


# ======================================================================================
# the pass
# ======================================================================================


@dataclass
class RefineStats:
    rounds: int = 0
    figures: int = 0
    broken_figures: int = 0
    flagged_onsets: int = 0
    tried: dict[str, int] = field(default_factory=dict)
    accepted: dict[str, int] = field(default_factory=dict)
    rejected_by_guard: int = 0
    moved_onsets: int = 0
    trace: list[dict[str, Any]] = field(default_factory=list)

    def bump(self, bucket: dict[str, int], kind: str) -> None:
        bucket[kind] = bucket.get(kind, 0) + 1

    def to_wire(self) -> dict[str, Any]:
        return {
            "rounds": self.rounds,
            "figures": self.figures,
            "brokenFigures": self.broken_figures,
            "flaggedOnsets": self.flagged_onsets,
            "tried": dict(sorted(self.tried.items())),
            "accepted": dict(sorted(self.accepted.items())),
            "rejectedByGuard": self.rejected_by_guard,
            "movedOnsets": self.moved_onsets,
        }


def _physical(decoded: DecodedMatrix, hand_map: HandMap, config: HandInferenceConfig):
    """``(capacity, span, crossing)`` violations — model-independent, for the guard."""
    capacity = span = crossings = 0
    for group in decoded.groups:
        per_hand: dict[str, list[int]] = {LEFT: [], RIGHT: []}
        for event in group.events:
            per_hand[hand_map[event.onset_id]].append(event.midi)
        for midis in per_hand.values():
            if not midis:
                continue
            if len(set(midis)) > config.hand.max_simultaneous:
                capacity += 1
            if max(midis) - min(midis) > config.hand.hard_span:
                span += 1
        if per_hand[LEFT] and per_hand[RIGHT] and max(per_hand[LEFT]) > min(per_hand[RIGHT]):
            crossings += 1
    return capacity, span, crossings


def refine_map(
    decoded: DecodedMatrix,
    hand_map: HandMap,
    config: HandInferenceConfig | None = None,
) -> tuple[HandMap, RefineStats, list[Figure]]:
    """Improve ``hand_map`` in place of the page. Returns the map, an account, the figures."""
    config = config or DEFAULT_CONFIG
    settings = config.refine
    stats = RefineStats()
    started = _time.perf_counter()

    current = dict(hand_map)
    original = dict(hand_map)
    do_pattern = settings.pattern_weight > 0.0
    do_ledger = settings.ledger_weight > 0.0
    figures = detect(decoded, current, config.figures) if do_pattern else []
    stats.figures = len(figures)
    if not settings.enabled or not (do_pattern or do_ledger):
        return current, stats, figures

    score = evaluate(decoded, current, config, figures)
    physical = _physical(decoded, current, config)
    _cost, parts = pattern_cost(figures, current, config)
    stats.broken_figures = sum(1 for p in parts if p["cost"] > EPS)
    stats.flagged_onsets = sum(len(v) for v in flagged(decoded, current, config).values())

    families = [f for f, on in (("pattern", do_pattern), ("ledger", do_ledger)) if on]
    if not settings.pattern_first:
        families.reverse()

    for _round in range(settings.max_rounds):
        if _time.perf_counter() - started > settings.time_budget_s:
            break
        stats.rounds += 1
        improved = False

        for family in families:
            if _time.perf_counter() - started > settings.time_budget_s:
                break

            targets: list[Any]
            if family == "pattern":
                _cost, parts = pattern_cost(figures, current, config)
                targets = [
                    p["figure"] for p in sorted(parts, key=lambda p: -p["cost"])
                    if p["cost"] > EPS
                ]
            else:
                relief = relief_map(figures, current, config)
                flags = {
                    key: [o for o in ids if relief.get(o, 1.0) > 0.5]
                    for key, ids in flagged(decoded, current, config).items()
                }
                flags = {k: v for k, v in flags.items() if v}
                targets = [("group", hand, [i]) for (i, hand) in sorted(flags)]
                targets += [
                    ("run", hand, indices)
                    for hand, indices in _runs(decoded, current, flags, config)
                    if len(indices) > 1
                ]
                if settings.window_resolve:
                    targets += [
                        ("window", "-", t[2])
                        for t in list(targets)[: settings.max_windows]
                        if t[0] == "group"
                    ]

            for target in targets:
                if _time.perf_counter() - started > settings.time_budget_s:
                    break

                # built here, against the live map — see the module docstring
                if family == "pattern":
                    alternatives = _pattern_cuts(target, current, config)
                elif target[0] == "window":
                    index = target[2][0]
                    start = max(0, index - settings.window_pad)
                    end = min(len(decoded.groups), index + settings.window_pad + 1)
                    alternatives = [
                        (f"ledger-window[{start}:{end}]", candidate)
                        for candidate in _window_resolve(
                            decoded, current, score.states, config, start, end
                        )
                    ]
                else:
                    prefix, hand, indices = target
                    alternatives = [
                        (f"ledger-{kind}", _move(current, ids))
                        for kind, ids in _ledger_cuts(
                            decoded, current, indices, hand, config, prefix
                        )
                    ]

                best: tuple[float, str, HandMap, Replay, tuple[int, int, int]] | None = None
                for kind, candidate in alternatives:
                    if candidate == current:
                        continue
                    stats.bump(stats.tried, kind)
                    trial = evaluate(
                        decoded, candidate, config, figures,
                        reference=score, changed=changed_span(decoded, current, candidate),
                    )
                    if trial.infeasible > score.infeasible:
                        stats.rejected_by_guard += 1
                        continue
                    if settings.require_own_gain:
                        if family == "pattern" and trial.pattern >= score.pattern - EPS:
                            continue
                        if family == "ledger" and trial.ledger >= score.ledger - EPS:
                            continue
                    if trial.total(settings) >= score.total(settings) - EPS:
                        continue
                    phys = _physical(decoded, candidate, config)
                    if settings.physical_guard and any(
                        new > old for new, old in zip(phys, physical)
                    ):
                        stats.rejected_by_guard += 1
                        continue
                    if best is None or trial.total(settings) < best[0] - EPS:
                        best = (trial.total(settings), kind, candidate, trial, phys)

                if best is None:
                    continue
                _total, kind, candidate, trial, phys = best
                stats.trace.append(
                    {
                        "kind": kind,
                        "moved": sum(1 for o in candidate if candidate[o] != current[o]),
                        "deltaBase": round(trial.base - score.base, 4),
                        "deltaLedger": round(trial.ledger - score.ledger, 4),
                        "deltaPattern": round(trial.pattern - score.pattern, 4),
                    }
                )
                current, score, physical = candidate, trial, phys
                stats.bump(stats.accepted, kind)
                improved = True

        if not improved:
            break

    stats.moved_onsets = sum(1 for o in current if current[o] != original[o])
    return current, stats, figures


def infer(decoded: DecodedMatrix, config: HandInferenceConfig) -> HandInferenceResult:
    """Beam dynamic program, then the second pass. The default method."""
    started = _time.perf_counter()
    base = beam_module.beam(decoded, config)
    if not config.refine.enabled:
        return base

    refined, stats, figures = refine_map(decoded, base.hand_of(), config)
    score = evaluate(decoded, refined, config, figures)

    assignments: list[Assignment] = []
    for index, group in enumerate(decoded.groups):
        partition = partition_of(group, refined)
        result = transition(
            score.states[index], group, partition, config.hand, config.weights,
            allow_infeasible=True,
        )
        assert result is not None
        share = result.breakdown.weighted_dict(config.weights)
        share["ledger"] = config.refine.ledger_weight * score.group_ledger[index]
        per_note = max(1, len(group.events))
        candidates, _relaxed = generate(group, config.hand, config.search)
        margins = beam_module._confidence_margins(
            score.states[index], group, partition, candidates, config
        )
        for position, event in enumerate(group.events):
            assignments.append(
                Assignment(
                    onset_id=event.onset_id,
                    row=event.row,
                    midi=event.midi,
                    note=event.note,
                    column=event.column,
                    time_seconds=event.onset_time,
                    duration_frames=event.duration_frames,
                    hand=partition[position],
                    confidence=margins[position],
                    cost_breakdown={
                        name: value / per_note for name, value in share.items() if value
                    },
                    reasons=list(result.reasons),
                )
            )

    diagnostics = Diagnostics(
        total_cost=score.total(config.refine),
        runtime_ms=(_time.perf_counter() - started) * 1000.0,
        states_expanded=base.diagnostics.states_expanded,
        states_pruned=base.diagnostics.states_pruned,
        avg_candidates=base.diagnostics.avg_candidates,
        max_candidates=base.diagnostics.max_candidates,
        infeasible_groups=base.diagnostics.infeasible_groups,
        extra={
            "beamWidth": config.search.beam_width,
            "baseCost": round(base.diagnostics.total_cost, 4),
            "ledgerCost": round(score.ledger, 4),
            "patternCost": round(score.pattern, 4),
            "refine": stats.to_wire(),
        },
    )
    return build_result(
        method="beam-refine-v1",
        decoded=decoded,
        assignments=assignments,
        diagnostics=diagnostics,
        warnings=list(base.warnings),
        config_used={
            "beamWidth": config.search.beam_width,
            "relocationMode": config.hand.relocation_mode,
            "ledgerWeight": config.refine.ledger_weight,
            "patternWeight": config.refine.pattern_weight,
            "refineRounds": stats.rounds,
        },
    )


__all__ = [
    "RefineStats",
    "Replay",
    "changed_span",
    "evaluate",
    "flagged",
    "infer",
    "pattern_cost",
    "refine_map",
    "relief_map",
]
