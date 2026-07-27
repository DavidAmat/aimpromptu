"""Piano matrix engine: model, granularity, cleaning, hands and operations.

The 88 x N matrix (``1`` onset, ``-1`` sustain, ``0`` silence) is the core
representation of the project.

| Module | Role |
|--------|------|
| ``keys`` | canonical 88-key tables: ES/EN names, MIDI, middle-C row |
| ``text_notation`` | the custom text notation parser — single source of truth |
| ``model`` | ``PianoMatrix``, timing math, conversions, npz |
| ``validator`` | per-row transition rules; ``validate`` / ``normalize`` |
| ``convert`` | sparse <-> dense, envelope conversions |
| ``granularity`` | collapse (merge rules) and upsample, one hierarchy step at a time |
| ``cleaning`` | Appendix B: a sustain dies when any other key is struck |
| ``approximation`` | Appendix C: fit human timings onto the grid |
| ``hands`` | Appendix D: split at middle C into two aligned matrices |
| ``ops`` | transpose, insert, slice/delete/replace, validated cell edits |

Pipeline order: raw -> ``granularity.collapse_to`` -> ``cleaning.clean_sustains``
-> ``hands.split_hands``.

**This module deliberately re-exports nothing.** ``schemas.matrix`` imports
``matrix.keys``, so any eager import here would run ``matrix.model`` — which
imports ``schemas.matrix`` — while that module is still half-initialized.
Import the submodule you need directly::

    from aitu_backend.matrix.model import PianoMatrix
    from aitu_backend.matrix.granularity import collapse_to
"""
