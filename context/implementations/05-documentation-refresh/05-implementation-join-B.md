# 05, join of wave B: report

Done by the orchestrator (2026-11-01), after Phases 3, 6, 10, 11 and 15.

## Edits applied

| From | File | Edit |
|---|---|---|
| 3 | `00-index.md`, `documentation/services/README.md` | `sheet-drawing.md` listed after `sheet-f1.md` |
| 3 | `sheet-f1.md` | the link to `sheet-drawing.md` |
| 6 | `annotations.md` (the hub) | the intro bullet, **Mark a stretch**, **The range toolbox**, **Copy and paste**: short, with links to `annotations-stretches.md` (Record a passage at the end and the blank sheet left to Phase 17) |
| 6 | `00-index.md` | the rows of `annotations-stretches.md` and `backend/editing.md`; the archive row with the old `annotations-stretches.md` |
| 6 | `components.md` 3 | the range toolbox row; a row for `FrameRangeFields.tsx` |
| 6 | `endpoints.md` 4.1 | the `/paste` row: its 404 and 409 |
| 10 | core `sheet/README.md` 14 | the three bullets (a stretch, a stretch of one hand, Simplify) replaced by one with links; the Tests bullet kept |
| 10 | `context/ai/README.md`, `whole-run.md` | the links to `stretch-and-simplify.md`; Simplify is a level now. The join also listed `levels.md` (Phase 11) in "Pages of this folder" |
| 10 | `endpoints.md` 4.1 | `/llm/simplify`: no longer offered by the dialog |
| 10, 11 | `00-index.md` | the rows of `ai/stretch-and-simplify.md`, `ai/levels.md`, `ai-levels.md` |
| 11 | `endpoints.md` 4.1 | the `GET /sheet/{uuid}/chords` row |
| 11 | `components.md` 3 | the rows of `PatternCatalog.tsx` and `patterns.ts` |
| 11 | `documentation/services/README.md` | `ai-levels.md` |
| 15 | `endpoints.md` | `/youtube/download` answers `201` and the metadata |

The reports of Phases 3 and 6 had a link each in their pending-edit text that broke the links check; the join made
them code.

## Checks

`check-links.py`: 531 files, 0 broken. `check-names.py`: the new missing names are pages wave C writes
(`context/ai/level-run.md`, `context/frontend/sheet-page.md`); the others are older, for the owner phases and Phase 20.
