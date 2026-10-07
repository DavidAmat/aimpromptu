# Projects and the steps of a project

A **project** is the work of turning a song into a piano sheet: the bundle of its audio, its piano
matrix notation and its metadata ([app context](../app/01-app-context.md)). Work in progress lives
in the user's **Personal Vault**, which is the **Projects** page; a project takes a song from its
audio to its piano sheet in five steps: **Source, Audio, Notes, Hands, Sheet**.

The steps were built in implementation 08 as the "flow page". Implementation 02 moved them to
`/projects/:id/:step` (Phase 1), gave projects their own storage (Phase 3, the project bundle of
[07-database.md](../07-database.md)) and their own routes, **add audio**, the video as a step, and
the `.aitu` export (Phase 5). The code is `aitu-frontend/src/pages/ProjectsPage.tsx` and
`aitu-frontend/src/pages/piece/`.

## 1. The Projects page

One row per project, the most recently changed first: the title ("Untitled project" until it has
one), the step it reached ("Transcribing" or "Reading" while a job works on it), and when it
changed. The whole row opens the project on that step. The `⋯` menu of a row has **Open**,
**Duplicate**, **Export**, **Rename**, **Notes Falling** (once it has notes) and **Delete** (with a
confirmation).

Until Phase 6 gives the Private Library its pages, the projects of the user's library (the 30 songs
of the seed list, for the master user) are listed under the vault, in a group **In my library**.

**New project** opens a menu:

| Choice | What it does |
|---|---|
| **From source** | `/projects/new`: the Source step of a new project |
| **From scratch** | Not built yet (Phase 8): shown disabled |
| **From other projects** | Not built yet (Phase 10): shown disabled |
| **Import** | Takes a `.aitu` file and opens the new project it makes |

The list is one request, `GET /projects?layer=vault&layer=private`, with the step of every row in
it. The backend keeps each project's step in its table and works it out again only after a part
changed ([backend/pieces-and-revisions.md](../backend/pieces-and-revisions.md) section 0).

## 2. Duplicate, export, import

- **Duplicate** makes a copy in the Personal Vault, "<title> (copy)", with new ids. The audio files
  are shared, not copied; history, edit sessions and a video are not copied.
- **Export** saves `<title>.aitu`: a zip of the project bundle (`project.json`, and for each part
  `notes.pmn`, `sheet.json`, `timeline.json`) and the audio files it uses. Nothing derived, nothing
  temporary, no history.
- **Import** makes a new project in the importer's Personal Vault from a `.aitu` file, with new ids
  and the same title. Each audio file is checked against the hash in its name, and a file that is
  not a project, or a damaged one, is refused with nothing left behind. Export, import and export
  again give the same notes, sheet and audio (a test checks it).

## 3. The routes and the step tabs

| Address | What opens |
|---|---|
| `/` | Goes to `/projects` |
| `/projects` | The Personal Vault (above) |
| `/projects/new` | The Source step alone, for a new project |
| `/projects/<id>` | The step the project reached (`resume` of `GET /pieces/{id}/status`) |
| `/projects/<id>/<step>` | That step: `source`, `audio`, `notes`, `hands` or `sheet` |
| `/projects/<id>/notes-falling` | Notes Falling, from the project's `⋯` menu (until Play mode, Phase 11) |

The old addresses (`/piece/...`) redirect to these. The header of a project is the back arrow to
Projects, the title, the step tabs, and the `⋯` menu (**Notes Falling**, **Export**). The tabs are
enabled from the backend's status answer, never from the page's own guess. Each tab has a small dot
for its state: filled when ready, a spinner while running, amber when out of date or unsaved, an
empty ring when not done. A tab that is not enabled is grey, and its tooltip says what is missing
("Predict hands first"). A step typed in the address that is not enabled opens the step reached
instead. A project with no audio yet opens on Source, with every other step closed.

Nothing is written before the user presses **Save**. A step with unsaved edits shows an amber dot,
and leaving it asks **Stay**, **Discard** or **Save and continue**. Each save sends the revision it
was made from, so an edit made elsewhere in the meantime is refused instead of overwritten. The
sidebar is closed inside a project, so the piano roll and the piano sheet have the width.

## 4. The steps

**1. Source.** On a new project: one drop zone for an **audio or a video file** (**Choose file**),
and one field **Paste a YouTube link** with the choice **Audio** or **Video**. No name is asked for:
the project takes the name of its file or of its video. An audio file and a YouTube link as Audio
open the Audio step (the download is a job with a thin progress bar). A video file or a YouTube link
as Video stores the audio of the video, keeps the video as a temporary file of the project, and
opens the Video step.

On a project that has its audio, the Source step lists its **audio files in the order they play**:
for each, its name (the file's name or the video's title at first), where it came from, its length
and how much of it is cut. A file is dragged by its handle to another place (or moved with **Move
up** and **Move down** in its `⋯` menu), renamed in place (**Rename**), or removed (**Remove**,
with a confirmation; not the last one). Each file keeps its own cuts when the order changes. Below
the list, **Add audio**: drop or choose one or more files, or paste a YouTube link; each is added at
the end. A change of the files changes the audio, so the step then says the notes must be
transcribed again, with **Open Audio**. A video project's Source step only says where the video came
from.

**2. Audio.** The waveform of the audio, full width, with zoom down to single 10 ms time frames and
an overview strip. Its tools are icon actions in a floating bar, each with a tooltip: play (jumping
over the cuts), play the selection, cut, restore, undo, redo, the zooms, **Add audio at the end**,
and **Save**. A cut is a range of time frames; the audio file is never changed. **Add audio** puts
another file at the end: the waveform then shows the files end to end, every second file on a
grey band, each named, with a dashed line at each join, and a cut may cross a join. With several
files a panel on the left lists them by name with their kept length: a click selects that file's
part of the waveform and zooms to it, so a cut can be made inside one file. Adding a file changes the audio,
so notes made before it are out of date. The primary action, **Transcribe**, saves first, asks
before it replaces notes that are current, and opens the Notes step.

**2. Video** (a project made from a video, in place of Audio). Three moments, one thing to do in each:

1. *Preparing the video*: its frames are taken out once, with a thin bar, as the step opens.
2. *Fit the piano*: a frame from the middle of the video and a rectangle to drag onto the keys; the
   keys are found when it settles, and **Save the piano** keeps them.
3. *The video with the piano on it*, played with its own audio, **Fit the piano again**, and
   **Read notes**: one job that measures how fast the roll falls (once per fitting), reads the notes
   and writes them into the project, then opens the Notes step. It takes about a third of the
   video's length (61 s for 3:09). The notes appear when it ends, not one by one (Q-8 of the plan).

The video reader's development views (the detection, the measurements, correcting single notes)
stay in **Lab**, for the master user.

**3. Notes.** The piano roll on a canvas: a vertical keyboard on the left, one row per key, the
rectangles on a time axis. While MuScriptor runs, the rectangles appear and grow as the notes
arrive, with a progress bar. After it, the audio plays with the playhead, and the notes can be
edited. The floating bar has play, undo, redo, delete and **Save**; **Continue to Hands** is on the
top row:

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
The page stays at 60 frames per second with 10,000 rectangles.

**4. Hands.** The same editor, coloured by hand (right hand blue, left hand green), with a floating
toolbox. **Predict hands** is the button beside **Continue to Sheet** (a real progress bar, about 1 s for a 3-minute piece, shown as unsaved
changes), **To right** and **To left** (keys R and L), the filter (**Both**, **Right**, **Left**),
and a counter that goes through the notes the split could not place. **Save** enables the Sheet tab.

**5. Sheet.** The piano sheet (`pages/piece/sheet/SheetPage`), drawn as the step opens: the highest
pile of gaps is a negra, and a first write takes the key with the fewest accidentals and the octave
brackets of high passages ([annotations.md](annotations.md)). A stale sheet opens with a banner and
is not drawn until **Write the sheet**; **Save** makes it current again.

## 5. Timings

Measured with `npm run time:flow` on the RTX 4090 (implementation 08, 2026-10-01; the first piano
sheet measured again in every phase of implementation 02):

| Piece | Length | Piece in | First note | Notes saved | Predict hands | First piano sheet |
|---|---|---|---|---|---|---|
| Superestrella, uploaded | 3:09 | 0.2 s | 0.3 s | 27 s | 0.9 s | 0.6 s |
| The Winner Takes It All, from the library | 5:56 | 0.2 s | 0.2 s | 52 s | 2.4 s | 1.0 s |
| A new YouTube URL | 2:21 | 3.8 s (download) | 0.3 s | 21 s | 1.4 s | 0.6 s |

**Read notes** of a video, measured with `aitu-backend/scripts/bench_video_read.py` (Phase 5) on a
copy of Superestrella's tutorial video (3:09, 1,892 frames, 1,495 notes): 61 s in all, of which
measuring the roll takes about 37 s and reading the notes about 22 s. In the browser, the first
**Read notes** took 66 s and a second one 25.5 s, because the roll is measured once per fitting.

## Where to look deeper

- The component tree and every file: [`documentation/services/frontend/components.md`](../../documentation/services/frontend/components.md)
- The routes and the shell: [pages.md](pages.md)
- The routes of the backend: [`documentation/services/backend/endpoints.md`](../../documentation/services/backend/endpoints.md)
- The bundle, the timeline and the `.aitu` file: [07-database.md](../07-database.md),
  [`paths-and-data.md`](../../documentation/services/backend/paths-and-data.md)
- The backend side of the steps: [backend/pieces-and-revisions.md](../backend/pieces-and-revisions.md),
  [backend/muscriptor.md](../backend/muscriptor.md)
- The piano sheet itself: [rendering.md](rendering.md), [annotations.md](annotations.md)
- The plan: [`implementations/02-private-web-app/02-plan.md`](../implementations/02-private-web-app/02-plan.md) sections 8 and 10
