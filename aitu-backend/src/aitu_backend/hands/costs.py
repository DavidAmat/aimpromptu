"""Hand state and the named cost components of the objective.

The objective, minimized over the whole piece::

    J = sum over onset groups of sum_i lambda_i * C_i(previous state, assignment)

Every term is named, separately weighted and separately reportable, so a
disagreement with the output is a question about *which term* is wrong rather
than about an opaque score. All costs are normalized so that "one octave of
trouble" is roughly 1.0 — no term can dominate merely by having a larger scale.

Hard feasibility (five fingers, absolute span) is **not** a large penalty; it is
a separate answer. :func:`transition` returns ``None``, and the search simply
never visits that state. Mixing the two is how a model ends up recommending
something unplayable because it was cheap in aggregate.

Term reference (definitions from the PoC's `implementation/notation.md`):

``span``          struck span beyond comfort, squared; minus a bonus for an exact octave
``capacity``      more than five distinct keys in one hand
``movement``      relocation distance beyond what the available time affords
``acceleration``  change of velocity between groups
``crossing``      hands inverted, plus a collision term when they are inverted *and* close
``crossdur``      escalating cost of *staying* crossed past a grace period
``interleaving``  pitch-order inversions inside one group (L-R-L-R shapes)
``voice``         taking a note the other hand's recent voice was carrying
``role``          swapping which hand is on top
``pitch_prior``   the demoted C4 rule: a weak nudge, never a decision
``octave``        splitting an exposed octave across hands
``split``         using two hands for a group one hand could hold
``balance``       load evenness for thick groups; grip strain when one hand takes them alone
``dominance``     an unclaimed middle/high passage defaults to the right hand
``polyphony``     striking while the same hand keeps another voice sounding
``engagement``    waking an idle hand
``handoff``       an unnecessary handover when the previous hand could have continued
``future``        reserved lookahead term (weight 0.0 by default)
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass, field, replace

from aitu_backend.hands.config import CostWeights, HandModel
from aitu_backend.hands.events import NoteEvent, OnsetGroup

#: Sentinel "this hand has never played". Comparisons use ``NEVER / 2`` so that
#: any real time, however small, reads as later.
NEVER = -1.0e9

LEFT = "left"
RIGHT = "right"
HANDS = (LEFT, RIGHT)

_OCTAVE = 12.0


@dataclass(frozen=True)
class HandState:
    """Interpretable state of one hand between onset groups.

    Deliberately readable: every field is something you could point at on a
    video of a pianist. That is what makes a cost explainable afterwards.
    """

    center: float | None = None
    notes: tuple[int, ...] = ()
    last_time: float = NEVER
    velocity: float = 0.0
    #: ``(midi, end_time)`` of notes still sounding.
    held: tuple[tuple[int, float], ...] = ()
    #: The group *before* the last one. Voice continuity needs two groups of memory,
    #: or any alternating figure (stride bass-chord-bass-chord, an ostinato woven
    #: around accents) always presents its "wrong half" and continuity goes silent.
    #: This was the single largest accuracy gain of the whole research effort.
    prev_notes: tuple[int, ...] = ()
    prev_time: float = NEVER

    @property
    def used(self) -> bool:
        return self.center is not None

    def hold_until(self) -> float:
        return max((end for _, end in self.held), default=self.last_time)

    def active_held(self, time: float) -> tuple[int, ...]:
        """MIDI numbers still sounding at ``time``."""
        return tuple(midi for midi, end in self.held if end > time + 1e-9)

    def key(self) -> tuple:
        """Deduplication key. Rounding merges states that differ below audibility."""
        return (
            None if self.center is None else round(self.center, 2),
            self.notes,
            round(self.last_time, 4),
            round(self.velocity, 1),
            tuple(sorted((midi, round(end, 4)) for midi, end in self.held)),
            self.prev_notes,
            round(self.prev_time, 4),
        )


@dataclass(frozen=True)
class PairState:
    """Joint state of both hands — the dynamic program's state."""

    left: HandState = field(default_factory=HandState)
    right: HandState = field(default_factory=HandState)
    #: Hand that played the highest sounding pitch of the last group.
    top_hand: str | None = None
    #: When the current inversion (left above right) began, or ``None``.
    crossed_since: float | None = None
    #: The previous group was an exact octave split across hands (parallel doubling).
    octave_doubling: bool = False

    def hand(self, name: str) -> HandState:
        return self.left if name == LEFT else self.right

    def key(self) -> tuple:
        return (
            self.left.key(),
            self.right.key(),
            self.top_hand,
            None if self.crossed_since is None else round(self.crossed_since, 4),
            self.octave_doubling,
        )


@dataclass(frozen=True)
class CostBreakdown:
    """Per-component costs of one transition, before weighting."""

    span: float = 0.0
    capacity: float = 0.0
    movement: float = 0.0
    acceleration: float = 0.0
    crossing: float = 0.0
    crossdur: float = 0.0
    interleaving: float = 0.0
    voice: float = 0.0
    role: float = 0.0
    pitch_prior: float = 0.0
    octave: float = 0.0
    split: float = 0.0
    balance: float = 0.0
    dominance: float = 0.0
    polyphony: float = 0.0
    engagement: float = 0.0
    handoff: float = 0.0
    future: float = 0.0

    def weighted_total(self, weights: CostWeights) -> float:
        return (
            weights.span * self.span
            + weights.capacity * self.capacity
            + weights.movement * self.movement
            + weights.acceleration * self.acceleration
            + weights.crossing * self.crossing
            + weights.crossdur * self.crossdur
            + weights.interleaving * self.interleaving
            + weights.voice * self.voice
            + weights.role * self.role
            + weights.pitch_prior * self.pitch_prior
            + weights.octave * self.octave
            + weights.split * self.split
            + weights.balance * self.balance
            + weights.dominance * self.dominance
            + weights.polyphony * self.polyphony
            + weights.engagement * self.engagement
            + weights.handoff * self.handoff
            + weights.future * self.future
        )

    def weighted_dict(self, weights: CostWeights) -> dict[str, float]:
        """Weighted components, camelCase — this is what reaches the wire."""
        return {
            "span": weights.span * self.span,
            "capacity": weights.capacity * self.capacity,
            "movement": weights.movement * self.movement,
            "acceleration": weights.acceleration * self.acceleration,
            "crossing": weights.crossing * self.crossing,
            "crossdur": weights.crossdur * self.crossdur,
            "interleaving": weights.interleaving * self.interleaving,
            "voice": weights.voice * self.voice,
            "role": weights.role * self.role,
            "pitchPrior": weights.pitch_prior * self.pitch_prior,
            "octave": weights.octave * self.octave,
            "split": weights.split * self.split,
            "balance": weights.balance * self.balance,
            "dominance": weights.dominance * self.dominance,
            "polyphony": weights.polyphony * self.polyphony,
            "engagement": weights.engagement * self.engagement,
            "handoff": weights.handoff * self.handoff,
            "future": weights.future * self.future,
        }

    def __add__(self, other: "CostBreakdown") -> "CostBreakdown":
        return CostBreakdown(
            **{
                name: getattr(self, name) + getattr(other, name)
                for name in CostBreakdown.__dataclass_fields__
            }
        )


@dataclass(frozen=True)
class TransitionResult:
    """Outcome of applying one candidate partition to a state."""

    state: PairState
    breakdown: CostBreakdown
    cost: float
    reasons: tuple[str, ...]


def _add(acc: dict[str, float], term: str, amount: float) -> None:
    """Accumulate one cost term. Absent means zero, which is what most terms are."""
    acc[term] = acc.get(term, 0.0) + amount


def _center(notes: tuple[int, ...]) -> float:
    return (min(notes) + max(notes)) / 2.0


def available_time(state: HandState, time: float, model: HandModel) -> float:
    """Seconds the hand had to relocate before ``time``.

    Under ``release_aware`` only notes still sounding *at* the new onset block
    the hand; a key released exactly on the next onset is ordinary legato and
    costs no preparation time.
    """
    if state.last_time <= NEVER / 2:
        return 1.0
    if model.relocation_mode == "release_aware":
        active_end = max(
            (end for _, end in state.held if end > time + 1e-9),
            default=state.last_time,
        )
        start = max(state.last_time, min(active_end, time))
    else:
        start = state.last_time
    return max(time - start, model.min_available_time)


def transition(
    prev: PairState,
    group: OnsetGroup,
    assignment: tuple[str, ...],
    model: HandModel,
    weights: CostWeights,
    *,
    allow_infeasible: bool = False,
) -> TransitionResult | None:
    """Apply one candidate hand partition of an onset group.

    ``assignment[i]`` is the hand of ``group.events[i]``; events are pitch-sorted
    ascending. Returns ``None`` when a hard feasibility constraint is violated,
    unless ``allow_infeasible`` — which the search uses only to report an
    impossible passage instead of pretending it is playable.
    """
    time = group.time_seconds
    events: tuple[NoteEvent, ...] = group.events
    per_hand: dict[str, list[NoteEvent]] = {LEFT: [], RIGHT: []}
    for event, hand in zip(events, assignment):
        per_hand[hand].append(event)

    # Costs accumulate in a plain dict and become a frozen CostBreakdown once, at
    # the end. Rebuilding an 18-field frozen dataclass fifteen times per transition
    # was pure overhead in the hottest function of the search.
    acc: dict[str, float] = {}
    reasons: list[str] = []
    new_states: dict[str, HandState] = {}

    for hand in HANDS:
        state = prev.hand(hand)
        assigned = tuple(sorted(event.midi for event in per_hand[hand]))
        held = state.active_held(time)

        if not assigned:
            new_states[hand] = replace(
                state, held=tuple((m, e) for m, e in state.held if e > time + 1e-9)
            )
            continue

        # --- capacity: five fingers ---------------------------------------------
        if len(set(assigned)) > model.max_simultaneous:
            if not allow_infeasible:
                return None
            _add(acc, "capacity", len(set(assigned)) - model.max_simultaneous)
        occupied = len(set(assigned) | set(held))
        if occupied > model.max_simultaneous:
            _add(acc, "capacity", 0.4 * (occupied - model.max_simultaneous))

        # --- span ----------------------------------------------------------------
        struck_span = max(assigned) - min(assigned)
        if struck_span > model.hard_span and not allow_infeasible:
            return None
        excess = max(0.0, struck_span - model.comfort_span)
        span_cost = model.span_curve * excess * excess
        if len(assigned) == 2 and struck_span == 12:
            # An octave is fingers 1 and 5: the most natural shape there is.
            span_cost -= model.octave_together_bonus
            reasons.append(f"{hand}: octave kept in one hand")
        elif excess > 0:
            reasons.append(f"{hand}: span {struck_span:.0f} st exceeds comfort")

        combined = assigned + held
        if len(combined) >= 2:
            combined_span = max(combined) - min(combined)
            # Under release_aware the held fingers are DOWN, so a struck note beyond
            # the hard span from a held one is unreachable, not merely awkward.
            if (
                model.held_span_hard
                and model.relocation_mode == "release_aware"
                and combined_span > model.hard_span
                and not allow_infeasible
            ):
                return None
            held_excess = max(0.0, combined_span - model.comfort_span)
            span_cost += model.sustain_span_weight * held_excess * held_excess / _OCTAVE
        _add(acc, "span", span_cost)

        # --- movement and acceleration -------------------------------------------
        target = _center(assigned)
        available = available_time(state, time, model)
        velocity = 0.0
        if state.center is not None:
            distance = abs(target - state.center)
            # In-place reach: if the previous and new struck notes all fit under one
            # comfort span the hand never relocated, it re-shaped in place. This is
            # what tremolos, repeated figures and rocking basses actually do.
            if (
                model.reach_slack
                and state.notes
                and (
                    max(*assigned, *state.notes) - min(*assigned, *state.notes)
                    <= model.comfort_span
                )
            ):
                distance = 0.0
            free = model.free_speed * available
            over = max(0.0, distance - free)
            move_cost = (over / _OCTAVE) ** model.movement_power
            if move_cost > 0.05:
                reasons.append(
                    f"{hand}: {distance:.0f} st in {available:.2f} s is a rushed relocation"
                )
            _add(acc, "movement", move_cost)
            velocity = (
                0.0
                if distance == 0.0
                else (target - state.center) / max(available, model.min_available_time)
            )
            _add(
                acc,
                "acceleration",
                abs(velocity - state.velocity) / (2.0 * model.free_speed),
            )

        # --- weak absolute-pitch prior -------------------------------------------
        # All that survives of the old C4 threshold: a nudge worth one twelfth of a
        # movement unit per octave of deviation, routinely overruled by context.
        prior = 0.0
        for midi in assigned:
            if hand == RIGHT:
                prior += max(0.0, model.pitch_prior_center - midi) / _OCTAVE
            else:
                prior += max(0.0, midi - model.pitch_prior_center) / _OCTAVE
        _add(acc, "pitch_prior", prior / len(assigned))

        # --- waking an idle hand --------------------------------------------------
        if state.last_time <= NEVER / 2 or (time - state.last_time) > model.engagement_gap:
            _add(acc, "engagement", 1.0)

        # --- same-hand polyphony --------------------------------------------------
        # Striking while this hand keeps OTHER notes sounding means one hand is
        # carrying two live voices; two free hands do that more naturally.
        if held and any(midi not in assigned for midi in held):
            _add(acc, "polyphony", 1.0)

        still_held = tuple(
            (midi, end)
            for midi, end in state.held
            if end > time + 1e-9 and midi not in set(assigned)
        ) + tuple((event.midi, event.end_time) for event in per_hand[hand])
        new_states[hand] = HandState(
            center=target,
            notes=assigned,
            last_time=time,
            velocity=velocity,
            held=tuple(sorted(still_held)),
            prev_notes=state.notes,
            prev_time=state.last_time,
        )

    left_new, right_new = new_states[LEFT], new_states[RIGHT]
    lefts = [event.midi for event in per_hand[LEFT]]
    rights = [event.midi for event in per_hand[RIGHT]]

    # --- crossing and collision ---------------------------------------------------
    # Being inverted costs a small constant. The *physical* difficulty of a crossing
    # comes from the hands being close while inverted, not from how far apart they
    # are: reaching two octaves over the other hand is easy, sharing five semitones
    # with it is not.
    crossed_since = prev.crossed_since

    def is_active(hand_state: HandState, struck: list[NoteEvent]) -> bool:
        return bool(struck) or bool(hand_state.active_held(time))

    # Only two ACTIVE hands can be crossed. A stale center left behind by a hand
    # that finished its gesture is not a physical position.
    inverted_now = (
        left_new.center is not None
        and right_new.center is not None
        and left_new.center > right_new.center
        and is_active(left_new, per_hand[LEFT])
        and is_active(right_new, per_hand[RIGHT])
    )
    if inverted_now:
        _add(acc, "crossing", model.crossing_base)
        reasons.append("hands crossed (left above right)")
        # A crossing is an ornament, not a posture: the longer the hands have
        # ALREADY been inverted, the more each further crossed group costs.
        if crossed_since is None:
            crossed_since = time
        else:
            over_grace = max(0.0, (time - crossed_since) - model.crossdur_grace)
            if over_grace > 0.0:
                _add(acc, "crossdur", over_grace / model.crossdur_ref)
                reasons.append("hands have stayed crossed too long")
    else:
        crossed_since = None

    if lefts and rights:
        gap = _closest_inversion(lefts, rights)
        if gap is not None:
            _add(
                acc,
                "crossing",
                max(0.0, model.collision_margin - gap) / model.collision_margin,
            )

    # --- interleaving inside the group --------------------------------------------
    inversions = _count_inversions(assignment)
    if inversions:
        _add(acc, "interleaving", inversions)

    # --- octave split ---------------------------------------------------------------
    # Only an EXPOSED octave — a bare two-note group exactly an octave apart with
    # similar durations — is one natural hand shape. An octave pair buried inside a
    # thicker group (stride chord plus melody note), or between a held and a passing
    # note, is not a chordal octave and is not charged.
    octave_splits = 0
    if (
        len(events) == 2
        and events[1].midi - events[0].midi == 12
        and assignment[0] != assignment[1]
        and max(events[0].duration_frames, events[1].duration_frames)
        <= 1.5 * max(1, min(events[0].duration_frames, events[1].duration_frames))
    ):
        octave_splits = 1
    # A CONTINUED doubling is two parallel voices, not a broken hand shape: a
    # parallel-octave fanfare pays once, not once per frame.
    if octave_splits and not prev.octave_doubling:
        _add(acc, "octave", octave_splits)

    # --- voice continuity ------------------------------------------------------------
    # The remembered voice of each hand depends only on the previous state, not on
    # which note we are looking at, so it is built once per transition rather than
    # once per note. On a thick chord that is the difference between O(k * m) and
    # O(m log m + k log m) — and it was the hottest path in the whole search.
    remembered = {
        LEFT: _voice_candidates(prev.left, time, model),
        RIGHT: _voice_candidates(prev.right, time, model),
    }
    voice_cost = 0.0
    for event, hand in zip(events, assignment):
        other = LEFT if hand == RIGHT else RIGHT
        d_same = _nearest_distance(remembered[hand], event.midi)
        d_other = _nearest_distance(remembered[other], event.midi)
        if d_other < d_same and d_other <= model.voice_tolerance:
            voice_cost += min(1.0, (d_same - d_other) / _OCTAVE)
            if d_other == 0.0:
                voice_cost += 0.5
    if voice_cost:
        _add(acc, "voice", voice_cost)
        reasons.append("breaks the voice that the other hand was carrying")

    # --- role stability ---------------------------------------------------------------
    # The "top" hand is the hand of the highest SOUNDING pitch (struck or still held),
    # not merely of this group's highest onset — otherwise alternating single-voice
    # textures (canons, inventions, accompaniment under a held melody) register
    # phantom role swaps every frame.
    def sounding_max(hand_state: HandState) -> int | None:
        active = [midi for midi, end in hand_state.held if end > time + 1e-9]
        return max(active) if active else None

    left_max, right_max = sounding_max(left_new), sounding_max(right_new)
    if left_max is not None and right_max is not None:
        top_hand: str | None = LEFT if left_max > right_max else RIGHT
    elif left_max is not None or right_max is not None:
        only = LEFT if left_max is not None else RIGHT
        # A lone sounding hand only claims the top role if nothing else is remembered.
        top_hand = prev.top_hand or only
    else:
        top_hand = prev.top_hand
    if prev.top_hand is not None and top_hand is not None and top_hand != prev.top_hand:
        _add(acc, "role", 1.0)

    # --- unnecessary handover in time ---------------------------------------------------
    # "If a passage can be played by one hand, use one hand." Charged only when the hand
    # that played the previous group could physically have taken these notes too.
    for hand in HANDS:
        struck = [event.midi for event in per_hand[hand]]
        if not struck:
            continue
        other = LEFT if hand == RIGHT else RIGHT
        this_state, other_state = prev.hand(hand), prev.hand(other)
        if other_state.last_time <= this_state.last_time + 1e-9:
            continue  # the other hand was not the most recent player
        if other_state.center is None:
            continue
        merged = sorted(set(struck) | {event.midi for event in per_hand[other]})
        if len(merged) > model.max_simultaneous:
            continue
        if merged[-1] - merged[0] > model.comfort_span:
            continue
        relocation = available_time(other_state, time, model)
        if abs(_center(tuple(merged)) - other_state.center) <= model.free_speed * relocation:
            _add(acc, "handoff", 1.0)
            reasons.append("avoids an unnecessary handover: one hand could continue")

    # --- unnecessary two-hand use ---------------------------------------------------------
    # Charged only for SMALL groups (<= 3 notes). For thicker groups, splitting is a load
    # decision handled by `balance`, not a fault. Groups whose notes have clearly different
    # durations are LAYERED VOICES (a held voice against a moving one) and are natural to
    # divide between hands, so they are exempt.
    durations = [event.duration_frames for event in events]
    heterogeneous = bool(durations) and max(durations) > 1.5 * max(1, min(durations))
    continued_doubling = (
        len(events) == 2
        and events[1].midi - events[0].midi == 12
        and assignment[0] != assignment[1]
        and prev.octave_doubling
    )
    if lefts and rights and not heterogeneous and not continued_doubling and len(events) <= 3:
        total_span = max(events[-1].midi - events[0].midi, 0)
        if total_span <= model.comfort_span:
            _add(acc, "split", 1.0)
            reasons.append("one hand could have taken the whole group")
        elif total_span <= model.comfort_span + 2:
            _add(acc, "split", 0.5)

    # --- hand-load balance -----------------------------------------------------------------
    size = len(events)
    if size >= 4:
        n_left, n_right = len(lefts), len(rights)
        group_span = events[-1].midi - events[0].midi
        if (
            n_left
            and n_right
            and (
                size >= model.balance_min_group
                or (group_span <= model.comfort_span and not heterogeneous)
            )
        ):
            # Evenness with a one-note allowance for the right hand, applied to big
            # groups and to compact blocks. This is what makes a six-note chord split
            # 3/3 rather than 2/4.
            uneven = max(0, abs(n_right - n_left) - 1)
            if uneven:
                _add(acc, "balance", uneven / size)
        elif (n_left == 0) != (n_right == 0):
            # One hand takes a thick group entirely while the other strikes nothing:
            # grip strain, but only when the idle hand is actually free to help rather
            # than pinned by its own sounding notes.
            taker = LEFT if n_left else RIGHT
            other_state = prev.hand(RIGHT if n_left else LEFT)
            if not other_state.active_held(time):
                strain = model.balance_strain * (size - 3)
                _add(acc, "balance", strain)
                if strain >= 0.3:
                    reasons.append(f"{taker}: repeated thick grip while the other hand is free")

    # --- right-hand dominance (weak) ---------------------------------------------------------
    # Fires only when the LEFT hand plays a group ALONE although the right hand was free: an
    # unclaimed middle/high passage defaults to the dominant hand. Mixed groups are a
    # split-point decision, not a dominance decision, and are never charged — charging them
    # per note was tried in the PoC and systematically biased split points downward.
    if lefts and not rights and not prev.right.active_held(time):
        high_lefts = sum(1 for midi in lefts if midi >= model.dominance_boundary)
        if high_lefts:
            _add(acc, "dominance", high_lefts / len(events))

    cost = CostBreakdown(**acc)
    new_pair = PairState(
        left=left_new,
        right=right_new,
        top_hand=top_hand,
        crossed_since=crossed_since,
        octave_doubling=bool(octave_splits),
    )
    return TransitionResult(
        state=new_pair,
        breakdown=cost,
        cost=cost.weighted_total(weights),
        reasons=tuple(dict.fromkeys(reasons)),
    )


def _count_inversions(assignment: tuple[str, ...]) -> int:
    """Pairs ``i < j`` where a right-hand note sits below a left-hand one.

    One pass carrying the running count of right-hand notes seen: the naive
    double loop is O(k^2), and a thick chord makes that the hottest code in the
    whole search.
    """
    seen_right = 0
    inversions = 0
    for hand in assignment:
        if hand == RIGHT:
            seen_right += 1
        elif seen_right:
            inversions += seen_right
    return inversions


def _closest_inversion(lefts: list[int], rights: list[int]) -> int | None:
    """Smallest ``left - right >= 0`` across the two hands, or ``None``.

    How close the hands come while inverted, which is what makes a crossing
    physically awkward. Sorting and walking both sequences once replaces the
    all-pairs scan.
    """
    ordered_rights = sorted(rights)
    best: int | None = None
    for left in sorted(lefts):
        # Rightmost right-hand note at or below this left-hand note.
        low, high = 0, len(ordered_rights)
        while low < high:
            middle = (low + high) // 2
            if ordered_rights[middle] <= left:
                low = middle + 1
            else:
                high = middle
        if low:
            gap = left - ordered_rights[low - 1]
            if best is None or gap < best:
                best = gap
                if best == 0:
                    return 0
    return best


def _voice_candidates(state: HandState, time: float, model: HandModel) -> list[int]:
    """Pitches this hand was recently carrying, sorted.

    Looks at the last **two** onset groups of the hand (each within the voice
    window), so a figure whose halves alternate — a stride bass under its own
    chords, an ostinato woven around accents — still counts as one remembered
    voice. One group of memory silently disabled this term on exactly the
    textures it was written for.
    """
    candidates: list[int] = []
    if state.last_time > NEVER / 2 and (time - state.last_time) <= model.voice_window:
        candidates += list(state.notes)
        candidates += [held_midi for held_midi, _ in state.held]
    if state.prev_time > NEVER / 2 and (time - state.prev_time) <= model.voice_window:
        candidates += list(state.prev_notes)
    return sorted(candidates)


def _nearest_distance(candidates: list[int], midi: int) -> float:
    """Distance from ``midi`` to the closest remembered pitch, or infinity."""
    if not candidates:
        return float("inf")
    position = bisect_left(candidates, midi)
    best = float("inf")
    if position < len(candidates):
        best = float(candidates[position] - midi)
    if position:
        best = min(best, float(midi - candidates[position - 1]))
    return best


def _voice_distance(state: HandState, midi: int, time: float, model: HandModel) -> float:
    """Convenience wrapper for one lookup. The hot path hoists the two steps."""
    return _nearest_distance(_voice_candidates(state, time, model), midi)


__all__ = [
    "HANDS",
    "LEFT",
    "NEVER",
    "RIGHT",
    "CostBreakdown",
    "HandState",
    "PairState",
    "TransitionResult",
    "available_time",
    "transition",
]
