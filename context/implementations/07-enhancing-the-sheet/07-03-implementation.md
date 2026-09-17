# 07-03 — Task 6B, Octaves: implementation report

Brief: `07-01-new-enchancements-v1.md`, task **6B** (plus the last line of task 6, the **Save with
the piece** button). Context: `07-00-context.md`.
Predecessors: `07-01-implementation.md` (tasks 1–6), `07-02-implementation.md` (tasks 7–8).

Everything in the brief was delivered, plus two follow-ups asked for after it: a tip dropped on
**another line** takes every frame in between (§3.4), and the note toolbox names the note it is
about (§7).

Package version: `@aimpromptu/grid-notation` **0.39.0 → 0.40.0**, rebuilt.

---

## 1. What the brief asked for, and where each piece landed

| Asked | Where it is |
|---|---|
| A rectangle around the dashed line, with draggable tips left and right | `annotations/draw-ottavas.ts`: `.grid-ottava-band` and two `.grid-ottava-tip` |
| Dropping a tip on another line includes every frame in between | `DrawOttavasOptions.frameAtPoint`, filled in by `draw-grand-staff.ts` |
| Enlarging overwrites whatever octave is to the right of it | `annotations/ottavas.ts: resizeOttava` |
| **Del** hides the `8va` and the dashed line, and does **not** move the notes | `OttavaAnnotation.hidden`, plus the Delete rule in `RhythmPage` |
| An eye icon in the frames dialog that crosses out to mean *hide 8va* | The **Octave** pill, beside the trash |
| The trash is the only way to remove one | Unchanged — `clearOttavaRange`, which was already there |
| Remove **Save with the piece** from the Frames dialog | Gone; the floating bar's **Save** is the only one |

---

## 2. `hidden` is a fourth field on the bracket, not a fourth kind of bracket

`OttavaAnnotation.hidden?: boolean`. Everything else about the span is untouched, and that is the
whole point:

- **`ottavaLookup` ignores it.** A hidden bracket still returns `OTTAVA_STAFF_STEP_OFFSET`, so the
  notes under it are still printed seven (or fourteen) staff steps from where they sound. Un-shifting
  them would be a different edit, and a reader asking for *less* ink would have got a wall of ledger
  lines — the opposite of what they asked for.
- **`drawOttava` returns early.** The group is still opened, with `data-hidden="true"` and the two
  columns, so the bracket is findable in the DOM and in a test; no glyph, no dashed line, no hook and
  no band go inside it.
- **`ottavaBlockHeight` skips it.** Room kept below the staves for a `8vb` that draws nothing is white
  space the reader cannot account for, and taking the room away is most of why they hid it.
- **`collectRangeMarkers` does not skip it.** The corner marks are the only thing left on the page
  saying the bracket is there, so they are the way back to it. Filtering them would have made hiding
  a one-way door.
- **`normalizeOttavas` already carried it** — it spreads the span — so nothing there changed.

Printing inherits all of this: `render-pages.ts` draws through the same `drawOttavas`, so a hidden
bracket is hidden on paper too, and `ottavaBlockHeight` is the same call in both places.

### Storing it

`SavedRhythm.Ottava.hidden: bool = False` (`schemas/rhythm.py`), `hidden?: boolean` on the wire type
in `api/timeScore.ts`, written in `save()` and read back in the `rhythm()` effect as
`span.hidden ?? false`. Absent on a reading saved before today, which reads as drawn — the answer
that reading was saved with.

`test_octave_brackets_survive_a_round_trip` **had to change**: it asserted `read["ottavas"] ==
body["ottavas"]` and the read now carries `hidden`. The two new tests are the round trip of a hidden
bracket and the old-reading-reads-as-drawn case.

---

## 3. The band, and the drag

### 3.1 It is drawn in the package, not overlaid by the app

The two range handles and the playhead are `div`s the app places against the last render. The
bracket is not: its `y` is `bracketY`, which clears the **highest note in the span**, so an overlay
would have had to read the geometry back out of the SVG after every render — including the ones the
app never asks for, because the renderer has its own `ResizeObserver`. The lyric block is the
precedent for the other way, and it is a much bigger interactive thing: drawn inside the package,
dragged inside the package, reported once on pointer-up. That is what this follows.

### 3.2 Invisible until the pointer is on it

`fill: transparent`, lit by `pointerenter` and dark again on `pointerleave`. A permanent box around
every bracket is the page talking about itself — the same mistake the corner marks' hover outline
was, which was reported twice before it was deleted in 07-01. The difference from that one is that
this lights up *the thing directly under the pointer*, never some unrelated stretch across the page.

### 3.3 The drag is measured in columns, not in absolute position

This is the part that would have been a silent bug. `bracketSpan` measures the bracket **from the
notes it covers**, not from the column boundary: the end tip sits a little past the last covered
notehead, which is usually several columns short of `toColumn`. Reading the frame under the tip and
storing it would therefore have pulled the end back onto the last note *every time a reader touched
a bracket*, including a click that never moved.

So the frame under the tip when the press began is compared with the frame under it now, and the
**difference** is added to the stored column:

```
steps = frameUnder(tip, now) − frameUnder(tip, at the press)
```

`steps = 0` gives no change, exactly. The pointer's offset from the tip is captured at the press and
added back on every move, so what is read is where the **tip** is, not where the pointer is — the
reader grabbed the tip somewhere, and the bracket follows the part they took hold of.

The ends are held one column apart and the far end is held inside `frameCount`. An inverted bracket
would cover nothing everywhere downstream, and a reader could not tell that from the bracket having
been deleted under their hand.

Reported once, on pointer-up, and only if the tip travelled more than `DRAG_SLOP`:

```ts
{ hand, fromColumn, toColumn, edge: 'start' | 'end', nextFromColumn, nextToColumn }
```

### 3.4 A tip dropped on another line takes every frame in between

This was asked for after the first pass, and it is where `frameUnder` earns its name.

A bracket is drawn one fragment per system and each fragment only knows its own line's `FrameGrid`,
so a tip measured against that alone stops at the right margin. The sheet wraps, so the frames a
reader wants next are as often on the line below as further right — which is the whole of the
report.

`DrawOttavasOptions.frameAtPoint(x, y)` answers with the column under a point on the **whole page**:
it is `player/playback-cursor.ts: frameAtPoint`, the same function the two range handles already use
to be draggable down onto another system. It picks the system nearest the `y` and reads the column
inside it. Both ends of the subtraction above go through it, so dropping a tip two lines down simply
makes the two frames far apart and every column between them ends up inside the bracket. It works
upward too: the end tip of a bracket that ends on line 2, dropped in the middle of line 1, gives
those frames back.

**The lookup has to be lazy, and that is the only awkward part.** At the moment a bracket on line 1
is drawn, the systems below it have not been laid out, so there is no page to read. `drawGrandStaff`
therefore passes a function closing over a `laidOut` variable that it fills in with the result it is
about to return. Nothing can call it before then: it is only ever reached from a pointer handler, and
a reader cannot press a tip on a page that has not finished drawing.

While the pointer is down, the band, the dashed line and the hook are clipped to the line the
fragment is on — a bracket now reaching two lines down has no room left on this one, and running to
the margin is the truthful half of that answer. Let go and the rebuild draws the rest.

A pointer position is needed now rather than a delta, so the drag converts client pixels to drawing
units against the SVG's own box (`attribute width ÷ on-screen width`) — the same conversion the lyric
block uses, which is what makes it correct while the sheet is magnified. With no layout to measure —
jsdom — the pointer's own coordinates are taken as drawing units, which is what the page does at its
natural size anyway.

### 3.4.1 Which fragment carries which tip

A bracket across a line break draws a fragment per system. The start tip goes on the fragment that
has the start (`isFirst`), the end tip on the one that has the end (`isLast`); a middle fragment gets
the band and neither tip, because neither end is there to pull.

### 3.5 Enlarging takes over what it reaches

`resizeOttava(ottavas, target, next, frameCount)`: take the target out of the list, put it back with
its new columns, and let `applyOttava` → `normalizeOttavas` do what it already does to a span that
arrives last — drop anything it overlaps **on the same hand**. Enlarging an `8va` across a `15ma`
leaves the `8va` and no trace of the `15ma`, which is what the brief asked for. The other hand is
never touched. A `target` that is not in the list, or a `next` that is inverted, leaves the list
alone rather than quietly deleting a bracket.

### 3.6 Clicking the band selects the stretch

The band without a drag calls `onOttavaSelect`, which `draw-grand-staff.ts` binds to the **same**
`onRangeMarkerSelect` the corner marks use — it looks the bracket's own marker out of the list it has
already collected. So the app needed no new plumbing for it: clicking a bracket is clicking its
corner.

**One existing line had to change for this to be safe.** `grid-notation-renderer.ts` passed
`onRangeMarkerSelect: (marker) => this.options.onRangeMarkerSelect?.(marker)` unconditionally, so
downstream code asking "is anybody listening?" always got yes. The band is drawn on exactly that
question, so a printed page would have grown a row of grab handles. It is now passed only when the
host supplied one, the way every other optional hook in that call already is.

---

## 4. The page

### 4.1 The eye, and the trash beside it

The **Octave** pill's per-hand row is now: four kind chips, an eye, a trash.

- Eye → `setOttavaHidden([side], range.fromColumn, !active.hidden)`, and the icon becomes
  `VisibilityOffIcon` when the bracket is hidden — crossed out, which is what the brief asked for.
- Trash → `clearOttavaRange`, unchanged. Its tooltip now says what removing does that hiding does
  not: *the notes go back to where they sound, in ledger lines if that is where they are.*

`setOttavaHidden` acts on the bracket covering the **first column** of the stretch, which is the one
`ottavaAtFrame(ottavas, side, range.fromColumn)` already picks out for the chips. Every overlapping
bracket would have been more generous and would have made the panel lie: the row says `8va` about one
bracket and the eye beside it would have acted on two.

### 4.2 Delete

The existing handler hid the picked notes and returned early when nothing was picked. Now:

1. Focus in a field → do nothing (unchanged).
2. Notes picked → hide them (unchanged), `preventDefault`.
3. Otherwise, a stretch marked and a **drawn** bracket on any hand in scope → hide those brackets.
4. Otherwise → do nothing, and do **not** `preventDefault`, so pressing Delete at nothing is not
   silently swallowed.

Notes first because that is what the key has always meant here and a note is the smaller, commoner
thing; the bracket second because a marked stretch with nothing picked inside it is a reader pointing
at the stretch itself. Step 3 filters on `span !== undefined && !span.hidden`, not on
`span?.hidden === false` — `hidden` is `undefined` on every bracket nobody has hidden, so the second
form would have made the key do nothing at all.

### 4.3 Clicking a corner, or a band, fills the panel in

`pickMarkedRange` took `{ fromColumn, toColumn }`. It now also takes `kind` and `hand`, sets
`rangeHand` when the marker belongs to a staff, and opens the pill the marker's kind belongs to
(`MARKER_TABS`). A reader who clicks an octave bracket is asking about that bracket, not about the
columns under it, and the eye is then one click away rather than three. `TimeScoreView` passes
`marker.hand` through for it.

### 4.4 The drag reaches the page

`TimeScoreView.onOttavaResize`, held in a **ref** and not listed as a build dependency — the same
treatment `onLyricLayoutChange`, `onStaffGapsChange` and `onRendererChange` already get, for the
reason in §2.4 of the context file. `RhythmPage.stretchOttava` calls `setOttavas` with the functional
form, so it is one step in the history and Command-Z puts the bracket back the length it was.

### 4.5 **Save with the piece** is gone from the Frames dialog

Every panel on this page edits the same one reading, and a Save inside one of them read as saving
that panel's part of it. The floating bar carries the only **Save** there is, beside **Remove all**.
Nothing else was touched: `save()`, `savedNote` and the Save at the foot of the page are unchanged.

---

## 5. Tests

**New: `vexflow-v2/tests/ottava-editing.test.ts`, 20 tests.** Five on hiding (no ink; the group is
still there and says so; the printed staff step is unchanged and exactly seven steps from the
un-bracketed one; no room reserved below; nothing to take hold of), two on the band, seven on the
drag, **two on dropping a tip on another line**, four on `resizeOttava`.

The two cross-line tests were each proven against the wiring rather than against the whole change:
replacing `frameAtPoint` in `draw-grand-staff.ts` with `() => undefined` — the fallback to the
bracket's own line — fails both and leaves the other eighteen passing. The fixture wraps at
`availableWidth: 320` into lines of `0–38` and `38–48`. The first test drops the end tip of a
bracket on line 1 onto line 2 and asserts the bracket now passes `38`; the second drops the end tip
of a bracket that ends on line 2 into the **middle** of line 1 and asserts it comes back well inside
it, which is the half a single-line reading cannot do, because that reading is clamped to the
columns its own line holds.

**Proven against the pre-change source** — the five touched `src/` files were copied aside, the
pre-change copies put back, the file run, and the originals restored (no `git stash`, because the
working tree carries other people's uncommitted work):

| | |
|---|---|
| **15 failed** | everything about hiding, the band, the drag and the resize rule |
| **3 passed** | the controls |

The three controls assert behaviour that deliberately did **not** change: *the notes stay written
where the bracket puts them* (they already did — hiding must not move them, and `hidden` was an
unknown extra field that `normalizeOttavas` carried through harmlessly), *a hidden bracket has
nothing to take hold of* and *the band is drawn only when a host is listening* (there was no band at
all before).

**`check-render.mjs`, seven new checks**, driving the app's own path in jsdom: a bracket is drawn; it
has a band and two tips; pressing the end tip and moving it four columns reports one change with a
longer `nextToColumn` (`0→13` on the fixture); a hidden bracket draws no number, no line and no hook;
the notehead's staff step is unchanged at `−9`; the hidden bracket is still findable; clearing it
puts all 44 noteheads back.

One trap found while writing those: `setAnnotations` **replaces** the envelope rather than merging
into it, so a bare `{ ottavas }` silently dropped the key change two checks above and broke an
unrelated assertion. The check now spreads `renderer.getAnnotations()`.

**Backend, two new tests** in `test_saved_rhythm.py`: a hidden bracket round-trips hidden; a bracket
saved without the field reads as drawn.

### Results

| Check | Result |
|---|---|
| `vexflow-v2` `vitest` | **485 passed** (53 files) |
| `vexflow-v2` `npm run lint` | clean |
| `vexflow-v2` `tsc -b && tsup` | clean, `dist/` rebuilt at 0.40.0 |
| `aitu-frontend` `npx tsc -b` | clean |
| `aitu-frontend` `npm run lint` | clean |
| `aitu-frontend` `npm run build` | clean |
| `aitu-frontend` `npm run check:render` | **51 passed, 0 failed** |
| `aitu-frontend` `npm run check:history` | every check passed |
| `aitu-frontend` `npm run check:note-names` | **15 passed, 0 failed** |
| `aitu-backend` `pytest` | **905 passed, 1 failed** |

The one backend failure is the documented pre-existing one,
`test_time_score_payload.py::test_the_worked_example_at_00_46_prints_three_equal_corcheas`. Both that
test file and `matrix/hands.py` were already modified in the working tree before this task started
(`git status` confirms), so the failure is not from this work. It was 903 passed before; the two new
tests account for the difference.

---

## 6. Files touched

### `../vexflow-v2` (0.40.0)

| File | Why |
|---|---|
| `annotations/ottavas.ts` | `hidden`, `resizeOttava` |
| `annotations/draw-ottavas.ts` | hidden draws nothing; the band, the two tips, the drag, `OttavaResizeChange`, `onOttavaSelect`, `frameCount`, `frameAtPoint`; `ottavaBlockHeight` skips hidden |
| `renderer/draw-grand-staff.ts` | threads `onOttavaResize`, binds `onOttavaSelect` to the marker list, hands the bracket a lazy page-wide `frameAtPoint` |
| `renderer/grid-notation-renderer.ts` | `onOttavaResize`; `onRangeMarkerSelect` passed only when the host supplied one |
| `index.ts` | exports `resizeOttava`, `OttavaResizeChange` |
| `tests/ottava-editing.test.ts` | **new** |
| `documentation/03-rendering.md`, `05-annotations.md` | the DOM, the field, the rule |

### `aitu-frontend`

| File | Why |
|---|---|
| `components/time/TimeScoreView.tsx` | `onOttavaResize` (through a ref), `hand` on the marker payload |
| `pages/playground/RhythmPage.tsx` | `stretchOttava`, `setOttavaHidden`, `MARKER_TABS`, the eye, the Delete rule, `hidden` on save and read-back, **Save with the piece** removed |
| `api/timeScore.ts` | `hidden?: boolean` |
| `scripts/check-render.mjs` | seven checks |

### `aitu-backend`

| File | Why |
|---|---|
| `schemas/rhythm.py` | `Ottava.hidden` |
| `tests/test_saved_rhythm.py` | two new tests, one existing one updated |

### Documentation

`context/frontend/annotations.md` (a new section, *An octave bracket, once it is on the page*),
`documentation/services/frontend/grid-notation.md`,
`documentation/services/backend/rhythm-and-annotations.md`.

---

## 7. The note toolbox says which note it is about

Asked for separately, and unrelated to the brackets except that it is the same panel family.

Picking **one** notehead used to open a panel titled `Note`, which a reader who has just clicked a
notehead already knows. It is now titled in solfege — `Do 4`, `Do-# 3`, `Re-b 5` — with the column
still in the subtitle underneath. Picking several still counts them: a chord is three notes at one
moment, three names in a title is a list rather than an answer, and the keyboard under **Show piano**
is where a chord is read.

### The name is the sheet's, not a second opinion

`spanishNoteName` in `music/noteNames.ts` takes the `letter`, `accidental` and `octave` that
`pitchToStaffPosition` returned and says them in solfege. It does **not** take a row or a MIDI
number, and that is the whole design of it: the same black key sounds the same and is written two
ways, and which one the page prints depends on the signature sounding at that column. A helper that
worked the name out from the pitch on its own would have said `Do-#` under a notehead drawn as
`Re-b`, and a reader would have had no way of telling which of the two the page meant.

So `RhythmPage` spells the picked row through `pitchToStaffPosition` against
`keySignatureAtFrame(frameOf(key), keySignature, keyChanges)` — the same call the **Key** pill
already uses — and hands the result over. Two things deliberately do not enter into it: an octave
bracket, and which staff the note is drawn on. Both move where a note is *printed*, and `letter` and
`octave` are the note as it **sounds**, which is what a player asking "which note is this" wants.

### The format, and the one place it differs from the app's other one

`Do 4`, `Do-# 3`, `Re-b 5` — the accidental joined by a hyphen, the octave after a space, exactly as
asked for. Middle C is `Do 4`, the reckoning `keyPositions`, the roll, the keyboard's octave numbers
and every tooltip already use.

**`keyPositions.es` still reads `Do#-4`**, and I left it alone. It is the label printed *inside* a
key twenty pixels wide on the keyboard drawing, where the tighter form is the reason it exists, and
changing it would move text in the Piano Roll and the video overlay, neither of which was asked
about. Worth knowing that the app now has two Spanish forms for one note: one for a label in a box,
one for a line of a panel.

### Checked

`aitu-frontend/scripts/check-note-names.ts`, run by `npm run check:note-names`, **15 checks, all
passing**. It runs the toolbox's own two steps — spell the row, then name it — over middle C, both
ends of the 88, white keys, and the same black key under `C`, `D`, `Ab`, `Eb`, `Bb` and `B`, which is
the half that matters: row 49 is `Si-b 4` in B flat and `La-# 4` in B. Plus a note under an `8va` and
under a `15mb`, and the same note on either staff, all of which must come out unchanged.

A pure function of what it is handed, like `check-history.ts`, so it needs no browser. Two of my own
expected values were wrong on the first run — row 46 is `Sol`, a white key, not the B flat I wanted
— and the code was right; the rows were corrected, not the assertions about them.

**Files:** `src/music/noteNames.ts` (`spanishNoteName`, `SPANISH_LETTERS`),
`src/pages/playground/RhythmPage.tsx` (`pickedNoteName`, the panel title),
`scripts/check-note-names.ts` (**new**), `package.json` (the script),
`context/frontend/annotations.md`, `context/04-local-development.md`,
`documentation/services/frontend/components.md` and `07-00-context.md` (the check listed beside the
others).

---

## 8. The limit that was here, and is not any more

The first pass of this task shipped with one: a drag reached only as far as the pointer could travel
on the line the tip was drawn on, because the frame was read from that system's own `FrameGrid`.
§3.4 is how it went, and it went the way that had been rejected the first time — resolving the
pointer against every system — once it was clear the lazy `frameAtPoint` closure makes the ordering
problem disappear rather than having to be worked around.

Nothing else about the drag changed. The subtraction, the clamps, the slop and the single report on
pointer-up are all as they were; only what `frameUnder` reads changed, from one line to the page.
