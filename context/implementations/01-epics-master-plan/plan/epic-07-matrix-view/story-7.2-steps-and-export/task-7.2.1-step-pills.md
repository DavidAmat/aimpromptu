# Task 7.2.1 — Processing step pills

## Subtask 7.2.1.1 — Pills

Pill buttons above the grid: `raw`, `collapsed`, `clean`, `two-hands`. Switching loads that persisted artifact for the working input. The grid component is generic across all of them.

## Subtask 7.2.1.2 — Two-hands rendering

Both hand matrices drawn in one grid, distinguished by color instead of black/gray:

- left hand: dark Green onset, light Green sustain
- right hand: dark Blue onset, light Blue sustain

Edges follow the hand color. Colors come from `palette.ts` aliases.

## Acceptance

All four pills render for a transcribed piece; hands visually distinct.
