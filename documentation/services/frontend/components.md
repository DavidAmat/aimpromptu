> Context: [context/frontend/README.md](../../../context/frontend/README.md) ·
> [context/frontend/pages.md](../../../context/frontend/pages.md) ·
> [context/frontend/projects.md](../../../context/frontend/projects.md)

# The component tree: where each piece lives

`aitu-frontend/src/`. React 19, TypeScript, Vite, MUI. The sheet itself is laid out and drawn by the
backend (`GET /sheet/{uuid}` answers an SVG), see
[rendering.md](../../../context/frontend/rendering.md). The vexflow-v2 package that drew it in the
browser before was removed in implementation 03, Phase 10 (2026-10-27), see
[deprecated/grid-notation.md](../../deprecated/grid-notation.md).

---

## 1. Routes and shell

`layout/routes.ts` is the single place every URL is written (`ROUTES`, the patterns, `LAB_TABS`). Nothing hardcodes a path. `App.tsx` holds the route table.

| Section | Path | Page |
|---|---|---|
| **Sign in** | `/login` | `pages/LoginPage.tsx`, outside the shell (implementation 02, Phase 4) |
| (start) | `/` | redirects to `/projects` |
| **Projects** | `/projects` | `pages/ProjectsPage.tsx`: `GET /projects` (the vault), the **New project** menu with **From scratch** (`POST /projects` with `scratch`, then its Sheet step; Phase 8) and Import (`POST /projects/import`), the row menu (Duplicate, Export, Rename, **Play**, Delete) through `api/projects.ts`; an edit copy (`row.editing`) says **Editing**, adds **Open the song**, and its Delete is **Discard changes** |
| · new project | `/projects/new` | `pages/piece/PiecePage.tsx` with the Source step only |
| · From other projects | `/projects/compose` | `pages/compose/ComposePage.tsx` (Phase 10, section 3.2) |
| · a project | `/projects/:id` | `PiecePage.tsx` + `PieceResume.tsx`: opens the step the project reached |
| · one step | `/projects/:id/<step>` | `PiecePage.tsx` + `SourceTab`, `AudioTab`, `NotesTab` or `SheetTab`; `/projects/:id/hands` (old links) redirects to `sheet` |
| · a passage | `/projects/:id/passages/:passageId` | `pages/piece/passage/PassagePage.tsx`, outside `PiecePage` (Phase 9, section 3.1) |
| **Songs** (My library) | `/library/songs`, `/library/songs/:id` | `pages/library/SongsPage.tsx`, `SongPage.tsx` (Phase 6, section 10) |
| **Artists** (My library) | `/library/artists`, `/library/artists/:id` | `pages/library/ArtistsPage.tsx`, `ArtistPage.tsx` |
| **Playlists** (My library) | `/library/playlists`, `/library/playlists/:id` | `pages/library/PlaylistsPage.tsx`, `PlaylistPage.tsx` (Phase 10, section 1.1) |
| **Play mode** | `/play/:projectId`, `/play/playlist/:playlistId` | `pages/play/PlayPage.tsx`, outside the shell (`RequireUser` only), keyed by the id (`PlayRoute` in `App.tsx`; Phase 11, section 4) |
| **Users** (Admin) | `/admin/users` | `pages/admin/UsersPage.tsx`, inside `RequireMaster` |
| **Lab** (Admin) | `/admin/lab/<tab>` | `layout/LabLayout.tsx` and `pages/video/`, inside `RequireMaster` |
| (development only) | `/dev/roll-bench` | `pages/dev/RollBenchPage.tsx`, lazy, only when `import.meta.env.DEV` |

`<step>` is one of `PIECE_STEPS` in `api/pieces.ts`: `source`, `audio`, `notes`, `sheet`.
`ROUTES.project(id, step?)` builds the address. Until Phase 3 the id of a project is the uuid of its
piece.

**The shell** (implementation 02, plan section 6.2): `layout/AppLayout.tsx` renders `ui/AppShell`
with `ui/Sidebar` (the logo, **Search**, Projects, the **My library** group with **Songs**,
**Artists** and **Playlists**, for the master user an Admin group with **Users** and **Lab**, and the user menu at the
bottom). The sidebar is open on the list pages and closed
inside a project and under 900 px. `⌘K` opens `layout/SearchDialog.tsx` from anywhere (the songs of
My library and the projects of the vault, Phase 6);
`layout/ShortcutsDialog.tsx` lists the shortcuts.

**The user menu** (`UserMenu` in `AppLayout.tsx`, Phase 4): the username and the role (Master user or
User), **Change password** (`layout/PasswordDialog.tsx`: the current password and a new one of at
least 8 characters, `PUT /auth/password`), the theme as a `Segmented` of **Light**, **Dark** and
**System** (MUI's `useColorScheme().setMode`), **Keyboard shortcuts** and **Sign out**.

**Signing in** (Phase 4):

| File | Role |
|---|---|
| `pages/LoginPage.tsx` | `/login`: the logo, **Username**, **Password**, **Sign in**. Returns to `?next=` when it is an address of this app, otherwise to Projects. The button stays busy while the backend slows a try after wrong passwords |
| `state/passageClipboard.ts` | The copied passage (Phase 8): a reference (part, `fromMs`, `toMs`, title) kept in `localStorage` so it reaches every page and tab of the app; `usePassageClipboard()`; JSON text for the system clipboard (`passageText`, `passageFromText`) |
| `state/AuthProvider.tsx`, `state/authContext.ts` | The signed-in user (`useAuth()`: `user`, `signIn`, `signOut`). Asks `GET /auth/me` once when the page opens; forgets the user on `SIGNED_OUT_EVENT` |
| `layout/RequireUser.tsx` | `RequireUser` (wraps the shell: nobody signed in opens `/login?next=...`) and `RequireMaster` (wraps Users and Lab: "Page not found" for another user) |
| `pages/admin/UsersPage.tsx` | **Admin → Users**: a `DataTable` of the users, **New user** (username and first password), per row **Reset password** and **Disable** / **Enable** |
| `pages/piece/PiecePage.tsx` | A project the backend answers `404` for (another user's, or none) shows "There is no project of yours at this address." with **Open Projects** |

`main.tsx` creates a **data router** (`createBrowserRouter`) with one route that renders `App`'s
route table. It exists for one reason: React Router's `useBlocker`, which the project page needs to
ask before a reader leaves a step with unsaved changes, only works with a data router. It also gives
the theme `defaultMode="light"`, wraps the router in `AuthProvider`, and puts `SchemeSync`
(`ui/scheme.tsx`) between the theme and the router (section 8).

`state/WorkingArtifactProvider.tsx` holds the working piece in `sessionStorage`. The project page
sets it when it loads a project; the sheet reads its `frameMs` from it.

---

### 1.1 My library (implementation 02, Phase 6)

| File | Role |
|---|---|
| `pages/library/SongsPage.tsx` | **Songs**: `GET /library/songs` as a `DataTable` (Title with **Editing** when a copy is open, Artist, Versions, Changed), a **Filter** field on the title and the artists, the empty state with **Open Projects** |
| `pages/library/SongPage.tsx` | One song: **Play** in its header (Play mode on the first version, Phase 11), its artists as links, its versions as `ListRow`s (a row opens the project read only; its `⋯`: Open, **Play**, **Edit** or **Continue editing** (`POST /projects/{id}/edit`), Duplicate, Export, Rename, History, Delete); the header's `⋯`: Rename song, Artists (an `Autocomplete` of names, `PATCH /library/songs/{id}`), Delete song. `HistoryDialog` lists `GET /library/versions/{id}/history`, each with **Restore** after a confirmation. `data-testid="version-<id>"` is read by `check:library` |
| `pages/library/ArtistsPage.tsx` | **Artists**: `GET /library/artists` as a `DataTable` (Name, Other names, Songs) with a **Filter** |
| `pages/library/ArtistPage.tsx` | One artist: **Names** (`ListRow`s, the default marked; Make default, Rename, Remove) with **Add a name**, **Songs**; the header's `⋯`: Merge into another artist (`MergeDialog`), Delete artist (disabled while it has songs) |
| `pages/library/TextDialog.tsx`, `shared.ts` | One field and one button (rename, add a name); `said()` (the backend's words of a refusal), `download()`, `stretchLabel()` |
| `pages/library/PlaylistsPage.tsx` | **Playlists** (Phase 10): a `DataTable` of the songs playlists (`GET /playlists`) and of the integrated playlists of the library (`GET /projects?layer=private`, `kind`), **New playlist** (a `TextDialog`) |
| `pages/library/PlaylistPage.tsx` | One songs playlist: **Play** (Phase 11, `ROUTES.playPlaylist`), rows dragged by a handle (`useRowDrag`), each a `ListRow` (the song and its artists, the version, the stretch or "Whole"; a click plays from it; `?at=` shades the row Play mode was closed on) with **Play from here**, Open, **Use “<version>”**, **The whole song**, Move up/down, **Remove from the playlist**; **Add a song** (`ChooseSongDialog`); Rename, Delete. `data-playlist-items`, `data-playlist-item` are read by `check:compose` |
| `pages/library/AddToPlaylistDialog.tsx` | **Add to a playlist**: a version (from the song page's version menu) or a stretch of it (from the read-only sheet's *Frames* panel) into a playlist or a new one |
| `pages/library/SongsPage.tsx` (Phase 10) | Rows picked by their checkbox (`DataTable`'s `selected`), **Make a playlist of N** |
| `pages/library/SongPage.tsx` (Phase 13) | "In the Public library" under the title when the song stands for a public one (`publicId`) |

### 1.2 The Public Library (implementation 02, Phase 13)

| File | Role |
|---|---|
| `api/publicLibrary.ts` | `publicApi`: the `/public` routes |
| `pages/public/PublicSongsPage.tsx` | **Public songs**: the search (debounced 250 ms), `FilterChip`s from the answer's `facets` (a chip only when it has values), a `DataTable` in server mode (`sort`, `onSortChange`, `paging`); the popularity header names the region and the decade on a second line (Phase 16: a label with `\n` is drawn with `pre-line`), and the title and artist columns stop at 300 and 210 px so the sorted column stays in view at 1440 px; every setting in the address (`q`, `decade`, `region`, `genre`, `tag`, `sort`, `dir`, `page`, `per`). `data-testid`: `public-search`, `filter-decade`, `filter-region`, `public-total` |
| `pages/public/PublicSongPage.tsx` | One public song: byline (artist links), the facts grid (worldwide and per region, "≈" with the reason on hover for `number_ones` and `estimated`, Phase 16), a `ChartHistory` per chart, `VersionLine`s (name, Default, In My library, creator, the like button, Play, `⋯`), `AddDialog` (versions to add, the default one ticked), Lyrics on request. `data-testid`: `public-byline`, `public-version`, `like`, `public-play`, `add-to-library`, `add-confirm`, `open-mine`, `show-lyrics`, `lyrics` |
| `pages/public/ChartHistory.tsx` | The chart line: places 1 to 100 over time, broken where the song was off the chart more than three weeks, the best place marked; drawn at its real width up to 640 px (a `ResizeObserver`; the first drawing at the window's width), so its words keep their size. `named` puts the chart's name and region above it; a chart of size 1 (number ones only) says "Weeks at number 1". `data-testid="chart-history"` |
| `pages/public/PublicArtistsPage.tsx`, `PublicArtistPage.tsx` | The artists (server mode); one artist's songs and albums (`DataTable`s by popularity), **Add to my library** (`data-testid="add-artist"`) |
| `pages/public/PublicPlaylistsPage.tsx`, `PublicPlaylistPage.tsx` | The public playlists; one with `ListRow`s (a click plays from that song), **Play** (`ROUTES.playPublicPlaylist`), **Add to my library** |
| `pages/public/shared.ts` | `popularityText` (one decimal), `versionLabel`, `monthYear`, `defaultVersion` |
| `pages/piece/SaveToLibraryDialog.tsx` (Phase 13) | The Artist and Song fields add `publicApi.suggest` answers under "Public library" (`groupBy`); a public song sends `publicSongId`, a public artist `publicArtistId` |
| `layout/SearchDialog.tsx` (Phase 13) | After 200 ms of no typing, the public songs and artists that match, under the user's own results |
| `pages/play/playQueue.ts`, `PlayPage.tsx` (Phase 13) | `?from=public` on `/play/playlist/:id` reads a public playlist; **Close** goes back to it |

## 2. The page of a project

One project, four steps in the order of the work: Source, Audio, Notes, Sheet (the Hands step left the
flow in implementation 03, Phase 5, and its code was removed in Phase 10). What each step
means for the reader is in [projects.md](../../../context/frontend/projects.md). This section
lists where the code is.

### 2.1 The page and its tabs

| File | Role |
|---|---|
| `pages/piece/PiecePage.tsx` | The page: loads the audio, `GET /pieces/{uuid}/status` and the project's row (`GET /projects/{projectId}`: its `library` or `editing` link), draws the header (back arrow, title, the step tabs with the Audio tab named **Video** for a video project, the primary action, the `⋯` menu with **Play** (the whole project, once its Sheet step is open), Export, and **Discard changes** on an edit copy), redirects a step that is not enabled, holds the leave dialog (**Stay**, **Discard**, **Save and continue**, a `ConfirmDialog`) and the `beforeunload` warning. Phase 6: **Save to library** once the Sheet step is ready (`SaveToLibraryDialog`); a project of the library (`audio.layer === "private"`) is `readOnly`, titled "<song> (<version>)", goes back to its song, and has **Edit** (`POST /projects/{id}/edit`) as its action, with **Play** beside it (Phase 11) |
| `pages/piece/pieceContext.ts` | What every tab shares: `usePiece()` (the piece, its status, `readOnly`, `refresh()`), `stepStatus()`, and `useUnsavedChanges(summary, {save, discard})`. `readOnly`: a version of the library, which every step shows without its changes (no handles or menus on Source; no cut, Save, Add audio or Transcribe on Audio, and no Video step; the roll in `view` mode with playback and no edit or Save; the sheet with Play and Print only and no toolbox) |
| `pages/piece/SaveToLibraryDialog.tsx` | **Save to library** (Phase 6): Artist and Song as `Autocomplete` over `GET /library/artists` and `GET /library/songs` that take a new name as typed (choosing a known song sends its id and fills its artist), **Version name** ("original" at first). On an edit copy a `Segmented` **Replace “<version>”** / **New version**. `POST /projects/{id}/library`, then the song |
| `pages/piece/PieceResume.tsx` | `/projects/:id`: follows the backend's `resume` |
| `pages/piece/PartsPanel.tsx` | The parts of a project of several parts, beside its Sheet step (Phase 10): `RailRow`s (subheader or "Part N", length), a click opens that part's sheet, drag and Move up/down (`PUT /projects/{id}/parts`), **Rename** (`PATCH …/parts/{part}`), **Join with “…”** (`POST …/join`). Hidden for one part. `data-parts-panel`, `part-<n>` are read by `check:compose` |
| `ui/StepTabs.tsx` | The step tabs, each with a dot for its state (filled ready, a spinner running, amber stale or unsaved, a ring missing) and the reason as a tooltip; `data-step` and `data-state` on each tab for the checks |
| `components/piece/stepLabels.ts` | The names of the four steps |
| `components/piece/StepProgress.tsx` | A short job in progress: label, bar, seconds taken |
| `api/pieces.ts` | `piecesApi`: `status`, `notes`, `patchNotes`; the types `PieceStatus`, `StepStatus`, `PieceNotes` |

The page enables its tabs from the status answer only. It never works out staleness itself: the
backend compares the revisions and answers every step at once.

A tab that is not enabled is greyed and ignores the press. It is not a disabled MUI tab, because a
disabled element receives no pointer events and its tooltip (the backend's reason) would never
show.

### 2.2 Source and Audio

| File | Role |
|---|---|
| `pages/piece/SourceTab.tsx` | A new project: the drop zone for an audio or a video file (`POST /audio/upload` or `POST /video/upload`), **Paste a YouTube link** with **Audio** / **Video** (`POST /youtube/jobs` as a job, or `POST /video/download`); a video opens the Video step. An existing project: `SourceFiles`, or where the video came from for a video project |
| `pages/piece/SourceFiles.tsx` | The Source step of a project with audio: its files in order (`GET /audio/{uuid}/files`), drag by the handle to reorder (native drag and drop, and **Move up** / **Move down**), **Rename** in place, **Remove** with a confirmation; **Add audio** by files (several at once) or a YouTube link (`POST /youtube/jobs` with `appendTo`). `data-source-files` and `data-file-row` are read by `check:projects` |
| `pages/piece/AudioTab.tsx` | The waveform full width, cuts, undo and redo, the floating bar of icon actions with **Add audio at the end** (`POST /audio/{uuid}/add`) and **Save** (`PUT /audio/{uuid}/cuts`), **Transcribe** on the top row. `data-selection`, `data-view`, `data-cuts` and `data-files` on its root are read by `check:flow` and `check:projects`. With several files, `FilePanel` on the left lists them; a click selects and zooms to one file's part. A project with a video gets `VideoStep` instead |
| `pages/piece/VideoStep.tsx` | The Video step (Phase 5): prepares the frames (`POST /video/{uuid}/sample`), fits the piano with `CalibrationEditor` in its compact form, plays the video with the piano on it (`FramePlayer`, `PianoOverlay`), **Read notes** (`POST /video/{uuid}/read`, followed on its progress stream), then opens Notes |
| `components/audio/CutWaveform.tsx` | Two stacked canvases (waveform, cuts and selection below; the playhead alone above) and an overview strip |
| `components/audio/waveformPaint.ts` | The painters of `CutWaveform`, with the files of a part of several files (every second one on a grey band, a dashed grey line at each join, each file's name) |
| `audio/frameView.ts` | The window of time frames on screen: zoom, pan, whole view |
| `audio/cuts.ts` | The cut rules, the same as the backend's `normalize_cuts`; pure functions |
| `audio/useCutPlayer.ts` | Plays the audio and jumps over the page's current cuts, or plays the frames selected |

The waveform comes from one request, `GET /audio/{uuid}/frames/peaks`: the lowest and highest
sample of every 10 ms time frame. Every zoom level is then drawn from memory, and every pixel sits
on the same axis as the cuts.

### 2.3 Notes: the canvas editor

`NotesTab.tsx` is one line: `<NotesEditor />`. The Hands tab shared this editor until implementation
03 (`HandsTab.tsx`, the Hands mode of `NotesEditor`, **Predict hands**, **To right** / **To left**, the
hand filter and `piecesApi.predictHands` were removed in Phase 10): the AI decides the hands with the
sheet, and a hand is changed on the sheet.

| File | Role |
|---|---|
| `pages/piece/NotesEditor.tsx` | The editor page: live view, playback, every gesture as an undo step, **Save**, the primary action on the top row (**Continue to Sheet**), **Hand colours** (the rectangles coloured by hand once the piece has hands) and the floating toolbox |
| `components/notes/PianoRollCanvas.tsx` | The piano roll visualization: the vertical keyboard, one row per key, the rectangles; modes `live`, `edit`, `view` |
| `components/notes/rollPaint.ts` | The painters: the lower canvas (rows, grid, ruler, keyboard, rectangles of the visible range) and the upper canvas (playhead, lit keys, sounding notes, band) |
| `components/notes/RollTimeBar.tsx` | The bar under the roll: the progress bar while the piece is transcribed, the scrub bar afterwards |
| `notes/rollNotes.ts` | `RollNotes`: the notes in typed arrays, one array per field, with an index by onset and one by key |
| `notes/rollView.ts` | Where things are on the canvas: time axis, key rows, zoom, snap to 10 ms |
| `notes/liveFeed.ts` | `LiveFeed`: the queue of stream messages, drained once per animation frame, and the frontier |
| `notes/useLiveTranscription.ts` | Follows the running transcription's progress stream into the feed |
| `notes/noteEdits.ts` | The edits as overrides on the saved notes; `toOperations` turns them into the `PATCH /pieces/{uuid}/notes` operations |
| `hooks/followJob.ts` | Follows one job to its end from a button (its one user, **Predict hands**, was removed in implementation 03, Phase 10) |
| `hooks/useEditHistory.ts` | Undo and redo, shared with the Audio tab and the sheet. `commit` (Phase 8) makes one step that replaces every edit at once, with its backend undo and redo (a paste) |

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

**The floating bar is the editor's toolbar**: Play/Pause, Undo, Redo, Delete, the selection's
Spanish name, **Save**.

### 2.4 Sheet

`pages/piece/SheetTab.tsx` renders `sheet/SheetPage` (section 3) with its `step` prop (`SheetStep`:
the piece, the Sheet step's state and reason, and `onChanged`), beside `PartsPanel` (Phase 10). It
gives the sheet `onSplit` (`POST /projects/{id}/parts/{part}/split` with `{atMs}`, then the panel and the
sheet read again), titles a part's sheet by its subheader, and on a version of the library a
`stretchAction` **Add to a playlist** and `enhanceInCopy` (**Enhance with AI** opens the edit copy and
starts there). `onChanged` refreshes the status after a change, so the dot of the step follows.

---

## 3. The sheet

`pages/piece/sheet/` is the Sheet step of a project and every other place a sheet is shown. The sheet
is laid out and drawn by the backend (`aitu_backend/sheet/`, `GET /sheet/{uuid}?width=N` answers the
SVG with its columns, systems and segments), and the page draws that SVG with what moves over it.
Every edit is written at once as one step of undo kept by the backend (no **Save**). What it does
for the reader is [`context/frontend/annotations.md`](../../../context/frontend/annotations.md) and its
sub pages; the backend side, phase by phase, is `aitu-backend/src/aitu_backend/sheet/README.md`
sections 12 to 17.

| Module | Role |
|---|---|
| `SheetPage.tsx` | The step types (`SheetStep`, `PassageView`, `PlayView`) and `SheetPage`, which draws `frames/FramesSheetPage` |
| `frames/FramesSheetPage.tsx` | The page: the sheet at once (the AI's or the algorithm's), **Enhance with AI**, the header at the top of the window (title, `AiMark`, the floating bar's buttons from one list), the floating bar, ⌘ and the wheel zoom, the toolboxes, Copy and Paste, Record, the roles of `step.passage` and `step.play` |
| `frames/FramesSheetView.tsx` | The SVG the backend draws, and over it, in the same staff-space units, what moves: the playhead (dragged and dropped across lines since implementation 04, Phase 1), the picked notes, the marked stretch, the veil over a segment the AI is writing |
| `frames/useFramesSheet.ts` | The sheet of a part as the page holds it: read for the page's width, read again at each step of the AI's job (`event: sheet` on the job's stream) |
| `frames/geometry.ts` | The arithmetic of the page from the cursor map the backend sends (one row per drawn column, one box per system) |
| `frames/FramesNoteToolbox.tsx`, `FramesRangeToolbox.tsx`, `readingTools.ts` | The note toolbox and the range toolbox (titled *Frames*), and what they share |
| `frames/FramesSheetToolbox.tsx` | The sheet toolbox: Title, Key, Transpose, Lyrics, View |
| `frames/FramesPreviewDialog.tsx` | The preview of a transposition: the sheet as it would be, **Transpose** or **Cancel** |
| `frames/FramesLyricsToolbox.tsx`, `useFramesLyrics.ts`, `lyricsText.ts` | The lyrics pieces on the sheet (stored in `sheet.f1`), the pasted words and the pool (`GET`/`PUT /sheet/{uuid}/words`) |
| `frames/EnhanceStretchDialog.tsx` | **Enhance with AI** for one stretch, with the user's own words |
| `frames/FramesPdfDialog.tsx` | Print to PDF (section 6) |
| `TransposeTab.tsx`, `LyricsTab.tsx`, `lyricsPieces.ts` | The **Transpose** and **Lyrics** tabs of the sheet toolbox, kept from the old sheet and used by the new one |
| `sheetConstants.ts`, `toolboxPlacement.ts` | The colours of the hands on the keyboards; where a toolbox opens |
| `PianoToolboxes.tsx` | The keyboard under the playhead |

| Shared component | Role |
|---|---|
| `components/time/ScorePlayer.tsx` | Plays the recording; `compact` draws only the scrub bar (the Sheet step); `headless` (Phase 11) draws nothing but a refused start; `stopAt` and `onEnded` (the end of a stretch, the end of the file); `preload` (`metadata` for a part of Play mode not yet playing, changed on the element without a new one); `keys` (Phase 9) turns Space off for a second player on the page. `version` (Phase 8) puts the audio at a new address when it changed under the page, because the browser keeps a media file by its address; the Audio and Notes steps add the audio revision the same way (`audioApi.fileUrl(uuid, normalized, revision)`) |
| `components/time/FigureGlyph.tsx` | One figure drawn as its glyph (the figure buttons of the toolboxes) |
| `ui/Toolbox.tsx`, `ui/FloatingBar.tsx` | The draggable panel and the floating bar every step uses |

**The old sheet was removed in implementation 03, Phase 10 (2026-10-27).** Its page
(`VexflowSheetPage` of `SheetPage.tsx`), `components/time/TimeScoreView.tsx` (the vexflow-v2
renderer), `ScorePdfDialog.tsx`, `NoteToolbox`, `RangeToolbox`, `SheetToolbox`, `SheetFloatingBar`,
`TransposeDialog`, `useNoteActions`, `useRangeActions`, `sheetEdits.ts` and `api/timeScore.ts` are
gone (section 9). Since Phase 8B nothing drew them.

### 3.1 The page of a passage (Phase 9)

`pages/piece/passage/PassagePage.tsx`, Recording in Sheet
([`context/frontend/recording-in-sheet.md`](../../../context/frontend/recording-in-sheet.md)). It reads
`GET /passages/{id}` and draws:

| Part | How |
|---|---|
| The frame | A recording mode: `position: fixed` over the window (layer 1100, under the floating bar and the toolboxes), a title bar ("Recording · <song>", the times, **Promote** as a menu of **Fit to the window** and **Replace the whole passage** or **Put it in** for a new passage, `⋯` with **Discard this passage**, **Close the recording** back to the sheet) |
| The left panel | `RailRow`s: **Current** (`take-current`), then each take with what it is and a bin (`ConfirmDialog`, `passagesApi.deleteTake`); **Record** and **Add a take from a file** (a hidden file field). A click shows that one (a take becomes the one on show, `PATCH /passages/{id}`) |
| The main area | The Current alone (`SheetPage` with `passage.role = "current"`, its play button driving the sheet's player through `playerRef`; starting one sheet stops the other). A take: a `Segmented` **Audio** / **Sheet** (`tab`; the Sheet once the take is written). **Audio**: `WaveformRangeSelector` of the take (its `initialRange` the stretch kept), **Write the proposal** (`passagesApi.readTake`, followed with `useProgress` and `ProgressBanner`). **Sheet**: the Current above the Proposal, `SheetPage` with `passage.role = "proposal"`, keyed by the take and its audio revision, the window (`frameWindow`, columns of the take) and the bar's actions (Record a take, **Fit**); the speed beside the tabs, a slider on a log scale, ×0.25 to ×4, sent on release |
| The recorder | A `Toolbox`: **Notes from** (**Microphone** or **MIDI piano**, `audio/useMidiInput.ts`: Web MIDI, the keys timed from the moment the sound starts recording, a key's note ending when it comes up; the piano chosen when there are several; the keys counted while recording); **Sound** for a MIDI take (a microphone or **No sound**); **Play the passage along** (an `Audio` of the Current at `playbackRate = 1 / speed`, pitch kept), **Microphone** (the `audioinput` devices, shown when there are several, the choice kept in `localStorage`), `LiveLevelBars`, Record / Stop (`useRecorder`, which asks for the device with echo cancellation, noise suppression and automatic gain off: they are made for speech and cut a piano); a take is sent (`passagesApi.addTake`) as soon as it stops. **Record** is disabled with its reason where the page cannot use the microphone (`navigator.mediaDevices` is missing off a secure address) |
| The promotion dialog | `passagesApi.facts` for the mode and the audio (**Keep the original audio** / **Use my recording**, a `Segmented`, for the window), the length change and the marks that go, only when there are; **Promote** calls `passagesApi.promote` with the mode and the audio, then opens the song's Sheet step with `promoted` in the navigation state (the cursor goes where the take went in; the undo is the last step of the sheet's log) |

`data-passage-page`, `data-passage-current`, `data-passage-proposal`, `data-passage-range` and
`data-passage-recorder` are read by `check:passage`.

### 3.2 From other projects (Phase 10)

`pages/compose/ComposePage.tsx` ([`context/frontend/playlists.md`](../../../context/frontend/playlists.md)
section 1), inside the shell with the sidebar closed:

| Part | How |
|---|---|
| The header | Back to Projects, "From other projects", **Save as integrated playlist** and **Save as song** (disabled with no passage); each opens `SaveDialog` (a title, the first passages' titles at first), then `POST /projects/compose` and the new project's Sheet step |
| The list | `state/composeDraft.ts`: `useComposeDraft()` keeps the passages (`{key, part, project, title, fromMs, toMs, join, subheader}`) in `localStorage` (`aitu.compose.draft`), emptied on save. Drawn as `RailRow`s with `useRowDrag`, a number, the stretch or "Whole", a `⋯` (Move up, Move down, Remove); between two rows `JoinControl`: a `Segmented` **Sequential** / **Subheader** and, for a subheader, its **Title** |
| The picker | `GET /projects?layer=vault&layer=private` with notes, as `ListRow`s (a version is "<song> (<version>)", the layer as status), a filter. A click reads the parts (`GET /projects/{id}/parts`) and the status of the part |
| The source | Its name, a **Part** select for several parts, **Choose another project**, **Add the whole sheet** (or **Add the whole project** without a sheet); `SheetPage` read only with `stretchAction` **Add this stretch** |

`data-compose-page`, `data-compose-picker`, `data-compose-source`, `data-compose-passages`,
`data-compose-passage` are read by `check:compose`.

---

## 4. Play mode (Phase 11)

`pages/play/` ([`context/frontend/play-mode.md`](../../../context/frontend/play-mode.md)), outside the
shell.

| Module | Role |
|---|---|
| `PlayPage.tsx` | The page: reads what it plays, draws each song (`data-play-song`) with its title and byline and each part (`PlaySegment`, memoised, `data-play-part="<song>:<part>"`, `data-play-active`) as `SheetPage` with `step.play`; drawn when it comes within 800 px of the window (`IntersectionObserver`) and kept. One transport per part (`players`, a map kept in state); the active part (the one playing or moved last) gets Space and the button; a part that starts stops any other; `ended` starts the next part of the song (`startWhenReady`, waiting for its sheet) or, in a songs playlist, opens the next song (one song) or scrolls to it (all songs) without starting it. **Close** (`navigate(-1)`, a project's page when there is no history, the playlist with `?at=` for a playlist), **Next** (`play-next`), **Play / Pause** (`play-toggle`, `data-playing`), the menu (`data-play-menu`: **Sheet** / **Notes Falling**, **One song** / **All songs**, kept in `localStorage` `aitu.play.allSongs`). The buttons fade 2.5 s after the pointer stops while it plays. Space, the arrows (scroll by 40 % of the window), Escape. `?at`, `?view=falling`, `?all` hold the choices |
| `playQueue.ts` | What it plays: `projectQueue` (`GET /projects/{id}`, `GET /projects/{id}/parts`: one song, its parts with their subheaders when there are several) and `playlistQueue` (`GET /playlists/{id}`; a song with a stretch plays its first part from `fromMs` to `toMs`; the parts of a version of several parts read with `GET /projects/{id}/parts`); `PlayClock`, the time of the active part for Notes Falling, read without drawing the sheets again |
| `FallingView.tsx` | Notes Falling of the active part (`data-play-falling`): `GET /matrix/{uuid}/events` (`usePlayedNotes`), the notes of the next 3 s over the 88-key `Piano`, the keys sounding lit, drawn from `PlayClock` (`useSyncExternalStore`); no selection, no sound of its own |

The modules of the old Notes Falling page that nothing else used went with it (section 9). Still
shared:

| Module | Role |
|---|---|
| `piano/Piano.tsx`, `piano/keyPositions.ts` | The 88-key SVG keyboard, both orientations (Notes Falling and the sheet's keyboard panel) |
| `playback/ProgressBar.tsx` | The scrub bar of `ScorePlayer`, with a draggable handle |
| `playback/playedNotes.ts`, `noteVisuals.ts` | Which notes are sounding; how a falling note is drawn |
| `playback/useSpacebarPlay.ts` | Space plays and pauses, except inside a text field (the Audio and Notes steps) |
| `hooks/usePlayedNotes.ts` | Loads the notes of a part and the waveform of its recording (Notes Falling) |
| `hooks/useElementSize.ts` | The measured pixel box of an element (the sheet, the roll, the waveform, Notes Falling, the video frame) |

`hooks/useNoteSelection.ts` (the Lab's notes on a frame) was removed in implementation 03, Phase 10,
with no user left.

**The canvas selects; the scrub bar seeks.** One surface, one meaning: that is what lets a click on
a rectangle mean "this note" without also jumping the recording somewhere nobody asked for.

**The SVG is measured, not stretched.** It used to declare a viewBox in keyboard units and stretch
it with `preserveAspectRatio="none"`, so the two axes scaled by different amounts and every note
name came out squashed; no font size could have fixed it. The viewBox is the element's real pixel
box now: one unit is one pixel, text is undistorted, and a 2 px border is 2 px.

---

## 5. Audio and editing

| Directory | Contents |
|---|---|
| `components/audio/` | `LiveLevelBars`, `WaveformView`, `WaveformRangeSelector` (the stretch of a take, on the page of a passage); `CutWaveform` and `waveformPaint` (the Audio step, section 2.2) |
| `audio/` | `useRecorder` (MediaRecorder), `time.ts` (`mm:ss.cc`); `cuts.ts`, `frameView.ts`, `useCutPlayer.ts` (the Audio step) |
| `components/ProgressBanner.tsx` | The progress of **Write the proposal** on the page of a passage |

---

## 6. Printing

| Module | Role |
|---|---|
| `pages/piece/sheet/frames/FramesPdfDialog.tsx` | The panel: the pages the backend lays out (`GET /sheet/{uuid}/pages`), the preview, Download |
| `print/scorePdf.ts`, `drawPage.ts`, `pdf.ts`, `opentype.ts` | The PDF writer |

Detail on the PDF in [score-pdf.md](score-pdf.md).

---

## 7. The API client

`src/api/`, one module per backend router, re-exported from `api/index.ts` so components have a
single import path:

```ts
import { sheetApi, matrixApi, piecesApi } from "../api";
```

| Module | Router |
|---|---|
| `client.ts` | `API_BASE`, `request`, `upload`, `buildUrl`, `ApiError`, `SIGNED_OUT_EVENT` (sent on any `401` except from the sign in itself) |
| `auth.ts` | `/auth`: `login`, `logout`, `me`, `changePassword`; the type `Me` |
| `admin.ts` | `/admin`: `users`, `createUser`, `changeUser` (disable, enable, reset the password); the type `AdminUser` |
| `audio.ts` | `/audio`, including `list` (with `updatedAt`), `cuts`, `saveCuts`, `framePeaks`, `fileUrl`; `AudioItem` has `projectId`, `layer`, `basedOn` (Phase 6) |
| `projects.ts` | `/projects`: `list`, `get`, `create`, `rename`, `remove`, `duplicate`, `exportUrl`, `import`, and (Phase 6) `saveToLibrary`, `edit`; `ProjectRow` with its `library` and `editing` links; (Phase 10) `compose`, `parts`, `reorderParts`, `renamePart`, `joinPart`, `splitPart` |
| `playlists.ts` | `/playlists` (Phase 10): `list`, `get`, `create`, `rename`, `reorder`, `remove`, `addItems`, `changeItem`, `removeItem`; `PlaylistRow`, `PlaylistDetail`, `PlaylistItem` |
| `library.ts` | `/library` (Phase 6): songs, versions (rename, delete, history, restore), artists and their names (add, change, remove, merge) |
| `matrix.ts` | `/matrix`, including `transcribe`, `activeJob`, `progressUrl` |
| `pieces.ts` | `/pieces`: the status of a project's steps, its notes and hands |
| `sheet.ts` | `/sheet` (implementation 03): the new sheet (`FramesSheet`), its edits, undo and redo, the AI's job, the pages for the PDF, `words` and `saveWords` (`GET`/`PUT /sheet/{uuid}/words`); the shared types `FigureName`, `KEY_SIGNATURES`, `KEY_LABELS`, `KeySignatureName`, `LyricLine`, `PassageRef`. It took them from `timeScore.ts` (`/time`), removed in Phase 10 |
| `passages.ts` | `/passages` (Phase 9): `open`, `get`, `update`, `discard`, `addTake`, `deleteTake`, `readTake`, `facts`, `promote`; the types `OpenPassage`, `PassageTake`, `PromotionFacts`, `Promoted` |
| `youtube.ts` | `/youtube`, including `startDownload` (`POST /youtube/jobs`) |
| `video.ts`, `frameExamples.ts` | `/video`, `/frame-examples` (Lab) |

**`API_BASE` is `/api` by default**: a path on the page's own address. The Vite server passes it to
the backend without the prefix (`vite.config.ts`: `http://127.0.0.1:8765`, or `AITU_API_PROXY`,
which `compose.yaml` sets to the `backend` service). The JSON, the audio files and the progress
stream then share one port, and because they are on the page's own origin the browser sends the
session cookie `aitu_session` with every one of them, the `<audio>` elements and the `EventSource`
streams included. `VITE_AITU_API_URL` still points the page at another backend directly, which then
has no session (the backend's CORS sends no credentials).

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
| `PageHeader` | The title on the left, the primary action on the right, an optional back arrow and a middle row (the step tabs). No subtitle. Under 900 px the title keeps at least 160 px, so wide actions go to the next line instead of hiding it (Phase 13) |
| `Section` | A group inside a page: an optional small title and its controls, no description, no border (it replaced `SectionCard`) |
| `IconAction` | An icon button with its tooltip, which is also its name; the shortcut after the title; a tooltip that says why when disabled; tooltips never catch the pointer, so one never covers the button beside it |
| `PillButton` | `primary` (black), `secondary` (white, grey border), `quiet`, `danger`; `busy` shows a spinner |
| `Segmented` | One of 2 to 4 options, as one rounded group |
| `ListRow`, `RowMenu` | A row: title (truncated, full on hover), status and meta in fixed columns, the `⋯` menu |
| `DataTable` | Sticky header, sortable columns, rows per page, sized to its content; with `selected` and `onSelectedChange`, a checkbox per row and one for all (Phase 10). **Server mode** (Phase 13): `sort` and `onSortChange` (the rows come sorted), `paging` (`{count, page, perPage, onPage, onPerPage}`: the rows are one page); a column's `firstDirection` is the direction of its first click (`desc` for a popularity). Under 600 px the page controls keep only the range and the arrows |
| `FilterChip` | A filter as a chip (Phase 13): its name with a down arrow; a click opens its values with their counts (grouped under a heading when they have one), the first entry takes it off; chosen, it is filled, shows the value, and has a cross |
| `EmptyState` | One line, and the action that creates the first one |
| `ConfirmDialog` | The confirm button repeats the action ("Delete project"); **Cancel**; an optional third choice |
| `RailRow`, `rowDrag.ts` | A row of a side panel in order (the takes of a passage, the passages of From other projects, the parts): label, detail, shaded when on show, an optional number, `⋯`, bin and drag handle. `useRowDrag(count, onMove)` gives each row of a list its drag handlers and drop mark; `movedOrder` (Phase 10) |
| `Toolbox`, `FloatingBar` | The draggable toolbox and the floating bar, white with the one shadow; the bar wraps on a narrow screen |
| `MiniPiano` | 88 keys at half size, to pick one key; Spanish names on hover; arrows move by a semitone or an octave |
| `FigurePicker` | The figure icons (`FigureGlyph`) as a `Segmented`, the Spanish name in the tooltip |
| `StepTabs` | The steps of a project, section 2.1 |
| `Pill`, `TabBar` | A small toggle chip; a tab strip that follows the address (the Lab tabs) |
| `timestamps.ts`, `progress.ts`, `relativeTime.ts` | Tabular figures that never wrap; the 520 px width of a progress bar on its own; "2 h ago", "yesterday", "3 Oct" |

`MiniPiano` and `FigurePicker` are built in Phase 1 and used by the Transpose tab since Phase 7.
`music/transpose.ts` holds what moves with a transposition: `transposeKey` (of two names for one key,
the one with fewer accidentals), `transposeKeyChanges`, `transposeRowMarks` (fingering, notes taken
off, trills, grace notes), `figureSteps`, `shiftFigure`, `intervalWords`.

**The tokens** are in `tokens.ts`: the colours of the page, light and dark, the type scale (13, 14,
16, 20, 28 px), the radii (12 for inputs, 16 for floating things, a pill for buttons) and the one
shadow. `theme.ts` builds the MUI theme from them, with both schemes as CSS variables. The app
opens in the light one, and the user menu chooses Light, Dark or System; MUI keeps the choice in the
browser (`localStorage`, `mui-mode`) and switches its variables at once, so everything styled
through the theme follows by itself.

Drawing code that cannot read the theme (a canvas, an SVG) imports `ui`, the scheme in use, and
follows a change this way (Phase 4):

- `applyScheme(scheme)` of `tokens.ts` copies the light or the dark tokens into `ui` in place.
- `SchemeSync` (`ui/scheme.tsx`, in `main.tsx`) reads MUI's mode, calls `applyScheme` before its
  children render, and provides the scheme in use.
- A component that draws with `ui` calls `useScheme()` (`ui/schemeContext.ts`), so it re-renders with
  the new colours: `CutWaveform`, `WaveformView`, `LiveLevelBars`, `PeakPlot`, `ProgressBar`,
  `MiniPiano`, `StepTabs`, `SourceTab`. Nothing is remounted, so a page with unsaved changes keeps
  them.
- The Lab pages draw with many `ui` colours, so `LabLayout` redraws them from the start on a change
  (a `key` on the scheme).
- The piano sheet stays white paper in both schemes (`paper`, plan P-8), and the piano roll keeps its
  own colours.

**`palette.ts` keeps only the colours of the
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

**In implementation 02, Phase 11** (Notes Falling became a view of Play mode):
`pages/piece/NotesFallingPage.tsx` with its transport and synthesised piano (`playback/usePlayback.ts`,
`PlayerToolbar.tsx`, `PlaybackTransport.tsx`), its note removals (`hooks/useStagedRemovals.ts`,
`components/notes/NoteSelectionToolbox.tsx`, `PendingRemovalsBar.tsx`), `describeEvents`, and
`library/loadPerformanceScore.ts` (kept for Play mode, which reuses `SheetPage` instead).

**In implementation 02, Phase 9**: `components/editing/RangeRerecordPanel.tsx` (Epic 11),
`ComposePassagePanel.tsx` (Epic 13), `components/editing/useClickTrack.ts` (the metronome, removed after the user's review: its clicks were recorded with the take), `components/time/PeakPlot.tsx` and `api/editing.ts`: the page
of a passage (section 3.1) replaced the two panels, the sheet's Re-record tab and its Record panel,
and Notes Falling's **Re-record this stretch** (now **Record this stretch**, which opens that page).

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

What survives under `music/` is `noteNames.ts`, `figures.ts` and `transpose.ts`.

**With the old sheet (implementation 03, Phase 10, 2026-10-27):** the package
`@aimpromptu/grid-notation` (the sibling repository vexflow-v2: the dependency, its build step in the
Dockerfile, the `vexflow` build context of `compose.yaml`, the `optimizeDeps` exclusion of
`vite.config.ts`), the page `VexflowSheetPage`, `components/time/TimeScoreView.tsx` and
`ScorePdfDialog.tsx`, `pages/piece/sheet/{NoteToolbox,RangeToolbox,SheetToolbox,SheetFloatingBar,TransposeDialog}.tsx`,
`{useNoteActions,useRangeActions,sheetEdits}.ts`, `music/renderOverrides.ts`, `music/granularities.ts`,
`hooks/useNoteSelection.ts`, `pages/piece/HandsTab.tsx` and the Hands mode of `NotesEditor.tsx`
(`piecesApi.predictHands`, `noteEdits.setHands`, `applyPrediction`, `idsWithoutHand`), the decoration
keyboard of `PianoToolboxes.tsx`, `api/timeScore.ts`, and the scripts `check-render.mjs`,
`check-note-names.ts` and `sheet-library.mjs`. The page of the old renderer is kept as
[deprecated/grid-notation.md](../../deprecated/grid-notation.md).

---

## 10. Checks

```bash
cd aitu-frontend
npm run lint              # eslint .
npm run build             # tsc -b && vite build
npm run check:history     # undo and redo reverse exactly one press
npm run check:geometry    # the video piano overlay, against the backend's fixture
npm run check:cuts        # the Audio tab's cuts follow the backend's rules; playback jumps over them
npm run check:notes       # the Notes tab's typed arrays, live feed and edits
```

The checks that drive the browser need the running app (`make up` from the repository root). Each
works on temporary copies or uploads and deletes them at the end, so the library is never changed.
They sign in first through `scripts/session.mjs`: it signs in as the master user with
`AITU_MASTER_USERNAME` and `AITU_MASTER_PASSWORD` of `.env` at the repository root (or
`AITU_CHECK_USERNAME` and `AITU_CHECK_PASSWORD` from the environment), makes every `fetch` of the
script send the cookie (`signIn(base)`), and gives every Playwright page the same cookie
(`useSession(browser)`). Since implementation 02, Phase 3 a temporary copy is made by
`POST /projects/{id}/duplicate` (new ids, the same audio files). The checks that act on the sheet
find it through `scripts/frames-page.mjs` (the new sheet's hooks: `[data-frames-sheet]`, a
`data-note` on every notehead, a stretch marked in the strip above the first line):

```bash
npm run check:flow           # a project walked in a headless Chromium, every step, live transcription included
npm run check:projects       # the Projects page: New project, Add audio, Duplicate, Export, Import, Rename, Delete, a video file
npm run check:library        # My library on a copy: Save to library, a version read only, Edit, Replace, History, New version, Artists
npm run check:paste          # Copy and Paste between two copies, undo and redo, ⌘V over a stretch, From scratch
npm run check:passage        # Record this passage on a copy: takes, Write the proposal, Fit, the window, both promotions, undo and redo, Discard
npm run check:compose        # From other projects on two copies, the parts (rename, move, join, split), playlists
npm run check:play           # Play mode on copies: Space, the fading buttons, lyrics by frames, Notes Falling, playlists
npm run check:public         # the Public Library on copies
npm run check:requests       # requests, the review and sharing, with a temporary user
npm run check:journey        # the whole journey of three users, timed
npm run check:frames-sheet   # the new Sheet step: drawn, played (implementation 03, Phase 5)
npm run check:frames-edit    # picking notes, moving them to the other hand, undo and redo (Phase 6)
npm run check:frames-tools   # the note and range toolboxes (Phase 7)
npm run check:frames-toolbox # the sheet toolbox: Title, Key, Transpose, Lyrics, View (Phase 8A)
npm run time:flow            # the whole flow timed on three temporary pieces (upload, a duplicated library piece, YouTube)
npm run bench:roll           # the Notes tab at 10,000 rectangles and at 100 stream messages per second
node scripts/baseline-sheets.mjs   # screenshots of every screen that draws a sheet
```

`npm run screenshot -- <path>` takes one picture of the app; `--theme dark` takes it in the dark
scheme, and `--signed-out` takes it without signing in (the sign-in page).

`check:flow` exists because the page of a project is mostly gestures on a canvas and navigation between
tabs, which no unit check reaches. It takes about 2 minutes with the transcription
(`--no-transcribe` skips it). `bench:roll` opens `/dev/roll-bench`, so it needs a development build.

`check:render` (the old renderer drawn in jsdom) and `check:note-names` (the note toolbox's names
against the old sheet's spelling) were removed with the old sheet in implementation 03, Phase 10.

---

## 11. Where to look deeper

- [projects.md](../../../context/frontend/projects.md): Projects and the steps of a project
- [rendering.md](../../../context/frontend/rendering.md): how the sheet is drawn now (by the backend)
- [deprecated/grid-notation.md](../../deprecated/grid-notation.md): the vexflow-v2 renderer of the old sheet (removed)
- [score-pdf.md](score-pdf.md): the PDF writer
- [../backend/endpoints.md](../backend/endpoints.md): what the API client calls
- `aitu-backend/src/aitu_backend/sheet/README.md` sections 12 to 17: what the toolboxes write (`sheet.f1`)
