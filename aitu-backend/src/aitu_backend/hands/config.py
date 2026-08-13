"""Configuration of the cost model and the search.

Two kinds of number live here and they are deliberately kept apart:

* :class:`CostWeights` — dimensionless multipliers. Setting one to ``0.0``
  removes that term, which is how the PoC ran its ablations.
* :class:`HandModel` — the physical hand: semitones and seconds. An ablation
  must never accidentally change what a hand can reach.

The defaults are the PoC's shipped v3 settings (``reports/final-recommendation.md``
§5, updated by ``implementation/CHANGELOG.md`` v3). ``movement``, ``voice``,
``free_speed`` and ``pitch_prior`` were tuned by coordinate descent on the
development split only; every other value is hand-set from ergonomic reasoning.
Do not "improve" one by eye — they interact, and the benchmark is the only
honest judge.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from typing import Any, Literal

#: How a hand's available relocation time is measured.
#:
#: ``release_aware`` — a hand cannot move while its assigned keys are still
#: sounding. ``onset_gap`` — a long interval between onsets grants preparation
#: time regardless of sustains. The matrix carries no pedal data, so neither is
#: provably right; the PoC benchmarked ``release_aware`` as better and the
#: ambiguity is documented rather than hidden.
RelocationMode = Literal["release_aware", "onset_gap"]


@dataclass(frozen=True)
class CostWeights:
    """Multipliers of the named cost components (dimensionless)."""

    span: float = 1.0
    capacity: float = 1.0
    #: Tuned on the dev split (was 1.0).
    movement: float = 0.50
    acceleration: float = 0.10
    crossing: float = 0.60
    #: Escalating cost of *remaining* crossed: a crossing is an ornament, not a posture.
    crossdur: float = 0.80
    interleaving: float = 0.50
    #: Tuned on the dev split (was 0.8). The largest single term.
    voice: float = 1.50
    role: float = 0.30
    #: Tuned on the dev split (was 0.08). Absolute pitch is only a weak prior.
    pitch_prior: float = 0.10
    #: Ledger lines, **inside the search**: zero, deliberately.
    #:
    #: This term used to run here at 0.50 and it was a regression. Measured over the
    #: 209-scenario research benchmark, an in-search ledger charge moved 49 onsets
    #: away from the human labels against 34 towards, taking onset accuracy from
    #: 0.9546 to 0.9506. The reason is not the geometry, it is the placement: a
    #: group-by-group dynamic program that cares about the page will rewrite whole
    #: textures to tidy one chord, and on the alternating-triad toccata it swaps the
    #: upper voice as readily as the lower one.
    #:
    #: The term is not gone. It moved to :class:`RefineConfig`, where a second pass
    #: proposes only the moves that could fix a specific ledger problem and accepts
    #: only those that measurably do. Same geometry, same weight scale, twenty times
    #: less collateral: 38 onsets towards the labels against 1 away, 0.9546 -> 0.9646.
    #:
    #: Raise it here only to reproduce the old behaviour or to ablate.
    ledger: float = 0.0
    octave: float = 0.50
    split: float = 0.60
    #: Hand-load balance for thick groups.
    balance: float = 0.40
    #: Weak right-hand default above the dominance boundary.
    dominance: float = 0.04
    #: Striking while the same hand holds another sounding voice.
    polyphony: float = 0.20
    engagement: float = 0.25
    handoff: float = 0.50
    future: float = 0.0


@dataclass(frozen=True)
class HandModel:
    """Physical and ergonomic parameters of one hand. Semitones and seconds."""

    #: An octave is comfortable for most adult hands.
    comfort_span: float = 12.0
    #: Beyond this a simultaneous group is declared infeasible, not merely costly.
    hard_span: float = 15.0
    span_curve: float = 0.75
    #: Five fingers, five distinct struck keys.
    max_simultaneous: int = 5
    #: Semitones per second that cost no movement penalty (v3, tuned on dev).
    free_speed: float = 26.0
    movement_power: float = 2.0
    #: Seconds; avoids division-like blow-ups at 0.
    min_available_time: float = 0.02
    #: An exact octave is a natural one-hand shape (fingers 1 and 5), so it is rewarded.
    octave_together_bonus: float = 0.30
    crossing_base: float = 0.30
    #: Semitones below which an inverted pair is a real collision rather than a reach-over.
    collision_margin: float = 8.0
    #: Held notes constrain the hand only softly — there is no pedal data.
    sustain_span_weight: float = 0.35
    #: Do-4 / C4. The old threshold rule, demoted to a weak prior.
    pitch_prior_center: float = 60.0
    #: Ledger lines a hand may run past its **own** side of its staff for free —
    #: the left below the bass staff, the right above the treble staff. Six,
    #: because the bottom octave of the piano is six ledger lines under the bass
    #: staff and the top of a melody is routinely five over the treble. This is
    #: register, not a mistake, and charging it would bias every split inwards.
    ledger_grace_outward: float = 6.0
    #: Ledger lines a hand may run **across** its staff for free — the left above
    #: the bass staff, the right below the treble staff. Two, which reaches Fa-4
    #: in the bass and Sol-3 in the treble: the shared middle register both hands
    #: write in every day. Past that the charge starts, gently at first — three
    #: lines is worth 0.08 — so an ordinary chord that dips a little below the
    #: treble is nudged, not overruled.
    #:
    #: Note this is a **grace, not a limit**. The term is one cost among
    #: eighteen; a passage the hands genuinely have to play across the staves
    #: still gets played that way, and prints with its ledger lines.
    ledger_grace_across: float = 2.0
    #: Ledger lines beyond the grace that count as one unit of trouble. The cost
    #: is quadratic in the excess divided by this, so a hand two lines past the
    #: grace is a nudge (0.64) and one six lines past is a verdict (5.76).
    ledger_reference: float = 2.5
    #: Whether the ``across`` charge is gated on the other hand's availability.
    #: Off reproduces the ungated term, which the benchmark says costs accuracy.
    ledger_gate: bool = True
    #: The other hand strikes nothing and holds nothing: its staff is empty and this
    #: note is simply on the wrong one. Full charge.
    ledger_gate_free: float = 1.0
    #: The other hand is playing but could still physically absorb these notes.
    #:
    #: Zero, which is stronger than it sounds: it means the term says nothing at all
    #: unless the other staff is empty. That is not timidity, it is what the labels
    #: show. Human engravers write 129 onsets three or more ledger lines across on
    #: this benchmark, and 116 of them are while the other hand is busy — every one
    #: a passage where somebody had to play those notes. What they essentially never
    #: write is a hand four lines across while the other staff sits empty: zero
    #: cases, against fourteen produced by the ungated search. Any value above zero
    #: here starts arguing with the 116.
    ledger_gate_busy: float = 0.0
    #: The other hand cannot take them because of the keys it is *striking now*.
    #: Nothing to decide, so nothing to charge — and, importantly, no constant left
    #: behind to skew the rest of the group.
    ledger_gate_unreachable: float = 0.0
    #: The other hand cannot take them because of what it is still *holding*.
    #:
    #: Full charge, unlike the struck case, because a sustain is a consequence of an
    #: earlier decision and may be the mistake itself. The closing cadence of *Mr Blue
    #: Sky* is exactly this: the right hand is pinned under sustains it did not have to
    #: take, so the ascent prints on the bass staff under seven ledger lines, and a gate
    #: that treats "holding" like "striking" reports nothing wrong. A genuine crossing
    #: over a chord the other hand really is holding is still safe: moving into it is
    #: infeasible, and the pass rejects infeasible moves outright.
    ledger_gate_sustained: float = 1.0
    #: Seconds of memory for voice continuity.
    voice_window: float = 1.20
    #: Semitones considered "the same voice".
    voice_tolerance: float = 4.0
    #: Seconds of idleness after which re-engaging a hand costs.
    engagement_gap: float = 1.50
    relocation_mode: RelocationMode = "release_aware"
    #: Seconds a crossing may last before the duration cost starts.
    crossdur_grace: float = 0.60
    #: Seconds of crossed time worth one unit of cost.
    crossdur_ref: float = 1.00
    #: Do-4; left-hand notes at or above this pay ``C_dominance``.
    dominance_boundary: float = 60.0
    #: Per struck note beyond three in one hand while the other idles.
    balance_strain: float = 0.30
    balance_min_group: int = 6
    #: In-place reach: no relocation charged if previous and new notes fit one span.
    reach_slack: bool = True
    #: Under ``release_aware``, a struck note beyond the hard span from a held note
    #: is unreachable — the fingers are physically down.
    held_span_hard: bool = True


@dataclass(frozen=True)
class FigureModel:
    """What counts as an accompaniment figuration.

    A figuration is not a repeated tune. Chopin's left hand climbs, Schubert's changes
    its bass note every bar, a nocturne's spreads and contracts. What repeats is the
    **shape**, and engravers make it visible by breaking the beam at the bottom of each
    turn — which is also the most reliable way to find one.

    Detection matters to the split because a figure is one hand's gesture. Handing one
    of its notes to the other hand leaves a hole in a beam group the reader is using to
    follow the pulse, and the group-by-group search has no way to notice that the notes
    it is dividing are the fourth turn of something it already assigned three times.
    """

    #: Slots per turn to consider.
    min_period: int = 2
    max_period: int = 8
    #: Two turns of a shape is a coincidence; three is a figure.
    min_cycles: int = 3
    #: Total notes a figure must contain, applied after the period is chosen — so a
    #: two-slot figure needs six turns to earn the name and a six-slot figure needs three.
    min_onsets: int = 12
    #: Semitones a note may differ from its counterpart in the previous turn, measured
    #: relative to each turn's own lowest note. Three lets a broken triad become a
    #: broken seventh without the figure being declared broken — and measuring against
    #: each turn's own anchor is what lets the harmony move underneath.
    shape_tolerance: float = 3.0
    #: Relative tolerance on the note spacing.
    ioi_tolerance: float = 0.18
    #: Empty grid slots tolerated in a row before the run is cut in two.
    max_gap_slots: int = 2
    #: A stream holier than this is debris, not a figure.
    max_gap_fraction: float = 0.30
    #: Semitones one turn's anchor may move from the last.
    max_anchor_drift: int = 12
    #: Fraction of comparable (turn, phase) pairs that must agree on the shape.
    min_match: float = 0.75
    #: Fraction of turns whose lowest note falls at the same phase — the beam break,
    #: used as a test. Without it almost any melody passes as a two-slot figure: a line
    #: that rises and falls by a few semitones "repeats" once each turn is measured from
    #: its own anchor. What a melody does not do is turn around at the same place every
    #: time. This single criterion removes most of the false positives.
    min_anchor_consistency: float = 0.75
    #: Fraction of consecutive turn-pairs whose pitch ranges must overlap — what
    #: separates a figuration from a scale. Both repeat a shape and both can climb, but
    #: a scale's turns tile end to end while a figuration's sit on top of each other.
    #: Runs are meant to be shared between the hands, so they must not be protected.
    min_cycle_overlap: float = 0.6
    #: Semitones between the highest and lowest note of a turn. Excludes trills.
    min_cycle_span: int = 3
    #: Figurations are essentially monophonic. A slot may carry a dyad — a pedal note
    #: under the pattern — but a mostly chordal stream is an accompaniment block.
    max_chordal_fraction: float = 0.34
    #: How close a note belonging to the *other* hand must sit to the contour's
    #: prediction before it counts as part of this figure. The mechanism that recovers
    #: a note the search took away.
    absorb_tolerance: float = 3.0
    #: Also look for figures in both hands' notes merged together.
    #:
    #: Off. It recovers one real blind spot — a figure divided roughly in half is a
    #: minority of both streams, so neither is complete enough to recognise — but the
    #: merged stream of a two-voice invention is indistinguishable from a figuration,
    #: and switching this on invents one. Turn it on only with a corpus that shows the
    #: trade is worth it.
    merged_stream: bool = False
    #: Below this confidence a figure is detected but gets no vote.
    min_confidence: float = 0.35


@dataclass(frozen=True)
class PatternWeights:
    """How badly a hand assignment cutting across a figuration counts."""

    #: Notes whose hand differs from the settled hand *of their own phase*. The real
    #: defect: the figure wobbling between hands mid-flight.
    broken: float = 1.0
    #: The figure uses both hands at all, scaled by how lopsided the split is. Weaker,
    #: because some figures are genuinely shared — a broken chord whose top note is the
    #: melody — and the phase term already leaves those alone.
    split: float = 0.35
    #: Hand changes between consecutive notes of the figure. Tells one clean handover
    #: apart from the same number of notes scattered.
    switch: float = 0.50


@dataclass(frozen=True)
class RefineConfig:
    """The second pass: two page-level defects, one objective.

    The search minimizes what the *hands* can do. Two things it cannot see are what the
    result looks like on paper — a hand parked four ledger lines onto the other staff —
    and whether it has cut a repeating figure in half. Both are cheap to detect after
    the fact and expensive to express inside a group-by-group dynamic program, so they
    are repaired here instead, by proposing a small set of targeted moves and keeping
    only those that measurably help.

    The two rules disagree by construction, and that is the point of putting them in one
    pass. The register rule wants a left hand above the bass staff moved up; a figure
    that climbed there wants to be left alone. A note inside a confident figure, held by
    that figure's owner, is *explained* — so its ledger charge is relieved, and the
    argument is settled inside the objective rather than by which pass ran last.
    """

    enabled: bool = True
    #: Ledger weight used by this pass. Zero here and in :class:`CostWeights` disables
    #: register repair entirely. 6.25 with ``ledger_reference = 2.5`` makes one ledger
    #: line past the grace cost 1.0 — twelve times the old in-search weight, which the
    #: benchmark shows is where the term starts paying for itself. The plateau is broad:
    #: 6.0 scores 0.9633 and 12.5 scores 0.9646, against 0.9546 for no term at all.
    ledger_weight: float = 6.25
    #: Weight on the figuration term.
    pattern_weight: float = 5.0
    #: Multiplier on the register charge for a note inside a figure its own hand owns.
    #: Zero forgives it completely: the pattern has already explained why the note is
    #: out of clef. Relief is denied to notes the *other* hand holds — their ledger
    #: lines are not the pattern's fault and should still argue for putting them back.
    pattern_ledger_relief: float = 0.0
    #: Flag a note when its across-ledger count exceeds ``ledger_grace_across`` by this.
    flag_slack: int = 1
    #: Flagged groups no further apart than this form one run.
    run_gap: int = 2
    #: When building a run, absorb adjacent groups within this many lines of the flag.
    shoulder_slack: int = 1
    #: Groups either side of a hotspot for the windowed re-solve.
    window_pad: int = 2
    max_windows: int = 24
    #: The windowed re-solve buys little — two accepted moves across 209 scenarios —
    #: and costs a fifth of the pass's runtime. On by default because it is the only
    #: move that can restructure rather than relocate; turn it off for speed.
    window_resolve: bool = True
    #: Reject any move that adds a span, capacity, crossing or feasibility violation,
    #: however much it improves the objective. It has never yet fired on the benchmark,
    #: which is the argument for keeping it: it costs nothing and it is what stops a
    #: future weight change from producing something unplayable.
    physical_guard: bool = True
    #: Each family of moves may only ever improve its own term.
    #:
    #: Without this the pass stops being a repair and becomes a second general-purpose
    #: optimizer. On the alternating-triad toccata it found a fifteen-onset move worth
    #: 6.7 of ergonomic cost that made the *page worse* and destroyed the hand
    #: alternation the labels ask for. Re-optimizing J is the beam's job.
    require_own_gain: bool = True
    #: In a group one hand plays outright, cut at the clef boundary rather than at the
    #: flag threshold. A rising triad stranded below the treble staff travels whole; an
    #: octave doubling that straddles the gap is split, one voice per staff.
    clef_cut_single_hand_groups: bool = True
    #: Repair figures before register problems. A figure put back in one hand often
    #: clears the register flag by itself, and where it does not, the relief it earns
    #: is what tells the register half to leave those notes alone.
    pattern_first: bool = True
    max_rounds: int = 3
    #: Wall-clock ceiling. The pass is bounded by construction; this bounds it in time.
    time_budget_s: float = 8.0
    patterns: PatternWeights = field(default_factory=PatternWeights)


@dataclass(frozen=True)
class SearchConfig:
    """Search limits for candidate generation and the beam."""

    #: Benchmark quality plateaus at 8; a synthetic three-minute piece still improves
    #: marginally up to 24. 12 keeps the plateau at roughly half the runtime of 24.
    beam_width: int = 12
    #: Max partitions kept per onset group.
    candidate_limit: int = 12
    #: Exhaustive 2^k below this group size, contiguous splits above.
    enumerate_max_notes: int = 6
    #: Groups used by the pruning heuristic.
    lookahead_groups: int = 1
    max_states_expanded: int = 2_000_000


@dataclass(frozen=True)
class HandInferenceConfig:
    """Top-level configuration passed to :func:`aitu_backend.hands.infer_hands`."""

    weights: CostWeights = field(default_factory=CostWeights)
    hand: HandModel = field(default_factory=HandModel)
    search: SearchConfig = field(default_factory=SearchConfig)
    figures: FigureModel = field(default_factory=FigureModel)
    refine: RefineConfig = field(default_factory=RefineConfig)
    #: One of :data:`aitu_backend.hands.infer.METHODS`.
    method: str = "refine"
    #: Promote a ``-1`` with no preceding onset to an onset instead of dropping it.
    #: Transcription output is imperfect; deleting data silently is worse.
    promote_orphan_sustains: bool = True

    def with_weights(self, **kwargs: float) -> HandInferenceConfig:
        """A copy with some weights replaced (ablations, per-piece preferences)."""
        return replace(self, weights=replace(self.weights, **kwargs))

    def with_hand(self, **kwargs: Any) -> HandInferenceConfig:
        """A copy with hand parameters replaced, e.g. a smaller ``hard_span``."""
        return replace(self, hand=replace(self.hand, **kwargs))

    def with_search(self, **kwargs: Any) -> HandInferenceConfig:
        """A copy with search limits replaced — the quality/latency dial."""
        return replace(self, search=replace(self.search, **kwargs))

    def with_figures(self, **kwargs: Any) -> HandInferenceConfig:
        """A copy with figuration-detection parameters replaced."""
        return replace(self, figures=replace(self.figures, **kwargs))

    def with_refine(self, **kwargs: Any) -> HandInferenceConfig:
        """A copy with second-pass settings replaced, e.g. ``enabled=False``."""
        return replace(self, refine=replace(self.refine, **kwargs))

    def with_method(self, method: str) -> HandInferenceConfig:
        return replace(self, method=method)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


#: The settings the PoC recommends shipping. Callers that do not care pass nothing.
DEFAULT_CONFIG = HandInferenceConfig()

__all__ = [
    "DEFAULT_CONFIG",
    "CostWeights",
    "FigureModel",
    "HandInferenceConfig",
    "HandModel",
    "PatternWeights",
    "RefineConfig",
    "RelocationMode",
    "SearchConfig",
]
