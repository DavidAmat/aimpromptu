# 02: Phase 1 report: the design system and the app shell

Plan: [`02-plan.md`](02-plan.md) sections 6, 7 and 10.2, and section 20, Phase 1. Checklist:
[`02-checklist.md`](02-checklist.md). Branch `feat/phase-1`, made from `master` at `603570f`. Done
2026-10-05 on the Ubuntu machine.

# 1. Summary

| Story | Result |
|---|---|
| 1.1 The design system | `src/ui/tokens.ts` (light and dark), the MUI theme with both schemes as CSS variables, Geist self-hosted; `palette.ts` keeps only the colours of the music. 19 shared components in `src/ui/`; `PageContainer`, `SectionCard` and `Placeholder` deleted |
| 1.2 The shell | `AppShell` and `Sidebar` (Projects, Lab under Admin, the user menu as a placeholder), open and closed, `⌘K` Search over the projects. The routes of plan section 6.3 for Phase 1; every old path redirects |
| 1.3 The pages | Projects; the flow at `/projects/:id/:step` with the Source, Audio, Notes and Hands steps restyled; Playground, YouTube page, old Piano Library and performance page removed; Notes Falling from a project's `⋯` menu; the video pages under `/admin/lab/`; `/scores`, `/sequence` and their frontend module removed; the 13-check pass, 33 screenshots |
| 1.4 Documentation | `color-palette.md`, `frontend/README.md`, `pages.md`, `components.md`, `aitu-frontend/README.md`, `flow-page.md`; the text-notation pages to `documentation/deprecated/`; the platform pages that named the removed pages or routes |

Checks at the end: `tsc -b` and `npm run lint` clean, `npm run build` passes (the same chunk-size
warning as Phase 0), every `check:*` passes (`check:flow` 80 checks with the live transcription),
backend on the CPU 1,032 passed, 3 failed (the known three), 1 skipped,
`scripts/docs/check-links.py` 364 files, 0 broken links.

# 2. Story 1.1: the design system

## 2.1 Tokens, theme, font

- `src/ui/tokens.ts`: the tokens of plan section 7.2, light and dark, plus `lineStrong` (`#C7C7C7`),
  which replaces the old `surface.strongLine` (an axis or a lane edge that must stay visible). Also
  the type scale (13, 14, 16, 20, 28), `size` (button 36 / 32, sidebar 260 / 64), `radius` (input
  12, float 16, pill, row 8) and the one `shadow.float`. `ui` exports the scheme in use, for drawing
  code that cannot read the theme (canvases, SVG).
- `src/ui/theme.ts`: `createTheme({ cssVariables: { colorSchemeSelector: "data-scheme" },
  colorSchemes: { light, dark } })`. Overrides for Button (pill, black contained, white outlined,
  the danger colour through `.MuiButton-colorError`; MUI 9 has no `containedError` slot), IconButton,
  ToggleButton(Group), OutlinedInput (12 px, black focus), Popover, Menu, Dialog (16 px, the one
  shadow), Tooltip, Chip, Tabs (black indicator), Alert (white with a grey border, the icon keeps its
  colour), LinearProgress (black bar, 3 px), Switch, Divider. A module augmentation adds
  `background.sidebar`. `main.tsx` passes `defaultMode="light"`: the dark scheme is defined but not
  offered until the user menu's theme choice (Phase 4).
- Geist Sans variable (`Geist-Variable.woff2` of the npm package `geist` 1.7.2) is
  `public/fonts/geist.woff2`, SIL OFL 1.1 in `geist-LICENSE.txt`, preloaded by `index.html`.
  Canvas and SVG text that named Inter (which was never loaded) now names Geist. `timestampSx` lost
  `fontFamily: monospace`: Geist with `tabular-nums` keeps the digits still.
- `palette.ts` keeps `palette` (the user's aliases), `grays` (now documented as the greys of the
  drawn music), `semantic` (hands, roll, waveform, the marks on notes) and `handColors`. `surface`
  is gone: its 25 files now read `ui.*` from the tokens (`panel` and `page` to `bg`, `mutedText` to
  `text2`, `strongLine` to `lineStrong`). `semantic.steps` and `semantic.matrixKeyboard` were unused
  and are deleted.

## 2.2 The shared components

In `src/ui/`, all exported from `ui/index.ts`:

`AppShell` and `PageBody`, `Sidebar`, `PageHeader`, `Section`, `IconAction`, `PillButton`,
`Segmented`, `ListRow`, `RowMenu`, `DataTable`, `EmptyState`, `ConfirmDialog`, `Toolbox`,
`FloatingBar`, `MiniPiano`, `FigurePicker`, `StepTabs`, and the helpers `relativeTime` / `fullTime`.
`Pill` and `TabBar` stay (TabBar draws the Lab tabs).

Notes for later phases:

- **`IconAction` puts its tooltip with `describeChild`.** Without it, MUI's Tooltip copies the title
  as `aria-label` onto the wrapping span, and the button's name exists twice (Playwright's
  `getByLabel` found two elements). The button's own `aria-label` is the title.
- **`Toolbox`** is the old `components/common/ToolboxDialog.tsx`, moved with `git mv` and restyled
  (white title bar with a bottom line instead of the black bar, 16 px radius, `shadow.float`,
  `maxWidth: 100vw - 16`). **`FloatingBar`** is the old `components/common/FloatingBar.tsx`, moved and
  restyled (24 px radius, the shadow, `flexWrap: wrap` and `maxWidth: 100vw - 16`, so on a phone it
  wraps into rows instead of running off the edge).
- **`StepTabs`** is generic (`StepItem<K>`). Each tab carries `data-step` and `data-state`
  (`ready`, `running`, `stale`, `missing`, `unsaved`); the check scripts read those instead of the
  old tick icons.
- **`PageHeader`** uses `useFlexGap`: with MUI Stack `spacing`, margins break once an item is moved
  with `order` on a narrow screen. On a phone the middle row (the step tabs) goes under the title
  and the action stays beside it.
- **`MiniPiano`** is 624 px (the 88 keys of `piano/keyPositions.ts` at half scale) in a scroll
  container, `role="slider"`, arrows by a semitone or an octave, Spanish names (`spanishNoteShort`)
  as SVG `<title>`. **`FigurePicker`** is a `Segmented` of `FigureGlyph` icons. Neither is used by a
  page before Phase 7.
- **`/dev/ui`** (`pages/dev/UiGalleryPage.tsx`, development builds only, beside `/dev/roll-bench`)
  shows every shared component on one page: screenshot 33.

# 3. Story 1.2: the shell

- `layout/AppLayout.tsx` composes `AppShell` + `Sidebar`. The groups are Projects, then an "Admin"
  heading with Lab. The sidebar is open on list pages and closed inside a project
  (`/^\/projects\/(?!$)/`); a toggle holds per kind of page; under 900 px it is always the 64 px
  rail. `⌘K` / `Ctrl+K` opens Search anywhere.
- The user menu is a placeholder: "Local user" (true until Phase 4) with one item,
  **Keyboard shortcuts** (`layout/ShortcutsDialog.tsx`). No disabled fake items.
- `layout/SearchDialog.tsx`: loads `GET /audio/` when opened, filters by every word of the query,
  arrows and Enter, "No project matches “…”" when empty, skeleton rows while loading.
- `layout/routes.ts`: `ROUTES` (projects, projectNew, project, projectNotesFalling, lab*,
  labVideoOf, devRollBench, devUi), `PROJECT_PATTERN`, `LAB_EXAMPLE_PATTERN`, `LAB_TABS`,
  `LEGACY_REDIRECTS`. `layout/LegacyRedirect.tsx` carries `:id`, `:slug`, the `*` rest and the
  query string. Measured redirects (screenshot script): `/piece/<id>/audio` to
  `/projects/<id>/audio`, `/piece/new` to `/projects/new`, `/playground/rhythm` and `/library...` to
  `/projects`, `/youtube` to `/projects/new`, `/video/notes?video=abc` to
  `/admin/lab/notes?video=abc`, `/video/examples/7years` to `/admin/lab/examples/7years`, `/` to
  `/projects`.

# 4. Story 1.3: the pages

## 4.1 Projects, and one backend field

`pages/ProjectsPage.tsx`: one `ListRow` per piece, newest change first, the step reached, when it
changed (relative, full date in a tooltip), and a `⋯` menu: Open, Notes Falling (disabled without
notes), Rename (a dialog), Delete (a `ConfirmDialog`, "Delete project"). Loading is skeleton rows;
an error says what failed with **Try again** (screenshot 02, with `/audio/` answering 503); empty is
"No projects yet" with **New project**.

The step of each row needs `GET /pieces/{id}/status`, measured at about 28 ms per piece (1.1 s for
39 in sequence). Putting it in the list would make the list, and Search, a second slower. So the page
draws the rows at once and asks the statuses six at a time; a step fills in when its answer arrives.

"When it changed" did not exist: `AudioMetadata` has `createdAt` only. `api/audio.py` adds a computed
`updatedAt` to `GET /audio/` and `GET /audio/{uuid}`: the newest `st_mtime` of the files directly in
the piece's folder (one `stat` per file, no read; history, staging and video not looked at). This is
not a storage change. `test_upload_endpoint_round_trip` checks it is set and does not go back after a
rename.

## 4.2 The page of a project

`pages/piece/PiecePage.tsx` reads `:id` (was `:uuid`). Its header is a `PageHeader`: back arrow to
Projects, the title (or "New project"), the `StepTabs` in the middle, a `RowMenu` with Notes Falling.
The chips of duration, source and engine left the header (the engine name is a technical word, plan
section 7.5). The leave dialog is a `ConfirmDialog` ("Save your changes?", **Stay**, **Discard**,
**Save and continue**). `PieceIndex.tsx` is deleted (`/piece` redirects to Projects).

- **Source** (`SourceTab.tsx`): on a new project, one drop zone ("Drop an audio file", **Choose
  file**, drag and drop) and **Paste a YouTube link** with a `Segmented` **Audio / Video**. Audio:
  `POST /youtube/jobs` with a thin bar from the progress stream, then the Audio step. Video:
  `POST /video/download` (one long request, indeterminate bar), then `ROUTES.labVideoOf(id)`. No
  name field: a project takes the file's or the video's name. On an existing project the step shows
  where its audio came from (kind, length, the file name or the YouTube link).
  **The drop zone takes audio only**: the backend has no video upload. Plan section 10.2 says "Drop
  an audio or video file"; the video file is Phase 5 work, with the video as a step of the project.
- **Audio** (`AudioTab.tsx`): top row with the playhead time, the selection, the cut summary and the
  primary **Transcribe** (its label still says "Save and transcribe", "Transcribe again"); the
  waveform full width; a `FloatingBar` of `IconAction`s (play jumping over the cuts, play the
  selection, cut, restore, undo, redo, the four zooms, discard, **Save**). The instruction
  paragraph, the "Every transcription uses MuScriptor" line and the three monospace readout lines
  are gone. The root carries `data-selection`, `data-view` and `data-cuts` for `check:flow`. The old
  `SaveBar` is deleted: two floating bars sat in the same corner.
- **Notes and Hands** (`NotesEditor.tsx`): the primary action (**Continue to Hands**, **Continue to
  Sheet**) moved to the top row; zooms and Follow are `IconAction`s; the note count is plain text;
  "Transcribing with MuScriptor…" is "Transcribing…"; the "Transcribed in" and "Predicted in" chips
  are gone (`data-predicted` keeps what the prediction changed). On Hands the floating toolbox holds
  Predict hands, Predict every note again, the filter **Both / Right / Left**, **To right**,
  **To left**, the counter of notes without a hand, and **Save**. The missing state is an
  `EmptyState` with **Open the Audio step**.
- **Sheet**: unchanged in behaviour, as the plan says (Phase 2). `RhythmPage.tsx` moved to
  `pages/piece/`; its `SectionCard`s are `Section`s without their descriptions, and its `Frame` no
  longer prints the subtitle paragraph (the `subtitle` props stay for Phase 2 to delete).
- **Notes Falling** moved to `pages/piece/` and renders inside the project page at
  `/projects/:id/notes-falling`, reading the project from the address (`usePiece`) instead of the
  Playground's working piece; title "Notes Falling", no subtitle or caption.

## 4.3 Removed (Q-4)

Frontend: `layout/PlaygroundLayout.tsx`, `layout/VideoLayout.tsx`, `layout/BackendStatus.tsx` (the
"API online" chip), `pages/playground/InputPage.tsx`, `pages/YouTubePage.tsx`,
`pages/LibraryPage.tsx`, `pages/PerformancePage.tsx`, `components/library/PlaylistSection.tsx`,
`library/playId.ts`, `api/library.ts`, `api/scores.ts`, `music/types.ts`, `ui/PageContainer.tsx`,
`ui/SectionCard.tsx`, `ui/Placeholder.tsx`, `pages/piece/PieceIndex.tsx`,
`components/piece/{StepTabs,SaveBar,YouTubeDownload}.tsx`,
`components/audio/{AudioLibraryList,AudioUpload,AudioRecorder}.tsx`,
`components/input/{TranscriptionSettings,ComposeNewPiece}.tsx`.

**`PerformancePage` is removed one implementation phase early.** The plan kept it until Phase 11 as
"the base of Play mode", but it only read the old `.npz` Piano Library (empty on disk), whose page
and `/library` client this phase removes, so nothing could open it. Its loader
`library/loadPerformanceScore.ts`, which builds a sheet from a stored audio and its rhythm, is kept
for Play mode. Plan sections 5 and 20 and checklist Task 11.2.2 now say so.

Backend: `api/scores.py`, `schemas/score.py` (and its three exports), `storage/paths.py::scores_json_path`,
`data/example-scores.json`, the four `/scores` and `/sequence` smoke tests and the path test. A new
test checks both routes answer 404 or 405. `matrix/text_notation.py` stays: `test_matrix_model.py`
and `test_matrix_validator.py` build matrices with it. The two old notebooks that wrote
`example-scores.json` (`notebooks/dummy-matrix/`, `notebooks/88-keys-matrix/`) are left as history.

The old `/library` router (playground, `.npz`) is still in the backend: Phase 3 deletes it with its
storage modules, as planned. No screen calls it now.

## 4.4 The Lab pages

The five video pages render under `layout/LabLayout.tsx` (title "Lab", `TabBar` of `LAB_TABS`).
Their `PageContainer` titles and subtitles are gone, their `SectionCard`s are `Section`s without
descriptions; their inner content is unchanged. They are development tools; a deeper restyle is
not in this phase.

# 5. The 13 checks of the 09 guidelines

Run on every page touched, with the screenshots of [`screenshots/phase-1/`](screenshots/phase-1/)
(1440 × 900 unless named narrow or wide; pages with a piece on a **temporary copy** of Superestrella,
`64897cf7`, made from `b99bc3ae` without its history, staging and video, deleted at the end).

| # | Check | Result |
|---|---|---|
| 1 | One sentence per screen | Projects: open or start a project. Source: bring the audio in. Audio: choose the region, then transcribe. Notes: check and edit the notes. Hands: give each note a hand. Lab: work on a video. Search: open a project by name |
| 2 | Every sentence a label, control or fact | Deleted: the Source descriptions, the Audio instructions and engine line, the Notes Falling subtitle and caption, the Lab subtitles and descriptions, the sheet's subtitle paragraph. Kept: warnings that apply (stale notes, cuts that make notes stale), the delete consequence |
| 3 | Words above the first content | Projects 3 ("Projects", "New project"); a project: the title and five step names |
| 4 | Very wide (2,400 px, shots 31, 32) | List pages keep 960 px; the project page uses the width; controls stay beside their content; no gap opens |
| 5 | Narrow (390 px, shots 27 to 30) | No horizontal overflow (measured 0 px on each); the floating bar wraps; titles truncate with the full value on hover; the step tabs scroll inside their row |
| 6 | Longest, shortest, none | A 200-character title truncates in its row (shot 33); a missing step shows a dash; a missing date shows a dash |
| 7 | Buttons say what happens | "New project", "Choose file", "Transcribe", "Continue to Hands", "Delete project", "Rename", "Try again", "Save and continue". No OK, Yes or Submit |
| 8 | Helper lines | None left that repeats a label |
| 9 | Loading, empty, partial, error | Skeleton rows; "No projects yet" with New project; a row's step fills in late with a skeleton; the error with Try again (shot 02); "No project matches" (shot 03) |
| 10 | Tab through it | Projects: logo, sidebar toggle, Search, Projects, Lab, Account, New project, then each row and its `⋯`; Enter opens. Every icon button is reachable and named |
| 11 | Internal names | Gone from the screen: "API online", engine names, "ms per column", "MuScriptor". Lab keeps its technical words (development pages) |
| 12 | Would a first-time user know each label | Yes for the shell and the steps; the icon actions explain themselves in tooltips |
| 13 | (pass 13 of the guidelines: the anti-patterns) | No lecture, no caveat wall, no far-away control (the table's page controls were moved under the table, shot 33), no confident zero |

| Shot | Page |
|---|---|
| 01 | Projects |
| 02 | Projects, the list failing (503) |
| 03, 04 | Search: nothing matches; "super" |
| 05 to 07 | A row's `⋯` menu; Rename; the delete confirmation |
| 08, 09 | The user menu; Keyboard shortcuts |
| 10 | The sidebar closed |
| 11 | New project (Source) |
| 12 | Source of a project with audio |
| 13, 14 | Audio; Audio with an unsaved cut (then discarded) |
| 15 to 17 | Notes; Hands; a tooltip of the hands toolbox |
| 18 | Sheet, unchanged until Phase 2 |
| 19 | Notes Falling |
| 20 to 25 | Lab: Video, Calibration, Detection, Notes, Examples, one example |
| 26 | Page not found |
| 27 to 30 | Narrow: Projects, New project, Audio, Hands |
| 31, 32 | Wide: Projects, Audio |
| 33 | `/dev/ui`, every shared component |

No page logged a console error, except the expected 404s of the made-up video id `abc` in the
redirect check.

# 6. The checks

| Check | Result |
|---|---|
| `tsc -b`, `npm run lint` | clean |
| `npm run build` | passes, the same chunk-size warning as Phase 0 |
| `check:render`, `check:history`, `check:note-names`, `check:geometry`, `check:cuts`, `check:notes` | 60, all, 15, 2, all, all passed |
| `check:flow` (with the transcription; the GPU was free) | 80 checks passed, no console error |
| Backend on the CPU (Phase 0, section 4.2) | 1,032 passed, 3 failed, 1 skipped (1,036 tests) |
| `scripts/docs/check-links.py` | 364 files, 0 broken links |

The backend count is 4 lower than the 1,040 of Phase 0 because 5 tests of the deleted routes went
and 1 test that they are gone came. The 3 failures are the same as Phase 0: the known
`test_the_worked_example_at_00_46_prints_three_equal_corcheas`, and the two Transkun tests that fail
on the CPU only.

`check:flow`, `time:flow` and `bench:sheet` were updated to the new paths and names: `/projects/...`,
the tab names without numbers, `data-state` instead of the tick icons, the new button names, and the
Audio step's data attributes instead of its old readout lines. `time:flow` and `bench:sheet` were not
run (they are timings, Phase 2 measures the sheet). After every check, `aitu-backend/data/audio/`
has its 39 pieces, as before.

# 7. Documentation

- Rewritten: [`../../colors/color-palette.md`](../../colors/color-palette.md) (tokens and the
  colours of the music), [`../../frontend/README.md`](../../frontend/README.md),
  [`../../frontend/pages.md`](../../frontend/pages.md),
  [`../../frontend/flow-page.md`](../../frontend/flow-page.md) (now "Projects and the steps of a
  project"; renamed `projects.md` in Phase 5),
  [`components.md`](../../../documentation/services/frontend/components.md) sections 1, 2, 5, 6, 8, 9,
  [`aitu-frontend/README.md`](../../../aitu-frontend/README.md).
- Moved to `documentation/deprecated/` with a banner: `notation-and-parsing.md` (from
  `context/backend/`), `schemas.md`, `sequence-logic.md` (from `documentation/services/backend/`).
- Made true where they named the removed pages or routes: `00-project-complete-overview.md`,
  `03-services-overview.md`, `04-local-development.md`, `07-database.md`, `backend/api.md`,
  `backend/README.md`, `02-notation-spec.md` (its scope line), `endpoints.md` (the MVP rows and
  section 9, `updatedAt`, section 6's frontend path), `paths-and-data.md`, `00-index.md`,
  `documentation/services/README.md`. Their full rewrites stay with the phases of plan section 19.

# 8. Learnings for later phases

- **Run the frontend checks against the container's Vite.** After new imports, Vite re-optimises its
  dependencies and the first page load answers 504 "Outdated Optimize Dep"; load again.
- **Read data attributes in browser checks, not on-screen words.** The minimal UI removes text the
  checks used to read. `data-step`, `data-state`, `data-selection`, `data-view`, `data-cuts`,
  `data-unsaved`, `data-predicted` are there for that.
- **A scratch Playwright script needs `node_modules`.** From the scratchpad, link
  `aitu-frontend/node_modules/playwright` and `playwright-core` into a `node_modules/` beside it.
- **MUI 9 theme overrides**: no `containedError` / `textError` slots; use the class selectors
  (`.MuiButton-colorError`) inside `contained` or `root`.
- **Dark mode**: the theme and the tokens are ready, but drawing code reads `ui` (the light tokens)
  directly. Phase 4 must make `ui` follow the chosen scheme, or pass the tokens down, before it
  offers the choice.
