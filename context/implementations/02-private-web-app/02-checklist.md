# 02: The private web app: checklist

The status lookup for this implementation. The plan is [`02-plan.md`](02-plan.md), the brief is
[`02-prompt.md`](02-prompt.md), and the app it builds is [`../../app/01-app-context.md`](../../app/01-app-context.md).
Each phase report is `02-implementation-phase-N.md`, written by the agent that finishes the phase.

One phase is one agent session. A story is ticked only when every task under it is done. Every phase
also ticks its documentation story (plan section 19) and leaves `scripts/docs/check-links.py`
passing.

Status letters: `[x]` complete, `[p]` in progress, `[b]` blocked, `[c]` cancelled, `[ ]` not started.

## Decisions

The plan's section 3.

- [x] **Q-1** SQLite plus files inside `.database/`. Answered 2026-10-05.
- [x] **Q-2** The app on the home network, with a password login and a master user from `.env`. Answered 2026-10-05.
- [x] **Q-3** A total promotion may change the length (everything after moves); cuts stay ranges in the Personal Vault, and the audio is written again on save to the Private Library. Answered 2026-10-05.
- [x] **Q-4** Video into From source, Notes Falling into Play mode, the video development pages into Lab; the Playground, the old `.npz` library and the text-notation MVP deleted. Answered 2026-10-05.
- [p] **Q-5** The sources of the Public Library. Worldwide: `musicchartsarchive.com`, downloaded by the parallel work (`public-library-build/`). The `spain` and `catalan` regions and the fields that site does not give: raised in Phase 12.
- [ ] **Q-6** The popularity weights. Raised in Phase 12.
- [ ] **Q-7** Offline downloads per project, now or in the production version. Raised in Phase 6.
- [ ] **Q-8** Live notes from the video reader. Raised in Phase 5.

# [ ] Phase 0: The documentation repaired, and a baseline

## [ ] Story 0.1: The links
- [ ] Task 0.1.1 **The link checker**: `scripts/docs/check-links.py` checks every relative link of `context/`, `documentation/` and the READMEs, and exits non-zero on a broken one.
- [ ] Task 0.1.2 **The fix**: every link broken by the move into `01-mvp/` (about 120), and the plain-text old paths (`02b-local-setup.md` section 12.4, `09-prompt.md`, `library/02-download-prompt.md`).
- [ ] Task 0.1.3 **The indexes**: `context/implementations/README.md` rewritten for the two groups (01-mvp, 02) with rows for 07 and 09 and the numbering rule; the implementation part of `00-index.md`; `app/01-app-context.md`, the two language guides and this folder added.

## [ ] Story 0.2: The leftovers
- [ ] Task 0.2.1 `TODO.md`, `project-features.md`, `project-implementation-organization.md` and `context/research/piano-transcription/piano-transcription-python-solutions.md` moved to `context/archive/`, with a line in the archive README each.
- [ ] Task 0.2.2 `library/` moved to `scripts/seed/youtube-library/`, its script paths fixed.
- [ ] Task 0.2.3 `00-documentation-instructions.md` updated (implementation folders, the end of the migration rules, `08-security` planned).

## [ ] Story 0.3: The baseline
- [ ] Task 0.3.1 Screenshots of every current page into the report.
- [ ] Task 0.3.2 Backend test count and frontend checks, as the reference for later phases.

# [ ] Phase 1: The design system and the app shell

## [ ] Story 1.1: The design system
- [ ] Task 1.1.1 **Tokens** (`src/ui/tokens.ts`), light and dark, the MUI theme, Geist self-hosted; `palette.ts` keeps only the colours of the music.
- [ ] Task 1.1.2 **The shared components** of plan section 7.4; `PageContainer` and `SectionCard` deleted.

## [ ] Story 1.2: The shell
- [ ] Task 1.2.1 `AppShell` and the sidebar (Projects, Lab, the user menu as a placeholder), open and closed states, `⌘K` search as a placeholder that lists pieces.
- [ ] Task 1.2.2 The routes of plan section 6.3 for Phase 1; the old paths redirect.

## [ ] Story 1.3: The pages
- [ ] Task 1.3.1 The flow at `/projects/:id/:step`; the step tabs and the Source, Audio, Notes and Hands steps restyled (plan section 10.2).
- [ ] Task 1.3.2 Playground, YouTube page and old Piano Library removed from the UI; Notes Falling reachable from a project's menu; the video development pages under `/admin/lab/`.
- [ ] Task 1.3.3 `/scores`, `/sequence`, their frontend module and their documentation removed (Q-4).
- [ ] Task 1.3.4 The 13-check pass of the 09 guidelines on every page touched, with screenshots.

## [ ] Story 1.4: Documentation
- [ ] Task 1.4.1 `color-palette.md`, `frontend/README.md`, `pages.md`, `components.md`, `aitu-frontend/README.md`, `flow-page.md` (first move towards `projects.md`).

# [ ] Phase 2: The sheet page

## [ ] Story 2.1: The split
- [ ] Task 2.1.1 `RhythmPage.tsx` split into modules with no change of behaviour; the checks and screenshots identical.

## [ ] Story 2.2: The defaults
- [ ] Task 2.2.1 The default negra from the highest peak (backend, test); the note under D-09 in `decisions.md`.
- [ ] Task 2.2.2 The default key signature and octave brackets on first write.

## [ ] Story 2.3: The page
- [ ] Task 2.3.1 The cards and the captions removed; the floating bar; the sheet toolbox with Title, Key and Layout.
- [ ] Task 2.3.2 The range and note toolboxes as icon actions with tooltips; the speed changes as a range toolbox tab.
- [ ] Task 2.3.3 The line wrap checked on three widths and on resize; fixed where it fails.
- [ ] Task 2.3.4 Timings of the first piano sheet and of a hand move, against implementation 08.

## [ ] Story 2.4: Documentation
- [ ] Task 2.4.1 `annotations.md` updated and split under 200 lines a page.

# [ ] Phase 3: The `.database/` folder, the tables, the project bundle, the migration

## [ ] Story 3.1: The folder
- [ ] Task 3.1.1 `AITU_DATABASE_DIR`, the link to `/mnt/ssd2/aimpromptu/.database`, `.gitignore`, the Compose mount, `VERSION`.
- [ ] Task 3.1.2 SQLAlchemy and Alembic; every table of plan section 8.6.

## [ ] Story 3.2: The bundle
- [ ] Task 3.2.1 `notes.pmn` version 2 and `sheet.json` (adapters and tests).
- [ ] Task 3.2.2 The audio store by hash, `audio_refs`, the timeline with cuts as segments, the cached joined audio.
- [ ] Task 3.2.3 Every writer moved to the bundle through `storage/paths.py`; the routes keyed by uuid work on parts.
- [ ] Task 3.2.4 The old `/library` router and its storage modules deleted.

## [ ] Story 3.3: The migration
- [ ] Task 3.3.1 `scripts/migrate/to_database.py` (plan section 8.9), tested on a fixture tree.
- [ ] Task 3.3.2 Run on a copy, then for real; the report with counts and sizes.
- [ ] Task 3.3.3 `make db-backup`, `db-restore`, `db-check`, `db-reindex`.

## [ ] Story 3.4: Documentation
- [ ] Task 3.4.1 `07-database.md` and `paths-and-data.md` rewritten; `piano-matrix-notation.md`, `pieces-and-revisions.md`, `backend/README.md`, `02-tech-stack.md`, `04-local-development.md` updated.

# [ ] Phase 4: Users, login and the home network

## [ ] Story 4.1: The backend
- [ ] Task 4.1.1 Users, sessions, Argon2, the `/auth` routes, the slow-down after wrong passwords.
- [ ] Task 4.1.2 The session check on every route; the rights table of plan section 9.3 with a test per row and two users.
- [ ] Task 4.1.3 The master user from `.env`; jobs with an owner.

## [ ] Story 4.2: The frontend
- [ ] Task 4.2.1 The login page; the user menu (password, theme, sign out); Admin → Users.

## [ ] Story 4.3: The network
- [ ] Task 4.3.1 `WEB_BIND`, Vite's allowed hosts; the app opened from the Mac at `http://ubuntu:5173`.

## [ ] Story 4.4: Documentation
- [ ] Task 4.4.1 `context/08-security.md` (new); `02b-local-setup.md` section 12, `04-local-development.md`, `README.md`, `09-coding-conventions.md`, `api.md`, `endpoints.md`.

# [ ] Phase 5: Projects and the Personal Vault

## [ ] Story 5.1: The projects
- [ ] Task 5.1.1 The `/projects` routes (list, create, rename, delete, duplicate).
- [ ] Task 5.1.2 The Projects page and **New project** with its three choices.

## [ ] Story 5.2: From source
- [ ] Task 5.2.1 The Source step (file, YouTube audio or video) on projects.
- [ ] Task 5.2.2 The Audio step with **add audio** (several files in one timeline).
- [ ] Task 5.2.3 The video as a step of the project, its temporary files; Q-8 measured.

## [ ] Story 5.3: Export and import
- [ ] Task 5.3.1 The `.aitu` file and its round-trip test.

## [ ] Story 5.4: Documentation
- [ ] Task 5.4.1 `projects.md` (from `flow-page.md`), `pieces-and-revisions.md`, `endpoints.md`.

# [ ] Phase 6: The Private Library

## [ ] Story 6.1: Saving
- [ ] Task 6.1.1 **Save to library** (artist, song, version name); the audio written on save; temporary files deleted.

## [ ] Story 6.2: The pages
- [ ] Task 6.2.1 Songs, one song with its versions, Artists with their names.
- [ ] Task 6.2.2 Edit through a vault copy; Replace the version or Save as a new version; history.
- [ ] Task 6.2.3 Duplicate and Export from any version.

## [ ] Story 6.3: Documentation
- [ ] Task 6.3.1 `context/music-library/` started; `projects.md`, `endpoints.md`.

# [ ] Phase 7: The sheet toolbox: transposition, lyrics, keys and clefs of passages

## [ ] Story 7.1: Transposition
- [ ] Task 7.1.1 `MiniPiano` and `FigurePicker`.
- [ ] Task 7.1.2 Notes transposition (preview, counts, undo).
- [ ] Task 7.1.3 Figures transposition (preview, beams and overrides removed and restored by undo, the next **From**).

## [ ] Story 7.2: Lyrics
- [ ] Task 7.2.1 The pool, drag and drop, frame snapping, offset, size, width, line breaks.
- [ ] Task 7.2.2 The edit toolbar (select, merge, split, back to pool, delete); old words read as placed pieces.

## [ ] Story 7.3: Passages
- [ ] Task 7.3.1 **Key for this passage**.
- [ ] Task 7.3.2 The automatic clef rule in `vexflow-v2`, its constants, screenshots, `npm test`.

## [ ] Story 7.4: Documentation
- [ ] Task 7.4.1 `annotations.md` pages, `rendering.md`, `rhythm-and-annotations.md` (`sheet.json`).

# [ ] Phase 8: Copy and paste, and From scratch

## [ ] Story 8.1: Copy and paste
- [ ] Task 8.1.1 The clipboard reference; the backend paste (notes, metadata, audio segments, the insert); undo.
- [ ] Task 8.1.2 Across projects and layers, with the read check.
- [ ] Task 8.1.3 The note under rule 2 in `wall-clock-rewrite.md`.

## [ ] Story 8.2: From scratch
- [ ] Task 8.2.1 The empty project, Record and Paste on a blank sheet.
- [ ] Task 8.2.2 Playback across several audio files, checked at every join.

## [ ] Story 8.3: Documentation
- [ ] Task 8.3.1 `editing.md`, `editing-and-compose.md`.

# [ ] Phase 9: Recording in Sheet

## [ ] Story 9.1: The page
- [ ] Task 9.1.1 Current and Proposal; recording and takes.
- [ ] Task 9.1.2 The condensed steps: range of the take, then transcription, hands and sheet with the passage's key and figure.

## [ ] Story 9.2: Promote
- [ ] Task 9.2.1 The window and the speed; keep the original audio or use the recording.
- [ ] Task 9.2.2 Replace the whole passage, with the length confirmation; undo after promotion.
- [ ] Task 9.2.3 The staged session generalised; the two old panels removed.

## [ ] Story 9.3: Documentation
- [ ] Task 9.3.1 `editing.md`, `editing-and-compose.md`, `projects.md`.

# [ ] Phase 10: From other projects, and the playlists

## [ ] Story 10.1: From other projects
- [ ] Task 10.1.1 The compose page: picker, read-only sheet, passages, sequential or subheader, reorder.
- [ ] Task 10.1.2 **Save as song** and **Save as integrated playlist** with parts.

## [ ] Story 10.2: Integrated playlist
- [ ] Task 10.2.1 Parts on the Sheet step, subheaders, the sub-song panel, reorder, join and split.

## [ ] Story 10.3: Songs playlist
- [ ] Task 10.3.1 My library → Playlists; **Make a playlist** from a selection.

## [ ] Story 10.4: Documentation
- [ ] Task 10.4.1 `projects.md` (playlists), `endpoints.md`.

# [ ] Phase 11: Play mode

## [ ] Story 11.1: The page
- [ ] Task 11.1.1 Close, Next, Play and Pause, the scroll that keeps the cursor in the middle, the keys.
- [ ] Task 11.1.2 Lyrics by their frames; Notes Falling as a view.

## [ ] Story 11.2: Playlists
- [ ] Task 11.2.1 The next song, the list when closed, the continuous page.
- [ ] Task 11.2.2 Entry points everywhere; `PerformancePage` removed.

## [ ] Story 11.3: Documentation
- [ ] Task 11.3.1 `context/frontend/play-mode.md` (new).

# [ ] Phase 12: The music library data reconciled

Starts once the parallel work ([`public-library-build/`](public-library-build/)) has data in `.music-library/`. Writes nothing into that folder or its scripts.

## [ ] Story 12.1: The reconciliation
- [ ] Task 12.1.1 Read the parallel work's plan, response and database.
- [ ] Task 12.1.2 `context/music-library/reconciliation.md`: the mapping to plan section 8.6, the gaps in both directions (genre, tags, regions; lyrics, album chart history), the identity rule for songs and artists across runs.
- [ ] Task 12.1.3 Only the missing fields added to section 8.6 and its Alembic migration.
- [ ] Task 12.1.4 The import script the Phase 13 import starts from; the 31 seed songs checked.

## [ ] Story 12.2: Popularity
- [ ] Task 12.2.1 The formula of plan section 15.6 run on the downloaded chart history (songs, and albums if kept).
- [ ] Task 12.2.2 Tuned on a list the user ranks by hand (human step).

## [ ] Story 12.3: Decisions
- [ ] Task 12.3.1 Q-5 (the regions not covered, the missing fields) and Q-6 raised with a recommendation each.

# [ ] Phase 13: The Public Library

## [ ] Story 13.1: The import
- [ ] Task 13.1.1 The reconciled data of Phase 12 into public rows, safe to run again; the seed songs present.

## [ ] Story 13.2: The pages
- [ ] Task 13.2.1 Search, filter chips, sort.
- [ ] Task 13.2.2 One song (metadata, fixed versions, Other versions by user), artists, public playlists.
- [ ] Task 13.2.3 Likes.

## [ ] Story 13.3: Pull
- [ ] Task 13.3.1 **Add to my library** for a song, an artist, a playlist.

## [ ] Story 13.4: Documentation
- [ ] Task 13.4.1 `music-library/ontology.md`, `popularity.md`.

# [ ] Phase 14: Requests, the Admin panel and sharing

## [ ] Story 14.1: Requests
- [ ] Task 14.1.1 The three kinds with items; the Publish dialog; My requests.
- [ ] Task 14.1.2 Changes asked and resent; withdraw.

## [ ] Story 14.2: Review
- [ ] Task 14.2.1 The review list and page, side by side, partial acceptance.
- [ ] Task 14.2.2 The publishing transaction; the creator's username on the version.

## [ ] Story 14.3: Sharing
- [ ] Task 14.3.1 Share a Private Library; **Shared**; the counts in the sidebar.

## [ ] Story 14.4: Documentation
- [ ] Task 14.4.1 `music-library/requests.md`, `08-security.md` (rights), `endpoints.md`.

# [ ] Phase 15: The checks, the documentation, and closing

## [ ] Story 15.1: The journey
- [ ] Task 15.1.1 The whole journey with two users on temporary copies, with timings.

## [ ] Story 15.2: The cleanup
- [ ] Task 15.2.1 Old redirects and the code that read `aitu-backend/data/` removed.

## [ ] Story 15.3: Documentation
- [ ] Task 15.3.1 `00-project-complete-overview.md`, `01-project.md`, `05-deployment.md` rewritten; run instructions in one place; the folder README marked complete.
