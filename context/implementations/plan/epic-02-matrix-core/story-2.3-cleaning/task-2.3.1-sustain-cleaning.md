# Task 2.3.1 — Sustain cleaning

`matrix/cleaning.py`: Appendix B of `01-matrix-notation-logic.md`. Goal: neat sheets — long sustains must not survive while other notes start.

## Subtask 2.3.1.1 — Rule

A note may keep sustaining only while no other note produces an onset. At the first column where any other key has a `1`, every carried sustain (`-1`) of other keys is cut (set to `0` from that column on, for that sounding span).

- Chords sustained together survive together (all struck simultaneously, sustained equally, nothing else played).
- A re-onset of the same key is not affected (a new `1` starts its own span).

## Subtask 2.3.1.2 — Implementation

Column sweep over the dense form: track open spans per row; on a column with onsets, close all open spans not re-struck in that column. Validate output with Task 2.1.2.

## Acceptance

Tests reproduce both Appendix B examples (the C3/C4 example and the classical accompaniment pattern) plus the chord counter-example where a same-key re-onset survives.
