# 02: Phase 12 report: The music library data reconciled

Plan: [`02-plan.md`](02-plan.md) sections 3.3 (Q-5, Q-6), 8.6, 15.3, 15.5 and 15.6, and section 20,
Phase 12. Checklist: [`02-checklist.md`](02-checklist.md). Branch `feat/phase-12`, made from
`master` at `9b9475b` (Phase 11 merged and pushed, after the user's check). Built 2026-10-16 on the
Ubuntu machine. The page this phase writes is
[`../../music-library/reconciliation.md`](../../music-library/reconciliation.md); this report is
the detail behind it. No UI changed, so there are no screenshots and no 13-check pass.

The download (`/home/david/Documents/projects/music/data/music-library/library.sqlite`) was only
read, always with `mode=ro&immutable=1`; its folder still dates from 7 October. Nothing was written
into the parallel work's worktree or scripts.

# 1. Summary

| Story | Result |
|---|---|
| 12.1 The reconciliation | `reconciliation.md`: the mapping table by table, the gaps both ways, the identity rule, the re-entries, the seed list. Revision `0003` adds only `song_lyrics`, `album_artists`, `album_chart_entries`, `albums.release_date`, `albums.popularity`. `library/public_import.py` (`make public-import`): the whole download in 2.5 s, a second run makes nothing; 23 of the 31 seed songs found, 8 added from the seed list. Run on copies only: the real import is Phase 13 |
| 12.2 Popularity | `library/popularity.py`: the formula of section 15.6 with every weight a parameter, time ranges, the chart's size and weight; it matches the parallel work's 17,454 stored scores where the songs are the same. On the real data the top is flat and long runs win (section 5). **Task 12.2.2 waits for the user**: the hand ranking of 20 songs (`library/hand_ranking.json`), then `make popularity-tune` |
| 12.3 Decisions | Q-5 and Q-6 raised with a recommendation each (section 9) |

Checks (section 7): backend 1,107 tests on the CPU (the GPU was in use), the 3 known CPU failures
and 1 skip; the 13 new tests pass; the migration matches the models; `check-links.py` passes.

# 2. What the download is, read from it

The implementation file of the parallel work was read first, then the database. What it adds to that
file:

- **The chart is the US one.** The week of 1978-01-07 of the site is the Hot 100 of that week (How
  Deep Is Your Love at 1, Baby Come Back at 2, ...). The site does not name its chart, so this is an
  inference. Rankings: 160,810 song weeks and 129,988 album weeks, positions 1 to 100, 2,615 and
  2,616 weeks from 1976-09-04 to 2026-10-03.
- **134 songs are re-entries** of another song: 81 `[re-release]`, 51 `[seasonal]`, one
  `[Re-Release]`, one `[re-recorded version]`. 66 have their first run in the download (same title
  without the bracket, same first artist, no week shared); 68 first charted before 1976.
- **No two artists share a name** once case, punctuation, "the", "&" and "$" are ignored: the site
  writes each artist one way. Each artist has exactly one name.
- **Album tracks**: 108,444 lines, 8,510 of them name a song in the download (8,412 songs). 8,404
  songs have their page's album in that album's track list; 102 are on the track list of another
  album; 94 are on more than one album.
- **Lyrics**: 16 MB in all, 1.8 KB on average, 14.9 KB at most.

# 3. Story 12.1: the reconciliation

## 3.1 The design

**Where the import lives.** In the backend (`aitu_backend/library/public_import.py`), because it
writes the app's tables through the app's models and Phase 13 runs it; not in `scripts/`, which
holds one-off scripts. It runs on the host (`make public-import`, with `uv`, like `make db-*`),
because the download is beside the repository and is not mounted in the containers.

**What revision `0003` adds, and only that.** Each addition is a field the download gives and the
import needs (the reconciliation, section 3). Rejected: a column `songs.lyrics` (a list of songs
would read the words), a nullable `album_id` on `chart_entries` (the existing table would be copied
by batch mode and its meaning changed; a table of its own is simpler), an identity table with
several keys per row (the re-entries are joined by a rule applied on each run, so one key per row is
enough; see section 8 for the case it does not cover).

**Public rows have no owner.** Section 15.5 says "owned by the master user"; the models of Phase 3
say `owner_id` is empty for a public row. The public rows follow the models: the master user manages
them through the Admin panel (Phase 14), no row names them.

**The identity**: `external_key` = `musicchartsarchive.com` + the source path. A seed song that the
charts do not have: `seed:<title>|<artist>` in the compared form. Seed artists: `seed:<name>`.

**A second run never undoes a person's change** (reconciliation section 4.2). A row it makes gets
everything; a row it finds gets only empty fields (year, release date, lyrics); links (artists,
albums) are written only for a new song or album; the chart weeks of its two charts are deleted and
written again, and the popularity worked out again. A weight the master user gives a chart is kept.

**Re-entries** (reconciliation section 4.3) are one song: `same_songs` maps each source song to the
song it repeats; the song keeps its own key, title, year (the earliest of the group) and artists,
gets the weeks of both and the first lyrics of the group. A re-entry with no earlier row keeps its
row without the bracket. Considered and rejected: keeping re-entries as songs of their own (the app
context asks for no duplicates, and a piano version is made of a song, not of a chart run).

## 3.2 The import on the real download

| Run | Result |
|---|---|
| Into an empty `.database/` | 2,995 artists, 8,341 albums (6,382 with a release date), 9,047 songs (+ 8 of the seed list, 3 new artists), 10,838 song credits, 8,510 album credits, 8,581 song-album links, 9,038 lyrics, 9,047 song regions, 160,810 song weeks, 129,988 album weeks; 2.5 s |
| The same again | 0 made, every count the same, 2.1 s |
| Into a copy of the real `.database/` (32 private songs, 24 artists) | the same counts; the private rows unchanged; 2.4 s |

Checked by hand on the result: Stayin' Alive (1977, Bee Gees, Saturday Night Fever at track 1, the
weeks at 65 and 1, its lyrics); Give Me Everything (Pitbull, then Ne-Yo); Folklore (2020-07-24,
13 of its 17 tracks have a song in the download); Billie Jean (one song, 1983, with the 2009 weeks
of its re-entry); White Christmas and All I Want For Christmas Is You without "[seasonal]".

## 3.3 The seed list

23 of the 31 songs are found by the rule of reconciliation section 7, with two hand rules (ELO,
"99 Red Balloons" as "99 Luftballons"). The 8 others did not reach the US chart: 1973, Stay the
Night and Bonfire Heart (James Blunt), Grace Kelly (Mika), Moonlight Shadow (Mike Oldfield), 2002
(Anne-Marie), Superestrella (Aitana), Club Can't Handle Me (the list says David Guetta). They are
added with the list's title and artist only. "I Knew You Were Trouble" has two songs of that title
on the chart; the list names no artist, so the most popular (Taylor Swift's) is taken.

# 4. The real `.database/` is at revision `0003`

The backend container runs `uvicorn --reload` on the mounted `src/`. When the migration file
appeared, it reloaded and, at its next request, brought the real `aitu.sqlite` to revision `0003`.
Checked read only: the three new tables exist and are empty, the two album columns exist, nothing
else changed. The revision only adds, so the app works as before.

The consequence: **code without revision `0003` (`master` before this branch is merged) cannot open
that database** (Alembic refuses a revision it does not know). If the branch were dropped, the way
back is `alembic downgrade 0002` (tested on a fresh database: down to `0002` and up again). The rule
is now in `07-database.md`.

# 5. Story 12.2: popularity

## 5.1 The code

`library/popularity.py`: `points`, `score` (a list of `Week(rank, size, weight)`), `Weights` (the
five numbers of the formula; `PLAN` is the plan's), `song_scores` and `album_scores` (from the tables,
with an optional `start..end`, both ends included), `store_all_time` (the public rows' all-time
value; 0.0 for a public row with no week), `kendall_tau` and `tune` (a grid of 480 weights: the peak
weight 0.2 to 0.6, the saturation 5 to 40, the two powers 1 to 4; ties broken by the distance to the
plan's weights). With several charts, each week counts with its chart's weight and the peak is the
best weighted peak (only one chart exists today).

Measured on the copy: all weeks, 9,041 songs, 212 ms; the 80s, 2,179 songs, 46 ms; the last two
years, 678 songs, 9 ms. A sort by popularity inside a decade can work it out on each request.

The app's scores equal the parallel work's stored ones for all 8,341 albums and the 8,981 songs not
joined; the 66 joined songs score higher (Dakiti 85.1 → 85.4, Into The Night 63.5 → 74.8).

## 5.2 The first weights on the real data

| | Plan's weights | A: saturation 25, week power 3 | B: 0.5/0.5, saturation 20, power 3 | C: 0.5/0.5, saturation 30, power 4 |
|---|---|---|---|---|
| Songs at 95 or more | 214 | 3 | 14 | 1 |
| Median score | 48.0 | 31.4 | 37.3 | 32.9 |
| Number 1 for 30 weeks | 97.0 | 81.9 | 88.8 | 81.6 |
| Number 1 for 1 week | 45.7 | 42.4 | 52.4 | 51.6 |
| Place 20 for 20 weeks | 65.1 | 42.0 | 47.2 | 39.0 |
| The first song | Lose Control (1 week at 1, 112 weeks) | the same | the same | the same |

(Before the joins; after them 218 songs are at 95 or more with the plan's weights.) Every variant
keeps Lose Control, Blinding Lights and A Bar Song first: the length of the run decides, and recent
songs run longer (median weeks per charting song: 14 in the 70s, 20 in the 90s to the 2010s, 7 in
the 2020s, where many songs chart one week; but a 2020s hit runs 60 to 112 weeks). So the weights
cannot be chosen from the data alone. The list for the user's ranking is
`library/hand_ranking.json`: 20 songs of different shapes (19 weeks at number 1, a 112-week run with
one week at 1, a top-10 peak of a few weeks, a 79-week run whose best place is 17, 12 weeks peaking at 35),
lettered by title so the letters suggest nothing.

**Needed later, when the user answers:** `make popularity-tune ORDER="..."`, then the chosen weights
become `PLAN` in `popularity.py` (and the values of plan section 15.6), and the tests of the plan's
examples change with them.

# 6. Tests

| File | Tests | What |
|---|---|---|
| `test_public_import.py` (new) | 6 | A small download in the parallel work's schema: every row becomes a public row with no owner; artists in order, through default names; a song with no artist; an album's artist, release date, chart history and popularity; the song-album links with their track numbers; the region; the two charts. A re-entry joins its song (one Billie Jean, weeks of both, the re-entry's lyrics); one with no earlier row loses its bracket. A second run makes nothing, keeps a changed title, a renamed artist, a removed credit, fills an empty year and lyrics, writes the chart weeks again. The seed list: found by title and artist, by title alone, by a second artist; the missing ones added once, with a new artist, no year, no region, popularity 0. The source file unchanged, nothing beside it. The compared forms |
| `test_popularity.py` (new) | 7 | The examples of the plan (97.0, 77.9, 65, 45.7, 41, 1); a position outside the chart; the chart's size and weight; other weights reorder two songs; a time range and the stored all-time value (a private song untouched); Kendall's tau; the tuning finds weights that follow a hand ranking the plan's weights do not |
| `test_database.py` | 1 changed | The three new tables |

# 7. The checks

| Check | Result |
|---|---|
| Backend, full run **on the CPU** (the app's own backend held 11 GB of the GPU, a process started a few minutes before) | 1,107 tests: 1,103 passed, 1 skipped (the real-model test), 3 failed: the known `test_the_worked_example_at_00_46_prints_three_equal_corcheas` and the two Transkun tests that fail only without a GPU. Phase 11: 1,094 |
| `black`, `flake8`, `mypy` on the new and changed modules | clean |
| The migration against the models (`alembic` `compare_metadata`) | no difference; down to `0002` and up again |
| `scripts/docs/check-links.py` | passes |
| Frontend checks, browser checks | not run: nothing in the frontend changed, and no route changed |

# 8. Open points

- **A merge of two public artists or songs (Phase 14) loses the merged row's key.** A later import
  would then make that row again. Phase 14 must keep the key: the simplest way is a table of extra
  keys per row, added with the merge.
- **A public song the master user deletes comes back on the next import.** The same table, as a
  list of refused keys, would cover it.
- **The lyrics are copyrighted text**: kept for this personal version only (reconciliation section 3).
- **"Club Can't Handle Me" is credited to David Guetta only**, as the seed list says (the single is
  Flo Rida's, with David Guetta). The master user can correct it by request; nothing is invented.
- **Albums are imported with their popularity** but no page uses it before Phase 13.
- **The chart is the US one** and its region is `worldwide`; a second country's chart is a second
  row of `chart_sources`, and its weeks a second set of `chart_entries` of the same songs.

# 9. Decisions for the user

**Q-5. The regions `spain` and `catalan`, the genres, the 8 seed songs not on the chart.**

| | Option | Consequence |
|---|---|---|
| Regions | **A (recommended)**: `spain` from the official Spanish weekly chart (PROMUSICAE: top 50 from 2008, top 100 from 2015), downloaded by a separate piece of work like the US one, after its terms and pace are checked; `catalan` with no chart, given by request (Phase 14) and from a list of Catalan artists the user writes | Spanish hits get a Spanish popularity; Catalan songs are found by region but have no chart popularity |
| | B: no download; both regions only by request | Nothing to build now; the regions start empty |
| Genres | **A (recommended)**: from Wikidata (open data; its genre of a song or artist), mapped by hand to the 13 genres, one or two per song | Most chart songs get a genre; the map needs one review |
| | B: only by request | The genre filter is empty at the start |
| Seed songs | **A (recommended, built)**: added with title and artist only | All 31 are in the Public Library; they get a chart later if a region's chart has them |
| | B: left out until another chart brings them (`make public-import ARGS=--no-seed`) | 8 of the user's own songs are missing from the Public Library |

**Q-6. The popularity weights.** The plan's weights make the top flat and favour long runs (section
5.2). Recommended: the user ranks the 20 songs of `hand_ranking.json`; the weights that follow that
order best replace the plan's, if they agree clearly better (Kendall's tau at least 0.1 higher);
otherwise keep the plan's and add a weight for the weeks at number 1.

# 10. Learnings for later phases

- **The running backend migrates the real database** as soon as a revision file is in `src/`
  (`--reload`). Write a migration only when it is ready, and say in the report that the real
  database moved.
- **Read the data before mapping it**: the re-entries, the US chart and the eight missing seed songs
  were not in the implementation file of the parallel work; three queries found them.
- **Open someone else's SQLite file with `mode=ro&immutable=1`**: nothing (not even a journal) is
  written beside it.
- **An import that runs again must know which fields belong to the source** (the chart weeks) and
  which become a person's once written (titles, names, links).
