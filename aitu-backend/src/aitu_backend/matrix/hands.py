"""Appendix D: split a matrix into a right hand and a left hand.

**This no longer splits at middle C.** The default is the beam dynamic program
in :mod:`aitu_backend.hands`, which allocates each onset to a hand by minimizing
a named ergonomic objective over time. The old ``Do-4`` rule is still reachable
as ``method="threshold"`` for speed and debugging.

Why the rule had to go. A fixed pitch boundary reads a note's register as a
decision when it is only evidence. It cannot express a hand crossing, a left
hand jumping into the middle register under a stable melody, a melody that dips
below middle C without changing hands, or an octave played by fingers 1 and 5 —
all of which are ordinary piano writing. On the research benchmark the threshold
scored 0.848 onset accuracy to the beam's 0.955, but the damning number is
structural: it produced 21 physically impossible hand spans, notes no hand could
actually reach together.

Splitting **never cuts**. Both outputs are full ``88 x N`` matrices, exact
partitions of the clean matrix, so the two stay frame-aligned when rendered one
above the other — which the notation contract requires (``r_matrix`` and
``l_matrix`` must have equal ``shape[1]``) and which the piano-roll views rely on
to color a note by its hand.

Downstream default clefs: right = treble, left = bass.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from aitu_backend.hands import DEFAULT_CONFIG, HandInferenceConfig, HandInferenceResult, infer_hands
from aitu_backend.hands.events import decode_matrix, split_grids
from aitu_backend.matrix.keys import MIDDLE_C_ROW, note_to_row
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.schemas.matrix import ONSET, Granularity, Hand, MatrixProcessingStep
from aitu_backend.schemas.metadata import HandAssignments

#: Row at and above which the *threshold* method puts a note in the right hand.
#: ``Do-4`` = middle C. Kept for the baseline only.
DEFAULT_SPLIT_ROW = MIDDLE_C_ROW

#: What ``split_hands`` does when nobody says otherwise.
DEFAULT_METHOD = "beam"


@dataclass(frozen=True)
class TwoHands:
    """The result of a split: two aligned, full-size matrices.

    ``inference`` is present for every method except the plain pitch threshold
    invoked through :func:`split_hands_at_row`; it carries the per-onset hands,
    costs, confidences and warnings that make a split reviewable.
    """

    right: PianoMatrix
    left: PianoMatrix
    #: Only meaningful for the threshold method; ``None`` for inferred splits.
    split_row: int | None = None
    inference: HandInferenceResult | None = None

    @property
    def frame_count(self) -> int:
        return self.right.frame_count

    @property
    def method(self) -> str:
        return self.inference.method if self.inference else "threshold-row"

    def combined(self) -> PianoMatrix:
        """Merge the hands back into one matrix.

        Exact for any :class:`TwoHands` this module produces: the split
        partitions the cells, so no cell is non-zero in both hands.
        """
        grid = np.where(self.right.grid != 0, self.right.grid, self.left.grid)
        return self.right.with_grid(grid, hand=None, processing_step=MatrixProcessingStep.CLEAN)

    def hand_map(self) -> str | None:
        """The compact ``"rrlrl…"`` string, or ``None`` for a threshold-row split.

        Read off **these two grids**, in canonical ``(column, row)`` order, not
        copied from ``inference.hand_map``. Those two agree whenever the hands
        were inferred from the very matrix being returned — but the pipeline now
        infers at the raw granularity and persists the collapsed hands, and two
        onsets that collapse into one column would leave the inferred string one
        character too long and every hand after it off by one. The grids are the
        thing being served, so the grids are what the map has to describe.
        """
        if self.inference is None:
            return None
        right, left = self.right.grid, self.left.grid
        onsets = np.nonzero(((right == ONSET) | (left == ONSET)).T)  # (column, row) order
        return "".join(
            "r" if right[row, column] == ONSET else "l"
            for column, row in zip(*onsets, strict=True)
        )

    def to_metadata(self) -> HandAssignments | None:
        """The metadata block to persist alongside the matrix.

        ``None`` when the split carries no inference (the raw row threshold),
        because writing a hand map without the identity fields that validate it
        would create something a consumer cannot safely trust.
        """
        if self.inference is None:
            return None
        diagnostics = self.inference.diagnostics
        hand_map = self.hand_map() or ""
        return HandAssignments(
            method=self.inference.method,
            hand_map=hand_map,
            onset_count=len(hand_map),
            granularity=Granularity(self.right.granularity),
            frame_count=self.right.frame_count,
            ambiguous_onsets=diagnostics.ambiguous_onsets,
            infeasible_groups=diagnostics.infeasible_groups,
            warnings=list(self.inference.warnings),
        )


def resolve_split_row(threshold: int | str = DEFAULT_SPLIT_ROW) -> int:
    """Accept a row index or a note name (``"Do-4"``) as the threshold."""
    return note_to_row(threshold) if isinstance(threshold, str) else threshold


def split_hands(
    matrix: PianoMatrix,
    config: HandInferenceConfig | None = None,
    *,
    method: str | None = None,
    infer_from: PianoMatrix | None = None,
) -> TwoHands:
    """Assign every onset to a hand and return the two aligned matrices.

    ``method`` overrides the config's: ``"beam"`` (default), ``"greedy"``,
    ``"exact"`` or ``"threshold"``. Every sustain follows its onset, so the two
    outputs recombine to ``matrix`` exactly.

    ``infer_from`` decides the hands from a *different* matrix and paints them
    onto ``matrix``. The pipeline uses it to keep two things apart that used to be
    one: the beam's cost model is tuned and benchmarked against Appendix-B-cleaned
    sustains — its ``release_aware`` relocation reads a hand as pinned for as long
    as its keys sound — while the matrix that should actually be *rendered* still
    has its full, uncut sustains. So it infers from the cleaned view and paints the
    collapsed one. Cleaning never adds, moves or removes an onset (only sustain
    cells), so the two matrices carry identical onsets and the assignment
    transfers exactly; a mismatch is a bug and raises rather than guessing.

    Cost: roughly 0.7 s for a four-minute piece at four frames per second. This
    runs once per matrix, not once per render, and the result is persisted so the
    notation, piano-roll and falling-note views all read the same split.
    """
    config = config or DEFAULT_CONFIG
    if method is not None:
        config = config.with_method(method)

    result = infer_hands(infer_from if infer_from is not None else matrix, config)
    if infer_from is None:
        right_grid, left_grid = result.right_grid, result.left_grid
    else:
        right_grid, left_grid = _repaint(matrix, result, config)

    common = {"processing_step": MatrixProcessingStep.TWO_HANDS}
    return TwoHands(
        right=matrix.with_grid(right_grid, hand=Hand.RIGHT.value, **common),
        left=matrix.with_grid(left_grid, hand=Hand.LEFT.value, **common),
        split_row=None,
        inference=result,
    )


def _repaint(
    matrix: PianoMatrix,
    result: HandInferenceResult,
    config: HandInferenceConfig,
) -> tuple[np.ndarray, np.ndarray]:
    """Apply an assignment made elsewhere to ``matrix``'s own cells.

    Onset ids are ``c{column}:r{row}``, so they are addresses rather than
    positions: the same onset has the same id in both matrices, and the ids only
    fail to line up if the two grids genuinely disagree about what was struck.
    """
    decoded = decode_matrix(matrix, promote_orphan_sustains=config.promote_orphan_sustains)
    hand_of = result.hand_of()
    missing = [event.onset_id for event in decoded.events if event.onset_id not in hand_of]
    if missing:
        raise ValueError(
            "The matrix being split and the one the hands were inferred from do not "
            f"share their onsets: {len(missing)} unassigned, first {missing[:3]}. "
            "They must differ only in sustain cells."
        )
    return split_grids(decoded, hand_of)


def split_hands_at_row(
    matrix: PianoMatrix,
    threshold: int | str = DEFAULT_SPLIT_ROW,
) -> TwoHands:
    """The original Appendix D rule: everything at or above ``threshold`` is right.

    Pure row arithmetic, no cost model, no per-onset reasoning — which is why it
    is a baseline and not the default. Useful when a caller genuinely wants a
    pitch split (a preview, a test fixture, a comparison), and fast enough to be
    free.
    """
    split_row = resolve_split_row(threshold)
    if not 0 <= split_row <= matrix.shape[0]:
        raise ValueError(f"Split row {split_row} outside 0..{matrix.shape[0]}")

    right_grid = matrix.grid.copy()
    right_grid[:split_row, :] = 0

    left_grid = matrix.grid.copy()
    left_grid[split_row:, :] = 0

    common = {"processing_step": MatrixProcessingStep.TWO_HANDS}
    return TwoHands(
        right=matrix.with_grid(right_grid, hand=Hand.RIGHT.value, **common),
        left=matrix.with_grid(left_grid, hand=Hand.LEFT.value, **common),
        split_row=split_row,
    )


def combine_hands(right: PianoMatrix, left: PianoMatrix) -> PianoMatrix:
    """Merge two hands back into one matrix.

    Where both hands hold a value for the same cell — which cannot happen for a
    :func:`split_hands` result, but can for hand-edited matrices — the right
    hand wins.
    """
    if right.shape != left.shape:
        raise ValueError(
            f"Hands must have the same shape to combine, got {right.shape} and {left.shape}"
        )
    grid = np.where(right.grid != 0, right.grid, left.grid)
    return right.with_grid(grid, hand=None, processing_step=MatrixProcessingStep.CLEAN)


def hand_of_row(row: int, threshold: int | str = DEFAULT_SPLIT_ROW) -> Hand:
    """Which hand a row belongs to **under the threshold rule**.

    A pitch-only answer. Inferred splits are per onset, not per row: the same
    row can belong to different hands at different moments, which is the whole
    point. Use :meth:`TwoHands.hand_map` when you need the real assignment.
    """
    return Hand.RIGHT if row >= resolve_split_row(threshold) else Hand.LEFT


__all__ = [
    "DEFAULT_METHOD",
    "DEFAULT_SPLIT_ROW",
    "TwoHands",
    "combine_hands",
    "hand_of_row",
    "resolve_split_row",
    "split_hands",
    "split_hands_at_row",
]
