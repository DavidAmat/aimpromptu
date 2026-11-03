# A stretch

A run of the AI that changes part of a sheet, not the whole song: **A stretch** writes one passage again, from the
user's words. It is a background job: the page shows the change as it is written, and it ends as one step of undo.
To make one hand easier over the song, the user writes that hand at a level ([levels.md](levels.md)).

The whole song is on [whole-run.md](whole-run.md). The code of this run is in
[documentation/services/backend/ai-runs.md](../../documentation/services/backend/ai-runs.md), section 7.

## A stretch

### What the user does

1. The user selects notes or a stretch on the Sheet step. The notes come from the note toolbox (the picked notes, with
   their frames); the stretch comes from the range toolbox (the frames marked).
2. **Enhance with AI** opens the dialog at the tab **A stretch**. It names what is selected: "this note", "these 3
   notes" or "this stretch".
3. The user chooses **Which hand**: **Both**, **Right** or **Left**. With one hand, the other hand stays exactly as it
   is.
4. The user chooses **How**:
   - **Your words**: the field **What should the AI change?** takes up to 1,000 characters. Without words, the AI
     writes the passage again as it is, with no change of notes.
   - **A level**: the passage is written again at Easy, Medium or Hard, with the patterns of that level. See
     [levels.md](levels.md) and [level-run.md](level-run.md).
5. The dialog shows the **model** and the **batches**, as for every run, and the cost and the time. Then
   **Enhance with AI** starts the run.

The status line of the dialog says what stays: "The left hand stays as it is." and "Undo takes it back."

### What the AI sees

One request for the stretch (a window conversation of one window):

- **The target**: the stretch as it is now: its notes in the hands chosen, with their beam groups, clefs, 8va lines and
  ornaments. The user's marks (fingers, figures set by hand, the grace note switch) are not sent: the AI never writes
  them.
- **The context**: the four seconds before the stretch, as decided.
- **The look-ahead**: the four seconds after the stretch, to read but not to change.
- **The other hand**, when the run is one hand: shown apart, as fixed.
- **The request**: the user's words come first and "override the usual choices": they are followed exactly. The request
  also says the purpose behind them, a sheet simpler to read and to play, with uniform patterns. When the user picked
  notes, the request names them (`f120 C5`), up to 40 names.

### What the AI may change

With words, the AI may:

- move notes from one hand to the other (with one hand chosen, only in that hand);
- join or cut beam groups, change the clefs and the 8va lines, add or remove ornaments;
- take notes off the sheet: a note of the target that the AI leaves out is removed;
- change a pitch, or add a note: a note written at a frame inside the stretch;
- set figures.

Without words, the notes stay. The AI changes the hands, the beam groups, the clefs, the 8va lines and the ornaments
only.

It may not write a note outside the stretch. The hard limits hold in every case: a beam group has at most 8 notes, no
note stands four or more ledger lines above its staff, and there is no 15ma in the bass clef. An 8va in the bass clef
is allowed (implementation 04-7): a hand changes to its other clef only for a passage of 5 columns or more, and a
shorter stretch stays in the hand's own clef with ledger lines or an octave line (8va in the bass clef, 8vb in the
treble clef). The app draws that rule on every sheet, whatever the AI writes.

### The checks

The reply goes through the checker (`check_answer`), then the beam check (`beam_floor`). A reply that fails gets the
problems as the next message, and the AI answers again: at most 3 replies (`MAX_CHECKS`). When no reply passes, the
stretch stays as it was. Without words, a reply that leaves a note out is refused. With words, the notes inside the
stretch may be left out and added.

When the answer passes, `splice` puts the stretch into the sheet. The clefs and the armadura in force after the
stretch come back at its end. The user's marks stay on their notes.

### What is stored

The run is one step of undo. It stores:

- the hands of the sheet in `notes.pmn`: the notes the AI left out are removed, and the notes it added are written;
- the sheet in `sheet.f1`, and the record's `stretches` list: the start, the end, the user's words and the cost of
  each stretch the AI wrote again. The page shows these passages as their own segments;
- for a stretch of one hand, only the figures of the AI's hand are set as by hand. The other hand's figures are not
  the AI's.

The message at the end of the run:

| Result | What the user reads |
|---|---|
| The stretch is written | No message: the passage shows the new sheet |
| No reply passed the checks | "The AI could not write this stretch again. It stays as it was." |
| The notes changed while the AI worked | "The notes changed while the AI worked. The stretch stays as it was." |
| Stopped by the user | "You stopped the AI..." and Revert takes it back |

### Batches

With more than one batch, the stretch is cut into batches of about the same time, at places that no beam group crosses
when possible. Each batch sees the batches before it, as written. A batch that fails keeps its notes; the rest go on.
The whole is one step of undo. The sheet shows the batches while the dialog is open.

### What the user can not do here

- A stretch of one hand cannot change the other hand.
- A stretch cannot reach past its frames: the AI writes inside the stretch only.
- The run does not start while another run works on the part (409): "The AI is already enhancing this sheet."

## Limits

- The audio does not change: a note added is a note of the part's notes, the audio is the same.
- A run whose notes changed while the AI worked is not stored: the sheet stays as it was.

## Where to look deeper

- [whole-run.md](whole-run.md): the whole run, the same panel, Stop and Revert
- [README.md](README.md): the AI in the app, the kinds of run, the model and the cost
- [documentation/services/backend/ai-runs.md](../../documentation/services/backend/ai-runs.md), section 7: the
  functions, the constants and the route of a stretch
- [levels.md](levels.md) and [level-run.md](level-run.md): a level of one hand, the way to make it easier
