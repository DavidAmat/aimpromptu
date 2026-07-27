# Epic 7 — Matrix tab

The debugging heart of the Playground: a spreadsheet-like view of any piano matrix (columns =
piano keys, rows = time frames), switchable between processing steps, exportable/importable as
JSON, with instant BPM/granularity recompute. A source banner distinguishes an entire track from a
saved segment, whose rows show both local and root-audio time. Editing and audio playback of the
matrix are nice-to-have stories at the end.

Read first: `project-features.md` "Matrix tab" section.

## Story 7.1 — Grid visualization

- Task 7.1.1 matrix grid: key columns with EN + rotated ES names, time-frame rows with
  `f:N · start` labels for full tracks and `f:N · local ↗ original` for segments (superseding the
  original `[start - end]` form — see
  [frontend/timestamps.md](../../../frontend/timestamps.md)), onset/sustain circles with
  connecting edges, frozen header, vertical column separators, downward-scroll time axis.

## Story 7.2 — Steps and export

- Task 7.2.1 step pills: switch raw / collapsed / clean / two-hands; hand color scheme.
- Task 7.2.2 json export/import: dense and sparse downloads with full metadata; import back in any session.

## Story 7.3 — Recompute and search

- Task 7.3.1 in-situ recompute: change BPM/granularity inside the view, matrices recomputed from raw and redisplayed automatically.
- Task 7.3.2 frame search: jump to a frame number or timestamp (also the landing point when coming from the Piano Roll tab).

## Story 7.4 — Editing and player (nice to have)

- Task 7.4.1 cell editing: add/select/delete circles with validator-enforced rules and save into the working artifact.
- Task 7.4.2 matrix player: play the matrix with synthesized piano tones and a running cursor row.

## Exit criteria

Manual trial: transcribe a short recorded scale, inspect raw vs clean in the grid, flip granularity from Fusa to Negra and back watching the matrix recompute, download the sparse JSON and re-import it.
