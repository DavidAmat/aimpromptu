# 04: The context of the polished sheet, for every later implementation

Audience: the agent of any later implementation in aimpromptu. Read this file after
[`../03-apply-poc-research/03-context.md`](../03-apply-poc-research/03-context.md) when a task touches the sheet page,
the decoration notes (grace notes), the AI's prompt, the notes the AI adds or leaves out, or **Enhance with AI**. It
says what implementation 04 changed on top of 03, which decisions now bind, where the code is, and which phase report
tells how each part was done and measured. 03's context stays true except where this page says otherwise.

State: done on 2026-10-28. Five phases, one branch each (`feat/04-phase-1` to `feat/04-phase-5`), each merged into
`master` after the user's check; the new logo (prompt `04-2-prompt.md`) on its own branch `feat/04-logo`. Folder
index: [`README.md`](README.md). Status of every task: [`04-checklist.md`](04-checklist.md).

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
          ── POST /sheet/{uuid}/llm/simplify  write_simplify(staff), batch after batch -> edits.apply_simplify
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
| Simplify | `frames.simplify_windows` (`SIMPLIFY_MS = (24000, 32000)`, `SIMPLIFY_ONSETS = 300`), `like_before`, `like_columns`, `simplify_prompt`, `check_simplify` (`renamed`), `write_simplify`, `Change`, `Simplified`; `job.start_simplify`, `LiveRun.advanced`, `LiveRun.staff`; `edits.apply_simplify`, `SIMPLIFY_LABELS` |
| Costs | `job.costs`: `USD_CACHE = 0.04`, `USD_WINDOW = 0.038`, `USD_BATCH = 0.008`, `USD_STRETCH = 0.02` |

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
| The Enhance with AI dialog, a stretch of one hand, Simplify, the costs, a note whose name changed | [phase 4](04-implementation-phase-4.md) | [`gallery/phase-4/`](gallery/phase-4/index.html); `scripts/simplify_gallery.py`; `npm run check:enhance-dialog` |
| The documentation, this page, the final checks | [phase 5](04-implementation-phase-5.md) | |

# 6. Checks

The checks of 03 ([`03-context.md`](../03-apply-poc-research/03-context.md) section 6), and: the tests
`tests/test_sheet_simplify.py` (no credits; stand-ins answer for the AI), the new cases of `test_sheet_frames.py`,
`test_sheet_llm_frames.py` and `test_part_sheet.py`; the browser checks `npm run check:frames-page` and
`npm run check:enhance-dialog` (a stand-in in the browser answers the requests that would start the AI).

# 7. Open points

- **7 Years in My library** (`1a16a836`) still holds its prompt 5 sheet. The prompt 6 run is on the edit copy in
  the Personal Vault (`477086a0`, the user's answer of Phase 3); the library version changes when the user saves
  that copy to the library (**Save to library** → **Replace**).
- The other songs keep their prompt 5 sheets until the user runs **Enhance it again with AI** or **Simplify** on
  them (credits: about $0.65 a whole run, $0.10 to $0.20 a Simplify of one hand).
- A Simplify run, like a whole run, is not saved batch by batch: a backend reload stops it and loses it.
- Simplify's cost estimate is low on dense songs (Moonlight Shadow: $0.10 estimated, $0.21 measured): more thinking
  per batch.
- 03's open points ([`03-context.md`](../03-apply-poc-research/03-context.md) section 8) are still open.
