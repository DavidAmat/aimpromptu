# aitu-frontend

React 19 + TypeScript + Vite app. It brings a recording in, shows how it was actually played, and
draws the sheet with `@aimpromptu/grid-notation`, a renderer built for this project, because
nothing off the shelf lays music out on a wall clock.

The app opens on the **flow page** (`/piece`): one piece, five tabs in the order of the work
(Source, Audio, Notes, Hands, Sheet), from the audio to the piano sheet.

**Documentation:** [context/frontend/](../context/frontend/README.md) ·
the flow page: [flow-page.md](../context/frontend/flow-page.md) ·
components: [components.md](../documentation/services/frontend/components.md) ·
rendering: [rendering.md](../context/frontend/rendering.md)

## Run

**In containers** (the usual way), from the repository root:

```bash
make up      # builds if needed, starts the backend (GPU) and this app; open http://localhost:5173
make logs    # follow both
make down    # stop both
```

The frontend container runs the Vite development server on the mounted source folder, so an edit
shows in the browser at once. After a change of `package-lock.json` or of `../../vexflow-v2`, run
`make build` (or `make up`, which rebuilds).

**Natively**, without containers:

```bash
npm install && npm run dev
```

with the backend running on `http://127.0.0.1:8765`. `make serve` from the repository root starts
both natively.

**The backend address.** The page calls `/api`, and the Vite server passes it to
`http://127.0.0.1:8765`, or to `AITU_API_PROXY`, which the container sets to the backend service
(`vite.config.ts`). `VITE_AITU_API_URL` points the page at a backend directly instead.

## npm scripts

| Script | What it does |
|---|---|
| `npm run dev` | The Vite development server on port 5173 |
| `npm run build` | Typecheck (`tsc -b`) and the production build |
| `npm run preview` | Serve the production build |
| `npm run lint` | ESLint over the project |
| `npm run check:render` | Draw a real score headlessly in jsdom: layout failures are silent otherwise |
| `npm run check:history` | Undo reverses exactly one press and returns to where it started |
| `npm run check:note-names` | The note toolbox names a note the way the sheet spells it |
| `npm run check:geometry` | The video piano overlay matches the backend's fixture |
| `npm run check:cuts` | The Audio tab's cuts follow the backend's rules, and playback jumps over them |
| `npm run check:notes` | The Notes tab's typed arrays, live feed and edits (the operations a save sends) |
| `npm run check:flow` | The flow page walked in a headless Chromium, every tab, live transcription included (`--no-transcribe` skips it) |
| `npm run time:flow` | The whole flow timed on three temporary pieces (an upload, a library copy, a YouTube URL) |
| `npm run bench:roll` | The Notes tab at 10,000 rectangles and at 100 stream messages per second |
| `npm run bench:sheet` | A hand move on the Sheet tab's piano sheet, timed part by part, on copies |
| `npm run screenshot -- <path>` | A screenshot of a page in a headless Chromium, for a machine with no screen |

**These need the running app** (`make up`): `check:flow`, `time:flow`, `bench:roll`, `bench:sheet`
and `screenshot`. They open `http://localhost:5173` (`--base` changes it). The first four work on
temporary pieces and delete them at the end, so the library is never changed. `bench:roll` opens
`/dev/roll-bench`, which exists in development builds only. The other checks need no browser and no
backend.

## Source layout

```text
src/
  api/        # typed client, one module per backend router; no component calls fetch
  hooks/      # useProgress (SSE), followJob, useEditHistory, selection, staged removals, element size
  layout/     # AppLayout, PlaygroundLayout, VideoLayout, routes.ts (every path lives here)
  pages/      # one component per route
    piece/    #   the flow page: PiecePage, the five tabs, NotesEditor (Notes and Hands)
    playground/ # Upload / Input, Notes Falling, the piano sheet (RhythmPage)
    video/    #   Video to Notes
    dev/      #   /dev/roll-bench, development builds only
  state/      # WorkingArtifactProvider: the piece shared across Playground tabs and the flow page
  ui/         # palette.ts, theme.ts, timestamps.ts, progress.ts and the shared MUI wrappers
  music/      # matrix contracts mirrored from the backend, note names, figures, overrides
  notes/      # the piano roll visualization's data: typed arrays, view, live feed, edits
  audio/      # recorder, mm:ss.cc, the Audio tab's cuts, view window and player
  piano/      # the 88-key SVG keyboard
  playback/   # the transport, the scrub bar, how a note rectangle is drawn
  print/      # the PDF writer
  library/    # load a piece for the performance view
  video/      # the video piano overlay geometry, note placement, the selected video
  components/
    piece/    # the flow page's tabs, save bar, step progress, YouTube download
    notes/    # PianoRollCanvas, rollPaint, RollTimeBar; the Notes Falling toolbox and removals bar
    time/     # PeakPlot, TimeScoreView (the ONLY file that touches the renderer)
    audio/    # recorder, upload, waveforms (CutWaveform for the Audio tab), range selection
    input/    # transcription settings, compose a new piece
    editing/  # re-record a passage, add a passage
    library/  # playlists
    video/    # the Video to Notes views: player, calibration, detection, overlay
    common/   # the floating bar and the draggable toolbox shell
```

## Rules

- **Colors** come from `src/ui/palette.ts` only. No hex literal in a component or stylesheet.
- **Requests** use `src/api/`. No `fetch` in a component.
- **Routes** come from `src/layout/routes.ts`. No URL string literal in a component.
- **Components** are MUI. Aceternity UI is allowed for decoration only; every functional
  control stays MUI so behavior is consistent.
- **The renderer** is reached from `components/time/TimeScoreView.tsx` and nowhere else.
- **No component derives a note's figure.** The printed figure comes from the backend and is
  passed through.

**After pulling `../../vexflow-v2`, rebuild it** (`npm run build` there). npm does not build a
linked dependency, and a stale `dist/` fails silently: the app keeps engraving with the old code and
nothing warns. The container holds its own build of the package, so also run `make build` from the
repository root.
