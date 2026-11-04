# 06, Phase 3: the frontend

Plan: [`06-plan.md`](06-plan.md) sections 4.2 (the dialog) and 4.5 (the panel and the history). Checklist:
[`06-checklist.md`](06-checklist.md), Phase 3. Branch `feat/06-copy-this-style`. No AI request: a stand-in in the browser
answers every request that would start the AI. The phase before:
[`06-implementation-phase-2.md`](06-implementation-phase-2.md).

# 1. Summary

| Part | Where (`aitu-frontend/src/pages/piece/sheet/frames/` unless said) |
|---|---|
| The tab, its status line, its button | `EnhanceDialog.tsx` (`EnhanceTab` `style`, `onStyle`) |
| The list: the reference, the passages, the ticks, Select all, Deselect all | `StylePassageList.tsx` (new) |
| The number of a batch in its colour (was two copies in the panels) | `BatchNumber.tsx` (new) |
| The reference and the passages on the sheet | `batches.ts` (`BatchPreview.reference`, `.places`, `REFERENCE_COLOUR`, `batchColour`, `passageKey`), `FramesSheetView.tsx` (`referenceBoxes`) |
| The start, the end messages, `checking` | `useFramesSheet.ts` (`copyStyle`, `endNotice`, `RunSummary.style`), `FramesSheetPage.tsx` (`sendStyle`) |
| The run's panel | `AiRunPanel.tsx` (`checking`, the count from the summary, no Revert when nothing was written) |
| The history and the run's detail | `AiRunDetail.tsx` (`StyleCheck`, `copiedText`), `AiHistoryPanel.tsx` (`dropped`), `patterns.ts` (`runTitle` with `kind`) |
| The types and the calls | `src/api/sheet.ts` (`stylePassages`, `copyStyle`, `StylePassages`, `AiRunPassage`...) |
| The browser check | `scripts/check-copy-style.mjs`, `npm run check:copy-style` |
| Two small backend additions | `part_sheet/job.py`: `costs` in the `GET` answer, `checking` in the event `style` |

Checks: `npx tsc -b` and `eslint` clean; `check:copy-style`, `check:enhance-dialog`, `check:ai-run-panel`,
`check:ai-history` all passed; the backend suite on CPU 1392 passed, 1 skipped; `flake8` clean on the changed files.

# 2. The dialog

- The tabs are **A stretch**, **Copy this style**, **The whole song**. `shownTab` is `song` while nothing is selected; both
  tabs of a selection are off then. On a version of My library there is no selection for the AI (`stretchOfSelection`
  answers `null`), so the tab is off there too.
- The list is asked for when the tab opens and when the hand changes, and again when the model changes (the costs
  follow the model). `found.key` is `hand:try`: `undefined` while no answer of this hand is there, `null` when it could
  not be read (**Try again** adds one to the try).
- **Ticks belong to a hand** (`unticked`, a record by hand). Each hand finds its own passages, and comes back as the user
  left it. First written as "the last hand only": going back to Both kept an untick or not, depending on whether a tick
  changed on the other hand. `check:copy-style` found it.
- **The cost follows the ticks with no request**: the `GET` answers `costs`, the estimate for each number of passages
  ticked, none first. So the page holds no price and no formula.
- The words of the list: `VERY_SIMILAR` 0.8 (the study: 0.84 and more for repeats, 0.6 to 0.8 for variants). "Very
  similar" or "Similar", then the key: "a semitone", "a tone", "N semitones", "higher" or "lower".
- The status line says every state: "Looking for similar passages.", "The passages could not be read.", "Select a shorter
  stretch.", "Select a longer stretch." (a reference with too few columns, Phase 1), "No passage of the song is like this
  one.", "Tick a passage first.", else the plan's line. With one hand it starts "The reference and the left hand stay as
  they are." The line has `role="status"`. The button is off unless a passage is ticked.
- `runControls` keeps the Model and hides **Batches** on this tab. The words are the same state as A stretch.

# 3. On the sheet

The reference is drawn in `REFERENCE_COLOUR` (`data-batch-reference`), with the words "The reference" on its **widest**
box: the first box may hold a column or two at the end of a line, and the name ran out of it. The passages keep the
number and the colour of their row (`places`): a passage not ticked leaves a gap in the numbers, not a new order. With
one hand everything is drawn over that staff.

# 4. The run, the panel, the history

- The event `style` now says `checking` (`true` only when the run asks the check; Go on and Write this batch again do
  not). `useFramesSheet` reads it, the event `check` ends it. The panel says "The AI is checking the passages" and no row
  says "Being written" meanwhile. A stream opened late receives the messages again, so a reload shows the same.
- The panel's count: after the end of a Copy this style run it comes from the summary (`total`, `batches`), not from the
  rows last seen, which may still hold a passage the check dropped. First it showed "0 of 3 batches" for 1 of 2.
- **Revert** is not offered when the run wrote nothing (`summary.batches === 0`). This also holds for a level run that
  wrote nothing, where the button did nothing useful.
- `AiRunDetail`: `StyleCheck` shows the reference and each passage with Kept or Dropped and why; in the panel (`compact`)
  only "Passages the AI dropped", with the reason. A check refused shows its refusals. A passage's `copiedText` is one line
  ("3 spellings and 2 fingers copied from the reference.").
- "Go on with the other batch" when one is left (it said "the other 1 batches", for level runs too).
- `endNotice`: `dropped` ("The AI kept no passage. The sheet stays as it was."), `failed` (three cases: a passage written
  again, some passages written, none), `stale`, part of the passages written, and `credits` with `style`.
- The words stay the level run's: "Check batch 1", "N of M batches", **Go on with the other batches**, **Write this batch
  again** (plan section 1: a batch is one passage written again).

# 5. `npm run check:copy-style`

On a temporary copy of 7 Years, deleted at the end. The list comes from the real `GET` (free), on a stretch the script
finds with three passages or more; the states the song does not have come from a stand-in. It walks: the tab off with
nothing selected; one note picked (its hand, "Select a longer stretch."); the controls; the rows; the drawing; a tick,
Deselect all, Select all, the keyboard (Space, Tab to the button); another hand and back; no passage, too long, too short,
the error and Try again; another key; twelve passages; a narrow and a wide window; the request sent; the check, the
wait, the dropped passage, the marks copied, an answer, Go on; the history; a check that drops every passage.

**A timeout that was not a bug.** The second stretch of the check timed out in 2 of 3 runs ("waiting for element to be
stable"), with a low load. Measured over 4 runs after a panel closes: one request at width 148, the sheet settles, no loop,
animation frames at 62 a second. The drag came during that one layout, so the check now waits for it; 3 runs of 3 passed
after that.

# 6. The pass of 13 checks of the minimal UI

The plan's "13 checks" is section 13 of the guidelines, which lists 12 points.

| Check | Result |
|---|---|
| 1 What the tab is for | Choose the passages to write the way the reference is written |
| 2 Every sentence | Labels, controls and facts only; no explanation of how the matcher works |
| 3 Words above the content | The dialog's title and the tabs only |
| 4 Very wide (2200) | The dialog keeps its width beside the sheet; nothing drifts |
| 5 Narrow (480) | No overlap, no scroll sideways; a long "how similar" is cut, in full on hover (`title`) |
| 6 Longest, shortest, none | 12 rows, "Very similar, 6 semitones higher"; "Similar"; no passage. Eight rows and a half show, so the cut row says the list goes on |
| 7 Buttons | **Copy this style**, **Select all**, **Deselect all**, **Try again** |
| 8 Helper lines | None |
| 9 Loading, empty, partial, error | All in the status line; the error offers Try again |
| 10 Keyboard | Space ticks, Tab reaches the button |
| 11 Internal names | None in the tab. The check's refusals in the run's detail show the check's own words ("P1"), as a level run's do |
| 12 A first-time user | "The reference" is named in the list and on the sheet, with its colour |

# 7. Needed later

- Phase 4: the panel and the history with a real run (this phase used a stand-in for the run; the list is real). The
  sheet is laid out twice when a run starts (the dialog closes, then the panel opens): the same for every run, not
  changed here.
- Phase 7: the docs of plan section 4.9 name `StylePassageList`, `BatchNumber`, the tab, `costs` and `checking`.
