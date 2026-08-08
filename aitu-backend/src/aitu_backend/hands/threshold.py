"""The old Appendix D rule, kept as a baseline: ``Do-4`` and above is the right hand.

Retained for three reasons, none of them "it is good enough":

1. **Speed.** ~80 ms where the beam takes ~2 s on the same benchmark. A preview
   or a very long matrix can trade quality for latency deliberately.
2. **Debugging.** When a split looks wrong, running both answers "is this the
   cost model or the plumbing?" in one call.
3. **Regression.** The existing tests assert the C4 rule; deleting it would hide
   whether a change broke the split or merely changed the method.

It is not the default and should not be. On the research benchmark it scored
0.848 onset accuracy against the beam's 0.955 — but the accuracy gap is the
least of it: the threshold produced **21 physically impossible hand spans** and
broke 21 invariants, because a fixed pitch boundary cannot express a hand
crossing, a left hand reaching into the middle register, or a melody that dips
below middle C without changing hands.
"""

from __future__ import annotations

import time as _time

from aitu_backend.hands.config import HandInferenceConfig
from aitu_backend.hands.costs import LEFT, PairState, RIGHT, transition
from aitu_backend.hands.events import DecodedMatrix
from aitu_backend.hands.result import Assignment, Diagnostics, HandInferenceResult, build_result

#: MIDI 60 = Do-4 = middle C. At or above it, the right hand.
DEFAULT_SPLIT_MIDI = 60


def infer(
    decoded: DecodedMatrix,
    config: HandInferenceConfig,
    *,
    split_midi: int = DEFAULT_SPLIT_MIDI,
) -> HandInferenceResult:
    """Assign by pitch alone, then score the result under the real cost model.

    Scoring a rule that optimizes nothing is the point: it makes the baseline
    comparable to the beam on the same objective, and it surfaces the impossible
    spans the rule creates instead of leaving them invisible.
    """
    started = _time.perf_counter()
    hand_map = {
        event.onset_id: (RIGHT if event.midi >= split_midi else LEFT) for event in decoded.events
    }

    state = PairState()
    total_cost = 0.0
    infeasible = 0
    per_onset: dict[str, dict[str, float]] = {}
    per_reasons: dict[str, list[str]] = {}

    for group in decoded.groups:
        partition = tuple(hand_map[event.onset_id] for event in group.events)
        result = transition(
            state, group, partition, config.hand, config.weights, allow_infeasible=False
        )
        if result is None:
            infeasible += 1
            result = transition(
                state, group, partition, config.hand, config.weights, allow_infeasible=True
            )
            assert result is not None
        share = result.breakdown.weighted_dict(config.weights)
        size = max(1, len(group.events))
        for event in group.events:
            per_onset[event.onset_id] = {
                name: value / size for name, value in share.items() if value
            }
            per_reasons[event.onset_id] = list(result.reasons)
        total_cost += result.cost
        state = result.state

    assignments = [
        Assignment(
            onset_id=event.onset_id,
            row=event.row,
            midi=event.midi,
            note=event.note,
            column=event.column,
            time_seconds=event.onset_time,
            duration_frames=event.duration_frames,
            hand=hand_map[event.onset_id],
            # The rule never weighs an alternative, so it has no decision margin.
            confidence=0.0,
            cost_breakdown=per_onset.get(event.onset_id, {}),
            reasons=per_reasons.get(event.onset_id, []),
        )
        for event in decoded.events
    ]

    warnings = list(decoded.warnings)
    if infeasible:
        warnings.append(
            f"The fixed {split_midi} threshold produced {infeasible} physically implausible "
            "group(s); the beam method avoids these"
        )

    diagnostics = Diagnostics(
        total_cost=total_cost,
        runtime_ms=(_time.perf_counter() - started) * 1000.0,
        infeasible_groups=infeasible,
        extra={"splitMidi": split_midi},
    )
    return build_result(
        method="threshold-c4",
        decoded=decoded,
        assignments=assignments,
        diagnostics=diagnostics,
        warnings=warnings,
        config_used={"splitMidi": split_midi},
    )


__all__ = ["DEFAULT_SPLIT_MIDI", "infer"]
