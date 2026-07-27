# Task 9.1.1 — VexFlow-ready score format

`notation/score_builder.py`: the backend digests matrix + metadata into a format the frontend renders without music logic. Heavy lifting stays backend-side (future GPU host argument).

## Subtask 9.1.1.1 — Format design

JSON score document containing, per hand: ordered measures, each with voice entries `{keys, duration, dots, isRest, tieToNext, beamGroup, annotations}`. Durations derived from column spans and BPM (Epic 2 timing math). Chords = simultaneous onsets in one column. Include measure boundaries computed from the time signature grid (default 4/4 over beat=negra) — needed for the ties-across-barline rule and beat guides.

Evolve the existing frontend `matrixToNotation.ts` logic by porting it into this backend builder; the frontend keeps only a thin VexFlow adapter.

## Subtask 9.1.1.2 — Hands and alignment

Input: r/l matrices (equal frame count). Output keeps both hands' measures index-aligned so simultaneous notes land vertically aligned in the grand staff. Single-hand mode (clean matrix only) supported for debugging and one-hand songs.

## Subtask 9.1.1.3 — Annotation overlay

Apply the `annotations` block from `metadata.json` (trill ranges, tuplet groups, key-signature changes, cue-size passages, lyrics, fingers — filled by later stories) as render directives referencing matrix indices (hand, column range, row). The underlying matrix is never modified by annotations.

## Subtask 9.1.1.4 — Endpoint

`GET /notation/{artifact}` returns only the score document — the artifact repository pre-generates it whenever a version is saved, so the Notation tab load is instant.

## Acceptance

Golden-file tests: known matrices -> expected score JSON (scale, chord, dotted note, two hands).
