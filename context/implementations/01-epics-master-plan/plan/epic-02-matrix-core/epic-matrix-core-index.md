# Epic 2 — Matrix core

The piano matrix engine in `aitu_backend/matrix/`: model, validation, granularity collapsing/upsampling, cleaning, hand splitting and structural operations. Pure Python/numpy/scipy, no UI, fully unit-testable. Everything else in the project builds on this epic.

Read first: `context/music/notation-logic/01-matrix-notation-logic.md` (all appendices) and `project-features.md` sections "The new notation", "Collapsing temporal resolution", "General Flexibility", "Right and Left Alignment and editing tempo".

## Story 2.1 — Model and validation

- Task 2.1.1 matrix model: in-memory PianoMatrix class over sparse COO, dense/sparse conversion, npz persistence, granularity/BPM timing math.
- Task 2.1.2 transition validator: enforce the 0/1/-1 Markov transition rules per row; used after every mutation.

## Story 2.2 — Granularity

- Task 2.2.1 collapse and upsample: one-hierarchy-step merge rules chained for multi-step collapses; upsampling rules for going finer.

## Story 2.3 — Cleaning and approximation

- Task 2.3.1 sustain cleaning: Appendix B rule — a sustain dies when any other onset starts.
- Task 2.3.2 duration approximation: Appendix C greedy rounding of real-world durations onto the granularity grid (max 2-figure ligatures).

## Story 2.4 — Hands and structural operations

- Task 2.4.1 two-hands split: C4 threshold duplication into r/l matrices, same shape.
- Task 2.4.2 matrix operations: transposition, tempo (column) insertion, slicing and range replacement.

## Exit criteria

Full pipeline callable as pure functions: raw -> collapsed -> clean -> two-hands, with round-trip tests over the notation-spec examples; recompute of any granularity from the raw fusa matrix is fast (sub-second for several minutes of music).
