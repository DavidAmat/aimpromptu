# 06 — Undo and redo on the sheet, and the space between lines: checklist

The status lookup for this implementation. The plan is [`06-plan.md`](06-plan.md); the frozen
decisions are the D numbers of
[`../03-time-based-concept/decisions.md`](../03-time-based-concept/decisions.md), and this plan adds
none and contradicts none.

One phase is one epic. A story is ticked only when every task under it is done.

Status letters: `[x]` complete, `[p]` in progress, `[b]` blocked, `[c]` cancelled, `[ ]` not started.

# [x] Phase 1 — Undo and redo on the sheet
Every edit that lives in the page's own state taken back in one step, by Command-Z and by two
buttons beside **Write the sheet**; the hand swap taken back through the backend; the three edits
Command-Z does not reach saying so.

Done 2026-09-16. The report is [`06-phase-1-implementation.md`](06-phase-1-implementation.md).
Sixteen edits, one history, **20 checks** in `npm run check:history` — proven to fail by breaking
the reducer. The first design held the history in refs and the React Compiler refused it with
eleven `Cannot access refs during render`; it is a pure reducer now. The hand swap's undo was driven
against the running backend: moving one note renamed 2 neighbours and the undo restored the score
note for note.

## [x] Story 1.1 — The history
- [x] Task 1.1.1 **The hook**: `useEditHistory.ts` — `past`, `present`, `future`, capped at 100 steps, a step carrying its label and optionally a backend undo and redo.
- [x] Task 1.1.2 **A setter per field**: the same signature a `useState` setter has and a stable identity across renders, so no call site on the page changes and the sheet is not rebuilt.
- [x] Task 1.1.3 **One press is one step**: every set made in one synchronous run committed as one step, so a deletion that also clears a fingering is one undo.
- [x] Task 1.1.4 **What resets it**: the saved reading read back, the first octave-bracket proposal, a different piece, a placed passage, Remove all, an accepted re-record.

## [x] Story 1.2 — The sixteen edits
- [x] Task 1.2.1 **The state gathered**: the sixteen values of section 5.1 into one `SheetEdits` object, with `save()`, `wipe()`, `live` and `pageEdits` reading it unchanged.
- [x] Task 1.2.2 **The redraw**: undo of hidden notes, trills or the decorative-notes switch draws the sheet again through the signature the page already watches.

## [x] Story 1.3 — The controls
- [x] Task 1.3.1 **The keyboard**: Command-Z and Shift-Command-Z, Control-Z, Control-Shift-Z and Control-Y, standing down while the focus is in a text field.
- [x] Task 1.3.2 **The two buttons**: beside **Write the sheet**, disabled when there is nothing to take back, each saying what step it is about.

## [x] Story 1.4 — The edits that write to the recording
- [x] Task 1.4.1 **The hand swap**: the hand each note had before, written back through `PUT /time/{uuid}/hands`, the sheet asked for again, and the pointer held where it is if the call fails.
- [x] Task 1.4.2 **The three that cannot be taken back**: a re-record, a placed passage and Remove all each say so in one line on the page, and each empties the history.

# [x] Phase 2 — The space between lines
A slider beside the Key signature that sets the white space between one set of pentagrams and the
next, undoable and saved with the piece.

Done 2026-09-16, then **reopened the same day** and finished. The report is
[`06-phase-2-implementation.md`](06-phase-2-implementation.md), whose section 6 supersedes the
numbers above it.

The first cut exposed the package's `systemGap`, which turned out not to be the number a reader
wants: a system is not its staves, and at a gap of nought two lines were still **162 px** apart —
more white than the staves are tall. The slider moved 28 px of a 190 px gap and looked broken. Two
fixes: the corner marks were being drawn **78 px** clear of the staff, outside the band reserved for
them, so the room was paid for twice; and the slider now carries the **white space itself**, 0
meaning the staves touch, default **72 px**. `resolveSystemGap` floors it per render so a printed
page, which has less room, cannot be pushed through itself. **0.34.0**, `dist/` rebuilt, 408 package
tests, eight of them new and all eight proven to fail against the pre-change source.

## [x] Story 2.1 — The drawing package
- [x] Task 2.1.1 **The option**: `systemGap` on the renderer options and on its state, with `MIN_SYSTEM_GAP` and `MAX_SYSTEM_GAP` exported beside the `SYSTEM_GAP` that was already there and is the default.
- [x] Task 2.1.2 **The setter**: `setSystemGap`, validated and re-rendering, the twin of `setStaffGap`; `render()` and `renderPages` both passing the state's gap.
- [x] Task 2.1.3 **The test and the build**: a test that the drawn height grows with the gap and that a gap outside the range is refused; version 0.34.0; `npm run build`.

## [x] Story 2.4 — The follow-up: the slider did almost nothing
- [x] Task 2.4.1 **The corner marks tied to the staves**: measured from `trebleTopY` and the bass staff's bottom instead of from the edge of the system box, the lanes tightened, and `rangeMarkerPadding()` made exactly what the furthest corner reaches.
- [x] Task 2.4.2 **The slider means the white space**: `SYSTEM_ROOM` named and exported, taken off in `TimeScoreView`, so 0 puts one pair of staves directly under the pair above and the default is 72 px.
- [x] Task 2.4.3 **A floor per render**: `resolveSystemGap` used by the drawing and by the paginator, so a printed page keeps its own tighter floor and a lyric's room is never given back.

## [x] Story 2.5 — The octave bracket says what it covers
- [x] Task 2.5.1 **Measured from the notes**: the span runs from just before the first notehead it covers to just after the last, instead of from `xForFrame(fromColumn)` to `xForFrame(toColumn)` — the latter being the column of the first note the bracket does *not* cover, and a notehead being centred on its column, so the hook landed on it.
- [x] Task 2.5.2 **Capped against the neighbour**: the overhang is cut to a fraction of the way to the next note, so both ends fall in a gap and nearer the note they cover. Version 0.35.0, `dist/` rebuilt.
- [x] Task 2.5.3 **The test**: `ottava-span.test.ts`, four assertions, three of them proven to fail against the pre-change source.

## [x] Story 2.6 — One line spread on its own
- [x] Task 2.6.1 **Per line, keyed by a column**: `StaffGapOverride` and `resolveStaffGap`, so the room stays with the music through a re-wrap and the widest answer wins where two meet.
- [x] Task 2.6.2 **Lines of different heights**: the tops accumulated in `drawGrandStaff`, and `planPages` given a `systemHeights` list so a printed page is never handed more lines than fit.
- [x] Task 2.6.3 **The page holds the answer**: reported up through `onStaffGapsChange`, kept in `SheetEdits` so it is undoable, and saved as `staffGaps`. Version 0.36.0, `dist/` rebuilt.

## [x] Story 2.7 — A bracket already open beats a proposed one
- [x] Task 2.7.1 **Measured under the open bracket**: how far out a chord is is counted against the transposition the reader is holding, not against the bare staff, so a note that asks for `15ma` on its own account is often an ordinary high note inside the open `8va`.
- [x] Task 2.7.2 **A set of notes, not one**: a different bracket needs a run of onsets wanting it, or one chord left hopeless even under the open one. Version 0.37.0, `dist/` rebuilt.
- [x] Task 2.7.3 **The test**: `ottava-suggestion-keeps-the-open-one.test.ts`, three assertions, proven to fail against the pre-change source.

## [x] Story 2.2 — The app
- [x] Task 2.2.1 **The prop**: `lineSpacing` on `TimeScoreView`, in the constructor for the first build and through `setSystemGap` after that, never in the build effect's dependency list.
- [x] Task 2.2.2 **The chrome placed again**: the playhead and the two range handles put back where they belong after the gap changes.
- [x] Task 2.2.3 **The slider**: beside the Key signature field, one of the undoable edits.

## [x] Story 2.3 — Saved with the piece
- [x] Task 2.3.1 **The field**: `lineSpacing` on `SavedRhythm`, backend and frontend, `null` meaning nobody has chosen.
- [x] Task 2.3.2 **The round trip**: saved, read back on reload, and pinned by a backend test.

# [x] Phase 3 — The documentation and the checks
Done 2026-09-16. The report is [`06-phase-3-implementation.md`](06-phase-3-implementation.md). Four
pages updated and two pre-existing inaccuracies corrected. Everything passes except two failures
confirmed as pre-existing rather than assumed. No browser driver on this machine, so the
click-through is the one human step left.
- [x] Task 3.1 **The context pages**: `frontend/annotations.md` gains undo and redo and what they do not reach; `frontend/rendering.md` gains the space between lines.
- [x] Task 3.2 **The service pages**: `frontend/grid-notation.md` gains the new option; `backend/rhythm-and-annotations.md` gains the new field.
- [x] Task 3.3 **The checks**: `npm run lint`, `npm run build` and `npm run check:render` in the app, `npm test` in the package, `make test` in the backend.
- [x] Task 3.4 **The report**: `06-phase-1-implementation.md`, `06-phase-2-implementation.md` and `06-phase-3-implementation.md` in this folder.
