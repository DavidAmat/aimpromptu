# 05, join of wave D: report

Done by the agent of the join (2026-11-01), after Phases 8 and 13 (both `[x]` in the checklist).

## Edits applied

| From | File | Edit |
|---|---|---|
| 8 E8.1 | `documentation/services/backend/paths-and-data.md` 4.5 | the first row of the snapshot table: the paste, the promotion, the start of an AI run (for **Revert**), the Lab's step |
| 8 E8.2 | the same, the paragraph **Putting a snapshot back** | the undo and redo of a promotion, **Revert** of an AI run, the rollback of a failed paste |
| 8 E8.3 | the same, section 2.4 | the sentence about `sheet.edits.json` (its start again after a whole AI run; a new transcription deletes it). Put after "at most 50)", the sentence joined to the next one by a comma, so the sentence still reads |
| 8 E8.4 | `context/frontend/rendering.md` (list of frontend files) | `FramesPdfDialog.tsx` links to `printing.md`; `FramesPreviewDialog.tsx` is the preview of **Transpose** |
| 13 E13.1 | `documentation/services/backend/endpoints.md` 1 | four rows after `llm/level-copy`: `GET llm/runs`, `GET llm/runs/{run_id}`, `POST .../continue`, `POST .../batches/{k}/again` |
| 13 E13.2, E13.3 | `documentation/services/frontend/components.md` 3 | the row of `AiRunPanel.tsx` gets the wait after batch 1 and **History**; two new rows `AiHistoryPanel.tsx`, `AiRunDetail.tsx` |
| 13 E13.4, E13.5 | `context/00-index.md` | the row of `ai/run-history.md` after `level-run.md`; "the history of runs (the log)" in the `ai-levels.md` row |
| 13 E13.6 | `documentation/services/README.md` | "the history of runs (the log)" in the `ai-levels.md` row |
| 13 E13.7 | `context/ai/README.md` | (a) the row **The history of runs** links `run-history.md`; (b) the list of pages has `run-history.md`; (c) the closing paragraph about the refresh is deleted (every page of the folder exists now) |
| 13 E13.8 | `context/ai/level-run.md` step 5 | `run-history.md` is a link; ", in this folder" deleted |

## Fixes outside the pending edits

- `context/implementations/05-documentation-refresh/05-implementation-phase-8.md`, E8.4 text: the quoted link
  `[printing.md](printing.md)` was read by `check-links.py` as a live link and broke the check. It is now the code span
  `` `printing.md` `` (the edit as applied to `rendering.md` is unchanged and correct).

## Checks

- `check-links.py`: 544 files, 0 broken links (after the fix above).
- `check-names.py` on the nine files of this join: the names it lists are on lines this join did not touch, so they are
  not new. They are in `components.md` lines 539 to 558 (a section of removed components and paths: old names such as
  `ScoreStack`, `VexflowSheetPage`, `music/handMap.ts`), `00-index.md` lines 139 (`feat/migrate-new-logic`, a branch
  name) and 311 (`TimeScoreView`), and `documentation/services/README.md` line 36 (`piano-sheet.md`, `notes.md`, and
  two more). Not fixed here; for Phase 20 (the whole-scope check).

## For Phase 20 (from the reports and the join)

- Phase 13: `context/ai/README.md` and the core README section 11 may still name the old run kinds; not checked there.
- Phase 8: `sheet-page.md` is 217 lines (over the limit of about 200), the glossary terms of its report.
