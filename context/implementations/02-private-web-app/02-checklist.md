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
- [x] **Q-5** The sources of the Public Library (left open when the implementation closed; closed by Phases 16 and 18). Worldwide: `musicchartsarchive.com`, downloaded by the parallel work (`public-library-build/`; in fact the US chart). The `spain` and `catalan` regions, the genres and the 8 seed songs not on that chart: raised in Phase 12 with a recommendation ([report](02-implementation-phase-12.md) section 9). The regions became Q-9 (Phase 16); the genres and tags became **Phase 18** (added 2026-10-19), from Wikidata, built 2026-10-19 (Q-11).
- [x] **Q-6** The popularity weights. **Answered 2026-10-16:** objective criteria instead of a hand ranking; the plan's formula with the power of a week's points at 8 ([report](02-implementation-phase-12.md) section 5.3).
- [x] **Q-7** Offline downloads per project: **left for the production version**. Answered 2026-10-15 (raised in Phase 6).
- [x] **Q-8** Live notes from the video reader: **one job with its stages**, the notes at the end (61 s for a 3:09 video, measured in Phase 5). Answered 2026-10-15.
- [x] **Q-9** The sources of the `spain` and `catalan` regions, from the 60s to today (takes over the region part of Q-5). **Answered 2026-10-18: the recommendations**: spanishcharts.com, los40.com, kworb.net (Spotify Spain), the APECAT PDFs and Wikipedia; both APECAT top 30s (songs in Catalan, and Catalan labels) count as `catalan` ([`regional-sources.md`](../../music-library/regional-sources.md) section 6).
- [x] **Q-10** Spotify for the inferred popularity: its API gives no play count, and since 2026 no `popularity` either (checked 2026-10-19); its Developer Policy forbids feeding its content to a machine learning model. Raised 2026-10-18. **Answered 2026-10-19: kworb.net's all-time streams as a second signal** (the API only finds the artist's Spotify id); the fit keeps them only if they lower the error.
- [x] **Q-11** The genres and tags from Wikidata: the map of its genres onto the 13, a song with no genre of its own (its performer's, or none), which tag categories to import. Added 2026-10-19; raised 2026-10-19 after the measure, before any row is written ([report](02-implementation-phase-18.md) section 8). **Answered 2026-10-19: every recommendation**: the walk up "subclass of" with corrections by hand (flamenco stays latin); a song's own genres, else its performer's when a matched song ties the performer to the artist; films only, from the soundtrack links.

# [x] Phase 0: The documentation repaired, and a baseline

## [x] Story 0.1: The links
- [x] Task 0.1.1 **The link checker**: `scripts/docs/check-links.py` checks every relative link of `context/`, `documentation/` and the READMEs, and exits non-zero on a broken one.
- [x] Task 0.1.2 **The fix**: every link broken by the move into `01-mvp/` (about 120), and the plain-text old paths (`02b-local-setup.md` section 12.4, `09-prompt.md`, `library/02-download-prompt.md`).
- [x] Task 0.1.3 **The indexes**: `context/implementations/README.md` rewritten for the two groups (01-mvp, 02) with rows for 07 and 09 and the numbering rule; the implementation part of `00-index.md`; `app/01-app-context.md`, the two language guides and this folder added.

## [x] Story 0.2: The leftovers
- [x] Task 0.2.1 `TODO.md`, `project-features.md`, `project-implementation-organization.md` and `context/research/piano-transcription/piano-transcription-python-solutions.md` moved to `context/archive/`, with a line in the archive README each.
- [x] Task 0.2.2 `library/` moved to `scripts/seed/youtube-library/`, its script paths fixed.
- [x] Task 0.2.3 `00-documentation-instructions.md` updated (implementation folders, the end of the migration rules, `08-security` planned).

## [x] Story 0.3: The baseline
- [x] Task 0.3.1 Screenshots of every current page into the report.
- [x] Task 0.3.2 Backend test count and frontend checks, as the reference for later phases.

# [x] Phase 1: The design system and the app shell

## [x] Story 1.1: The design system
- [x] Task 1.1.1 **Tokens** (`src/ui/tokens.ts`), light and dark, the MUI theme, Geist self-hosted; `palette.ts` keeps only the colours of the music.
- [x] Task 1.1.2 **The shared components** of plan section 7.4; `PageContainer` and `SectionCard` deleted.

## [x] Story 1.2: The shell
- [x] Task 1.2.1 `AppShell` and the sidebar (Projects, Lab, the user menu as a placeholder), open and closed states, `⌘K` search as a placeholder that lists pieces.
- [x] Task 1.2.2 The routes of plan section 6.3 for Phase 1; the old paths redirect.

## [x] Story 1.3: The pages
- [x] Task 1.3.1 The flow at `/projects/:id/:step`; the step tabs and the Source, Audio, Notes and Hands steps restyled (plan section 10.2).
- [x] Task 1.3.2 Playground, YouTube page and old Piano Library removed from the UI; Notes Falling reachable from a project's menu; the video development pages under `/admin/lab/`.
- [x] Task 1.3.3 `/scores`, `/sequence`, their frontend module and their documentation removed (Q-4).
- [x] Task 1.3.4 The 13-check pass of the 09 guidelines on every page touched, with screenshots.

## [x] Story 1.4: Documentation
- [x] Task 1.4.1 `color-palette.md`, `frontend/README.md`, `pages.md`, `components.md`, `aitu-frontend/README.md`, `flow-page.md` (first move towards `projects.md`).

# [x] Phase 2: The sheet page

## [x] Story 2.1: The split
- [x] Task 2.1.1 `RhythmPage.tsx` split into modules with no change of behaviour; the checks and screenshots identical.

## [x] Story 2.2: The defaults
- [x] Task 2.2.1 The default negra from the highest peak (backend, test); the note under D-09 in `decisions.md`.
- [x] Task 2.2.2 The default key signature and octave brackets on first write.

## [x] Story 2.3: The page
- [x] Task 2.3.1 The cards and the captions removed; the floating bar; the sheet toolbox with Title, Key and Layout.
- [x] Task 2.3.2 The range and note toolboxes as icon actions with tooltips; the speed changes as a range toolbox tab.
- [x] Task 2.3.3 The line wrap checked on three widths and on resize; fixed where it fails (it never re-wrapped on a narrower window: fixed in `TimeScoreView`).
- [x] Task 2.3.4 Timings of the first piano sheet and of a hand move, against implementation 08.

## [x] Story 2.4: Documentation
- [x] Task 2.4.1 `annotations.md` updated and split under 200 lines a page.

# [x] Phase 3: The `.database/` folder, the tables, the project bundle, the migration

## [x] Story 3.1: The folder
- [x] Task 3.1.1 `AITU_DATABASE_DIR`, the folder `/mnt/ssd2/aimpromptu/.database` (a link in the repository at first; `AITU_DATABASE_DIR` in `.env` since 2026-10-06), `.gitignore`, the Compose mount, `VERSION`.
- [x] Task 3.1.2 SQLAlchemy and Alembic; every table of plan section 8.6.

## [x] Story 3.2: The bundle
- [x] Task 3.2.1 `notes.pmn` version 2 and `sheet.json` (adapters and tests).
- [x] Task 3.2.2 The audio store by hash, `audio_refs`, the timeline with cuts as segments, the cached joined audio.
- [x] Task 3.2.3 Every writer moved to the bundle through `storage/paths.py`; the routes keyed by uuid work on parts.
- [x] Task 3.2.4 The old `/library` router and its storage modules deleted.

## [x] Story 3.3: The migration
- [x] Task 3.3.1 `scripts/migrate/to_database.py` (plan section 8.9), tested on a fixture tree.
- [x] Task 3.3.2 Run on a copy, then for real; the report with counts and sizes.
- [x] Task 3.3.3 `make db-backup`, `db-restore`, `db-check`, `db-reindex`.

## [x] Story 3.4: Documentation
- [x] Task 3.4.1 `07-database.md` and `paths-and-data.md` rewritten; `piano-matrix-notation.md`, `pieces-and-revisions.md`, `backend/README.md`, `02-tech-stack.md`, `04-local-development.md` updated.

# [x] Phase 4: Users, login and the home network

## [x] Story 4.1: The backend
- [x] Task 4.1.1 Users, sessions, Argon2, the `/auth` routes, the slow-down after wrong passwords.
- [x] Task 4.1.2 The session check on every route; the rights table of plan section 9.3 with a test per row and two users.
- [x] Task 4.1.3 The master user from `.env`; jobs with an owner.

## [x] Story 4.2: The frontend
- [x] Task 4.2.1 The login page; the user menu (password, theme, sign out); Admin → Users.

## [x] Story 4.3: The network
- [x] Task 4.3.1 `WEB_BIND`, Vite's allowed hosts; the app opened from the Mac at `http://ubuntu:5173` (checked by the user on 2026-10-06, who then changed the master password).

## [x] Story 4.4: Documentation
- [x] Task 4.4.1 `context/08-security.md` (new); `02b-local-setup.md` section 12, `04-local-development.md`, `README.md`, `09-coding-conventions.md`, `api.md`, `endpoints.md`.

# [x] Phase 5: Projects and the Personal Vault

## [x] Story 5.1: The projects
- [x] Task 5.1.1 The `/projects` routes (list, create, rename, delete, duplicate); the step kept in `projects.step`.
- [x] Task 5.1.2 The Projects page and **New project** with its three choices (two disabled until Phases 8 and 10) and Import.

## [x] Story 5.2: From source
- [x] Task 5.2.1 The Source step (an audio or a video file, YouTube audio or video) on projects, for every user.
- [x] Task 5.2.2 The Audio step with **add audio** (several files in one timeline).
- [x] Task 5.2.3 The video as a step of the project, its temporary files; Q-8 measured.

## [x] Story 5.3: Export and import
- [x] Task 5.3.1 The `.aitu` file and its round-trip test.

## [x] Story 5.4: Documentation
- [x] Task 5.4.1 `projects.md` (from `flow-page.md`), `pieces-and-revisions.md`, `endpoints.md`.

# [x] Phase 6: The Private Library

## [x] Story 6.1: Saving
- [x] Task 6.1.1 **Save to library** (artist, song, version name); the audio written on save; temporary files deleted.

## [x] Story 6.2: The pages
- [x] Task 6.2.1 Songs, one song with its versions, Artists with their names.
- [x] Task 6.2.2 Edit through a vault copy; Replace the version or Save as a new version; history.
- [x] Task 6.2.3 Duplicate and Export from any version.

## [x] Story 6.3: Documentation
- [x] Task 6.3.1 `context/music-library/` started; `projects.md`, `endpoints.md`.

# [x] Phase 7: The sheet toolbox: transposition, lyrics, keys and clefs of passages

## [x] Story 7.1: Transposition
- [x] Task 7.1.1 `MiniPiano` and `FigurePicker` (built in Phase 1), in the **Transpose** tab.
- [x] Task 7.1.2 Notes transposition (preview, counts, undo): `POST /time/{id}/transpose`, exact undo; the key and the marks of a key move with the notes.
- [x] Task 7.1.3 Figures transposition (preview, beams and overrides removed and restored by undo, the next **From**).

## [x] Story 7.2: Lyrics
- [x] Task 7.2.1 The pool, drag and drop, frame snapping (`vexflow-v2` 0.43.0), offset, size, width (its frames), line breaks.
- [x] Task 7.2.2 The edit toolbar (select, merge, split, line break, size, back to pool, delete); old words read as placed pieces.

## [x] Story 7.3: Passages
- [x] Task 7.3.1 **Key for this passage**.
- [x] Task 7.3.2 The automatic clef rule in `vexflow-v2` (0.43.0, not pushed), its constants measured on the 38 pieces, screenshots, `npm test` (515).

## [x] Story 7.4: Documentation
- [x] Task 7.4.1 `annotations.md` pages, `rendering.md`, `rhythm-and-annotations.md` (`sheet.json`); `endpoints.md`, `components.md`, `projects.md`.

# [x] Phase 8: Copy and paste, and From scratch

## [x] Story 8.1: Copy and paste
- [x] Task 8.1.1 The clipboard reference; the backend paste (notes, metadata, audio segments, the insert); undo.
- [x] Task 8.1.2 Across projects and layers, with the read check.
- [x] Task 8.1.3 The note under rule 2 in `wall-clock-rewrite.md`.

## [x] Story 8.2: From scratch
- [x] Task 8.2.1 The empty project, Record and Paste on a blank sheet.
- [x] Task 8.2.2 Playback across several audio files, checked at every join.

## [x] Story 8.3: Documentation
- [x] Task 8.3.1 `editing.md`, `editing-and-compose.md`.

# [x] Phase 9: Recording in Sheet

## [x] Story 9.1: The page
- [x] Task 9.1.1 Current and Proposal; recording and takes.
- [x] Task 9.1.2 The condensed steps: range of the take, then transcription, hands and sheet with the passage's key and figure.

## [x] Story 9.2: Promote
- [x] Task 9.2.1 The window and the speed; keep the original audio or use the recording.
- [x] Task 9.2.2 Replace the whole passage, with the length confirmation; undo after promotion.
- [x] Task 9.2.3 The staged session generalised (as hidden projects of the vault); the two old panels removed.

## [x] Story 9.3: Documentation
- [x] Task 9.3.1 `editing.md`, `editing-and-compose.md`, `projects.md` (and `recording-in-sheet.md`, new).

# [x] Phase 10: From other projects, and the playlists

## [x] Story 10.1: From other projects
- [x] Task 10.1.1 The compose page: picker, read-only sheet, passages, sequential or subheader, reorder (`/projects/compose`; the list kept in the browser until saved).
- [x] Task 10.1.2 **Save as song** and **Save as integrated playlist** with parts (`POST /projects/compose`, each passage a paste of Phase 8).

## [x] Story 10.2: Integrated playlist
- [x] Task 10.2.1 Parts on the Sheet step, subheaders, the sub-song panel, reorder, join and split (one part's sheet at a time; the continuous drawing is Play mode's, Phase 11).

## [x] Story 10.3: Songs playlist
- [x] Task 10.3.1 My library → Playlists; **Make a playlist** from a selection (and **Add to a playlist** from a version or a stretch of it).

## [x] Story 10.4: Documentation
- [x] Task 10.4.1 `projects.md` (playlists: `context/frontend/playlists.md`, new), `endpoints.md`; `editing.md`, `editing-and-compose.md`, `paths-and-data.md`, `07-database.md`, `private-library.md`, `pages.md`, `annotations-stretches.md`, `components.md`, `aitu-frontend/README.md`.

# [x] Phase 11: Play mode

Built 2026-10-15 ([`02-implementation-phase-11.md`](02-implementation-phase-11.md)); every check passes (`check:passage`, `check:flow` and `time:flow` with the GPU on 2026-10-16). Checked by the user on 2026-10-16 and merged into `master`.

## [x] Story 11.1: The page
- [x] Task 11.1.1 Close, Next, Play and Pause, the scroll that keeps the cursor in the middle, the keys (`/play/:projectId`, each part the Sheet step's page in a play role).
- [x] Task 11.1.2 Lyrics by their frames; Notes Falling as a view (on the recording's clock; the old page and its address removed).

## [x] Story 11.2: Playlists
- [x] Task 11.2.1 The next song, the list when closed, the continuous page (**All songs**; the parts of one song play on, a songs playlist waits at each new song).
- [x] Task 11.2.2 Entry points everywhere (`PerformancePage` was removed in Phase 1): song, version, Projects, a project's menu, a playlist and its rows.

## [x] Story 11.3: Documentation
- [x] Task 11.3.1 `context/frontend/play-mode.md` (new); `pages.md`, `projects.md`, `playlists.md`, `components.md`, `endpoints.md`, `editing-and-compose.md` (the audio kind fix found on the way).

# [x] Phase 12: The music library data reconciled

Built 2026-10-16 ([`02-implementation-phase-12.md`](02-implementation-phase-12.md)); merged into `master` after the user's ok (2026-10-16). Q-6 answered;
Q-5 keeps its recommendations for later work. Starts any time after Phase 3. The parallel data is ready: `data/music-library/library.sqlite` next to the repository (on this machine `/home/david/Documents/projects/music/data/music-library/library.sqlite`). Writes nothing into that folder or its scripts.

## [x] Story 12.1: The reconciliation
- [x] Task 12.1.1 Read `public-library-build/02-a-public-library-build-implementation.md`, then `library.sqlite`. There is no response file.
- [x] Task 12.1.2 `context/music-library/reconciliation.md`: the mapping to plan section 8.6, the gaps in both directions (genre, tags, regions; lyrics, album chart history), the identity rule for songs and artists across runs (and the 134 re-entries).
- [x] Task 12.1.3 Only the missing fields added to section 8.6 and its Alembic migration (revision `0003`: `song_lyrics`, `album_artists`, `album_chart_entries`, `albums.release_date`, `albums.popularity`).
- [x] Task 12.1.4 The import script the Phase 13 import starts from (`library/public_import.py`, `make public-import`; run on copies only); the 31 seed songs checked (23 on the chart, 8 added from the seed list).

## [x] Story 12.2: Popularity
- [x] Task 12.2.1 The formula of plan section 15.6 run on the downloaded chart history (songs and albums; `library/popularity.py`).
- [x] Task 12.2.2 Tuned: the user chose objective criteria instead of a hand ranking (2026-10-16); `DEFAULT` weights, `make popularity-check`.

## [x] Story 12.3: Decisions
- [x] Task 12.3.1 Q-5 (the regions not covered, the missing fields) and Q-6 raised with a recommendation each.

## [x] Story 12.5: A version of the library always has its piano sheet (asked 2026-10-16)
- [x] Task 12.5.1 The rule: Save already refused; Restore refuses a state without a sheet; `make db-check` reports one; a test.
- [x] Task 12.5.2 The 30 songs of the Phase 3 migration given their hands and sheet through the real pages (`scripts/sheet-library.mjs`, after `make db-backup`); 30 of 30.

## [x] Story 12.4: Documentation
- [x] Task 12.4.1 `music-library/reconciliation.md` (new), `music-library/README.md`, `00-index.md`, `07-database.md` (revision `0003`, the running backend migrates), `paths-and-data.md` section 6; the plan's "as built in Phase 12" notes (sections 8.6, 15.5, 15.6).

# [x] Phase 13: The Public Library

Built 2026-10-16 ([`02-implementation-phase-13.md`](02-implementation-phase-13.md)); merged into
`master` after the user's ok (2026-10-16). Two answers of the user (2026-10-16): only a song with
a version is added to My library; **Save to library** suggests the public songs and artists.

## [x] Story 13.1: The import
- [x] Task 13.1.1 The reconciled data of Phase 12 into public rows, safe to run again; the seed songs present (run on the real `.database/` after `make db-backup`; a second run makes 0 rows; 23 + 8 seed songs).

## [x] Story 13.2: The pages
- [x] Task 13.2.1 Search, filter chips, sort (the backend's in-memory list; the popularity of a decade on the request).
- [x] Task 13.2.2 One song (metadata, chart line, fixed versions, Other versions by user), artists, public playlists (and Play mode on them).
- [x] Task 13.2.3 Likes.

## [x] Story 13.3: Pull
- [x] Task 13.3.1 **Add to my library** for a song, an artist, a playlist; **Save to library** on a public song or artist (asked 2026-10-16).

## [x] Story 13.4: Documentation
- [x] Task 13.4.1 `music-library/ontology.md`, `popularity.md` (new); `music-library/README.md`, `private-library.md`, `reconciliation.md`, `00-index.md`, `pages.md`, `endpoints.md` §7.3, `paths-and-data.md`, `components.md`, `aitu-frontend/README.md`; the plan's "as built in Phase 13" notes.

# [x] Phase 14: Requests, the Admin panel and sharing

Built 2026-10-16, the request page laid out like a pull request 2026-10-18
([`02-implementation-phase-14.md`](02-implementation-phase-14.md)); merged into `master` after the
user's ok (2026-10-18). The user's answer at the start (2026-10-16): a fourth kind of
request, **Playlist**. Revision `0004` moved the real `.database/` (after `make db-backup`).

## [x] Story 14.1: Requests
- [x] Task 14.1.1 The three kinds with items (and **Playlist**); the Publish dialog (and Suggest a change, Propose a song, Ask for a fixed version); My requests.
- [x] Task 14.1.2 Changes asked and resent; withdraw.

## [x] Story 14.2: Review
- [x] Task 14.2.1 The review list and page, side by side, partial acceptance (the page laid out like a pull request at the user's ask of 2026-10-18: Conversation with comments on a stretch, Sheet with Proposed and Now; revision `0005`).
- [x] Task 14.2.2 The publishing transaction; the creator's username on the version.

## [x] Story 14.3: Sharing
- [x] Task 14.3.1 Share a Private Library; **Shared**; the counts in the sidebar.

## [x] Story 14.4: Documentation
- [x] Task 14.4.1 `music-library/requests.md` (new), `08-security.md` (rights), `endpoints.md` (§7.4, §7.5); `ontology.md`, `private-library.md`, `music-library/README.md`, `00-index.md`, `07-database.md`, `paths-and-data.md`, `backend/api.md`, `frontend/pages.md`, `aitu-frontend/README.md`; the plan's "as built in Phase 14" notes.

# [x] Phase 15: The checks, the documentation, and closing

Built 2026-10-18 ([`02-implementation-phase-15.md`](02-implementation-phase-15.md)); merged into
`master` after the user's ok (2026-10-18). Q-5 stays open for later work.

## [x] Story 15.1: The journey
- [x] Task 15.1.1 The whole journey with two users on temporary copies, with timings (`npm run check:journey`: two temporary users and the master user, 21 checks, passed twice; the times of 16 steps).

## [x] Story 15.2: The cleanup
- [x] Task 15.2.1 Old redirects and the code that read `aitu-backend/data/` removed (`LEGACY_REDIRECTS`, `LegacyRedirect.tsx`; `scripts/migrate/`, its test, `paths.data_dir()`, `AITU_DATA_DIR`; the Lab records moved to `tests/fixtures/frame-examples/`).

## [x] Story 15.3: Documentation
- [x] Task 15.3.1 `00-project-complete-overview.md`, `01-project.md`, `05-deployment.md` rewritten; run instructions in one place (`04-local-development.md`; the root and service READMEs, `02b-local-setup.md` and the area READMEs link to it); the folder README marked complete.

# [x] Phase 16: The `spain` and `catalan` regions, from the 60s to today

Added 2026-10-18 at the user's ask (plan section 20). Built 2026-10-19
([`02-implementation-phase-16.md`](02-implementation-phase-16.md)); merged into `master` after the
user's ok (2026-10-19). Q-9 answered 2026-10-18. Revision `0006` moved the real `.database/` (after
`make db-backup`).

## [x] Story 16.1: The research
- [x] Task 16.1.1 A deep research on the internet: the Spanish and Catalan charts and radio lists of each decade from the 60s, with their years, what they give, licence, format and pace; MusicBrainz and Wikidata for artists and identifiers.
- [x] Task 16.1.2 `context/music-library/regional-sources.md` with the recommendation; Q-9 raised before any download.

## [x] Story 16.2: The data
- [x] Task 16.2.1 The download of the chosen sources into `data/music-library-regions/<source>/`, paced and resumable (`scripts/music-library-regions/`, `make regional-download`, `make regional-build`: five sources, no refusal; one database per source).
- [x] Task 16.2.2 The import into public rows (the Phase 12 identity rule; existing songs get the region; new songs and artists), on copies, then on the real `.database/` after `make db-backup` (`library/regional_import.py`, `make regional-import`; revision `0006`: `song_region_popularity`, `song_keys`, `artist_keys`; 12,014 songs and 4,034 artists made; a second run made 0).

## [x] Story 16.3: Popularity per region
- [x] Task 16.3.1 The formula per region (an adapted one for sources with no weekly places); one popularity per song and region (every place against 100; the largest of a region's charts; number ones with a fitted weight lowered for a spread top; a month as 3 weeks; Spotify's totals as an estimate only where no chart lists the song; all by the Q-6 criteria).
- [x] Task 16.3.2 The pages: the Region chip with `spain` and `catalan`, the region's popularity, the charts of a song (`check:public`, 9 new checks; the 13-check pass).

## [x] Story 16.4: Documentation
- [x] Task 16.4.1 `regional-sources.md` (new), `reconciliation.md`, `popularity.md`, `ontology.md`, `07-database.md`, `paths-and-data.md` (and `endpoints.md`, `music-library/README.md`, `00-index.md`, the scripts' README).

# [x] Phase 17: A popularity inferred from YouTube views

Added 2026-10-18 at the user's ask (plan section 20). Built 2026-10-19
([`02-implementation-phase-17.md`](02-implementation-phase-17.md)) on `feat/phase-17`; merged into
`master` after the user's ok (2026-10-19). Q-10 answered 2026-10-19; the formula chosen by the user the same day.
Revision `0007` moved the real `.database/` (after `make db-backup`).

## [x] Story 17.1: The sample
- [x] Task 17.1.1 Songs with a chart popularity across scores, decades and regions; their official video (Los 40, Wikidata and Enderrock first; MusicBrainz left out, it rarely links these videos; then 100 searches on low-scored `catalan` songs); views and upload date (`library/signals.py`; 6,664 pairs of a song and a region, 166 `catalan`).
- [x] Task 17.1.2 Spotify, as Q-10 decides: the artist's Spotify id, then kworb's all-time streams per song (694 artists before Spotify asked for a 23-hour wait; 3,764 pairs with streams).

## [x] Story 17.2: The fit
- [x] Task 17.2.1 Scatter plots (popularity against views, views per year, streams); seven candidates measured on songs left out (best formula 21.0 points, the median 24.3); the user chose the line with the streams (2026-10-19).

## [x] Story 17.3: The inferred popularity
- [x] Task 17.3.1 Stored with its source and date for songs with no chart data, shown as inferred; a chart popularity wins; a command within the day's quota (revision `0007`; `make popularity-infer`, `make popularity-refresh`; `check:public` 49; 4 `catalan` songs today, 53 waiting for searches; asked after the first check: "–" for a song with no value in the region shown, and a **Popularity by region** column; `check:public` 52).

## [x] Story 17.4: Documentation
- [x] Task 17.4.1 `popularity.md` (section 6, new), `ontology.md`, `endpoints.md`, `07-database.md`, `paths-and-data.md`, `.env.example` (and `regional-sources.md`, `music-library/README.md`, `00-index.md`, the READMEs of the implementations).

# [x] Phase 18: Genres and tags from Wikidata

Added 2026-10-19 at the user's ask (plan section 20): the genre and tag part of Q-5. Needs no key;
Q-11 is raised halfway. Built 2026-10-19 on `feat/phase-18`
([`02-implementation-phase-18.md`](02-implementation-phase-18.md)); Q-11 answered the same day. No
revision; the real `.database/` was written after `make db-backup`. Merged into `master` after the
user's ok (2026-10-19).

## [x] Story 18.1: The measure
- [x] Task 18.1.1 Every Wikidata song or single with a performer, its genres and its performers' genres (the answers kept, as Phase 17's); matched to the public songs by the identity rule, the item's id kept in `song_keys` (`library/genres.py`, `make genres-measure`; through QLever, the Wikidata query service limited every client to 1 query a minute; 229,348 items, 6,242 public songs matched; the key is written by the import).
- [x] Task 18.1.2 The counts: songs with genres of their own or only through their performer, per region and decade; every Wikidata genre and its songs; the properties that tie a song to a film, a video game, a TV show or an advert, and the songs each gives (own 24 %, through the performer 32 %, by a unique name 19 %, none 25 %; `catalan` 76 % none; 514 genres; 119 songs in 88 films, 24 in TV, 1 game, 0 adverts).
- [x] Task 18.1.3 Q-11 raised with a proposed map of the most frequent genres onto the 13, before any row is written.

## [x] Story 18.2: The import
- [x] Task 18.2.1 At most two genres per song and the tags chosen, as public rows; safe to run again; a request's genre or tag never removed; on a copy, then on the real `.database/` after `make db-backup` (`make genres-import`: 11,717 songs with a genre, 119 songs in 87 films, 8,297 keys; a second run writes nothing; a song an accepted request named is left alone, no revision; the second genre corrected after the first run: at least half as frequent as the first, a tie to the commoner genre).

## [x] Story 18.3: The pages
- [x] Task 18.3.1 The Genre (and Tag) chips with their counts; `check:public`; the 13-check pass (`check:public` 58, 6 new; the category reads "Films", not `films`).

## [x] Story 18.4: Documentation
- [x] Task 18.4.1 `music-library/genres.md` (new), `ontology.md`, `reconciliation.md` (Q-5), `07-database.md` and `paths-and-data.md` (if a revision), `endpoints.md` (if a route changes) (no revision and no route: `paths-and-data.md` for the writer and the key; and `requests.md`, `music-library/README.md`, `00-index.md`, `00-documentation-instructions.md`).
