# 05, Phase 12: The AI, part 4: the level run

The plan is [`05-plan.md`](05-plan.md); the checklist is [`05-checklist.md`](05-checklist.md). Wave C (with Phases 4,
7, 16, 17). Read: the code of `sheet/llm/levels.py` (the prompts, the plan, the batches, the check, `write_level`),
`prompt/levels/` (`shared.md`, `easy.md`, `medium.md`, `hard.md`, `feedback.md`, `VERSION` = 7), `part_sheet/job.py`
(`start_level`, `_level_work`, `continue_level`, `costs`, `level_cost`, `batch_plan`), `api/sheet.py` (`LevelRequest`,
`_start_level`, `/llm/level`, `/llm/level-copy`). No code was changed, no app was run.

## Docs changed

- `context/ai/level-run.md` (new, 192 lines): what a level run does, in order (the plan, the batches, the check, the
  store, the wait); the plan and its summary; the rules of a run; the batches and what a batch request holds; the check
  with its limits per level (one table); Strict and Suggested; the patterns of a run; the cost and the time.
- `documentation/services/backend/ai-levels.md`: section 8 is now the level run, in five parts (the prompts, the check
  and the run in `levels.py`, the measures in `sheet/levels/`, the job in `job.py`, the request in `api/sheet.py`);
  section 9 is a placeholder for Phase 13. The intro and "Where to look deeper" point to the new page.
- `context/ai/levels.md`: the sentence "`level-run.md` (Phase 12, not yet written)" is now a link.

## What was stale

- `ai-levels.md` section 8 was a placeholder ("Phase 12 adds the level run"), and its intro pointed to it.
- `levels.md` said the level run was not written yet.
- The `endpoints.md` row of `POST /sheet/{uuid}/llm/level` lacks `strict`, `chords`, `batches`, `model`, the
  `waiting` state, and the 409 "not set up" answer. See the pending edit E12.1.

## Code and docs that disagree in a way that looks like a bug (for the user)

- `sheet/llm/levels.py`, `LIMITS["hard"]`: `shortest` is 64, so the figure check (a new note shorter than the shortest
  allowed) never fires at hard. The comment of `Limits.shortest` says it is the shortest figure of a new note. This may
  be intended (hard may use the fusa), but the comment and the value do not say so. The page says "the figures are not
  checked for length at hard". Please confirm.
- Question, not a bug found: `part_sheet/job.py`, `_level_work`, and `sheet/llm/levels.py`, `write_level`. A Stop (or any
  other error) ends the batches, and the batches accepted before it are stored as one step. The page says so. If the
  user expects a Stop to discard the run, the code and the dialog disagree. Please confirm.

## New terms for the glossary (Phase 20)

- **decided context**: the end of the previous batch as written (the last 6 seconds), given to the next batch.
- **look-ahead**: the next 4 seconds of notes, shown to a batch and not written.
- **target** (of a batch): the notes of the batch as the sheet has them now; the AI writes them again.
- **the plan's section** (`S1 f33-f780 L=… R=… | why`): a part of the song that keeps one pattern per hand.
- **rule** (of a run): how the song plays a pattern, or a decision a batch took; every later batch follows it.
- **explain**: the `# explain:` lines of a batch, for the user, in simple words.
- **riff**: the top notes of the left-hand chords, when the right hand has no melody there.
- **artifact**, **not melody**, **keep**, **free**: the words of the declared lines and the plan's refs.

## Not checked

- The run itself (no run in the app, per the rules). Behaviour is from reading the code.
- The frontend: the levels part of `EnhanceDialog.tsx`, `PatternCatalog.tsx` and the waiting state of `AiRunPanel.tsx`
  were not read (not in this phase's file list). The page says what the dialog sends, from the backend's side only.
- The cost numbers were read from the constants in `job.py`; they were not measured again.
- `check-names.py`: one missing name, `run-history.md` (Phase 13 writes it); the link is not written, so the links check
  passes. `check-links.py`: 534 files, 0 broken links.

## Pending edits for shared files

- **E12.1** `documentation/services/backend/endpoints.md`, the row `POST | /sheet/{uuid}/llm/level` (section "Implementation
  04-3, Phase 4"). Replace the row's text with:

  > Implementation 04-3, Phase 4; changed by 04-5: a level of a range, in place: `{right, left: easy | medium | hard, hand: both | right | left, start, end, patterns, words, exact, strict, chords, batches, model}`; the plan of the range, then batches (each checked, at most three replies each); one step of undo. `exact` (the dialog's **Deselect all**): `patterns` are exactly the ticks, so a hand with none has no pattern (written `free`); without it a hand with none gets `defaults`. `strict`: the ticked refs written Strict. `chords`: the guide of the song, saved with the part (`null` keeps the saved one). The run writes its first batch and waits when it has two batches or more (`waiting` in the `done` summary); `continue` and `again` are in the run's routes. The job's `done` summary: `level` (`ok`, `failed`, `stale`, `gone`), `batches`, `total`, `levelName`, `usd`, `run`, `waiting`, `note`. 202 `{jobId, status}`. 400 without a range, 403 on a sheet the user cannot change, 409 while the AI works on the part or when the AI is not set up.

- **E12.2** `context/00-index.md`, section "The AI (`context/ai/`)", after the row `| [ai/levels.md](ai/levels.md) | ...`: add
  `| [ai/level-run.md](ai/level-run.md) | A level run: the plan of the song, the batches, the rules, the check and its limits per level, Strict and Suggested, the explanations, the cost |`

- **E12.3** `context/00-index.md`, row `[../documentation/services/backend/ai-levels.md]` (around line 298): add "the level run" to its description, before "the dialog".

- **E12.4** `documentation/services/README.md`, the row of `ai-levels.md` (line 15): add ", the level run" to its description, after "the level copy".

- **E12.5** `context/ai/README.md`: (a) in the table row of "A level", remove "(Phase 11)" and "(Phase 12)" from the last cell, so it reads `` `levels.md`, `level-run.md` ``; (b) in the list of pages of this folder, after the line `- [levels.md](levels.md): ...`, add
  `- [level-run.md](level-run.md): a level run: the plan, the batches, the rules, the check, Strict and Suggested.`

- **E12.6** `context/ai/stretch-and-simplify.md` (Phase 10's page, now a sibling): line 26, replace "`levels.md` (written by Phase 11) and `level-run.md` (Phase 12)" by "`levels.md` and `level-run.md`"; line 185, replace "(written by Phases 11 and 12)" by nothing.

- **E12.7** `documentation/services/backend/ai-runs.md`, line 176: replace "(`ai-levels.md` and `context/ai/level-run.md`, Phases 11 and 12)" by "(`ai-levels.md` and `context/ai/level-run.md`)".

## Commit note for the join

- Commit `d17ad3d` holds my files, and also, in the two shared tracking files, the lines another agent of wave C had
  written on disk before my commit: the ticks of Phase 17, the report link of Phase 16 and 17 and their inventory rows,
  and the inventory row of `piano-matrix-notation.md` and the other Phase 16 rows. The working tree is unchanged. The
  Phase 16 and 17 reports were not yet committed when `d17ad3d` was made. Nothing to undo: the join should check that
  these lines are right.

## Left for later phases

- Phase 13: `context/ai/run-history.md` (the link from `level-run.md` to it is not written yet: it is named in backticks
  in section "What the run does", step 5; make it a link when the page exists). `ai-levels.md` section 9 (the log, the
  routes, `write_again`, `answer.md`).
- Phase 20: the glossary terms above.
- Not touched: `context/frontend/`, `components.md` (the dialog's levels part is Phase 11's pending edit, not mine).
