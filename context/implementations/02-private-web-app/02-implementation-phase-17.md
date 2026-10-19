# 02: Phase 17 report: A popularity inferred from YouTube views

Plan: [`02-plan.md`](02-plan.md) sections 3.3 (Q-10), 15.6 and 20, Phase 17. Checklist:
[`02-checklist.md`](02-checklist.md). Branch `feat/phase-17`, made from `master` at `4f0bba9`. Built
2026-10-19 on the Ubuntu machine; another project held about 20 GB of the GPU, so the backend tests
ran on the CPU and no check that transcribes was run (nothing of the transcription changed).

The page this phase writes is [`../../music-library/popularity.md`](../../music-library/popularity.md)
section 6; this report is the detail behind it. The plots are in [`research/phase-17/`](research/phase-17/).

# 1. Summary

| Story | Result |
|---|---|
| 17.1 The sample | `library/signals.py`: free video ids from Los 40 (3,281 songs), Wikidata (4,500) and Enderrock's yearly Catalan top 100s (89, added in this phase); `videos.list` for 8,800 videos (about 200 units); an official channel rule (artist, Topic, Vevo, label); 100 searches spent on `catalan` songs of low chart values (81 found). 6,269 songs with an official video; the sample is 6,664 pairs of a song and a region with a chart value (`weeks`). Every answer kept in `data/music-library-views/answers.sqlite` |
| 17.1.2 Spotify (Q-10) | Q-10 answered at the start: kworb.net's all-time streams as a second signal, the API only for the artist's Spotify id. 694 artist searches, then Spotify asked for a wait of 23 hours (429, `Retry-After: 82217`); 646 kworb pages: 3,411 songs with streams (3,764 pairs of the sample) |
| 17.2 The fit | Seven candidates measured on songs left out (5 folds by song). The views say little: the best formula is 21.0 points from the chart value on average, the region's median 24.3; the rank correlation 0.43. **The user chose the line with the streams** (2026-10-19): `popularity.INFERRED` |
| 17.3 The inferred popularity | Revision `0007` (`song_signals`; the basis `inferred` and `inferred_on`). `make popularity-infer` and `make popularity-refresh`; a chart value always wins (the regional import keeps an inferred value only where no chart lists the song). The song page shows "≈ 64.6 of 100" with "Inferred from YouTube views" on hover; the lists sort by it. On the real database: 4 `catalan` songs today; 49 more and 4 songs with no region wait for the next days' searches |
| 17.4 Documentation | `popularity.md` section 6 (new), `ontology.md`, `regional-sources.md`, `endpoints.md`, `07-database.md`, `paths-and-data.md`, `.env.example`, the indexes; the plan and the checklist |

# 2. Q-10 (at the start)

Checked with the keys of `.env` before raising it: `GET /v1/tracks/{id}` and `/v1/artists/{id}`
return no `popularity` and no `followers` (removed in 2026), only identifiers and the ISRC. kworb.net
lists every track of an artist with its all-time streams (`/spotify/artist/<id>_songs.html`, robots
allows all), but only for artists it follows: 2 of the 5 Catalan artists tried (Oques Grasses, Els
Catarres; not Txarango, Lluís Llach, Sopa de Cabra). The user chose kworb's streams as a second
signal, kept only if they lower the error.

# 3. The signals (Story 17.1)

## 3.1 Where a video id comes from

| Source | How | Songs |
|---|---|---|
| Los 40 | `youtube_id` of `los40.sqlite` (Phase 16), found by `song_keys` | 3,281 |
| Wikidata | All items with P1651 and P175: 52,449 rows, 39,510 items in 2 s; labels (en, es, ca, mul) of items and performers by `VALUES` blocks of 2,000 (8 s each). A filter on the item's address timed out (504). Matched by `regional_import.Index.find` (title and one credited artist) | 4,500 |
| Enderrock | The 9 yearly "Top 100 de videoclips en català a YouTube" (2017 to 2025), `youtube.com/embed/<id>`; the video's title "Artist - Song" split and matched by the same rule | 89 |
| Search | `search.list` (`videoCategoryId=10`, 5 results), its own bucket of 100 a day | 100 asked, 81 found |

The 7,506 songs with a free id had 8,800 videos: 8,231 answered, 569 deleted or private.

## 3.2 The official rule (`signals.channel_kind`)

A first rule (the artist's name and words like "official" around it) kept 5,483 of 7,417 songs. The
rejected channels were mostly label-run: VEVO channels with other names ("CAguileraVEVO",
"5SOSVEVO", "SimonGarfunkelVEVO") and labels ("Warner Music Spain", 79 songs; Rhino; Atlantic;
Sony's "Catálogo" channels). The rule now: the artist's own channel (with and without "and"), its
"- Topic", a VEVO channel whose name is part of a credited name or starts one, else **`label`**: any
VEVO or label channel when the video's title names one of the artists and the song (a cover on
another artist's VEVO stays out). Kept: 6,188 of 7,506 (vevo 3,561, artist 1,878, label 512,
topic 237). Still out: fans, TV archives, directors' channels (Lyrical Lemonade), Eurovision.

## 3.3 The streams

`Client.spotify_artist` (one search, the item of the same compared name) then `kworb_songs`; a song
keeps the most streamed track of one of its title forms. 4 s between kworb pages. After 694
searches (about 50 minutes) Spotify answered 429 with `Retry-After: 82217`. The client slept on it:
**a wait longer than 5 minutes now closes the host for the run** (`MAX_WAIT`), and the streams
continue from the answers kept. 646 artists have a page, 24 have none.

## 3.4 What is kept

`answers.sqlite` (113 MB): one row per answer, keyed without any secret. A `youtube:video:` answer
older than 30 days is deleted when the answers are opened, and `refresh` always asks again
(`videos(days=0)`), so no view count is kept past 30 days (YouTube API Developer Policies). Whether
a value derived from views is a "derived metric" the policy forbids stays unresolved; the value is
worked out again from views read within the last 25 days (`FRESH_DAYS`).

# 4. The fit (Story 17.2)

`python -m aitu_backend.library.inferred fit` (`make popularity-fit`): the sample is every pair of a
song and a region with a `weeks` value and an official video (worldwide 3,452, spain 3,046,
catalan 166). Five folds by song; the mean difference from the chart value on the fifth left out;
the rank correlation ("order"); the share within 10 points.

| Candidate | Error | Order | Within 10 | worldwide | spain | catalan |
|---|---:|---:|---:|---:|---:|---:|
| The region's median (no signal) | 24.3 | 0.02 | 19 % | 23.7 | 25.1 | 22.1 |
| A line on the log of the views | 23.2 | 0.26 | 20 % | 22.6 | 23.9 | 25.2 |
| A line on the log of the views per year online | 23.4 | 0.23 | 20 % | 23.0 | 24.0 | 23.2 |
| The same with terms: region, decade, channel, years before the upload | 21.5 | 0.40 | 25 % | 20.3 | 23.0 | 17.8 |
| A curve that only rises, per region | 22.7 | 0.26 | 21 % | 22.2 | 23.7 | 16.5 |
| **The line with terms and the streams (chosen)** | **21.0** | **0.43** | 26 % | 19.8 | 22.6 | 18.2 |
| Boosted trees (a ceiling, not a formula) | 20.1 | 0.46 | 29 % | 18.2 | 22.4 | 17.5 |
| Boosted trees with the streams | 19.2 | 0.52 | 31 % | 17.2 | 21.5 | 17.4 |

On the 3,764 pairs with streams only: 22.2 without them, 21.4 with (order 0.42 and 0.46); the
streams alone order the songs as well as the views alone (0.31 and 0.33). On the 570 songs known
from number ones only (not in the fit), the chosen line is 12.9 points off (median 19.2).

**Why the views say so little** (plot 02): they set a ceiling, not a level. A song with few views
is rarely a big hit, but a video with millions of views a year can belong to a song that scored
near 0: a global hit that charted low in Spain (the power 8 gives places below 40 almost nothing),
or a US song of 10 weeks around place 50. Every relation also pulls its values to the middle: for
nine pairs in ten the chosen line gives 26 to 65, where chart values run from 6 to 89.

The design was cleaned before freezing it: the sample has no song before 1970 and none without a
year, so the first design's decade columns repeated the intercept. Now one term per decade from the
80s (the 70s and before the base), and a song with no year counts in its video's decade.
`popularity.inferred` gives the fit's values within 0.06 points (a test checks it within 0.2).

```text
INFERRED: intercept -92.6; per log10 of views per year 10.1; spain +5.3, catalan +34.1;
80s +5.0, 90s +4.7, 00s -1.4, 10s -17.5, 20s -18.1; vevo +0.8, topic +3.2, label +3.4;
+0.04 a year before the upload; per log10 of streams +8.5, or +78.0 with no streams
```

# 5. The inferred popularity (Story 17.3)

## 5.1 Revision `0007`

`song_signals` (one row per public song: `video_id`, `found_by`, `channel`, `published_on`,
`views`, `streams`, `read_on`); `song_region_popularity.inferred_on` and the basis `inferred` (the
table copied by batch mode). Written in the scratchpad, tried on a copy (up, down, up; no difference
from the models; the 13,777 rows kept), then `make db-backup` (`.database-20261019-100413.tar.zst`)
and into `src/`. **The app was running** (`make up`: the backend reloads on `src/` changes): it moved
the real database to `0007` at 12:04, minutes after the backup. A first `docker ps | head` had
shown only another project's containers.

## 5.2 Who gets a value

`inferred.targets`: a song of `spain` or `catalan` that no chart of the region scores, and
`worldwide` for a public song with no region at all. `infer` reads the signals of the targets whose
signals are missing or older than 25 days (free ids, then searches while the day's last), writes
`popularity.inferred(...)` with `inferred_on`, and removes the inferred values no longer wanted.
`refresh` reads every kept video again and works the values out again. The regional import deletes
only the rows of other bases, then replaces an inferred row when a chart now scores the song. The
catalogue takes a `worldwide` inferred value as the song's popularity (the lists sort by it); a
decade filter still works from chart weeks only.

## 5.3 The real run

`make popularity-collect` (6 s from the answers kept) and the 100 searched songs: 6,526 rows of
`song_signals` (6,269 with a video, 3,412 with streams). `make popularity-infer`: 57 targets (53
`catalan`, 4 with no region); 4 values written ("Agafant l'horitzó", Txarango, 64.6; "Fins que
arribi l'alba", Els Catarres, 63.1; "Tanca els ulls" 61.7; "Yo Sigo Iual" 61.3, all from
Enderrock), 53 waiting: the day's searches were spent. `make db-check`: no problem.

## 5.4 The page

The song page shows "Popularity in Catalan ≈ 64.6 of 100" with "Inferred from YouTube views: no
chart of the region lists it" on hover; a `Worldwide` entry is labelled "Popularity worldwide"
(screenshot [`03d-inferred-song`](screenshots/phase-17/03d-inferred-song.png)). The 13 checks of
the 09 guidelines: one fact changed, no new control, no sentence added (the hover), no internal
name on screen ("≈" and the hover), the 390 px check still passes.

# 6. The checks

| Check | Result |
|---|---|
| Backend, full run **on the CPU** (another project held 20 GB of the GPU) | 1,140 tests: 1,136 passed, 1 skipped (the real-model test), 3 failed: the known `test_the_worked_example_at_00_46_prints_three_equal_corcheas` and the two Transkun tests that fail only without a GPU. Phase 16: 1,130 |
| `test_signals.py` (new, 10) | The official rule, the kworb reader, the 30 days, the day's searches, a song's video and streams collected and stored (nothing asked twice), the import keeping an inferred value until a chart gives one, a song on no chart listed by its inferred worldwide value, the candidates measured on songs left out, `infer` and `refresh` (a video gone, a chart replacing the value), the formula against its fit |
| `test_regional_import.py`, `test_public.py`, `test_public_import.py`, `test_popularity.py`, `test_database.py` | pass |
| `black`, `flake8`, `mypy` on the changed backend modules; `tsc -b`, `npm run lint` | clean |
| `check:public` (2 new checks: a Catalan song with an inferred value, its page with "≈" and the hover) | 49 passed, twice, nothing left behind |
| `make db-check` on the real `.database/` | no problem |
| `scripts/docs/check-links.py` | passes |

# 7. Open points

- **53 songs wait for searches**: run `make popularity-infer` on the next days (100 searches a
  day); a song whose search finds no official video gets no value.
- **Spotify is closed for about 23 hours** after 694 searches; only the songs of those artists have
  streams. Wikidata's P1902 (an artist's Spotify id) would give the ids with no Spotify call.
- **`make popularity-refresh` must run within 30 days** (by 2026-11-13) and then monthly; nothing
  runs it by itself.
- **4 public songs have no region** (three from Los 40, one from Wikipedia: Phase 16 made them with
  no chart week); they are targets for `worldwide`.
- **The inferred values gather in the middle** (26 to 65): by design of a fitted line, and shown as
  "≈".

# 8. Learnings

- **Check for a running app with the whole list**: `docker ps | head` hid it, and a revision put
  into `src/` migrated the real database at once (the backup came first, by luck of order).
- **A `Retry-After` can be a day**: wait out a short one, stop on a long one, keep what was read.
- **Measure a signal by the error on songs left out against a plain guess**: the views looked
  strong on the scatter's top right and were 3 points better than the median.
- **Label channels upload the official videos of older songs**: an artist-only rule drops most of
  the 80s Spanish catalogue.
- **A design column that never varies in the sample is arbitrary in the fit**: check the
  coefficients before freezing them.
