# Task 9.1.1 — VexFlow-ready score format

`notation/score_builder.py`: the backend digests matrix + metadata into a format the frontend renders without music logic. Heavy lifting stays backend-side (future GPU host argument).

## Subtask 9.1.1.1 — Format design

JSON score document containing, per hand: ordered measures, each with voice entries
`{keys, duration, dots, isRest, isSpacer, tieToNext, beamGroup, annotations}`. Durations are
onset-led: simultaneous onsets form a chord, every chord member shares the span to the next onset,
and a recorded release never creates an interior rest. `isSpacer` is a timing-only, invisible rest
used solely when an interior span has an unwritable residue. `tieToNext` is retained for transport
compatibility but always false: a cross-barline gap becomes a leading rest in the following
measure. Include measure boundaries computed from the time signature grid (default 4/4 over
beat=negra).

Visible rests are allowed before a measure's first entrance. At the end, first expand the final
note/chord to one legal figure that approaches the barline; only an unwritable remainder becomes a
visible trailing rest.

Evolve the existing frontend `matrixToNotation.ts` logic by porting it into this backend builder; the frontend keeps only a thin VexFlow adapter.

## Subtask 9.1.1.2 — Hands and alignment

Input: r/l matrices (equal frame count). Output keeps both hands' measures index-aligned so simultaneous notes land vertically aligned in the grand staff. Single-hand mode (clean matrix only) supported for debugging and one-hand songs.

## Subtask 9.1.1.3 — Annotation overlay

Apply the `annotations` block from `metadata.json` (trill ranges, tuplet groups, key-signature changes, cue-size passages, lyrics, fingers — filled by later stories) as render directives referencing matrix indices (hand, column range, row). The underlying matrix is never modified by annotations.

## Subtask 9.1.1.4 — Endpoint

`GET /notation/{artifact}` returns only the score document — the artifact repository pre-generates it whenever a version is saved, so the Notation tab load is instant.

## Acceptance

Golden-file tests: known matrices -> expected score JSON (scale, chord, dotted note, two hands),
plus regressions for delayed entrances, interior gaps, unequal chord releases and measure-tail
expansion.
