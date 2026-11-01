# The sheet toolbox: Info, Key, Transpose, Lyrics, View

What the Sheet step can say about the whole sheet. The overview of the page, the defaults and undo is
[annotations.md](annotations.md). The note toolbox is [annotations-notes.md](annotations-notes.md) and the range
toolbox is [annotations-stretches.md](annotations-stretches.md). The old sheet's version of this page is the record in
[old-sheet-tools/annotations-sheet.md](../archive/old-sheet-tools/annotations-sheet.md).

Code: `aitu-frontend/src/pages/piece/sheet/frames/FramesSheetToolbox.tsx` (the five tabs, the Info, Key and View tabs),
`pages/piece/sheet/TransposeTab.tsx`, `pages/piece/sheet/LyricsTab.tsx` and `lyricsPieces.ts` (the Lyrics tab and its
pool), `frames/FramesLyricsToolbox.tsx`, `frames/useFramesLyrics.ts`, `frames/lyricsText.ts` (the lyrics pieces on the
sheet), `pages/piece/sheet/PianoToolboxes.tsx` (the keyboard). Backend: `api/sheet.py` (`/reading`, `/transpose`,
`/stretch`, `/words`) and `part_sheet/reading.py` (the actions of the whole sheet).

## Opening it

The sheet toolbox opens from the floating bar: the sliders icon, titled **Sheet toolbox**. It is one panel titled
**Sheet** with five tabs, **Info**, **Key**, **Transpose**, **Lyrics** and **View**. A passage's Proposal shows only
**Key**, **Transpose** and **View**.

Every change in it is one step of undo, except the zoom, which is how the page is looked at and is not saved.

While the AI writes the sheet, the panel shows why in its subtitle and only the **Info** fields can be changed. The
run keeps them. The other tabs are off until it ends.

## Info

Three fields: **Title**, **Subtitle** and **Artist**. They are printed above the sheet and on the PDF
([printing.md](printing.md)). Each field is written when you leave it or press Enter, so one word is one step, not
one per letter. The field is kept to 200 characters. An empty **Title** shows the project's name as its placeholder.

The tab was named **Title** until 2026-10-30.

The request is `POST /sheet/{uuid}/reading` with the action `titles`. A title the user removes is taken off the sheet.

## Key

The **Armadura of the piece**: the key signature of the piece, on both clefs. It changes the spelling only; no note
moves. A passage marked above the staves can take its own armadura with the range toolbox.

When another armadura prints fewer signs over the whole piece, a button offers it, for example **Use D major (3 fewer
signs)**. The tab asks `GET /sheet/{uuid}/stretch` for the whole sheet to find it. No button shows when no other
armadura prints fewer signs.

The request is the action `piece-key`.

## Transpose

Two modes, **Notes** and **Figures**, chosen at the top of the tab. Neither changes anything until you confirm it in
the preview dialog (**Preview**, then **Transpose** or **Cancel**; [FramesPreviewDialog.tsx](../../aitu-frontend/src/pages/piece/sheet/frames/FramesPreviewDialog.tsx)).
Each confirmed transposition is one undo step.

The tab starts again each time it is opened: **Notes** shows two keyboards on Do 4, and **Figures** starts on negra.
The backend keeps a `figuresFrom` field of the rhythm, but the sheet toolbox never sets it, so the **From** figure is
not remembered.

**Notes.** Two small keyboards, **From** and **To**. The interval between them is written in words ("Up 2
semitones"). **Preview** asks `POST /sheet/{uuid}/transpose` with `preview=true`, and the dialog draws the sheet as it
would be. **Transpose** asks again without the preview.

- Every note of the recording moves by the same number of semitones. No time moves, and each note keeps its hand.
- The armadura of the piece and of each passage moves too. Of two names for one key, the one with fewer signs is
  taken (`reading.moved_key`). Spelling is written again by the rules.
- The clefs are fitted again where a note reads four ledger lines or more from its staff.
- A note that would leave the keyboard is taken off the page. The dialog says how many.

**Figures.** Two rows of figure icons, **From** and **To**, with no names. The step between them is counted in figures
(from redonda to fusa). **Preview** and **Transpose** send the action `figures` to `POST /sheet/{uuid}/reading`.

- Every figure moves by the same number of steps. The spacing keeps the figure it was measured with, so no note
  moves; the dialog says so.
- The reference figure of the sheet moves by the same factor (`reading.rename_figures`).
- A figure set by hand moves too, when the new figure exists. One that has no figure to become goes back to the rule,
  and the dialog says how many.
- The main figure cannot go past the end of the ladder: the tab says **No shorter or longer figure left** and
  **Preview** is off.

Each transposition is one step of undo. Command-Z brings back every note and figure exactly, the ones taken off the
page included.

## Lyrics

The **Lyrics** tab holds the words of the song and its **pool** of lyrics pieces. The pieces on the sheet are written
by dragging them from the pool.

**The words.** Paste the lyrics in **Paste the lyrics**, then **Save lyrics**. The button reads **Lyrics saved** when
the words and the pool are the saved ones. The words and the pool are kept with the part in `project.json`
(`parts[].lyrics` and `parts[].lyricsPool`), so they outlive **Remove all** and a new transcription. The request is
`PUT /sheet/{uuid}/words`. The sheet's own **Save** does not keep the pool.

**The pool.** **Add to the pool** makes each line of the words a lyrics piece in the pool. The pool keeps every piece.
A piece that is on the sheet has a green tick, so the list shows what is in and what is not.

- Click a piece to edit its words in a one-line field. **Enter** (or the scissors at the end of the field) splits it
  where the cursor is, into two pieces in the same place. Leaving the field keeps the words. Escape drops the change.
- Each piece has a tick box beside its cross. Only neighbouring pieces can be ticked together.
- **Merge**, beside the pool's title, joins the ticked pieces into the first one. It is the way back from a split made
  by mistake.

**Onto the sheet.** A piece is dragged from the pool onto the sheet. It starts on the frame under the pointer (drop it
on the note where it starts). It is held for about as long as its words take, 120 ms a character, and never past the
next piece. Pull its right edge afterwards to where it ends. Two pieces never share a frame: a drop onto frames
another piece holds is refused, and the piece goes back where it was.

On the sheet, drag a piece to move it (it keeps its length), up or down to lift it over high notes, or pull its right
edge to another frame. A piece always starts and ends on a frame, which is what Play mode shows.

**The lyrics on the sheet.** A lyrics piece is plain text: a serif italic in a soft charcoal. A click on it picks it
(Command-click or Shift adds one), and the **lyrics toolbox** opens beside it. Marking a stretch above the staves picks
every piece over it. Escape, or a click elsewhere, lets go.

The lyrics toolbox ([FramesLyricsToolbox.tsx](../../aitu-frontend/src/pages/piece/sheet/frames/FramesLyricsToolbox.tsx))
has these controls. Each one is one step of undo.

| Control | What it does |
|---|---|
| **Words** | The text of one picked piece, edited in place; Enter splits it where the cursor is |
| **Font** | Lora, Geist or Montserrat. The PDF prints Lora as Times and the others as Helvetica |
| **Size** | The size of the words |
| **Style** | Normal, bold or italic |
| Back in the line of words | A block moved or made narrower by hand goes back above its first frame, on one line |
| Merge | Joins the picked pieces into one, from the first frame to the last |
| Split | Two pieces at the cursor; the frames are shared in proportion to the words |
| New line | A line break at the cursor |
| Back to the pool | Takes the picked pieces off the sheet; their pool pieces lose the tick |
| Delete | Deletes them (also the Delete key) |

A picked piece on the sheet is a block with an outline. Drag it to move it (it keeps its frames), drag its side handle
to make it narrower or wider (the words wrap as the pointer moves), or drag its corner to make the words larger or
smaller. A block put anywhere is saved with where it sits (`at`, `dx`, `dy`), its `width`, `font`, `bold` and `italic`.

A piece whose frames cross a line break shares its words between the two lines, in proportion to the frames it takes
on each line.

The words are stored as the sheet's own `lyrics` (the action `lyrics` of `/reading`; `part_sheet/reading.py`,
`set_lyrics`). Pieces saved on the old sheet are converted when they are first read (`part_sheet/legacy.py`).

## View

- **Zoom**: a slider from 70 % to 200 %, with a mark at 100 %. It is how big the page is drawn, kept in this browser and
  not saved with the sheet. Command and scroll over the sheet change it too.
- **Space between lines**: from 2 to 16 staff spaces, the engine's own being 5. It is the white between one pair of
  staves and the next, saved with the sheet (the action `line-space`). Going back to 5 saves nothing (`null`).

## The keyboard

*Show the keyboard* is in the `⋯` menu of the floating bar (**More sheet actions**). It opens the **Piano** toolbox
(`PianoToolboxes.tsx`), with the time of the playhead as its subtitle. It draws the keys sounding under the playhead, on
two colours for each hand: a key struck at the playhead (**RH onset**, **LH onset**) and a key still sounding from an
earlier note (**RH sustain**, **LH sustain**). Its notehead on the staff is where the note began, so two lit keys of
the same name can share one notehead.

It also edits:

- Click a lit key and that note comes off the page.
- Click a dark key and it is added to the recording, on the hand picked by **Add to: Right / Left**. It takes the
  length that hand is already holding. Command-Z reaches it.

## Print to PDF

The printer icon of the floating bar prints the sheet to PDF. The paper, the margins, the size of the music and the
space between lines on the paper are told in [printing.md](printing.md).

## Not on the new sheet

The old **Layout** tab was replaced by **View** (Phase 8, 2026-10-26). These were dropped, on the user's answers:
space between notes (the spacing is measured), size of marks (one size for all), frame numbers, hide decorative notes
(a grace note replaces it), and group high notes under 8va (**Clefs by the rule** of a stretch replaces it). **Find
trills** and the old **Remove all** are not here either. The list of all of them is in
[annotations.md](annotations.md).

## Where to look deeper

- [annotations.md](annotations.md): the hub of the Sheet step's tools
- [annotations-notes.md](annotations-notes.md): the note toolbox
- [annotations-stretches.md](annotations-stretches.md): the range toolbox
- [printing.md](printing.md): Print to PDF
- [play-mode.md](play-mode.md): the lyrics as Play mode shows them
- [`documentation/services/backend/endpoints.md`](../../documentation/services/backend/endpoints.md): the routes of
  `/reading`, `/transpose`, `/stretch` and `/words`
