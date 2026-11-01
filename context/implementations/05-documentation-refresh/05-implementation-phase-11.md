# 05, Phase 11: the levels, the catalog of patterns, the chords of the song

Plan: [`05-plan.md`](05-plan.md) section 6, Phase 11 (wave B). Checklist: [`05-checklist.md`](05-checklist.md).
Written 2026-11-01 by the Phase 11 agent (a small model), on `feat/05-docs-refresh`.

## Docs changed

- `context/ai/levels.md` (new, 123 lines): what a level is, what the user does in the dialog, the catalog (114
  patterns, the approved sets, the super hard ones), the grid, the harmony, the hands, the chords of the song, the
  level in place and the level copy, the limits.
- `documentation/services/backend/ai-levels.md` (new, 149 lines): the files, constants, functions and routes of the
  catalog (`sheet/llm/catalog/`, `load_patterns`, `catalog_rows`, `run_refs`), the grid (`sheet/levels/grid.py`), the
  harmony (`harmony.py`), the hands (`hands.py`), the guide's chords (`guide_chords`, `_chords`, `GET /chords`), the
  level copy (`flow.level_copy`, `run_llm_level_copy`), the dialog's files. Section 8 says Phases 12 and 13 add below.
- `documentation/services/backend/paths-and-data.md`: `project.json` gets three entries: `levelOf`, the origin
  `{"levelOf": id}`, and `parts[].chords`.
- `context/07-database.md`: checked, no change. Phase 14 had already written `level_of` (revision `0010`) correctly.
- `05-inventory.md`: a row for each new page. `05-checklist.md`: Phase 11's own lines.

## What was stale

- No `context/` page told the catalog, the grid or the chords of the song (only the core README and the code did).
- `paths-and-data.md` did not have `levelOf`, the origin of a level copy, nor the part's `chords`.
- `endpoints.md` has `/levels/catalog`, its SVG route and `/llm/level-copy` already (04-3 Phase 4), but not
  `GET /sheet/{uuid}/chords` (04-5). Pending edit E1.
- `components.md` has no row for the gallery (`PatternGallery`) nor for `patterns.ts`. Pending edit E2.

## Code and docs that disagree (for the user)

- The gallery's **Super hard** tab shows the 15 super hard patterns (2 left, 13 right). The run's level choice
  (`EnhanceDialog.tsx` `LEVELS`) offers Easy, Medium and Hard only, and the backend `Level` type
  (`api/sheet.py` line 618) is `Literal["easy", "medium", "hard"]`. `run_refs` would accept a ticked super hard ref
  for a hand, so the code allows it through the list. The docs say "no level writes at super hard yet". Please
  confirm that is the intent.
- The plan calls the component `PatternCatalog`; the file `frames/PatternCatalog.tsx` exports `PatternGallery`. The
  docs use the real name.
- `components.md` (the `EnhanceDialog.tsx` row) says the gallery has **Select all**. The dialog's text (its header
  comment) names **Deselect all** and **Approved** only. Not verified in the UI (see Not checked).

## New terms for the glossary (Phase 20)

- **Level**: Easy, Medium or Hard for a hand, in Enhance with AI (the levels part of the dialog).
- **Pattern** and its **ref** (`right easy 1`): a figure of notes per hand and level from the catalog.
- **The catalog**: the list of patterns the AI may use (`patterns.json`).
- **The approved set**: the patterns used for a hand when none is ticked (the `defaults`).
- **Super hard**: the fourth level of the catalog's gallery (no run writes at it yet).
- **The grid**: where a new note of a level may start (frames of 40 ms).
- **The chords of the song**: a guitar guide pasted with the lyrics; saved with the part.
- **The level copy**: a whole song at one level, a new project in My projects (`<title> · Easy`).

## Not checked

- The gallery in the browser (no app was run): ticking a super hard pattern; **Select all** (see above).
- `api/projects.py` `levelSong` (line 294, `links.get(project.id)`): what the link is. Not read in detail; `projects.md`
  (Phase 14) owns it.
- The frame length (40 ms): stated in `grid.py`'s docstring; the constant was not found by grep.
- The migration file of revision `0010`: the revision is named in `07-database.md`; the file was not opened.
- The left hard approved set: the catalog's `about` says it was not tested in the research; the docs say so.

## Pending edits for shared files

- **E1 `documentation/services/backend/endpoints.md`**: insert after the row of `POST | \`/sheet/{uuid}/llm/level-copy\``
  (line 131):

  ```text
  | GET | `/sheet/{uuid}/chords` | Implementation 04-5 (2026-10-31): the song's chords of a guitar guide, saved with the part (`parts[].chords` in `project.json`): `{text}` (`""` when none). **Enhance with AI** opens with them; every level request saves its `chords` there (`LevelRequest.chords`) and sends them to the AI. |
  ```

- **E2 `documentation/services/frontend/components.md`**: insert after the row of `` `frames/EnhanceDialog.tsx` `` (line 264):

  ```text
  | `frames/PatternCatalog.tsx` | The gallery of patterns (`PatternGallery`, implementation 04-3, Phase 4): the tabs Easy, Medium, Hard, Super hard; each pattern drawn from `GET /sheet/levels/catalog/{hand}/{level}/{number}.svg`, with its name and line; the ticks (**Strict** or **Suggested**, `STRICTNESS`) |
  | `frames/patterns.ts` | `drawingUrl` (the drawing's route), `shortRef` (`medium 2`), `runTitle` (the title of a run in the history) |
  ```

- **E3 `context/00-index.md`**: insert after the row `[ai/whole-run.md](ai/whole-run.md)` (line 90):

  ```text
  | [ai/levels.md](ai/levels.md) | Levels: the catalog of patterns, the grid, the chords of the song, the level copy |
  ```

- **E4 `context/00-index.md`**: insert after the row `[../documentation/services/backend/ai-runs.md]` (line 294):

  ```text
  | [../documentation/services/backend/ai-levels.md](../documentation/services/backend/ai-levels.md) | The code of the levels: the catalog, the grid, the harmony, the hands, the chords of the song, the level copy, the dialog |
  ```

- **E5 `documentation/services/README.md`**: insert after the row `[ai-runs.md](backend/ai-runs.md)` (line 13):

  ```text
  | [ai-levels.md](backend/ai-levels.md) | The code of the levels: the catalog of patterns, the grid, the harmony, the hands, the chords of the song, the level copy |
  ```

## Checks

- `check-links.py`: 526 files, 0 broken links.
- `check-names.py` on the four files of this phase: `ai-levels.md` 0 missing; `levels.md` 1 missing, `level-run.md`
  (Phase 12 writes it; it is named in code style until then); `paths-and-data.md` and `07-database.md` list 7 and 1
  missing names, all on lines Phase 11 did not write (they were there before).

## Left for later phases

- Phase 12: `context/ai/level-run.md` (the plan, the rules, the batches, the check, Strict and Suggested, the
  explanations, the cost). In `levels.md`, turn the code-styled `level-run.md` into a link. In `ai-levels.md` section 8:
  `_level_work`, the prompt files of `sheet/llm/prompt/levels/`, `system_prompt`, `plan_prompt`, `batch_prompt`,
  `check_level` and the limits (`LIMITS`). `POST /llm/level` is already in `endpoints.md`.
- Phase 13: `context/ai/run-history.md`; the log (`ai-runs/<id>.json`) in `ai-levels.md` and `paths-and-data.md`;
  `GET /llm/runs` and the other three routes; `AiRunDetail`, `AiHistoryPanel`.
