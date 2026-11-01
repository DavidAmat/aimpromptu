# The Sheet page: the frontend shell

The page that shows a sheet. It is the Sheet step of a project, and every other place a sheet is drawn: a version of
My library, Play mode, the two sheets of a passage, From other projects and the requests review. It holds the header,
the buttons, the floating toolbox, the zoom, the cursor and the recording, and the AI's marks on the sheet. The
drawing itself comes from the backend ([rendering.md](rendering.md), [sheet-drawing.md](../../documentation/services/backend/sheet-drawing.md)).

The page is one component, `FramesSheetPage`. The other files are its helpers: the view that lays the cursor and the
marks over the drawing, the hook that loads the sheet, and the small modules of the Sheet step.

## 1. Where the page is drawn

`SheetTab.tsx` gives the Sheet step to `SheetPage.tsx`. `SheetPage.tsx` keeps only the types of the step and draws
`FramesSheetPage`. Every other screen gives the same page a different `SheetStep`:

| Place | How the step reads | What the page then does |
|---|---|---|
| The Sheet step | the default: `projectId` is set | every tool; the info button; the floating toolbox |
| A version of My library | `readOnly` (the project page's read only state); `enhanceInCopy` | no toolbox and no edit; **Enhance with AI** opens the edit copy |
| Play mode | `play` (a `PlayView`) | the sheet alone: no header, no bar, no toolbox; the cursor kept in the middle |
| The page of a passage | `passage.role` is `current` or `proposal` | the Current is read only, with no bar; the Proposal has every tool and its own bar, and a window over the take |
| Compose (a playlist's stretch, the sources of From other projects) | `readOnly`; `stretchAction` (**Add this stretch**) | a marked stretch goes to the screen's own action |
| The requests review | `readOnly`; `stretchAction` (**Comment on this stretch**) | a marked stretch becomes the stretch the request talks about |

The page knows the place from the step only. A new screen that draws a sheet passes a `SheetStep` and gets the same page.

## 2. The header

The header is the top of the window. It sticks there while the sheet scrolls. It is drawn unless the page is in Play
mode, is a passage's page, or has no notes yet.

- The title: the sheet's title, else the step's label, else **Untitled**. Below it, the subtitle and the artist, with a
  dot between them, when the song has them.
- The AI mark beside the title (`components/piece/AiMark.tsx`). Green, with the tooltip **Enhanced with AI**, once the
  AI wrote the sheet, for good. Faint grey, with **Not enhanced with AI yet**, when it could and has not.
- The info button, shown when the step has a `projectId`. It opens the song's metadata. It is not a tool of the sheet
  (`data-testid="sheet-info"`; see [folders-and-metadata.md](folders-and-metadata.md)).
- The buttons of the sheet, the same list the floating toolbox shows (section 4), with test hooks that start with
  `header-`.
- One more button that hides or shows the floating toolbox (`header-floating-toggle`).

## 3. The empty sheet

A part with no notes shows **Nothing to write yet.** and, when the user can change it, two buttons: **Record a
passage** and, when a passage was copied, **Paste the copied passage**. The header and the floating toolbox are not
drawn. The player is not drawn either.

## 4. The buttons

The buttons come from one list, `sheetButtons`. It is drawn twice: in the floating toolbox (tooltips above) and in
the header (tooltips below). Which buttons a page shows depends on its place (section 1).

| Button | Shown | Key | What it does |
|---|---|---|---|
| **Play** / **Pause** | always | Space | starts and stops the recording |
| the passage's own actions | a Proposal | | the actions of the take (the passage's bar) |
| **Record a passage at the end** | not read only, not a passage | | opens a passage that starts after the last note |
| **Paste** | not read only, not a passage | ⌘V | puts the copied passage in at the cursor or over the marked stretch |
| **Print to PDF** | not a passage | | opens the PDF dialog (`FramesPdfDialog.tsx`) |
| **Undo** and **Redo** | not read only | ⌘Z, ⇧⌘Z | walk the part's steps |
| **Sheet toolbox** | not read only | | opens or closes the sheet toolbox |
| `⋯` **More sheet actions** | not read only | | **Show the keyboard** or **Hide the keyboard**; **History of AI runs** when the AI can run |
| **Enhance with AI** | when the AI can run here and nothing runs | | opens the Enhance with AI dialog; once the sheet is enhanced it reads **Enhance it again with AI** |

**Enhance with AI** opens one dialog. It opens on the **A stretch** tab when notes are picked or a stretch is marked,
and on **The whole song** tab otherwise. The dialog's tabs are in [annotations.md](annotations.md) and the AI pages
of [`context/ai/`](../ai/README.md). The page starts no AI run by itself: a run starts only from this button (the
user's decision of 2026-10-30).

## 5. The floating toolbox

The floating toolbox is a row of the same buttons (`ui/FloatingBar.tsx`). It is drawn at the bottom right of the
window at first, is kept on screen, and is dragged by its grip. It sits under the toolboxes (z-index 1200), so a panel
the user works in is never behind it.

- **Hide** puts it away. A small round button with an eye then stands where its hide button was, and the header's
  button does the same. The hidden state is kept in this browser (`aitu.framesSheet.floatingHidden`).
- It is not drawn in Play mode, on the Current of a passage, while the sheet is loading, or when it is empty.

## 6. Zoom

- ⌘ and the wheel, or a trackpad pinch (the wheel with Control), over the sheet zoom it. The first events of a
  gesture scale the drawing at once, from the pointer, with a CSS scale; the zoom grows or shrinks by at most a
  quarter a wheel event.
- When the wheel stops for 220 ms (`WHEEL_PAUSE_MS`), the page asks the backend for the sheet again at the width the
  new zoom gives. The line under the pointer is kept under it when the new drawing comes.
- The width asked is the window's width in staff spaces at the zoom: the pixels divided by 8.5 px a space and by the
  zoom, less 8 spaces of margin. It is rounded to steps of 4 spaces and kept between 60 and 320. A wheel that does not change the width draws nothing again.
- The zoom runs from 70 % to 200 % (`MIN_ZOOM`, `MAX_ZOOM`). **View → Zoom** in the sheet toolbox sets the same
  value. The zoom is kept in this browser (`aitu.framesSheet.zoom`). It is how the page is looked at, not part of the
  sheet.

## 7. The sheet's state

`useFramesSheet.ts` holds the sheet of the part as the page sees it. There is no **Save** button: every change is
written at once, as one step of undo kept by the backend.

- It reads `GET /sheet/{uuid}` for the page's width, and again after each change.
- While the AI writes, the backend sends a message on the job's stream each time the sheet changes. Each one asks for
  the sheet again. Messages closer than 250 ms are read as one.
- An edit is one request. Its answer is the sheet, drawn again in place of the one on the page. Further edits wait
  until it is back.
- While the AI writes, the sheet cannot be changed: the buttons that would change it are disabled, and their
  tooltip says **The AI is enhancing this sheet**. A sheet the user cannot change at all says **This sheet cannot be
  changed here**.
- A paste, an undo or a redo can change the audio too. The player then loads it under a new address (the audio
  revision). The cursor goes back to the start of the passage, or to where it was.

## 8. The cursor and the recording

- The recording plays in `ScorePlayer.tsx` (`compact`: the scrub bar only). The page keeps the player's time and whether
  it plays. The cursor is placed by time, not by column: `geometry.ts` (`placeAt`) reads the column the time falls in.
- A frame is 40 ms. The cursor's line is drawn between two columns of the drawing.
- While it plays, the notes the cursor reaches are lit: the noteheads of its column, and a decoration note only from
  its own onset (`headsByColumn`, `laterOnsets`). A lyrics piece lights while its frames sound.
- The cursor's line is kept in view while the recording plays (`follow`). In Play mode it is kept in the middle of the
  window (`centre`).
- A click on the sheet moves the recording there. The cursor can also be dragged and dropped, across lines: the
  pointer shows a hand; the page scrolls when the pointer is near the window's top or bottom; the recording moves to
  the cursor when it is let go, and plays on if it played. A press that does not move is a click.
- Space plays and stops. The player takes Space only where the page sets `keys`: not in Play mode, and not on a
  passage's Current, where another player is on the page.

## 9. What the sheet draws over itself

`FramesSheetView.tsx` draws the backend's SVG as it is, scaled to the page, and an overlay in the same units (staff
spaces). The overlay holds:

- **The veil**: a pale band over the staves of a segment the AI is writing (the breathing animation). A run of one hand
  veils only its staff.
- **The reveal**: a segment that comes back is drawn column by column, in about 1.8 s, over blank staves.
- **The batches** of a run: while the Enhance with AI dialog or the run panel is open, each batch is a coloured band
  over the staff it rewrites (`batches.ts`).
- **The picked notes**: lavender (`data-selected`). A click on a notehead picks it. ⌘ or Shift adds it. A box dragged
  across the staves picks the notes in it.
- **The marked stretch**: a band over the staves in scope, and a strip above the upper staff of each line, reaching
  3.5 staff spaces up, where the stretch is marked by a drag.
- **The lyrics pieces**: each block is picked, moved, widened, scaled or has its frames moved on the sheet (Phase 8;
  see [annotations-sheet.md](annotations-sheet.md)).
- **The window** over a take, in a passage's Proposal: a blue frame with a grip. The grip moves it.

The frame numbers on the sheet come from the backend (see [sheet-drawing.md](../../documentation/services/backend/sheet-drawing.md)).
The range toolbox also types the frames in (`FrameRangeFields.tsx`).

## 10. Keys

The page listens to the window's keys. A key in a text field does nothing.

| Key | What it does |
|---|---|
| Escape | lets go the picked notes, the marked stretch and the picked lyrics pieces (also on a read-only sheet) |
| Delete, Backspace | takes off the picked lyrics pieces first, else the picked notes (not on a read-only sheet) |
| ⌘Z, ⇧⌘Z, ⌘Y | undo, redo |
| ⌘V | paste the copied passage |
| ⌘C | copies the marked stretch or the picked notes (the browser's copy event) |
| Space | play, pause |

## 11. The AI's answers on the page

- A run's panel (`AiRunPanel.tsx`) opens at the right while the AI writes, and after. The sheet is laid out beside it,
  so its batches show whole (`ENHANCE_PANEL_WIDTH`). **Stop**, then **Revert** and **Close**.
- The history of AI runs (`AiHistoryPanel.tsx`) opens from `⋯`, at the same place.
- A run that ends with a word the user should know (no batch accepted, or the notes the AI added and left out) shows
  it once in an alert (`data-sheet-notice`). The alert is hidden while the run panel is open, which says the same.
- An error of a read or a write shows in an alert at the top of the page. A write refused by the backend shows in a
  short message at the bottom (`data-testid="sheet-refused"`).

The runs themselves are told in [`context/ai/`](../ai/README.md): [whole-run.md](../ai/whole-run.md) (**Enhance it
again with AI**, **Write it all again**), [stretch-and-simplify.md](../ai/stretch-and-simplify.md) (a stretch and
**Simplify**), and [levels.md](../ai/levels.md).

## 12. The files of the page

| File | Role |
|---|---|
| `pages/piece/SheetTab.tsx` | The Sheet step: gives the page the piece, its status and the step's callbacks (`onChanged`, `onSplit`, `stretchAction`) |
| `pages/piece/sheet/SheetPage.tsx` | The types of the step (`SheetStep`, `PassageView`, `PlayView`); draws `FramesSheetPage` |
| `pages/piece/sheet/frames/FramesSheetPage.tsx` | The page: the header, `sheetButtons`, the floating toolbox, the zoom and the wheel, the recording, the keys, the toolboxes and the dialogs |
| `pages/piece/sheet/frames/FramesSheetView.tsx` | The drawing and its overlay: the cursor, the picks, the marked stretch, the veil, the reveal, the lyrics pieces, the window |
| `pages/piece/sheet/frames/useFramesSheet.ts` | The sheet as the page holds it: the reads, the job's messages, the edits, the AI's start, stop and revert |
| `pages/piece/sheet/frames/geometry.ts` | The arithmetic of the page: the cursor's place, the time under a point, the noteheads of a column |
| `pages/piece/sheet/frames/navigation.ts` | The navigation state of **Enhance with AI** on a version of My library (which run, which model, how many batches) |
| `pages/piece/sheet/toolboxPlacement.ts` | Where a toolbox opens, measured from what is drawn |
| `pages/piece/sheet/sheetConstants.ts` | The colours of the hands on the keyboards; `formatSeconds`, a time as `mm:ss.cc` (see [timestamps.md](timestamps.md)) |
| `ui/FloatingBar.tsx` | The floating bar: grip, hide, the eye button |
| `components/piece/AiMark.tsx` | The AI mark |
| `components/time/ScorePlayer.tsx` | The recording, with its scrub bar |

`hooks/usePlayedNotes.ts` is not part of the sheet. Only Notes Falling (`pages/play/FallingView.tsx`) uses it.

## 13. Undo and redo

Every change to the sheet is one step of the part's log, `sheet.edits.json` (`part_sheet/edits.py`, at most 50 steps).
The log is a file, so it survives a reload and another page. A copy of the part (duplicate, export, Save to library)
starts without steps.

- **Undo** and **Redo** (section 4) walk the log. Their tooltips name the step, for example **Undo: Move a note to the
  left hand**. ⌘Z, ⇧⌘Z and ⌘Y walk it too (Control on Windows and Linux). Both are off with nothing to walk, while an edit
  is on its way, and while the AI writes the sheet or the sheet is locked; the tooltip says why when it is the lock.
- A step holds what its edit changed: the hand of each note moved, the notes taken off the page or put back, the keys
  of a **Transpose**, and the lines of `sheet.f1` that a reading edit changed. Undo puts the before back, and redo the
  after. A step touches only the notes still as it left them: a hand that something else changed since stays.
- A paste, a promotion of a passage and **Revert** of an AI run keep the part as it was, in its history (see
  [paths-and-data.md](../../documentation/services/backend/paths-and-data.md), section 4.5). Their undo puts that copy
  back, so the audio changes too, and the player loads it again.
- The log starts again when a whole AI run writes the sheet, and when a new transcription replaces the notes.

## Where to look deeper

- [rendering.md](rendering.md): how the sheet is drawn, the checks of the page
- [annotations.md](annotations.md): the tools of the sheet, one section per toolbox
- [annotations-notes.md](annotations-notes.md), [annotations-stretches.md](annotations-stretches.md),
  [annotations-sheet.md](annotations-sheet.md): the note toolbox, the range toolbox, the sheet toolbox
- [printing.md](printing.md): the PDF and its pages
- [timestamps.md](timestamps.md): how a time is written
- [play-mode.md](play-mode.md), [recording-in-sheet.md](recording-in-sheet.md), [playlists.md](playlists.md): the other places that draw the page
- [`documentation/services/frontend/components.md`](../../documentation/services/frontend/components.md) section 3: the modules of the page
