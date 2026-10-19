# 02: Phase 16 report: The `spain` and `catalan` regions, from the 60s to today

Plan: [`02-plan.md`](02-plan.md) sections 3.3 (Q-9), 15.5, 15.6 and 20, Phase 16. Checklist:
[`02-checklist.md`](02-checklist.md). Branch `feat/phase-16`, made from `master` at `7bbfcc2` (the
plan changes for Phases 16 and 17, committed at the start of this phase). Built 2026-10-18 and
2026-10-19 on the Ubuntu machine; the GPU held about 18 GB of another project, so the backend tests
ran on the CPU and no check that transcribes was run (nothing of the transcription changed).

The pages this phase writes are [`../../music-library/regional-sources.md`](../../music-library/regional-sources.md)
(new) and the regional parts of [`popularity.md`](../../music-library/popularity.md); this report
is the detail behind them.

# 1. Summary

| Story | Result |
|---|---|
| 16.1 The research | Four researchers in parallel (the official Spanish charts, the Spanish radio lists, the Catalan lists, the open catalogues and the APIs), one report: [`research/phase-16-spanish-and-catalan-charts.md`](research/phase-16-spanish-and-catalan-charts.md). `regional-sources.md` with the table of sources, the gaps per decade, the recommendation. **Q-9 raised, answered 2026-10-18: the recommendations** (five sources; both APECAT top 30 count as `catalan`) |
| 16.2 The data | `scripts/music-library-regions/` (download, readers, build, tests): five sources downloaded into `data/music-library-regions/` beside the repository, paced, resumable, no refusal. Revision `0006`. `library/regional_import.py` (`make regional-import`): on copies, then on the real `.database/` after `make db-backup`; 12,014 songs and 4,034 artists made, `spain` 12,870 songs, `catalan` 960; a second run made nothing |
| 16.3 Popularity per region | Every place scored against 100; a region's popularity the largest of its charts'; the lists of number ones only with a fitted weight, the monthly list as 3 weeks a month, kworb's totals as an estimate where no chart lists the song; all chosen by the Q-6 criteria (section 5). The pages: the Region chip, "Popularity in Spain", a popularity per region on the song page, every chart named with its region |
| 16.4 Documentation | `regional-sources.md` (new), `popularity.md`, `reconciliation.md`, `ontology.md`, `music-library/README.md`, `07-database.md`, `paths-and-data.md` §6, `endpoints.md` §7.3, `00-index.md`, the scripts' README; the plan's "as built" notes; the checklist |

Checks (section 7): backend 1,130 tests on the CPU, only the 3 known CPU failures; `test_regional_import.py`
(new, 6) and `test_parse.py` (new, 6) pass; `check:public` (changed, 47 checks: the 38 of Phase 13 and 9 for the regions) passes; lint, build
and `check-links.py` pass; `make db-check` reports no problem.

# 2. The research and Q-9 (Story 16.1)

The `deep-research` skill ran four researchers in parallel; the previous session ended while they
ran, they were resumed by message and saved their notes; one writer made the report. The notes and
the report are in `data/music-library-regions/research_notes/` and `reports/` (outside git); the
report is copied into this folder's `research/`. What it found, in short: Spain has every weekly
place only from 2001-12-30 (PROMUSICAE: top 20, 50, 100), Los 40 every place from 2004 and the
number one from 1966, before 2002 only number ones (plus an unsourced weekly top 10 for 1982 to
1996); Catalonia has one measured chart, the APECAT / BMAT monthly top 30 from September 2018. No
chart source has an open licence; PROMUSICAE allows "strictly private" use, Los 40 "personal and
private" viewing and reserves text and data mining. The user chose the recommendation (2026-10-18).

Found on the way, for Phase 17 (Q-10): Spotify's Web API gives no `popularity` since February 2026
and its terms forbid training on its data; YouTube's `search.list` has its own bucket of 100 calls a
day since June 2026, and stored statistics must be refreshed within 30 days. The user put
`YOUTUBE_API_KEY`, `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` in `.env` (2026-10-18); nothing
reads them yet.

# 3. The download and the build (Story 16.2.1)

## 3.1 The scripts

`scripts/music-library-regions/`, standard library only like the parallel work's
`scripts/music-library/`: `common.py` (one timer per source, `manifest.sqlite`, a page saved once
under `raw/`, a refusal or a challenge page waits 60, 120, 240 s then stops), `download.py`,
`parse.py` (the readers), `build.py` (one database per source, written again from `raw/`),
`test_parse.py`. The client name is the parallel work's. Times and counts: `regional-sources.md`
section 7.

| Source | How it is read |
|---|---|
| spanishcharts.com | Every Sunday from 2001-12-30 (`weekchart.asp?cat=s&year=Y&date=YYYYMMDD`; the year menu starts at 2005, earlier weeks load by address). Rows split on `<tr onclick=...showitem.asp`; a new entry shows an image where last week's place is. The key is the site's own `interpret|titel` |
| los40.com | The 61 year pages (`/lista40/numeros-1/YYYY/`, the trailing slash or a 301) give every number one with its list's date: 1966 to 2003 need nothing else. Every Saturday from 2004-01-03 (`/lista40/listas-anteriores/YYYY-MM-DD/`); a date with no list answers 200 with no row. Each row has a YouTube link (75 % of the songs) and an Apple Music id. Names are escaped twice on some rows (`&amp;amp;`); artists are separated by `;` |
| kworb.net | One page, `es_weekly_totals.html`: per song its Spotify track id, weeks, top 10 weeks, peak, weeks at the peak, streams |
| APECAT | The archive page's 198 PDF links; `pdftohtml -xml` gives each text with its place and font: the title in ExtraBold, the artist in Medium, the label plain, the place left of 170 pt. The PDFs of 2018 and 2019 cut text into pieces of one to three letters: pieces of one font on one line are joined, a gap of more than 3 pt a space. The series comes from the file name (CatLang, Llengua; CatProd, Produccio): the header letters sit at different heights. The period comes from the header's date range, not from the month name (wrong on several files: an "abril" file says MARÇ, two 2024 files both say JULIOL); the three first lists have no range and get the 12th of the month before to the 11th. 3 PDFs are images (2020), 2 repeat an earlier list (the June 2022 Catalan-label list is May's again) |
| Wikipedia | `index.php?title=...&action=raw`, a redirect followed. A small wikitable reader with rowspans filled down; the header row before the first `|-` is read; the 1982 Spanish page has the place and the date columns the other way round. `size` of a week is its highest place (a page that repeats a date gives 20 rows) |

## 3.2 What went wrong and was fixed

- **An APECAT file name with accents** stopped the first run after 19 files (`urllib` refuses a
  non-ASCII address); the address is quoted before it is sent. The run continued from file 20.
- **A 404 page in the repository root** (`yr.html`) left by a researcher's `curl`; moved out.

# 4. The import (Story 16.2.2)

## 4.1 Revision `0006`

Written in the scratchpad first and tried on a copy of the real database (up, down, up; no
difference from the models), because the running backend migrates the real database as soon as a
revision is in `src/` (Phase 12's learning). Then `make db-backup`
(`.database-20261018-220952.tar.zst`) and the file into `src/`: the real database moved to `0006`
at the next request. It adds the regions `spain` and `catalan`, `song_region_popularity` (`song_id`,
`region_id`, `popularity`, `basis`, `chart_source_id`), `song_keys` and `artist_keys`.
`database.HEAD_REVISION` is `0006`.

**Why a table of keys**: a song found on four sources has four identities; `external_key` holds one.
It is also what the open point of Phases 12 to 14 asked for (a merge must keep both keys).

## 4.2 The identity rule

`regional_import.py` reads the five source databases (read only) in the order of the
recommendation; a song an earlier source made is found by the later ones. A song is: the public song
with its key (`external_key` or `song_keys`); else the public song whose compared title (no case,
accents, punctuation; also without a closing `(...)`, a `feat.` part, a ` - Remix` ending; a title
of symbols only, "+", as it is) is the same **and** that credits one of its artists (the credit's
parts, split on `;`, `/`, `,`, `feat.`, `con`, `amb`, and the parts of an `&` or `y` for matching
only); else a new song with the year of its first week, and its artists found by any name of a
public artist, or made (split on `&` or `y` only when every part is a known artist: "Alaska y
Dinarama" stays one). Checked on samples of the joins (all right) and by a search for missed
duplicates: 28 pairs, nearly all distinct recordings ("(Taylor's Version)", remixes), one real miss
(the symbol title, fixed).

## 4.3 The weeks

The weeks of the seven charts are deleted and written again on every run. A list's period becomes
its weeks: a week one, a fortnight of the 60s two, a month three (section 5.3). A number one only
list has one row per week at place 1.

## 4.4 The real run

`make db-backup` (`.database-20261019-085953.tar.zst`, 1.3 GB), `make regional-import` (5 s): the
counts of `regional-sources.md` section 7; a second run: every song found by its key, 0 made, 2.1 s;
`make db-check`: no problem. The real database now has 21,069 public songs and 7,032 public
artists.

# 5. Popularity per region (Story 16.3.1)

Each change was measured on a copy of the real database after the import
(`scratchpad/measure.py`), with the criteria of Q-6.

## 5.1 Every place against 100

`popularity.Weights.reference` (`DEFAULT`: 100; `PLAN`: none, the chart's own size). Songs of the
Spanish sales chart whose best place is 6 to 10, median popularity by the era of their first week:

| Era | Against the chart's own size | Against 100 |
|---|---:|---:|
| Top 20 (2002 to 2008), 241 songs | 11.2 | 43.1 |
| Top 50 (2009 to 2014), 153 songs | 30.3 | 47.6 |
| Top 100 (2015 to 2026), 292 songs | 50.4 | 50.4 |

The US chart is a top 100: no worldwide score moved (a test checks it).

## 5.2 A region's charts

`song_scores` and `chart_scores` take a region; a region's score is the **largest** of its charts'
scores (they overlap), a chart with no region counts as `worldwide` (as before Phase 16). The Q-6
criteria on the Spanish sales chart alone: 47 of 6,539 songs at 95 or more (0.7 %), the order
follows the weeks at number 1 (Spearman 0.63).

## 5.3 The lists of number ones only, and the monthly list

Three attempts, in order:

1. **The median of a number one's points per week at number 1** on the full list (the research's
   suggestion): 4.35 and 7.70. From 1982 to 1996 the number ones scored 10.9 points away from their
   full top 10 score, and dozens of 60s and 70s songs scored 100.0. The ratio counts a song's other
   weeks, so it does not say how close the stand-in comes.
2. **The weight closest to the full score** (fitted as the Spotify estimate): 3.00 (the sales list,
   on the weekly top 10 of 1982 to 1996) and 7.90 (Los 40, on its lists from 2004). Closer (10.3 and
   6.6 points), but 171 songs of `spain` (1.3 %) at 95 or more: in the 60s and 70s a number one held
   the top 3 to 4 weeks, from the 80s on one week.
3. **The closest weights, lowered together as little as Q-6 needs** (at most 1 % of the region's
   songs with a chart value at 95 or more): a factor 0.60, so 1.80 and 4.74. 96 songs at 95 or more;
   the mean difference rises to about 13 points (a per-chart limit, tried first, gave 1.35 and 4.10
   and 16 points: too strict). Chosen.

The same criterion for `catalan`: with a month as 4 weeks (the weeks it covers), 22 of 907 songs
(2.4 %) were at 95 or more; a radio's monthly list keeps a song for months. A month counts as the
most weeks (4, 3, 2, 1) that keep 1 %: **3** (4 songs, 0.4 %).

## 5.4 The Spotify estimate

kworb's totals become points: the weeks at the peak at the peak, the other top 10 weeks spread over
the places below it, the other weeks over 11 to 200 (zero below 100); one factor fitted on the
4,057 songs also on the sales chart: 1.15, mean error 7.0 points. First used whenever it was higher
(2,839 + about 1,100 songs replaced a chart value); then only for a song no chart of the region
lists (2,839 songs, average 2.0): a chart value always wins, as the plan asks of Phase 17.

## 5.5 The result

| Region | Songs | `weeks` | `number_ones` | `estimated` | At 95 or more |
|---|---:|---:|---:|---:|---:|
| `spain` | 12,870 | 8,524 | 1,507 | 2,839 | 96 |
| `catalan` | 960 | 907 | 0 | 0 | 4 |

Songs of each region by the decade of their year: `spain` 50s 12, 60s 160, 70s 264, 80s 750, 90s
1,008, 00s 2,084, 10s 3,088, 20s 2,935, no year 2,569 (kworb's songs); `catalan` 70s 2, 80s 1, 90s
1, 00s 8, 10s 261, 20s 687 (the songs before 2018 are the Catalan Spotify table's, with no
popularity). The all-time `spain` order starts with number ones of the 60s and 70s and the hits of
the 2020s; "Himno oficial del centenario" (El Arrebato, the physical singles chart of 2005) is first.

# 6. The pages (Story 16.3.2)

| Page | Change |
|---|---|
| Public songs | The Region chip offers `spain` (12,870) and `catalan` (960) with their counts. With a region the column is "Popularity in Spain", sorted by it; with a decade too, "Popularity in Spain in the 70s", worked out from that region's weeks of the decade. The header is on two lines (`DataTable`: a label with a line break) and the title and artist columns are at most 300 and 210 px: with a region the table was wider than the page at 1440 px and the sorted column was out of view |
| A public song | "Popularity worldwide" (when the song has a regional one and is worldwide), one fact per region ("Popularity in Spain", "≈ 96.5 of 100" for `number_ones` or `estimated`, why on hover), **On the charts**: each chart named with its region; a list of number ones only says "Weeks at number 1" and no best place. The chart line starts at the window's width (it started at 640 px and shrank after a measure, which made the 390 px check fail once with three charts) |
| API | `GET /public/songs/{id}`: `regionPopularity: [{region, popularity, basis}]`, each chart's `region` and `size`. `GET /public/songs?region=`: the region's popularity |

## 6.1 The 13 checks of the 09 guidelines

On Public songs and a public song, with the screenshots of [`screenshots/phase-16/`](screenshots/phase-16/).

| # | Check | Result |
|---|---|---|
| 1 | One sentence | Find a song by where it was a hit, and see how big a hit it was there |
| 2 | Every sentence a label, control or fact | No sentence added; the hover on "≈" says why |
| 3 | Words above the first content | Unchanged: the title, the chips |
| 4 | Very wide | The five columns fit at 1440 px whatever the titles (shots 02b, 02c) |
| 5 | Narrow (390 px) | 0 px of sideways scroll on a song with three charts (shot 15); the table scrolls inside itself |
| 6 | Longest, shortest, none | A long title or credit cut with "…" (full on hover); a song only on number ones lists: no best place (shot 03c); a song with no regional popularity: the worldwide fact only |
| 7 | Buttons say what happens | No new button; the chip values are "Spain", "Catalan" |
| 8 | Helper lines | None added |
| 9 | Loading, empty, partial, error | Unchanged |
| 10 | Tab through it | The chip and its menu, as before |
| 11 | Internal names | None: no "basis", "number_ones", "estimated" on screen; "≈" and the hover |
| 12 | First-time user | "Popularity in Spain", "Weeks at number 1", "On the charts" |
| 13 | Anti-patterns | No badge, no colour: the region is grey text after the chart's name |

| Shot | Page |
|---|---|
| 02b | Public songs, Spain |
| 02c | Spain in the 70s |
| 02d | Catalan |
| 03b | "Superestrella" (Aitana): Popularity in Spain, two charts |
| 03c | "Black is black" (Los Bravos): two lists of number ones only, "≈" |
| 01, 03 to 17 | The Phase 13 walk again; 15 is Stayin' Alive at 390 px with its three charts |

# 7. The checks

| Check | Result |
|---|---|
| Backend, full run **on the CPU** (another project held 18 GB of the GPU) | 1,130 tests: 1,126 passed, 1 skipped (the real-model test), 3 failed: the known `test_the_worked_example_at_00_46_prints_three_equal_corcheas` and the two Transkun tests that fail only without a GPU. Phase 15: 1,124 |
| `test_regional_import.py` (new) | 6 passed: the identity rule across sources, a monthly list as weeks, the fitted weight, the popularity per region and its basis, the worldwide popularity unchanged, a second run that makes nothing and keeps a changed title, the list and the song page by region, the month rule |
| `test_parse.py` (new, `scripts/music-library-regions/`) | 6 passed, no network: each reader on small pieces of its format written in the test |
| Changed tests | `test_popularity.py` (the reference size), `test_public.py` (`spain` is a region now; `mars` is the unknown one), `test_database.py` (the new tables and regions) |
| `black`, `flake8`, `mypy` on the changed backend modules | clean |
| `tsc -b`, `npm run lint` | clean |
| `check:public` (changed: the regions) | 47 checks passed (9 new), nothing left behind (run three times: a header check and a wait for "the chart" needed changes, then the 390 px race of section 6) |
| `make db-check` on the real `.database/` | no problem after both imports |
| `scripts/docs/check-links.py` | passes |

# 8. Open points

- **An artist written two ways is two artists** ("Aitana" and "Aitana Ocaña"; matching by artist
  never joins the same song under two names). A merge is a request (Phase 14); the keys are kept.
- **The artists list sorts by the worldwide popularity**: a Spanish-only artist is at 0 there.
- **The 100 songs of the Catalan Spotify table and every Catalan song before 2018 have no
  popularity**: no places exist. Phase 17 (YouTube views); Enderrock's yearly YouTube lists, with
  views, are a natural sample.
- **The physical singles chart of 2005 to 2008** puts a football anthem first in Spain; it is what
  the chart says.
- **Not downloaded** (the research's second wave): Discomanía's top 20s of 1960 to 1965, the
  PROMUSICAE year-end lists, El Portal's radio chart, Enderrock's lists; and the hand work (the
  book, the scans).
- **Los 40 reserves text and data mining**; the download was for this private app only (the user's
  choice under Q-9).

# 9. Learnings

- **Measure a stand-in by how close it comes, not by a ratio**: the research's median ratio looked
  reasonable and was 11 points off; the fitted weight and the Q-6 criteria told the difference.
- **A rule fitted on one era can saturate another**: the number ones of the 60s and 70s held the
  top three times longer than those it was fitted on. Check the share at 95 or more per region.
- **A radio's monthly list keeps a song for months**: counting a month as the weeks it covers
  saturates its top.
- **Old PDFs cut text into letters**: `pdftohtml -xml` gives positions and fonts; join pieces of a
  line by their gaps, and take a series or a date from the most reliable place (the file name, the
  date range), not the month name.
- **A drawing that starts wide and shrinks after a measure** fails a narrow-window check that reads
  the page too early; start it at the window's width.
- **A wider table header can push the sorted column out of view**: check the widest content at
  1440 px when a column's label grows.
