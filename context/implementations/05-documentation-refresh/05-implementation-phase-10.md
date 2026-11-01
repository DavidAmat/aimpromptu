# 05, Phase 10: The AI, part 2: a stretch, Simplify, the Enhance with AI dialog

Wave B. Plan: [05-plan.md](05-plan.md) section 6, Phase 10. Checklist: [05-checklist.md](05-checklist.md).

## Docs changed

- `context/ai/stretch-and-simplify.md` (new, 185 lines): a stretch (the dialog's tab **A stretch**, the hands, the user's
  words, what the AI sees and may change, the checks, the batches, what is stored and the messages) and Simplify (the
  batches, the rules `simple.1` to `simple.4`, the answer lines, the checks, what is stored, the messages). It says that
  the dialog no longer offers Simplify.
- `documentation/services/backend/ai-runs.md` (sections 7 and 8 added, 202 lines): the functions, the constants, the
  routes and the tests of a stretch (`job.start_stretch`, `frames.write_stretch`, `stretch_request`, `check_answer`,
  `splice`, `edits.apply_stretch`) and of Simplify (`job.start_simplify`, `frames.write_simplify`, `simplify_windows`,
  `simplify_prompt`, `check_simplify`, `edits.apply_simplify`). The intro sentence that promised "Phase 10 adds" is
  replaced.
- Inventory: the row of `ai-runs.md` (State `updated`, 1 missing name), a new row for `stretch-and-simplify.md`.
- Checklist: Phase 10 ticked.

## What was stale

- Nothing in `context/` told a stretch or Simplify (the implementation records and the core README did).
- `ai-runs.md` said that Phase 10 would add the stretch and Simplify: now it does.
- The core README section 14 says "prompt 6" for Simplify; the prompt is version 7 (`PROMPT_VERSION = "7"`, the
  `simple.*` rules in `prompt/frames/instructions.md`). Fixed by the pending edit below.
- `context/ai/README.md` and `whole-run.md` point to this page as "a page Phase 10 writes": the pending edits make
  them links.
- `components.md`: the `EnhanceDialog.tsx` row already says **A stretch** (Both, Right, Left; the words or a level) and
  the batches. No change needed.
- `endpoints.md`: the rows of `/llm/stretch` and `/llm/simplify` are right, except that the Simplify row does not say
  the dialog no longer offers it (pending edit).

## Code and docs that disagree (for the user; not a doc fix)

1. **Simplify is not reachable from the dialog.** The dialog's tab **The whole song** calls `onSong("all", ...)` only
   (`EnhanceDialog.tsx` line 331); its header comment says the old Simplify run "is no longer offered here". The
   navigation state `enhanceWithAi: simplify-left | simplify-right | simplify-both` (`navigation.ts`) would still start
   it, but nothing in the code sends it (`SheetTab.tsx` `writeInCopy` gets the dialog's `all`). So
   `POST /sheet/{uuid}/llm/simplify`, `job.start_simplify`, `frames.write_simplify` and `api/sheet.ts` `simplify` are
   dead from the UI. **Your call**: remove them, or keep them for a later use. The docs describe them as they are.
2. Stale comments that still offer Simplify in the whole song: `aitu-frontend/src/pages/piece/sheet/frames/FramesSheetPage.tsx`
   line 18 (the header comment: "**Simplify** the left hand, the right..."); `useFramesSheet.ts` line 15 ("So is **Simplify**").
3. Code comments name "prompt 6" for the rules of Simplify: `frames.py` in `simplicity` (its docstring) and
   `check_simplify`. The prompt is version 7.
4. The code comment in `part_sheet/job.py` `start_simplify` says the summary has `simplify` values `ok`, `none`,
   `stale`, `failed`; the code also returns `gone` (the part deleted meanwhile). The docs list `gone`.

## New terms for the glossary (Phase 20)

- None for the app's words. The code's word **like passage** (`like_before`: an earlier passage that repeats the batch)
  is used in the page only in its own sentences.

## Not checked

- No run of the AI or the tests (the rules: no action in the app, no AI request). `tests/test_sheet_reading.py` and
  `tests/test_sheet_simplify.py` are named, not run; `npm run check:frames-tools` and `check:enhance-dialog` are named,
  not run.
- The format of the picked notes (`"<frame>:<midi>"`, `_place`) is read in the job, not traced in the page.
- The sheet's drawing of the batches of a stretch while the dialog is open: read in the dialog (`onPreview`), not in
  `FramesSheetView.tsx`.
- The limit of batches (1 to 60) comes from `RunChoice`, read in the route only.
- The cost figures are named by their constants (`USD_STRETCH`, `USD_BATCH`, `USD_CACHE`), not quoted.

## Pending edits for shared files

These are the edits for the join of wave B. Keep the order of the phases; the join applies them.

**P1. `aitu-backend/src/aitu_backend/sheet/README.md`, section 14** (owner in wave B: Phase 3):
In section 14 (`## 14. The note and range tools`), delete the three bullets **A stretch with the user's words**, **A
stretch of one hand** and **Simplify** (from their `- **` to the line before the next bullet or heading). Keep the
bullet `- Tests: ...` (it names `tests/test_sheet_reading.py`). Then add at the end of section 14, before `## 15.`:

> - **A stretch and Simplify** (implementation 03, Phase 7; implementation 04, Phase 4): `llm.frames.write_stretch`,
>   `write_simplify`, `job.start_stretch`, `job.start_simplify`, `edits.apply_stretch`, `edits.apply_simplify`. The
>   rules, the batches and the checks are told in [context/ai/stretch-and-simplify.md](../../../../context/ai/stretch-and-simplify.md);
>   the functions and the routes in [ai-runs.md](../../../../documentation/services/backend/ai-runs.md), sections 7 and 8.

**P2. `context/ai/README.md`** (owner 9; the join applies it):
- Table, row **A stretch**: the last cell "`stretch-and-simplify.md` (Phase 10 writes it)" → `[stretch-and-simplify.md](stretch-and-simplify.md)`.
- Table, row **Simplify** a hand: the text → "| **Simplify** a hand | The easier version of one hand, or both, over the song: no longer in the dialog, a level of that hand does it | The tab **The whole song**, as a level | [stretch-and-simplify.md](stretch-and-simplify.md) |".
- Section **Pages of this folder**: after the bullet `- [whole-run.md](whole-run.md): ...`, add
  `- [stretch-and-simplify.md](stretch-and-simplify.md): a stretch of the sheet with the user's words, and Simplify.`
- The paragraph "The other pages of the folder ... : the stretch and Simplify, the levels, the level run and the history of
  runs." → replace "the stretch and Simplify, the levels," by "the levels,".

**P3. `context/ai/whole-run.md`** (owner 9), step 2: replace ", a page Phase 10 writes.)" by ".)", so the sentence ends
"... which is told in `context/ai/stretch-and-simplify.md`.)".

**P4. `documentation/services/backend/endpoints.md`** (shared), section 4.1, the row `POST /sheet/{uuid}/llm/simplify`: replace
"409 while the AI works on the part. |" by "409 while the AI works on the part. The dialog no longer offers it: a hand is
simplified as a level (`POST /sheet/{uuid}/llm/level`). |".

**P5. `context/00-index.md`** (the join), the group **The AI** (`context/ai/`): after the row of `ai/whole-run.md`, add
`| [ai/stretch-and-simplify.md](ai/stretch-and-simplify.md) | A stretch of the sheet with the user's words, and Simplify: the batches, the rules, the stored run |`.

`components.md`, `documentation/services/README.md` and `02-tech-stack.md`: no change from this phase.

## Checks

- `check-links.py`: 526 files, 0 broken.
- `check-names.py` on `stretch-and-simplify.md` and `ai-runs.md`: 4 missing, all `level-run.md` (Phase 12 writes it:
  three in the new page, one in `ai-runs.md` section 8). The other names are found.

## Left for later phases

- Phase 11: `context/ai/levels.md` (exists in the tree now) and `ai-levels.md`: the page links the level of one hand as
  the way to simplify it. Phase 11 writes the names of its functions; nothing from this page depends on them.
- Phase 12: `context/ai/level-run.md`: the four links to it (in `stretch-and-simplify.md` and `ai-runs.md` section 8)
  resolve then. Also the level of one hand ("Simplify") in the plan of a level run.
- Phase 20: the glossary: nothing new in the app's words (section above).
