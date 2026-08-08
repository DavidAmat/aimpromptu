"""Beam dynamic program over onset groups — the method that ships.

One engine serves three methods; only the beam width and the lookahead differ:

* ``beam_width = 1``   + lookahead -> contextual greedy (fast baseline)
* ``beam_width = W``   + lookahead -> beam DP, the default (W = 12)
* ``beam_width = inf`` -> exact DP over the reachable state graph (small-case oracle)

Left to right over onset groups, the state is the joint hand state
(:class:`~aitu_backend.hands.costs.PairState`) and the transition is one
candidate partition. Complexity is ``O(G * W * C)`` transitions for ``G`` groups
and ``C`` candidates per group, so runtime tracks **polyphony**, not matrix
resolution — a dense chordal texture is the risk, not a fine granularity.

Why a beam and not a greedy pass: a locally convenient assignment routinely
creates an impossible jump one group later. Why a beam and not an exact DP: the
PoC measured **zero search regret** at width 12 on its benchmark, meaning the
beam finds the true optimum of the objective everywhere it could afford to
verify. Any remaining error is in the cost model, which is a far better place
for it than in the search.

Deterministic throughout: equal-cost states keep insertion order, which is the
deterministic candidate order from :mod:`aitu_backend.hands.candidates`. The
same matrix always produces the same split.
"""

from __future__ import annotations

import math
import time as _time
from dataclasses import dataclass

from aitu_backend.hands.candidates import Partition, generate
from aitu_backend.hands.config import HandInferenceConfig
from aitu_backend.hands.costs import (
    LEFT,
    RIGHT,
    CostBreakdown,
    HandModel,
    PairState,
    available_time,
    transition,
)
from aitu_backend.hands.events import DecodedMatrix, OnsetGroup
from aitu_backend.hands.result import Assignment, Diagnostics, HandInferenceResult, build_result

#: Cost margin, in objective units, that maps to ~63% confidence.
CONFIDENCE_SCALE = 0.5

#: Stands in for "unbounded beam" without an infinity that breaks slicing.
UNBOUNDED = 10**9


@dataclass
class _Node:
    """One surviving state at one group, plus the edge that reached it."""

    state: PairState
    cost: float
    parent: int
    partition: Partition
    breakdown: CostBreakdown
    reasons: tuple[str, ...]


def _lookahead(state: PairState, group: OnsetGroup | None, model: HandModel) -> float:
    """Optimistic estimate of the movement the next group will still require.

    Used only to *rank* states for pruning, never added to the reported cost.
    Keeping it admissible-ish matters: an over-eager estimate would prune the
    very states that pay off one group later.
    """
    if group is None:
        return 0.0
    midis = [event.midi for event in group.events]
    low, high = min(midis), max(midis)
    time = group.time_seconds
    best = math.inf
    for target, other in ((low, high), (high, low), ((low + high) / 2.0, None)):
        cost = 0.0
        for hand, pitch in ((LEFT, target), (RIGHT, other if other is not None else target)):
            hand_state = state.left if hand == LEFT else state.right
            if hand_state.center is None:
                continue
            gap = available_time(hand_state, time, model)
            over = max(0.0, abs(pitch - hand_state.center) - model.free_speed * gap)
            cost += (over / 12.0) ** model.movement_power
        best = min(best, cost)
    return 0.0 if best is math.inf else best * 0.5


def run(
    decoded: DecodedMatrix,
    config: HandInferenceConfig,
    *,
    beam_width: int,
    method: str,
    use_lookahead: bool = True,
) -> HandInferenceResult:
    """Run the dynamic program and build a full result."""
    started = _time.perf_counter()
    weights, model, search = config.weights, config.hand, config.search
    warnings = list(decoded.warnings)

    levels: list[list[_Node]] = []
    frontier: list[_Node] = [_Node(PairState(), 0.0, -1, (), CostBreakdown(), ())]
    expanded = pruned = 0
    infeasible_groups = 0
    candidate_counts: list[int] = []
    group_candidates: list[list[Partition]] = []

    for index, group in enumerate(decoded.groups):
        candidates, relaxed = generate(group, model, search)
        group_candidates.append(candidates)
        candidate_counts.append(len(candidates))
        if relaxed:
            infeasible_groups += 1
            warnings.append(
                f"Column {group.column}: no physically plausible hand partition for "
                f"{len(group)} simultaneous onsets; reported as implausible"
            )
        next_group = (
            decoded.groups[index + 1]
            if use_lookahead and search.lookahead_groups > 0 and index + 1 < len(decoded.groups)
            else None
        )

        # State deduplication: many (parent, partition) pairs land on the same joint
        # hand state, and only the cheapest way of reaching it can ever matter.
        pool: dict[tuple, tuple[float, _Node]] = {}
        for parent_index, parent in enumerate(frontier):
            for partition in candidates:
                result = transition(
                    parent.state, group, partition, model, weights, allow_infeasible=relaxed
                )
                expanded += 1
                if result is None:
                    continue
                total = parent.cost + result.cost
                priority = total + _lookahead(result.state, next_group, model)
                key = result.state.key()
                current = pool.get(key)
                if current is None or priority < current[0] - 1e-12:
                    pool[key] = (
                        priority,
                        _Node(
                            result.state,
                            total,
                            parent_index,
                            partition,
                            result.breakdown,
                            result.reasons,
                        ),
                    )

        if not pool:
            # Every candidate was infeasible from every surviving state. Relax once
            # rather than dropping the group: an unplayable passage must appear in the
            # output with a warning, not vanish.
            for parent_index, parent in enumerate(frontier):
                for partition in candidates:
                    result = transition(
                        parent.state, group, partition, model, weights, allow_infeasible=True
                    )
                    if result is None:
                        continue
                    total = parent.cost + result.cost
                    pool[result.state.key()] = (
                        total,
                        _Node(
                            result.state,
                            total,
                            parent_index,
                            partition,
                            result.breakdown,
                            result.reasons,
                        ),
                    )
            infeasible_groups += 1

        ranked = sorted(pool.values(), key=lambda item: item[0])
        pruned += max(0, len(ranked) - beam_width)
        frontier = [node for _, node in ranked[:beam_width]]
        levels.append(frontier)
        if expanded > search.max_states_expanded:
            warnings.append("Search aborted early: max_states_expanded exceeded")
            break

    # ---- reconstruct the cheapest path ---------------------------------------------
    path: list[_Node] = []
    if levels:
        node_index = min(range(len(levels[-1])), key=lambda i: levels[-1][i].cost)
        for level in range(len(levels) - 1, -1, -1):
            node = levels[level][node_index]
            path.append(node)
            node_index = node.parent
        path.reverse()

    states: list[PairState] = [PairState()]
    for node in path:
        states.append(node.state)

    assignments: list[Assignment] = []
    total_cost = path[-1].cost if path else 0.0
    for step, node in enumerate(path):
        group = decoded.groups[step]
        share = node.breakdown.weighted_dict(weights)
        size = max(1, len(group.events))
        margins = _confidence_margins(
            states[step], group, node.partition, group_candidates[step], config
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
                    hand=node.partition[position],
                    confidence=margins[position],
                    cost_breakdown={name: value / size for name, value in share.items() if value},
                    reasons=list(node.reasons),
                )
            )

    diagnostics = Diagnostics(
        total_cost=total_cost,
        runtime_ms=(_time.perf_counter() - started) * 1000.0,
        states_expanded=expanded,
        states_pruned=pruned,
        avg_candidates=(sum(candidate_counts) / len(candidate_counts) if candidate_counts else 0.0),
        max_candidates=max(candidate_counts, default=0),
        infeasible_groups=infeasible_groups,
        extra={"beamWidth": "exact" if beam_width >= UNBOUNDED else beam_width},
    )
    return build_result(
        method=method,
        decoded=decoded,
        assignments=assignments,
        diagnostics=diagnostics,
        warnings=warnings,
        config_used={"beamWidth": beam_width, "relocationMode": model.relocation_mode},
    )


def _confidence_margins(
    state: PairState,
    group: OnsetGroup,
    chosen: Partition,
    candidates: list[Partition],
    config: HandInferenceConfig,
) -> list[float]:
    """Local decision margin per onset, mapped to ``(0, 1]``.

    Measures how much more the cheapest local alternative that flips this note
    would cost from the same predecessor state. It is uncalibrated and blind to
    downstream effects — read :attr:`~aitu_backend.hands.result.Assignment.confidence`
    before using it for anything but ordering.
    """
    base = transition(state, group, chosen, config.hand, config.weights, allow_infeasible=True)
    if base is None:  # pragma: no cover - allow_infeasible never returns None
        return [1.0] * len(chosen)
    costs: dict[Partition, float] = {}
    for partition in candidates:
        result = transition(
            state, group, partition, config.hand, config.weights, allow_infeasible=True
        )
        if result is not None:
            costs[partition] = result.cost

    margins: list[float] = []
    for position in range(len(chosen)):
        alternatives = [
            cost for partition, cost in costs.items() if partition[position] != chosen[position]
        ]
        if not alternatives:
            margins.append(1.0)
            continue
        margin = max(0.0, min(alternatives) - base.cost)
        margins.append(1.0 - math.exp(-margin / CONFIDENCE_SCALE))
    return margins


def greedy(decoded: DecodedMatrix, config: HandInferenceConfig) -> HandInferenceResult:
    """Contextual greedy: width 1 with one-group lookahead."""
    return run(decoded, config, beam_width=1, method="greedy-v3", use_lookahead=True)


def beam(decoded: DecodedMatrix, config: HandInferenceConfig) -> HandInferenceResult:
    """Beam dynamic programming — the shipped method."""
    return run(
        decoded,
        config,
        beam_width=config.search.beam_width,
        method="beam-dp-v3",
        use_lookahead=True,
    )


def exact(decoded: DecodedMatrix, config: HandInferenceConfig) -> HandInferenceResult:
    """Unpruned DP over the reachable state graph. An oracle for small cases only."""
    return run(decoded, config, beam_width=UNBOUNDED, method="exact-dp", use_lookahead=False)


__all__ = ["CONFIDENCE_SCALE", "beam", "exact", "greedy", "run"]
