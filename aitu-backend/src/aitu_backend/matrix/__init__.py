"""Piano matrix engine: the wall-clock grid, the hand split, and what measures it.

The 88 x N matrix (``1`` onset, ``-1`` sustain, ``0`` silence) is the core
representation of the project. **A column is a fixed number of milliseconds**
(D-01), so the matrix is a clock rather than a rhythm, and no module here has an
opinion about what any note is called.

| Module | Role |
|--------|------|
| ``keys`` | canonical 88-key tables: ES/EN names, MIDI, middle-C row |
| ``text_notation`` | the custom text notation parser; its header carries ``frameMs`` |
| ``time_grid`` | frame <-> millisecond conversion; the only module that knows the frame length |
| ``model`` | ``PianoMatrix``, timing math, conversions, npz |
| ``validator`` | per-row transition rules; ``validate`` / ``normalize`` |
| ``convert`` | sparse <-> dense, envelope conversions |
| ``cleaning`` | Appendix B: a sustain dies when any other key **of that hand** is struck |
| ``hands`` | Appendix D: split into two aligned matrices (beam inference; see ``aitu_backend.hands``) |
| ``ops`` | transpose, insert, slice/delete/replace, validated cell edits |
| ``intervals`` | the gaps between one hand's attacks, measured on raw times (D-07) |
| ``peaks`` | where those gaps pile up |
| ``ladder`` | one named peak turned into all nine figure lengths (D-10) |
| ``passages`` | the user-drawn sections, each with its own ladder (D-19) |

Pipeline order: recorded notes -> ``transcription.events_to_matrix.events_to_time_matrix``
-> ``hands.split_hands`` -> measurement. The split comes before any measurement
(D-31), because the gaps between a right-hand run and a held left-hand chord are
not a rhythm and would bury the peak the user is meant to name.

``granularity``, ``approximation``, ``tempo_map`` and ``isochrony`` were deleted
in Phase 4. They collapsed one grid onto another, fitted durations to a beat,
rebased columns when a tempo changed, and forced an even run onto a beat grid.
None of those questions exists once a column is a millisecond count.

**This module deliberately re-exports nothing.** ``schemas.matrix`` imports
``matrix.keys``, so any eager import here would run ``matrix.model`` (which
imports ``schemas.matrix``) while that module is still half-initialized. Import
the submodule you need directly::

    from aitu_backend.matrix.model import PianoMatrix
    from aitu_backend.matrix.time_grid import frame_of_seconds
"""
