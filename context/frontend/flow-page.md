# Projects and the steps of a project

A **project** is the work of turning a song into a piano sheet. Until Phase 3 of implementation 02
gives projects their own storage, a project is one of today's pieces, and its id is the piece's
audio uuid. **Projects** in the sidebar lists them; a project takes a piece from its audio to its
piano sheet in five steps: **Source, Audio, Notes, Hands, Sheet**.

The steps were built in implementation 08 as the "flow page", to replace the loose Playground tabs as
the way into the app: before it, no screen knew which step a piece had reached, and nothing stopped
the user from opening the piano sheet of a piece whose notes had changed. Implementation 02, Phase 1
moved them to `/projects/:id/:step`, inside the new shell, and restyled the first four steps. This
page becomes `projects.md` in Phase 5, when the three ways to start a project exist. The code is
`aitu-frontend/src/pages/ProjectsPage.tsx` and `aitu-frontend/src/pages/piece/`.

## 1. The routes and the step tabs

| Address | What opens |
|---|---|
| `/` | Goes to `/projects` |
| `/projects` | The list of projects, newest change first, with the step each one reached |
| `/projects/new` | The Source step alone, for a new project (**New project**) |
| `/projects/<id>` | The step the project reached (`resume` of `GET /pieces/{id}/status`) |
| `/projects/<id>/<step>` | That step: `source`, `audio`, `notes`, `hands` or `sheet` |
| `/projects/<id>/notes-falling` | Notes Falling, from the project's `⋯` menu (until Play mode, Phase 11) |

The old addresses (`/piece/...`) redirect to these.

The header of a project is the back arrow to Projects, the title, the step tabs, and the `⋯` menu.
The tabs are enabled from the backend's status answer, never from the page's own guess
([backend/pieces-and-revisions.md](../backend/pieces-and-revisions.md)). Each tab has a small dot
for the state of its step: filled when ready, a spinner while running, amber when out of date or
unsaved, an empty ring when not done yet. A tab that is not enabled is grey, and its tooltip says
what is missing ("Predict hands first"). A step typed in the address that is not enabled opens the
step the project reached instead. The user can always return to an earlier step.

Opening a project from the list goes to its furthest ready step: a project with a piano sheet opens
on Sheet, one that was only transcribed opens on Notes, a new audio opens on Audio.

The sidebar is closed inside a project, so the piano roll and the piano sheet have the width; the
button beside the logo opens it.

## 2. Save, and leaving a tab

Nothing is written before the user presses **Save**. A step with unsaved edits shows an amber dot on
its tab, and the floating bar carries **Save**. Any navigation inside the app (another step, the
sidebar, the back button) asks first: **Stay**, **Discard** or **Save and continue**. Closing the browser tab
shows the browser's own warning. Each save sends the revision it was made from, so an edit made
elsewhere in the meantime is refused with a message and **Reload the notes**, instead of being
overwritten.

## 3. The tabs

**1. Source.** On a new project: one drop zone for an audio file (**Choose file**), and one field
**Paste a YouTube link** with the choice **Audio** or **Video**. No name is asked for: the project
takes the name of its file or of its video. An audio file and a YouTube link as Audio open the Audio
step (the download runs as a job with a thin progress bar, about 4 s for a 2-minute video). A YouTube
link as Video downloads the video and its audio and opens it in **Lab**, where the piano is fitted
and the notes are read; Phase 5 makes those pages steps of the project. On a project that already
has its audio, the step says where the audio came from (the file, or the YouTube link).

**2. Audio.** The waveform of the original audio, full width, with zoom down to single 10 ms time
frames and an overview strip. Its tools are icon actions in a floating bar, each with a tooltip:
play (jumping over the cuts), play the selection, cut the selection (Delete), restore the cuts in
the selection, undo, redo, the zooms, and **Save**. The audio file is never copied: a cut is a range
of time frames saved in the piece. The primary action, **Transcribe**, is on the top row; it saves
first, asks before it replaces notes that are current, and opens the Notes step.

**3. Notes.** The piano roll visualization on a canvas: a vertical keyboard on the left, one row per
key, the rectangles on a time axis. While MuScriptor runs, the rectangles appear and grow as the notes
arrive, with a progress bar that says the time elapsed and left. After it, the original audio plays
with the playhead, and the notes can be edited. The floating bar has play, undo, redo, delete and
**Save**; **Continue to Hands** is on the top row:

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
green). The hand tools are in the floating toolbox. **Predict hands** runs the hand split with a
real progress bar (about 1 s for a 3-minute piece) and shows the answer as unsaved changes.
**To right** and **To left** (keys R and L) move the selected notes to the other hand; the filter
(**Both**, **Right**, **Left**) shows both hands or one, the other faint. A note the
split could not place stays red, and a counter in the toolbar goes through them one at a time. A
hand given by the quick rule to an added note has a dashed border. **Save** ticks the tab and
enables the Sheet tab.

**5. Sheet.** The piano sheet (`pages/piece/sheet/SheetPage`), drawn as soon as the step opens:
the highest pile of gaps is a negra, and a first write takes the key with the fewest accidentals and
the octave brackets of high passages ([annotations.md](annotations.md)). The page is the sheet, a
floating bar and the toolboxes. A stale sheet (the notes or the hands changed after it was saved)
opens with a banner and is not drawn until the user presses **Write the sheet**; **Save** then makes
it current again. A hand moved on the piano sheet redraws it in about 250 to 270 ms on a piece of 3 to 4
minutes.

## 4. Timings

Measured on 2026-10-01 with `npm run time:flow`, through the whole flow, on the RTX 4090:

| Piece | Length | Piece in | First note | Notes saved | Predict hands | First piano sheet |
|---|---|---|---|---|---|---|
| Superestrella, uploaded | 3:09 | 0.2 s | 0.3 s | 27 s | 0.9 s | 0.6 s |
| The Winner Takes It All, from the library | 5:56 | 0.2 s | 0.2 s | 52 s | 2.4 s | 1.0 s |
| A new YouTube URL | 2:21 | 3.8 s (download) | 0.3 s | 21 s | 1.4 s | 0.6 s |

## 5. What changed in the rest of the app

The project is the entry point. The Playground, the YouTube to Audio page and the old Piano Library
were removed in implementation 02, Phase 1 (decision Q-4): a YouTube download is the Source step,
Notes Falling opens from a project, and the video reader's pages are in **Lab**. The Playground's
**Piano Roll** tab had already gone in implementation 08, because the Notes and Hands steps replace
it.

## Where to look deeper

- The component tree and every file: [`documentation/services/frontend/components.md`](../../documentation/services/frontend/components.md)
- The routes and the shell: [pages.md](pages.md)
- The plan of the private web app: [`implementations/02-private-web-app/02-plan.md`](../implementations/02-private-web-app/02-plan.md)
- The backend side of the steps: [backend/pieces-and-revisions.md](../backend/pieces-and-revisions.md),
  [backend/muscriptor.md](../backend/muscriptor.md)
- The piano sheet itself: [rendering.md](rendering.md), [annotations.md](annotations.md)
- The plan and the phase reports:
  [`implementations/01-mvp/08-new-algorithm-notes-detection-muscriptor/`](../implementations/01-mvp/08-new-algorithm-notes-detection-muscriptor/README.md)
