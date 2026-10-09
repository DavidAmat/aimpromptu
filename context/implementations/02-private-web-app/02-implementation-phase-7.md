# 02: Phase 7 report: the sheet toolbox (transposition, lyrics, keys and clefs of passages)

Plan: [`02-plan.md`](02-plan.md) sections 11.4 to 11.7, and section 20, Phase 7. Checklist:
[`02-checklist.md`](02-checklist.md). Branch `feat/phase-7`, made from `master` at `f0477bb`
(Phase 6 merged and pushed at the start of this session, after the user's check). Done 2026-10-07
on the Ubuntu machine. The drawing package `vexflow-v2` moved to 0.43.0 (section 5).

# 1. Summary

| Story | Result |
|---|---|
| 7.1 Transposition | The sheet toolbox's **Figures** tab became **Transpose**: **Notes** (two `MiniPiano`s, From and To) and **Figures** (two `FigurePicker`s), each with **Preview**, one dialog for both (the sheet as it would be, the facts, **Transpose** or **Cancel**). Notes are moved on the backend (`POST /time/{id}/transpose`) with an exact undo; the key, the key changes and every mark addressed by a key move with them. Figures shift the main figure, the figures set by hand and the next **From**; beam marks that no longer fit are removed and counted |
| 7.2 Lyrics | A **Lyrics** tab in the sheet toolbox: paste, the pool, a piece dragged onto the sheet lands on the frame under the pointer, moves and resizes snapped to frames (package 0.43.0), the edit toolbar (merge, split at the cursor, line break, smaller, larger, back to the pool, delete), picking by click, Command-click and a stretch marked above the staves. Words saved before are read as placed pieces. The range toolbox's Lyrics tab is gone |
| 7.3 Passages | **Key for this passage** in the range toolbox's Key tab. The clef rule (`suggestClefRanges`, package 0.43.0) taken on a first write and offered again in the Clef tab; its numbers measured on the 38 pieces with notes; a proposed octave bracket is cut where a clef change begins |
| 7.4 Documentation | `annotations.md`, `annotations-sheet.md`, `annotations-stretches.md`, `rendering.md`, `projects.md`; `rhythm-and-annotations.md`, `endpoints.md`, `components.md`, `aitu-frontend/README.md`; the package's `05-annotations.md`; the plan's "as built in Phase 7" notes |

Checks at the end (section 7): backend 1,095 tests on the CPU (the GPU was held by another
project), 1,091 passed, the 3 known CPU failures, 1 skip; every frontend check passes, the new
`check:transpose`, `check:lyrics` and the clefs half too (39 checks, two clean runs in a row).

# 2. Story 7.1: transposition

## 2.1 Notes (`notation/transpose.py`, `POST /time/{id}/transpose`)

`transpose_events(events, semitones, hold, restore)` returns new events: every note moves by
`semitones`, the notes taken off the page too (so putting one back later brings it back in the new
key). A note that would leave the 88 keys is **taken off** (`removed`) and left on its key; its id
goes to `held` and `taken_off`. Times never change, so no column moves and every mark keyed by a
column stays on its music; each note keeps its `hand`.

The route writes through `pipeline.save_edit(notes_changed=True, hands_changed=True,
sheet_follows=True)`: the notes revision rises; with the hands complete before, `handsNotesRevision`
follows the notes, so the Hands step stays ready; a saved sheet that was current stays current (the
page that asks draws the result, as a hand move does). `preview` writes nothing and answers the
counts. `422` for 0 semitones; a library version answers `403` (it is a write).

**The undo is exact.** The same route with the opposite interval, `hold` = the answer's `held` and
`restore` = its `takenOff`: the held notes do not move, the taken-off ones are put back, every other
note moves back. A test checks the notes are equal, id by id, after a transposition that takes two
bass notes off the keyboard and its undo.

**The preview sheet.** `POST /time/{id}/score` gained `transpose`: the stored notes are moved in
memory and split by `pipeline.split_events` (the body of `split_of`'s `compute`, made public,
without the cache), and the page edits are applied as usual. The page sends `hiddenNotes` and
`trills` already moved, because they are addressed by key.

**On the page** (`SheetPage.previewNotes`, `confirmTranspose`): the preview asks for the counts and
the sheet at once and shows them in `TransposeDialog` (a read-only `TimeScoreView`). **Transpose**
writes, then in the same gesture stages the step (its `undo` and `redo` call the route and draw
again) and sets the key signature (`transposeKey`: of the signatures with the new tonic, the one
with fewer accidentals; a tie keeps the flat or sharp side), the key changes, and the marks
addressed by a key (`transposeRowMarks`: fingering, notes taken off the page, trills, grace notes;
one whose note left the keyboard goes). Measured in the browser on a copy of Elefants: 1,292 notes
moved two semitones, the key Db major became Eb major, undo and redo gave the notes back exactly.

**Not done on purpose.** The marks moved on the page are saved by **Save**, like a hand move's
fingerings: a reader who transposes and leaves without saving keeps the moved notes and the old
key in `sheet.json` (the unsaved dot says so). Writing the key on the backend too would have made
the route know about the sheet's marks; it stays the page's.

## 2.2 Figures (a page edit)

`figureSteps(from, to)` on the ladder semifusa…redonda; the main figure moves by that many rungs
(`shiftFigure`), which renames every figure by proportion and moves nothing (D-18). A figure set by
hand moves with the rest; a dotted negra or blanca stays dotted where a dotted figure exists, and
one with nothing to become is removed. The preview's sheet gives each chord's printed figure; a
beam break or join on a chord that prints a negra or longer is removed. The dialog says "Every
figure becomes one step shorter. No note moves." and, when it applies, "Removed, because they no
longer fit: n beam marks, m figures set by hand." **Transpose** is one step: `anchorFigure`,
`figuresFrom` (the **To**), the overrides and the beam marks. **From** opens on `figuresFrom` (negra
the first time). A step that would take the main figure off the ladder disables **Preview** ("No
shorter or longer figure left").

# 3. Story 7.2: lyrics

## 3.1 The model: a piece is today's `Lyric`

The plan named new fields (`id`, `fromFrame`, `toFrame`, `lines`, `width`). They were not needed:
`fromColumn`/`toColumn` are already frames; a line break is a newline in `text` (the package always
breaks there); `offsetY` and `fontSize` exist; and the width of a piece **is its frames** (the right
edge is pulled to a frame). Two pieces never share a frame, so the first frame names a piece and no
id is stored. So `sheet.json` did not change shape, and words saved before read as placed pieces
with nothing to convert: their `offsetX` and pixel `width` are kept and drawn until the piece is
moved, when the frames take over (`lyricsPieces.movePiece`).

## 3.2 Snapping, in the package

`GridNotationRenderer` takes `onLyricPlace`. The drawing reports where a dragged block ended (its
edges and middle, in drawing units, `onLyricDrop` of the annotations); the renderer turns that into
frames (`placeLyricDrop`): the left edge to the nearest frame of the line the block's middle is
over (another line too), keeping the number of frames; a pulled right edge to the nearest frame, at
least one after the start. A move to another line takes the lines' distance off the vertical offset.
`renderer.frameAtClientPoint(clientX, clientY)` names the frame under a point on screen; the page
uses it for a piece dropped from the pool (the browser's own drag and drop, data type
`application/x-aitu-lyrics-piece`).

`lyricIsPlaced` is now true only for a move sideways (`offsetX` not 0): a piece lifted over its
frames is still as wide as them and still asks them for room.

## 3.3 Two defects found by the screenshots

- **A block narrower than its words.** A dropped "second line" wrapped into two lines. The spacing
  pass opens the frames under a lyric to hold its words, but a later rule (silence charged per
  group of frames) closed them again, and the wrap had no rounding margin. Fixed in the package: an
  untouched block is never narrower than its words on one line, and the wrap has half a pixel of
  give (test in `lyric-snapping.test.ts`).
- **Saved words came back as 32-pixel blocks.** The backend answers an unset `width`, `offsetX`,
  `offsetY` or `fontSize` as `null`; the page passed `null` to the package, which read it as a
  width of 32 pixels and a block moved sideways. This was there before Phase 7 (any saved words
  came back like that) and showed now because pieces are saved more. Fixed twice: `editsFromSaved`
  drops the `null` fields, and `TimeScoreView` treats `null` as absent; the `LyricLine` type says
  `number | null`. `check:lyrics` reloads after **Save** and checks the piece draws on one line.

## 3.4 The tab and the gestures

`LyricsTab.tsx`: **Paste the lyrics**, **Add to the pool** (one piece per non-empty line), the pool
(each a chip, draggable, with a delete), and for the picked pieces the **Words** field (one piece;
Enter splits at the cursor) and the toolbar (`IconAction`s with tooltips). The functions on the
list are pure, in `lyricsPieces.ts`, each returning the new list or the sentence of a refusal, which
the floating bar's message shows ("Another lyrics piece is already over those frames."). A piece
dropped is held 120 ms a character, never past the next piece. Split shares the frames in
proportion to the words. Back to the pool puts the pieces at the top of the pool, one line each.

While the Lyrics tab is open (`lyricsMode`), a click on a piece picks it (the package's
`onAnnotationSelect`, with Command read from the press), and a stretch marked above the staves picks
the pieces over it instead of opening the range toolbox; Delete deletes the picked pieces. The
picked pieces are outlined by a `<style>` rule on their first frame, so a redraw the page did not
ask for keeps the outline. Clicking a piece, or its corner mark, opens the toolbox on this tab. The
handlers the sheet keeps read the mode and the list through refs, so they keep their identity and
the sheet is not rebuilt.

## 3.5 The look, after the user's review (2026-10-09)

The user asked for the lyric blocks to sit in the page: no border, a light gray background, a font
made for lyrics, and a text colour that feels clean. In the package (still 0.43.0, not pushed):
`LYRIC_BOX_FILL` `#f1f2f4` with no stroke, the words in `LYRIC_FONT` (Lora, then Georgia, Times),
italic, weight 500, in `LYRIC_TEXT_FILL` `#3b3f46`. Lora italic (SIL OFL 1.1, the Latin subset,
which covers Spanish and Catalan) is self-hosted in `public/fonts/lora-italic.woff2`, declared in
`src/index.css` like Geist and Montserrat. The PDF writer maps a serif family to Times, so a printed
sheet shows the words in Times Italic. A picked piece is `#e5e8ec` with a 1.5 px `#5b6b82` outline
(the `<style>` rule of `TimeScoreView`). `check:lyrics` passes again; shots 07 to 12 are retaken.

**Second review, the same day.** The user asked for the words alone: no block at rest, the block
(and what resizes it) only while a piece is picked, and plain text again on Escape or a click
elsewhere. So `LYRIC_BOX_FILL` is now `transparent` (the block still takes the pointer); the page
draws, by CSS, a faint `#f4f5f7` block under a pointer resting on a piece, and for a picked piece
`#f1f2f4` with a 1 px `#8592a6` outline and the grip of the right edge shown as a bar. The corner
marks of a lyric are left off (`[data-kind="lyric"]`): the words are what a reader clicks. Escape
and a press on the sheet anywhere but a piece (`onLyricsClear`) let the pieces go. `check:lyrics`
checks the four states.

**Save lyrics** (asked in the same review): the Lyrics tab's field is the song's words, saved with
the part by `PUT /time/{uuid}/lyrics` into `parts[].lyrics` of `project.json` (not `sheet.json`,
which **Remove all** and a new transcription delete), read back by `GET` when the page opens. The
button is first, beside **Add to the pool**; it reads **Lyrics saved** when the field holds what is
saved. **Add to the pool** no longer empties the field. The draft is held by the page, so it
outlives a change of tab. Not an edit of the sheet: no undo, and the sheet's **Save** does not carry
it. A backend test checks the save, the trim, `null` for an empty text, and that the words outlive
`DELETE /time/{uuid}/rhythm`.

**Editing a piece of the pool** (third review): a click on a piece of the pool turns it into a
field; Enter makes a new line; leaving the field (or Command-Enter) replaces the piece by one piece
per line in the same place (`lyricsPieces.editPoolPiece`), one undo step; Escape drops the change;
no words left removes the piece. `check:lyrics` breaks "of words second line" into two pieces and
checks the order (shot 10b).

**Fourth review: the pool keeps its pieces, no overlap, the frame under the pointer.**

- The pool keeps every piece; a piece on the sheet has a green tick (`placedInPool`: words compared
  with line breaks and spaces folded, a line placed twice ticks two pieces in pool order). A drop no
  longer removes the piece; **Back to the pool** only removes from the sheet and adds words the pool
  lacks (a merge or a split) at the top; Delete removes from the sheet only.
- **"It lands to the right".** `frameAtClientPoint` and the move snapping read the **nearest frame
  line**; a notehead is drawn just right of its line, so a drop on a note in a narrow column took
  the next frame. Both now read the column that holds the point, as a click above the staves does
  (`'floor'`), a move with 4 units of give. `check:lyrics` drops on a right-hand notehead and checks
  the piece starts on that note's frame (f323 on f323).
- **No overlap, and visible.** `showLyricGuide` in the package shades, over the strip above the
  treble staff, every other piece's frames in gray with an end line at each side, and the frames
  the dragged piece would cover in green or red. The package calls it during a block drag
  (`onLyricDragging`); the page calls it during a pool drag (`guidePoolDrag`, from `dragover`, once
  per frame). A move onto another piece is refused in the package (the block is drawn back, nothing
  reported); a pulled edge stops at the next piece; a pool drop on a frame another piece covers is
  refused. Tests: four in `lyric-snapping.test.ts` (519 in the package); `check:lyrics` checks the
  red guide and both refusals (shot 08b).

**Fifth review: Enter splits the pool piece at once.** The pool's edit field was multi-line: Enter
added a line and the field stayed open, showing one piece on two lines. It is now one line; Enter,
or the scissors at its right end, splits the piece at the cursor (`splitPoolEdit`: a newline at the
cursor, then `editPoolPiece`) and closes the field; the scissors keep the focus on a press so the
cursor is still where the split goes. A ref stops the blur of the closing field from keeping a
change twice, or one that Escape dropped. `check:lyrics` splits with Enter and with the scissors
(shot 10a).

**Sixth review: merge pieces of the pool.** Command-click picks pieces of the pool (a plain click
still edits); a row above the list offers **Merge n pieces** (from two) and **Cancel**.
`mergePoolPieces` joins them with a space, in pool order, in the place of the first. The picked
places are held for the pool they were picked in, so any change of the pool lets them go and a
place never names another piece. `check:lyrics` merges the two halves of the scissors split back
(shot 10c).

**Seventh review: a tick box per piece, consecutive only, Merge by the title.** Command-click was
not discoverable. A pool piece is now a small row of its own (MUI's chip has room for one icon on
the right): the green tick when on the sheet, the words (a click edits them), a **tick box**, and
the cross. The ticked pieces are always one run of consecutive pieces: with some ticked, only the
piece just before or after the run can be ticked and only an end unticked; the other boxes are
disabled and say why in their tooltip. **Merge** is beside "Pool (n)", disabled until two are
ticked. A defect found by `check:lyrics`: the tooltip of one button covered the button beside it,
because MUI tooltips are interactive (they catch the pointer); `IconAction` tooltips are now
`disableInteractive` across the app, and `check:projects`, `check:library`, `check:flow` and the
whole toolbox script pass again.

**Eighth review: Save lyrics saves the pool too.** The pool was saved by the sheet's **Save**
(`sheet.json`); now **Save lyrics** saves it with the words: `parts[].lyricsPool` in `project.json`,
through `PUT /time/{uuid}/lyrics` (`pool`; absent keeps the saved one). The button is offered when
the words or the pool differ from what is saved. The page reads the reading and the saved lyrics
in one `Promise.all`, so neither overwrites the other's pool; the pool saved by **Save lyrics**
wins, a pool an older sheet saved in `sheet.json` is the fallback, and `PUT /time/{uuid}/rhythm`
without `lyricsPool` keeps that older pool (so nothing saved in the last days is lost). The sheet's
unsaved dot ignores the pool (`sameSheet`), its Save no longer sends it, and **Remove all** keeps it.
One backend test (the pool saved, absent keeps it, a sheet saved without it keeps the older one);
`check:lyrics` checks the button comes back after a pool change and the pool after a reload.

# 4. Story 7.3: keys and clefs of passages

## 4.1 Key for this passage

`passageKeyHint` asks the drawing (`suggestKeyFor(from, to)`, the same count the page prints with)
and offers a key only when it saves accidentals over the one in force there. The button names the
major key as the key picker does ("Use Bb major here"; the plan's example was in Spanish, the
pickers are in English since Phase 2). One press is `applyKeySignatureRange`. Checked in the browser
with the piece put in C major: the stretch offered Bb major, and the Key tab got its dot.

## 4.2 The clef rule (`suggestClefRanges`, `DEFAULT_CLEF_RULE`)

As built: a left-hand chord is **high** when its lowest note is 2 ledger lines or more above the
bass staff (E4); 4 high chords or more in a row print in the treble clef; one lower chord in a row
stays inside the run **only if it prints no more ledger lines on the treble staff than on the bass
staff**; a run must save ledger lines; it ends at its last chord's end or the next left-hand onset.
`suggestClefChanges` writes the transitions. `TimeScoreView` reports them on every build
(`onClefSuggestion`); the page takes them once, on a first write (`clefsDecided`, after the key like
the brackets). The Clef tab offers the runs inside the stretch again.

**Measured** (a read-only script over `GET /time/{id}/score` of the 38 projects with notes; runs /
pieces with a run / left-hand onsets in runs):

| Setting | Runs | Pieces | Onsets |
|---|---|---|---|
| 1 ledger line, 4 chords | 95 | 16 | 744 |
| **2 ledger lines, 4 chords** (kept) | **62** | **10** | **440** |
| 2 ledger lines, 6 chords | 18 | 8 | 236 |
| 3 ledger lines, 4 chords | 42 | 9 | 311 |

With one ledger line the rule reached pieces whose left hand only touches middle C; six chords drops
most runs of the tutorials whose left hand really plays high. The kept setting gives runs on 10
pieces, mostly Superestrella's tutorial and The Other Side, and none on 28.

**What the first screenshot showed, and what changed.** The first version held any one lower chord
inside a run; on Superestrella a low chord then printed four ledger lines under the treble staff.
The hold now needs the chord to read no worse there. The second screenshot showed three high chords
left with no bracket: the octave suggestion ran on into the treble run and the page dropped the
whole bracket; `clearOfClefChanges` now cuts a bracket where a clef change begins. Shot 13 shows the
result: an `8va` over the three chords, then the treble run, then the bass clef again.

**A limit of the package:** no clef change can be stored at frame 0 (each hand starts on its own
clef), so a run that opens the piece stays in the bass clef. A test states it.

# 5. The drawing package, `vexflow-v2` 0.43.0

Branch `plan-resume`, two commits, **not pushed** (the phase rule speaks of this repository only;
the walkthrough asks):

- `427d3f3`: a fix from implementation 08 (2026-10-01) that was in the working tree and already in
  `dist/`, uncommitted: a middle line of a wrapped octave bracket no longer throws when the pointer
  leaves its band. Committed as it was, with its test.
- `f049ba5` 0.43.0: `clef-rule.ts`, `onLyricDrop`/`onLyricPlace`/`LyricPlaceChange`,
  `frameAtClientPoint`, `lyricIsPlaced` for a sideways move only, the lyric width and wrap fixes,
  `documentation/05-annotations.md`; tests `clef-rule.test.ts` (9) and `lyric-snapping.test.ts` (7).
  515 tests pass; lint and Prettier clean.

`package-lock.json` there differs from git only by npm's own rewrite (the version and `libc`
fields), as it did before this phase; left uncommitted. The frontend image builds its own copy of
the package, so `make up` was run after each change of it.

# 6. Tests

| File | Tests | What |
|---|---|---|
| `test_time_score_api.py` | 4 new | every note moves and no time does, the preview writes nothing, the notes revision rises; notes leaving the keyboard are taken off and the undo is exact id by id; the preview sheet draws the moved notes and writes nothing; 0 semitones is refused |
| `vexflow-v2/tests/clef-rule.test.ts` | 9 new | a run of four; shorter runs; one ledger line is not high; a harmless lower chord held, two not; a low chord never held; the run ends at the next low note; the two transitions; frame 0; options |
| `vexflow-v2/tests/lyric-snapping.test.ts` | 7 new | a move snaps and keeps the length; a pulled edge lands on a frame and never before the start; reported instead of the pixel layout; raised is not placed; the frame under a point; off the drawing; a block as wide as its words keeps one line |

# 7. The checks

| Check | Result |
|---|---|
| Backend, full run **on the CPU** (another project held 11 GB of the GPU) | 1,095 tests: 1,091 passed, 1 skipped (the real-model test), 3 failed: the known `test_the_worked_example_at_00_46_prints_three_equal_corcheas` and the two Transkun tests that fail only without a GPU (Phase 0 report, section 4.2). Phase 6: 1,091 tests |
| `vexflow-v2`: `npm test`, lint, Prettier, build | 515 passed (0.42.0: 499); clean |
| `tsc -b`, `npm run lint`, `npm run build` | clean; the chunk-size warning of Phase 0 |
| `check:render`, `check:history`, `check:note-names`, `check:geometry`, `check:cuts`, `check:notes` | 60, all, 15, all, all, all passed |
| `check:projects`, `check:library`, signed in | every check passed, no console error |
| `check:transpose`, `check:lyrics`, `--only clefs` (new, `scripts/check-sheet-toolbox.mjs`) | 39 checks, two clean runs in a row, nothing left behind. The one 404 accepted is `GET /time/{id}/rhythm` of a sheet with no saved reading, which the page reads as "nothing saved" |
| `check:flow`, signed in, with the live transcription | every check passed, no console error |
| `bench:sheet`, median of a hand move, three runs | Elefants 214 to 221 ms, Superestrella tutorial 273 to 286 ms, The Other Side 521 to 532 ms (Phase 6: 221, 279, 475; Phase 5: 212, 270, 516; implementation 08: 599 for The Other Side). The Other Side is within the earlier range and under the reference of plan section 20; nothing of this phase is on the path of a hand move except one cheap suggestion per build |
| `time:flow`, the first piano sheet | 0.6 s, 0.9 s, 0.5 s (Phase 6: the same); notes saved 26.9 s, 51.0 s, 20.9 s |
| `make db-check` on the real `.database/` | 40 projects, no problem, after every script |
| `scripts/docs/check-links.py` | passes |

The browser scripts signed in with `AITU_MASTER_PASSWORD` of `.env`.

# 8. The 13 checks of the 09 guidelines

Run on the Transpose tab and dialog, the Lyrics tab, and the range toolbox's Key and Clef tabs,
with the screenshots of [`screenshots/phase-7/`](screenshots/phase-7/), taken by
`check-sheet-toolbox.mjs` on its own copies.

| # | Check | Result |
|---|---|---|
| 1 | One sentence | Transpose: move every note, or rename every figure, after seeing the result. Lyrics: put the words of the song on the sheet |
| 2 | Every sentence a label, control or fact | The dialog's lines are facts the reader acts on (what moves, how the key moves, how many notes leave the keyboard, what is removed) |
| 3 | Words above the first content | Transpose: "Notes / Figures", "From Do 4", "To Re 4". Lyrics: "Paste the lyrics" |
| 4 | Very wide | The toolbox keeps its width (400 px); the dialog's sheet takes the dialog's width |
| 5 | Narrow (390 px, shots 11, 14, 15) | 0 px of sideways scroll; the keyboards scroll inside their own box; the dialog's sheet re-wraps |
| 6 | Longest, shortest, none | A long lyric line is cut with "…" in the pool, full on hover; an empty paste disables **Add to the pool**; no pool, no list; no piece picked, no toolbar |
| 7 | Buttons say what happens | "Preview", "Transpose", "Cancel", "Add to the pool", "Use Bb major here", "Treble clef for the high left-hand notes (n)"; icon actions say it in their tooltips ("Merge the picked pieces into one", "Split the piece where the cursor is (Enter)", "Back to the pool") |
| 8 | Helper lines | None added. Dragging a pool piece is said in its tooltip ("… — drag onto the sheet") |
| 9 | Loading, empty, partial, error | The dialog keeps the sheet's place with a spinner while it is written; a failed preview or write is an error line in the dialog; a refused move or drop is the floating bar's message |
| 10 | Tab through it | Segmented tabs, the `MiniPiano`s (arrows move a semitone or an octave), the figure pickers, the dialog's buttons. Dragging a piece from the pool needs a pointer (section 11) |
| 11 | Internal names | None: no "semitones" in a button, no "pmn", "row", "column", "offset" |
| 12 | First-time user | "Transpose", "From", "To", "Pool", "Words", "Back to the pool" |
| 13 | Anti-patterns | No lecture: the dialog says what changes in two or three lines |

| Shot | Page |
|---|---|
| 01 | Transpose → Notes, the preview dialog (Do 4 to Re 4, Db major to Eb major, 1,292 notes) |
| 02 | The sheet after **Transpose** and **Save** |
| 03, 04 | Transpose → Figures, the preview; the tab reopened, **From** on corchea |
| 05, 06 | A stretch: "Use Bb major here"; its Clef tab |
| 07 to 10 | Lyrics: the pool; a piece dropped; two pieces picked; after split, line break and larger |
| 11, 12 | 390 px and dark: the Lyrics tab |
| 13 | The clef rule on a first write of Superestrella's tutorial |
| 14 to 16 | 390 px: the Transpose tab and its dialog; dark: the Transpose tab |

# 9. Documentation

- Context: `frontend/annotations.md` (the defaults with the clef rule, five edits on the recording),
  `annotations-sheet.md` (Transpose and Lyrics), `annotations-stretches.md` (Key for this passage,
  the clef rule, no Lyrics tab), `rendering.md` (which clefs the page proposes, with the
  measurement), `projects.md` (the Sheet step).
- Detail: `endpoints.md` (`POST /time/{uuid}/transpose`, the score's `transpose`),
  `rhythm-and-annotations.md` (`lyricsPool`, `figuresFrom`, lyrics as pieces, `null` read as
  absent), `components.md` (the new modules, `music/transpose.ts`, the checks),
  `aitu-frontend/README.md` (the checks).
- The plan: "as built in Phase 7" notes in sections 11.4 to 11.7; Q-7 and Q-8 rows.
- `vexflow-v2/documentation/05-annotations.md`.

# 10. Q-7 and Q-8, for the user

Unchanged since Phase 6 (its report, section 5): Q-7, offline downloads per project, recommended to
leave for the production version; Q-8, live notes from the video reader, recommended to keep one job
with its stages (the Phase 5 report, section 4.5, has the measurement). Both asked again in this
walkthrough. Nothing built in Phase 7 depends on either answer.

# 11. Open points

- **`vexflow-v2` is committed, not pushed** (section 5): the walkthrough asks.
- **Dragging from the pool needs a mouse or a trackpad**: the browser's drag and drop does not run
  on a touch screen. An iPad would need a "place at the playhead" button; not built.
- **A notes transposition's marks are page edits until Save** (section 2.1).
- **A clef run at frame 0** stays in the bass clef (package limit, section 4.2).
- **Play mode** shows the lyrics pieces by their frames: Phase 11.

# 12. Learnings for later phases

- **The backend answers an unset optional field as `null`, not absent.** Anything that spreads a
  saved field into the drawing package must treat `null` as absent; read saved values through one
  function that drops them.
- **A rule taken on a first write meets the other rules taken in the same build.** The clef rule and
  the octave suggestion each looked right alone; together a bracket ran into a clef change and was
  dropped. Take them in a fixed order inside one functional update, and reconcile there.
- **`[data-…] svg` matches a spinner.** Wait for something only the real drawing has
  (`.grid-onset-group`).
- **Text drawn line by line has no spaces between its lines** in `textContent`: read `tspan`s.
- **A script that copies "the project named X" must skip its own copies**, which carry the name too.
- **Lay a measurement over the whole library before choosing a constant**: one ledger line looked
  natural and doubled the pieces touched.
