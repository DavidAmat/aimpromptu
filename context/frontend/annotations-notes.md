# The note toolbox

What the Sheet step can say about the notes picked on the sheet. The page, the two selections and the
undo are in [annotations.md](annotations.md). Code: `aitu-frontend/src/pages/piece/sheet/frames/FramesNoteToolbox.tsx`
(the panel), `readingTools.ts` (the figures, the ornaments and the chord keyboard's column, shared with the
range toolbox). The chord keyboard's sibling, the keyboard panel under the playhead, is `PianoToolboxes.tsx`, not
this toolbox.

Every control writes at once, is one step of undo, and redraws the sheet. Nothing changes while the AI writes
the part; the controls say why in their tooltips.

## Picking the notes

- Click a notehead. ⌘-click or Shift-click adds one or takes one away; a drag across the staves picks a box.
  Escape drops the pick.
- The panel opens beside the notes. Its title is the printed name of one note (`Do-# 5`, spelled against the
  key at that column), or the number of notes. Under it, the time of the notes in the recording.
- A figure, a beam, a grace note and an ornament belong to a **chord** (the notes of one hand at one column):
  picking one note names the whole chord of that hand. A finger belongs to one note.
- The title bar has three actions:
  - **Enhance these notes with AI, with your own words**: opens the Enhance with AI dialog on the stretch of
    these notes. Shown only where the AI can run on the sheet.
  - **Copy the frames of these notes** (⌘C): keeps the stretch they cover for a Paste.
  - **Select the frames of these notes**: hands the selection to the range toolbox
    ([annotations-stretches.md](annotations-stretches.md)).

## The rows

| Row | Control | What it does |
|-----|---------|--------------|
| (top) | The seven figures, redonda to semifusa | Sets the figure of every picked chord by hand. The rule keeps it, and it is never a grace note. The figure is shown pressed when every picked chord has it. **Back to the figures of the rule** (⌫) gives the figure back to the rule |
| **Finger** | 1 to 5 | One number on every picked note. On a single chord, one number per note: in the right hand the smallest number goes to the lowest note, in the left the largest does. **Remove the finger numbers** (⌫) takes them off |
| **Alteration** | ♭♭, ♭, ♮, ♯, × | Shown for notes written with a sharp or a flat, or spelled by hand. The same key under another name (La-# 4 as Si-b 4 in a key of sharps). The spelling rule then keeps it. **Back to the spelling of the key** (⌫) gives it back |
| **Hand** | Right / Left | Gives the picked notes to that hand. Written into the notes (`notes.pmn`), one step of undo |
| **Beam** | Link icon | **Beam these notes as one group** joins the picked chords. On a group already made, **Remove the beam** takes it away. Needs one hand, chords that follow one another, none a grace note, each a corchea or shorter |
| **Beam** | Scissors icon | **Start a new beam here** cuts the group in front of the first picked chord; when it already starts one, **Join to the beam before** joins it back. Needs one hand |
| **Grace** | Corchea icon | **Write as grace notes of the next note** (the next note of their hand), or **Write as normal notes**. ⌫ (**Back to the grace rule**) gives them back to the rule |
| **Duplicate** | Shorter figures | Each picked note is played again at that shorter figure, filling its own time: a negra becomes two corcheas, four semicorcheas. Up to 16 copies of a note. Offered only for figures shorter than the picked chords' |
| **Unite** | Merge icon, or the figure it makes | Two or more consecutive chords of one hand, with the same keys, become one chord at the first one's place. Its figure is the sum of theirs when that sum is a figure (two corcheas make a negra); otherwise the figure nearest to the time the chords fill in the recording |
| **Marks** | *tr*, *mord*, *turn* | Over picked onsets of one hand that follow one another: the first is written with the ornament, the others are played inside it and not drawn. Pressed again on the same onsets, it goes away |
| **Marks** | *arp*, *ferm* | *arp* rolls each picked chord; *ferm* puts a fermata over each. Pressed again, it goes away |
| (bottom) | 🗑 **Take them off the page** (Delete) | Marks the notes removed in `notes.pmn`, as the Notes step does: they leave the page. Undo brings them back |

One row reaches further than its icons say:

- **Hand** changes the neighbours too. A note's printed length runs to the next onset of its own hand, so the
  notes of both hands around a moved note can be drawn with new lengths.

## The chord keyboard

When the picked notes sit in one column (both hands count), the panel shows a small keyboard, scrolled to the
chord, where the column's keys are lit in their hand's colour (both hands). It works on the chord:

- A **dark key** adds a note to the column, as long as that hand's chord, so it prints the chord's figure and
  stays in its beam group. The hand is the hand of the notes picked; with both hands picked, the hand of the
  nearest lit key (the right hand on a tie). The note goes in through `POST /sheet/{uuid}/add`.
- A **lit key** takes that note off (`POST /sheet/{uuid}/remove`).
- ⌘-click, Shift-click or Control-click on a lit key picks that note or lets it go. The picked notes' keys keep
  their full colour with a dot; the other lit keys turn pale. **Hand** then moves only the picked notes. A note
  added on the keyboard is the one picked after.

Notes picked in several columns show no keyboard: it is the chord of one moment.

## How an edit is kept

- The routes are `POST /sheet/{uuid}/reading` (the figure, alteration, finger, beam, grace and ornament actions,
  one `action` each), `POST /sheet/{uuid}/hands`, `POST /sheet/{uuid}/duplicate`, `POST /sheet/{uuid}/unite` and
  `POST /sheet/{uuid}/remove` (`aitu-backend/src/aitu_backend/api/sheet.py`).
- `part_sheet/reading.py` checks an action and plans its change (`set_figure`, `set_alter`, `set_fingers`,
  `set_grace`, `join_beam`, `break_beam`, `set_ornament`). `part_sheet/edits.py` `edit_reading` stores the decision
  in the sheet and lays the sheet on the notes again, so the rules run (figures, grace notes, beam groups, spelling)
  around the user's decision.
- Hand, duplicate, unite, take off the page and a note added on the keyboard change the notes themselves, in
  `notes.pmn` (`move_hands`, `duplicate_notes`, `unite_notes`, `remove_notes`, `add_note`). Each is one step of undo.
- The decisions the user makes are kept through a new AI run: a figure set by hand, a finger, the grace switch.
  The beams, clefs, octave lines, armaduras and ornaments are the AI's kinds too, and a new run writes them again
  ([editing.md](../backend/editing.md) has the rule of the note edits).

## Where to look deeper

- [annotations.md](annotations.md): the page, the selections, undo and what is saved
- [annotations-stretches.md](annotations-stretches.md): the range toolbox, which opens on the same selection
- [annotations-sheet.md](annotations-sheet.md): the sheet toolbox
- [editing.md](../backend/editing.md): the note edits in the backend, and the rule of undo
- [rendering.md](rendering.md): how the sheet is drawn after an edit

Archive of the old sheet's note toolbox (the record, removed in implementation 03, Phase 10):
[`context/archive/old-sheet-tools/annotations-notes.md`](../archive/old-sheet-tools/annotations-notes.md).
