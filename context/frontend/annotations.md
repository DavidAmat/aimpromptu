# The Sheet step: what a reader can say about a piece

Every editorial decision the Sheet step of a project offers, where the control is, and what it changes. None of it
changes the recording except where these pages say so. This page is the hub; the detail of each toolbox is on its own
page:

- [annotations-notes.md](annotations-notes.md): the **note toolbox** (figures, fingers, alteration, hand, beams, grace
  notes, duplicate, unite, marks, taking notes off the page, the chord keyboard).
- [annotations-stretches.md](annotations-stretches.md) and [annotations-sheet.md](annotations-sheet.md): the **range
  toolbox** and the **sheet toolbox**. Both pages still tell the old sheet until they are rewritten (implementation 05,
  Phases 6 and 7); until then, these two toolboxes are told in the section below.

The code is `aitu-frontend/src/pages/piece/sheet/` (the new sheet in `frames/`). The old sheet's page and selections
are kept in the archive: [old-sheet-tools/annotations-hub-old-sheet.md](../archive/old-sheet-tools/annotations-hub-old-sheet.md).

## The new sheet

Since implementation 03, Phase 10 (2026-10-27) the Sheet step has only the new sheet: the backend draws it
([rendering.md](rendering.md)); the old sheet's code is gone. On the new sheet:

- **The figures**: the reference figure (the length the sheet calls a negra, `quarterMs` of `sheet.f1`) is named by
  the AI (a reference request) or by the algorithm (`proposal.beat`), not by the reader; **Transpose → Figures** of
  the sheet toolbox is the override. This changes D-09 (the app showed the piles of gaps and the reader named the
  negra). The sheet has no compases, no tempo, no puntillos and no silencios.
- **Decoration notes** (grace notes; implementation 04, Phase 2): one or two notes shorter than a semicorchea (a
  fusa or shorter), two figures or more shorter than the next note of their hand and sounding just before it. A
  lone short note that is not one, just before a note more than two figures longer, is written two figures shorter
  than it (a semicorchea before a blanca is a corchea); a run of three or more keeps its figures. The **Grace**
  switch of the note toolbox and a figure set by hand win over the rule. Every sheet follows it when it is drawn.

- **Pick notes**: click a notehead (the recording goes there), ⌘-click or Shift-click to add or take one away, or
  drag a box across the staves. Escape drops the pick. The note toolbox opens beside the notes, titled with the
  name the sheet prints (`Do-# 5`) or the number of notes, with their time under it.
- **Mark a stretch**: in the strip above the upper staff of a line (it shows faintly under the pointer), click for
  one column, drag across columns (on to the next lines too), Shift-click to extend. The stretch is a lavender
  band; the range toolbox (*Frames*) opens to the left of it. Its first line holds the frame numbers of the first and
  last columns of the stretch in two fields ("From frame [283] to frame [495]"; implementation 04-3, Phase 2b): other
  numbers, then Enter or leaving both fields, mark the stretch they name. The sheet has a grey dashed line every 100
  frames with the frame number and the time on its top, so that the user can name a place in the words of **Enhance
  with AI**. Its first row, **Both / Right / Left**, narrows the
  band and the Clef and Octave tabs to one hand. One selection at a time: picking notes drops the stretch, and the
  other way round. Each toolbox hands its selection to the other from its title bar.
- **The note toolbox**: the seven figures, **Finger**, **Alteration**, **Hand**, **Beam**, **Grace**, **Duplicate**,
  **Unite**, **Marks** and the trash icon, with the chord keyboard. Its title bar holds **Enhance these notes with AI**
  (the AI mark), **Copy the frames of these notes** and **Select the frames of these notes**. Every control is one step
  of Undo. The detail is in [annotations-notes.md](annotations-notes.md).
- **The range toolbox**: **Key** (the armadura of the stretch on both clefs, ✓; 🗑 back to the armadura of the
  piece; *Use D major here* when another armadura prints fewer signs over the stretch), **Clef** (treble or bass for
  each hand in scope, the hand's own clef again after the stretch; **Clefs by the rule** writes the clefs and 8va of
  the clef rules over the stretch), **Octave** (8va, 15ma, 8vb, 15mb over each hand in scope; a bass clef takes no
  8va or 15ma). A tab with a dot means the stretch already carries that setting.
- **Enhance with AI** of a stretch, with your own words: the AI mark (the logo) in the title bar of either toolbox
  (the stretch of the notes picked, or the stretch marked) opens the Enhance with AI dialog on **A stretch**:
  **Both**, **Right** or **Left** (one hand: only that hand changes, the other stays exactly as it is; chosen from
  the notes picked or the range toolbox's hand; implementation 04, Phase 4), and the words. A short instruction ("all these notes are in the left hand: share them
  between the two hands", "make these octaves single notes, keep the rhythm", "octaves as negras, one on each
  beat"), or none. Your words come first, and the AI aims at a stretch simpler to read and to play (uniform
  patterns, the same pitch for the same role): it writes the hands, beams, clefs and ornaments again as they ask,
  and when they ask it takes notes off, changes pitches, adds notes and sets figures. Those changes go into the
  notes of the part (Notes Falling shows them); the audio does not change. About 10 seconds and one to three cents;
  the stretch has the pale veil meanwhile and then appears column by column. The answer is one step of Undo. When
  no answer is accepted, a quiet line says the stretch stays as it was.
- **Undo and Redo**: the arrows of the floating bar, ⌘Z and ⇧⌘Z (Control-Z and Control-Y on Windows). The
  backend keeps the steps, so they survive a reload and another page; the last 50 are kept. A new AI run on the
  whole sheet, or a new transcription, starts them again (with one step, "Notes the AI added and left out", when
  the run added or left out notes; implementation 04, Phase 3); a Simplify run is one step ("Simplify the left hand
  with AI").
- **No Save button**: each change is written at once.
- **Nothing can be changed while the AI writes the sheet** (the whole sheet or a stretch): the toolboxes and the
  arrows say why.
- **The whole song** (the Enhance with AI dialog with nothing picked; implementation 04, Phase 4): **Simplify the
  left hand**, **the right hand** or **both hands** writes only the rules of simplicity (a pattern that repeats is
  written the same way every time; a quick chord that makes one hand jump far keeps the note near the main note),
  adding or leaving out a few notes; the hands, beams and clefs stay, and the other hand is not touched. The AI goes
  over the song batch after batch, each seeing what was simplified before, so a chorus that repeats gets the same
  change. **Write it all again** is the whole run below. Each choice shows its cost.
- **Enhance it again with AI** (the whole sheet, **Write it all again**) reads the current hands, the ones you
  moved among them, as a suggestion, and may change any of them (the user's answer of Phase 6). It keeps your
  fingers, your figures set by hand and your grace note switches; it writes the beams, clefs, 8va, armaduras and
  ornaments again (the user's answer of Phase 7). Since prompt version 6 (implementation 04, Phase 3) it also
  follows the rules of simplicity and may add or leave out a few notes for them (at most a tenth of a window),
  written into the notes as a stretch does. A first run reads the notes without hands.
- **The sheet toolbox** (the sliders icon of the floating bar; implementation 03, Phase 8): **Info** (named
  Title until 2026-10-30: title, subtitle and artist above the sheet and on the PDF, written when the field is left;
  editable also while the AI writes the sheet), **Key** (the armadura of the
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
- **Copy and paste** (Phase 8B): **Copy this stretch** (the range toolbox), **Copy the frames of these notes** (the
  note toolbox) or ⌘C keep a reference to the stretch in the app's clipboard (every tab, and the system clipboard as
  text); **Paste** (the floating bar, ⌘V) puts it in at the cursor, or over the marked stretch: its notes, its audio
  and its sheet (the AI's or your decisions in it come along, read in their own armadura and clefs, and yours again
  after it); everything after it moves later. One step of undo: Undo puts the part back as it was, audio included.
  The range toolbox also has **Record this passage** and **Start a new part here** (a project of parts), the floating
  bar **Record a passage at the end**; a blank sheet (From scratch) says *Nothing to write yet.* with **Record a
  passage** and **Paste the copied passage**.
- **A read-only sheet** (a version of My library, a source of From other projects, the requests review): a stretch
  marked in the strip opens a small *Frames* panel with **Copy this stretch** and the screen's own action (**Add to
  a playlist**, **Add this stretch**, **Comment on this stretch**).
- **The page of a passage** (Record in Sheet, [recording-in-sheet.md](recording-in-sheet.md)): the Current is read
  only, with no bar; the Proposal (a take) has every tool, its own bar with the passage's actions, and the window
  over the take (a blue band, dragged by its grip above the first line). Both read with the song's reference figure
  (the take's at its speed) and the song's armadura where the passage starts. The take's sheet is the algorithm's,
  with **Enhance with AI** as a button. **Promote** carries the Proposal's sheet into the song, and the song's sheet
  opens with the promotion as its last step of undo.
- **Not on the new sheet** (the user's answers of Phase 8): space between notes, size of marks, frame numbers, hide
  decorative notes, group high notes under 8va (Layout); Find trills, Remove all and Bring back N notes taken off.
- **Not on the new sheet** (the user's answer of Phase 7): even spacing of a run, the room of a stretch (Spacing),
  speed changes (Speed), print smaller, a decoration that is not played (the grace note switch replaces both), and
  hiding or dragging an 8va bracket.

## Where to look deeper

- [annotations-notes.md](annotations-notes.md): the note toolbox
- [annotations-stretches.md](annotations-stretches.md): the range toolbox
- [annotations-sheet.md](annotations-sheet.md): the sheet toolbox
- [rendering.md](rendering.md): how the sheet is drawn
- [projects.md](projects.md): the steps of a project around the Sheet step
- [`documentation/services/backend/rhythm-and-annotations.md`](../../documentation/services/backend/rhythm-and-annotations.md):
  `sheet.json` field by field (the old sheet's file, still read)
- `aitu-backend/src/aitu_backend/sheet/README.md` sections 13 to 17: the new sheet's edits and marks
- [old-sheet-tools/annotations-hub-old-sheet.md](../archive/old-sheet-tools/annotations-hub-old-sheet.md): the old sheet's page and selections (the record)
