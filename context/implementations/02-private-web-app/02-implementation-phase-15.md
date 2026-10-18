# 02: Phase 15 report: The checks, the documentation, and closing

Plan: [`02-plan.md`](02-plan.md) sections 6.3, 19 and 20, Phase 15. Checklist:
[`02-checklist.md`](02-checklist.md). Branch `feat/phase-15`, made from `master` at `8261b73`
(Phase 14 merged after the user's ok, 2026-10-18). Built 2026-10-18 on the Ubuntu machine. The GPU
was free this time (only three small processes of another project, about 1.4 GB), so the journey
transcribed on it and the backend tests ran on it.

This is the last phase of implementation 02.

# 1. Summary

| Story | Result |
|---|---|
| 15.1 The journey | `npm run check:journey` (new, `aitu-frontend/scripts/check-journey.mjs`): a YouTube link to a piano sheet, saved to the library, published with a new song and artist, reviewed and accepted by the master user, found and added by a second user, played in Play mode, and made into a project from other projects. Two temporary users, removed at the end with everything they made. **21 checks passed, twice in a row**; the times of 16 steps (section 3) |
| 15.2 The cleanup | The old redirects (`LEGACY_REDIRECTS`, `LegacyRedirect.tsx`) removed; the migration (`scripts/migrate/`, `tests/test_to_database.py`), `paths.data_dir()`, `paths.frame_examples_seed_dir()`, `config.data_dir_override()` and `AITU_DATA_DIR` removed; `aitu-backend/data/` is gone, its Lab records now the fixture `tests/fixtures/frame-examples/` (section 4) |
| 15.3 Documentation | `00-project-complete-overview.md`, `01-project.md`, `05-deployment.md` and the root `README.md` rewritten; `04-local-development.md` the one home of the run instructions; the indexes and the folder README say the implementation is complete (section 5) |

Checks (section 6): backend 1,124 tests on the GPU, only the 1 known failure; lint, build and `check-links.py` pass; `check:play`
(changed) passes; `make db-check` on the real `.database/` reports no problem after every run.

# 2. The journey (Story 15.1)

## 2.1 Who does what

The plan asks for the journey "with two users". The check uses **three accounts**: two temporary
users it makes through **Admin → Users** (`journey-a-<time>`, the author; `journey-b-<time>`, the
reader) and the master user, who only reviews. The alternative was the master user as the second
user, but then **Add to my library** and **From other projects** would write into the master user's
real library, which the rule of the plan forbids ("every script that clicks or writes in the app
works on a temporary copy"). With two temporary users, the only real rows the check touches are
the public ones it creates, and those are new (a song and an artist named with the time).

The song is the one `time:flow` uses since implementation 08: Yann Tiersen, "Comptine d'un autre
été, l'après-midi" (2:21, solo piano, not in any library). The proposal names it
`Comptine (journey <time>)` by `Yann Tiersen (journey <time>)`, so it never matches a public song.

## 2.2 The walk

| # | Who | What | Checked |
|---|---|---|---|
| 1 | Author | **New project**, the YouTube link, **Download the audio** | the project is the author's; the master user gets `404` on it |
| 2 | Author | **Transcribe**, followed live; **Predict hands**, Save; the Sheet step, Save | 1,014 notes; every step `ready` |
| 3 | Author | **Save to library** (artist, song, version `original`) | the song with its one version |
| 4 | Author | **Publish** on the version, **Propose this song** (filled from the song and its artist, "A new artist"), year 2001, **Send request** | the request in **Requests** |
| 5 | Master user | **Review** lists it; the request page; its **Sheet** tab; **Review** → every item **Accept** → **Send decision** | three items (new artist, new song, piano sheet); Accepted; the public song has the author's version, credited to the author |
| 6 | Reader | **Public songs**, search, the song, **Add to my library** | the version is `original (journey-a-…)` in the reader's library |
| 7 | Reader | **Play** (Play mode), Play, Space pauses, Escape closes | the recording plays |
| 8 | Reader | **New project → From other projects**, the pulled version whole, **Save as song** | the new project holds all 1,014 notes, and is the reader's |
| 9 | — | Rights | the author gets `404` on the reader's project, the reader `404` on the author's version and `403` on Review |
| 10 | — | Clean up (`public_fixture remove-user` twice, `remove-song`, `remove-artist`) | no user and no public song left; `make db-check` clean, no audio file left without a project |

No console error and no failed request, other than the ones the walk asks for (the reader's `403`
on Review) and the `404` of a sheet not yet written before the Sheet step.

## 2.3 Four runs

1. **Failed: the backend container had lost its GPU.** The transcription waited on nothing;
   `nvidia-smi` inside the container said "Failed to initialize NVML". The known answer
   (`docker compose up -d --force-recreate --no-deps backend`, in the memory of this machine and in
   `04-local-development.md`) gave the GPU back. The same run then saw my edits of `App.tsx` reload
   its page. It cleaned up after itself.
2. **Failed after Play mode**: Play mode hides its buttons while the music plays (the sheet alone),
   so a click on Pause waited 30 s for a button that was not shown. The script now uses the keys, as
   `check:play` does: Space pauses, Escape closes. The cursor moved between the two screenshots, so
   the page was right.
3. **Passed** (21 checks). One time looked too short: **Save as song** to the new project's first
   notehead, 0.2 s. The wait could count a notehead of the compose page that was still on screen.
   The script now waits for the compose page's sheet to leave first.
4. **Passed** (21 checks), with the honest time (0.5 s). Its screenshots are in
   [`screenshots/phase-15/`](screenshots/phase-15/).

# 3. Timings

Run 4, the RTX 4090 with MuScriptor `large` (float16) loaded, headless Chromium at 1440 x 900. Each
step is timed from the press of its button to its result on screen. The third column is the same
song in implementation 08, Phase 9 (the baseline of the flow; the sheet step was a separate
**Write the sheet** then).

| Step | Waited for | Phase 15 | Implementation 08 |
|---|---|---:|---:|
| Download the audio | the Audio step of the new project | 4.5 s | 3.8 s |
| Transcribe | the first note in the live view | 0.3 s | 0.34 s |
| Transcribe | every note saved, on screen | 22.3 s | 21.4 s |
| Predict hands | the hands on screen | 1.4 s | 1.4 s |
| Save the hands | saved | 0.1 s | 0.10 s |
| The Sheet step | the first notehead drawn | 0.5 s | 0.14 + 0.55 s |
| Save the sheet | saved | 0.1 s | 0.21 s |
| Save to library | the song with its version | 0.3 s | — |
| Publish | the request sent | 0.1 s | — |
| The request's Sheet tab (master user) | the proposed sheet drawn | 0.4 s | — |
| Send decision | Accepted, written to the Public Library | 0.1 s | — |
| Add to my library (reader) | the song in the reader's library | 0.1 s | — |
| Play | Play mode, the first notehead drawn | 0.4 s | — |
| Play | the recording playing | 0.1 s | — |
| From other projects | the chosen version's sheet drawn | 0.5 s | — |
| Save as song | the new project's Sheet step drawn | 0.5 s | — |

**What the numbers say.** The steps implementation 08 measured take the same time after sixteen
phases: the transcription is the only step a user waits for (about 22 s for a 2:21 song), and the
download depends on YouTube (3.8 to 4.5 s over the four runs). Every step implementation 02 added
answers in half a second or less on this song. Run 3 gave the same times within 0.3 s.

**Save to library** writes the audio again only when the project has cuts (Q-3); this one had none,
so 0.3 s is a move and a few rows. With cuts, Phase 6 measured the rewrite on Elefants
([report](02-implementation-phase-6.md)).

# 4. The cleanup (Story 15.2)

## 4.1 The old redirects

Plan section 6.3 kept every old path (`/piece/...`, `/playground/...`, `/youtube`, `/video/...`,
`/library`, `/library/play/...`, and since Phase 11 `/projects/:id/notes-falling`) as a redirect
"for one implementation". Removed: `LEGACY_REDIRECTS` in `routes.ts`, `layout/LegacyRedirect.tsx`
and their routes in `App.tsx`. An old path now opens the page of an unknown address
(`NotFoundPage`). `check:play` visited the old Notes Falling address; it now checks that
`/play/<id>?view=falling` opens Play mode on Notes Falling.

`/library` was one of the redirects, to `/library/songs`. It is not a page of the sidebar, so it
now opens the unknown address page too.

## 4.2 The old store

The user deleted `aitu-backend/data/audio/` after checking the app (Phase 3); what was left were
the committed `README.md` and the Lab records `frame-examples/*.json`. Removed:

| Thing | Where it was |
|---|---|
| The migration | `scripts/migrate/to_database.py`, its test `aitu-backend/tests/test_to_database.py` |
| The tools that moved the gitignored data from the Mac (implementation 08) | `scripts/migrate/manifest.sh`, `push-data-to-ubuntu.sh`, `data-paths.txt`: they listed `aitu-backend/data/audio`, and `.database/` moves by `make db-backup` now |
| The path functions and the setting | `paths.data_dir()`, `paths.frame_examples_seed_dir()`, `config.data_dir_override()`, `AITU_DATA_DIR` (`config.py` table, `.env.example`, `compose.yaml` and its mount of `aitu-backend/data`) |
| The ignore rules of the old store | `.gitignore` |
| Its README | `aitu-backend/data/README.md` |

**The Lab records** are the calibration and the hand annotations of each Synthesia screenshot,
made by hand and impossible to rebuild. The real Lab reads its own copy in
`.database/lab/frame-examples/` since Phase 3; only `tests/test_video_examples.py` still read the
committed ones. They moved to `aitu-backend/tests/fixtures/frame-examples/` (`git mv`, so their
history follows) and the test names that folder. The tests of `config.py` no longer test the
setting that is gone; `conftest.py` keeps clearing the master user's variables.

Not changed, and why:

- `tests/test_pmn.py` and `test_muscriptor_engine.py` have a fixture named `data_dir`: it patches
  `backend_root` to a temporary folder, and reads nothing of the old store.
- `pocs/poc-muscriptor/` read its audio from `aitu-backend/data/audio/`. A proof of concept kept for
  its data; its README now says the folder is gone.
- `scripts/seed/youtube-library/seed_library.py` (the seed list of 31 songs) is older than
  `.database/` and calls the store API of that time. Its `library.json` and `seed-state.json` are
  what Phase 3 and Phase 12 read. Not run since Phase 3 (section 8).
- The editor settings that hide `aitu-backend/data/audio` (`.vscode/settings.json`,
  `.cursorignore`, `.cursorindexingignore`) are not tracked by git; they are the user's.

# 5. The documentation (Story 15.3)

| Page | What changed |
|---|---|
| `context/00-project-complete-overview.md` | Rewritten for the app as built: users, what is stored in the three layers, the flow, the sidebar, the project steps, From scratch and From other projects, Recording in Sheet, My library, the Public Library, requests and the review, sharing, Play mode, every router, the code map. The stale "plot the reader clicks" is gone (the negra default of Phase 2). Its run section is two sentences and the link |
| `context/01-project.md` | The product page: it points at the app context, says what the app does in four points, keeps the problem domain, gives the two groups of implementations, and the scope of this version. "A database" and "authentication" are no longer out of scope |
| `context/05-deployment.md` | Was a stub ("POC is local-only; planned: Docker containers"). Now: what runs on the machine at home, how to move it (`db-backup`, `db-restore`), and what a production version needs, each line tied to a risk of `08-security.md` or a choice of the app context |
| `README.md` (root) | The product and its run section rewritten: `make up`, the address, the link |
| Run instructions | `04-local-development.md` is the one home. The root `README.md`, `aitu-backend/README.md`, `aitu-frontend/README.md`, `context/backend/README.md`, `context/frontend/README.md`, `02b-local-setup.md` (12.2, 12.3) and `09-coding-conventions.md` now say the one command and link to it. Its section 5 lists every browser check (it named five) and when to skip the ones that transcribe |
| Two contradictions found on the way | `02b-local-setup.md` 12.1 said `.database/` was a link in the repository (it is `AITU_DATABASE_DIR` since 2026-10-06) and that `aitu-backend/data/` was read by the migration; fixed |
| The redirects and the old store | `frontend/pages.md`, `projects.md`, `play-mode.md`, `frontend/README.md`, `components.md`, `score-pdf.md` (it still named `/playground/rhythm`), `endpoints.md`, `07-database.md`, `paths-and-data.md` (§7 the mount, §9 the migration as history), `aitu-backend/README.md`, `aitu-frontend/README.md` |
| The state of the work | `implementations/README.md`, the folder README (Phases 14 and 15 added, "complete"), `00-index.md`, `00-documentation-instructions.md`; the plan's "as built" notes (sections 6.3 and 20); the checklist |
| `aitu-frontend/README.md` | `check:journey` in the table of scripts |

# 6. The checks

| Check | Result |
|---|---|
| Backend, full run **on the GPU** (`make test-backend`) | 1,124 tests: 1,123 passed and the known `test_the_worked_example_at_00_46_prints_three_equal_corcheas`, which fails on a clean checkout too. Nothing skipped: the GPU tests ran, the real-model test too. Phase 14: 1,133; the 9 fewer are the 8 tests of the migration and the test of `AITU_DATA_DIR`, removed with them |
| `test_config.py`, `test_video_examples.py`, `test_database.py` after the cleanup, on the CPU | 27 passed |
| `black`, `flake8` on the changed backend files | clean |
| `tsc -b`, `npm run lint`, `npm run build` | clean; the chunk-size warning of Phase 0 |
| `check:journey` (new) | 21 checks, passed twice in a row (runs 3 and 4) |
| `check:play` (changed) | 32 checks passed, nothing left behind (run alone, after the backend tests) |
| `make db-check` on the real `.database/` | no problem after every run; no audio file left without a project |
| `scripts/docs/check-links.py` | passes |

No page changed its look, so the 13 checks of the 09 guidelines were not run again; the screenshots
of the journey show the pages of Phases 5 to 14 as they are.

| Shot | Page |
|---|---|
| 01 | **New project**: the YouTube link |
| 02 | The Notes step, live |
| 03 | The Hands step |
| 04 | The Sheet step |
| 05, 06 | **Save to library**; the author's song |
| 07 | **Publish** with **Propose this song** |
| 08, 09 | The request, the master user's view: Conversation; Sheet |
| 10, 11 | **Finish your review**, every item accepted; Accepted |
| 12, 13 | The reader: **Add to my library**; the reader's song |
| 14 | Play mode, playing |
| 15, 16 | **From other projects** with the pulled version; the new project's Sheet step |

# 7. What implementation 02 leaves open

These are the open points of the phase reports that are still true, gathered for the next work.

| Point | Where it came from |
|---|---|
| **Q-5**: the sources of the `spain` and `catalan` regions, genres and tags (Wikidata recommended for genres); the 8 seed songs not on the chart | Phase 12, section 9 |
| A merge of public artists or songs, by request or by the master user, must keep both import keys and move the private `public_id` links | Phases 12, 13, 14 |
| The master user cannot move **Default** away from Hard | Phase 14 |
| A user is never deleted in the app, only disabled (the checks remove theirs with `public_fixture remove-user`, a host command) | Phase 14 |
| A read-only sheet (a request's Sheet tab) says "Untitled" when the sheet has no title, and every sheet draws the passage header ("negra = 150 ms · ≈400 BPM") | Phase 14, section 9; seen again in shots 09 and 16 |
| Offline downloads (Q-7), HTTPS, a production build | Left for the production version ([`05-deployment.md`](../../05-deployment.md)) |
| `seed_library.py` predates `.database/` | Section 4.2 |
| The lyrics of the public songs are shown, fine for this personal version only | Phase 13 |

# 8. Learnings

- **The GPU of the backend container can disappear while the app looks healthy**: `/health`
  answers and a transcription waits. A long check that transcribes should look at
  `GET /matrix/engine` (or `nvidia-smi` in the container) before it starts.
- **Do not edit `src/` of either service while a browser check runs**: both reload on a change
  (`uvicorn --reload`, Vite), and the check fails for a reason that is not the app's.
- **Play mode hides its buttons while it plays**: a script uses the keys (Space, Escape).
- **A wait for "a notehead" after a page change must make sure the old page is gone**, or it
  measures the page it left.
- **A journey with two users needs three accounts** when the reviewer is the master user: the
  master user's library must stay untouched.
