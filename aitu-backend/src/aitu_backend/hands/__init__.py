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

Entry points:

* :func:`infer_hands` — a :class:`~aitu_backend.matrix.model.PianoMatrix` in,
  a :class:`HandInferenceResult` out (right/left matrices, per-onset hands,
  costs, confidences, warnings).
* :func:`encode_hand_map` — the compact ``"rrlrl…"`` string that travels in
  ``metadata.json`` alongside the sparse COO payload.

``matrix/hands.py`` is the caller the rest of the project uses; nothing outside
this package should need to know the cost model exists.
"""

from __future__ import annotations

from aitu_backend.hands.config import (
    DEFAULT_CONFIG,
    CostWeights,
    HandInferenceConfig,
    HandModel,
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
from aitu_backend.hands.infer import METHODS, infer_hands
from aitu_backend.hands.result import Assignment, Diagnostics, HandInferenceResult

__all__ = [
    "Assignment",
    "CostWeights",
    "DEFAULT_CONFIG",
    "DecodedMatrix",
    "Diagnostics",
    "HAND_CHARS",
    "HandInferenceConfig",
    "HandInferenceResult",
    "HandModel",
    "METHODS",
    "NoteEvent",
    "OnsetGroup",
    "RelocationMode",
    "SearchConfig",
    "decode_hand_map",
    "decode_matrix",
    "encode_hand_map",
    "hand_char",
    "infer_hands",
]
