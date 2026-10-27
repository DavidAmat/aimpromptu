# Projects and the steps of a project

A **project** is the work of turning a song into a piano sheet: the bundle of its audio, its piano
matrix notation and its metadata ([app context](../app/01-app-context.md)). Work in progress lives
in the user's **Personal Vault**, which is the **Projects** page; a project takes a song from its
audio to its piano sheet in four steps: **Source, Audio, Notes, Sheet**. A fifth step, Hands, left the flow in
implementation 03, Phase 5 (the AI decides the hands with the sheet), and its code was removed in Phase 10.

The steps were built in implementation 08 as the "flow page". Implementation 02 moved them to
`/projects/:id/:step` (Phase 1), gave projects their own storage (Phase 3, the project bundle of
[07-database.md](../07-database.md)) and their own routes, **add audio**, the video as a step, and
the `.aitu` export (Phase 5). The code is `aitu-frontend/src/pages/ProjectsPage.tsx` and
`aitu-frontend/src/pages/piece/`.

## 1. The Projects page

One row per project, the most recently changed first: the title ("Untitled project" until it has
one), the step it reached ("Transcribing" or "Reading" while a job works on it), and when it
changed. While a job works on a project (a transcription, a video read, or Sonnet writing its sheet,
implementation 03, Phase 5) a small spinner stands before the title; its tooltip says which, and the
list looks again every 5 s until it ends. A project whose sheet the AI enhanced has the green AI mark there
(the icon of **Enhance with AI**, tooltip "Enhanced with AI"); a project with notes the AI has not enhanced
has the same mark faint and hollow ("Not enhanced with AI yet"). The same mark stands before each song of My library (green when the AI
enhanced one of its versions) and each version of a song (`components/piece/AiMark.tsx`). The status **Editing** is not about the AI: it is
the edit copy of a version of My library, until **Save to library** or **Discard changes**. The whole row opens the project on that step. The `⋯` menu of a row has **Open**,
**Duplicate**, **Export**, **Rename**, **Play** (Play mode, once it reaches its Sheet step) and **Delete** (with a
confirmation).

Finished work is not here: it is in **My library** ([music-library/private-library.md](../music-library/private-library.md),
Phase 6). A copy made there by **Edit** is listed here like any project, says **Editing** (its
tooltip names the version and the song), and its `⋯` adds **Open the song**; its Delete reads
**Discard changes** and leaves the version as it was.

**New project** opens a menu:

| Choice | What it does |
|---|---|
| **From source** | `/projects/new`: the Source step of a new project |
| **From scratch** | A blank piano sheet, "Untitled project", opened on its Sheet step (Phase 8; section 5 below) |
| **From other projects** | `/projects/compose`: passages of other projects, saved as a song or an integrated playlist (Phase 10; [playlists.md](playlists.md)) |
| **Import** | Takes a `.aitu` file and opens the new project it makes |

The list is one request, `GET /projects`, with the step of every row in it. The backend keeps each project's step in its table and works it out again only after a part
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
| `/projects/<id>/<step>` | That step: `source`, `audio`, `notes` or `sheet` (an old `hands` address opens `sheet`) |

The old addresses (`/piece/...`) redirected to these until implementation 02, Phase 15. The header of a project is the back arrow to
Projects, the title, the step tabs, the primary action, and the `⋯` menu (**Play**,
**Export**, and **Discard changes** on an edit copy). The primary action is **Save to library** once
the Sheet step is ready (disabled while a step has unsaved edits), and nothing before.

**A version of My library** opens on the same page **read only** (Phase 6): the title is the song
and the version ("Superestrella (original)"), the back arrow goes to the song, and the one action is
**Edit**. Each step shows what it holds and offers no change: the Source step lists the files
without handles, menus or Add audio; the Audio step plays and zooms (no cut, no Save, no
Transcribe); Notes draws the roll and plays it (no edit, no Save); the
Sheet draws, plays and prints, and nothing on it opens a toolbox. A version with a video shows its
audio, not the Video step. The tabs are
enabled from the backend's status answer, never from the page's own guess. Each tab has a small dot
for its state: filled when ready, a spinner while running, amber when out of date or unsaved, an
empty ring when not done. A tab that is not enabled is grey, and its tooltip says what is missing
("Transcribe first."). A step typed in the address that is not enabled opens the step reached
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
edited. The floating bar has play, **Follow the playhead** (on by default: the roll scrolls with the playhead; moving the view by hand turns it off, and Play turns it on again), undo, redo, delete and **Save**; **Continue to Sheet** is on the
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

Until Sonnet decides them, the notes have no hand colours: the Notes step and Notes Falling show a new
transcription in one colour.

**4. Sheet** (implementation 03, Phase 5). The new piano sheet, without compases, drawn by the backend
(`pages/piece/sheet/frames/`, [rendering.md](rendering.md)). It is on screen at once:

- **A new transcription** goes to Sonnet by itself. The algorithm's sheet is drawn first; Sonnet writes the
  hands and the reading in the background, part by part (about half a minute each). The part at Sonnet looks
  pale, and a part that comes back appears column by column. No text says any of it. At the end the hands are
  saved in the notes, and the sheet is saved beside them (`sheet.f1`); opening it again calls nothing.
- **A project made before Phase 5** keeps its saved hands and shows the algorithm's sheet from them (with the
  key and a renamed figure of its old sheet), and offers **Enhance with AI** on the floating bar (a
  confirmation says it costs about $1 of the monthly credits). On a version of My library the button opens the
  copy that edits it, as **Edit** does, and starts there. The 10 songs Sonnet wrote in implementation 03,
  Phase 4 show Sonnet's sheet.
- **Enhanced with AI.** A sheet the AI wrote (or part of it) carries the green badge **Enhanced with AI** beside
  its title, for good: later changes of the notes or the hands do not remove it, only a new transcription does.
  Its button then reads **Enhance it again with AI**, and the confirmation says a new run may give much the same
  result; a new run that does not finish leaves the sheet the AI wrote before. The page says "AI", not the
  model's name (Sonnet 5.5 today), because the model may change.
- **To hear it**: Play (or Space) plays the recording with a cursor; the notes the cursor reaches are lit; a
  click on the sheet moves the recording there.
- **To edit it**: the tools of [annotations.md](annotations.md); every change is written at once as one step
  of undo.
- **The old sheet** (vexflow-v2) was one press away on the floating bar (**Edit in the old sheet**) until
  implementation 03, Phase 8B, and its code was removed in Phase 10. An old saved sheet (`sheet.json`) is still
  read for its key, its renamed figure and its marks, and nothing writes a new one.

The Sheet step is *running* while the AI writes, *ready* once a sheet is stored (`sheet.f1`, or an old
`sheet.json`), and *missing* otherwise; it is never *stale* any more.

**Then, Save to library.** Once the sheet is ready, **Save to library** asks **Artist**, **Song** and
**Version name**, moves the project into My library (its audio written again with only the ranges in
use, its video and other temporary files deleted) and opens the song. On an edit copy the dialog
opens on **Replace “<version>”**, with **New version** beside it. The whole flow:
[music-library/private-library.md](../music-library/private-library.md).

## 5. Copy and paste, and From scratch

**Copy** a stretch of any sheet: the copy icon of the range toolbox (titled *Frames*) or of the note
toolbox (the frames those notes cover), or ⌘C. A version of My library, which opens read only, still
lets a stretch be marked and offers **Copy this stretch**. **Paste** is on the sheet's floating bar
(its tooltip names what was copied and where it goes) and ⌘V: it puts the passage in **at the
cursor**, or **in place of the marked frames** when a stretch is marked. Its notes, its marks (with
the key and the clefs it had) and its audio come with it; everything after moves later; the sheet is
saved with it, and the cursor stays at the start of the passage. One **Undo** takes the whole paste
back, notes and audio included, and **Redo** puts it again. The copied passage stays in the app's
clipboard across projects and browser tabs. On the Source step a pasted passage is a file of its
own ("Pasted"), between the two halves of the file it was pasted into; on the Audio step its band
is named after where it came from. What the backend does:
[`backend/editing.md`](../backend/editing.md).

**From scratch** makes "Untitled project" and opens its blank sheet. With no audio yet the page has
no step tabs, only the sheet's empty state: **Record a passage** (the page of a new passage,
section 6) and **Paste the copied passage**. Once a passage brings audio, the steps appear and work
as for any project.

## 6. Recording in Sheet

**Record this passage** (the record icon of the range toolbox) opens the page of the marked stretch,
`/projects/<id>/passages/<passageId>`: the **Current** (the stretch as it is) and the **Proposal** (a
take recorded or added from a file, written in the passage's key and figure). **Promote** puts the
take into the song, fitted into the window or in place of the whole passage, as one step of the
sheet's undo. **Record a passage** on the floating bar and on a blank sheet opens a new passage at
the end. The whole page: [recording-in-sheet.md](recording-in-sheet.md).

## 7. From other projects, and the parts

**From other projects** makes a project of passages of other projects, joined **Sequential** or
under a **Subheader**; a project of several parts lists them beside its Sheet step, where they are
renamed, moved, joined and split. The page, the parts and the songs playlists:
[playlists.md](playlists.md).

## 8. Timings

Measured with `npm run time:flow` on the RTX 4090 (implementation 08, 2026-10-01; the first piano
sheet measured again in every phase of implementation 02):

| Piece | Length | Piece in | First note | Notes saved | Predict hands (gone since implementation 03, Phase 5) | First piano sheet |
|---|---|---|---|---|---|---|
| Superestrella, uploaded | 3:09 | 0.2 s | 0.3 s | 27 s | 0.9 s | 0.6 s |
| The Winner Takes It All, from the library | 5:56 | 0.2 s | 0.2 s | 52 s | 2.4 s | 1.0 s |
| A new YouTube URL | 2:21 | 3.8 s (download) | 0.3 s | 21 s | 1.4 s | 0.6 s |

The Hands step and its column are gone since implementation 03, Phase 5. On the new Sheet step
(`npm run check:frames-sheet -- --live`, 2026-10-25, a 40 s clip of 7 Years): the algorithm's sheet on screen
0.9 s after the step opened, Sonnet's first part back after about 19 s, the whole clip written in 91 s for
$0.18. A whole song takes 4 to 17 minutes and $0.5 to $1.7 (implementation 03, Phase 4).

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
- Recording in Sheet: [recording-in-sheet.md](recording-in-sheet.md)
- From other projects, the parts, the playlists: [playlists.md](playlists.md)
- The plan: [`implementations/02-private-web-app/02-plan.md`](../implementations/02-private-web-app/02-plan.md) sections 8 and 10
