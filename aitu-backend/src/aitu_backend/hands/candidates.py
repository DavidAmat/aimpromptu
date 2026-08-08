"""Candidate partition generation for one onset group.

A group of ``k`` simultaneous onsets has ``2^k`` raw partitions, so this is where
the combinatorics are controlled. We keep:

* every contiguous low/high split (``k + 1`` of them) — the ordinary chord shapes;
* non-contiguous partitions with at most ``max_inversions`` pitch-order
  inversions — the crossing and voice-continuity exceptions;
* nothing that violates finger capacity or the absolute span limit.

The exception candidates matter more than they look. Prune them and the model
quietly degrades into a disguised pitch threshold, which is the thing this
whole package exists to replace. :func:`all_partitions` stays available so the
oracle loss caused by pruning can be measured on small cases rather than assumed.
"""

from __future__ import annotations

from itertools import product

from aitu_backend.hands.config import HandModel, SearchConfig
from aitu_backend.hands.costs import LEFT, RIGHT
from aitu_backend.hands.events import OnsetGroup

#: One hand name per event of a group, in the group's pitch order.
Partition = tuple[str, ...]


def all_partitions(k: int) -> list[Partition]:
    """Every ``2^k`` assignment, in deterministic order."""
    return [tuple(item) for item in product((LEFT, RIGHT), repeat=k)]


def _contiguous(k: int) -> list[Partition]:
    """``split`` low notes to the left hand, the rest to the right."""
    return [tuple([LEFT] * split + [RIGHT] * (k - split)) for split in range(k + 1)]


def _inversions(partition: Partition) -> int:
    """Pitch-order inversions: a right-hand note below a left-hand one."""
    return sum(
        1
        for i in range(len(partition))
        for j in range(i + 1, len(partition))
        if partition[i] == RIGHT and partition[j] == LEFT
    )


def is_feasible(group: OnsetGroup, partition: Partition, model: HandModel) -> bool:
    """Hard constraints only: five struck keys per hand, absolute span limit."""
    for hand in (LEFT, RIGHT):
        midis = [event.midi for event, assigned in zip(group.events, partition) if assigned == hand]
        if not midis:
            continue
        if len(set(midis)) > model.max_simultaneous:
            return False
        if max(midis) - min(midis) > model.hard_span:
            return False
    return True


def is_overloaded(group: OnsetGroup, model: HandModel) -> bool:
    """True when no two-hand partition could possibly play this group.

    Ten fingers is ten fingers. Past ``2 * max_simultaneous`` distinct struck
    keys there is no assignment to search for, so searching is not caution — it
    is burning time on a question with no answer. Real piano writing never gets
    here; noisy transcriptions and stress fixtures do.
    """
    return len({event.midi for event in group.events}) > 2 * model.max_simultaneous


def _balanced_neighbourhood(k: int) -> list[Partition]:
    """The even contiguous split and its two neighbours, deterministic."""
    middle = k // 2
    splits = sorted({max(0, middle - 1), middle, min(k, middle + 1)})
    return [tuple([LEFT] * split + [RIGHT] * (k - split)) for split in splits]


def generate(
    group: OnsetGroup,
    model: HandModel,
    search: SearchConfig,
    *,
    max_inversions: int = 1,
) -> tuple[list[Partition], bool]:
    """Return ``(candidates, relaxed)`` for one onset group.

    ``relaxed`` is True when no partition satisfies the hard constraints. The
    group is then reported as physically implausible rather than silently
    dropped or disguised — an unplayable transcription is information.
    """
    k = len(group)
    if k == 0:
        return [()], False

    if is_overloaded(group, model):
        # Nothing to optimize: report it and keep the search cheap. Still a few
        # candidates rather than one, so the surrounding context can pick the
        # least bad seam instead of being handed an arbitrary decision.
        return _balanced_neighbourhood(k), True

    raw: list[Partition]
    if k <= search.enumerate_max_notes:
        raw = [item for item in all_partitions(k) if _inversions(item) <= max_inversions]
    else:
        raw = list(_contiguous(k))
        # Nearest-center heuristic for very wide groups, where enumeration is hopeless.
        midis = [event.midi for event in group.events]
        pivot = (min(midis) + max(midis)) / 2.0
        raw.append(tuple(LEFT if midi < pivot else RIGHT for midi in midis))

    seen: set[Partition] = set()
    ordered: list[Partition] = []
    for partition in list(_contiguous(k)) + raw:
        if partition not in seen:
            seen.add(partition)
            ordered.append(partition)

    feasible = [item for item in ordered if is_feasible(group, item, model)]
    if not feasible:
        return ordered[: search.candidate_limit], True
    if len(feasible) > search.candidate_limit:
        # Contiguous splits first, then the lowest-inversion exceptions.
        feasible.sort(key=lambda item: (_inversions(item), ordered.index(item)))
        feasible = feasible[: search.candidate_limit]
    return feasible, False


__all__ = ["Partition", "all_partitions", "generate", "is_feasible", "is_overloaded"]
