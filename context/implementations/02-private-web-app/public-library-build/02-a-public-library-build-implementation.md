# 02-a: How the public music library was built

This file is the context for Phase 12 and Phase 13 of
[`../02-plan.md`](../02-plan.md). Those phases reconcile this database with the app and then import
the public rows. Read this file before `library.sqlite`.

The plan of the download is [`02-a-public-library-build-plan.md`](02-a-public-library-build-plan.md).
The phase reports are `02-a-implementation-phase-1.md` through `02-a-implementation-phase-5.md` in
this folder. There is no response file. The brief asked for one. The plan and these reports took
its place.

The app does not read this database yet. Spain, Catalan, genre and tags are not in it.

# 1. Where the scripts are

Another agent was editing `/home/david/Documents/projects/music/aimpromptu`. A branch checkout in
that folder would have replaced those files. The download therefore uses a second folder, a git
worktree:

- Folder: `/home/david/Documents/projects/music/aimpromptu-public-library`
- Branch: `feat/02-a-public-library`

Do not checkout `feat/02-a-public-library` in the original folder. One branch can be checked out
in only one folder.

The scripts are `scripts/music-library/` on that branch. They use the Python standard library only
(`urllib`, `html.parser`, `sqlite3`). They do not add a dependency to the backend. Run them from
the worktree root.

The fixtures under `scripts/music-library/fixtures/` are small saved pages, committed, so
`python3 scripts/music-library/test_parse.py` needs no network.

# 2. Where the data is, and where it was moved

## 2.1 The first place

The brief asked for a folder `.music-library/` inside the repository, with `raw/` inside it, and
for that folder to stay out of git. Phase 1 did that. `/.music-library/` is still in `.gitignore`.

While the pages were downloading, each saved file was recorded in the manifest as a path relative
to the checkout, for example:

```
.music-library/raw/singles/bee-gees/stayin-alive.html
```

## 2.2 The move

On 2026-10-06 the folder was moved out of the repository. An editor opened on the project was
watching every HTML file. The new place is next to the checkout, not inside it.

On this machine the folder is:

```
/home/david/Documents/projects/music/data/music-library
```

That is `data/music-library` in the parent of the repository. Both checkouts
(`aimpromptu` and `aimpromptu-public-library`) have the same parent, so both see this folder.
`MUSIC_LIBRARY_DIR` can point somewhere else. When it is unset, the scripts use
`REPO.parent / "data" / "music-library"`.

The bytes were moved. The manifest text was not rewritten. A row still says
`.music-library/raw/...`, but the file is now `data/music-library/raw/...` with that
`.music-library/` prefix removed. Stayin' Alive is:

```
/home/david/Documents/projects/music/data/music-library/raw/singles/bee-gees/stayin-alive.html
```

`build_library.py` reads `data/music-library/raw/`. It does not open the path stored in the
manifest. That is why `library.sqlite` matches the moved files.

`_store_html` in `common.py` still writes under `checkout/.music-library/raw/`, and a later
download still looks there to decide if a page is already saved. That path does not exist after
the move. A new run of `download_charts.py` or `download_entities.py` would request the pages
again. Phase 12 and Phase 13 do not download. They read `library.sqlite`.

## 2.3 The files

```
/home/david/Documents/projects/music/data/music-library/
  raw/                  the HTML, in folders that follow the site
  manifest.sqlite       one row per URL, and the visit queue
  library.sqlite        the database Phase 12 reads
  phase2-download.log   the week-page log
  phase3-download.log   the song, artist and album log
  phase3-progress.txt   the last progress line of Phase 3
```

`library.sqlite` is about 50 MB. `manifest.sqlite` is about 13 MB. Neither file is the app
database `.database/`. Neither file is in git.

Week files sit under the year, so one folder does not hold every week. The path stored on a
ranking is still the site path, such as `/singles-chart/1978-02-11`.

`raw/` contains `decades/`, `singles-charts/`, `album-charts/`, `singles-chart/YYYY/`,
`album-chart/YYYY/`, `singles/`, `artists/` and `albums/`.

# 3. What was downloaded

The source is [musicchartsarchive.com](https://musicchartsarchive.com/). The client name is
`AImpromptuMusicLibrary/1.0 (personal local archive)`. Images, styles and scripts were not
requested. `/search/` and `/singles-chart/current` were not requested. Dated pages come from the
year lists.

Every manifest row is HTTP 200. The site did not answer 403, 429 or 503, so question Q-1 was not
raised.

| Kind | Pages | What it is |
|---|---|---|
| decade | 6 | `/1970s` through `/2020s` |
| year | 102 | 51 singles years and 51 album years |
| week | 5,231 | 2,615 singles weeks and 2,616 album weeks |
| song | 9,113 | one page per song path linked from the weeks, plus no extra songs |
| artist | 2,995 | 2,856 paths on the week pages, plus 139 artist links found on song and album pages |
| album | 8,341 | 7,834 paths on the album weeks, plus 507 album links found on song pages |

Charts start on 1976-09-04. There are no year pages before 1976. The pages were read in October
2026, so 2026 is a partial year.

9,104 of the 9,113 song pages have lyrics.

A song or an album is unique by its source path, not by its title. Two songs can share a title.
The source path is the value Phase 12 should keep as the external key, so a later import of the
same page updates the same public row.

# 4. How a page becomes a row

The parser is `html.parser` in `common.py`. An anchor is classified by its path prefix
(`/singles/`, `/albums/`, `/artists/`, `/singles-chart/`, `/album-chart/`). A full
`https://musicchartsarchive.com/...` URL becomes the path only. HTML entities are decoded
(`Stayin' Alive`, not `Stayin&#039; Alive`).

## 4.1 Who is created

Week pages create every song, album and artist they link. A saved song page then replaces the
title, the lyrics, the artist list and the album link. An album linked from a song page is created
even when that album is on no album chart. A saved album page replaces the title, the release
date, the artist list and the tracks. A saved artist page supplies the default name (the page
heading) and the year.

Artist pages are not a source of extra songs. See Also is not followed. A track that links to a
song which is not already in the database does not create that song and does not download it.

Only a link to `/artists/...` is an artist. Text beside a link is ignored. The credit line
(`Pitbull feat. Ne-Yo, AfroJack & Nayer`) is ignored. Give Me Everything keeps Pitbull and Ne-Yo,
in that order, because those are the two artist links. Afrojack and Nayer have no artist page on
that song, so they are not artists of it.

A link whose path is `/node/...` is not an artist. Seven songs and three albums have no artist
because of that. The artist was not invented. The songs are
`/singles/bebe-rexha/dirty-blonde`, `/singles/everlast/what-its-like`,
`/singles/frida/somethings-going-on`, `/singles/iann-dior/im-gone`,
`/singles/jason-isbell/the-nashville-sound`, `/singles/mystikal/unpredictable` and
`/singles/post-malone/twelve-carat-toothache`. The albums are `/albums/drake/7969-santa`,
`/albums/everlast/whitey-ford-sings-the-blues` and `/albums/prince/symbol`.

One song file is not under `singles/{artist}/`:
`/singles/earth-wind-and-fire-re-release`, title `September [re-release]`. It is stored. The path
is the identity.

## 4.2 Year

The year of a song is the year cell on an artist page, on the row that links to that song. It is
not the year of the first chart week. If two artist pages give two years, the earlier year is
stored and `import_note` records both.

The year of an album is the year of its release date. The stored release date is the date prefix
of the `content` attribute (`2020-07-24` from `2020-07-24T00:00:00-05:00`). If the album page has
no release date, the artist-page year is used, with the same earlier-year rule.

3 songs have no year, out of 9,113. Question Q-2 was not raised. Those years stay empty:

- `/singles/everlast/what-its-like`
- `/singles/lil-baby/forever2`
- `/singles/perry-como/home-for-the-holidays-1954`

157 albums have no year (1.9% of 8,341). The release date is missing and no artist page links the
album.

The decade is not a column. The views `song_decade` and `album_decade` calculate it from the year:
1978 is `70s`, 2004 is `00s`, 2017 is `10s`, 2024 is `20s`. A null year gives a null decade.

## 4.3 Rankings

The ranking used for popularity is the Chart History on the song or album page. That history
includes positions outside the weekly top 50. Stayin' Alive starts at position 65 on 1977-12-10
and is position 1 on 1978-02-11.

After the history is stored, each week page is compared:

- same position: nothing is added
- the week is missing from the history: the week-page position is inserted and `import_note` records it
- the positions differ: the history position stays and `import_note` records the week page

A date is one row in `chart_week`, shared by the singles chart and the albums chart. There are
2,616 dates. There are 2,615 singles week files and 2,616 album week files.

The printed peak and the printed week count are compared by `checks.py`. They are not columns.
No difference was found between the printed peak and the best stored position.

## 4.4 Tracks

A track list is read as lines. A line that does not start with a number is ignored. That drops
side labels (`Side one`) and notes (`Physical bonus track.`). `position` counts in reading order
across the whole album. `printed_number` is the number on the line, and it can restart after a
side label. `performed by` links on a track do not create artists and do not change the song.

Folklore has release date 2020-07-24, year 2020, and 17 tracks. Track 17 is The Lakes, with no
song. The bonus line is not a track.

## 4.5 import_note

48 rows. Three kinds:

| Kind | Rows | What was stored |
|---|---|---|
| Artist pages give two or more years | 19 | The earlier year |
| Chart History lists two positions for one date | 18 | The first position read |
| A week page position differs from Chart History | 11 | The history position |

# 5. How the download was made faster

`robots.txt` allows these pages and sets `Crawl-delay: 10`, which is 10 seconds between requests.
The first choice in the plan was one request at a time, then a wait of 10 seconds. A saved file
with HTTP 200 would be skipped, so a stopped run could continue.

At that pace, about 5,200 week pages take about 15 hours. After the week pages existed, the count
of song, artist and album paths on those pages was 19,803. At 10 seconds per page that second run
is 55.0 hours.

Three paces were considered.

| Pace | Gap between requests | What happened |
|---|---|---|
| `--workers 1` | 10 seconds | The first plan. Still available. It is the robots.txt reading, one request at a time |
| 10 workers, one shared timer | 1 second | Used for the week pages in Phase 2. The same 10 seconds are shared by the pool, so the requests do not all start together. This change was made while some week files were already saved |
| 30 workers, one shared timer | one third of a second | Used for the song, artist and album pages in Phase 3. The log says `30 workers, 0.333333s between requests`. The Phase 2 estimate at 10 workers was 5.5 hours for those pages |

A pool with no shared timer was not used. The workers would have sent their first requests at the
same moment. The code uses one timer (`_Gate` in `common.py`). A worker may send one request only
when that timer says the gap has passed.

The other way the run stays short is that a file already saved with HTTP 200 is not requested
again. `--refresh` is the only way to download it again. URLs wait as rows in `visit_queue`, in
the same `manifest.sqlite`. A row left `claimed` by a stopped process returns to `pending` when the next run starts.

If the site answers 403, 429 or 503, every worker waits and that URL is tried after 60 seconds,
then 120, then 240. If it still fails, the process stops and the saved files stay. The same
command continues. That stop did not happen.

Phase 3 also writes `phase3-progress.txt` about once a second, so the run can be watched without
the terminal. `download_entities.py --status` prints that file and the manifest counts.

# 6. The database Phase 12 reads

`build_library.py` creates the tables, deletes the previous rows, and fills them from `raw/`. A
second run writes the same rows. It does not add a second copy. The build of the full catalog took
about 69 seconds. The raw HTML stays, so a parser fix does not need a new download.

Running `build_library.py` also deletes `popularity`. After a rebuild, run `popularity.py` again.

## 6.1 Counts

Checked by `checks.py` on 2026-10-06, then the popularity rows were added on 2026-10-07.

| What | Count |
|---|---|
| artists | 2,995 |
| songs | 9,113 |
| albums | 8,341 |
| chart weeks (one row per date) | 2,616 |
| rankings | 290,798 |
| album tracks | 108,444 |
| songs with lyrics | 9,104 |
| songs with a year | 9,110 |
| songs with an album | 8,540 |
| albums with a release date | 6,382 |
| import_note | 48 |
| region | 1, code `worldwide` |
| popularity rows | 17,454 (every song and every album) |

Every song and every album has region `worldwide`. There is no genre column and no tag table.

The examples in the plan hold. Stayin' Alive is `/singles/bee-gees/stayin-alive`, year 1977, one
artist (Bee Gees), album Saturday Night Fever, a ranking at 1977-12-10 position 65, a ranking at
1978-02-11 position 1, lyrics not empty. Give Me Everything has artists Pitbull and Ne-Yo only, in
that order. Folklore is the track check in section 4.4.

## 6.2 Tables

Integer ids. The source path is unique.

| Table | What a row is |
|---|---|
| `region` | One row, `worldwide` |
| `artist` | `source_path`, such as `/artists/bee-gees` |
| `artist_name` | One name per artist, `is_default = 1`, the heading of the artist page. No second name was invented |
| `song` | `source_path`, `title`, `year`, `lyrics`, `album_id`, `region_id` |
| `song_artist` | `song_id`, `artist_id`, `position`. Position 1 is the main artist |
| `album` | `source_path`, `title`, `release_date`, `year`, `region_id` |
| `album_artist` | Same shape as `song_artist`. These are the album artist links, not the `performed by` links |
| `album_track` | `album_id`, `position`, `printed_number`, `title`, `song_id`. `song_id` is empty when that song is not in the database |
| `chart` | Two rows, `singles` and `albums` |
| `chart_week` | One row per date, `YYYY-MM-DD` |
| `ranking` | `chart_id`, `chart_week_id`, `position`, and exactly one of `song_id` and `album_id` |
| `popularity` | `entity_kind` (`song` or `album`), `entity_id`, `region_id`, `score`. The score is the all-weeks value for `worldwide` |
| `import_note` | A difference recorded during the build. It does not change the stored value |

Indexes: `ranking(song_id, chart_week_id)`, `ranking(album_id, chart_week_id)`, `song(title)`,
`artist_name(name)`.

The app tables in plan section 8.6 are not these names. Phase 12 writes the mapping. The identity
to preserve is the source path. The app already has `external_key` on public artists, albums and
songs for that import. A song in this database points at an artist. The app's `song_artists` points
at an artist name. This import has one default name per artist, so that name is the one to use.

Fields this database has that section 8.6 does not yet place: the lyrics, the album chart history,
the album popularity, and the album tracks. Phase 12 decides where they go. Fields section 8.6 has
that this database does not give: genre, tags, and the regions `spain` and `catalan`.

# 7. Popularity

The formula is the app plan's section 15.6, copied into `popularity.py`. It was not tuned. N is
100. A position worse than 100 adds nothing to the score. The week count still includes that week.
The best position is the lowest position number. The score is rounded to one decimal place.

A song uses the singles rankings. An album uses the album rankings.

```
points(r) = ((N + 1 - r) / N) ^ 2
S         = sum of points over the weeks in the time range
peak      = ((N + 1 - best rank) / N) ^ 3
P         = 100 * (0.6 * (1 - exp(-S / 10)) + 0.4 * peak)
```

The unit examples still match: 30 weeks at number 1 is 97.0, 10 weeks is 77.9, one week is 45.7.

`python3 scripts/music-library/popularity.py` replaces every `popularity` row with the all-weeks
score. A second run wrote the same 17,454 rows. The sum of the scores is 835,444.6. The region is
`worldwide`.

A time range is `--from YYYY-MM-DD --to YYYY-MM-DD`. Both ends are included. The scores are
printed and are not stored. A filter by decade in the app has to calculate the score again from
the rankings. The stored column is only the all-weeks score.

| Print | Score | Best position | Week count | Stored |
|---|---|---|---|---|
| Stayin' Alive, all weeks | 90.2 | 1 | 27 | yes, 90.2 |
| Folklore, all weeks | 100.0 | 1 | 307 | yes, 100.0 |
| Stayin' Alive, 1977-01-01 to 1979-12-31 | 90.2 | 1 | 27 | no |

The 1977-1979 score matches the all-weeks score because every ranking week of Stayin' Alive is
already inside 1977-12-10 to 1978-06-10 (27 weeks, four of them at position 1). A window of only
1978 excludes the four weeks of December 1977 and prints 89.0, best position 1, week count 23. That
window is not stored.

Folklore's unrounded score is 99.999970, which rounds to 100.0. Eight of its 307 weeks are position
1. The formula approaches 100 when the history is long and the best position is 1. Two songs and
44 albums are stored as 100.0. The weights stay with the app plan's question Q-6.

6 songs are stored as 0.0 because they have no ranking. 309 albums are stored as 0.0. 291 of those
have no album ranking (an album linked from a song page can exist with no album chart). 18 have one
to three weeks at position 96 to 100, and one decimal place of that score is 0.0.

# 8. What Phase 12 and Phase 13 use

Phase 12 reads `library.sqlite` at the path in section 2. It does not write into
`data/music-library/` and it does not run the download. The mapping, the gaps and the identity rule
go in `context/music-library/reconciliation.md`, as the app plan already says.

Phase 13 imports the reconciled public rows into `.database/`. The running app then does not read
`data/music-library/`. The import can run again. The source path is what keeps a song, an artist
or an album the same row.

Commands, from the worktree root, if the database has to be built again from the HTML that is
already on disk:

```bash
python3 scripts/music-library/test_parse.py
python3 scripts/music-library/build_library.py
python3 scripts/music-library/checks.py
python3 scripts/music-library/popularity.py
```

`test_parse.py` does not use the network. After Phase 5 it is 21 tests, all passing.
