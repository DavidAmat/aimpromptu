# aitu-frontend

React 19 + TypeScript + Vite app. It brings a recording in, shows how it was actually played, and
draws the sheet with `@aimpromptu/grid-notation`, a renderer built for this project, because
nothing off the shelf lays music out on a wall clock.

The app first asks to sign in (`/login`, implementation 02, Phase 4), then opens on **Projects**
(`/projects`), inside a shell with a left sidebar. A project goes from
its audio to its piano sheet in five steps (Source, Audio, Notes, Hands, Sheet), at
`/projects/:id/:step`. For the master user an **Admin** group holds **Users** (make users, reset a
password, disable a user) and **Lab** (the video reader's pages). The look is black, white and grey,
with colour only on the music (implementation 02, plan section 7), in a light or a dark scheme chosen
in the user menu. Who can open what: [08-security.md](../context/08-security.md).

**Documentation:** [context/frontend/](../context/frontend/README.md) ·
projects and their steps: [projects.md](../context/frontend/projects.md) ·
colours: [color-palette.md](../context/colors/color-palette.md) ·
components: [components.md](../documentation/services/frontend/components.md) ·
rendering: [rendering.md](../context/frontend/rendering.md)

## Run

**In containers** (the usual way), from the repository root:

```bash
make up      # builds if needed, starts the backend (GPU) and this app; open http://ubuntu:5173 from the Mac
make logs    # follow both
make down    # stop both
```

The frontend container runs the Vite development server on the mounted source folder, so an edit
shows in the browser at once. It listens on every address of the machine (`WEB_BIND`, default
`0.0.0.0`) and answers only to the host names of `allowedHosts` in `vite.config.ts` (`localhost`,
`ubuntu`, `david-ubuntu`, `david-ubuntu.local`, plus `AITU_ALLOWED_HOSTS`) and to IP addresses. Sign
in as the master user with `AITU_MASTER_PASSWORD` of `.env`. After a change of `package-lock.json` or of `../../vexflow-v2`, run
`make build` (or `make up`, which rebuilds).

**Natively**, without containers:

```bash
npm install && npm run dev
```

with the backend running on `http://127.0.0.1:8765`. `make serve` from the repository root starts
both natively. Natively the page listens on `localhost` only.

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
| `npm run check:cuts` | The Audio step's cuts follow the backend's rules, and playback jumps over them |
| `npm run check:notes` | The Notes tab's typed arrays, live feed and edits (the operations a save sends) |
| `npm run check:flow` | A project walked in a headless Chromium, every step, live transcription included (`--no-transcribe` skips it) |
| `npm run check:projects` | The Projects page and the Personal Vault in a headless Chromium: New project, **Add audio**, Duplicate, Export, Import, Rename, Delete, a video file opening its Video step; on files it makes and deletes |
| `npm run check:library` | My library in a headless Chromium, on a copy of Elefants under a song of its own: **Save to library** (the audio written again), a version read only, **Edit**, Replace, History and Restore, a new version, Songs and Artists; all deleted at the end |
| `npm run check:transpose` | The sheet toolbox's **Transpose** in a headless Chromium, on a copy of Elefants: notes (the notes moved on the backend, the key with them, undo and redo exact) and figures (the main figure, the next **From**), the preview dialog; **Key for this passage** and the Clef tab of the range toolbox (`scripts/check-sheet-toolbox.mjs --only transpose`) |
| `npm run check:paste` | **Copy** and **Paste** (Phase 8), on copies of Superestrella's tutorial and Elefants: a stretch copied, pasted at the cursor (its notes, its audio as a file of its own, the saved sheet, the cursor kept), undo and redo exact, ⌘V over a marked stretch, a reload; **From scratch** (no step tabs, Paste fills it); a stretch of a version of My library pasted across layers; every join of the audio checked sample by sample by `aitu-backend/scripts/check_joins.py` in the backend container (`scripts/check-paste.mjs`) |
| `npm run check:passage` | **Record this passage** (Phase 9), on a copy of Elefants: the page of a stretch, a take recorded with Chromium's fake microphone and one added from a file (the passage's own audio twice as slow), **Write the proposal** (the GPU job), **Fit** (×2) and the window dragged, **Fit to the window** with the recording (the length kept, every join checked), undo and redo, **Replace the whole passage** (the song as much longer as the dialog said), a blank sheet's new passage played on a simulated MIDI piano with no sound (the keys are the notes), a MIDI take with the microphone, **Discard**, 390 px and dark (`scripts/check-passage.mjs`) |
| `npm run check:compose` | **From other projects** and the playlists (Phase 10), on copies of Elefants and Superestrella's tutorial: a stretch of a read-only sheet and a whole project added, a **Subheader**, a passage moved, the list kept over a reload, **Save as integrated playlist** (two parts, the notes of each passage, the sources unchanged); the parts renamed, moved, joined and split (**Start a new part here**); on a copy saved to My library, **Make a playlist** from Songs, **Add to a playlist** from a version, a song removed, the playlist deleted; 390 px and dark (`scripts/check-compose.mjs`) |
| `npm run check:play` | **Play mode** (Phase 11), on copies of Elefants: **Play** from Projects, the page with the sheet alone, Space, the buttons fading while it plays, the cursor kept in the middle of the window, a lyrics piece shown by its frames, the arrows, a double-click moving the cursor, **Notes Falling** as a view and its old address, Escape; an integrated playlist of two parts played on; two copies saved as songs, **Play** on a song and a version, a songs playlist with **Next**, a stretch that stops by itself, **All songs**, Close back to the playlist; 390 px and dark (`scripts/check-play.mjs`). Uses no GPU |
| `npm run check:requests` | **Requests, the review and sharing** (Phase 14), with a temporary user the check makes and removes: **Share my library**, the user's **Shared** and **Add to my library**, **Publish** a version on the public “7 Years”, **Propose a song** with a new artist, the master user's **Review** (counts, oldest first), a change asked and **Change and send again**, side by side and Play, the accepted version and **Ask for a fixed version**, a withdrawn change, the rights; 390 px and dark; everything public it made removed (`aitu_backend.library.public_fixture`), and the user with all of theirs (`scripts/check-requests.mjs`). Uses no GPU |
| `npm run check:public` | **The Public Library** (Phase 13): a copy of a version of My library placed as two public versions of “Stayin' Alive” (`aitu_backend.library.public_fixture`, on the host); Public songs (the count, a search, the Decade chip and its popularity, a sort), one song (byline, chart line, versions, a like, lyrics, **Play**), **Add to my library** and the song in My library with its link back, a song with no version, an artist, the artists, a public playlist (**Add to my library**, **Play**, Close), **Search**, **Save to library** on a public song; 390 px and dark; everything it made deleted (`scripts/check-public.mjs`). Uses no GPU |
| `npm run check:lyrics` | The **Lyrics** tab, on a copy of Elefants: words saved before read as a piece, the pool, a piece dragged onto the sheet, moved and resized on frames, merge, split, line break, larger, back to the pool, delete, undo, Save and a reload. `--only clefs` of the same script checks the clef rule on a first write |
| `npm run time:flow` | The whole flow timed on three temporary pieces (an upload, a copy opened from Projects, a YouTube URL) |
| `npm run bench:roll` | The Notes tab at 10,000 rectangles and at 100 stream messages per second |
| `npm run bench:sheet` | A hand move on the Sheet step's piano sheet, timed part by part, on copies |
| `npm run screenshot -- <path>` | A screenshot of a page in a headless Chromium, for a machine with no screen. Options: `--piece <uuid>`, `--wait <selector>`, `--delay <ms>`, `--out <file.png>`, `--width`, `--height`, `--full`, `--base <url>`, `--theme dark` (the dark scheme), `--signed-out` (the sign-in page, without signing in) |

**These need the running app** (`make up`): `check:flow`, `check:projects`, `check:library`, `check:transpose`, `check:lyrics`, `check:paste`, `check:passage`, `check:compose`, `check:play`, `check:public`, `check:requests`, `time:flow`,
`bench:roll`, `bench:sheet` and `screenshot`. They open `http://localhost:5173` (`--base` changes
it). All but `bench:roll` and `screenshot` work on temporary pieces and delete them at the end, so the library is never
changed. `bench:roll` opens
`/dev/roll-bench`, which exists in development builds only and needs no sign in. The other checks
need no browser and no backend.

**Signing in.** Every page and every route of the backend need a session, so `check:flow`,
`check:projects`, `check:library`, `check:transpose`, `check:lyrics`, `check:paste`, `check:passage`, `check:compose`, `check:play`, `check:public`, `check:requests`, `time:flow`, `bench:sheet` and
`screenshot` sign in first through `scripts/session.mjs`. Once the master user's password was changed in the app (as on the Ubuntu
machine since 2026-10-06), the line of `.env` no longer signs in: give `AITU_CHECK_PASSWORD` (and
`AITU_CHECK_USERNAME` for another user) in the environment of the command. They act as
the master user, with `AITU_MASTER_USERNAME` (default `master`) and `AITU_MASTER_PASSWORD` of `.env`
at the repository root, the same values the backend made the master user from. To sign in as
another user, set `AITU_CHECK_USERNAME` and `AITU_CHECK_PASSWORD` in the environment. Without a
password the script stops at once and says so. `session.mjs` gives the cookie to every `fetch` of
the script (`signIn(base)`) and to every Playwright page (`useSession(browser)`).

## Source layout

```text
src/
  api/        # typed client, one module per backend router; no component calls fetch
  hooks/      # useProgress (SSE), followJob, useEditHistory, selection, the played notes, element size
  layout/     # AppLayout (the shell, the user menu), RequireUser and RequireMaster (the guards), PasswordDialog, LabLayout, SearchDialog, ShortcutsDialog, LegacyRedirect, routes.ts (every path lives here)
  pages/      # one component per route
    LoginPage.tsx     # Sign in
    ProjectsPage.tsx  # Projects
    admin/    #   UsersPage: Admin → Users
    piece/    #   a project: PiecePage, the five steps, NotesEditor (Notes and Hands), sheet/ (the Sheet step, split into modules), passage/ (Recording in Sheet)
    play/     #   Play mode: PlayPage, its Notes Falling view, what it plays (a project, a playlist)
    video/    #   the Lab pages: the video reader
    dev/      #   /dev/roll-bench, development builds only
  state/      # AuthProvider: the signed-in user; WorkingArtifactProvider: the working piece and its frameMs
  ui/         # the design system: tokens (light and dark), theme, scheme (SchemeSync, useScheme), palette (the colours of the music), the shared components
  music/      # note names, figures, overrides
  notes/      # the piano roll visualization's data: typed arrays, view, live feed, edits
  audio/      # recorder, mm:ss.cc, the Audio step's cuts, view window and player
  piano/      # the 88-key SVG keyboard
  playback/   # the scrub bar, the played notes, how a note rectangle is drawn
  print/      # the PDF writer
  video/      # the video piano overlay geometry, note placement, the selected video
  components/
    piece/    # step names, step progress
    notes/    # PianoRollCanvas, rollPaint, RollTimeBar
    time/     # TimeScoreView (the ONLY file that touches the renderer), ScorePlayer, FigureGlyph
    audio/    # waveforms (CutWaveform for the Audio step), range selection, level bars
    video/    # the Lab views: player, calibration, detection, overlay
```

## Rules

- **Colors** come from `src/ui/tokens.ts` (the page) and `src/ui/palette.ts` (the music) only. No
  hex literal in a component or stylesheet. A component that draws with `ui` (a canvas, an SVG)
  calls `useScheme()`, so it redraws when the user changes between the light and the dark scheme.
- **Shared components** come from `src/ui/`: a title, a button, a list row, a table, a toolbox, an
  empty state, a confirmation. Every icon button is an `IconAction`, with its tooltip.
- **Requests** use `src/api/`. No `fetch` in a component.
- **Routes** come from `src/layout/routes.ts`. No URL string literal in a component.
- **Components** are MUI, styled by the theme. Every functional control stays MUI so behavior is
  consistent.
- **The renderer** is reached from `components/time/TimeScoreView.tsx` and nowhere else.
- **No component derives a note's figure.** The printed figure comes from the backend and is
  passed through.

**After pulling `../../vexflow-v2`, rebuild it** (`npm run build` there). npm does not build a
linked dependency, and a stale `dist/` fails silently: the app keeps engraving with the old code and
nothing warns. The container holds its own build of the package, so also run `make build` from the
repository root.
