# 05, join of wave C: report

Done by the orchestrator (2026-11-01), after Phases 4, 7, 12, 16 and 17.

## Edits applied

| From | File | Edit |
|---|---|---|
| 4 | `projects.md` section 4 | the Sheet step is one paragraph with links to `sheet-page.md`, `annotations.md`, `../ai/`, `folders-and-metadata.md` (no "Sonnet", no run by itself); 293 → 257 lines, still over the limit (Phase 20) |
| 4 | `components.md` 3 | the rows of `frames/navigation.ts` and `components/piece/AiMark.tsx` |
| 4 | `00-index.md` | the row of `frontend/sheet-page.md` |
| 4 | `whole-run.md`, `sheet-drawing.md` | `sheet-page.md` is a link now |
| 7 | `annotations.md` (the hub) | the intro bullet; the four bullets of the sheet toolbox, lyrics, Print to PDF and the keyboard panel made one, with a link to `annotations-sheet.md` |
| 7 | `00-index.md` | the row of `frontend/annotations-sheet.md` (the new sheet's toolbox) |
| 12 | `endpoints.md` 4.1 | `/llm/level`: `strict`, `chords`, `batches`, `model`, the wait after the first batch, the 202 and the 409 when the AI is not set up |
| 12 | `00-index.md`, `documentation/services/README.md` | the row of `ai/level-run.md`; "the level run" in the rows of `ai-levels.md` |
| 12 | `context/ai/README.md`, `stretch-and-simplify.md`, `ai-runs.md` | `levels.md` and `level-run.md` are links now (no phase numbers) |
| 16 | `endpoints.md` 1 | `GET /pieces/{uuid}/notes`: its `stale` |
| 17 | `projects.md` section 6 | **Record a passage at the end** (the floating bar) and **Record a passage** (a blank sheet) |

Phase 7's report had two links in its pending-edit text that broke the links check (code spans over two lines); the
join put each span on one line.

## Checks

`check-links.py`: 540 files, 0 broken.

## For the user (from the reports, not decided here)

- Phase 4: `sheet.pending` is still written after a transcription and read by nothing; comments still say "Sonnet".
- Phase 7: `figuresFrom` is never set, so Transpose → Figures never remembers its last **To**.
- Phase 12: at hard the figure check never fires (`LIMITS["hard"].shortest` 64); a Stop keeps the batches accepted.
- Phase 16: `matrix/hands.py` `DEFAULT_METHOD = "beam"`, but `refine` runs.
