# 05, join of wave A: report

Done by the orchestrator (2026-11-01), after Phases 2, 5, 9, 14, 18 and 19.

## Edits applied

| From | File | Edit |
|---|---|---|
| 2 | `00-index.md`, `documentation/services/README.md` | `sheet-f1.md` listed after `time-matrix.md` |
| 5 | `endpoints.md` 4.1 | rows `/duplicate`, `/unite`, `/take-out` after `/remove` |
| 5 | `components.md` 3 | the note toolbox row; the range toolbox its own row (Phase 6 owns it) |
| 5 | `00-index.md` | the rows of `annotations.md` and `annotations-notes.md`; the archive row links the two files of `archive/old-sheet-tools/` (no README there) |
| 9 | core `sheet/README.md` | sections 5 and 11: the model client (`sheet_llm`, Terra by default, Sonnet when chosen; checked in `job._complete`), prompt version 7, `job._complete` in the diagram |
| 9 | `endpoints.md` 4 | "Sonnet" to "the AI" in the sheet's own description (the other rows stay for Phases 10 to 13) |
| 9 | `components.md` 8 | the `AiMark.tsx` row |
| 9 | `00-index.md`, `documentation/services/README.md` | the group `context/ai/` (README, whole-run); `ai-runs.md` |
| 14 | `endpoints.md` 7, 7.1.1 | "the AI writes"; the link to `folders-and-metadata.md` |
| 14 | `components.md` 8.1, `00-index.md` | the link; the row of `folders-and-metadata.md` |
| 14 | `private-library.md` | 5.1 the link; the sheet-library script "since removed" (the sentence had no path in backticks, so only those words were added) |
| 18 | `components.md` | new section 1.3, shared libraries and requests |
| 19 | `endpoints.md` 1 | the logout needs no session; the video reader's routes (a new block before 1.1) |
| 19 | `components.md` | the `/dev/ui` row; the Lab as section **1.4** (Phase 18 took 1.3) |
| 19 | `00-index.md`, `projects.md` | the row of `lab.md`; the link to `lab.md` |

## Checks

`check-links.py`: 520 files, 0 broken. `check-names.py` on the changed files: no new missing name; the ones listed are
older (the "Removed" sections and the history of removed routes), for the owner phases and Phase 20.
