# 07-01 — New enhancements v1: implementation report

Brief: `07-01-new-enchancements-v1.md`. Context: `07-00-context.md`.

Six tasks, all delivered. One part of Task 6 could not be built as written and is explained in §7.

Package version: `@aimpromptu/grid-notation` **0.37.0 → 0.38.0**, rebuilt.

---

## 1. Task 1 — spacings

Three separate problems were in this one task. Each has its own fix.

### 1.1 The beam split with nothing at the seam (`notation/beam-groups.ts`)

`splitAtArpeggioLowPoints` cut a run at any note that was **strictly** lower than both neighbours
and no higher than anything in a three-note window. On the reported page (`images/i1.png`) a level
run of corcheas wandering by one staff step satisfied that at every other note, so the run came out
as several beams with nothing at the seams a reader could see.

New: the dip has to be at least `ARPEGGIO_DIP` (**2** staff steps, a third) below **both**
neighbours. A real arpeggio always returns by a leap, so the case the rule exists for is kept and
the case it should never have caught is dropped.

- `PlanBeamGroupsOptions.arpeggioDip?: number`, default `ARPEGGIO_DIP`, threaded through
  `draw-music.ts` → `draw-grand-staff.ts` → `GridNotationRendererOptions.arpeggioDip`.
- `arpeggioDip: 1` restores the old behaviour exactly. The existing Alberti test
  (`rows = [39, 46, 43, 46, …]`, a fourth of dip) is unaffected.

### 1.2 Room in front of a long note (`notation/spacing.ts`)

Column width is measured from the ink in the column, and a blanca draws no more ink than a corchea —
so a run of corcheas into a blanca put the two noteheads exactly as close together as two corcheas.

New: `measureFrameWidths` records the printed rung of every onset per hand (`FIGURE_RUNG`, the
ladder of halves; dotted figures share their undotted rung, as `SHIFT_LADDER` does on the host
side). For consecutive onsets in one hand where the earlier is a **corchea or shorter**
(`rung <= SHORTEST_LONG_RUNG`) and the later is **two rungs or more** longer, the column *before*
the later onset gets `LONG_NOTE_APPROACH_SPACES × (hops − 1)` extra staff spaces.

Charged at the boundary and per extra rung, never as a width per figure — giving figures widths
would put printing back inside layout and break D-18/D-22. `longNoteApproachSpaces: 0` turns it off.

Placement matters: it is added to `widths` (staff spaces) **before** the silence-group budget, so the
opened column is no longer "empty" and the budget leaves it alone.

### 1.3 A global "Space between notes"

- `measureFrameWidths({ noteSpacingPx })` — added to every column that carries an onset, after the
  pixel conversion and before the per-range `spacings` scale.
- `GridNotationRendererOptions.noteSpacingPx`, `GridRendererState.noteSpacingPx`,
  `setNoteSpacing(px)` (clamped 0–48 by `clampNoteSpacing`; `MAX_NOTE_SPACING` exported).
  It re-measures and re-renders, because it is a horizontal change.
- `TimeScoreView` prop `noteSpacing` (default `DEFAULT_NOTE_SPACING = 0`), read from a ref in the
  build and driven by its own effect — never a build dependency.
- `RhythmPage`: `SheetEdits.noteSpacing`, `EDIT_LABELS.noteSpacing`, a slider beside **Space between
  lines**, saved as `SavedRhythm.noteSpacing`.

**Not a zoom.** Silent columns are untouched, so a held note keeps exactly the width the wall clock
gives it.

---

## 2. Task 2 — changing clef

The renderer already had the whole clef-change machinery (`applyClefRange`, `clearClefRange`,
`clefAtFrame`, `drawClefTransition`, `annotations.clefChanges`, width reservation in
`measureFrameWidths`, beam splitting at `clefChangeFrames`). Nothing in the package needed adding for
the clef itself. What was missing was the hand-scoped selection and the persistence.

- **`FrameRangeSelection.hand?: 'right' | 'left'`** (optional, additive). `drawFrameRuler` takes a
  new `handBands?: StaffBands` and paints the highlight into that hand's band instead of the
  ruler's full band; `draw-grand-staff.ts` computes the two bands from the geometry it has just
  drawn, so a spread line is honoured. The fill carries `data-hand`.
- `RhythmPage`: `rangeHand: "both" | "right" | "left"` state (**not** in `SheetEdits` — it is part
  of the selection, like the columns, so Command-Z must not touch it). It is the first row of the
  frames toolbox and is reset by `closeFrames`.
- New **Clef** pill: treble/bass chips per hand in scope, plus a clear. Asking for the clef the hand
  already reads calls `clearClefRange` rather than storing a transition that changes nothing.
- `SheetEdits.clefChanges` → `TimeScoreView.clefChanges` → `annotations.clefChanges`; stored as
  `SavedRhythm.clefChanges` (`schemas/rhythm.py: ClefChange`).

### Where a click starts a range, and where the panel opens

Two reports about the same gesture.

**The range started before the click.** `drawFrameRuler` selected the whole group the click landed
in, and a group is about a second, so the click ended up near the middle of the result and a reader
aiming at a note had to drag the left handle back to where they had just pointed. Now the cell's
handler reads the pointer's frame and sends `{ fromColumn: frame, toColumn: frame + groupLength }` —
same length, start where they pointed.

The frame comes from `grid.frameAtX(svgX - NOTEHEAD_LEAD, system.startFrame)`, with `svgX` recovered
from the cell's own SVG `x`/`width` against its `getBoundingClientRect`. Not by dividing the cell
evenly: columns are not the same width, so a linear guess is worst exactly where the music is
densest and the reader is being most careful. A `keydown` activation has no pointer and keeps the
group's start. The shift-extend path in `grid-notation-renderer.ts` is untouched and still takes the
min/max with the previous range. `TimeScoreView` clamps `toColumn` to `frameCount`, because the last
group of the piece can now name a column past the end.

**The panel covered the purple.** `besideOnScreen` opens a panel to the right of what it is about,
which is right for noteheads — a note selection is the size it is — and wrong for a stretch, which
starts where the reader clicked and is then dragged *rightwards* by its handle. So the panel was
exactly where the stretch was about to go, and the reader had to drag the panel away to finish the
gesture. `clearOfRange` opens the frames toolbox to the **left** of where the stretch starts, the one
side it does not grow towards, and **below the staves** left-aligned with the start when there is no
room there. The note toolbox keeps `besideOnScreen`.

Two tests in `sheet-spacing-and-beams.test.ts`. jsdom has no layout, so the cell is told its own SVG
attributes as its screen box — one user unit to one pixel, which is what the page does at its
natural size. The pointer test fails against the pre-change source; the keyboard one passes, which
is the control.

### Air around a clef change

Reported: a clef change reads as cluttered, with the chord before it running into the barline.

`measureFrameWidths` reserved the block with
`pixels[frame - 1] = max(pixels[frame - 1], clefTransitionWidth())`. The block is drawn **leftward**
from `frameX`, so it occupies the previous frame's column — and that frame's own notes are drawn from
the same column's left edge rightward. Two different things in one column, so `max` sized the column
for whichever was wider and then drew both inside it: the only clearance between a chord and the
barline was the block's own leading `TRANSITION_PADDING`.

Now a sum: `pixels[frame - 1] = ceilToTenth(pixels[frame - 1] + clefTransitionWidth())`. The previous
frame keeps the room it asked for and the block gets its own beside it.

`TRANSITION_PADDING` in `clef-changes.ts` also went from `0.75` to `1.25` staff spaces. It was copied
from the key-change block and the two are not the same problem: a key change draws both clefs and a
row of naturals, so it reads as a boundary however tightly it is set, while a clef change is one
glyph and set tight it reads as another note of the chord beside it. Because the drawing measures
from `left = frameX - width`, widening the block moves the glyph left and so gives air on **both**
sides — before the barline and after the clef.

**`keyTransitionWidth` is still reserved with a `max` and has the same defect.** Left alone: it was
not what was reported, it shows far less because a key block is almost always the wider of the two,
and changing it moves the layout of every piece that has a key change.

---

## 3. Task 3 — beam rendering

`beamBreakAt` had no opposite. Added `beamJoinAt(hand, frame)`: *do not start a group here*. It
stands down **only** `splitAtArpeggioLowPoints` — the one automatic cut that is a guess. A beam still
never crosses a key change, a clef change, a cue boundary or a tuplet boundary, because those are not
guesses about phrasing but things a beam cannot be drawn over.

- `SheetEdits.beamJoins: ReadonlySet<string>` keyed `hand:startFrame`, same shape as `beamBreaks`,
  filtered by `live` the same way, stored as `SavedRhythm.beamJoins`.
- Note toolbox: a link icon (**Beam all**) beside the scissors (**break**). Enabled only when the
  selection is ≥2 **whole** chords whose printed figures are all in `BEAMABLE_FIGURES` (corchea and
  shorter) — a negra has no beam to share.
- Joining clears any break on the same chords and vice versa: the two are opposite answers to one
  question and holding both would be the reader contradicting themselves.

### Even spacing over a run

Reported after the first pass: the beam of corcheas is not evenly spaced. It is not a bug — each
column is as wide as the ink in it and **both staves share the column**, so wherever the left hand
needs room at one of the right hand's onsets, that gap opens and its neighbours do not. Truthful, and
it reads as an uneven performance, which is the worse lie.

`ScoreAnnotations.evenSpacings: EvenSpacingAnnotation[]` — `{ hand, fromColumn, toColumn, scale }`.
Applied in `measureFrameWidths` **last of everything**, because being even is a statement about the
finished result and any rule running after it would undo it.

- The onsets of `hand` inside the range are read off `rungAt`, which the main loop already builds.
- Each gap is the sum of `pixels[onset[i] … onset[i+1] − 1]`.
- The target is `max(gaps) × scale` — the **tightest even spacing the run allows**, because every gap
  is the sum of widths its columns asked for and a smaller one cannot be drawn. `scale` is clamped
  from below at 1 in the measurer as well as in the UI and the schema.
- The slack is spread **proportionally** across a gap's columns rather than dumped on the last one,
  so the other hand's notes keep their place inside it.
- A run with fewer than two onsets of that hand is left alone.

`setEvenSpacings(runs)` is the setter, so plus and minus move the page instead of rebuilding it.

UI, in the note toolbox's **Beam** row, in the order the request asked for: `=` (`DragHandleIcon`,
which is exactly two bars), then `+` and `−`, **disabled until `=` has been pressed** — until then
there is no one distance for them to be a multiple of. `=` is enabled whenever the selection is two
or more onsets of one hand (`selectedRun`). Step: `EVEN_SPACING_STEP = 0.15`.

**`scale` was first clamped at 1 and that was wrong.** Reported: the minus refused to work, with a
tooltip claiming a column cannot be narrower than the note in it. Both halves were true and the
conclusion was not. `=` sets every gap to `max(gaps)`, and the widest gap in a run is usually wide
because of the **other** hand — a four-note chord with accidentals under one of these notes — so
evening a run makes the whole of it as wide as its worst moment, with the run's own noteheads left
swimming. A reader looking at that is right, and the control was second-guessing what was in front
of them over a collision they could see had not happened.

Now `MIN_EVEN_SPACING_SCALE = 0.25` … `MAX_EVEN_SPACING_SCALE = 4`, exported from the package so the
UI and the schema cannot drift from the drawing. Below 1 each gap is scaled **down** to the target
as well as up — `if (target === current) continue` rather than `if (target <= current)` — so the run
is genuinely even at any scale. Every column keeps `MIN_COLUMN_PX = 0.2`, because `FrameGrid` refuses
a width that is not positive. Glyphs may touch below 1; that is visible, one press back, and the
reader's to judge. The schema bound moved to `ge=0.25` and its round-trip test now asserts that a
tighter-than-measured run is **kept** rather than refused.

### Two more things the page was doing that nobody asked it to

**The ladder was printed through the octave bracket.** `corchea = 217 ms · ≈138 BPM` sat at
`trebleTopY − 12`, which is also where `drawOttavas` puts an `8va`. There is no free room under the
frame numbers — the label strip reaches the top of the system's own padding — so the header needed a
block of its own: `PASSAGE_HEADER_BLOCK = 16` added to `extraTopPadding` whenever the page carries
any header, and `drawPassageHeaders` now takes `baselineY` instead of `trebleTopY`, because only the
caller that reserved the room knows how much it reserved. Reserved on every system rather than per
system, so every line stays the same height and the paginator keeps counting them the simple way.

**The first attempt measured from the staff and was still caught.** `trebleTopY − padding.top − DROP`
is fine while `padding.top` is 60, and `padding.top` drops to 24 the moment the column numbers come
off — which is now the page's default. The deeper reason is that an octave bracket is the one thing
above a staff that is **not** at a fixed offset from it: `bracketY` clears the highest note in the
span, so over a passage reaching above the staff the bracket climbs and there is no height a header
can sit at and be safe. The baseline is now
`trebleTopY − padding.top − extraTopPadding + PASSAGE_HEADER_DROP` — the top of the system box, which
is the one line everything above the staff has to fit under. The two tests use notes high enough that
the bracket climbs, with the column numbers on and off; both fail against the pre-change source.

**An orange box appeared on the way to the ruler.** Not the corner marks — those are useful and stay.
It was `drawHoverPreview` in `draw-range-markers.ts`: hovering a corner outlines that marker's whole
stretch in the marker's own colour. A pointer travelling to the ruler crosses a corner, so the
outline appeared around some unrelated stretch and was then replaced by the reader's purple band —
the page looked like it had picked something itself and then changed its mind.

**Deleted from the package**, not gated behind an option. `drawHoverPreview`, the `band` option that
carried its geometry, the `mouseenter`/`mouseleave`/`focus`/`blur` listeners and `PREVIEW_DASH` are
gone; `hand-scope.test.ts` now asserts that hovering a corner draws nothing and still picks nothing.
An option defaulting to on would have left a way for it to come back, and it had already been
reported twice. The corner's own `<title>` names the columns, which is the same answer in words and
does not draw over the music to give it.

*(Two wrong turns on the way: I first read the report as being about the corner marks themselves and
turned those off — they are back. Then I hid the preview behind `rangeMarkerPreview: false` in the
app, which is correct but leaves the drawing code one prop away from returning.)*

### Show frame numbers

`frameLabels` existed only as a print option. It is now a live one — `GridNotationRendererOptions.frameLabels`
plus `setFrameLabels(show)`, a re-render and not a re-measure, because the numbers are a strip above
the staves and no column changes width. `TimeScoreView` takes `showFrameLabels`; `RhythmPage` holds
`frameLabelsOn` as plain view state (**not** a `SheetEdits` field — it is how the page is being
looked at, like the keyboard panel beside it) and starts it **off**.

`systemGapFor` had to learn about it. `padding.top` drops from `GRAND_STAFF_TOP_PADDING` (60) to
`GRAND_STAFF_TOP_PADDING_BARE` (24) when the labels are off, so subtracting the full `SYSTEM_ROOM`
would have made the same number on the space-between-lines slider mean two different gaps depending
on a switch that has nothing to do with it. `resolveSystemGap` would have floored it safely either
way; it would just have been lying.

### A drag is not a new selection

Reported: dragging the right-hand handle of a stretch moved the frames toolbox on top of it.
`dragEdge` reports through the same `onSelectRange` a fresh ruler click does, so `pickRange` was
re-placing the panel on every pixel of the drag — and `pressedAt.current` by then was the *handle*,
which is the end being dragged, so the panel walked along underneath the stretch.

`onSelectRange(range, { adjusting: true })` from `dragEdge`. `pickRange` places the panel only when
that flag is absent. Where a panel sits is the reader's from the moment it opens: it moves when they
drag it and at no other time.

Stored as `SavedRhythm.evenSpacings` (`schemas/rhythm.py: EvenSpacing`, `scale` bounded `1.0…4.0`),
and filtered by `live` like every other mark keyed by a column.

---

## 4. Task 4 — note editing

The panel was rewritten from prose plus dropdowns to controls plus tooltips.

| Was | Now |
|---|---|
| A `TextField select` of nine figure names | A row of seven drawn figures (`components/time/FigureGlyph.tsx`, tables in `music/figures.ts`), the printed figure filled in, plus ⌫ to un-name |
| Fingering buttons + two paragraphs | The buttons and a ⌫ |
| "Grace note", six interval buttons, a crushed/leaned-on pair, three paragraphs | **Decoration** chip → **Piano Edit**, a keyboard panel: the note being decorated in lavender, the decoration in pink, click a key to choose. Always `appoggiatura` |
| Two full-width hand buttons + a paragraph | `R`/`L` `ButtonGroup` |
| "Start a new beam here" + a paragraph | 🔗 / ✂ icon buttons |
| — | **Small** and **Trill** chips, moved here from the frames toolbox |
| A full-width error button + a paragraph | 🗑 |

**Delete takes the picked notes off the page**, one or many, by calling `hideSelected` — the same
function the trash button calls, so it is the same single step in the history and Command-Z brings
them back whichever way they went. A shortcut with its own code path would have been a second way to
delete a note and a second thing to keep in step with the undo.

Both `Delete` and `Backspace`: on a Mac the key most people call Delete sends `Backspace`. It stands
down inside `input, textarea, select, [contenteditable]`, and it calls `preventDefault` because
Backspace on a page with nothing focused is the browser's "go back", which would take the reader off
the sheet and lose everything unsaved.

Nothing new was needed for the undo. `hideSelected` writes `hiddenNotes` and `fingers` in one run of
the event loop, which `useEditHistory` already folds into one step — `check-history.ts` pins exactly
that shape ("two fields written in one run make one step", "one undo takes both fields back") using
these two fields. The key binding itself is app-level UI with no DOM harness on this page, so it is
verified by hand rather than by a test.

`putGrace(noteKey, row)` now takes an absolute row rather than a semitone offset. `GRACE_STEPS` and
`ALL_FIGURES` are gone.

`FigureGlyph` draws the shapes itself rather than using Bravura: the font is installed into the
document by the renderer, so a control using it would be blank on any screen where the sheet has not
been drawn yet. The two exported tables live in `music/figures.ts` because
`react-refresh/only-export-components` only tolerates primitive constant exports beside a component.

---

## 5. Task 5 — editing from the Piano dialog

`Piano.tsx` gained two optional props and stays a picture without them
(`PianoRollPage` and `NotesFallingPage` are unchanged):

- `keyColours?: Readonly<Record<number, string>>` — a named row is drawn as a `<rect>` in that
  colour instead of the pressed-key artwork, and a colour lights a key whether or not it is in
  `pressedKeys`.
- `onKeyPress?: (row) => void` + `keyTitle?` — adds an invisible hit layer, whites first then blacks
  so the black key wins where they overlap.

`RhythmPage`:

- `soundingByFrame` rewritten to carry `{ row, hand, onsetFrame }`. The onset is worked out by
  walking each hand's sparse matrix per row and breaking at a new attack or a gap in the columns —
  the same rule `renderOverrides.ownCells` uses. Hidden notes are excluded, so the keyboard and the
  sheet now agree (they did not before).
- Right hand `semantic.rightHand.onset` (blue), left hand `palette.dark.Orange` — orange rather than
  the roll's green, because green beside blue at key size is two shades of one thing.
- Click a lit key → the note is taken off the page (`hiddenNotes`, and its fingering goes).
- Click a dark key → `PUT /time/{uuid}/notes`, on the hand the **Add note R/L** pills say.
- Length: the longest `printedFrames` that hand is already holding at that column, else
  `round(anchorMs / frameMs)`. Documented as a starting point; the figure pills change it.
- Undo: `stageEdit("Note added", …)` marks the note removed and redraws; redo un-removes it.

### Struck here vs. held from earlier

Reported on Superestrella at f103: one notehead on the page, two Si lit on the keyboard. Not a bug
in the data or in the map — the right hand strikes **B6** at f103 and is still holding the **B5** it
struck at **f97**. Verified against the stored piece:

```
right  [('B5', 'held'), ('B6', 'onset')]
left   [('A#4', 'held'), ('C#5', 'held'), ('F#4', 'held')]
notes drawn at f103: [('right', 'B6', 'negra')]
notes drawn f96–f110 right: [(97, 'B5'), (97, 'B6'), (103, 'B6')]
```

The panel was truthful and unreadable: it could not say which lit key *begins* in this column. That
was tolerable while it only reported, and is not now that a key is something you click — clicking
the pale B5 takes off a note that starts three columns back.

`HELD_COLOUR` is the second shade per hand (`semantic.rightHand.sustain`, `palette.light.Orange` —
the roll's own held colour for the right hand, so a reader who has seen one has seen both).
`soundingColours` picks it whenever `note.onsetFrame !== playheadFrame`, and the tooltip on a held
key names the column the note began in before the reader presses it.

The legend is `KEY_LEGEND`: four swatches, **RH onset / RH sustain / LH onset / LH sustain**. It
replaced the paragraph that used to sit under the keyboard — a reader looking at a lit key looks
*across* at a swatch of the same colour, not down at a sentence about it — so the dialog is now the
pills, the legend and the keyboard, with nothing below it. `onset` and `sustain` are the words the
roll and the matrix already use, rather than a second vocabulary invented for this panel.

### Octave numbers on the keyboard

`Piano.tsx` draws the octave number at the foot of every Do — `key.midi % 12 === 0`, printed as
`midi / 12 - 1`, so C1…C8 on an 88-key board and middle C is 4. That is the same reckoning
`music/noteNames.ts` and `keyPositions.en` already use, so the panel, the tooltips and the roll
cannot disagree about what B4 means.

Drawn after the lit keys and in white on one, because slate on a filled key is hard to read. Left
off in `orientation="vertical"` (the Piano Roll): the whole drawing is turned a quarter turn there,
so the numbers would lie on their sides, and that view labels its notes itself.

### Backend: `PUT /time/{uuid}/notes`

`api/time_score.py: put_added_notes`. Times are the column's own (`startFrame × frameMs / 1000`) —
`trim_to_music` only trims the **end**, so a column maps straight to a second with no offset. Hand is
pinned on the `NoteEvent` the way `PUT /hands` pins a correction. A key already struck in that column
in either hand is refused and counted rather than merged, because the matrix rejects a frame where
both hands hold one key. Events are re-sorted and `forget_split_cache()` is called.

### Picking notes moves the cursor

`pickNotes` now calls `player.current.seek(min(frameOf(keys)) * frameMs / 1000)`. Every note is a
moment as well as a pitch, and the keyboard panel draws exactly one moment, so without this a reader
who clicked a chord got a note toolbox about it and a keyboard showing somewhere else. A band
spanning several columns resolves to its **first** column. The page is not scrolled — the reader is
already looking at what they clicked, the same choice the double-click seek makes.

`pickNotes` therefore depends on `frameMs`, so its identity changes when the column length does.
That is safe: `frameMs` also changes `score`, which rebuilds the sheet anyway.

**A float bug had to be fixed for it to work.** `playheadFrame` was
`Math.floor(playheadSeconds * 1000 / frameMs)`. A column turned into seconds and back lands a hair
*under* the whole number on roughly **1 % of columns** (measured: 148 of 20 000 at both 40 ms and
20 ms), so a cursor put exactly on a note fell into the column before it and the keyboard drew the
wrong chord. Now `Math.floor(… + 1e-6)`, which is nought mismatches at 11.6, 20, 25, 32, 33.333 and
40 ms over 200 000 columns, at both the start and the middle of each.

`ScorePlayer.seekTo` reports the clamped target straight back through `onTime`, so while the
recording is paused `playheadSeconds` is exactly what was asked for and the audio element's own
rounding never enters into it.

---

## 6. Task 6 — frames dialog

- **Applies to: Both / R / L** is the first row. It narrows the highlight and drives **Clef** and
  **Octave**.
- Pills laid out `repeat(3, 1fr)` — six of them do not fit in a row on a 360 px panel.
- **Trill** and **Small** removed; they are in the note toolbox now (§4).
- **Words** → **Lyrics**.
- **Spacing** is now a slider (25–400 %) with live redraw, replacing the *Narrower*/*Wider* pair.
- **Octave** shows one row when a hand is chosen, two when "Both" is.

### The §2.4 trap, avoided twice

A slider whose value is a build dependency rebuilds every note on every pixel of the drag. Two new
setters were added to the package for this:

- `setNoteSpacing(px)` (§1.3)
- `setSpacings(ranges)` — new; `annotations.spacings` used to be a build dependency of
  `TimeScoreView`, which was fine for two step buttons and is not fine for a handle.

Both re-measure and re-render; `TimeScoreView` reads both from refs inside the build and puts the
playhead and range handles back afterwards, because a horizontal change re-wraps.

---

## 7. What could not be built as written

**"Regarding the spacing… again, it depends on whether we have previously selected the left hand or
the right hand."**

A spacing range cannot be per hand. A column is one slice of wall clock and **both staves share it**
— that is the whole of what makes the two hands line up, and it is D-22/D-23, which `07-00-context.md`
says may not be reinterpreted. Widening a column for one hand would mean two `time → x` maps in one
system, and the hands would stop being vertically aligned.

Delivered instead: the slider, the live preview, and one line in the panel saying that spacing is
both staves whichever hand is chosen. **Clef** and **Octave** do honour the hand pills, which is
where the request's real value was.

---

## 8. Trill mark

The `tr` was a `TextAnnotation`, which is a word at a column and has nowhere to put a length. Added
`ScoreAnnotations.trills: TrillAnnotation[]` (just an anchor). `drawTrill` prints an italic `tr` at
the anchor's start and a **geometrically drawn wavy line** to the anchor's end — drawn rather than a
repeated font glyph so it stretches to exactly the columns the reader marked, which on a wall-clock
page a glyph multiple never would. A trill crossing a line break draws its part on each system and
prints `tr` only where it starts.

Bravura's `ornamentTrill` / `wiggleTrill` were not used: the package's glyph table carries exact
transcribed metadata boxes per glyph and adding two without the real metadata would be guesswork.

`shiftAnnotationColumns` shifts `trills` with everything else; `tests/annotations.test.ts` key list
updated.

---

## 9. Tests

New: `vexflow-v2/tests/sheet-spacing-and-beams.test.ts`, 26 tests — the 11 below plus six for even
spacing: that the fixture is genuinely uneven to begin with, that `=` sets every gap to the widest
one, that it never closes a gap, that a higher scale stays even, that a scale below one is held at
even, that the columns outside the run are untouched, and that a run of fewer than two onsets does
nothing.

**Proven against the pre-change source** (`git stash push` of the ten touched `src/` files, run,
`git stash pop`): **7 failed, 4 passed**. The four that passed are the controls — they assert
behaviour that deliberately did **not** change (the Alberti split survives, a one-rung step gets no
extra room, a jump from a negra gets none, `arpeggioDip: 1` still cuts).

New backend tests:

- `test_saved_rhythm.py` — clef changes round-trip / absent-reads-as-empty / a third clef is 422;
  beam joins round-trip; note spacing round-trip / absent-is-null / out of range is 422. (7)
- `test_time_score_api.py` — a note added from the keyboard reaches the score and can be taken off
  again by `/removed`; a key already struck is refused and counted. (2)

`check-render.mjs` extended by 10 checks: a clef change through `setClefForRange`, a clef transition
drawn, the space between notes moving the notes and putting them back, every notehead still drawn,
and an even run through `setEvenSpacings` — the fixture's own run measures `14.6, 20.2, 14.6` and
comes out `20.2, 20.2, 20.2`, so the check proves it on the app's own path and not only in a unit.

### Results

| Check | Result |
|---|---|
| `vexflow-v2` `vitest` | **465 passed** (52 files) |
| `vexflow-v2` `tsc -b && tsup` | clean, `dist/` rebuilt at 0.38.0 |
| `aitu-frontend` `npx tsc -b` | clean |
| `aitu-frontend` `npm run lint` | clean |
| `aitu-frontend` `npm run build` | clean |
| `aitu-frontend` `npm run check:render` | **44 passed, 0 failed** |
| `aitu-frontend` `npm run check:history` | every check passed |
| `aitu-backend` `pytest` | **903 passed, 1 failed** |

A wheel-zoom feature (`MIN_ZOOM`, `MAX_ZOOM`, `clampZoom`, `onZoomChange`, a zoom anchor) appeared
in the working copy of `TimeScoreView.tsx` part-way through this task, from outside this work, and
briefly broke `react-refresh/only-export-components`. Its author has since moved the function out and
lint is clean. Every change made here to that file survived the overlap; the counts above were
re-run after it.

The one backend failure is the documented pre-existing one,
`test_time_score_payload.py::test_the_worked_example_at_00_46_prints_three_equal_corcheas`. Both that
test file and `matrix/hands.py` were already modified in the working tree before this task started
(see the session's opening `git status`), so the failure is not from this work.

---

## 10. Files touched

### `../vexflow-v2` (0.38.0)

| File | Why |
|---|---|
| `notation/beam-groups.ts` | `ARPEGGIO_DIP`, `arpeggioDip`, `beamJoinAt` |
| `notation/spacing.ts` | `FIGURE_RUNG`, `LONG_NOTE_APPROACH_SPACES`, `noteSpacingPx` |
| `notation/draw-music.ts` | threads `beamJoinAt`, `arpeggioDip` |
| `renderer/draw-grand-staff.ts` | threads both, computes `handBands` |
| `renderer/grid-notation-renderer.ts` | the three new options, `setNoteSpacing`, `setSpacings`, `clampNoteSpacing` |
| `ruler/frame-ruler.ts` | `FrameRangeSelection.hand`, `StaffBands`, banded highlight |
| `annotations/types.ts` | `TrillAnnotation`, `ScoreAnnotations.trills` |
| `annotations/draw-annotations.ts` | `drawTrill`, `wavyPath` |
| `annotations/shift-columns.ts` | shifts `trills` |
| `index.ts` | exports `TrillAnnotation` |
| `tests/annotations.test.ts` | key list |
| `tests/sheet-spacing-and-beams.test.ts` | **new** |
| `documentation/03-rendering.md`, `05-annotations.md` | the new options and annotations |

### `aitu-frontend`

| File | Why |
|---|---|
| `pages/playground/RhythmPage.tsx` | every task |
| `components/time/TimeScoreView.tsx` | `clefChanges`, `beamJoins`, `noteSpacing`, trills, `spacings` by setter, `selectedRange.hand` |
| `components/time/FigureGlyph.tsx` | **new** |
| `music/figures.ts` | **new** |
| `piano/Piano.tsx` | `keyColours`, `onKeyPress`, `keyTitle` |
| `api/timeScore.ts` | `addNotes`, `clefChanges`, `beamJoins`, `noteSpacing` |
| `scripts/check-render.mjs` | six checks |

### `aitu-backend`

| File | Why |
|---|---|
| `schemas/rhythm.py` | `ClefChange`, `clef_changes`, `beam_joins`, `note_spacing` |
| `api/time_score.py` | `PUT /{uuid}/notes` |
| `tests/test_saved_rhythm.py`, `tests/test_time_score_api.py` | 9 new tests |

### Documentation

`context/frontend/annotations.md`, `documentation/services/frontend/grid-notation.md`,
`documentation/services/backend/rhythm-and-annotations.md`,
`documentation/services/backend/endpoints.md`.

---

## 11. Known issue, not introduced here and now three times more likely

`useEditHistory` opens one step per run of the event loop. A slider drag fires many `onChange`
events, so it records many steps and can push the 100-step limit until earlier edits fall off the
end. This was already true of the **Space between lines** slider shipped in 06; there are now three
sliders. The fix is a coalescing rule in the reducer (consecutive writes to the same single field
join one step) and it was left out of this task deliberately, because it changes the undo model and
belongs in its own change with its own `check:history` cases.
