# Task 7.3.1 — In-situ BPM/granularity recompute

The most impactful feature of this view: change BPM and temporal resolution without leaving the grid.

## Subtask 7.3.1.1 — Controls

BPM input + granularity dropdown in the tab toolbar, prefilled from the current artifact metadata.

## Subtask 7.3.1.2 — Recompute

On change, call the fast-recompute path (Task 4.3.1: steps 3–5 from the stored raw fusa matrix). The raw matrix is never mutated, so coarse and fine targets are always reachable without information loss. Grid refreshes automatically with the new artifacts; both directions (finer/coarser) supported.

## Subtask 7.3.1.3 — Persistence

Recomputed matrices replace the working artifacts on disk (playground working folder), so all other tabs see the same state after the change is saved.

## Acceptance

Manual trial: flip granularity Fusa -> Corchea -> Negra -> Fusa repeatedly; each switch <1 s and consistent (merge-rule testing loop).
