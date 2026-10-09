# The sheet toolbox, the keyboard panel, and trills

What the Sheet step can say about the whole piece. The overview of the page, the defaults, undo and
saving is [annotations.md](annotations.md). Code: `aitu-frontend/src/pages/piece/sheet/SheetToolbox.tsx`,
`TransposeTab.tsx`, `TransposeDialog.tsx`, `LyricsTab.tsx`, `lyricsPieces.ts`, `PianoToolboxes.tsx`,
and the Trills panel in `SheetPage.tsx`; `music/transpose.ts`.

## The sheet toolbox

Opened from the floating bar (the sliders icon, *Sheet toolbox*). Five tabs; every change in it is
one undo step, except zoom and the frame numbers, which are how the page is looked at and are not
saved.

| Tab | Content |
|---|---|
| **Title** | Title, subtitle and artist printed above the sheet. Each is written when you leave the field or press Enter, so a word is one undo step, not one per letter. An empty title prints the project's name. The PDF takes the title |
| **Key** | The key signature of the piece, on both clefs. It changes spelling only: no note moves. When another key would print fewer accidentals, a button offers it: *Use B major (5 fewer accidentals)* |
| **Transpose** | **Notes** and **Figures** (below), each with **Preview** |
| **Lyrics** | The pasted lyrics, the pool, and the edit toolbar of the lyrics pieces (below) |
| **Layout** | Space between notes, space between lines, size of marks, zoom (also ⌘ and scroll over the sheet), frame numbers on or off, *Hide decorative notes*, and *Group high notes under 8va (n)* |

Implementation 02, Phase 7 replaced the **Figures** tab of Phase 2 (one row of figure icons for the
main figure) by **Transpose**, and added **Lyrics**.

## Transpose

Two kinds, chosen at the top of the tab. Neither changes anything until the dialog's **Transpose**:
**Preview** opens one dialog with the piano sheet as it would be and **Transpose** or **Cancel**;
a line of text is added only when it changes the decision (notes that would leave the keyboard,
marks that would be removed). Each transposition is then one undo step.

**Notes.** Two small keyboards, **From** and **To** (both on Do 4 at first; the name of a key is on
its tooltip, in Spanish). The interval between the two keys ("Up 2 semitones") moves **every note
of the recording**: it is written on the backend (`POST /time/{id}/transpose`), no time moves, and
each note keeps its hand. The key signature of the piece and of every passage moves with it (Db
major up two semitones is Eb major; of two names for one key, the one with fewer accidentals), and
so do the marks that name a key: fingering, notes taken off the page, trills, grace notes. A note
that would leave the 88 keys is taken off the page and counted in the dialog. Command-Z moves every
note back exactly, the ones taken off included.

**Figures.** Two rows of figure icons, **From** and **To**, no names. **From** is pressed on negra
the first time and on the last **To** after that (`figuresFrom` of `sheet.json`). The step between
them renames every figure by the same number of rungs (D-18): negra to corchea makes every figure
one step shorter, and no note moves. A figure set by hand moves with them; one that has nothing to
become, and a beam mark on notes that become a negra or longer, is removed, and the dialog says how
many. Command-Z brings them back exactly.

## Lyrics

**Paste the lyrics**, then **Save lyrics**: the words and the pool are kept with the part (in
`project.json`, so they outlive **Remove all** and a new transcription), and the tab opens with them
every time. Any change of the words or of the pool (a piece added, edited, split, merged or
removed) offers **Save lyrics** again; the sheet's own **Save** does not keep the pool.
**Add to the pool** makes each line a **lyrics piece** in the pool, listed in the tab. The pool
keeps every piece: one on the sheet carries a **green tick** (a line placed twice, twice), so the
list shows what is in and what is not. Click a piece of the pool to edit its words in a one-line field:
**Enter** (or the scissors at the end of the field) splits it where the cursor is into two pieces in
the same place and closes the field, so a long line is broken in two and the order is kept; leaving
the field keeps the words as typed; Escape drops the change. Each piece of the pool has a **tick
box** beside its cross: only pieces next to each other can be ticked together (with some ticked,
only the piece just before or after them can be added, and only an end let go), and **Merge**,
beside the pool's title, joins them in the place of the first: the way back from a split made by
mistake (one undo step, like every change of the pool).

A piece is **dragged from the pool onto the sheet**: it starts on **the frame under the pointer**
(the column that holds it, as a click above the staves reads it; drop it on the note it starts on)
and is held for about as long as its words take (120 ms a character), never past the next piece;
pull its right edge afterwards to where it ends. On the sheet, drag a piece to move it (it starts on
the frame under its left edge, on any line, and keeps its length), up or down to lift it over high
notes, or pull its right edge to the frame it should end on (never into the next piece). **Two
pieces never share a frame.** While a piece is dragged, the strip above the staves shades every
other piece's frames in gray with a line at each end, and the frames the dragged one would cover in
green, or in red where they would cover another; a drop on red is refused (a moved piece goes back
where it was). A piece always starts and ends on a frame, which is what Play mode shows it by.

A piece is **plain text** on the page: a serif italic (Lora, self-hosted; Times Italic in the PDF)
in a soft charcoal, with no block and no corner marks. Pointing at it shows its block faintly; a
picked piece shows the block, a thin outline and a grip on its right edge, to move or resize it.
Escape, or a click elsewhere on the sheet, lets it go and it is plain text again.

While the tab is open, a click on a piece picks it, Command-click adds one, and marking a stretch
above the staves picks every piece over it. For the picked pieces:

| Action | What it does |
|---|---|
| **Words** | The text of one picked piece, edited in place; Enter splits it where the cursor is |
| Merge | Joins the picked pieces into one, in order, from the first frame to the last |
| Split | Two pieces at the cursor; the frames are shared in proportion to the words |
| New line | A line break inside the piece, at the cursor |
| Smaller, Larger | The font size, one pixel at a time |
| Back to the pool | Takes them off the sheet; their pool pieces lose the tick (words the pool does not have, from a merge or a split, join it at the top) |
| Delete | Deletes them (also the Delete key) |

Clicking a piece with the toolbox closed opens it on this tab. Words saved before Phase 7 (a line
over a stretch, with a pixel offset or width) are read as placed pieces and drawn where they were;
the first move puts them on frames. The range toolbox no longer has a Lyrics tab.

Notes on **Layout**:

- **Space between notes** is added to every column that carries a note and to no silence, so a held
  note still takes exactly the room the wall clock gives it. It is not a zoom. A stretch that needs
  more than the rest of the page is the range toolbox's **Spacing**.
- **Space between lines** is the white between one pair of staves and the next. It is vertical, so
  no column changes width. One line can also be spread on its own with the small handle between its
  two staves; that is keyed by a column, so it stays with the music when the page re-wraps.
- **Size of marks** sets how big every mark over and under the staff is drawn (fingering, words,
  `tr`), one number for all of them.
- **Frame numbers** (`f0`, `f100`) are how a mark is addressed; off to begin with, because they take
  most of the room above every staff and mean nothing musically.
- **Hide decorative notes** leaves off a sixteenth or shorter right before an eighth or longer, and
  the note before it runs on.
- **Group high notes under 8va** replaces the brackets on the page with the ones the notes ask for
  (the same rule as the first write). A bracket already open is what a second one has to beat.

## The keyboard panel

*Show the keyboard* in the `⋯` of the floating bar. It draws the keys sounding under the playhead,
the right hand in blue and the left in orange, with a number on every Do. Four colours, named in the
panel's legend: **RH onset** and **LH onset** are struck at the playhead; **RH sustain** and **LH
sustain** are still sounding from a note struck earlier, whose notehead is where it began. That is
why two keys of the same name can be lit where the page draws one notehead.

It edits as well as reports. Click a lit key and that note comes off the page. Click a dark one and
it is **added to the recording**, on the hand **Add to: Right / Left** says, taking the length that
hand is already holding. Command-Z reaches an addition.

## Trills

*Find trills* in the `⋯` asks the backend for runs where two notes take turns three times or more,
and lists them in a small panel: the two notes, the hand, the time. ✓ writes one as a trill. A
suggestion only: a missed trill costs nothing, a wrong one hides notes that were really played. A
trill prints as `tr` over the note with a wavy line to where the shake stops; every alternation
stays in the recording and still plays. *Print every trill as its notes* removes them all.

## Where to look deeper

- [annotations.md](annotations.md) — the page, the defaults, undo and saving
- [printing.md](printing.md) — Print to PDF
- [rendering.md](rendering.md) — how the sheet is drawn and wrapped
