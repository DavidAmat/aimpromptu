# 02-a: The public music library: checklist

The status lookup for this work. The plan is
[`02-a-public-library-build-plan.md`](02-a-public-library-build-plan.md). The brief is
[`02-a-public-library-build-prompt.md`](02-a-public-library-build-prompt.md). The app context is
[`../../../app/01-app-context.md`](../../../app/01-app-context.md).

Each phase report is `02-a-implementation-phase-N.md`, written by the agent that finishes the phase.

Status letters: `[x]` complete, `[p]` in progress, `[b]` blocked, `[c]` cancelled, `[ ]` not started.

This work does not edit the app. The other plan stays the owner of Spain, Catalan, genre, tags and
the popularity weights.

## Decisions

The plan's section 5.

- [x] **D-1** 10 seconds between requests, one request at a time, resume from saved files. Decided in the plan, 2026-10-05.
- [x] **D-2** Raw HTML under `.music-library/raw/`, week files split by year. Decided in the plan, 2026-10-05.
- [x] **D-3** `.music-library/library.sqlite` and `manifest.sqlite`, not the app database. Decided in the plan, 2026-10-05.
- [x] **D-4** Identity is the source path, not the title. Decided in the plan, 2026-10-05.
- [x] **D-5** Chart History is the ranking. A week page only fills a missing week. Decided in the plan, 2026-10-05.
- [x] **D-6** Chart size N is 100. Decided in the plan, 2026-10-05.
- [x] **D-7** Entities are the week-page links, plus albums and artists linked from those songs and albums. Decided in the plan, 2026-10-05.
- [x] **D-8** Decade is a view. All-weeks popularity is stored. Other time ranges are calculated on request. Decided in the plan, 2026-10-05.
- [ ] **Q-1** A block from the site (403, 429, 503). Raised only if a download phase hits it.
- [ ] **Q-2** A large number of songs with no year. Raised in Phase 4 only if the empty count is large.

# [ ] Phase 1: The scripts, the fixtures and the schema

## [ ] Story 1.1: The folder
- [ ] Task 1.1.1 A git worktree in a second folder, on a new branch. No branch checkout in the folder the other agent uses.
- [ ] Task 1.1.2 `scripts/music-library/` with `README.md`, and the `/.music-library/` block in `.gitignore`. No other shared file.
- [ ] Task 1.1.3 The fixtures of plan section 7.6, saved from the live pages, committed under `scripts/music-library/fixtures/`.

## [ ] Story 1.2: The parser and the schema
- [ ] Task 1.2.1 `common.py` and the parser: paths, artist links only, lyrics, tracks, full album URLs.
- [ ] Task 1.2.2 `test_parse.py` passes with no network, covering every fixture case in plan section 7.6.
- [ ] Task 1.2.3 The tables of plan section 7.2, created by `build_library.py` on an empty raw folder without error.
- [ ] Task 1.2.4 The popularity unit tests match the examples in plan section 8.

# [ ] Phase 2: The week pages

## [ ] Story 2.1: The download
- [ ] Task 2.1.1 Decade pages, year pages, and every dated singles and album week page, in `manifest.sqlite` with status 200.
- [ ] Task 2.1.2 The count report: weeks per chart, unique song paths, unique artist paths, unique album paths, and the estimated hours for Phase 3.

# [ ] Phase 3: The song, artist and album pages

## [ ] Story 3.1: The download
- [ ] Task 3.1.1 Every entity of plan decision D-7 saved with status 200.
- [ ] Task 3.1.2 The report: pages saved, song pages with lyrics, extra album links, extra artist links.

# [ ] Phase 4: The database

## [ ] Story 4.1: The build
- [ ] Task 4.1.1 `build_library.py` fills `library.sqlite` from `raw/`. A second run does not duplicate rows.
- [ ] Task 4.1.2 `checks.py` matches the examples in plan section 9: Stayin' Alive, Give Me Everything, Folklore, worldwide, no genre table.
- [ ] Task 4.1.3 `import_note` summarized in the phase report. No invented year and no invented artist.

# [ ] Phase 5: Popularity

## [ ] Story 5.1: The scores
- [ ] Task 5.1.1 All-weeks scores written into `popularity` for songs and albums.
- [ ] Task 5.1.2 Stayin' Alive and Folklore printed for all weeks, and Stayin' Alive printed again for 1977-01-01 to 1979-12-31.
- [ ] Task 5.1.3 The script README documents the commands. The phase report is the closing summary.
