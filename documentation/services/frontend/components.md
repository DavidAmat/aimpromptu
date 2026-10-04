> Context: [context/frontend/README.md](../../../context/frontend/README.md) ·
> [context/frontend/pages.md](../../../context/frontend/pages.md) ·
> [context/frontend/flow-page.md](../../../context/frontend/flow-page.md)

# The component tree: where each piece lives

`aitu-frontend/src/`. React 19, TypeScript, Vite, MUI. The sheet itself is drawn by
`@aimpromptu/grid-notation`, see [grid-notation.md](grid-notation.md).

---

## 1. Routes and shell

`layout/routes.ts` is the single place every URL is written. Nothing hardcodes a path: navigation,
the top bar and the Playground tab strip all read from it. `App.tsx` holds the route table.

The top bar, in this order: **Piece**, **YouTube to Audio**, **Video to Notes**, **Playground**,
**Piano Library** (`TOP_SECTIONS`). **Piece** is first because a piece now starts there.

| Section | Path | Page |
|---|---|---|
| (start) | `/` | redirects to `/piece/new` |
| **Piece** (the flow page) | `/piece` | `pages/piece/PieceIndex.tsx`: the working piece, or `/piece/new` |
| · new piece | `/piece/new` | `pages/piece/PiecePage.tsx` with the Source tab only |
| · a piece | `/piece/:uuid` | `PiecePage.tsx` + `PieceResume.tsx`: opens the step the piece reached |
| · one step | `/piece/:uuid/<step>` | `PiecePage.tsx` + `SourceTab`, `AudioTab`, `NotesTab`, `HandsTab` or `SheetTab` |
| YouTube to Audio | `/youtube` | `pages/YouTubePage.tsx` |
| Video to Notes | `/video/*` | `layout/VideoLayout.tsx` and `pages/video/` |
| **Playground** | `/playground` | `layout/PlaygroundLayout.tsx` |
| · Upload / Input | `/playground/input` | `pages/playground/InputPage.tsx` |
| · Notes Falling | `/playground/notes-falling` | `pages/playground/NotesFallingPage.tsx` |
| · Piano Sheet | `/playground/rhythm` | `pages/playground/RhythmPage.tsx` |
| · (old Piano Roll) | `/playground/piano-roll` | redirects to `/piece` |
| Piano Library | `/library` | `pages/LibraryPage.tsx` |
| Performance view | `/library/play/:id` | `pages/PerformancePage.tsx` |
| (development only) | `/dev/roll-bench` | `pages/dev/RollBenchPage.tsx`, lazy, only when `import.meta.env.DEV` |

`<step>` is one of `PIECE_STEPS` in `api/pieces.ts`: `source`, `audio`, `notes`, `hands`, `sheet`.
`ROUTES.piece(uuid, step?)` builds the address.

**The Piano Roll tab was removed in implementation 08** (decision Q-4). The Notes and Hands tabs of
the flow page are the piano roll visualization now, with its editor. The old address redirects to
`/piece` so a saved link still opens something useful.

`main.tsx` creates a **data router** (`createBrowserRouter`) with one route that renders `App`'s
route table. It exists for one reason: React Router's `useBlocker`, which the flow page needs to
ask before a reader leaves a tab with unsaved changes, only works with a data router.

`state/WorkingArtifactProvider.tsx` holds the piece the Playground tabs share, in
`sessionStorage`, so switching tabs does not lose it. The flow page sets it when it loads a piece,
so the Playground and the flow page show the same piece.

---

## 2. The flow page

One piece, five tabs in the order of the work: Source, Audio, Notes, Hands, Sheet. What each step
means for the reader is in [flow-page.md](../../../context/frontend/flow-page.md). This section
lists where the code is.

### 2.1 The page and its tabs

| File | Role |
|---|---|
| `pages/piece/PiecePage.tsx` | The page: loads the audio and `GET /pieces/{uuid}/status`, draws the tabs, redirects a step that is not enabled, holds the leave dialog (**Stay**, **Discard**, **Save and continue**) and the `beforeunload` warning |
| `pages/piece/pieceContext.ts` | What every tab shares: `usePiece()` (the piece, its status, `refresh()`), `stepStatus()`, and `useUnsavedChanges(summary, {save, discard})` |
| `pages/piece/PieceIndex.tsx` | `/piece`: the working piece, or a new one |
| `pages/piece/PieceResume.tsx` | `/piece/:uuid`: follows the backend's `resume` |
| `components/piece/StepTabs.tsx` | The numbered tabs with the state icon of each step (ready, running, stale, missing; a pencil while the Notes or Hands tab has unsaved changes) and the reason as a tooltip |
| `components/piece/stepLabels.ts` | The names of the five steps |
| `components/piece/SaveBar.tsx` | The save bar (the `FloatingBar`): what is unsaved, **Discard**, **Save** |
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
| `pages/piece/SourceTab.tsx` | Three ways in: the library (`AudioLibraryList`), YouTube, upload |
| `components/piece/YouTubeDownload.tsx` | Paste a URL; the download runs as a job (`POST /youtube/jobs`) with its progress bar |
| `pages/piece/AudioTab.tsx` | The waveform, cuts, undo and redo, **Save** (`PUT /audio/{uuid}/cuts`), **Transcribe** |
| `components/audio/CutWaveform.tsx` | Two stacked canvases (waveform, cuts and selection below; the playhead alone above) and an overview strip |
| `components/audio/waveformPaint.ts` | The painters of `CutWaveform` |
| `audio/frameView.ts` | The window of time frames on screen: zoom, pan, whole view |
| `audio/cuts.ts` | The cut rules, the same as the backend's `normalize_cuts`; pure functions |
| `audio/useCutPlayer.ts` | Plays the audio and jumps over the page's current cuts (**Play all**), or plays the frames selected (**Play selection**) |

The waveform comes from one request, `GET /audio/{uuid}/frames/peaks`: the lowest and highest
sample of every 10 ms time frame. Every zoom level is then drawn from memory, and every pixel sits
on the same axis as the cuts.

### 2.3 Notes and Hands: the canvas editor

The Notes and Hands tabs are one editor. `NotesTab.tsx` and `HandsTab.tsx` are one line each:
`<NotesEditor step="notes" />` and `<NotesEditor step="hands" />`.

| File | Role |
|---|---|
| `pages/piece/NotesEditor.tsx` | The editor page: live view, playback, every gesture as an undo step, **Save**, and on the Hands step **Predict hands**, **To Left** / **To Right** (keys L and R), the hand filter |
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

`pages/piece/SheetTab.tsx` renders `RhythmPage` (section 3) with an optional `step` prop
(`SheetStep`: the piece, the Sheet step's state and reason, and `onChanged`). Without the prop the
Playground page is unchanged. With it, the piece comes from the flow page, a stale reading is
loaded but not drawn until **Write the sheet**, and `onChanged` refreshes the status after a saved
reading or **Remove all**, so the tab's tick follows.

The Sheet tab does not use `useUnsavedChanges`, because `RhythmPage` does not know whether the
reading on screen differs from the saved one.

---

## 3. The sheet

`pages/playground/RhythmPage.tsx` is the largest file in the app and it is the product: see
where the notes keep landing, say what one of those piles is, and read the result. It is both the
Playground's **Piano Sheet** tab and the flow page's **Sheet** tab.

| Component | Role |
|---|---|
| `components/time/PeakPlot.tsx` | The distribution of gaps. Click a bar to name it. |
| `components/time/TimeScoreView.tsx` | The staff. Owns the renderer instance, the playhead, selection and the range handles. |
| `components/time/ScorePlayer.tsx` | Play the recording under the sheet. |
| `components/time/ScorePdfDialog.tsx` | Paper size, margins, title, and a preview of the real pages. |
| `components/common/FloatingBar.tsx` | Save / Remove all / PDF, floating over the sheet. Also the save bar and toolbar of the flow page. |
| `components/common/ToolboxDialog.tsx` | The draggable shell every toolbox uses. |

**`TimeScoreView` passes the figures straight through.** It does not work out what a note should be
called from how many columns it covers, because a column is a slice of time and says nothing about
note values. That is the whole point of the model: position and figure are two separate numbers.

**The floating bar exists because of a real failure.** A long piece went unsaved simply because the
button was past every stave. The bar follows the reader down the page and can be dragged, hidden
and shown again. It keeps itself inside the window when its width changes.

**Both toolboxes open beside what they are about.** Selecting notes (click, ⌘-click, or a rubber
band) opens the note toolbox; shift-dragging across the column numbers opens the frames toolbox,
which is about a *stretch of time* rather than about notes. A stretch carrying an edit draws two
corner marks in its own colour, so it can be seen without being selected.

**Each toolbox can hand its selection to the other.** `ToolboxDialog` takes a `headerAction`, one
control in the title bar beside the close button: **Select frames** on the note toolbox marks the
stretch from the first picked note to the last, and **Select notes** on the frames toolbox picks
every note that begins inside the stretch on the hands **Applies to** names. Both use the
renderer's own `setSelection` / `clearSelection` rather than through page state, so the far panel
opens, is placed and takes the cursor to the music exactly as a click would. Neither raises
`clearSelectionsAt`, which drops *both* selections and is one half too much here.

**The playhead follows the music only while the recording is sounding.** A scrub drag sweeps the
line through a hundred staves in a second, and the page chasing it made the gesture impossible to
finish. `followPlayhead` gates it; the stave index is still recorded while not following, so
resuming does not jump.

---

## 4. Notes Falling

`pages/playground/NotesFallingPage.tsx`, drawn from `GET /matrix/{uuid}/events`: the notes in the
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

## 5. Input, audio and editing

| Directory | Contents |
|---|---|
| `components/audio/` | `AudioUpload`, `AudioRecorder`, `LiveLevelBars`, `WaveformView`, `WaveformRangeSelector`, `AudioLibraryList`; `CutWaveform` and `waveformPaint` (the Audio tab, section 2.2) |
| `components/input/` | `TranscriptionSettings` (the time resolution), `ComposeNewPiece` |
| `components/editing/` | `RangeRerecordPanel` (Epic 11), `ComposePassagePanel` (Epic 13), `useClickTrack` |
| `audio/` | `useRecorder` (MediaRecorder), `time.ts` (`mm:ss.cc`); `cuts.ts`, `frameView.ts`, `useCutPlayer.ts` (the Audio tab) |
| `components/ProgressBanner.tsx` | The progress of a long job (transcription, YouTube download, re-record) |

`TranscriptionSettings` has **no engine field** since implementation 08: MuScriptor is the only
engine, and the page warns when it is not installed. There is no BPM and no granularity, because
neither exists.

`ComposeNewPiece` is a source on Upload / Input beside upload, record and the audio library. It is
the only entry point with no recording behind it, so it takes the page on its own. **Record** and
**Compose** are only on the Playground; the flow page's Source tab has the library, YouTube and
upload. The Input page shows one line pointing to the **Piece** page.

---

## 6. Library and printing

| Module | Role |
|---|---|
| `pages/LibraryPage.tsx` | Browse, tag, filter; playground version management |
| `components/library/PlaylistSection.tsx` | Playlists, ordering, playing mode |
| `pages/PerformancePage.tsx` | Read-only performance view with overlay pills |
| `library/loadPerformanceScore.ts` | Fetch the score payload and the saved rhythm together |
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
| `audio.ts` | `/audio`, including `cuts`, `saveCuts`, `framePeaks`, `fileUrl` |
| `matrix.ts` | `/matrix`, including `transcribe`, `activeJob`, `progressUrl` |
| `pieces.ts` | `/pieces`: the flow page's status, notes and hands |
| `timeScore.ts` | `/time`, the largest, and the mirror of `schemas/time_matrix.py` |
| `editing.ts` | `/audio/{uuid}/edits` |
| `library.ts` | `/library` |
| `youtube.ts` | `/youtube`, including `startDownload` (`POST /youtube/jobs`) |
| `video.ts`, `frameExamples.ts` | `/video`, `/frame-examples` (Video to Notes) |
| `scores.ts` | `/scores`, `/sequence`, the text-notation MVP |

**`API_BASE` is `/api` by default**: a path on the page's own address. The Vite server passes it to
the backend without the prefix (`vite.config.ts`: `http://127.0.0.1:8765`, or `AITU_API_PROXY`,
which `compose.yaml` sets to the `backend` service). The JSON, the audio files and the progress
stream then share one port. `VITE_AITU_API_URL` still points the page at another backend directly.

`hooks/useProgress.ts` consumes the Server-Sent Events (SSE) progress stream of a job and returns
its `done` payload as `result`. `hooks/followJob.ts` does the same as one `await`, for a button
that starts a short job and uses its answer.

---

## 8. The UI kit

`src/ui/`: `PageContainer`, `SectionCard`, `Pill`, `TabBar`, `Placeholder`, `theme.ts`,
`palette.ts`, `timestamps.ts`, `progress.ts`.

`progress.ts` gives a progress bar that stands on its own a width of at most 520 px. A bar that
belongs to something wide (the bar under the piano roll visualization, which is also its time axis)
keeps that width.

The theme is **light and pinned**. It was reversed from dark on 2026-07-27 after a real failure: on
the original dark ground a struck matrix note drawn in `grays.ink` was invisible against a
`grays.ink` background. The `surface` tokens exist so a view cannot assume a ground again. The one
dark panel is the piano roll visualization (`semantic.roll`), as in the MuScriptor examples. Colour
definitions: [color-palette.md](../../../context/colors/color-palette.md).

Timestamps are `mm:ss.cc` everywhere and never wrap:
[timestamps.md](../../../context/frontend/timestamps.md).

---

## 9. Removed

Stated so nobody looks for them.

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

What survives under `music/` is `types.ts` (matrix contracts mirrored from `schemas/matrix.py`),
`noteNames.ts`, `figures.ts`, `granularities.ts` and `renderOverrides.ts`.

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
npm run check:flow    # the flow page walked in a headless Chromium, every tab, live transcription included
npm run time:flow     # the whole flow timed on three temporary pieces (upload, library copy, YouTube)
npm run bench:roll    # the Notes tab at 10,000 rectangles and at 100 stream messages per second
npm run bench:sheet   # a hand move on the Sheet tab, timed part by part
```

`check:flow` exists because the flow page is mostly gestures on a canvas and navigation between
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

- [flow-page.md](../../../context/frontend/flow-page.md): the flow page, step by step
- [grid-notation.md](grid-notation.md): how the sheet is actually drawn, and the stale-`dist` trap
- [score-pdf.md](score-pdf.md): the PDF writer
- [../backend/endpoints.md](../backend/endpoints.md): what the API client calls
- [../backend/rhythm-and-annotations.md](../backend/rhythm-and-annotations.md): what the toolboxes save
