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
    #: One of :data:`aitu_backend.hands.infer.METHODS`.
    method: str = "beam"
    #: Promote a ``-1`` with no preceding onset to an onset instead of dropping it.
    #: Transcription output is imperfect; deleting data silently is worse.
    promote_orphan_sustains: bool = True

    def with_weights(self, **kwargs: float) -> "HandInferenceConfig":
        """A copy with some weights replaced (ablations, per-piece preferences)."""
        return replace(self, weights=replace(self.weights, **kwargs))

    def with_hand(self, **kwargs: Any) -> "HandInferenceConfig":
        """A copy with hand parameters replaced, e.g. a smaller ``hard_span``."""
        return replace(self, hand=replace(self.hand, **kwargs))

    def with_search(self, **kwargs: Any) -> "HandInferenceConfig":
        """A copy with search limits replaced — the quality/latency dial."""
        return replace(self, search=replace(self.search, **kwargs))

    def with_method(self, method: str) -> "HandInferenceConfig":
        return replace(self, method=method)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


#: The settings the PoC recommends shipping. Callers that do not care pass nothing.
DEFAULT_CONFIG = HandInferenceConfig()

__all__ = [
    "DEFAULT_CONFIG",
    "CostWeights",
    "HandInferenceConfig",
    "HandModel",
    "RelocationMode",
    "SearchConfig",
]
