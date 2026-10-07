# 02: The private web app

**State: live, opened 2026-10-05.** Four decisions answered (Q-1 to Q-4); four more are raised during the
work (Q-5 to Q-8). Sixteen phases, 0 to 15, each on its own `feat/phase-N` branch. **Phase 0 done and merged
2026-10-05** ([`02-implementation-phase-0.md`](02-implementation-phase-0.md)). **Phase 1 done and merged
2026-10-05** ([`02-implementation-phase-1.md`](02-implementation-phase-1.md)). **Phase 2 done and merged
2026-10-06** ([`02-implementation-phase-2.md`](02-implementation-phase-2.md)). **Phase 3 done and merged
2026-10-06** ([`02-implementation-phase-3.md`](02-implementation-phase-3.md)); `aitu-backend/data/`
deleted after the user's check (its committed `README.md` and Lab records stay). **Phase 4 done and merged
2026-10-06** ([`02-implementation-phase-4.md`](02-implementation-phase-4.md)). **Phase 5 done and
checked by the user 2026-10-07** ([`02-implementation-phase-5.md`](02-implementation-phase-5.md)),
merged at the start of Phase 6. **Phase 6 done 2026-10-07**
([`02-implementation-phase-6.md`](02-implementation-phase-6.md)), on `feat/phase-6`, waiting for the
user's check. Q-7 and Q-8 are open.

The brief is [`02-prompt.md`](02-prompt.md), the app it builds is
[`../../app/01-app-context.md`](../../app/01-app-context.md), the plan is [`02-plan.md`](02-plan.md)
and the status lookup is [`02-checklist.md`](02-checklist.md). Phase reports go beside them as
`02-implementation-phase-N.md`, following
[`../../language/communication-implementation-plans.md`](../../language/communication-implementation-plans.md).

| File | What it is |
|---|---|
| [`02-prompt.md`](02-prompt.md) | The brief, in the user's own words |
| [`02-plan.md`](02-plan.md) | The plan: the structure of the app, the design system, `.database/`, users, projects, the sheet, copy and paste, Recording in Sheet, playlists, the music library, requests, Play mode, sixteen phases |
| [`02-checklist.md`](02-checklist.md) | The status lookup, and the decisions |
| [`02-implementation-phase-0.md`](02-implementation-phase-0.md) | Phase 0: the links repaired, the leftovers archived, the baseline (screenshots in [`screenshots/phase-0/`](screenshots/phase-0/), test counts) |
| [`02-implementation-phase-1.md`](02-implementation-phase-1.md) | Phase 1: the design system, the sidebar shell, Projects and the restyled steps, the removed pages (screenshots in [`screenshots/phase-1/`](screenshots/phase-1/)) |
| [`02-implementation-phase-2.md`](02-implementation-phase-2.md) | Phase 2: the sheet page split into modules, the defaults (the highest peak is a negra), the redesigned page and toolboxes, the line wrap fixed, the timings (screenshots in [`screenshots/phase-2/`](screenshots/phase-2/)) |
| [`02-implementation-phase-3.md`](02-implementation-phase-3.md) | Phase 3: `.database/` (SQLite and the project bundles), the tables, `notes.pmn` version 2, the audio store by hash, the migration of the 39 pieces, backup and check (screenshots in [`screenshots/phase-3/`](screenshots/phase-3/)) |
| [`02-implementation-phase-4.md`](02-implementation-phase-4.md) | Phase 4: users, sign in, the rights table with a test per row, Admin → Users, the dark theme, the app on the home network (screenshots in [`screenshots/phase-4/`](screenshots/phase-4/)) |
| [`02-implementation-phase-5.md`](02-implementation-phase-5.md) | Phase 5: the `/projects` routes and the Projects page, **add audio**, the video as a step of the project, the `.aitu` export and import, Q-8 measured (screenshots in [`screenshots/phase-5/`](screenshots/phase-5/)) |
| [`02-implementation-phase-6.md`](02-implementation-phase-6.md) | Phase 6: the Private Library: **Save to library** with the audio written again, My library's Songs and Artists, read-only versions, Edit, Replace, history (screenshots in [`screenshots/phase-6/`](screenshots/phase-6/)) |
| [`public-library-build/`](public-library-build/) | A parallel piece of work: downloading `musicchartsarchive.com` into `data/music-library/` (next to the repository) to build the data of the Public Library. Phase 12 reconciles it with this plan |

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
