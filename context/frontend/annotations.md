# The Sheet step: what a reader can say about a piece

Every editorial decision the Sheet step of a project offers, where the control is, and what it
changes. None of it changes the recording except where these pages say so. The detail of each
toolbox is on its own page:

- [annotations-notes.md](annotations-notes.md): the **note toolbox** (figures, fingers, hand, beams,
  even spacing, decoration, small print, trill, taking a note off the page).
- [annotations-stretches.md](annotations-stretches.md): the **range toolbox** (key, clef, octave
  brackets, spacing, speed, Record this passage) and what can be done to a bracket on the page.
- [annotations-sheet.md](annotations-sheet.md): the **sheet toolbox** (title, key, transpose,
  lyrics, layout), the keyboard panel, and **Find trills**.

The code is `aitu-frontend/src/pages/piece/sheet/` (implementation 02, Phase 2 split the old
5,328-line `RhythmPage.tsx` into it; see
[`documentation/services/frontend/components.md`](../../documentation/services/frontend/components.md)).

## The new sheet (implementation 03, Phases 6 and 7)

Since implementation 03, Phase 5 the Sheet step opens on the **new sheet** (without compases, drawn by the
backend; [rendering.md](rendering.md)). Everything below this section is the **old sheet**, which opens from
**Edit in the old sheet** and keeps the tools that have not moved yet (copy and paste, Record a passage, Start a new
part: implementation 03, Phase 8B). On the new sheet:

- **Pick notes**: click a notehead (the recording goes there), ⌘-click or Shift-click to add or take one away, or
  drag a box across the staves. Escape drops the pick. The note toolbox opens beside the notes, titled with the
  name the sheet prints (`Do-# 5`) or the number of notes, with their time under it.
- **Mark a stretch**: in the strip above the upper staff of a line (it shows faintly under the pointer), click for
  one column, drag across columns (on to the next lines too), Shift-click to extend. The stretch is a lavender
  band; the range toolbox (*Frames*) opens to the left of it. Its first row, **Both / Right / Left**, narrows the
  band and the Clef and Octave tabs to one hand. One selection at a time: picking notes drops the stretch, and the
  other way round. Each toolbox hands its selection to the other from its title bar.
- **The note toolbox**: the seven **figures** (pressing one sets the figure by hand: the rule keeps it, and it is
  never a grace note; ⌫ gives the chords back the rule's figure; a beam the new figure broke comes back with Undo,
  not with ⌫); **Finger** 1 to 5 (on a single chord one number per note, from the thumb in the right hand and from
  the little finger in the left); **Hand: Right / Left** (written into the notes, `notes.pmn`); **Beam** (join the
  picked notes as one group, pressed again to take the beam away; cut the group in front of the first one, or join
  it to the group before); **Grace** (write as grace notes of the next note of their hand, or as normal notes,
  whatever the grace rule says; ⌫ back to the rule); **Marks** (*tr*, *mord*, *turn* over onsets of one hand that
  follow one another: the first is written with the ornament, the others are played inside it and not drawn;
  *arp* rolls a chord; *ferm* a fermata; pressed again, each goes away); 🗑 or **Delete** takes the notes off the
  page (they leave the notes; Undo brings them back).
- **The keyboard of the note toolbox** (the user's request of Phase 8A): when the notes picked are in one column, the
  toolbox opens with a small keyboard (scrolled to the chord; the octave number on each Do) where that column's keys
  are lit in their hand's colour, both hands. A dark key adds a note to the column, in the hand of the notes picked
  (both hands picked: the hand of the nearest lit key) and as long as that hand's chord, so it prints the chord's
  figure and stays in its beam group; a lit key takes that note off. Each press is one step of Undo, and the chord
  stays picked. Notes of several columns show no keyboard.
- **The range toolbox**: **Key** (the armadura of the stretch on both clefs, ✓; 🗑 back to the armadura of the
  piece; *Use D major here* when another armadura prints fewer signs over the stretch), **Clef** (treble or bass for
  each hand in scope, the hand's own clef again after the stretch; **Clefs by the rule** writes the clefs and 8va of
  the clef rules over the stretch), **Octave** (8va, 15ma, 8vb, 15mb over each hand in scope; a bass clef takes no
  8va or 15ma). A tab with a dot means the stretch already carries that setting.
- **Enhance with AI** of a stretch, with your own words: the ✨ in the title bar of either toolbox (the stretch of
  the notes picked, or the stretch marked). A short instruction ("all these notes are in the left hand: share them
  between the two hands", "make these octaves single notes, keep the rhythm", "octaves as negras, one on each
  beat"), or none. Your words come first, and the AI aims at a stretch simpler to read and to play (uniform
  patterns, the same pitch for the same role): it writes the hands, beams, clefs and ornaments again as they ask,
  and when they ask it takes notes off, changes pitches, adds notes and sets figures. Those changes go into the
  notes of the part (Notes Falling shows them); the audio does not change. About 10 seconds and one to three cents;
  the stretch has the pale veil meanwhile and then appears column by column. The answer is one step of Undo. When
  no answer is accepted, a quiet line says the stretch stays as it was.
- **Undo and Redo**: the arrows of the floating bar, ⌘Z and ⇧⌘Z (Control-Z and Control-Y on Windows). The
  backend keeps the steps, so they survive a reload and another page; the last 50 are kept. A new AI run on the
  whole sheet, or a new transcription, starts them again.
- **No Save button**: each change is written at once.
- **Nothing can be changed while the AI writes the sheet** (the whole sheet or a stretch): the toolboxes and the
  arrows say why.
- **Enhance it again with AI** (the whole sheet) reads the current hands, the ones you moved among them, as a
  suggestion, and may change any of them (the user's answer of Phase 6). It keeps your fingers, your figures set by
  hand and your grace note switches; it writes the beams, clefs, 8va, armaduras and ornaments again (the user's
  answer of Phase 7). A first run reads the notes without hands.
- **The sheet toolbox** (the sliders icon of the floating bar; implementation 03, Phase 8): **Title** (title,
  subtitle and artist above the sheet and on the PDF, written when the field is left), **Key** (the armadura of the
  piece; *Use D major (n fewer signs)* when another prints fewer signs over the piece), **Transpose** (**Notes**:
  every note moved by the interval of two keyboards, the sheet with them, the armaduras renamed with fewer signs, a
  note off the 88 keys taken off; **Figures**: every figure renamed by the same number of steps, the page keeps its
  spacing; each with **Preview** and **Transpose**), **Lyrics** (as on the old sheet: paste, **Save lyrics**, the
  pool; a piece is dragged from the pool onto the sheet, on the frame under it), and
  **View** (**Zoom**, kept in this browser; **Space between lines**, kept with the sheet). Every change is one step
  of Undo.
- **Lyrics blocks** (implementation 03, Phase 8A++, the user's request): a click on a piece on the sheet picks it
  (⌘ or Shift adds one) and opens the **lyrics toolbox** beside it: the **Words** (Enter splits the piece where the
  cursor is), **Font** (Lora, Geist, Montserrat), **Size**, **Normal**, **Bold**, **Italic**, *Back in the line of
  words*, merge, split, a new line, back to the pool, delete (also the Delete key). On the sheet a picked piece is a
  block with an outline: drag it anywhere (it keeps its frames), drag its side handle to make it narrower or wider
  (the words wrap as the pointer moves), drag its corner to make the words larger or smaller. Its frames, when the
  words sound in Play mode, are a bar in the strip above the staves, with an end on each side to drag. While a piece
  is picked the strip marks no stretch; a click off the pieces lets them go. A piece whose frames cross a line break
  shares its words between the lines by the width its frames take on each (60 % of the width, about 60 % of the
  words), so a narrower window splits it again. Every change is one step of Undo.
- **Print to PDF** (the printer icon): the paper, the margins, the size of the music (a 6.5 mm staff by default) and
  the space between lines on paper (6 mm by default), both kept in this browser, the title and page numbers;
  the lines are laid out again for the paper (never shrunk) and never split across a page turn
  ([printing.md](printing.md)).
- **The keyboard panel** (`⋯` → *Show the keyboard*): the keys sounding under the cursor, as on the old sheet; a lit
  key takes that note off the page, a dark one adds a note to the hand of **Add to** (one step of Undo).
- **Not on the new sheet** (the user's answers of Phase 8): space between notes, size of marks, frame numbers, hide
  decorative notes, group high notes under 8va (Layout); Find trills, Remove all and Bring back N notes taken off.
- **Not on the new sheet** (the user's answer of Phase 7): even spacing of a run, the room of a stretch (Spacing),
  speed changes (Speed), print smaller, a decoration that is not played (the grace note switch replaces both), and
  hiding or dragging an 8va bracket.

## The page

The page is the sheet (plan section 11.2 of implementation 02). From top to bottom:

- **The title lines**: the title (the project's name until one is written in the **Title** tab),
  and under it the subtitle and the artist.
- **A scrub bar**: the time of the playhead and the length of the piece. Drag it to move the
  recording.
- **The piano sheet**. It wraps to the width of the window, and wraps again when the window is
  made wider or narrower.
- **The floating bar** (draggable, can be hidden): play or pause (also Space), undo, redo, the
  **sheet toolbox**, **Record a passage at the end** (Phase 9), **Paste** (⌘V, Phase 8), **Print to PDF**, **Save**, and
  `⋯` with *Show the keyboard*, *Find trills*, *Bring back N notes taken off* (when some are) and
  *Remove all*.

There is no button to write the sheet: it is drawn as soon as the page opens. The one exception is
a **stale** sheet (the notes or the hands changed after it was saved): it opens with a banner and
waits for **Write the sheet**, then **Save** makes it the sheet of the project again.

Every icon on the page has a tooltip saying what it does. The old cards above the sheet (the plot
of gaps, *Name it*, *Does the piece change speed?*) and the captions under the controls are gone
(plan section 11.1). Their explanations are on these pages.

## The defaults of a first write

Four things the reader used to choose by hand are chosen when a sheet is first written (a project
with no saved sheet, or after **Remove all**). Each is the baseline of the page, not an undo step,
and an ordinary edit after that:

| Default | How | Where to change it |
|---|---|---|
| **The figures** | The highest pile of gaps (the one holding the most) is a **negra** (D-09 as changed by implementation 02). The backend chooses the pile: `GET /time/{uuid}/default-reading` | Sheet toolbox, **Transpose → Figures** |
| **The key signature** | The one that prints the fewest accidentals, measured on the drawn notes | Sheet toolbox, **Key**; a passage in the range toolbox, **Key** |
| **The left hand's clef** | The treble clef over every run of four or more left-hand chords written two ledger lines or more above the bass staff (the clef rule, [rendering.md](rendering.md)) | Range toolbox, **Clef** |
| **Octave brackets** | Over every run of three or more chords written three ledger lines or more outside its staff, measured in the key just chosen, never over a passage the clef rule moved | Range toolbox, **Octave**; again with *Group high notes under 8va* in **Layout** |

The pile is measured once, when the sheet is first written, and its length is saved with the
sheet: a sheet opened again is drawn from the saved length, not from a pile measured again on the
notes, so a paste, a cut or a split of a part (Phase 10) does not rename its figures.

The negra is a convention, not a measurement: statistics cannot tell a negra from a corchea, so a
piece can come out twice too fast or too slow. One **Transpose → Figures** renames every note and moves
nothing.

## The two selections, and the two toolboxes

There are two ways to pick something on the sheet, and each opens its own panel **beside what you
picked**. Both panels can be dragged, and once dragged they stay where you put them.

- **Noteheads**: click one, ⌘-click to add, or drag a rubber band across the staves. Opens the
  **note toolbox**; every control applies to the whole set. It also takes the recording to where
  those notes are (the first column of the set), so the keyboard panel draws the chord you clicked.
  The page does not scroll: you are already looking at the notes.
- **A stretch of time**: click above the staves. The stretch starts where you clicked and runs for
  one group; shift-click another cell to extend it, or pull either end to any column. Opens the
  **range toolbox** (titled *Frames*). Its first row is **Both / Right / Left**: pick one hand and
  the highlight shrinks to that hand's staff, and **Clef** and **Octave** act on that hand alone.

**Either selection can be handed to the other** from the icon in the panel's title bar: from notes,
*Select the frames of these notes*; from a stretch, *Select the notes in this stretch* (every note
that begins inside it, on the staves in scope).

A stretch that carries an edit draws **two corner marks in its own colour**, so it can be seen
without being selected. Click a corner to open that stretch again on the tab of what it carries.

**The range toolbox opens to the left of where the stretch starts**, or below the staves when there
is no room, and stays there: a stretch grows to the right as you drag its handle, so a panel on that
side would end up on top of it. The note toolbox opens to the right.

## Taking it back

**Command-Z takes the last edit back, Shift-Command-Z puts it back** (Control-Z and Control-Y on
Windows), and so do the two arrows of the floating bar, whose tooltips say what they are about:
*Undo: Main figure*. In a text field the keys do what they do in any text field. **One press is one
step**, however many things it changed. At least 20 steps are kept (the history keeps 100).

Six edits are written onto the **recording** rather than onto this page:

| Edit | Does Command-Z reach it? |
|---|---|
| **A note added on the keyboard panel** | Yes. It is marked removed again, and the sheet is drawn again |
| **A hand swap** | Yes. The hand each note had before is written back, and the sheet is drawn again |
| **A notes transposition** | Yes. Every note moves back by the same interval, the notes it took off the keyboard come back, and the key and the marks move back with them |
| **A paste** (Phase 8) | Yes. The part is put back as it was before the paste, notes, audio and saved sheet; Redo pastes it again ([projects.md](projects.md) section 5) |
| **A promotion of a re-recorded passage** (Phase 9) | Yes. The part is put back as it was before the promotion, notes, audio and saved sheet; Redo promotes again ([recording-in-sheet.md](recording-in-sheet.md)). The sheet opens with it as its last step |
| **Remove all** | No. It asks first, deletes the saved sheet and puts the notes taken off back on the recording |

Until Phase 9 a re-record and a recorded passage were two panels of this page that undo could not
reach; the page of a passage replaced both.

## Keeping it

**Save** is on the floating bar, always visible. Nothing is written before it. A **dot on Save**
says there are changes it would keep: a sheet never saved, a change since the last save, or a stale
sheet. Undoing back to the saved state takes the dot away. A refused save is said in a message at
the bottom of the window that stays until it is closed.

Everything is stored in one file beside the notes, `sheet.json` (the *metadata* of the app
context; `rhythm.json` until implementation 02, Phase 3), and **none of it is in the recording**,
except the notes taken off the page, which Save also takes out of the matrix. Transcribing the piece again
clears the file on purpose: its column numbers point at the notes that were there before.

## Why a column number is a safe address

Every mark is keyed by column (a frame), and **a column never moves** as long as the piece's
wall-clock length does not change. That is what lets a fingering survive a change of figures, a
passage re-recorded into its window, a change of key, and a reload. The places length does change are
a paste and a re-recorded passage put in whole, and there marks move with their notes in the same
write; see
[`../backend/editing.md`](../backend/editing.md).

## Where to look deeper

- [`documentation/services/backend/rhythm-and-annotations.md`](../../documentation/services/backend/rhythm-and-annotations.md)
  — `sheet.json` field by field
- [rendering.md](rendering.md) — what the renderer does with the marks
- [projects.md](projects.md) — the steps of a project around the Sheet step
- [`../implementations/02-private-web-app/02-implementation-phase-2.md`](../implementations/02-private-web-app/02-implementation-phase-2.md)
  — the phase that made this page
