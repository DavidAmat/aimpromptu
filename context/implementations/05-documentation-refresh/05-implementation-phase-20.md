# 05, Phase 20: the platform pages, the READMEs, the indexes, the closing (report)

Done 2026-11-02 by the orchestrator (wave E, alone), with two helper agents for the platform pages and the READMEs.
Plan section 6, Phase 20.

## Docs changed

- `context/app/01-app-context.md`: the glossary gets one dated list of the app's words since implementation 03 (the
  new terms of every phase report), grouped by area, each group linked to its page. The user's own text is unchanged.
- `context/00-documentation-instructions.md`: `context/ai/` in the list of areas.
- `context/00-index.md`: a section for 05; the 04 section names 04-3, 04-4 and 04-5 and lists their files; "five
  groups"; the archive row of `project-timings.md`.
- `context/implementations/README.md`: five groups; the 04 row with 04-3, 04-5 and 04-4; the 05 row done.
- `04-3-checklist.md` Phase 6 closed (done by 05); `04-5-checklist.md` task 5.2 dated; the 04 README's state line.
- `context/frontend/projects.md`: 257 → 234 lines. The Timings section moved to `context/archive/project-timings.md`
  (new, with a banner); section 5 (Copy and paste) short, with links to `annotations-stretches.md` and `editing.md`.
- `context/frontend/sheet-page.md`: 217 → 206 lines; section 12 (the file table) became a pointer to `components.md`
  section 3, which lists every file.
- `context/archive/README.md`: a section for what the refresh moved (`old-sheet-tools/`, `project-timings.md`).
- `documentation/services/frontend/components.md`: stale names removed or marked as removed (`hooks/followJob.ts`,
  `print/opentype.ts`, `PeakPlot`, the old exports of `music/transpose.ts`).
- `endpoints.md`: `/folders` and `/metadata` in the row of `USER_ROUTERS`.
- The platform pages (a helper agent): `00-project-complete-overview.md` (the routers, the stored files `sheet.f1`,
  `sheet.edits.json`, `ai-runs/`, the model, 04-3, 04-5 and 05, links to the new pages; 255 lines, the one-shot
  overview), `01-project.md` (the AI on the sheet, folders, a 05 row), `02-tech-stack.md` (SQLAlchemy, Alembic, the
  `openai` and `anthropic` SDKs, pillow, `server.allowedHosts`), `02b-local-setup.md` (the size of
  `/mnt/ssd2/aimpromptu`), `03-services-overview.md`, `04-local-development.md` (the AI keys, the new checks; 205
  lines), `05-deployment.md` (the AI APIs), `09-coding-conventions.md` (the real packages, no `notation/`, no 501
  endpoints, an AI row, the `.claude/` folder), `colors/color-palette.md` (the sheet's colours, the batches' colours).
- The READMEs (a helper agent): `context/backend/README.md`, `context/backend/api.md` (`/folders`, `/metadata`, the
  AI routes), `context/frontend/README.md` (the sidebar, Enhance with AI, links to `lab.md` and the new pages),
  `documentation/README.md`, `documentation/services/README.md`, `aitu-backend/README.md`, `aitu-frontend/README.md`
  (the Lab link, six missing npm scripts), `README.md`, and at the top of the core README a map: which page tells
  each section now.

## Code and docs that disagree (for the user; from every report, not fixed: docs only)

1. **"Sonnet" left in the code** for any AI run: `part_sheet/store.py` (`ask_sonnet`, `asked`), `part_sheet/job.py`
   (docstrings, and the `PartGone` message "The part was deleted while Sonnet wrote its sheet."), `api/sheet.py`,
   `storage/paths.py` (`part_frames_pending_path`), `transcription/pipeline.py`, `FramesSheetPage.tsx`,
   `useFramesSheet.ts`, `FramesSheetView.tsx`. The runs use GPT-6.1 Terra by default (Phases 2, 4, 9, 14).
2. **`sheet.pending` is dead**: written after each transcription, read by nothing (`store.asked` has no caller)
   (Phase 4).
3. **Simplify is not reachable** from the dialog: `POST /llm/simplify`, `job.start_simplify`, `frames.write_simplify`
   and `api/sheet.ts` `simplify` have no caller in the UI. Remove or keep (Phase 10).
4. **A run left `running` after a crash**: only a `BaseException` sets a level run to `stopped`; a backend that stops
   leaves the log `running`, and the history shows "The AI is writing" (Phase 13). Not checked at start-up.
5. **Hard skips the figure check**: `LIMITS["hard"].shortest` is 64, so a new note is never too short at hard (Phase 12).
6. **A Stop keeps the accepted batches** of a level run as one step (Phase 12). Confirm that is the intent.
7. **Super hard** patterns can be ticked in the gallery, but no level writes at super hard (`Level` is easy, medium,
   hard) (Phase 11).
8. **Transpose → Figures** never remembers its last **To**: `figuresFrom` is never set (Phase 7).
9. **`matrix/hands.py` `DEFAULT_METHOD = "beam"`**, but `refine` runs (the config's method) (Phase 16).
10. Stale comments and docstrings: `sheet_llm.py` `OpenAIComplete` ("not used yet"; it is used by every run),
    `audio/frames.py` (cuts in `metadata.json`; they are in `timeline.json`), `audio/piece_audio.py` (where
    `piece-r<N>.flac` is written), `engrave/frames.py` (a segment redraw the app never asks for), "prompt 6" in
    `frames.py` (version 7), the Lab's page headers (Phases 3, 9, 10, 15, 19).
11. **`OPENAI_API_KEY`** is missing from `.env.example`, and the `compose.yaml` header names only `HF_TOKEN` and
    `ANTHROPIC_API_KEY`; every default run needs it. `pyproject.toml` still says `openai` is "used only by the
    comparison scripts".
12. Hex colours outside `palette.ts` (`BATCH_COLOURS` in `frames/batches.ts`, `WINDOW_COLOUR` and the lyric fills in
    `FramesSheetView.tsx`); `api/_placeholders.py` is dead code.
13. Small: two time helpers (`formatSeconds` and `formatTime`); `formatFrameLabel` and `FRAME_LABEL_WIDTH` unused
    (Phase 4); `sheet/llm/prompt/instructions.md` and `prompt/frames/instructions.md` share a name (Phase 9).

## Not checked

- No run of the app, the tests or the AI (plan section 5).
- `projects.md` stays a little over the limit (234 lines): its four steps are one flow, and each step's part is short.

## Checks

- `check-links.py`: 547 files, 0 broken links.
- `check-names.py` on the whole scope: 170 missing names in 68 files (Phase 1: 204). What is left is history on
  purpose (the "Removed" sections, such as `components.md` section 9 with 79), the machine paths of `02b-local-setup.md`
  (29), FastAPI's `/docs`, and commands `09-coding-conventions.md` recommends that were never built.
- The inventory: every row has its final State.
