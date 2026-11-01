# The Sheet step: what a reader can say about a piece

Every editorial decision the Sheet step of a project offers, where the control is, and what it changes. None of it
changes the recording except where these pages say so. This page is the hub; the detail of each toolbox is on its own
page:

- [annotations-notes.md](annotations-notes.md): the **note toolbox** (figures, fingers, alteration, hand, beams, grace
  notes, duplicate, unite, marks, taking notes off the page, the chord keyboard).
- [annotations-stretches.md](annotations-stretches.md): the **range toolbox**, copy and paste, **Delete these frames**. [annotations-sheet.md](annotations-sheet.md): the **sheet toolbox**, the lyrics on the sheet, the keyboard panel and Print to PDF.

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
- **Mark a stretch**: a click, a drag or Shift-click in the strip above the upper staff; the range toolbox opens beside it. One selection at a time: picking notes drops the stretch, and the other way round. The detail is in [annotations-stretches.md](annotations-stretches.md).
- **The note toolbox**: the seven figures, **Finger**, **Alteration**, **Hand**, **Beam**, **Grace**, **Duplicate**,
  **Unite**, **Marks** and the trash icon, with the chord keyboard. Its title bar holds **Enhance these notes with AI**
  (the AI mark), **Copy the frames of these notes** and **Select the frames of these notes**. Every control is one step
  of Undo. The detail is in [annotations-notes.md](annotations-notes.md).
- **The range toolbox** (*Frames*): the frame numbers, **Which staff**, the tabs **Key**, **Clef** and **Octave**, its title bar's actions. Detail in [annotations-stretches.md](annotations-stretches.md).
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
- **The sheet toolbox**, the lyrics on the sheet, Print to PDF and the keyboard panel: [annotations-sheet.md](annotations-sheet.md).
- **Copy and paste** (Phase 8B): copy with ⌘C, the toolboxes' title bars or the read-only panel; paste with ⌘V or the floating bar. Detail in [annotations-stretches.md](annotations-stretches.md) and [annotations-notes.md](annotations-notes.md).
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
