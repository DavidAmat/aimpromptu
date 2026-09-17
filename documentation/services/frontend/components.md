> Context: [context/frontend/README.md](../../../context/frontend/README.md) ·
> [context/frontend/pages.md](../../../context/frontend/pages.md)

# The component tree: where each piece lives

`aitu-frontend/src/`. React 19, TypeScript, Vite, MUI. The sheet itself is drawn by
`@aimpromptu/grid-notation` — see [grid-notation.md](grid-notation.md).

---

## 1. Routes and shell

`layout/routes.ts` is the single place every URL is written. Nothing hardcodes a path: navigation,
the top bar and the Playground tab strip all read from it.

| Section | Path | Page |
|---|---|---|
| YouTube to Audio | `/youtube` | `pages/YouTubePage.tsx` |
| **Playground** | `/playground` | `layout/PlaygroundLayout.tsx` |
| · Upload / Input | `/playground/input` | `pages/playground/InputPage.tsx` |
| · Piano Roll | `/playground/piano-roll` | `pages/playground/PianoRollPage.tsx` |
| · Notes Falling | `/playground/notes-falling` | `pages/playground/NotesFallingPage.tsx` |
| · Piano Sheet | `/playground/rhythm` | `pages/playground/RhythmPage.tsx` |
| Piano Library | `/library` | `pages/LibraryPage.tsx` |
| Performance view | `/library/play/:id` | `pages/PerformancePage.tsx` |

The tab order is the order of the work: bring a piece in, look at how it was actually played, then
name the figures and write the sheet. The two visual views sit between input and the sheet because
that is when they are useful — they are how you check the transcription before committing to
reading it.

`state/WorkingArtifactProvider.tsx` holds the piece the Playground tabs share, in
`sessionStorage`, so switching tabs does not lose it.

---

## 2. The sheet

`pages/playground/RhythmPage.tsx` is the largest file in the app and it is the product: look at
where the notes keep landing, say what one of those piles is, and read the result.

| Component | Role |
|---|---|
| `components/time/PeakPlot.tsx` | The distribution of gaps. Click a bar to name it. |
| `components/time/TimeScoreView.tsx` | The staff. Owns the renderer instance, the playhead, selection and the range handles. |
| `components/time/ScorePlayer.tsx` | Play the recording under the sheet. |
| `components/time/ScorePdfDialog.tsx` | Paper size, margins, title, and a preview of the real pages. |
| `components/common/FloatingBar.tsx` | Save / Remove all / PDF, floating over the sheet. |
| `components/common/ToolboxDialog.tsx` | The draggable shell both toolboxes use. |
| `components/notes/NoteSelectionToolbox.tsx` | Everything you can say about picked notes. |
| `components/notes/PendingRemovalsBar.tsx` | Staged deletions, with Save and Discard. |

**`TimeScoreView` passes the figures straight through.** It does not work out what a note should be
called from how many columns it covers, because a column is a slice of time and says nothing about
note values. That is the whole point of the model: position and figure are two separate numbers.

**The floating bar exists because of a real failure.** A long piece went unsaved simply because the
button was past every stave. The bar follows the reader down the page and can be dragged, put away
and brought back.

**Both toolboxes open beside what they are about.** Selecting notes — click, ⌘-click, or a rubber
band — opens the note toolbox; shift-dragging across the column numbers opens the frames toolbox,
which is about a *stretch of time* rather than about notes. A stretch carrying an edit draws two
corner marks in its own colour, so it can be seen without being selected.

**Each toolbox can hand its selection to the other.** `ToolboxDialog` takes a `headerAction`, one
control in the title bar beside the close button: **Select frames** on the note toolbox marks the
stretch from the first picked note to the last, and **Select notes** on the frames toolbox picks
every note that begins inside the stretch on the hands **Applies to** names. Both go through the
renderer's own `setSelection` / `clearSelection` rather than through page state, so the far panel
opens, is placed and takes the cursor to the music exactly as a click would. Neither raises
`clearSelectionsAt` — that drops *both* selections, which is one half too much here.

**The playhead follows the music only while the recording is sounding.** A scrub drag sweeps the
line through a hundred staves in a second, and the page chasing it made the gesture impossible to
finish. `followPlayhead` gates it; the stave index is still recorded while not following, so
resuming does not jump.

---

## 3. The two visual views

`pages/playground/PianoRollPage.tsx` and `NotesFallingPage.tsx`, both drawn from
`GET /matrix/{uuid}/events` — the notes in the engine's own seconds. **Neither asks for a tempo or a
resolution**, and a rectangle is as long as the note was actually held.

| Module | Role |
|---|---|
| `piano/Piano.tsx`, `piano/keyPositions.ts` | The 88-key SVG keyboard, both orientations |
| `playback/usePlayback.ts` | The transport: original audio or synthesised piano |
| `playback/PlaybackTransport.tsx`, `PlayerToolbar.tsx` | The controls |
| `playback/ProgressBar.tsx` | **One scrub bar for every page**, with a draggable handle |
| `playback/playedNotes.ts`, `noteVisuals.ts` | Which notes are sounding; how a rectangle is drawn |
| `playback/useSpacebarPlay.ts` | Space plays and pauses, standing down inside a text field |
| `hooks/useNoteSelection.ts`, `useStagedRemovals.ts` | Picking notes; staging a deletion |
| `hooks/useElementSize.ts` | The measured pixel box the SVG viewBox uses |

**The canvas selects; the scrub bar seeks.** One surface, one meaning — that is what lets a click on
a rectangle mean "this note" without also jumping the recording somewhere nobody asked for. On the
sheet, a **double-click on ground that answers to nothing else** (the strip above the top stave, the
gaps between systems, the margins) is the seek, because a single click there already means nothing.

**The SVG is measured, not stretched.** It used to declare a viewBox in keyboard units and stretch
it with `preserveAspectRatio="none"`, so the two axes scaled by different amounts and every note
name came out squashed — no font size could have fixed it. The viewBox is the element's real pixel
box now: one unit is one pixel, text is undistorted, and a 2 px border is 2 px.

---

## 4. Input, audio and editing

| Directory | Contents |
|---|---|
| `components/audio/` | `AudioUpload`, `AudioRecorder`, `LiveLevelBars`, `WaveformView`, `WaveformRangeSelector`, `AudioLibraryList` |
| `components/input/` | `TranscriptionSettings` (engine and time resolution), `ComposeNewPiece` |
| `components/editing/` | `RangeRerecordPanel` (Epic 11), `ComposePassagePanel` (Epic 13), `useClickTrack` |
| `audio/` | `useRecorder` (MediaRecorder), `time.ts` (`mm:ss.cc`) |

`TranscriptionSettings` has **two fields**: the engine and the time resolution. There is no BPM and
no granularity, because neither exists.

`ComposeNewPiece` is a fourth source on Upload / Input beside upload, record and the audio library.
It is the only entry point with no recording behind it, so it takes the page on its own.

---

## 5. Library and printing

| Module | Role |
|---|---|
| `pages/LibraryPage.tsx` | Browse, tag, filter; playground version management |
| `components/library/PlaylistSection.tsx` | Playlists, ordering, playing mode |
| `pages/PerformancePage.tsx` | Read-only performance view with overlay pills |
| `library/loadPerformanceScore.ts` | Fetch the score payload and the saved rhythm together |
| `print/scorePdf.ts`, `drawPage.ts`, `pdf.ts`, `opentype.ts` | The PDF writer |

Detail on the PDF in [score-pdf.md](score-pdf.md).

---

## 6. The API client

`src/api/`, one module per backend router, re-exported from `api/index.ts` so components have a
single import path:

```ts
import { timeScoreApi, matrixApi, editingApi } from "../api";
```

| Module | Router |
|---|---|
| `client.ts` | `API_BASE`, `request`, `upload`, `ApiError` |
| `audio.ts` | `/audio` |
| `matrix.ts` | `/matrix` |
| `timeScore.ts` | `/time` — the largest, and the mirror of `schemas/time_matrix.py` |
| `editing.ts` | `/audio/{uuid}/edits` |
| `library.ts` | `/library` |
| `youtube.ts` | `/youtube` |
| `scores.ts` | `/scores`, `/sequence` — the text-notation MVP |

`hooks/useProgress.ts` consumes the SSE transcription stream.

---

## 7. The UI kit

`src/ui/`: `PageContainer`, `SectionCard`, `Pill`, `TabBar`, `Placeholder`, `theme.ts`,
`palette.ts`, `timestamps.ts`.

The theme is **light and pinned**. It was reversed from dark on 2026-07-27 after a real failure: on
the original dark ground a struck matrix note drawn in `grays.ink` was invisible against a
`grays.ink` background. The `surface` tokens exist so a view cannot assume a ground again. Colour
definitions: [color-palette.md](../../../context/colors/color-palette.md).

Timestamps are `mm:ss.cc` everywhere and never wrap —
[timestamps.md](../../../context/frontend/timestamps.md).

---

## 8. Removed with the VexFlow stack

Stated so nobody looks for them. `PianoSheet`, `ScoreStack`, `SequenceComposer`, `LayoutControls`,
`ScoreSheet`, `renderScore`, `KeySignaturePanel`, `OctavePanel`, `GridScore`, `MatrixGrid`,
`music/matrixToNotation.ts`, `music/notes.ts`, `music/gridNotation.ts` and `music/handMap.ts` are all
gone, along with the `components/notation/` and `components/matrix/` folders.

The spacing controls those needed have no equivalent: the score re-wraps at a fixed size rather than
being scaled, and zoom lives in the renderer's own chrome.

What survives under `music/` is `types.ts` (matrix contracts mirrored from `schemas/matrix.py`),
`noteNames.ts`, `granularities.ts` and `renderOverrides.ts`.

---

## 9. Checks

```bash
cd aitu-frontend
npm run lint          # eslint .
npm run build         # tsc -b && vite build
npm run check:render  # draw a real score headlessly in jsdom
npm run check:note-names  # what the note toolbox calls a note, against how the sheet spells it
```

`check:render` exists because a notation renderer fails loudly at draw time and **silently at layout
time**. A wrong option name throws and you see it; a score that draws no noteheads, or loses a hand,
or stops beaming, renders a blank-looking page with no error at all. Neither typecheck nor lint can
see either one.

It draws a real schema 2.0 envelope and hands the renderer each note's printed figure, the same way
`TimeScoreView` does, so it guards the path the app actually uses. 26 checks.

It was broken from P6.9 until 2026-09-13: its fixture was still a 1.x `tempoBpm` / `granularity`
envelope built for `GridNotationEditor`, and the package had refused it since the 1.x reader was
deleted. Nothing said so, which is the failure mode this check exists to prevent, one level up.

---

## 10. Where to look deeper

- [grid-notation.md](grid-notation.md) — how the sheet is actually drawn, and the stale-`dist` trap
- [score-pdf.md](score-pdf.md) — the PDF writer
- [../backend/endpoints.md](../backend/endpoints.md) — what the API client calls
- [../backend/rhythm-and-annotations.md](../backend/rhythm-and-annotations.md) — what the toolboxes save
