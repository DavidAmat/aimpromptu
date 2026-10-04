# The flow page

The flow page (**Piece** in the top bar) takes a piece from its audio to its piano sheet in five
steps, one tab each: **Source, Audio, Notes, Hands, Sheet**. It was built in implementation 08 to
replace the loose Playground tabs as the way into the app: before it, no screen knew which step a
piece had reached, and nothing stopped the user from opening the piano sheet of a piece whose notes
had changed. The code is `aitu-frontend/src/pages/piece/`.

## 1. The route and the tabs

| Address | What opens |
|---|---|
| `/` | Goes to `/piece/new` |
| `/piece/new` | The Source tab alone, for a new piece |
| `/piece` | The working piece (the one the Playground tabs share), or a new one |
| `/piece/<uuid>` | The step the piece reached (`resume` of `GET /pieces/{uuid}/status`) |
| `/piece/<uuid>/<step>` | That step: `source`, `audio`, `notes`, `hands` or `sheet` |

The tabs are enabled from the backend's status answer, never from the page's own guess
([backend/pieces-and-revisions.md](../backend/pieces-and-revisions.md)). Each tab shows the state of
its step as an icon (a tick for ready, a spinner for running, a warning for stale, an empty circle for
missing). A tab that is not enabled is greyed, and its tooltip says what is missing ("Predict hands
first"). A step typed in the address that is not enabled opens the step the piece reached instead.
The user can always return to an earlier tab.

Opening a piece from the library goes to its furthest ready step: a piece with a piano sheet opens on
Sheet, a piece that was only transcribed opens on Notes, a new audio opens on Audio.

## 2. Save, and leaving a tab

Nothing is written before the user presses **Save**. A tab with unsaved edits shows a pencil on its
tab, and the floating bar carries **Save**. Any navigation inside the app (another tab, the top bar,
the back button) asks first: **Stay**, **Discard** or **Save and continue**. Closing the browser tab
shows the browser's own warning. Each save sends the revision it was made from, so an edit made
elsewhere in the meantime is refused with a message and **Reload the notes**, instead of being
overwritten.

## 3. The tabs

**1. Source.** The audio library (opens a piece where it was left), a YouTube URL (the download runs
as a job with a progress bar, about 4 s for a 2-minute video) and an upload. Both new ways open the
Audio tab.

**2. Audio.** The waveform of the original audio on a canvas, with zoom down to single 10 ms time
frames and an overview strip. The user selects a part and presses **Delete** to cut it from the
selected region; **Restore** puts a cut back; undo and redo work. **Play all** jumps over the cuts,
**Play selection** plays the selected frames. The audio file is never copied: a cut is a range of
time frames saved in the piece. **Transcribe** saves first, asks before it replaces notes that are
current, and opens the Notes tab.

**3. Notes.** The piano roll visualization on a canvas: a vertical keyboard on the left, one row per
key, the rectangles on a time axis. While MuScriptor runs, the rectangles appear and grow as the notes
arrive, with a progress bar that says the time elapsed and left, then "Transcribed in 0:26". After
it, the original audio plays with the playhead, and the notes can be edited:

| Gesture | Effect |
|---|---|
| Click, Command-click, a drag on empty space | Select a note, add or remove one, select a band |
| Drag a rectangle; Shift-drag | Move it in time by 10 ms steps; also to another key |
| Drag the left or right edge | Make it shorter or longer |
| Arrow keys (Shift: bigger steps) | Move in time by 10 ms, or by one key (an octave) |
| Double-click on empty space | Add a 250 ms note on that key |
| Delete or Backspace | Delete the selected notes |
| Command-Z, Shift-Command-Z, Command-A, Escape | Undo, redo, select all, clear |
| Press or drag in the time ruler, or on the bar under the roll | Move the playhead |

One key sounds one note at a time: a note moved into the next onset of its key is shortened to it.
The page stays at 60 frames per second with 10,000 rectangles, and during a live stream of 100
messages per second.

**4. Hands.** The same editor, with the rectangles coloured by hand (right hand blue, left hand
green). **Predict hands** runs the hand split with a real progress bar (about 1 s for a 3-minute
piece) and shows the answer as unsaved changes. **To Right** and **To Left** (keys R and L) move the
selected notes to the other hand; the filter shows both hands or one, the other faint. A note the
split could not place stays red, and a counter in the toolbar goes through them one at a time. A
hand given by the quick rule to an added note has a dashed border. **Save** ticks the tab and
enables the Sheet tab.

**5. Sheet.** The Playground's piano sheet page (`RhythmPage`) with every tool it has, given the
piece by the flow page. A stale sheet (the notes or the hands changed after it was saved) opens with
a banner and is not drawn until the user presses **Write the sheet**; **Save** then makes it current
again. A hand moved on the piano sheet redraws it in about 250 to 270 ms on a piece of 3 to 4
minutes.

## 4. Timings

Measured on 2026-10-01 with `npm run time:flow`, through the whole flow, on the RTX 4090:

| Piece | Length | Piece in | First note | Notes saved | Predict hands | First piano sheet |
|---|---|---|---|---|---|---|
| Superestrella, uploaded | 3:09 | 0.2 s | 0.3 s | 27 s | 0.9 s | 0.6 s |
| The Winner Takes It All, from the library | 5:56 | 0.2 s | 0.2 s | 52 s | 2.4 s | 1.0 s |
| A new YouTube URL | 2:21 | 3.8 s (download) | 0.3 s | 21 s | 1.4 s | 0.6 s |

## 5. What changed in the rest of the app

The flow page is the entry point. The Playground keeps **Upload / Input** (without an engine choice:
MuScriptor is the only engine), **Notes Falling** and **Piano Sheet**. Its old **Piano Roll** tab was
removed in Phase 9 of implementation 08 (decision Q-4), because the Notes and Hands tabs replace it;
`/playground/piano-roll` opens the flow page.

## Where to look deeper

- The component tree and every file: [`documentation/services/frontend/components.md`](../../documentation/services/frontend/components.md)
- The routes and the shell: [pages.md](pages.md)
- The backend side of the steps: [backend/pieces-and-revisions.md](../backend/pieces-and-revisions.md),
  [backend/muscriptor.md](../backend/muscriptor.md)
- The piano sheet itself: [rendering.md](rendering.md), [annotations.md](annotations.md)
- The plan and the phase reports:
  [`implementations/08-new-algorithm-notes-detection-muscriptor/`](../implementations/08-new-algorithm-notes-detection-muscriptor/README.md)
