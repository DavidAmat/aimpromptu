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
changed. While a job works on a project (a transcription, a video read, or the AI writing its sheet,
implementation 03, Phase 5) a small spinner stands before the title; its tooltip says which, and the
list looks again every 5 s until it ends. A project whose sheet the AI enhanced has the green AI mark there
(the AImpromptu logo, also the icon of **Enhance with AI**, tooltip "Enhanced with AI"; implementation 04, prompt
04-2); a project with notes the AI has not enhanced has the same mark faint grey ("Not enhanced with AI yet"). The same mark stands before each song of My library (green when the AI
enhanced one of its versions) and each version of a song (`components/piece/AiMark.tsx`). The status **Editing** is not about the AI: it is
the edit copy of a version of My library, until **Save to library** or **Discard changes**. The whole row opens the project on that step. The `⋯` menu of a row has **Open**,
**Duplicate**, **Export**, **Rename**, **Folders…**, **Info**, **Play** (Play mode, once it reaches its Sheet step)
and **Delete** (with a confirmation).

**The list's pills and folders.** The Projects page has three pills (**Folders**, **All**, **Filter**), folders of
My projects, a metadata filter, and the **Info** dialog of a row. All of it is in
[folders-and-metadata.md](folders-and-metadata.md).

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
the end. A change of the files changes the audio, so once the notes are out of date the step says
"The audio changed after the notes were made. Transcribe it again.", with **Open Audio**. **Remove**
says that the file's part of the audio and its cuts go. A project keeps at least one file, and a file
cannot go if the files left would be cut completely (restore a part of them first). A video project's Source step only says where the video
came from.

**2. Audio.** The waveform of the audio, full width, with zoom down to single 10 ms time frames and
an overview strip. Its tools are icon actions in a floating bar, each with a tooltip: play (jumping
over the cuts), play the selection, cut, **Only keep the selected part** (it cuts everything else at once),
restore, undo, redo, the zooms, **Add audio at the end**, and **Save** (with **Discard the changes**). A cut is a range
of time frames; the audio file is never changed. **Add audio** puts
another file at the end: the waveform then shows the files end to end, every second file on a
grey band, each named, with a dashed line at each join, and a cut may cross a join. With several
files a panel on the left lists them by name with their kept length: a click selects that file's
part of the waveform and zooms to it, so a cut can be made inside one file. Adding a file changes the audio,
so notes made before it are out of date. The primary action saves first and opens the Notes step.
Its label says what it does: **Transcribe** when no notes exist, **Transcribe again** when they do (with
unsaved cuts, **Save and transcribe** and **Save and transcribe again**), and **Show the transcription**
while a transcription runs. Current
notes are replaced only after **Transcribe again?** is confirmed (when nothing is unsaved); the old notes
go to history.

**2. Video** (a project made from a video, in place of Audio). Three moments, one thing to do in each:

1. *Preparing the video*: its frames are taken out once, with a thin bar, as the step opens.
2. *Fit the piano*: a frame from the middle of the video and a rectangle to drag onto the keys; the
   keys are found when it settles, and **Save the piano** keeps them.
3. *The video with the piano on it*, played with its own audio, **Fit the piano again**, and
   **Read notes** (**Read notes again** once the notes exist): one job that measures how fast the roll falls (once per fitting), reads the notes
   and writes them into the project, then opens the Notes step. It takes about a third of the
   video's length (61 s for 3:09). The notes appear when it ends, not one by one (Q-8 of the plan).

The video reader's development views (the detection, the measurements, correcting single notes)
stay in **Lab** ([lab.md](lab.md)), for the master user.

**3. Notes.** The piano roll on a canvas: a vertical keyboard on the left, one row per key, the
rectangles on a time axis. While MuScriptor runs, the rectangles appear and grow as the notes
arrive, with a progress bar. After it, the audio plays with the playhead, and the notes can be
edited. The floating bar has play, **Follow the playhead** (on by default: the roll scrolls with the playhead; moving the view by hand turns it off, and Play turns it on again), undo, redo, delete and **Save**; **Continue to Sheet** is on the
top row. The gestures, in short (the code: `pages/piece/NotesEditor.tsx` and `components/notes/PianoRollCanvas.tsx`):

| Gesture | Effect |
|---|---|
| Click, Command-click, a drag on empty space | Select a note, add or remove one, select a band |
| Drag a rectangle; Shift-drag | Move it in time by 10 ms steps; Shift-drag also moves it to another key |
| Drag the left or right edge | Make it shorter or longer |
| Left and Right arrows (Shift: 100 ms) | Move the selection in time by 10 ms |
| Up and Down arrows (Shift: an octave) | Move the selection by one key |
| Double-click on empty space | Add a 250 ms note on that key |
| Delete or Backspace | Delete the selected notes |
| Command-Z, Shift-Command-Z, Command-A, Escape | Undo, redo, select all, clear |
| Press or drag in the time ruler, or on the bar under the roll | Move the playhead |

One key sounds one note at a time: a note moved into the next onset of its key is shortened to it.
The roll is built for about 10,000 rectangles; the bench page `pages/dev/RollBenchPage.tsx` runs that case
(its speed is not measured in this page).

**Hand colours** (a switch in the Notes step, on by default): blue for a note of the right hand, green for
the left, red for a note with no hand. The hands are written with the sheet, so until the piece has hands
every note has one colour (the switch is off, and disabled). The choice is kept in this browser.

**4. Sheet.** The new piano sheet, drawn by the backend and shown by the Sheet page ([sheet-page.md](sheet-page.md)):
the title with the AI mark, the buttons, the floating toolbox, the zoom and the recording. It is on screen at once.
The AI writes the sheet only when the user presses **Enhance with AI**; the page starts no run by itself. A sheet the
AI wrote keeps the green AI mark for good, and its button then reads **Enhance it again with AI**. The tools of the
sheet are in [annotations.md](annotations.md), the AI's runs in [`../ai/`](../ai/README.md), and the info button in
[folders-and-metadata.md](folders-and-metadata.md). The Sheet step is *running* while the AI writes, *ready* once a
sheet is stored (`sheet.f1`, or an old `sheet.json`), and *missing* otherwise; it is never *stale* any more. An old
saved sheet (`sheet.json`) is still read for its key, its renamed figure and its marks; nothing writes one.

**Then, Save to library.** Once the sheet is ready, **Save to library** asks **Artist**, **Song** and
**Version name**, moves the project into My library (its audio written again with only the ranges in
use, its video and other temporary files deleted) and opens the song. On an edit copy the dialog
opens on **Replace “<version>”**, with **New version** beside it. The whole flow:
[music-library/private-library.md](../music-library/private-library.md).

## 5. Copy and paste, and From scratch

**Copy** a stretch of any sheet (the range toolbox, the note toolbox, ⌘C; also **Copy this stretch** on a read-only
version of My library) and **Paste** it at the cursor or in place of the marked frames (the floating bar, ⌘V). Its
notes, its marks and its audio come with it, and one **Undo** takes the whole paste back. On the Source step a pasted
passage is a file of its own ("Pasted"). The tools: [annotations-stretches.md](annotations-stretches.md); what the
backend does: [`backend/editing.md`](../backend/editing.md).

**From scratch** makes "Untitled project" and opens its blank sheet. With no audio yet the page has
no step tabs, only the sheet's empty state: **Record a passage** (the page of a new passage,
section 6) and **Paste the copied passage**. Once a passage brings audio, the steps appear and work
as for any project.

## 6. Recording in Sheet

**Record this passage** (the record icon of the range toolbox) opens the page of the marked stretch,
`/projects/<id>/passages/<passageId>`: the **Current** (the stretch as it is) and the **Proposal** (a
take recorded or added from a file, written in the passage's key and figure). **Promote** puts the
take into the song, fitted into the window or in place of the whole passage, as one step of the
sheet's undo. **Record a passage at the end**
(the floating bar) and **Record a passage** (a blank sheet) open a new passage at the end. The whole page: [recording-in-sheet.md](recording-in-sheet.md).

## 7. From other projects, and the parts

**From other projects** makes a project of passages of other projects, joined **Sequential** or
under a **Subheader**. A project of several parts lists them in the **Parts** panel beside its Sheet step, where
each part can be renamed (**Rename**), moved (**Move up**, **Move down**) and joined to the one before it
(**Join with**). A part is split off from the range toolbox (**Start a new part here**). The page and the songs
playlists: [playlists.md](playlists.md).

## 8. Timings

The measures of the steps (implementation 08, and the new Sheet step of implementation 03) are kept in
[`archive/project-timings.md`](../archive/project-timings.md).

## Where to look deeper

- The component tree and every file: [`documentation/services/frontend/components.md`](../../documentation/services/frontend/components.md)
- The routes and the shell: [pages.md](pages.md)
- The routes of the backend: [`documentation/services/backend/endpoints.md`](../../documentation/services/backend/endpoints.md)
- The bundle, the timeline and the `.aitu` file: [07-database.md](../07-database.md),
  [`paths-and-data.md`](../../documentation/services/backend/paths-and-data.md)
- The pills, the folders, the metadata and the info dialog: [folders-and-metadata.md](folders-and-metadata.md)
- The backend side of the steps: [backend/pieces-and-revisions.md](../backend/pieces-and-revisions.md),
  [backend/muscriptor.md](../backend/muscriptor.md)
- The piano sheet itself: [rendering.md](rendering.md), [annotations.md](annotations.md)
- Recording in Sheet: [recording-in-sheet.md](recording-in-sheet.md)
- From other projects, the parts, the playlists: [playlists.md](playlists.md)
- The plan: [`implementations/02-private-web-app/02-plan.md`](../implementations/02-private-web-app/02-plan.md) sections 8 and 10
