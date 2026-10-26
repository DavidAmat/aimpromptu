# 03: Phase 8 report: the other screens and the sheet toolbox

Plan: [`03-plan.md`](03-plan.md) section 7, Phase 8. Checklist: [`03-checklist.md`](03-checklist.md). Branch
`feat/migrate-new-logic` (level with `master` at the start: nothing to merge). Written 2026-10-26 on the Ubuntu
machine. **In progress**: the study and 8A are built; the user asked for a keyboard in the note toolbox (built
2026-10-26, section 8.1) for free lyrics blocks with a lyrics toolbox (section 8.2) and for a denser PDF (section 8.3)
before checking 8A in the browser; 8B is next.

# 1. Summary

| Task | Result |
|---|---|
| 8.1 Study and inventory | Section 2: what the old sheet still does outside the two toolboxes, in two groups (the Sheet step's own tools; the screens built on a marked stretch), with its use in the database. Four questions (section 3), all answered. The phase is built in two halves, each checked in the browser |
| 8.2 Lyrics in the format and in the engine | `lyric` lines in `sheet.f1`, a text primitive of the engine (`<text data-lyric>`), picked, dragged and lit on the page (section 4) |
| 8.3, half 8A | The sheet toolbox (Title, Key, Transpose notes and figures with their preview, Lyrics, View), the keyboard panel, Print to PDF from the new engine, the lyrics in Play mode (sections 4 and 5). Built; the user's check is next |
| 8.3, 8A+ | The user's request: a keyboard in the note toolbox for the picked column (section 8.1). Built, frontend only; `check:frames-toolbox` covers it |
| 8.3, 8A++ | The user's second request: lyrics as free blocks, a lyrics toolbox (section 8.2). Not started |
| 8.3, half 8B | Not started: `sheet.f1` through every change of a part's length, copy and paste, Start a new part, the read-only stretch actions, the requests review, Recording in Sheet, the blank sheet; then the switch removed (section 8) |

# 2. The study (task 8.1)

## 2.1 What the old sheet still does

Read only, 2026-10-26: `SheetPage.tsx` (3,302 lines), `SheetFloatingBar.tsx`, `SheetToolbox.tsx`, `TransposeTab.tsx`,
`TransposeDialog.tsx`, `LyricsTab.tsx`, `lyricsPieces.ts`, `PianoToolboxes.tsx`, `ScorePdfDialog.tsx`, `print/`,
`PassagePage.tsx`, `ComposePage.tsx`, `RequestSheet.tsx`, `Conversation.tsx`, `PlayPage.tsx`, `SheetTab.tsx`, and the
backend's `editing/` (`paste.py`, `passages.py`, `parts.py`, `compose.py`, `marks.py`) and `api/time_score.py`.

**The Sheet step's own tools** (built in 8A):

| Tool (old sheet) | Where | New sheet |
|---|---|---|
| Sheet toolbox: Title (title, subtitle, artist) | `SheetToolbox.tsx`, `sheet.json` | Kept: `title` lines of `sheet.f1` |
| Sheet toolbox: Key of the piece, with the fewest-signs hint | same | Kept: `piece-key`; the hint from `GET /sheet/{uuid}/stretch` over the whole piece |
| Transpose → Notes, with Preview | `TransposeTab.tsx`, `POST /time/{uuid}/transpose`, `TransposeDialog.tsx` (draws with vexflow-v2) | Kept on the edit model: `POST /sheet/{uuid}/transpose` (the stored sheet moves with the notes); the preview drawn by the backend |
| Transpose → Figures, with Preview | same, `figuresFrom` and the overrides of `sheet.json` | Kept: `figures` (the reference figure renamed, the spacing's figure kept) |
| Lyrics: paste, pool, pieces on frames, edit toolbar | `LyricsTab.tsx`, `lyricsPieces.ts`, `PUT /time/{uuid}/lyrics` (pool in `project.json`), `sheet.json` `lyrics` | Kept as it was (the user's answer): the tab and its helpers reused; the pieces are `lyric` lines of `sheet.f1` |
| Layout: space between notes, space between lines, size of marks, zoom, frame numbers, hide decorative notes, group under 8va | `SheetToolbox.tsx` | **View**: Zoom and Space between lines; the rest dropped (the user's answer) |
| The keyboard panel | `PianoToolboxes.tsx`, `PUT /time/{uuid}/notes` | Kept: `POST /sheet/{uuid}/add`, and a lit key is the Phase 7 removal |
| Find trills | `SheetPage.tsx`, `GET /time/{uuid}/trills` | Dropped (the user's answer) |
| Remove all, Bring back N notes taken off | `SheetFloatingBar.tsx` | Dropped (the user's answer) |
| Print to PDF | `ScorePdfDialog.tsx` (vexflow-v2's `renderPages`), `print/` (the app's own PDF writer) | Kept: the backend lays out the pages, the same writer writes them |
| Play mode: lyrics shown with their frames | `PlayPage.tsx` over `SheetPage` | Kept: lit in the drawing |
| The blank sheet of From scratch (Record a passage, Paste) | `SheetPage.tsx` | 8B |

**The screens of a stretch** (8B): copy (range and note toolboxes, ⌘C, **Copy this stretch** on a read-only sheet),
paste at the cursor or over a marked stretch (`POST /time/{uuid}/paste`, undone by a history version), **Start a
new part here** (`projects.splitPart`), **Add to a playlist** (a version of My library), **Add this stretch** (From
other projects), **Comment on this stretch** and the excerpts of the Conversation (the requests review), Recording in
Sheet (the Current, the Proposal with its own toolbox, the window over it, the speed, Promote carrying the
Proposal's sheet), **Record a passage at the end**.

## 2.2 The finding that shapes 8B

The old sheet moves its marks with every change of a part's length (`editing/marks.py`: `shift`, `cut_out`,
`extract`, `put_in`, used by paste, promotion, split, join and From other projects). None of these writes touches
`sheet.f1`: after them the stored sheet is laid again on the notes by column and key (`build.reapply`), so every
decision after the change (the AI's hands aside, which are in `notes.pmn`) is lost, and the stored clef and armadura
changes stay at the old frames. 8B starts with the same four moves for an F1 frames sheet.

## 2.3 The use in the database (read only, 2026-10-26)

46 `sheet.json` outside the histories (projects, library versions, public and request parts):

| Field | Sheets | Note |
|---|---|---|
| `lyrics` (placed pieces) | 4 (2 songs, each with its library version) | 3 pieces in all |
| lyrics pasted (`project.json`) | 4 projects | 2 more songs have words but no piece placed |
| `title`, `subtitle`, `artist` | 0 | |
| `figuresFrom` (Transpose figures) | 0 | `anchorFigure` is `corchea` on 7 |
| `lineSpacing` changed | 3 (60 instead of 72) | |
| `noteSpacing` changed | 1 | |
| `dropDecorative` | 3 | |
| `annotationScale` changed | 0 | |

The database also holds 1 request (5 comments), 1 songs playlist (2 songs) and 1 project of two parts.

# 3. The user's answers (2026-10-26)

1. **Layout**: keep Zoom and Space between lines; drop space between notes, size of marks, frame numbers, hide
   decorative notes and group under 8va (the recommendation).
2. **Lyrics**: drawn above the upper staff, as today, with the whole editor (the pool, dragging onto frames, split,
   merge, the words, size and lift). The recommendation was between the staves with no size or lift; the user kept
   the old place. A press on a piece picks it; anywhere else in the strip a press marks a stretch.
3. **A take's sheet** (Recording in Sheet): the algorithm's, with Enhance with AI as a button; Promote carries its
   reading into the song (the recommendation).
4. **The `⋯` menu**: drop Find trills, Remove all and Bring back N notes taken off (the recommendation).

The agent's choices, written in the plan: Transpose figures renames the figures and the spacing keeps its figure
(D-18); the old marks of `sheet.json` stay stored when the switch goes, Phase 9 maps them; the phase is built in two
halves.

# 4. The backend (8A)

## 4.1 The core (`aitu_backend.sheet`)

- `Sheet.titles`, `Sheet.lyrics` (`Lyric`: start, end, text, size, lift), `Sheet.space_ms`, `Sheet.line_space`;
  `carry_extras(source, target)`. Lyric sizes are in staff spaces: 1.4 by default, 0.8 to 4.2 (the old 12 px, 7 to
  36 px, at about 8.5 px a staff space).
- F1, frames view: `spaceMs=`, `lineSpace=` in the header; `title`, `subtitle`, `artist` and `lyric f<a> f<b> "words"
  size= lift=` lines after the clefs line. Written only when set: every older sheet writes byte for byte as before
  (the golden files and the round trips of Phases 2 to 7 pass unchanged). LLM prompts build new sheets, so these
  lines never reach the AI.
- The engine: the spacing reads `space_ms` before `quarter_ms`; `line_space` is the gap between systems; a lyrics
  piece is a text primitive above the upper staff of the line that holds its first column, all pieces of a line on
  one baseline 0.8 staff spaces above the ink under them (at most 2 above the top line), `lift` raising one further;
  the words take no width, so no column moves. `render_pages` draws once and deals whole lines onto pages.
- `splice` (a stretch the AI wrote again) carries the extras.

## 4.2 `part_sheet`

- `reading.py`: `set_titles`, `set_piece_key`, `set_line_space` (2 to 16 staff spaces), `set_lyrics` (the whole
  list; refused when two pieces share a frame; size clamped, lift -4 to 20), `rename_figures` (`quarter_ms` x
  2^steps, `space_ms` set once and cleared when back; figures set by hand moved, or given back to the rule when
  nothing is left to become), `moved_key`, `transpose_sheet`, `far_notes`; five new actions of `plan`.
- `edits.py`: `edit_reading` split so `preview_reading` shares it; a rename sets the record's `quarter_ms` and
  `reference = "user"`. `transpose_notes` (one step with `_Step.keys`; preview), `add_note` (one step), `note_ends`.
- `build.py`: `reapply` carries the extras; `sheet_settings`, answered by `draw`.
- `job.py`: the AI run keeps the extras (its live sheet too) and a figure the user named (`write_frames(quarter_ms=)`,
  no reference request; the record keeps `reference: user`).
- `api/sheet.py`: `reading?preview=true`, `POST /transpose`, `POST /add`, `GET /pages`; each note's `end`.

# 5. The frontend (8A)

- `FramesSheetToolbox.tsx`: Title, Key, Transpose (the old `TransposeTab` reused; the frontend's figure ladder runs
  from the shortest figure, so its steps are turned to the backend's sign), Lyrics (the old `LyricsTab` reused), View.
- `useFramesLyrics.ts`: the pasted words and the pool saved as before; the pieces as the old tab's `LyricLine`s
  (size and lift converted at 12/1.4 px a staff space); every change one edit with a label from what changed
  ("Place a lyrics piece", "Move a lyrics piece", "Size of a lyrics piece", ...); landing and dropping a pool piece;
  Delete.
- `FramesSheetView.tsx`: lyrics picked (outline and grip), dragged (move to the frame under the left edge, lift
  in half staff spaces, the right edge pulled), pool pieces dropped, the frames of the pieces shaded (grey, green,
  red) while one is dragged; the sounding piece lit (bold, black), in Play mode the others faint while it plays.
  Lyric blocks are measured when the drawing goes in (the lint rule forbids refs read during render).
- `FramesSheetPage.tsx`: the floating bar has Print, the sheet toolbox and `⋯` (Show the keyboard); the title lines
  come from the sheet; the zoom is kept in this browser; a stretch marked while the Lyrics tab is open picks the
  pieces over it; the previews; the keyboard panel (the old `PianoToolbox`) from each note's `end`.
- `FramesPreviewDialog.tsx`, `FramesPdfDialog.tsx` (A4 or Letter, orientation, margins, extra space between lines,
  title, second line, page numbers; staff space 1.75 mm).
- `print/drawPage.ts`: `<use>` (with the referenced path's own transform), `<polygon>`, `S`/`T` curves, a new run per
  line of a `<text>`; `print/scorePdf.ts`: a `selector`, and no Bravura when no glyph is text.
- `lyricsPieces.ts` keeps its own copy of the three lyric sizes (it no longer imports vexflow-v2); `Piano.tsx` gives
  each key `data-key-row` for the checks.

# 6. Measurements

| What | Value |
|---|---|
| Drawing 7 Years with two lyrics pieces and a wider line space | 29 ms (the same as without) |
| The pages of 7 Years, A4 (staff 96 spaces, 5 pages) | 41 ms in the backend |
| The PDF of 7 Years, 5 A4 pages | 50 kB (the old sheet: about 450 kB, most of it Bravura) |
| Transpose figures, negra to corchea, on 7 Years | the reference figure 480 to 960 ms, the spacing's figure kept; 6 more grace notes (131 to 137) and new flags move the line breaks: 343 of 705 columns stay in place |

The last line is a limit of D-18 on the new sheet: the spacing stays, but the rules that read the figure names
(grace notes, flags, beams) change some notes' room, and a line break moves the columns after it.

# 7. Checks (8A)

| Check | Result |
|---|---|
| `tests/test_sheet_toolbox.py` (new, 8 tests) | The format round trip and older sheets unchanged; the engine's lyrics, widths kept with the spacing's figure and the line space; titles, armadura, line space with undo; lyrics placed, refused over another, kept through a hand move; Transpose figures (preview, widths, a new AI run keeps the name, back again); Transpose notes on an AI sheet (preview, the AI's beam groups and hands kept, undo exact); a note added and undone; the pages |
| `tests/test_sheet_reading.py` | `test_every_action_of_the_page_is_planned` now also plans the sheet's own actions |
| The sheet tests of Phases 1 to 7 and the golden files | pass unchanged |
| Backend, full run on the CPU | 1,378 tests, the 3 known failures (section 7.1) |
| `npx tsc -b`, `npx eslint` on the changed files | clean |
| `npm run check:frames-toolbox` (new) | all 22 passed (section 6 for the figures); with the chord keyboard (section 8.1), all 31 |
| `npm run check:frames-sheet`, `check:frames-edit`, `check:frames-tools` | all passed (`check:frames-edit` and `check:frames-tools` again after the chord keyboard) |
| `npm run check:play` | all passed; its lyrics step moved to the new sheet (lit and faint) |
| The drawings | the lyric above the staff, Play mode's lit lyric, and the PDF's first page rendered by poppler, zoomed in: the first PDF had broken clefs (the `s` curve), fixed in `drawPage.ts` |

## 7.1 The full backend run

In the image, on the CPU (another project holds the GPU): 1,378 tests; 3 failed, the same three as in Phase 7:
`test_the_worked_example_at_00_46_prints_three_equal_corcheas` (failing since Phase 0) and the two
`test_transcription_transkun.py` tests, which load a checkpoint saved on CUDA. Every other test passed (one skips
itself without a GPU).

# 8. The user's three requests, then 8B

## 8.1 The keyboard of the note toolbox (8A+, built 2026-10-26)

**The request (2026-10-26), before the check of 8A:** a small piano in the note toolbox. When notes are
picked (a single note or a chord), the toolbox shows a keyboard with the keys of the picked column lit in their
hand's colour; a dark key adds a note to that column (in the chord's hand, as long as the chord), a lit key takes
that note off; each press is one step of undo. The backend routes exist (`POST /sheet/{uuid}/add`, which today puts
a note at the onset of a drawn column, and `/remove`); each drawn note carries its `end` frame. Pieces to reuse:
`ui/MiniPiano.tsx` (the Transpose tab's keyboards: `role="slider"`, keys with `data-midi`) or `piano/Piano.tsx`
(the keyboard panel: `keyColours`, `onKeyPress`, `data-key-row`), `PianoToolbox`'s colours (`HAND_COLOUR`,
`HELD_COLOUR`), and the keyboard panel's `pressKey` in `FramesSheetPage.tsx`. Open points for the session's study:
what the keyboard shows when notes of several columns are picked, and whether a note added there should get the
chord's figure set by hand (`fix`).

**The answers, from the code and the old keyboard panel (no question to the user):**

- **Several columns picked: no keyboard.** The keyboard panel shows one moment (the cursor's column); a keyboard of
  two columns would light keys that do not sound together, and a press would not say which column it adds to.
- **Both hands of the column lit**, each in its colour (`HAND_COLOUR`, as the keyboard panel): the user sees the whole
  chord of that moment, and a key the other hand already plays is not added twice (the backend refuses it anyway).
  Notes still held from earlier columns are not lit: the keyboard is about the notes struck in this column.
- **The hand of a key added**: the hand of the notes picked; with both hands picked, the hand of the column's note
  nearest to the key (the right hand on a tie) (`readingTools.handForKey`).
- **No `fix` for the note added.** Measured with a scratch test on the stand-in part (the algorithm's sheet and the
  AI's): a note added to a beamed right-hand chord of corcheas came back with the chord's figure and beam group,
  because `assign_figures` gives one figure per chord and `assemble` keeps the chord in its group (the new note has
  no beam of its own in `build.reapply`, but its chord does). A chord with a figure set by hand keeps it for every
  note of the chord. The length sent is the longest note of that hand in the column (`end` minus the column, in 40 ms
  frames), so the note sounds as long as its chord.
- **The chord stays picked after each press** (`FramesSheetPage.repick`): the notes picked, plus the one added, minus
  the one taken off, found again in the answer; when the column moved by a frame or two (its first note was taken
  off: Phase 7's `reapply` case), the same keys there; when none of the picked notes is left, the notes of the same
  hands still in the column. The toolbox closes only when the column is empty.

**What was built (frontend only; the routes of 8A did not change):**

- `ui/MiniPiano.tsx`: the drawing is now `MiniKeys` (any keys lit in their own colours, `data-midi` and `data-lit` on
  each key, the octave number on each Do when asked); `MiniPiano` (the Transpose tab) draws with it and looks as
  before. `piano/keyPositions.keepKeyInView` scrolls a key into view (shared by both).
- `FramesNoteToolbox.tsx`: `ChordKeys` at the top of the toolbox (`data-chord-keys`, role `group`), scrolled to the
  chord when another column is picked; each key's tooltip says what a press does ("Sol 5: add it to the right hand",
  "Re 5, right hand: take it off"), or why it is locked.
- `FramesSheetPage.tsx`: `pressChordKey` (a lit key: `POST /sheet/{uuid}/remove`; a dark key: `POST
  /sheet/{uuid}/add` with the hand and the length), then `repick`.
- `readingTools.ts`: `midiOf`, `oneColumn`, `handForKey`.
- `check:frames-toolbox`: a right-hand beamed chord of two notes on the copy of 7 Years: both keys lit; a dark key
  adds Si 5 with the chord's figure (corchea) and beam group, one step "Add a note", the chord still picked with the
  new key lit; the lit key takes it off ("Take a note off the page"), the chord still picked; Undo twice; Shift-click
  on a note of another column hides the keyboard. The toolbox pictures were looked at zoomed: Re 5 and La# 5 lit,
  then Si 5 too, "One chord of 3".

## 8.2 Lyrics as free blocks and a lyrics toolbox (8A++)

**The user's second request (2026-10-26):** lyrics pieces as free blocks, and a lyrics toolbox. Today a piece's width
follows its frames, so narrowing it to wrap the words onto two or three lines is not possible, and the strip above
the staves lights up and marks a stretch while the user works on a piece. Wanted: a click highlights the block; the
block is moved anywhere and resized freely (narrower, wider, taller, shorter), the words wrap inside it, and none of
this touches the frames; no stretch strip while a piece is picked or dragged; a lyrics toolbox beside the picked
pieces with the size, several fonts, normal, bold and italic, and the old toolbar's actions. What exists: the `lyric`
lines (`start`, `end`, `text`, `size`, `lift`; `sheet/sheet/f1.py`, `data.Lyric`), the engine's text primitive
(`engrave/frames.py` `_lyrics`, `svg.py` kind `"t"`: one baseline per line of music, no wrapping, the backend has no
text metrics), the page's drag code (`FramesSheetView.tsx`, `LyricDrag`; the strip in `stripAt`, `pull`, `press`),
the old tab (`LyricsTab.tsx`) and its adapter (`useFramesLyrics.ts`), and the PDF writer, which maps a serif font to
Times, other text to Helvetica (`print/drawPage.ts` `encode`; Courier is a base font too). Open points for the
study: how a block stays with its music when the lines re-wrap (anchored to its first frame with a free offset `dx`,
`dy` and a `width`?), where the words wrap (in the page, which measures text, sending the lines; or in the engine
with a table of character widths), which font families, and how Play mode lights a block that no longer spans its
frames.

## 8.3 A denser PDF (8A+++)

The user's third request (2026-10-26). Even with the page's Zoom at its smallest, the PDF is very large, there is no
control of the size, and the space between lines cannot go below the slider's minimum, so the pages carry much white
space. A printed piano score has about five lines (two staves each) a page: that is the default to reach.

What exists: `FramesPdfDialog.tsx` asks `GET /sheet/{uuid}/pages` for a staff width of `(paper - margins) / 1.75 mm
- 8` staff spaces and a gap of the sheet's own line space (5 staff spaces, or the user's View setting) plus the
dialog's extra (0 to 8); the page's Zoom is not used. On the engine's side (`engrave/frames.py`), `render_pages`
deals whole lines; each line's height is its ink (`ymin` to `ymax`: ledger lines, 8va, lyrics) plus the gap between
the two staves (`Options.min_staff_gap` 6, more when the ink between them asks), and `draw` puts `gap` between two
lines' ink. Measured once on 7 Years (A4 portrait, margins 14 and 16 mm): 5 pages, 6 lines on page one under the
title.

Points for the study: a "size of the music" control (a printed staff of about 5.5 to 8 mm; printed piano editions
use about 6.5 to 7 mm), a smaller least space between lines (also below the sheet's own), perhaps a tighter gap
between the two staves on paper, and defaults that give about five lines on an A4 page on the 10 viewer songs.
Measure lines per page before and after, and show the user the pages.

## 8.4 Then 8B

1. `sheet.f1` through every change of a part's length: an F1 version of `editing/marks.py` (`shift`, `cut_out`,
   `extract`, `put_in`, the key and clef in force at the edges), used by paste, promotion, split, join, From other
   projects and a comment's excerpt.
2. Copy and paste on the new sheet (the range and note toolboxes, ⌘C, ⌘V, the floating bar), as a step of the new
   log whose undo restores a history version, as the old page did.
3. **Start a new part here**; the read-only stretch actions (Copy this stretch, Add to a playlist, Add this stretch,
   Comment on this stretch) in a small Frames panel; the requests review (Proposed / Now, the excerpts).
4. Recording in Sheet: the Current and the Proposal on the new sheet, the window over the Proposal, the speed, the
   Proposal's own toolbox and undo, Promote carrying its reading into the song; the blank sheet (Record a passage,
   Paste).
5. The switch removed (`SheetPage` draws only the new sheet); the old sheet's browser checks moved to the new hooks.

# 9. Documentation

- `aitu-backend/src/aitu_backend/sheet/README.md` section 15.
- `context/frontend/annotations.md` ("The new sheet"), `annotations-sheet.md`, `play-mode.md`, `printing.md`,
  `rendering.md`.
- `documentation/services/backend/endpoints.md` (routes table, section 4.1),
  `documentation/services/frontend/score-pdf.md`.
- [`03-plan.md`](03-plan.md) Phase 8, sections 8 and 11; [`03-checklist.md`](03-checklist.md).
