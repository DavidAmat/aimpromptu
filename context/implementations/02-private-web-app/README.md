# 02: The private web app

**State: live again: Phases 0 to 15 complete (2026-10-18); Phases 16 and 17 added the same day at the
user's ask** (the `spain` and `catalan` regions; a popularity inferred from YouTube views). Opened
2026-10-05. Each phase is built on its own
`feat/phase-N` branch and merged into `master` after the user's check; each has its report below.
Nine of the ten decisions are answered (Q-1 to Q-4 before the plan, Q-6 to Q-10 on the way).
**Q-5** keeps genres and tags for later work (its region part became Q-9, answered 2026-10-18);
**Q-10** (Spotify) was answered 2026-10-19 (kworb's streams as a second signal). **Phase 16** (the
`spain` and `catalan` regions) was built 2026-10-19 ([`02-implementation-phase-16.md`](02-implementation-phase-16.md))
and merged into `master` after the user's ok (2026-10-19). **Phase 17** (a popularity inferred from
YouTube views) was built 2026-10-19 ([`02-implementation-phase-17.md`](02-implementation-phase-17.md))
and waits for the user's ok to merge. The old store `aitu-backend/data/` is gone: its pieces moved into
`.database/` in Phase 3, the user deleted it after checking the app, and Phase 15 removed the code
that read it (its Lab records are now a test fixture). **Phase 15** walked the whole journey with two
users and closed the documentation ([`02-implementation-phase-15.md`](02-implementation-phase-15.md));
merged into `master` after the user's ok (2026-10-18).

The brief is [`02-prompt.md`](02-prompt.md), the app it builds is
[`../../app/01-app-context.md`](../../app/01-app-context.md), the plan is [`02-plan.md`](02-plan.md)
and the status lookup is [`02-checklist.md`](02-checklist.md). Phase reports go beside them as
`02-implementation-phase-N.md`, following
[`../../language/communication-implementation-plans.md`](../../language/communication-implementation-plans.md).

| File | What it is |
|---|---|
| [`02-prompt.md`](02-prompt.md) | The brief, in the user's own words |
| [`02-plan.md`](02-plan.md) | The plan: the structure of the app, the design system, `.database/`, users, projects, the sheet, copy and paste, Recording in Sheet, playlists, the music library, requests, Play mode, eighteen phases |
| [`02-checklist.md`](02-checklist.md) | The status lookup, and the decisions |
| [`02-implementation-phase-0.md`](02-implementation-phase-0.md) | Phase 0: the links repaired, the leftovers archived, the baseline (screenshots in [`screenshots/phase-0/`](screenshots/phase-0/), test counts) |
| [`02-implementation-phase-1.md`](02-implementation-phase-1.md) | Phase 1: the design system, the sidebar shell, Projects and the restyled steps, the removed pages (screenshots in [`screenshots/phase-1/`](screenshots/phase-1/)) |
| [`02-implementation-phase-2.md`](02-implementation-phase-2.md) | Phase 2: the sheet page split into modules, the defaults (the highest peak is a negra), the redesigned page and toolboxes, the line wrap fixed, the timings (screenshots in [`screenshots/phase-2/`](screenshots/phase-2/)) |
| [`02-implementation-phase-3.md`](02-implementation-phase-3.md) | Phase 3: `.database/` (SQLite and the project bundles), the tables, `notes.pmn` version 2, the audio store by hash, the migration of the 39 pieces, backup and check (screenshots in [`screenshots/phase-3/`](screenshots/phase-3/)) |
| [`02-implementation-phase-4.md`](02-implementation-phase-4.md) | Phase 4: users, sign in, the rights table with a test per row, Admin → Users, the dark theme, the app on the home network (screenshots in [`screenshots/phase-4/`](screenshots/phase-4/)) |
| [`02-implementation-phase-5.md`](02-implementation-phase-5.md) | Phase 5: the `/projects` routes and the Projects page, **add audio**, the video as a step of the project, the `.aitu` export and import, Q-8 measured (screenshots in [`screenshots/phase-5/`](screenshots/phase-5/)) |
| [`02-implementation-phase-6.md`](02-implementation-phase-6.md) | Phase 6: the Private Library: **Save to library** with the audio written again, My library's Songs and Artists, read-only versions, Edit, Replace, history (screenshots in [`screenshots/phase-6/`](screenshots/phase-6/)) |
| [`02-implementation-phase-7.md`](02-implementation-phase-7.md) | Phase 7: the sheet toolbox's Transpose (notes and figures, with a preview and an exact undo) and Lyrics (the pool, pieces snapped to frames), Key for this passage, the clef rule for the left hand (screenshots in [`screenshots/phase-7/`](screenshots/phase-7/)) |
| [`02-implementation-phase-8.md`](02-implementation-phase-8.md) | Phase 8: copy and paste of a passage (notes, marks and audio, undo and redo exact, across projects and layers), the audio timeline with ranges of files, From scratch, the audio checked at every join (screenshots in [`screenshots/phase-8/`](screenshots/phase-8/)) |
| [`02-implementation-phase-9.md`](02-implementation-phase-9.md) | Phase 9: Recording in Sheet: the page of a passage (Current and Proposal, takes recorded or from a file, the condensed steps in one job), the speed and the window, the promotions (fit to the window with either audio, the whole passage with the length change) as one undoable write through the paste, the staged session removed (screenshots in [`screenshots/phase-9/`](screenshots/phase-9/)) |
| [`02-implementation-phase-10.md`](02-implementation-phase-10.md) | Phase 10: From other projects (passages of other projects saved as a song or an integrated playlist), the parts of a project (rename, move, join, split), songs playlists (screenshots in [`screenshots/phase-10/`](screenshots/phase-10/)) |
| [`02-implementation-phase-11.md`](02-implementation-phase-11.md) | Phase 11: Play mode: the sheet alone, Close, Next, Play, the cursor kept in the middle, lyrics by their frames, Notes Falling as a view, an integrated playlist played on, a songs playlist song by song, the entry points; the audio kind fix of Replace the version (screenshots in [`screenshots/phase-11/`](screenshots/phase-11/)) |
| [`02-implementation-phase-12.md`](02-implementation-phase-12.md) | Phase 12: the downloaded music library reconciled with the tables (`reconciliation.md`, revision `0003`, the import script tried on copies), the popularity formula and its weights chosen by objective criteria (Q-6), every library version with its piano sheet |
| [`02-implementation-phase-13.md`](02-implementation-phase-13.md) | Phase 13: the Public Library: the import on the real database, the songs (search, filter chips, sort, the popularity of a decade), one song (its chart line, versions, likes), artists, playlists, **Add to my library**, public suggestions in **Save to library** and **Search** (screenshots in [`screenshots/phase-13/`](screenshots/phase-13/)) |
| [`02-implementation-phase-14.md`](02-implementation-phase-14.md) | Phase 14: requests (four kinds with their items), the review laid out like a pull request (Conversation with comments on a stretch, Sheet with Proposed and Now, Finish your review), the publishing transaction, sharing a Private Library, the counts in the sidebar (screenshots in [`screenshots/phase-14/`](screenshots/phase-14/)) |
| [`02-implementation-phase-15.md`](02-implementation-phase-15.md) | Phase 15: the whole journey with two temporary users and its timings (`check:journey`), the old redirects and the code of the old store removed, the platform pages rewritten, run instructions in one place (screenshots in [`screenshots/phase-15/`](screenshots/phase-15/)) |
| [`research/phase-16-spanish-and-catalan-charts.md`](research/phase-16-spanish-and-catalan-charts.md) | Phase 16: the research on the charts and lists of Spain and Catalonia, from the 60s to today, with a source for every fact (summed up in [`regional-sources.md`](../../music-library/regional-sources.md)) |
| [`02-implementation-phase-16.md`](02-implementation-phase-16.md) | Phase 16: the `spain` and `catalan` regions: the research, the download of five sources, revision `0006`, the import, the popularity per region chosen by the Q-6 criteria, the Region chip and the song page (screenshots in [`screenshots/phase-16/`](screenshots/phase-16/)) |
| [`02-implementation-phase-17.md`](02-implementation-phase-17.md) | Phase 17: a popularity inferred from YouTube views: Q-10 (kworb's streams), the official videos (Los 40, Wikidata, Enderrock, searches), the fit measured on songs left out (plots in [`research/phase-17/`](research/phase-17/)), revision `0007`, `make popularity-infer` and `-refresh`, the song page (screenshots in [`screenshots/phase-17/`](screenshots/phase-17/)) |
| [`public-library-build/`](public-library-build/) | A parallel piece of work, finished 2026-10-07: downloading `musicchartsarchive.com` into `data/music-library/` (next to the repository) to build the data of the Public Library. Phase 12 reconciled it with this plan and Phase 13 imported it |

## What it is for

The MVP of [`../01-mvp/`](../01-mvp/) takes one audio file to one piano sheet, for one person. This
work turns it into the app of the app context: a local web app on the home network, with users and a
master user, a clean minimal UI with a sidebar, projects that start from a source, from scratch or
from other projects, three storage layers (Personal Vault, Private Library, Public Library) in one
portable `.database/` folder, a music library of songs, artists and versions, requests reviewed in an
Admin panel, two kinds of playlist, and Play mode.

## What it does not touch

MuScriptor, the piano matrix notation's meaning, the hand split and the drawing of the piano sheet stay
as implementation 08 left them. The production version (cloud, HTTPS, public sign-up) is later work.
