# 06 — Phase 1: undo and redo on the sheet

Technical report. The plan is [`06-plan.md`](06-plan.md), the status lookup is
[`06-checklist.md`](06-checklist.md).

## What shipped

| File | Change |
|---|---|
| `aitu-frontend/src/hooks/useEditHistory.ts` | **New.** The history: a pure reducer plus a thin React wrapper |
| `aitu-frontend/src/scripts/check-history.ts` | **New.** 20 assertions over the reducer, wired as `npm run check:history` |
| `aitu-frontend/src/pages/playground/RhythmPage.tsx` | Sixteen `useState` values gathered into one `SheetEdits`; the keyboard; the two buttons; the hand swap staged with its backend calls; the three resets |

## 1. The architecture, and the one thing that forced it

The obvious first design held `present` in a ref so that several setters in one run could each see
what the previous one wrote, and read `past`/`future` from refs during render for `canUndo`. **The
React Compiler rejected it**: this app lints with `react-hooks` + the compiler's own rules, and
`Cannot access refs during render` fired eleven times, plus four
`Compilation Skipped: Existing memoization could not be preserved` where `field()` built setters
lazily into a `Map` ref.

The rule is right. A value read during render that React did not see change is a page that draws
something other than what it holds. The rewrite is a `useReducer` over plain values:

```
HistoryState<T> = { present: T; past: HistoryStep<T>[]; future: HistoryStep<T>[] }
HistoryAction<T> = edit | stage | walk | reset
```

`dispatch` is stable, so the per-field setters are built once in a `useMemo` keyed on the labels
object and are the same function on every render — which is load-bearing, because
`TimeScoreView`'s build effect would tear down and rebuild every note otherwise.

## 2. One press is one step, without a transaction API

The grouping problem: `hideSelected` writes two fields, `moveSelected` three, and a reader pressing
undo means the press, not a third of it. Rather than making every multi-field call site declare a
transaction, each write carries a **gesture number**:

```ts
let gestureNow = 0, gestureEnding = false;
function gesture(): number {
  if (!gestureEnding) {
    gestureEnding = true;
    queueMicrotask(() => { gestureNow += 1; gestureEnding = false; });
  }
  return gestureNow;
}
```

Module level rather than a ref, deliberately: it is a fact about the browser's event loop, not about
a component, and a ref could not be read where it is needed without reading it during render. The
reducer merges a write into the top of `past` when the gesture numbers match, and pushes otherwise.

**No call site on the page says anything about grouping.** Verified in `check-history.ts`: two
fields in one gesture → one step; three gestures → three steps.

Checked against the async case by hand: in `moveSelected` every write happens in one synchronous
stretch after `await setHands(...)`, and the microtask that ends the gesture only runs once that
stretch yields at `await apply()`. One step.

## 3. `stage`, and why the label needs to win

An ordinary step is named by the first field written. That is right everywhere except a hand swap,
which moves fingerings first and would come out called "Fingering". `stage(label, effects)` is
called *before* the setters and carries `rename: true` through `record`, so it overrides the label
even when joining a step that a field already opened. `check-history.ts` pins it.

`stage` also pushes a step when **nothing on the page changed** — a hand swap where no fingering,
figure or beam break moved. The state part is empty; the step exists because the recording changed
and the `effects` are the way back.

## 4. The hand swap through the backend

`PUT /time/{uuid}/hands` takes a hand per note, so it is exactly symmetrical. `moveSelected` reads
each note's current hand out of its own key (`handOf(noteKey)`) **before** anything moves, and hands
the two lists to `stage`:

```ts
stageEdit("Hand", {
  undo: async () => { await setHands({ notes: wasPlayedBy }); await applyRef.current(); },
  redo: async () => { await setHands({ notes: nowPlayedBy }); await applyRef.current(); },
});
```

`applyRef` is new and necessary: the closure is made at the moment of the edit, and the `apply` it
would otherwise capture still holds that moment's ladder, speed changes and page edits. Redrawing
through it would draw the piece as it was rather than as it is.

`walk` runs the call **first** and only dispatches on success, so a failed undo leaves the page
saying exactly what it said before — which is the truth, because nothing changed anywhere. The
failure is surfaced raw and worded by the page through its existing `readable()`.

**Proven end to end against the running backend** on `classical-mix`: moving one right-hand note at
column 6 renamed **2 neighbouring notes** (the D-14 effect), and the undo restored the score
identically — every note's hand, column, row and figure.

## 5. What resets the baseline instead of adding a step

Six places, all calling `edits.reset`:

| Where | Why |
|---|---|
| `GET /time/{uuid}/rhythm` resolving | The reading is where the reader left off, not something they just did |
| The first octave-bracket proposal | The page did it to itself before anyone arrived |
| `audioUuid` or `composed` changing | A different piece, or an insertion that moved every mark after it |
| `wipe` (**Remove all**) | It deletes the file and puts notes back on the recording |
| The re-record `onAccepted` | It wrote over a window of the recording |

The piece change is compared during render against a `useState`, mirroring the existing
`if (view.key !== key) setView(...)` line rather than a ref. It also fixes a pre-existing leak: the
edits used to survive a change of piece when the new piece had no saved reading, because the load
effect returns early on `null`.

`ottavasDecided` is now reset at the top of the rhythm effect, for the same pre-existing reason.

## 6. The three that Command-Z does not reach

Each says so on the page, in one line, before the button that does it: a warning `Alert` above
`RangeRerecordPanel`, one above `ComposePassagePanel`, and a `Tooltip` on **Remove all**.

**Remove all** also now clears `spacings`, `dropDecorative` and `lineSpacing`, which it did not
before — it went field by field and those three were added after it was written. `NO_EDITS` makes
that class of omission impossible.

## 7. Scope notes

Three edits beyond the prompt's list are in the history, because they are the same kind of thing and
a Command-Z that skipped them could not be trusted: **mark size**, **speed changes** and the new
**space between lines**.

**Speed changes do not redraw on undo**, deliberately: adding one does not redraw either, and the
page has always asked for **Write the sheet**. Hidden notes, trills and the decorative switch *do*
redraw on undo with no new code, through the `editSignature` effect the page already had.

## 8. Checks

- `npm run check:history` — 20 assertions, **proven to fail** by removing the `Object.is` guard
  (2 checks went red, restored).
- `npx tsc -b` clean, `npm run lint` clean (zero errors, zero warnings), `npm run build` clean.
