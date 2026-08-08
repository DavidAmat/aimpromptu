# Task 9.4.2 — Transposition · progress

Status: **done** on 2026-07-27. Preview, then accept, both from the Notation tab.

## The operation

Task 2.4.2 already had `matrix.ops.transpose` (row shift, clamped to the 88 keys). This task is the
UI over it plus one decision about *what* gets shifted.

`POST /matrix/{uuid}/transpose` gained a `persist` flag:

- **`persist=false`** (default) — preview. Shifts the recomputed clean matrix, returns it, stores
  nothing.
- **`persist=true`** — accept. Shifts the stored **raw** matrix and re-derives everything from it.

Shifting the raw rather than the displayed matrix matters: a row shift means the same thing at every
granularity, so transposing the source loses nothing and every later recompute, every step pill and
every other tab stays in the new key. Shifting the clean matrix would have meant re-expanding it back
to fusa, which is lossy for no reason. The previous raw is kept as `raw_before_edit.npz` by
`persist_edited_raw`, as with any other edit.

## Section preview (9.4.2.2)

`POST /notation/{artifact}/preview` renders a column range at a candidate transposition and
optionally a candidate key, without storing anything. It slices both hands at the same columns so a
grand staff preview stays aligned, and rebases them to 0.

The overlay is deliberately **not** applied to a preview: annotations are addressed by absolute
column and a slice has been rebased, so applying them would put lyrics under the wrong notes. A
preview is about pitch and rhythm.

In the tab: from-frame, to-frame, a −12…+12 semitone slider, **Preview**, then **Accept shift**.
Accept is disabled for saved versions — those are immutable, and editing one means saving a new
version from the Playground.

## Errors found

The first slice used `payload.from_column` unclamped, so a from-frame past the end raised inside
`slice_frames`. It is now clamped to the matrix and always yields at least one column.

## Manual trial

[`user_review/epic-09-notation.md`](../user_review/epic-09-notation.md) step 9.6 — the task file's
own script: transcribe a piece, preview +2 semitones on a five-second slice, accept, verify the full
score shifted (and that the Matrix tab agrees).

## For the next worker

The task file places this "during the audio-to-matrix flow". It is reachable from the Notation tab
because that is where you can *see* whether the key is right; the Matrix tab's own transpose control
is the same endpoint without `persist`, so wiring an accept there too is a one-line change.
