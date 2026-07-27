"""Move a piano matrix between temporal granularities.

Two directions, deliberately asymmetric (see ``project-features.md``,
"Collapsing temporal resolution"):

**Collapse** (fine -> coarse) merges column *pairs*, halving the column count and
doubling ``time_step_seconds`` while the BPM stays put. It runs **one hierarchy
step at a time** — semifusa -> fusa -> semicorchea -> … — because the merge rules
are only defined for adjacent steps. Merge table, applied per row::

    [1, 1]  -> 1        [0, 1]  -> 1        [-1,  0] -> -1
    [1, 0]  -> 1        [0, 0]  -> 0        [-1,  1] ->  1
    [1, -1] -> 1        [0, -1] -> impossible (the validator catches it)
                                            [-1, -1] -> -1

Read as one sentence: **an onset anywhere in the pair wins; otherwise a sustain
in the pair wins; otherwise silence.**

**Upsample** (coarse -> fine) is *not* the inverse — collapsing destroys
information irreversibly. It is a plain expansion::

    0 -> [0, 0]         1 -> [1, -1]        -1 -> [-1, -1]

Consequence, and the reason the raw fusa matrix is kept forever: to see a piece
at a coarser granularity, **always re-collapse from the stored raw matrix**,
never from a matrix that has already been through the pipeline.

Note that collapsing *itself* is associative — ``collapse_to`` always walks one
step at a time, so two chained calls give the same cells as one. What is not
recoverable is everything the later steps remove: Appendix B cleaning (Task
2.3.1) deletes sustains, and the two-hands split zeroes half the rows. Collapse
one of those and the loss compounds silently. So :func:`collapse_to` refuses a
matrix whose ``processing_step`` is anything but ``raw`` unless the caller
passes ``allow_chaining=True`` and means it.

Everything is vectorized: a reshape to pairs plus a handful of whole-array
comparisons, no Python loop over columns.
"""

from __future__ import annotations

import numpy as np

from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.progress import BaseProgress, default_reporter
from aitu_backend.schemas.matrix import (
    GRANULARITY_HIERARCHY,
    ONSET,
    SUSTAIN,
    Granularity,
    MatrixProcessingStep,
)


def hierarchy_index(granularity: Granularity | str) -> int:
    """Position in the coarse -> fine ladder; ``redonda`` is 0."""
    return GRANULARITY_HIERARCHY.index(Granularity(granularity))


def steps_between(source: Granularity | str, target: Granularity | str) -> int:
    """Signed hierarchy distance. Positive = collapse, negative = upsample."""
    return hierarchy_index(source) - hierarchy_index(target)


def is_coarser(target: Granularity | str, than: Granularity | str) -> bool:
    return hierarchy_index(target) < hierarchy_index(than)


def _one_step_coarser(granularity: Granularity) -> Granularity:
    index = hierarchy_index(granularity)
    if index == 0:
        raise ValueError(f"{granularity.value} is already the coarsest granularity")
    return GRANULARITY_HIERARCHY[index - 1]


def _one_step_finer(granularity: Granularity) -> Granularity:
    index = hierarchy_index(granularity)
    if index == len(GRANULARITY_HIERARCHY) - 1:
        raise ValueError(f"{granularity.value} is already the finest granularity")
    return GRANULARITY_HIERARCHY[index + 1]


# ------------------------------------------------------------------- collapse


def merge_pairs(grid: np.ndarray) -> np.ndarray:
    """Apply the merge table to a grid, halving its column count.

    An odd column count is padded with one silence column first, so the tail
    frame survives instead of being dropped.
    """
    rows, columns = grid.shape
    if columns % 2:
        grid = np.concatenate([grid, np.zeros((rows, 1), dtype=grid.dtype)], axis=1)
        columns += 1

    pairs = grid.reshape(rows, columns // 2, 2)
    left, right = pairs[:, :, 0], pairs[:, :, 1]

    merged = np.zeros((rows, columns // 2), dtype=np.int8)
    # Onset anywhere in the pair wins ...
    merged[(left == ONSET) | (right == ONSET)] = ONSET
    # ... otherwise a sustain in the pair wins ...
    sustain = ((left == SUSTAIN) | (right == SUSTAIN)) & (merged != ONSET)
    merged[sustain] = SUSTAIN
    # ... otherwise the cell stays silent, which it already is.
    return merged


def collapse_one_step(matrix: PianoMatrix) -> PianoMatrix:
    """Merge to the next coarser granularity. Raises at ``redonda``."""
    target = _one_step_coarser(matrix.granularity)
    return matrix.with_grid(
        merge_pairs(matrix.grid),
        granularity=target,
        processing_step=MatrixProcessingStep.COLLAPSED,
    )


def collapse_to(
    matrix: PianoMatrix,
    target: Granularity | str,
    *,
    allow_chaining: bool = False,
    reporter: BaseProgress | None = None,
) -> PianoMatrix:
    """Collapse to ``target``, one hierarchy step at a time.

    ``target`` equal to the current granularity returns a copy. A finer target
    raises — use :func:`upsample_to`, and prefer re-collapsing from the raw
    matrix.

    ``allow_chaining`` permits starting from a matrix that is not ``raw``.
    Leave it ``False``: cleaning and the hand split are lossy, and collapsing
    their output compounds the loss invisibly. Recompute from the stored raw
    matrix instead — that is what it is stored for.
    """
    target_granularity = Granularity(target)
    distance = steps_between(matrix.granularity, target_granularity)

    if distance == 0:
        return matrix.copy()
    if distance < 0:
        raise ValueError(
            f"{target_granularity.value} is finer than {matrix.granularity.value}; "
            "collapsing only goes coarser. Use upsample_to, or recompute from the raw matrix."
        )
    if matrix.processing_step is not MatrixProcessingStep.RAW and not allow_chaining:
        raise ValueError(
            f"This matrix is already at the '{matrix.processing_step.value}' step, and the "
            "pipeline steps are lossy. Re-collapse from the stored raw matrix, or pass "
            "allow_chaining=True if you really mean to compound the loss."
        )

    progress = default_reporter(reporter)
    current = matrix
    with progress.stage("collapse", total=distance) as stage:
        for _ in range(distance):
            current = collapse_one_step(current)
            stage.advance(message=current.granularity.value)
    return current


# ------------------------------------------------------------------- upsample


def expand_columns(grid: np.ndarray) -> np.ndarray:
    """Expand each column into two, doubling the column count.

    ``0 -> [0, 0]``, ``1 -> [1, -1]``, ``-1 -> [-1, -1]``: the second half of a
    struck column becomes a sustain, everything else repeats.
    """
    first = grid
    second = np.where(grid == ONSET, np.int8(SUSTAIN), grid)
    stacked = np.stack([first, second], axis=2)
    return stacked.reshape(grid.shape[0], grid.shape[1] * 2).astype(np.int8)


def upsample_one_step(matrix: PianoMatrix) -> PianoMatrix:
    """Expand to the next finer granularity. Raises at ``semifusa``."""
    target = _one_step_finer(matrix.granularity)
    return matrix.with_grid(expand_columns(matrix.grid), granularity=target)


def upsample_to(
    matrix: PianoMatrix,
    target: Granularity | str,
    *,
    reporter: BaseProgress | None = None,
) -> PianoMatrix:
    """Upsample to ``target``, one hierarchy step at a time.

    This does **not** recover information a collapse removed; it only re-spaces
    what is there.
    """
    target_granularity = Granularity(target)
    distance = -steps_between(matrix.granularity, target_granularity)

    if distance == 0:
        return matrix.copy()
    if distance < 0:
        raise ValueError(
            f"{target_granularity.value} is coarser than {matrix.granularity.value}; "
            "upsampling only goes finer. Use collapse_to."
        )

    progress = default_reporter(reporter)
    current = matrix
    with progress.stage("upsample", total=distance) as stage:
        for _ in range(distance):
            current = upsample_one_step(current)
            stage.advance(message=current.granularity.value)
    return current


# ---------------------------------------------------------------- convenience


def retarget(
    matrix: PianoMatrix,
    target: Granularity | str,
    *,
    allow_chaining: bool = False,
    reporter: BaseProgress | None = None,
) -> PianoMatrix:
    """Move to ``target`` in whichever direction is needed."""
    target_granularity = Granularity(target)
    distance = steps_between(matrix.granularity, target_granularity)
    if distance == 0:
        return matrix.copy()
    if distance > 0:
        return collapse_to(
            matrix, target_granularity, allow_chaining=allow_chaining, reporter=reporter
        )
    return upsample_to(matrix, target_granularity, reporter=reporter)


def collapsed_frame_count(frame_count: int, steps: int) -> int:
    """Frames left after ``steps`` collapses, accounting for odd-count padding."""
    if steps < 0:
        raise ValueError("steps cannot be negative")
    count = frame_count
    for _ in range(steps):
        count = (count + 1) // 2
    return count
