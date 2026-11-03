# 04: The context of the polished sheet, for every later implementation

Audience: the agent of any later implementation in aimpromptu. Read this file after
[`../03-apply-poc-research/03-context.md`](../03-apply-poc-research/03-context.md) when a task touches the sheet page,
the decoration notes (grace notes), the AI's prompt, the notes the AI adds or leaves out, or **Enhance with AI**. It
says what implementation 04 changed on top of 03, which decisions now bind, where the code is, and which phase report
tells how each part was done and measured. 03's context stays true except where this page says otherwise.

State: done on 2026-10-28. Five phases, one branch each (`feat/04-phase-1` to `feat/04-phase-5`), each merged into
`master` after the user's check; the new logo (prompt `04-2-prompt.md`) on its own branch `feat/04-logo`. Folder
index: [`README.md`](README.md). Status of every task: [`04-checklist.md`](04-checklist.md). The Simplify run this
page tells of was removed in 04-6, its code too (section 9): what the page says of it is the record of 04.

# 1. What implementation 04 did

Using the sheet of 03, the user found things to polish in two places ([`04-1-prompt.md`](04-1-prompt.md), the brief
with the answers of the first discussion; [`04-plan.md`](04-plan.md), the plan, with the changes each phase made in
its section 9):

- **The sheet page** (Phase 1): ⌘ and the wheel (or a trackpad pinch) zoom the sheet and lay it out again for the
  window; the AI mark next to the title instead of the green badge; the floating toolbox's buttons also in a header
  that stays at the top; a hidden floating toolbox that is seen and comes back; a cursor that can be dragged and
  dropped, also to another line.
- **The new logo** (prompt [`04-2-prompt.md`](04-2-prompt.md)): `images/the-logo.png` traced to one SVG path
  (`ui/Logo.tsx`, drawn in the colour of the text around it); the sidebar, the sign-in page and the favicons use it;
  it is also the **AI mark** (`components/piece/AiMark.tsx`: green, "Enhanced with AI"; faint grey, "Not enhanced
  with AI yet") and the icon of every **Enhance with AI** button.
- **The decoration-note rule** (Phase 2), on every sheet when it is drawn.
- **Prompt version 6** (Phase 3): the rules of simplicity and the amateur pianist rule; a whole run may add and
  leave out a few notes, which go into `notes.pmn`. Run on 7 Years ($0.63).
- **The Enhance with AI dialog** (Phase 4): a stretch of both hands or of one (the other then fixed), and for the
  whole song **Simplify** the left hand, the right hand or both (the rules of simplicity only, batch after batch),
  or **Write it all again** (the whole run of 03).

# 2. The decisions that bind later work

| Decision | Where it is told |
|---|---|
| **Decoration notes**: one or two columns of one hand, all **fusas or shorter**, two figures or more shorter than the next note of their hand, sounding just before it. A run of three or more stays written. Changes the grace-note row of 03 | plan 3.1; [phase 2](04-implementation-phase-2.md) section 3 |
| **A lone short note** (one or two columns, not a decoration note) just before a note more than two figures longer is written two figures shorter than that note (a semicorchea before a blanca: a corchea); the end of a run of three or more is never lengthened | plan 3.1; [phase 2](04-implementation-phase-2.md) section 3 |
| The user's marks win over the rule: `asgrace` is a decoration note whatever its figure, `nograce` never, a `fix` figure is never lengthened | plan 3.1 point 4 |
| The rule runs on **every sheet when it is drawn**: every stored `sheet.f1` is laid again on its notes (`build.reapply`); the stored files are not rewritten by the rule | plan 3.2; [phase 2](04-implementation-phase-2.md) section 4 |
| Prompt 6: **rules of simplicity** (simple.1 a repeated pattern written the same way every time; simple.2 the amateur pianist: a quick chord just before a main note keeps only the notes within an octave of it; simple.3 no note moves to another frame or name; simple.4 change little) | plan 4.3; [phase 3](04-implementation-phase-3.md) section 3 |
| The AI may add and leave out notes, **declared** in comment lines (`# leave out f1822 G2`, `# add f4556 D1`) and within limits: a column never loses all its near notes, an added note joins a column of its hand within an octave and with a name of that column or of the 8 around, at most a tenth of a window (4 at least). An undeclared change is an error | plan 9 (Phase 3); [phase 3](04-implementation-phase-3.md) section 5 |
| The notes the AI adds or leaves out go into `notes.pmn` (left out: marked removed, not deleted), as a stretch does (`edits.change_notes`); the audio does not change | plan 3.3; [phase 3](04-implementation-phase-3.md) section 6 |
| A whole run still starts the steps of undo again, with one step "Notes the AI added and left out" when it changed notes; a Simplify run is one step | [phase 3](04-implementation-phase-3.md) section 6; [phase 4](04-implementation-phase-4.md) section 5 |
| A stretch of **one hand** (Right or Left of the range toolbox or the dialog) changes that hand only; the other hand stays exactly as it is (the prompt shows it, the check refuses a change, `splice` keeps it) | plan 3.5; [phase 4](04-implementation-phase-4.md) section 4 |
| **Simplify** does the rules of simplicity only; hands, beams, clefs and the other hand do not move; a batch answers only the change lines with their reason; each batch sees every change before it, the earlier passage most like it, and the end of the batch before | plan 3.5, 9 (Phase 4); [phase 4](04-implementation-phase-4.md) section 5 |
| Simplify keeps each note's name as a recommendation: a name may change only when the earlier passage like this one has the new note at the same place (found by the 2 columns around it) (user, 2026-10-28) | [phase 4](04-implementation-phase-4.md) section 8 |
| The AI mark is the logo; the page says "AI", never the model's name; the mark is never lost (03's rule kept) | `04-2-prompt.md`; [phase 1](04-implementation-phase-1.md) section 3 |
| The sheet's buttons are **one list** (`sheetButtons`) drawn in the header and the floating toolbox; a new button goes there once | [phase 1](04-implementation-phase-1.md) sections 3 and 7 |
| Only 7 Years ran with prompt 6; the other songs keep their prompt 5 sheets until the user runs the AI on them (credits) | plan 2 |

# 3. What changed in how the sheet works

## 3.1 The files of a part

The files of 03 ([`03-context.md`](../03-apply-poc-research/03-context.md) section 3.1) are the same. New in the
record line of `sheet.f1` (`part_sheet.store.Record`): `prompt` `6` or `6+hands`; `added` and `leftOut` (the notes a
whole run added and left out; written only when not 0); `simplified` (one row per Simplify run: hand, added, left
out, usd, written, change lines). `notes.pmn` now also holds the notes the AI added and marks removed the ones it
left out.

## 3.2 The backend

```text
notes.pmn ── propose_frames / assemble: figures, find_graces (fusas or shorter), lengthen_lone, beam groups
          ── part_sheet.build: every stored sheet laid again (reapply), except a text an edit just stored
          ── POST /sheet/{uuid}/llm           write_frames, prompt 6, places to check, declared changes
          ── POST /sheet/{uuid}/llm/stretch   write_stretch(staff=None | 1 | 2)
          ── POST /sheet/{uuid}/llm/simplify  write_simplify(staff), batch after batch (removed in 04-6)
          ── GET  /sheet/{uuid}/llm/costs     the dialog's estimates (job.costs)
```

| Part | Code |
|---|---|
| The decoration-note rule | `sheet/proposal/frames.py`: `find_graces` (`RUN_FIGURE = 16`, `GRACE_FIGURE = 32`), `lengthen_lone`; `sheet/llm/frames.py`: `beam_pairs` (two written notes a stored sheet held as a pair of decoration notes get one beam, once) |
| Every sheet drawn with it | `part_sheet/build.py`: `_compute` (case 1 through `reapply`), `mark_settled` / `_settled` (a text an edit stored is drawn as it is: one edit stays at about 0.28 s) |
| Prompt 6 | `sheet/llm/prompt/frames/instructions.md`, `VERSION`; `frames.PROMPT_VERSION = "6"`; example 5 |
| Places to check | `frames.places` (`far_quick`, `broken_octaves`), listed in the window prompt under "Places to check"; the AI decides each one |
| The check of note changes | `frames.declared`, `frames.simplicity` (`NEAR = 12`, `PATTERN_COLUMNS = 8`, `CHANGE_MIN = 4`, `CHANGE_SHARE = 0.1`), `check_answer(simplify=True)` |
| Storing a whole run's changes | `Part.added`, `frames.placed`, `FramesSong.changes()`; `job.commit(changes=)`; `edits.change_notes`, `edits.record_run` |
| A stretch of one hand | `window_prompt(fixed=)`, `stretch_request(staff=)`, `check_answer(hand=)`, `write_stretch(staff=)`, `splice(keep=)`, `edits.apply_stretch(staff=)` |
| Simplify (removed in 04-6, section 9; `like_before` and `LiveRun.staff` stay, for the level runs) | `frames.simplify_windows` (`SIMPLIFY_MS = (24000, 32000)`, `SIMPLIFY_ONSETS = 300`), `like_before`, `like_columns`, `simplify_prompt`, `check_simplify` (`renamed`), `write_simplify`, `Change`, `Simplified`; `job.start_simplify`, `LiveRun.advanced`, `LiveRun.staff`; `edits.apply_simplify`, `SIMPLIFY_LABELS` |
| Costs | `job.costs`: `USD_CACHE = 0.04`, `USD_WINDOW = 0.038`, `USD_BATCH = 0.008` (Simplify's, removed in 04-6), `USD_STRETCH = 0.02` |

The core's [`README.md`](../../../aitu-backend/src/aitu_backend/sheet/README.md) is still the reference: section 9 the
rule, 11 prompt 6 and the check, 12 the drawing of every sheet and a whole run's note changes, 14 a stretch of one
hand and Simplify. The routes: [`documentation/services/backend/endpoints.md`](../../../documentation/services/backend/endpoints.md).

## 3.3 The frontend

`aitu-frontend/src/pages/piece/sheet/frames/`:

- `FramesSheetPage.tsx`: the header (`data-sheet-header`, `position: sticky`: the title, `AiMark`, `sheetButtons`,
  the toggle of the floating toolbox), the hidden state of the floating toolbox (`aitu.framesSheet.floatingHidden`
  in the browser), ⌘ and the wheel zoom (a CSS scale at once, one `GET /sheet` at a pause of 220 ms, the line under
  the pointer kept under it), the Enhance with AI dialog and the end notice of Simplify.
- `FramesSheetView.tsx`: the cursor dragged and dropped (`grab`, `grabbing`, `data-dragging`; a press that does not
  move stays a click); the veil and the reveal cover one staff when the AI writes one hand (the segment's `staff`).
- `EnhanceDialog.tsx` (was `EnhanceStretchDialog.tsx`): **A stretch** (Both, Right, Left, the words) and **The whole
  song** (the four runs and their cost).
- `ui/FloatingBar.tsx`: the round button of a hidden bar where its hide button was, with a border and an eye.
- `ui/Logo.tsx`, `components/piece/AiMark.tsx`: the logo and the AI mark.

The pages for a reader: [`context/frontend/projects.md`](../../frontend/projects.md) (the Sheet step),
[`context/frontend/annotations.md`](../../frontend/annotations.md) (the tools),
[`context/frontend/rendering.md`](../../frontend/rendering.md) (the code and the hooks); the components:
[`documentation/services/frontend/components.md`](../../../documentation/services/frontend/components.md).

# 4. Rules for a new change

03's rules ([`03-context.md`](../03-apply-poc-research/03-context.md) section 4) still hold. Added by 04:

- **A change of the decoration-note rule or of any rule of `assemble`** changes every stored sheet at once (they are
  laid again when drawn). Measure it on every stored sheet of My library before and after (Phase 2 did it with
  `scripts/grace_gallery.py --study`): only the columns the rule is about may change.
- **A change of the prompt** gets a new `VERSION`; the record of each sheet keeps the version it was written with.
- **A new AI run kind** that changes notes uses `edits.change_notes` and stores one step of undo, so the edits, undo
  and the next run see one truth.
- **A new sheet button** goes into `sheetButtons` once; the header's copy has the `data-testid` `header-<name>`; a
  check that finds a button by its name finds two.
- **A run of one hand** sends the segments with `staff`, so the page veils that staff only.

# 5. Where to find how a part was done

| Topic | Phase report | Also |
|---|---|---|
| The header, the floating toolbox and why it did not seem to come back, the wheel zoom, the cursor dragged | [phase 1](04-implementation-phase-1.md) | [`screenshots/phase-1/`](screenshots/phase-1/); `npm run check:frames-page` |
| The decoration notes of My library before and after, the rule, every sheet laid again, two written notes with one beam | [phase 2](04-implementation-phase-2.md) | [`gallery/phase-2/`](gallery/phase-2/index.html); `scripts/grace_gallery.py` |
| Prompt 6, places to check, the check of note changes, storing them, the tests and the real run on 7 Years | [phase 3](04-implementation-phase-3.md) | [`gallery/phase-3/`](gallery/phase-3/index.html); `scripts/simplicity_gallery.py` |
| The Enhance with AI dialog, a stretch of one hand, Simplify, the costs, a note whose name changed | [phase 4](04-implementation-phase-4.md) | [`gallery/phase-4/`](gallery/phase-4/index.html); `scripts/simplify_gallery.py` (removed in 04-6); `npm run check:enhance-dialog` |
| The documentation, this page, the final checks | [phase 5](04-implementation-phase-5.md) | |

# 6. Checks

The checks of 03 ([`03-context.md`](../03-apply-poc-research/03-context.md) section 6), and: the tests
`tests/test_sheet_simplify.py` (renamed `test_sheet_stretch_one_hand.py` in 04-6, its Simplify tests removed; no credits; stand-ins answer for the AI), the new cases of `test_sheet_frames.py`,
`test_sheet_llm_frames.py` and `test_part_sheet.py`; the browser checks `npm run check:frames-page` and
`npm run check:enhance-dialog` (a stand-in in the browser answers the requests that would start the AI).

# 7. Open points

- **7 Years in My library** (`1a16a836`) still holds its prompt 5 sheet. The prompt 6 run is on the edit copy in
  the Personal Vault (`477086a0`, the user's answer of Phase 3); the library version changes when the user saves
  that copy to the library (**Save to library** → **Replace**).
- The other songs keep their prompt 5 sheets until the user runs **Enhance it again with AI** (or a level) on
  them (credits: about $0.65 a whole run).
- (Closed by 04-6: Simplify was removed. It was not saved batch by batch, and its estimate was low on dense songs.)
- 03's open points ([`03-context.md`](../03-apply-poc-research/03-context.md) section 8) are still open.

# 8. Later work: implementations 04-3 and 04-5 (added 2026-11-01)

Sections 1 to 7 describe implementation 04. The work after it, **04-3** (2026-10-29 to 31) and **04-5** (2026-10-31),
has its own plans and reports, which stay the record. This section says what changed, which decisions bind, where the
code is, and what is open. The documentation of both is in the documentation refresh (05): the AI pages of
[`context/ai/`](../../ai/README.md) and the frontend pages linked below. 04-3's own documentation phase (its Phase 6)
never ran; the refresh does that work, and 04-5's task 5.2 is closed the same way.

## 8.1 What changed in 04-3

- **Folders and metadata of projects**: the folder tree, the pills (Folders, All, Filter), the metadata and the info
  button. Plan [`04-3-plan.md`](04-3-plan.md) section 4; [phase 1](04-3-implementation-phase-1.md). Page:
  [folders-and-metadata.md](../../frontend/folders-and-metadata.md).
- **Frame marks** on the sheet and frames typed in the range toolbox: [phase 2b](04-3-implementation-phase-2b.md).
  Pages: [sheet-page.md](../../frontend/sheet-page.md), [annotations-stretches.md](../../frontend/annotations-stretches.md).
- **The levels**: a level copy of the whole song, the catalog of patterns, and the level run with its plan and batches
  (plan section 5; [phases 2 to 4](04-3-implementation-phase-4.md)). Pages: [levels.md](../../ai/levels.md),
  [level-run.md](../../ai/level-run.md), [ai-levels.md](../../../documentation/services/backend/ai-levels.md).
- **The model**: every AI run uses one OpenAI model at `medium`, chosen by measure in
  [phase 5](04-3-implementation-phase-5.md) (section 10, the models; plan section 5.9 first said an Anthropic one).
  Since 04-6 the model is a setting (section 9). Page: [ai/README.md](../../ai/README.md).

## 8.2 What changed in 04-5

- **Strict and Suggested** for each ticked pattern (the default is Suggested). A Strict hand plays its pattern on every
  chord, the same way through the song.
- **The rules and the explanations** of a run: the plan writes one rule per pattern, each batch explains itself in
  simple words and may add a rule.
- **The first batch first**: a run of two batches or more writes batch 1 and waits. **Go on with the other batches**
  writes the rest.
- **Write this batch again**, from the history, with the user's answer; the **History of AI runs** and its log
  (`ai-runs/<id>.json`, the four routes of `/llm/runs`).
- **The chords of the song** (a guitar guide, saved with the part), and a new left easy 1 (the other left easy patterns
  one number up).
- Pages: [level-run.md](../../ai/level-run.md), [run-history.md](../../ai/run-history.md),
  [levels.md](../../ai/levels.md); the code in
  [ai-levels.md](../../../documentation/services/backend/ai-levels.md) section 9.

## 8.3 The decisions that bind

- The model of every AI run is the setting `AITU_LLM_MODEL` (04-6, section 9; its default is the model 04-3 chose, 8.1).
- A level run of two batches or more writes its first batch and waits; the user checks it on the sheet first (the
  user, 2026-10-31).
- A batch is written again only from the history, one at a time, with the user's answer.
- The check decides what reaches the sheet, not the AI: a batch the check refuses three times keeps the earlier notes,
  and the sheet does not change.
- A Strict pattern may be changed in shape by the user's words; the changed shape is the Strict one (the words of 04-5,
  2026-10-31).

## 8.4 Where the code is

- Backend: `sheet/llm/levels.py` (the prompts, the check, `write_again`), `sheet/llm/prompt/levels/` (the prompt files
  and `VERSION`), `sheet/levels/` (the grid, the harmony, the hands), `part_sheet/job.py` (`start_level`,
  `continue_level`, `again_batch`), `part_sheet/runs.py` (the log), `api/sheet.py` (the routes).
- Frontend, in `pages/piece/sheet/frames/`: `EnhanceDialog.tsx`, `PatternCatalog.tsx`, `patterns.ts`, `AiRunPanel.tsx`,
  `AiRunDetail.tsx`, `AiHistoryPanel.tsx`, `batches.ts`.

## 8.5 Open points

- (Closed by 04-7, Phase 1: **the octaves of the user's words**, 04-5 report, finding 1. Decided by the user on
  2026-10-31, [`04-5-checklist.md`](04-5-checklist.md) Decisions: the octave numbers in the user's words are only
  examples, and the AI chooses what reads best on the staff. The level prompt says it
  (`sheet/llm/prompt/levels/shared.md`, "The register"). No code.)
- **Hard and the figure check**: `LIMITS["hard"]` has `shortest` 64, so the figure check never fires at hard (the
  Phase 12 report of the refresh). Please confirm that this is intended.
- **A Stop keeps the batches it accepted** (the level run's page says so). If the user expects a Stop to discard the run,
  the dialog and the code disagree.
- **The temporary copies** of the 04-5 real runs (on 20 de Enero) were kept until the user had looked at the pages.
  Delete them after that.
- The 04-5 run cost was about $0.47 of the $2 the user allowed, measured on those copies (04-5 report, section 4).

# 9. Later work: implementation 04-6 (added 2026-11-03)

04-6 has its own brief, plan, checklist and phase reports ([`04-6-plan.md`](04-6-plan.md)), which stay the record.
Branch `feat/04-6-run-safety-and-model`, merged into `master` only at the user's ok.

## 9.1 What changed

- **A run left after a crash** (Part A): at each start of the backend, `part_sheet/runs.close_unfinished` (called by
  `main.lifespan`) marks every log `ai-runs/<id>.json` still `running` as `stopped`, with the note "The backend
  stopped during the run."; a batch marked written whose notes never reached the sheet becomes not written (`error`),
  and keeps its conversation, so **Write this batch again** still works. The note shows in the run's detail of
  **History of AI runs**. The other marks of a run in progress are not stored, or are removed when the run starts
  (plan section 3.1). Page: [run-history.md](../../ai/run-history.md).
- **The model of the LLM in one place** (Part B): the setting `AITU_LLM_MODEL` (`config.llm_model`) and one table,
  `aitu_backend/llm_models.py` (labels, providers, efforts, prices, measured ratios). `GET /sheet/{uuid}/llm/costs`
  answers the dialog's choices (`models`) and the setting's model (`model`); the frontend keeps no list. A model
  never measured takes its cost ratio from its prices; with no price it costs $0, with a warning, and never stops a
  run. The code's comments say "the LLM", the page "the AI". Page: [ai/README.md](../../ai/README.md), the only page
  of the docs that names the default model.
- **Simplify removed** (Part C): its route, job, frames code, cost keys, script and frontend calls. Its tests of code
  that stays are in `tests/test_sheet_stretch_one_hand.py`. The rules of simplicity of the whole run stay, and so does
  the record's `simplified` field of old sheets.

## 9.2 The decisions that bind

- No model's name in the code, the comments or the docs, except: the default of `config.py`, the table of
  `llm_models.py`, `llm_models.MEASURED_WITH` (a dated measure), [ai/README.md](../../ai/README.md), and history (a
  measure, an implementation's record, a golden file).
- A new model: add it to `llm_models.TABLE` (with `choice` on to offer it) and, to make it the default, set
  `AITU_LLM_MODEL`. The page needs no change.
- The dialog sends a model only when the user chose one; left on the setting's, the backend uses the setting.

## 9.3 Open points

- **The fresh backend image has no `openai`** (Phase 4 report, section 3): the image of 2026-10-25 was built before
  `openai` entered `pyproject.toml`; the running container has it installed by hand. `docker compose build backend`
  fixes it, at a time the user chooses.
- **Two Transkun tests fail on the CPU** (a checkpoint saved on the GPU, loaded without `map_location`): not related
  to 04-6.
- A level copy made just before a crash stays as a project of My projects, holding the song as it was (plan section
  3.1).
