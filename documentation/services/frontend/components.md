> Context: [context/frontend/README.md](../../../context/frontend/README.md) ·
> [context/frontend/pages.md](../../../context/frontend/pages.md) ·
> [context/frontend/flow-page.md](../../../context/frontend/flow-page.md)

# The component tree: where each piece lives

`aitu-frontend/src/`. React 19, TypeScript, Vite, MUI. The sheet itself is drawn by
`@aimpromptu/grid-notation`, see [grid-notation.md](grid-notation.md).

---

## 1. Routes and shell

`layout/routes.ts` is the single place every URL is written (`ROUTES`, the patterns, `LAB_TABS`,
`LEGACY_REDIRECTS`). Nothing hardcodes a path. `App.tsx` holds the route table.

| Section | Path | Page |
|---|---|---|
| (start) | `/` | redirects to `/projects` |
| **Projects** | `/projects` | `pages/ProjectsPage.tsx` |
| · new project | `/projects/new` | `pages/piece/PiecePage.tsx` with the Source step only |
| · a project | `/projects/:id` | `PiecePage.tsx` + `PieceResume.tsx`: opens the step the project reached |
| · one step | `/projects/:id/<step>` | `PiecePage.tsx` + `SourceTab`, `AudioTab`, `NotesTab`, `HandsTab` or `SheetTab` |
| · Notes Falling | `/projects/:id/notes-falling` | `PiecePage.tsx` + `pages/piece/NotesFallingPage.tsx` |
| **Lab** | `/admin/lab/<tab>` | `layout/LabLayout.tsx` and `pages/video/` |
| (old paths) | `/piece/...`, `/video/...`, `/youtube`, `/playground/...`, `/library...` | `layout/LegacyRedirect.tsx`, until Phase 15 |
| (development only) | `/dev/roll-bench` | `pages/dev/RollBenchPage.tsx`, lazy, only when `import.meta.env.DEV` |

`<step>` is one of `PIECE_STEPS` in `api/pieces.ts`: `source`, `audio`, `notes`, `hands`, `sheet`.
`ROUTES.project(id, step?)` builds the address. Until Phase 3 the id of a project is the uuid of its
piece.

**The shell** (implementation 02, plan section 6.2): `layout/AppLayout.tsx` renders `ui/AppShell`
with `ui/Sidebar` (the logo, **Search**, Projects, Lab under Admin, and the user menu at the bottom,
a placeholder with **Keyboard shortcuts** until Phase 4). The sidebar is open on the list pages and
closed inside a project and under 900 px. `⌘K` opens `layout/SearchDialog.tsx` from anywhere;
`layout/ShortcutsDialog.tsx` lists the shortcuts.

`main.tsx` creates a **data router** (`createBrowserRouter`) with one route that renders `App`'s
route table. It exists for one reason: React Router's `useBlocker`, which the project page needs to
ask before a reader leaves a step with unsaved changes, only works with a data router. It also gives
the theme `defaultMode="light"`.

`state/WorkingArtifactProvider.tsx` holds the working piece in `sessionStorage`. The project page
sets it when it loads a project; the sheet reads its `frameMs` from it.

---

## 2. The page of a project

One project, five steps in the order of the work: Source, Audio, Notes, Hands, Sheet. What each step
means for the reader is in [flow-page.md](../../../context/frontend/flow-page.md). This section
lists where the code is.

### 2.1 The page and its tabs

| File | Role |
|---|---|
| `pages/piece/PiecePage.tsx` | The page: loads the audio and `GET /pieces/{uuid}/status`, draws the header (back arrow, title, the step tabs, the `⋯` menu with Notes Falling), redirects a step that is not enabled, holds the leave dialog (**Stay**, **Discard**, **Save and continue**, a `ConfirmDialog`) and the `beforeunload` warning |
| `pages/piece/pieceContext.ts` | What every tab shares: `usePiece()` (the piece, its status, `refresh()`), `stepStatus()`, and `useUnsavedChanges(summary, {save, discard})` |
| `pages/piece/PieceResume.tsx` | `/projects/:id`: follows the backend's `resume` |
| `ui/StepTabs.tsx` | The step tabs, each with a dot for its state (filled ready, a spinner running, amber stale or unsaved, a ring missing) and the reason as a tooltip; `data-step` and `data-state` on each tab for the checks |
| `components/piece/stepLabels.ts` | The names of the five steps |
| `components/piece/StepProgress.tsx` | A short job in progress: label, bar, seconds taken |
| `api/pieces.ts` | `piecesApi`: `status`, `notes`, `patchNotes`, `predictHands`; the types `PieceStatus`, `StepStatus`, `PieceNotes` |

The page enables its tabs from the status answer only. It never works out staleness itself: the
backend compares the revisions and answers every step at once.

A tab that is not enabled is greyed and ignores the press. It is not a disabled MUI tab, because a
disabled element receives no pointer events and its tooltip ("Predict hands first.") would never
show.

### 2.2 Source and Audio

| File | Role |
|---|---|
| `pages/piece/SourceTab.tsx` | A new project: the drop zone for an audio file, **Paste a YouTube link** with **Audio** / **Video** (`POST /youtube/jobs` as a job, or `POST /video/download` then Lab). An existing project: where its audio came from |
| `pages/piece/AudioTab.tsx` | The waveform full width, cuts, undo and redo, the floating bar of icon actions with **Save** (`PUT /audio/{uuid}/cuts`), **Transcribe** on the top row. `data-selection`, `data-view` and `data-cuts` on its root are read by `check:flow` |
| `components/audio/CutWaveform.tsx` | Two stacked canvases (waveform, cuts and selection below; the playhead alone above) and an overview strip |
| `components/audio/waveformPaint.ts` | The painters of `CutWaveform` |
| `audio/frameView.ts` | The window of time frames on screen: zoom, pan, whole view |
| `audio/cuts.ts` | The cut rules, the same as the backend's `normalize_cuts`; pure functions |
| `audio/useCutPlayer.ts` | Plays the audio and jumps over the page's current cuts, or plays the frames selected |

The waveform comes from one request, `GET /audio/{uuid}/frames/peaks`: the lowest and highest
sample of every 10 ms time frame. Every zoom level is then drawn from memory, and every pixel sits
on the same axis as the cuts.

### 2.3 Notes and Hands: the canvas editor

The Notes and Hands tabs are one editor. `NotesTab.tsx` and `HandsTab.tsx` are one line each:
`<NotesEditor step="notes" />` and `<NotesEditor step="hands" />`.

| File | Role |
|---|---|
| `pages/piece/NotesEditor.tsx` | The editor page: live view, playback, every gesture as an undo step, **Save**, the primary action on the top row (**Continue to Hands**, **Continue to Sheet**), and on the Hands step the floating toolbox with **Predict hands**, the hand filter, **To right** / **To left** (keys R and L) |
| `components/notes/PianoRollCanvas.tsx` | The piano roll visualization: the vertical keyboard, one row per key, the rectangles; modes `live`, `edit`, `view` |
| `components/notes/rollPaint.ts` | The painters: the lower canvas (rows, grid, ruler, keyboard, rectangles of the visible range) and the upper canvas (playhead, lit keys, sounding notes, band) |
| `components/notes/RollTimeBar.tsx` | The bar under the roll: the progress bar while the piece is transcribed, the scrub bar afterwards |
| `notes/rollNotes.ts` | `RollNotes`: the notes in typed arrays, one array per field, with an index by onset and one by key |
| `notes/rollView.ts` | Where things are on the canvas: time axis, key rows, zoom, snap to 10 ms |
| `notes/liveFeed.ts` | `LiveFeed`: the queue of stream messages, drained once per animation frame, and the frontier |
| `notes/useLiveTranscription.ts` | Follows the running transcription's progress stream into the feed |
| `notes/noteEdits.ts` | The edits as overrides on the saved notes; `toOperations` turns them into the `PATCH /pieces/{uuid}/notes` operations |
| `hooks/followJob.ts` | Follows one job to its end from a button (**Predict hands**) |
| `hooks/useEditHistory.ts` | Undo and redo, shared with the Audio tab and the sheet |

**Why a canvas.** The old Piano Roll was SVG, one React element per note, rebuilt many times per
second during playback. The editor keeps the notes in typed arrays and paints them directly. React
renders the canvas only when the page changes something (the selection, a saved edit, a mode).
The live stream, the growing rectangles and the playhead are painted from one animation loop. The
measured result (`npm run bench:roll`): 60 frames per second with 10,000 rectangles, and no dropped
frame at 100 stream messages per second.

**The keyboard is drawn on the canvas**, one row of the same height per key, so a click on a
rectangle is never ambiguous. The rows show the keys the piece uses, with a small margin.

**Edits are overrides.** The page loads the saved notes once and keeps every change as "the note
with this id, as the page now has it". One undo step is one small map, "unsaved" is a comparison of
two maps, and **Save** sends only the difference.

**The playhead** is moved in the time ruler and on the bar under the roll. A double-click on empty
space adds a note of 250 ms, so it does not move the playhead here.

**Playback** uses `useCutPlayer` with no cuts. Once cuts are saved, the backend serves the edited
audio, which is already in the time of the notes.

**The floating bar is the editor's toolbar** on both steps: Play/Pause, Undo, Redo, Delete, on the
Hands step **To Left**, **To Right** and the count of notes without a hand (with arrows to visit
them one at a time), the selection's Spanish name, **Save**.

### 2.4 Sheet

`pages/piece/SheetTab.tsx` renders `sheet/SheetPage` (section 3) with its `step` prop (`SheetStep`:
the piece, the Sheet step's state and reason, and `onChanged`). The piece comes from the project, a
stale reading is loaded but not drawn until **Write the sheet** (in the stale banner), and
`onChanged` refreshes the status after a save or **Remove all**, so the dot of the step follows.

The page now knows whether the sheet differs from the saved one (`unsaved`, the dot on **Save**), so
a leave dialog like the other steps' is possible; it is not wired yet.

---

## 3. The sheet

`pages/piece/sheet/` is the Sheet step of a project. Implementation 02, Phase 2 split the old
`RhythmPage.tsx` (5,328 lines) into it with no change of behaviour (twelve screenshots identical
byte for byte), then redesigned it to plan section 11. What it does for the reader is
[`context/frontend/annotations.md`](../../../context/frontend/annotations.md) and its three sub pages.

| Module | Role |
|---|---|
| `SheetPage.tsx` | The page: the state the modules share, the requests (default reading, saved reading, sheet, save, Remove all), the effects, the layout (title lines, scrub bar, sheet, floating bar, the toolboxes) |
| `sheetEdits.ts` | The edits model: `SheetEdits` (one value, so undo is one history), `NO_EDITS`, the undo labels, `editsFromSaved` and `savedRhythmOf` (to and from `rhythm.json`) |
| `sheetConstants.ts` | The colours of the keyboards, the tabs of the range toolbox, the figure ladder, small helpers |
| `toolboxPlacement.ts` | Where a toolbox opens, measured from what is drawn |
| `useNoteActions.ts`, `NoteToolbox.tsx` | What the note toolbox knows about the picked notes and its actions; the panel |
| `useRangeActions.ts`, `RangeToolbox.tsx` | The same for a marked stretch; the panel with its tabs, Speed among them |
| `SheetToolbox.tsx` | The sheet toolbox: Title, Key, Figures, Layout |
| `SheetFloatingBar.tsx` | Play, undo, redo, sheet toolbox, Record, Print, Save with its unsaved dot, `⋯`; the messages of a refused save and a refused move |
| `PianoToolboxes.tsx` | The keyboard under the playhead, and the decoration keyboard |

| Shared component | Role |
|---|---|
| `components/time/TimeScoreView.tsx` | The staff. Owns the renderer instance, the playhead, selection and the range handles |
| `components/time/ScorePlayer.tsx` | Plays the recording; `compact` draws only the scrub bar (the Sheet step) |
| `components/time/ScorePdfDialog.tsx` | Paper size, margins, title, and a preview of the real pages |
| `components/time/PeakPlot.tsx` | The plot of gaps; left only in the compose and re-record panels, which Phases 8 and 9 replace |
| `ui/Toolbox.tsx`, `ui/FloatingBar.tsx` | The draggable panel and the floating bar every step uses |

**The sheet is drawn on arrival.** `SheetPage` asks for the saved reading and for
`GET /time/{uuid}/default-reading` (the highest pile of gaps of the reading's hand, called a negra)
at the same time, and draws as soon as both are answered, so the defaults of a first write (the key
with the fewest accidentals, then the octave brackets in that key, taken from the first build's
`onKeySuggestion` / `onOttavaSuggestion`) never land on a reader's own key. After that, any change of
the page edits, the main figure or the speed changes asks for the sheet again after 400 ms.

**Unsaved is an identity.** Every edit makes a new `SheetEdits` value and undo puts the old one
back, so `edits.state !== cleanEdits` (the value saved or loaded) is exactly "the page is not what was
saved".

**The stage of `TimeScoreView` is a block at normal zoom.** As an inline-block it took the width of
the drawing in it, so a narrower window never reached the renderer's resize watch and the lines kept
their length, cut off at the right. It is an inline-block only while magnified.

**`TimeScoreView` passes the figures straight through.** It does not work out what a note should be
called from how many columns it covers, because a column is a slice of time and says nothing about
note values. That is the whole point of the model: position and figure are two separate numbers.

**The floating bar exists because of a real failure.** A long piece went unsaved simply because the
button was past every stave. The bar follows the reader down the page and can be dragged, hidden
and shown again. It keeps itself inside the window when its width changes, and wraps into two rows
on a phone.

**Both toolboxes open beside what they are about.** Selecting notes (click, ⌘-click, or a rubber
band) opens the note toolbox; a click above the staves opens the range toolbox (titled *Frames*),
which is about a *stretch of time* rather than about notes. A stretch carrying an edit draws two
corner marks in its own colour, so it can be seen without being selected.

**Each toolbox can hand its selection to the other.** `Toolbox` takes a `headerAction`, one
control in the title bar beside the close button: *Select the frames of these notes* on the note
toolbox marks the stretch from the first picked note to the last, and *Select the notes in this
stretch* on the range toolbox picks every note that begins inside it on the staves in scope. Both use the
renderer's own `setSelection` / `clearSelection` rather than through page state, so the far panel
opens, is placed and takes the cursor to the music exactly as a click would. Neither raises
`clearSelectionsAt`, which drops *both* selections and is one half too much here.

**The playhead follows the music only while the recording is sounding.** A scrub drag sweeps the
line through a hundred staves in a second, and the page chasing it made the gesture impossible to
finish. `followPlayhead` gates it; the stave index is still recorded while not following, so
resuming does not jump.

---

## 4. Notes Falling

`pages/piece/NotesFallingPage.tsx`, inside the page of a project (the project in the address), drawn from `GET /matrix/{uuid}/events`: the notes in the
engine's own seconds. **It asks for no tempo and no resolution**, and a rectangle is as long as the
note was actually held.

| Module | Role |
|---|---|
| `piano/Piano.tsx`, `piano/keyPositions.ts` | The 88-key SVG keyboard, both orientations (also on the sheet) |
| `playback/usePlayback.ts` | The transport: original audio or synthesised piano |
| `playback/PlaybackTransport.tsx`, `PlayerToolbar.tsx` | The controls |
| `playback/ProgressBar.tsx` | **One scrub bar** for Notes Falling and the sheet, with a draggable handle |
| `playback/playedNotes.ts`, `noteVisuals.ts` | Which notes are sounding; how a rectangle is drawn |
| `playback/useSpacebarPlay.ts` | Space plays and pauses, except inside a text field (also on the Notes and Hands tabs) |
| `hooks/usePlayedNotes.ts` | Loads the notes of the working piece and the waveform of its recording |
| `hooks/useNoteSelection.ts`, `useStagedRemovals.ts` | Picking notes; staging a deletion |
| `components/notes/NoteSelectionToolbox.tsx` | The panel for picked notes: **Delete** and **Put back** only |
| `components/notes/PendingRemovalsBar.tsx` | Staged deletions, with Save and Discard |
| `hooks/useElementSize.ts` | The measured pixel box the SVG viewBox uses |

`NoteSelectionToolbox` had hand buttons and a walk through the notes without a hand while the old
Piano Roll used it. Those moved to the Hands tab with the piano roll, so the panel now holds only
**Delete** and **Put back**. Neither writes at once: the floating **Save** bar commits.

**The canvas selects; the scrub bar seeks.** One surface, one meaning: that is what lets a click on
a rectangle mean "this note" without also jumping the recording somewhere nobody asked for. On the
sheet, a **double-click on ground that answers to nothing else** (the strip above the top stave, the
gaps between systems, the margins) is the seek, because a single click there already means nothing.

**The SVG is measured, not stretched.** It used to declare a viewBox in keyboard units and stretch
it with `preserveAspectRatio="none"`, so the two axes scaled by different amounts and every note
name came out squashed; no font size could have fixed it. The viewBox is the element's real pixel
box now: one unit is one pixel, text is undistorted, and a 2 px border is 2 px.

---

## 5. Audio and editing

| Directory | Contents |
|---|---|
| `components/audio/` | `LiveLevelBars`, `WaveformView`, `WaveformRangeSelector` (the re-record and compose panels); `CutWaveform` and `waveformPaint` (the Audio step, section 2.2) |
| `components/editing/` | `RangeRerecordPanel` (Epic 11), `ComposePassagePanel` (Epic 13), `useClickTrack` |
| `audio/` | `useRecorder` (MediaRecorder), `time.ts` (`mm:ss.cc`); `cuts.ts`, `frameView.ts`, `useCutPlayer.ts` (the Audio step) |
| `components/ProgressBanner.tsx` | The progress of a long job of the re-record and compose panels |

---

## 6. Printing, and what Play mode will start from

| Module | Role |
|---|---|
| `library/loadPerformanceScore.ts` | Fetch the score payload and the saved rhythm together. Kept for Play mode (Phase 11); nothing calls it now |
| `print/scorePdf.ts`, `drawPage.ts`, `pdf.ts`, `opentype.ts` | The PDF writer |

Detail on the PDF in [score-pdf.md](score-pdf.md).

---

## 7. The API client

`src/api/`, one module per backend router, re-exported from `api/index.ts` so components have a
single import path:

```ts
import { timeScoreApi, matrixApi, piecesApi } from "../api";
```

| Module | Router |
|---|---|
| `client.ts` | `API_BASE`, `request`, `upload`, `buildUrl`, `ApiError` |
| `audio.ts` | `/audio`, including `list` (with `updatedAt`), `cuts`, `saveCuts`, `framePeaks`, `fileUrl` |
| `matrix.ts` | `/matrix`, including `transcribe`, `activeJob`, `progressUrl` |
| `pieces.ts` | `/pieces`: the status of a project's steps, its notes and hands |
| `timeScore.ts` | `/time`, the largest, and the mirror of `schemas/time_matrix.py` |
| `editing.ts` | `/audio/{uuid}/edits` |
| `youtube.ts` | `/youtube`, including `startDownload` (`POST /youtube/jobs`) |
| `video.ts`, `frameExamples.ts` | `/video`, `/frame-examples` (Lab) |

**`API_BASE` is `/api` by default**: a path on the page's own address. The Vite server passes it to
the backend without the prefix (`vite.config.ts`: `http://127.0.0.1:8765`, or `AITU_API_PROXY`,
which `compose.yaml` sets to the `backend` service). The JSON, the audio files and the progress
stream then share one port. `VITE_AITU_API_URL` still points the page at another backend directly.

`hooks/useProgress.ts` consumes the Server-Sent Events (SSE) progress stream of a job and returns
its `done` payload as `result`. `hooks/followJob.ts` does the same as one `await`, for a button
that starts a short job and uses its answer.

---

## 8. The shared components and the tokens

`src/ui/` (implementation 02, plan sections 7.2 to 7.4). Pages draw these things only through them,
so the same job looks the same everywhere.

| Component | What it draws |
|---|---|
| `AppShell`, `PageBody` | The sidebar beside the page; the side gutters and the 960 px width of a list page (`wide` for a canvas) |
| `Sidebar` | Open (260 px, words) or closed (64 px, icons with tooltips); groups with a heading; the footer |
| `PageHeader` | The title on the left, the primary action on the right, an optional back arrow and a middle row (the step tabs). No subtitle |
| `Section` | A group inside a page: an optional small title and its controls, no description, no border (it replaced `SectionCard`) |
| `IconAction` | An icon button with its tooltip, which is also its name; the shortcut after the title; a tooltip that says why when disabled |
| `PillButton` | `primary` (black), `secondary` (white, grey border), `quiet`, `danger`; `busy` shows a spinner |
| `Segmented` | One of 2 to 4 options, as one rounded group |
| `ListRow`, `RowMenu` | A row: title (truncated, full on hover), status and meta in fixed columns, the `⋯` menu |
| `DataTable` | Sticky header, sortable columns, rows per page, sized to its content |
| `EmptyState` | One line, and the action that creates the first one |
| `ConfirmDialog` | The confirm button repeats the action ("Delete project"); **Cancel**; an optional third choice |
| `Toolbox`, `FloatingBar` | The draggable toolbox and the floating bar, white with the one shadow; the bar wraps on a narrow screen |
| `MiniPiano` | 88 keys at half size, to pick one key; Spanish names on hover; arrows move by a semitone or an octave |
| `FigurePicker` | The figure icons (`FigureGlyph`) as a `Segmented`, the Spanish name in the tooltip |
| `StepTabs` | The steps of a project, section 2.1 |
| `Pill`, `TabBar` | A small toggle chip; a tab strip that follows the address (the Lab tabs) |
| `timestamps.ts`, `progress.ts`, `relativeTime.ts` | Tabular figures that never wrap; the 520 px width of a progress bar on its own; "2 h ago", "yesterday", "3 Oct" |

`MiniPiano` and `FigurePicker` are built in Phase 1 and used from Phase 7 (transposition).

**The tokens** are in `tokens.ts`: the colours of the page, light and dark, the type scale (13, 14,
16, 20, 28 px), the radii (12 for inputs, 16 for floating things, a pill for buttons) and the one
shadow. `theme.ts` builds the MUI theme from them, with both schemes as CSS variables; the app opens
in the light one until the theme choice of Phase 4. Drawing code that cannot read the theme (a
canvas, an SVG) imports `ui`, the scheme in use. **`palette.ts` keeps only the colours of the
music**: the hands, the selection, the piano roll, the waveform, the marks on notes and video
frames. The one dark panel is the piano roll visualization (`semantic.roll`). Colour definitions:
[color-palette.md](../../../context/colors/color-palette.md).

**The face is Geist Sans**, self-hosted in `public/fonts/geist.woff2` (SIL OFL 1.1) and preloaded by
`index.html`. Montserrat stays for the note names on the rectangles, Bravura for the music.

Timestamps are `mm:ss.cc` everywhere and never wrap:
[timestamps.md](../../../context/frontend/timestamps.md).

---

## 9. Removed

Stated so nobody looks for them.

**In implementation 02, Phase 1** (decision Q-4): the Playground (`layout/PlaygroundLayout.tsx`,
`pages/playground/InputPage.tsx`; Notes Falling and the sheet moved to `pages/piece/`), the YouTube
to Audio page (`pages/YouTubePage.tsx`), the old Piano Library (`pages/LibraryPage.tsx`,
`pages/PerformancePage.tsx`, `components/library/`, `library/playId.ts`, `api/library.ts`), the
text-notation MVP client (`api/scores.ts`, `music/types.ts`), the old shell (`layout/VideoLayout.tsx`,
`layout/BackendStatus.tsx`, the "API online" chip), the old kit (`ui/PageContainer.tsx`,
`ui/SectionCard.tsx`, `ui/Placeholder.tsx`), `pages/piece/PieceIndex.tsx`, and the components the
new Source step replaced (`AudioLibraryList`, `AudioUpload`, `YouTubeDownload`, `AudioRecorder`,
`TranscriptionSettings`, `ComposeNewPiece`, `SaveBar`, the old `StepTabs`).

**With the old Piano Roll (implementation 08, Q-4):** `pages/playground/PianoRollPage.tsx`,
`components/notes/RollNote.tsx` (one memoized SVG rectangle per note) and
`components/notes/HandlessStrip.tsx` (the strip of red marks for notes without a hand). The Notes
and Hands tabs replace them. Also gone in implementation 08: `pages/piece/LaterStepTab.tsx`, the
placeholder of the Notes, Hands and Sheet tabs before Phases 7 and 8.

**With the VexFlow stack:** `PianoSheet`, `ScoreStack`, `SequenceComposer`, `LayoutControls`,
`ScoreSheet`, `renderScore`, `KeySignaturePanel`, `OctavePanel`, `GridScore`, `MatrixGrid`,
`music/matrixToNotation.ts`, `music/notes.ts`, `music/gridNotation.ts` and `music/handMap.ts` are all
gone, along with the `components/notation/` and `components/matrix/` folders.

The spacing controls those needed have no equivalent: the score re-wraps at a fixed size rather than
being scaled, and zoom lives in the renderer's own chrome.

What survives under `music/` is `noteNames.ts`, `figures.ts`, `granularities.ts` and `renderOverrides.ts`.

---

## 10. Checks

```bash
cd aitu-frontend
npm run lint              # eslint .
npm run build             # tsc -b && vite build
npm run check:render      # draw a real score headlessly in jsdom
npm run check:note-names  # what the note toolbox calls a note, against how the sheet spells it
npm run check:history     # undo and redo reverse exactly one press
npm run check:geometry    # the video piano overlay, against the backend's fixture
npm run check:cuts        # the Audio tab's cuts follow the backend's rules; playback jumps over them
npm run check:notes       # the Notes tab's typed arrays, live feed and edits
```

These need the running app (`make up` from the repository root). Each works on temporary copies or
uploads and deletes them at the end, so the library is never changed:

```bash
npm run check:flow    # a project walked in a headless Chromium, every step, live transcription included
npm run time:flow     # the whole flow timed on three temporary pieces (upload, library copy, YouTube)
npm run bench:roll    # the Notes tab at 10,000 rectangles and at 100 stream messages per second
npm run bench:sheet   # a hand move on the Sheet tab, timed part by part
```

`check:flow` exists because the page of a project is mostly gestures on a canvas and navigation between
tabs, which no unit check reaches. It takes about 2 minutes with the transcription
(`--no-transcribe` skips it). `bench:roll` opens `/dev/roll-bench`, so it needs a development build.

`check:render` exists because a notation renderer fails loudly at draw time and **silently at layout
time**. A wrong option name throws and you see it; a score that draws no noteheads, or loses a hand,
or stops beaming, renders a blank-looking page with no error at all. Neither typecheck nor lint can
see either one.

It draws a real schema 2.0 envelope and hands the renderer each note's printed figure, the same way
`TimeScoreView` does, so it guards the path the app actually uses.

It was broken from P6.9 until 2026-09-13: its fixture was still a 1.x `tempoBpm` / `granularity`
envelope built for `GridNotationEditor`, and the package had refused it since the 1.x reader was
deleted. Nothing said so, which is the failure mode this check exists to prevent, one level up.

---

## 11. Where to look deeper

- [flow-page.md](../../../context/frontend/flow-page.md): Projects and the steps of a project
- [grid-notation.md](grid-notation.md): how the sheet is actually drawn, and the stale-`dist` trap
- [score-pdf.md](score-pdf.md): the PDF writer
- [../backend/endpoints.md](../backend/endpoints.md): what the API client calls
- [../backend/rhythm-and-annotations.md](../backend/rhythm-and-annotations.md): what the toolboxes save
