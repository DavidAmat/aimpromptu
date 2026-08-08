"""What an inference run returns: assignments, diagnostics, split matrices.

Two audiences, one object:

* **The pipeline** wants ``right`` and ``left`` matrices and the compact
  ``hand_map`` string. That is all it takes to render a grand staff, color a
  piano roll and persist the decision.
* **A human deciding whether the model is wrong** wants the per-onset cost
  breakdown, the reasons, the confidence and the warnings.

The second is not decoration. A split that cannot be interrogated is one that
gets argued about instead of fixed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np

from aitu_backend.hands.encoding import encode_hand_map
from aitu_backend.hands.events import DecodedMatrix, split_grids
from aitu_backend.schemas.matrix import Hand, MatrixProcessingStep

#: Bumped when the shape of the persisted hand metadata changes.
SCHEMA_VERSION = "1.0"

#: Below this confidence an onset is counted as ambiguous. It is a review-queue
#: threshold, not a correctness claim — see :attr:`Assignment.confidence`.
AMBIGUOUS_BELOW = 0.30


@dataclass
class Assignment:
    """One onset, its hand, and why."""

    onset_id: str
    row: int
    midi: int
    note: str
    column: int
    time_seconds: float
    duration_frames: int
    hand: str
    #: **Not a probability.** ``1 - exp(-margin / 0.5)``, where ``margin`` is how
    #: much more the cheapest *local* alternative that flips this note would cost
    #: from the same predecessor state. It ignores downstream consequences and has
    #: never been calibrated against human corrections. Safe: sorting a review
    #: queue, highlighting close calls. Unsafe: thresholding for auto-acceptance,
    #: showing a user a percentage, comparing across pieces.
    confidence: float
    cost_breakdown: dict[str, float] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)

    def to_wire(self) -> dict[str, Any]:
        return {
            "onsetId": self.onset_id,
            "row": self.row,
            "midi": self.midi,
            "note": self.note,
            "column": self.column,
            "timeSeconds": round(self.time_seconds, 6),
            "durationFrames": self.duration_frames,
            "hand": self.hand,
            "confidence": round(self.confidence, 4),
            "costBreakdown": {
                name: round(value, 5) for name, value in self.cost_breakdown.items() if value
            },
            "reasons": self.reasons,
        }


@dataclass
class Diagnostics:
    """Runtime and search diagnostics for one run."""

    total_cost: float = 0.0
    runtime_ms: float = 0.0
    states_expanded: int = 0
    states_pruned: int = 0
    ambiguous_onsets: int = 0
    onset_groups: int = 0
    onsets: int = 0
    avg_candidates: float = 0.0
    max_candidates: int = 0
    #: Groups with no physically plausible partition. Non-zero means the matrix
    #: asks for something unplayable; the warnings say where.
    infeasible_groups: int = 0
    extra: dict[str, Any] = field(default_factory=dict)

    def to_wire(self) -> dict[str, Any]:
        data = asdict(self)
        extra = data.pop("extra")
        wire: dict[str, Any] = {
            _camel(name): (round(value, 4) if isinstance(value, float) else value)
            for name, value in data.items()
        }
        wire.update(extra)
        return wire


def _camel(name: str) -> str:
    head, *rest = name.split("_")
    return head + "".join(part.title() for part in rest)


@dataclass
class HandInferenceResult:
    """Everything a caller needs from one inference run."""

    method: str
    assignments: list[Assignment]
    diagnostics: Diagnostics
    #: Aligned full-size ``88 x N`` grids. Disjoint, and they recombine exactly.
    right_grid: np.ndarray
    left_grid: np.ndarray
    #: Onset ids in canonical ``(column, row)`` order — what ``hand_map`` indexes.
    onset_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION
    config_used: dict[str, Any] = field(default_factory=dict)

    def hand_of(self) -> dict[str, str]:
        """``onset_id -> "left" | "right"``."""
        return {item.onset_id: item.hand for item in self.assignments}

    @property
    def hand_map(self) -> str:
        """The compact ``"rrlrl…"`` string that travels in metadata."""
        return encode_hand_map(self.onset_ids, self.hand_of())

    def ambiguous(self) -> list[Assignment]:
        """Assignments worth a human glance, lowest confidence first."""
        close = [item for item in self.assignments if item.confidence < AMBIGUOUS_BELOW]
        return sorted(close, key=lambda item: item.confidence)

    def to_matrices(self, source: "Any") -> tuple[Any, Any]:
        """Wrap the grids as ``PianoMatrix`` objects carrying ``source``'s metadata."""
        common = {"processing_step": MatrixProcessingStep.TWO_HANDS}
        return (
            source.with_grid(self.right_grid, hand=Hand.RIGHT.value, **common),
            source.with_grid(self.left_grid, hand=Hand.LEFT.value, **common),
        )

    def to_wire(self) -> dict[str, Any]:
        """Full diagnostic payload. The matrices are *not* included — they travel
        as matrices, and duplicating them here would double every response."""
        return {
            "schemaVersion": self.schema_version,
            "method": self.method,
            "handMap": self.hand_map,
            "assignments": [item.to_wire() for item in self.assignments],
            "diagnostics": self.diagnostics.to_wire(),
            "warnings": self.warnings,
        }


def build_result(
    *,
    method: str,
    decoded: DecodedMatrix,
    assignments: list[Assignment],
    diagnostics: Diagnostics,
    warnings: list[str],
    config_used: dict[str, Any] | None = None,
) -> HandInferenceResult:
    """Assemble a result and paint the aligned split grids."""
    hand_map = {item.onset_id: item.hand for item in assignments}
    right_grid, left_grid = split_grids(decoded, hand_map)
    diagnostics.onsets = len(assignments)
    diagnostics.onset_groups = len(decoded.groups)
    diagnostics.ambiguous_onsets = sum(
        1 for item in assignments if item.confidence < AMBIGUOUS_BELOW
    )
    return HandInferenceResult(
        method=method,
        assignments=assignments,
        diagnostics=diagnostics,
        right_grid=right_grid,
        left_grid=left_grid,
        onset_ids=decoded.onset_ids,
        warnings=warnings,
        config_used=config_used or {},
    )


__all__ = [
    "AMBIGUOUS_BELOW",
    "SCHEMA_VERSION",
    "Assignment",
    "Diagnostics",
    "HandInferenceResult",
    "build_result",
]
