"""Hand inference: which hand plays each onset of a piano matrix.

Replaces Appendix D's ``Do-4`` threshold with the beam dynamic program that won
the `poc-piano-hand-prediction` research PoC (v3, 0.955 onset accuracy over 209
benchmark scenarios versus 0.848 for the threshold, zero invariant violations,
0.68 s for a four-minute piece).

The threshold is not "0.1 worse": it produced 21 physically impossible hand
spans on the benchmark, because absolute pitch is *evidence*, not a decision.
Either hand moves through any register, hands cross, a left hand jumps from a
bass note to middle-register chords while the right hand holds a melody. This
package treats the split as what it is — a temporally coupled resource
allocation over two moving hands — and minimizes a named, ablatable objective
(:mod:`aitu_backend.hands.costs`) over onset groups.

Since the beam, two page-level defects it structurally cannot see have been repaired in
a second pass (:mod:`aitu_backend.hands.refine`, the ``refine`` method and the default):
a hand parked several ledger lines onto the other staff, and a repeating accompaniment
figure cut in half. Both are properties of the *result* rather than of a step, so pricing
them inside the group-by-group search made matters worse — 0.9506 against 0.9546 for
having no such term at all. Repaired afterwards, with a gate on whether the other hand
could actually have helped, the same geometry is worth 0.9641 for one regression.
``documentation/services/backend/hand-inference-second-pass.md`` has the numbers.

Entry points:

* :func:`infer_hands` — a :class:`~aitu_backend.matrix.model.PianoMatrix` in,
  a :class:`HandInferenceResult` out (right/left matrices, per-onset hands,
  costs, confidences, warnings).
* :func:`encode_hand_map` — the compact ``"rrlrl…"`` string that travels in
  ``metadata.json`` alongside the sparse COO payload.
* :func:`detect_figures` — the accompaniment figures found in a reading of the
  music. Useful beyond hand inference: the turn boundaries it reports are where an
  engraver breaks a beam.

``matrix/hands.py`` is the caller the rest of the project uses; nothing outside
this package should need to know the cost model exists.
"""

from __future__ import annotations

from aitu_backend.hands.config import (
    DEFAULT_CONFIG,
    CostWeights,
    FigureModel,
    HandInferenceConfig,
    HandModel,
    PatternWeights,
    RefineConfig,
    RelocationMode,
    SearchConfig,
)
from aitu_backend.hands.encoding import (
    HAND_CHARS,
    decode_hand_map,
    encode_hand_map,
    hand_char,
)
from aitu_backend.hands.events import DecodedMatrix, NoteEvent, OnsetGroup, decode_matrix
from aitu_backend.hands.figuration import Figure, detect_figures
from aitu_backend.hands.infer import METHODS, infer_hands
from aitu_backend.hands.result import Assignment, Diagnostics, HandInferenceResult

__all__ = [
    "DEFAULT_CONFIG",
    "HAND_CHARS",
    "METHODS",
    "Assignment",
    "CostWeights",
    "DecodedMatrix",
    "Diagnostics",
    "Figure",
    "FigureModel",
    "HandInferenceConfig",
    "HandInferenceResult",
    "HandModel",
    "NoteEvent",
    "OnsetGroup",
    "PatternWeights",
    "RefineConfig",
    "RelocationMode",
    "SearchConfig",
    "decode_hand_map",
    "decode_matrix",
    "detect_figures",
    "encode_hand_map",
    "hand_char",
    "infer_hands",
]
