# 06 — Undo and redo on the sheet, and the space between lines: implementation plan

Read the prompt this plan answers first: [`06-prompt.md`](06-prompt.md). The status lookup is
[`06-checklist.md`](06-checklist.md). The frozen decisions are the D numbers of
[`../03-time-based-concept/decisions.md`](../03-time-based-concept/decisions.md) and the contract is
[`../03-time-based-concept/contract.md`](../03-time-based-concept/contract.md). **This plan adds no
decision and contradicts none.** Section 4 says why, one by one.

Two pieces of work, asked for together and kept apart here because they touch different things:

1. **Undo and redo** for every edit a reader makes on the sheet of the Playground's Rhythm page.
2. **The space between lines** — a slider beside the Key signature that sets how much white space
   there is between one set of pentagrams and the next.

---

## 1. What we are building and why

### 1.1 Undo and redo

The Rhythm page lets a reader make about sixteen different kinds of edit, and **not one of them can
be taken back in one step today**. Some have their own private way out — a figure override has an
Undo button in the note toolbox, an octave bracket is cleared by pressing the chip that set it, a
lyric has "Take it off", notes taken off the page have "Bring them all back" — and each of those is
a different control in a different place. Several have no way out at all: there is no way to take
back one fingering, and the only way to undo **Remove all changes** on the speed changes is to add
every one of them again.

So the page already asks a reader to be careful in a way that a drawing program does not. Command-Z
is the one gesture everybody already knows, and the page has the right shape for it: nearly every
edit is a small value held in the page's own state, and the whole set of them is what gets written
to `rhythm.json`. Taking one back is going back to the previous set.

The one exception is the small group of edits that write to the **recording** rather than to the
page — a hand swap, a re-record, placing a passage. The prompt is explicit: each must either be
undoable through the backend or say plainly that it is not. Section 5.6 answers that for each of
the three.

### 1.2 The space between lines

The sheet draws a **system**: a right-hand pentagram and a left-hand pentagram joined by a `{`
curly bracket. A long piece wraps onto many of them down the page. The white space between one
system and the next is a fixed 28 pixels inside the drawing package, and nothing in the app can
change it.

That one number is wrong in both directions at once:

- On most pieces it is **too much**. The page is mostly white space, and a reader scrolls further
  than the music needs.
- On a piece with high notes it is **too little**. A low note of the left hand of one system is
  drawn below its staff on ledger lines, a high note of the right hand of the next system is drawn
  above its staff on ledger lines, and the two run into each other.

There is no number that is right for every piece, which is exactly the shape of a control the
reader should hold. The page already holds two of the same kind — **Mark size** for how big the
marks over and under the staff are drawn, and the **Spacing** pill for how wide a stretch of
columns is set — and the drawing package already lets the gap **inside** one system be dragged.
This is the missing third.

---

## 2. Terminology

The words of the prompt, used with one meaning each and no synonyms.

- **the sheet** — the drawn score on the Playground's Rhythm page.
- **an edit** — one thing a reader decides about the sheet. The full list is in section 5.1.
- **undo** — take the last edit back. **redo** — put it back again.
- **a step** — what one undo takes back. One press of one control is one step, however many pieces
  of page state it changed.
- **the page's own state** — the values `RhythmPage.tsx` holds and writes to `rhythm.json`. Nothing
  in the recording.
- **the recording** — what the transcription recorded, the thing `events.json` holds. Three edits
  write to it: a hand swap, a re-record, placing a passage.
- **a system** — one pair of pentagrams joined by the `{` curly bracket. The user's "line" and
  "set of lines".
- **the space between lines** — the white space between the bottom of one system and the top of the
  next. `systemGap` in the drawing package.
- **the space inside a system** — the white space between the two pentagrams of one system.
  `staffGap` in the drawing package. **It is not what this work changes**, and the two are kept
  apart on purpose: they are already two separate numbers in the package and a reader wanting more
  room between lines does not want the two hands pulled apart.

---

## 3. What already exists and is reused

| Thing | Where | What it gives |
|---|---|---|
| The page and every edit on it | `aitu-frontend/src/pages/playground/RhythmPage.tsx` | Sixteen `useState` values that are exactly the set undo has to hold |
| The one seam to the renderer | `aitu-frontend/src/components/time/TimeScoreView.tsx` | Where a new drawing option goes in |
| `staffGap`, and its drag handle | `vexflow-v2/src/renderer/grid-notation-renderer.ts` | The **model to copy**: an option, a piece of state, a `setStaffGap` that re-renders, and validation against a min and a max |
| `systemGap` | `vexflow-v2/src/renderer/draw-grand-staff.ts` | The gap already exists in the drawing and in the paginator. It is simply not reachable from the browser renderer |
| The printed panel's own line-gap slider | `aitu-frontend/src/components/time/ScorePdfDialog.tsx` | Precedent for the control and for the words: "Extra space between lines" |
| `PUT /time/{uuid}/hands` | `aitu-backend/src/aitu_backend/api/time_score.py` | Symmetric: it takes a hand per note, so writing the old hand back undoes it |
| `SavedRhythm` | `aitu-backend/src/aitu_backend/schemas/rhythm.py` | Where `annotationScale` lives, and so where the new line spacing goes |
| The debounced redraw | `RhythmPage.tsx`, the effect on `editSignature` | Already asks for the sheet again whenever the edits that travel with the request move. Undo gets its redraw free |

---

## 4. The frozen decisions, checked one by one

**Nothing here contradicts a frozen decision, and nothing here needs a new one.** The checks worth
writing down, because they are the ones a reader of this plan would ask about:

| Decision | Why this work does not touch it |
|---|---|
| **D-17** per-note figure override is local | Undo restores a previous set of overrides. It still changes one glyph per chord and nothing else |
| **D-21** a ladder change moves nothing outside its passage | Undo of a speed change restores the previous boundaries. Locality is the backend's and is untouched |
| **D-22 / D-23 / D-25 / D-26 / D-33** the `time → x` map | The space between lines is **vertical**. It is not in the map, it is not in the contract, and no column changes width because of it |
| **D-28** no bars, no metre | Nothing here draws or implies either |
| **D-29** every player plays the recorded times | Undo never touches playback |
| **D-34** the reader's beam break beats every rule | Undo restores a previous set of breaks. The rule that the reader's answer is applied last is the package's and is untouched |
| **Contract §6** who owns what | The space between lines is a renderer concern, like `staffGap`, which the renderer already owns and already lets the reader drag |

One thing to **raise rather than decide silently**, and it is a naming point rather than a
contradiction: `context/frontend/annotations.md` says "None of it changes the recording except where
this page says so", and the page then says so for a hand swap and for hidden notes. This work adds
a sentence to the same page for each of the three edits that write to the recording, saying whether
Command-Z reaches it. That is new prose in an existing file, not a new rule.

---

## 5. The design — undo and redo

### 5.1 What is one edit

Sixteen values, all of them already in `RhythmPage`'s state and all of them already written to
`rhythm.json` (or, for the new one, about to be):

| The edit | The state | Where the control is |
|---|---|---|
| Key signature | `keySignature` | Beside the sheet |
| Key of a stretch | `keyChanges` | Frames toolbox → **Key** |
| Octave brackets | `ottavas` | Frames toolbox → **Octave**, and the `8va` chip |
| Trills | `trills` | Frames toolbox → **Trill**, and the **Find trills** chips |
| Words | `lyrics` | Frames toolbox → **Words** |
| Small stretches | `cueRanges` | Frames toolbox → **Small** |
| Spacing | `spacings` | Frames toolbox → **Spacing** |
| Fingers | `fingers` | Note toolbox → **Fingering** |
| Figure overrides | `overrides` | Note toolbox → **Figure** |
| Beam breaks | `beamBreaks` | Note toolbox → **Beam** |
| Notes taken off | `hiddenNotes` | Note toolbox, and **Bring them all back** |
| Grace notes | `graceNotes` | Note toolbox → **Grace note** |
| The decorative-notes switch | `dropDecorative` | Beside the sheet |
| Mark size | `annotationScale` | Under the sheet |
| Speed changes | `stretches` | **Does the piece change speed?** |
| The space between lines | `lineSpacing` | Beside the sheet — **new, section 6** |

The last three are not in the prompt's list. They are here because they are the same kind of thing
— a value in the page's own state, written to `rhythm.json`, changed by a control on this screen —
and a Command-Z that skipped them would be a Command-Z a reader could not trust.

**Not an edit, and so not in the history:** which notes are picked, which stretch is marked, where a
toolbox sits, what is typed in a field before it is applied, the trill suggestions the backend
found, which pile of gaps is named and what it is called. Those last two are not a reading of the
sheet, they are the question the sheet is drawn from, and they already have their own visible
controls.

### 5.2 The shape: one object, one history

Today those sixteen values are sixteen `useState` calls. They become **one object**, `SheetEdits`,
held by a new hook.

```
aitu-frontend/src/hooks/useEditHistory.ts
```

```ts
interface HistoryStep<T> {
  label: string;      // "Octave bracket" — what the tooltip says will be taken back
  before: T;
  after: T;
  undo?: () => Promise<void>;   // only for a step that also wrote to the recording
  redo?: () => Promise<void>;
}
```

The hook holds `past: HistoryStep[]`, `present: T` and `future: HistoryStep[]`, capped at 100
steps. A snapshot is a shallow copy of an object of sixteen fields, so it shares everything the step
did not touch and costs almost nothing.

**Every call site in `RhythmPage` stays exactly as it is written today.** The hook hands back a
setter per field with the same signature a `useState` setter has, and with a stable identity across
renders, which the page depends on in several `useCallback` dependency lists and in
`TimeScoreView`'s build effect:

```ts
const setOttavas = edits.field("ottavas", "Octave bracket");
// and then, unchanged, anywhere on the page:
setOttavas((current) => clearOttavaRange(current, side, range));
```

### 5.3 One press is one step, even when it sets four things

`hideSelected` sets `hiddenNotes` and clears `fingers`. `moveSelected` sets three. `wipe` sets
fifteen. Each of those is **one** thing the reader did and must be **one** undo.

The hook groups by tick: the first `set` of a synchronous run records `before` and schedules a
microtask; every later `set` in the same run only moves `after`; the microtask commits one step. No
call site says anything about grouping, and no user gesture can produce two unrelated edits in one
tick.

The label of the step is the label of the first field set in that run, unless a call site names one
explicitly.

### 5.4 What resets the history instead of adding to it

Going back past these would restore marks over notes that are not there any more, which is worse
than not going back at all. Each of them **replaces the baseline and empties both stacks**:

- reading the saved reading back from `GET /time/{uuid}/rhythm` on arrival;
- the first sheet of a piece nobody has decided octave brackets on taking the page's own proposal —
  the reader did not do that, so Command-Z must not point at it;
- loading a different piece (`audioUuid` changes);
- placing a passage, which changes how long the piece is and moves every mark after the insertion;
- **Remove all** — section 5.6;
- accepting a **re-record** — section 5.6.

### 5.5 Getting the sheet drawn again after an undo

Three of the sixteen values travel with the sheet request rather than being drawn here — hidden
notes, trills and the decorative-notes switch — because the printed length of a note is the gap to
the next onset in the same hand and only the backend measures that. The page already watches a
signature of exactly those three and asks for the sheet again 400 ms after it moves. **Undo of any
of the three therefore redraws with no new code.**

Speed changes are the one value that does not redraw by itself, today or after this work: adding
one and pressing **Write the sheet** is how the page already works, so undoing one and pressing
**Write the sheet** is the same gesture. This is deliberate consistency, and it is written into the
report rather than being quietly different.

### 5.6 The three edits that write to the recording

| Edit | Answer | How |
|---|---|---|
| **A hand swap** | **Undoable, through the backend** | `PUT /time/{uuid}/hands` takes a hand per note, so the step carries the hand each note had before it and undo writes those back, then asks for the sheet again. Redo writes the new hands back the same way |
| **A re-record** | **Not undoable, and the page says so** | Accepting replaces a window of the recording and can splice the audio. Nothing brings it back. The panel says it in one line before Accept, and accepting empties the history |
| **Placing a passage** | **Not undoable, and the page says so** | The same: it writes notes into the recording and moves every mark after the insertion point. The panel says it, and placing one empties the history |
| **Remove all** | **Not undoable, and the page says so** | It deletes `rhythm.json` and puts hidden notes back on the recording. Letting Command-Z restore the screen would suggest the file came back too, which it did not. It is already armed behind two presses; the button's tooltip now says Command-Z does not reach it |

A step that carries a backend call is committed **after** the call succeeds. If an undo's call
fails, the pointer does not move and the page says what the backend said — anything else would show
a page that disagrees with the recording.

### 5.7 The two controls

- **Command-Z** undoes, **Shift-Command-Z** redoes. Control-Z and Control-Shift-Z on Windows, and
  Control-Y too, because that is the other redo everybody has. The handler does nothing while the
  focus is in a text field, so typing Command-Z in the **Words** box still undoes the typing.
- **Two buttons beside "Write the sheet"**, in the **Name it** card, disabled when there is nothing
  to take back and carrying what the step was: *Undo: Octave bracket (⌘Z)*.

---

## 6. The design — the space between lines

### 6.1 In the drawing package

`systemGap` is already the number the drawing uses and the paginator budgets with. It is simply not
reachable: `GridNotationRendererOptions` has no field for it and `render()` never passes it, so the
browser always draws with the default 28.

Four small additions to `vexflow-v2`, each mirroring what `staffGap` already does:

1. `MIN_SYSTEM_GAP`, `DEFAULT_SYSTEM_GAP` (= the existing `SYSTEM_GAP`, 28) and `MAX_SYSTEM_GAP`,
   exported.
2. `systemGap?: number` on `GridNotationRendererOptions`, and on `GridRendererState`.
3. `setSystemGap(px)`, validated against the min and the max, re-rendering — the twin of
   `setStaffGap`.
4. `render()` passes the state's gap to `drawGrandStaff`, and `renderPages` passes it as the
   default so **the printed page matches the screen** unless the print panel is told otherwise.

Version 0.33.0, and **`npm run build` in `../vexflow-v2`** — the app runs whatever `dist/` was last
built from and nothing warns when that is stale.

### 6.2 In the app

`TimeScoreView` takes a `lineSpacing` prop. It goes into the constructor for the first build and
then through `setSystemGap` in an effect of its own — **not** into the build effect's dependency
list, which would tear down and rebuild every note on every pixel of the drag. The playhead and the
two range handles are placed imperatively against the last render, so both are placed again after
the gap changes.

`RhythmPage` puts a small slider beside the **Key signature** field, where the prompt asks for it,
labelled with what it does and what it costs. It is one of the sixteen undoable edits, and it is
saved with the piece.

### 6.3 Saved with the piece

A reading that resets on reload is the exact failure octave brackets had for a month. `SavedRhythm`
gets `lineSpacing` beside `annotationScale`, optional, `null` meaning nobody has chosen and the page
draws with its own default. Backend model, frontend type, save, load, and the field documented in
`documentation/services/backend/rhythm-and-annotations.md`.

---

## 7. The phases

### Phase 1 — Undo and redo

The history, the sixteen values, the keyboard, the two buttons, the hand swap through the backend,
and the plain sentence on each of the three that Command-Z does not reach. Frontend only.

### Phase 2 — The space between lines

The package option, the setter, the build, the test; the prop and the imperative re-place in
`TimeScoreView`; the slider on the page; the field in `SavedRhythm` on both sides. The slider joins
the history in the same change, so Phase 1 must land first.

### Phase 3 — The documentation and the checks

`context/frontend/annotations.md`, `context/frontend/rendering.md`,
`documentation/services/frontend/grid-notation.md`,
`documentation/services/backend/rhythm-and-annotations.md`, and the report in this folder. Then
`npm run lint`, `npm run build`, `npm run check:render` in the app, `npm test` in the package and
`make test` in the backend.

---

## 8. What could go wrong, and what is done about it

| Risk | What is done |
|---|---|
| A setter changing identity rebuilds the whole sheet on every render | The hook hands back the same function object per field for the life of the page, and `TimeScoreView`'s build effect is unchanged |
| Two edits in one gesture become two undos | Grouping by tick, so one press is one step whatever it sets |
| Command-Z eats a reader's typing | The handler stands down while the focus is in a field |
| Undo restores a mark over a note that is not there | The six resets of section 5.4, and `live` already drops any mark left naming nothing |
| An undo that calls the backend half-succeeds | The step is committed after the call, the pointer does not move on a failure, and the page says what the backend said |
| The slider rebuilds the sheet on every pixel | The gap is driven through `setSystemGap`, never through the build effect |
| A stale `dist/` means the slider does nothing and nothing warns | `npm run build` in `../vexflow-v2` is a task of Phase 2, and `npm run check:render` is run afterwards |

---

## 9. How it is checked

- `aitu-frontend`: `npm run lint`, `npm run build`, `npm run check:render`.
- `vexflow-v2`: `npm test`, with a new test asserting the drawn height grows with the gap and that
  a gap outside the range is refused.
- `aitu-backend`: `make test`, with the round trip of the new field pinned in
  `tests/test_saved_rhythm.py`.
- By hand, in the browser, on a real piece: every one of the sixteen edits made and taken back, the
  hand swap taken back and put back, the slider dragged to both ends, and a reload showing the
  spacing that was saved.
