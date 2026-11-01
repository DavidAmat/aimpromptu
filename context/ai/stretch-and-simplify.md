# A stretch and Simplify

Two runs of the AI that change part of a sheet, not the whole song. **A stretch** writes one passage again, from the
user's words. **Simplify** makes one hand (or both) easier to read and play, over the whole song, by leaving out
and adding a few notes. Both are background jobs: the page shows the change as it is written, and each one ends as
one step of undo.

The whole song is on [whole-run.md](whole-run.md). The code of these runs is in
[documentation/services/backend/ai-runs.md](../../documentation/services/backend/ai-runs.md), section 7 (a stretch)
and section 8 (Simplify).

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
note stands four or more ledger lines above its staff, and there is no 8va in the bass clef.

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

## Simplify

Simplify is the AI making one hand easier to read and play, over the whole song, with the rules of simplicity only.
The hands, the beam groups, the clefs and the figures are decided and stay. The AI only chooses notes to **leave out**
and notes to **add**.

### How it is reached now

The dialog no longer offers the Simplify run without a level: its docstring says "the older Simplify run without a
level is no longer offered here". Making a hand simpler is now **a level of that hand** (`levels.md`, `level-run.md`).
The run is still in the code: the route `POST /sheet/{uuid}/llm/simplify` with `{hand: left | right | both}`, and the
job `start_simplify`. The dialog does not call it.

The rest of this section tells the run as the code has it.

### The batches

The song is cut into batches of one hand (or both): 24 to 32 seconds of music each, at most 300 onsets (`SIMPLIFY_MS`,
`SIMPLIFY_ONSETS`). A batch ends after a pause of that hand. Each batch sees:

- every change made before it, with its reason (`so_far`): the batches repeat each other's choices;
- the earlier passage most like it, as simplified, with its changes (`like_before`: the same keys, in runs of 4
  columns, at least 30 % of the batch);
- the last 8 seconds of the previous batch, as simplified (`SIMPLIFY_CONTEXT_MS`);
- the places the app finds to check (`places`): the far notes of quick chords and the broken octaves.

### The rules

The prompt has the rules of simplicity only (`simple.1` to `simple.4` in `prompt/frames/instructions.md`):

- simple.1: a passage that repeats one pattern (octaves, chords, single notes, a bass and chord figure) is written
  the same way every time;
- simple.2: a quick note or chord just before a main note of the hand, that makes the hand jump far, keeps only the
  notes near the main note;
- simple.3: the notes keep their place: no note moves to another frame, and no pitch changes its name, except a name
  that the earlier passage like it also changes at the same place;
- simple.4: change little.

### The answer

The AI answers the change lines only, one per note: `# leave out f120 G2: why` or `# add f240 D1: why`, or the one
line `# no change`. The checker (`check_simplify`) refuses:

- a note left out that is not a note of the target;
- a note added where its hand plays no note of the target, or that is not within an octave of a note of its column,
  or that does not have the name of a note of that column or of the pattern around it;
- more than a tenth of the target's notes changed (and at least 4 in a small batch);
- a name changed where the earlier passage like it has no new note at the same place.

A refused reply gets the problems as the next message, at most 3 replies. A batch that still fails keeps its notes. An
error that stops the requests (no credits, no network) stops the rest of the batches; the batches done stay.

### What is stored

The run is one step of undo, stored at the end (`apply_simplify`):

- the notes left out are removed in `notes.pmn`, and the notes added are written there;
- the sheet is laid again on those notes: the beam groups are cut and the clefs fitted around the changed notes;
- `Record.simplified` lists each run: the hand, the notes added, the notes left out, the cost, what was written, and
  the change lines.

The job's last message says what happened (the summary field `simplify`):

| `simplify` | What the user reads |
|---|---|
| `ok` | "The AI added N notes and left out M notes in the right hand." |
| `none` | "The AI found nothing to simplify in the right hand." |
| `failed` | "The AI could not simplify the sheet. It stays as it was." |
| `stale` | "The notes changed while the AI worked. The sheet stays as it was." |

## Limits

- Simplify does not move a note to the other hand: each hand stays as it is, and the AI changes only its notes.
- The audio does not change in either run: a note added is a note of the part's notes, the audio is the same.
- A run whose notes changed while the AI worked is not stored: the sheet stays as it was.

## Where to look deeper

- [whole-run.md](whole-run.md): the whole run, the same panel, Stop and Revert
- [README.md](README.md): the AI in the app, the kinds of run, the model and the cost
- [documentation/services/backend/ai-runs.md](../../documentation/services/backend/ai-runs.md), sections 7 and 8: the
  functions, the constants and the routes of a stretch and of Simplify
- [levels.md](levels.md) and [level-run.md](level-run.md): a level of one hand, the way to simplify it now
