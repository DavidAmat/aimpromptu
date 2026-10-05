# 02: Phase 2 report: the sheet page

Plan: [`02-plan.md`](02-plan.md) sections 4 (D-09), 11.1 to 11.4, 11.6, and section 20, Phase 2.
Checklist: [`02-checklist.md`](02-checklist.md). Branch `feat/phase-2`, made from `master` at
`1ebe100`. Done 2026-10-06 on the Ubuntu machine.

# 1. Summary

| Story | Result |
|---|---|
| 2.1 The split | `RhythmPage.tsx` (5,328 lines) became `pages/piece/sheet/` (11 modules). Twelve screenshots of the Sheet step identical **byte for byte** to the old code; `check:flow` 80 of 80. Committed alone (`1dc3b27`) before any change of behaviour |
| 2.2 The defaults | The backend chooses the figure ladder: the highest pile of gaps is a negra (`default_anchor`, `GET /time/{uuid}/default-reading`, 9 tests); the note under D-09. The key with the fewest accidentals and the octave brackets are applied on the first write |
| 2.3 The page | The cards, the plot and the captions gone; the sheet drawn on arrival; the floating bar; the sheet toolbox (Title, Key, Figures, Layout); the range and note toolboxes as icon actions with tooltips; Speed as a range tab. **The line wrap was broken** for a window made narrower; fixed. Timings at or under implementation 08 |
| 2.4 Documentation | `annotations.md` rewritten and split into four pages under 200 lines; components, endpoints, rhythm fields, D-09, flow-page and the indexes updated |

Checks at the end: `tsc -b` and `npm run lint` clean, `npm run build` passes (the chunk-size warning
of Phase 0), every `check:*` passes (`check:flow` 82 checks with the live transcription), backend on
the CPU 1,044 passed, 3 failed (the known three), 1 skipped, `scripts/docs/check-links.py` passes.

# 2. Story 2.1: the split

## 2.1 The modules

| Module | Lines | What it holds |
|---|---:|---|
| `SheetPage.tsx` | 2,110 | The state the modules share, the requests, the effects, the layout |
| `sheetEdits.ts` | 463 | `SheetEdits`, `NO_EDITS`, the undo labels, `editsFromSaved`, `savedRhythmOf`, `hiddenNotesOut` |
| `sheetConstants.ts` | 223 | Colours of the keyboards, `FRAME_TABS`, the clef and bracket choices, `SHIFT_LADDER`, helpers |
| `toolboxPlacement.ts` | 146 | Where a toolbox opens |
| `useNoteActions.ts`, `NoteToolbox.tsx` | 634, 343 | The note toolbox's derived values and actions; the panel |
| `useRangeActions.ts`, `RangeToolbox.tsx` | 214, 695 | The same for a stretch; the panel |
| `SheetToolbox.tsx` | 343 | The sheet toolbox (Phase 2 step 2; in step 1 it was `SheetControls.tsx`, the row of controls under the player) |
| `SheetFloatingBar.tsx` | 226 | The floating bar and its two messages |
| `PianoToolboxes.tsx` | 231 | The keyboard under the playhead and the decoration keyboard |

The page is still 2,110 lines, most of it the comments of each callback. The next split would move
the requests (default reading, saved reading, sheet, save, Remove all) into a `useSheetReading` hook;
not needed for this phase.

## 2.2 How "no change of behaviour" was checked

The code was moved verbatim (Python extraction by line ranges, then props), the hooks hold only
`useMemo` and `useCallback`, and every effect stayed in the page in its old order. Then:

- A scratch Playwright script took 12 pictures of the Sheet step on a temporary copy of Superestrella
  (`b99bc3ae`): the page, the full page, the note toolbox, two notes picked, the decoration keyboard,
  the range toolbox on each of its six tabs, the keyboard panel. It was run twice on the old code
  (`git stash`) to check the pictures are repeatable (identical hashes), then on the new code:
  **12 of 12 identical byte for byte**.
- `check:flow` (80, with the transcription) and every other `check:*` passed.

# 3. Story 2.2: the defaults

## 3.1 What the old page really did

Before writing the backend rule, one finding: the old page always built the ladder from **the
biggest pile of gaps of the saved hand**, chosen in the browser. The saved `anchorMs` was only
printed ("Last saved as corchea = 217 ms"); only the **name** of the pile (`anchorFigure`) and the
hand were the reader's. Measured on Superestrella: the saved `anchorMs` 217.1 is exactly the highest
pile's median. So the new rule keeps the behaviour of every saved sheet and changes one thing: on a
sheet nobody has named, the name is **negra** without a click.

## 3.2 The backend

- `matrix/ladder.py`: `DEFAULT_ANCHOR_FIGURE = negra`, `default_anchor(peaks)`: the pile with the
  most gaps, the first in the list on a tie, `None` when there are none. The module note says D-09
  changed.
- `GET /time/{uuid}/default-reading?hand=&frameMs=`: `{hand, anchorFigure, anchorMs, centreMs,
  attackCount, gapCount, endSeconds}`. When the hand asked for has **no pile** (not only no gaps:
  the shuffle stub's left hand has one gap, too few for a pile) both hands are measured and `hand`
  says `both`. `anchorMs` is `null` for a piece with no gaps.
- `SavedRhythm` gained `title`, `subtitle`, `artist` (optional, at most 200 characters), for the
  Title tab. Phase 3 moves the reading into `sheet.json`.
- The Sheet step's status reasons: "Not saved yet." (missing) and "The notes or the hands changed
  since this sheet was saved." (stale); the old texts named the plot and the button.
- Tests: 6 for the route (`test_time_score_api.py`), 3 for `default_anchor`
  (`test_matrix_peaks.py`), 3 for the title fields (`test_saved_rhythm.py`).
- The note under D-09 in
  [`decisions.md`](../01-mvp/03-time-based-concept/decisions.md), and its index line.

## 3.3 The frontend

`anchorFigure` (the main figure) and the three title lines are now fields of `SheetEdits`, so each
change is one undo step. The page asks for the saved reading and the default reading at the same
time and draws when both have answered (`rhythmChecked`), so the defaults never land on a reader's
own key. The key and the brackets are taken from the first build's reports (`onKeySuggestion`,
`onOttavaSuggestion`) as the baseline, not as steps: the key first, then the brackets of the **next**
build, so they are measured in the new key (`keyMoving`). **Remove all** returns the sheet to a first
write, so it takes the defaults again.

Measured on a copy of Superestrella without its saved sheet (`fresh-check.mjs`): first notehead
857 ms after the page opened, no button; key **B major** (5 sharps, the fewest accidentals), figure
**negra**, anchor 217.1 ms, hand right, **15** octave brackets; undo disabled on arrival; the dot on
Save; after Save the step is `ready` and the dot is gone; Corchea in Figures asks for the sheet
again and is one step (*Undo: Main figure*); undo back to the saved state takes the dot away.

The negra default can be wrong by a factor of two. On Superestrella it reads `negra = 217 ms ·
≈276 BPM`; its reader had chosen corchea (138 BPM). That is D-09's own warning (statistics cannot
tell the two apart) and the reason the Figures tab is one press (screenshots 03, 04).

# 4. Story 2.3: the page

## 4.1 What was removed, and where it went

| Before | Now |
|---|---|
| Card *Add a passage* (with its warning) | **Record a passage** on the bar opens the same `ComposePassagePanel` in a toolbox, with a one-line warning. An empty piece shows "Nothing to write yet." with **Record a passage** |
| Card *How this piece was played* (hand select, counts, the plot) | Gone. The hand is the saved one (or right, falling back to both) |
| Card *Name it* (figure select, **Write the sheet**, undo and redo, "one step longer / shorter") | The figure is automatic; **Figures** tab; undo and redo on the bar; **Write the sheet** only in the stale banner |
| Card *Does the piece change speed?* | **Speed** tab of the range toolbox, as a percentage of the speed of the piece (ms no longer on screen; still stored as ms) |
| The row under the player: key, two sliders with captions, the key hint, five chips | **Key** and **Layout** tabs; the key hint is a button in **Key**; *Show piano* in `⋯` |
| The player's two buttons and paragraph | `ScorePlayer compact`: the scrub bar only; play on the bar and Space |
| Rows under the sheet (save button and text, hidden notes, trills, mark size) | Save on the bar; *Bring back N notes* and *Find trills* in `⋯` (the trills in a small panel); mark size in **Layout** |
| *Remove all* armed by two presses | A `ConfirmDialog` |
| Frame numbers in toolbox subtitles (`f160 – f184`) | Times (`00:06.40 – 00:07.40`); plan 7.5 keeps `f101` only for the frame numbers of the sheet and lyrics |

## 4.2 The bar and the toolboxes

The floating bar: play or pause, undo and redo (tooltips name the step), the sheet toolbox, Record,
Print, **Save** (a dot when unsaved, "Saved" for a moment after), and `⋯`. Save stays visible rather
than inside `⋯` as plan section 11.2 wrote; the plan now says so (a save hidden in a menu is the
"hidden action" of the 09 guidelines). Unsaved is `edits.state !== cleanEdits` (identity: every edit
makes a new value and undo restores the old one).

The note toolbox: the figures as icon actions, finger numbers, **Right / Left** as a `Segmented`,
beam and even spacing icons, the three marks as icons (🎹, A−, *tr*), delete. The range toolbox:
**Both / Right / Left**, the tabs as a grid of chips with a dot when the stretch carries the setting,
✓ and 🗑 icon actions, no captions. Tooltips carry what the captions said.

A refused hand move and a failed undo are a message at the bottom of the window instead of an alert
under the sheet (which could be pages away).

## 4.3 The line wrap (Task 2.3.3)

The prompt said the line wrap may have stopped working. Measured with `wrap-check.mjs` (window
resized while the sheet is open): it wrapped again when the window got **wider**, never when it got
**narrower**. At 900 px and 390 px the lines kept 1,688 px and were cut off at the right (scrollable
inside the sheet's box, so the page showed no scroll bar).

The cause was in `TimeScoreView`, not in `vexflow-v2`: the box the renderer watches
(`observeResize`) sits in a stage drawn as `inline-block`, which takes the width of its content. It
grew with the window (`minWidth: 100%`) but never shrank below the drawing inside it, so the
renderer's `ResizeObserver` never saw the window shrink. The stage is now a `block` at normal zoom
and an `inline-block` only while magnified (where the layout must keep its width). After the fix:
1440 → 900 → 1800 → 390 → 1440 px, every notehead inside the window each time, no page error.
`check:flow`'s hand move on a zoomed sheet still passes. No change in `vexflow-v2`.

## 4.4 Timings (Task 2.3.4)

**The first piano sheet** (`npm run time:flow`, the three pieces of implementation 08 Phase 9, all
temporary). In 08 it was two steps (tab to **Write the sheet** ready, then the button to the sheet);
now it is the tab press to the first notehead:

| Piece | Implementation 08 | Now |
|---|---:|---:|
| Superestrella (upload, 3:09) | 0.14 + 0.62 = 0.76 s | **0.59 s** |
| The Winner Takes It All (library copy, 5:56) | 0.17 + 0.99 = 1.16 s | **0.90 s** |
| Comptine (new YouTube URL, 2:21) | 0.14 + 0.55 = 0.69 s | **0.46 s** |

Faster because the sheet no longer waits for a ladder-preview request beside the score request. The
whole walks: 32.2 s, 58.7 s, 30.7 s (08: 33.0, 60.0, 31.1).

**A hand move** (`npm run bench:sheet`, median of 6 moves, press to the next frame on screen):

| Piece | Implementation 08 | Now |
|---|---:|---:|
| Elefants (3:53) | 252 ms | **215 ms** |
| Superestrella tutorial (3:10) | 272 ms | **267 ms** |
| The Other Side (4:33, 4,295 notes) | 599 ms | **469 ms** |

Redraws per move are unchanged (2, 4, 2). Both targets ("within 10 % of implementation 08") hold.

**`time:flow` had been broken since Phase 1** (which updated its paths but did not run it): it
waited for the texts "Transcribed in" and "Predicted in", the tab "4. Hands" and a button "Play",
all gone or renamed. Each wait was 10 minutes. Fixed to `data-predicted`, "Hands", "Play from the
playhead"; the backend's own transcription time is no longer on screen, so its column is empty.
`check:flow`, `bench:sheet` and `time:flow` no longer press **Write the sheet** except on a stale
sheet, and find the hand buttons by name.

## 4.5 The 13 checks of the 09 guidelines

Screenshots in [`screenshots/phase-2/`](screenshots/phase-2/), 1440 × 900 unless named, all on
temporary copies of Superestrella (made from `b99bc3ae` without its history, staging and video,
deleted at the end). After every script, `aitu-backend/data/audio/` has its 39 pieces.

| # | Check | Result |
|---|---|---|
| 1 | One sentence | Read and edit the piano sheet of this project |
| 2 | Every sentence a label, control or fact | Deleted: the player's paragraph, every slider caption, the key caption, the "Click a notehead…" line, the lyrics helper text, the spacing captions, "Nothing saved yet…", "Last saved as…". Kept: the stale banner, the re-record and Record warnings (undo cannot reach them), the Remove all consequence |
| 3 | Words above the first content | The title line and the times of the scrub bar (shot 02) |
| 4 | Very wide (2,400 px, shot 26) | The sheet uses the width; the bar stays at the bottom right with the music |
| 5 | Narrow (390 px, shots 22 to 25) | 0 px of horizontal overflow; the sheet wraps to 294 px; the bar wraps into two rows; the toolboxes fit the window |
| 6 | Longest, shortest, none | A long project name truncates with the full name on hover; no subtitle and no artist draw nothing; an empty piece shows "Nothing to write yet." |
| 7 | Buttons say what happens | "Save", "Write the sheet", "Remove all", "Record a passage", "Add the words", "Use B major (5 fewer accidentals)"; icons named in tooltips |
| 8 | Helper lines | None left |
| 9 | Loading, empty, partial, error | A spinner in the place of the sheet; the empty piece; the stale banner (shots 20, 21); a refused save in a message that stays |
| 10 | Tab through it | The bar's buttons and the toolboxes are buttons with names; the tabs are `role=tab` / toggle buttons |
| 11 | Internal names | Gone: `ms`, "column", "pile", "gap". Left: the ladder line printed on the sheet (`corchea = 217 ms · ≈138 BPM`), see section 6 |
| 12 | First-time user | "Main figure" needs the icons to be understood; acceptable for a musician, and Phase 7's Transpose replaces it |
| 13 | Anti-patterns | No lecture, no caveat wall, no far-away control (the refused move message moved next to the bar), no hidden action (Save on the bar) |

| Shot | Page |
|---|---|
| 01, 02 | The Sheet step before (Phase 1) and after |
| 03 to 05 | A first write (the defaults, the dot); Corchea in Figures; the Title tab |
| 06 to 08 | Sheet toolbox: Key, Figures, Layout |
| 09, 10 | Note toolbox; a tooltip |
| 11 to 14 | Range toolbox: Key, Octave, Speed, Lyrics |
| 15, 16 | The `⋯` menu; the Remove all confirmation |
| 17 to 19 | The keyboard; Trills; Record a passage |
| 20, 21 | A stale sheet, before and after Write the sheet |
| 22 to 25 | 390 px: the page, the note toolbox, the range toolbox, Layout |
| 26 | 2,400 px |
| 27 | The window resized to 900 px: the lines wrapped again |

# 5. Documentation

- [`../../frontend/annotations.md`](../../frontend/annotations.md) rewritten (the page, the defaults,
  the selections, undo, saving) and split: [`annotations-notes.md`](../../frontend/annotations-notes.md),
  [`annotations-stretches.md`](../../frontend/annotations-stretches.md),
  [`annotations-sheet.md`](../../frontend/annotations-sheet.md). The longest is 129 lines.
- [`components.md`](../../../documentation/services/frontend/components.md) sections 2.4 and 3,
  [`endpoints.md`](../../../documentation/services/backend/endpoints.md) (the new route, the title
  fields), [`rhythm-and-annotations.md`](../../../documentation/services/backend/rhythm-and-annotations.md),
  `grid-notation.md` (`SheetPage`), `flow-page.md`, `frontend/README.md`, `pieces-and-revisions.md`,
  `00-project-complete-overview.md`, `00-index.md`, `aitu-frontend/README.md`, the note under D-09.
- The plan: section 11.2 (the bar as built), 11.4 (Title stored in `rhythm.json`; the Figures tab
  until Phase 7), 11.6 (the Speed tab).

# 6. Open points

- **The ladder line printed on the sheet** (`corchea = 217 ms · ≈138 BPM`, on screen and in the
  PDF) still shows `ms`, which plan section 7.5 wants off the screen. It is part of the drawn music
  (a tempo mark), so changing it is a product choice: raised in the walkthrough.
- **A leave dialog on the Sheet step** is now possible (the page knows it is unsaved) and is not
  wired; the other steps have one. Small; a later UI phase can take it.
- `components/time/PeakPlot.tsx` stays only for the compose and re-record panels, which Phases 8 and
  9 replace.

# 7. Learnings for later phases

- **Run every script a phase touches, timings included.** `time:flow` was updated in Phase 1 and
  broken until now; its waits are 10 minutes each, so a stale selector looks like a hang.
- **Pixel-identical screenshots are a cheap proof of a refactor.** Playwright pictures of the same
  temporary copy are repeatable byte for byte; hash them before and after (`git stash` for before).
- **A click in the middle of a frame group may land on a glyph.** Scripts that open the range
  toolbox should click near the top of the group (`y + 4`).
- **An `inline-block` around a resize-observed box only grows.** Anything that wraps to its
  container must sit in a box whose width comes from its parent, not from its content.
- **Defaults taken from the renderer's reports** must wait for the saved reading, and the second
  default (brackets) must wait for the build that follows the first (key).
