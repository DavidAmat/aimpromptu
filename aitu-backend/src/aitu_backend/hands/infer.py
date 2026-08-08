"""Public entry point: a ``PianoMatrix`` in, a hand assignment out.

This is the only function the rest of the backend calls. ``matrix/hands.py``
wraps it for the pipeline; nothing else should need to know that a cost model
exists.
"""

from __future__ import annotations

from collections.abc import Callable

from aitu_backend.hands import beam as beam_module
from aitu_backend.hands import threshold as threshold_module
from aitu_backend.hands.config import DEFAULT_CONFIG, HandInferenceConfig
from aitu_backend.hands.events import DecodedMatrix, decode_matrix
from aitu_backend.hands.result import HandInferenceResult
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.schemas.matrix import MatrixProcessingStep

_Method = Callable[[DecodedMatrix, HandInferenceConfig], HandInferenceResult]

#: Selectable methods. ``beam`` is the default and the recommendation; the rest
#: exist for comparison, speed and debugging.
METHODS: dict[str, _Method] = {
    "beam": beam_module.beam,
    "greedy": beam_module.greedy,
    "exact": beam_module.exact,
    "threshold": threshold_module.infer,
}

#: What a caller gets when it asks for nothing.
DEFAULT_METHOD = "beam"


def infer_hands(
    matrix: PianoMatrix,
    config: HandInferenceConfig | None = None,
) -> HandInferenceResult:
    """Assign exactly one hand to every onset of ``matrix``.

    ``matrix`` must be a one-hand matrix — normally the whole-keyboard
    Appendix-B clean, whose sustains are what the cost model was tuned against. A
    ``two-hands`` matrix is already split; re-inferring from one half would
    silently discard the other, so it is refused.

    The pipeline no longer renders the matrix it infers from: it passes the clean
    view here and applies the answer to the collapsed one, so each hand can keep
    the sustains the other hand used to cut. See
    :func:`aitu_backend.matrix.hands.split_hands`.

    Every sustain inherits its onset's hand, and the returned grids recombine to
    the input exactly. Runtime tracks onset groups and polyphony: roughly 0.7 s
    for a four-minute piece, ~3 s for a dense chordal worst case.
    """
    config = config or DEFAULT_CONFIG
    if matrix.processing_step is MatrixProcessingStep.TWO_HANDS:
        raise ValueError(
            "infer_hands expects a one-hand matrix (normally the 'clean' step); "
            "this matrix is already split into two hands"
        )
    method = METHODS.get(config.method)
    if method is None:
        raise ValueError(
            f"Unknown hand-inference method '{config.method}'. "
            f"Expected one of {sorted(METHODS)}"
        )
    decoded = decode_matrix(matrix, promote_orphan_sustains=config.promote_orphan_sustains)
    return method(decoded, config)


__all__ = ["DEFAULT_METHOD", "METHODS", "infer_hands"]
