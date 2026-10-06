# 02-a: The public music library from Music Charts Archive

Read the brief first: [`02-a-public-library-build-prompt.md`](02-a-public-library-build-prompt.md).
The app this data will serve later is [`../../../app/01-app-context.md`](../../../app/01-app-context.md),
section Music Library and the song metadata list. The status lookup is
[`02-a-public-library-build-checklist.md`](02-a-public-library-build-checklist.md).

Phase reports go in this folder as `02-a-implementation-phase-N.md`. The agent that finishes phase N
writes that report, following
[`../../../language/communication-implementation-plans.md`](../../../language/communication-implementation-plans.md)
and [`../../../language/communication-style.md`](../../../language/communication-style.md).

This work downloads the charts and builds a local relational database. It does not connect to the
app. Another agent is building the app from [`../02-plan.md`](../02-plan.md). The two must not edit
the same files (section 4).

The pages cited in section 2 were read on 2026-10-05, while this plan was written.

---

# 1. Context

## 1.1 What this work is for

The Public Library needs real songs, real artists and real albums, with rankings, so that a later
import can fill the app. The source for the worldwide region is
[musicchartsarchive.com](https://musicchartsarchive.com/).

The site is a set of weekly charts. A decade page lists the years. A year page lists the chart
dates. A date page lists the ranking of that week. A song page, an artist page and an album page
then add the metadata that is not on the week page.

The result of this work is files on disk and one SQLite database (a single relational file). The
app does not read them yet. Spain and Catalan music are not in this source, and this work does not
add them.

## 1.2 What the site contains

These are observed facts, not guesses.

- The menu has six decade pages: `/1970s`, `/1980s`, `/1990s`, `/2000s`, `/2010s`, `/2020s`.
- Charts start on 1976-09-04. The site says so, and the 1976 year page has 17 dates, from
  1976-09-04 to 1976-12-25. A full year such as 1978 has 52 dates. The 2026 singles year page,
  read on 2026-10-05, has 40 dates, the last one 2026-10-03.
- Each decade page links two year lists: `/singles-charts/YYYY` and `/album-charts/YYYY`.
- A singles week is `/singles-chart/YYYY-MM-DD`. An album week is `/album-chart/YYYY-MM-DD`.
  The same date is used by both charts when both exist. They are not always identical: on
  2026-10-05 the 2026 album year page had 41 dates and the singles year page had 40.
- A week page is a table of 50 rows (`cols-50`). Columns: position, the song or album link, the
  artist link, an empty cell. Example: `/singles-chart/1978-02-11`, row 1, Stayin' Alive, Bee Gees.
- A song page such as `/singles/bee-gees/stayin-alive` has the title, an Album link, the Lyrics,
  one or more Artist links, and a Chart History of date plus position. That history includes
  positions outside the weekly top 50. Stayin' Alive starts at position 65 on 1977-12-10 and later
  reaches 1. The page also prints a peak and a week count. Those two numbers can be calculated
  from the history, so they are not stored (section 3.4).
- An artist page such as `/artists/bee-gees` has the artist name as the page heading, a table of
  albums (link, peak, year) and a table of singles (link, peak, year). Some rows have no link.
  Bee Gees has a See Also list of other artist pages (Barry Gibb, Robin Gibb). That list is other
  artists, not other names of the Bee Gees.
- An album page such as `/albums/taylor-swift/folklore` has the title, artist links, a Release
  Date (`2020-07-24` on Folklore), a Track List, and a Chart History in the same shape as a song.
  Saturday Night Fever (`/albums/soundtrack/saturday-night-fever`) has no Release Date. Its album
  artist link is `/artists/soundtrack`.
- Lyrics are on the song page, in the Lyrics field. They are present for Stayin' Alive and for
  Give Me Everything.
- `robots.txt` allows these pages and sets `Crawl-delay: 10` (10 seconds between requests). It
  disallows `/search/` and the site admin paths. This work does not use search.

## 1.3 How a page is written

The parser has to accept the HTML as it is, including the uneven parts below.

- A singles row uses a relative link: `/singles/bee-gees/stayin-alive`. An album row uses a full
  URL: `https://musicchartsarchive.com/albums/soundtrack/saturday-night-fever`. Both become the
  path only, starting with `/`.
- The artist cell is sometimes broken HTML. On 1978-02-11, position 33 is a link to
  `/artists/art-garfunkel` followed by the text `with James Taylor & Paul Simon` and a spare
  closing tag. Only the real link is an artist. The same pattern appears on the current chart
  (`Tame Impala` is a link, `JENNIE` is text).
- One link can contain several names. On the current chart, one link to `/artists/karol-g` has
  the text `Karol G, Judeline & rusowsky`. The artist is the path. The name is the heading of the
  artist page, not the text of that link.
- Give Me Everything (`/singles/pitbull/give-me-everything`) shows the text
  `Pitbull feat. Ne-Yo, AfroJack & Nayer`, but the Artist field links only `/artists/pitbull` and
  `/artists/ne-yo`. Afrojack and Nayer have no artist link on that page, so they are not artists
  of this song.
- A track list mixes numbered lines, side labels and notes. Folklore has `1.` through `17.`, then
  the line `Physical bonus track.`, then `17. "The Lakes"` with no song link. Saturday Night Fever
  restarts the numbers under `Side one`, `Side two` and `Side three`, and some lines say
  `performed by` with an artist link.
- `/singles-chart/current` is the latest week under a fixed path. The canonical URL is still
  `/singles-chart/current`. This work downloads dated pages from the year lists, not `current`.

---

# 2. Terminology

Words from the brief and from the app context. New words are defined once.

- **Music Library**: songs, artists, albums and their metadata. This work builds the worldwide
  part of the future Public Library, as files, not inside the app.
- **Song**, **artist**, **album**: the three entities. A song may have no album. A song may have
  several artists.
- **Artist name**: the app allows several names for one artist, with one default name. This source
  gives one name per artist page, and that name is the default. No second name is invented.
- **Rankings**: the pairs of chart date and position, for a song or for an album.
- **Popularity**: a number from 0 to 100, calculated from the rankings, for a chosen time range.
  The default range is all the weeks. The formula is the one already written in
  [`../02-plan.md`](../02-plan.md) section 15.6 (section 8 of this plan). This work does not tune it.
- **Region**: where a song was popular. Every row from this site is `worldwide`, because the brief
  says so. This is not a claim that the chart is a world chart. The chart is the one this site
  publishes, and the library labels it worldwide.
- **Year** and **decade**: the year is a value the site prints. The decade (70s, 80s, 00s, 10s, 20s)
  is calculated from the year. The site's decade pages (`/1970s`) are only a way to find the years.
- **Lyrics**: the text in the Lyrics field of the song page.
- **Chart week**: one date, such as `1978-02-11`. Singles and albums share the date when both have
  that week. The date is stored once.
- **Source path**: the path of the page, such as `/singles/bee-gees/stayin-alive`. This is the
  identity of the entity. The title is not the identity. The app context uses Heaven by Bryan Adams
  and Heaven by Avicii as two songs. The same rule applies here.

**Not the app's project.** A project in the app is a piano sheet. This work does not create
projects, versions, users or requests.

---

# 3. What is kept

The rule from the brief: if the site does not have a field, do not invent it. The fields below are
the ones the app context asks for and the site actually has, plus the lyrics, the album tracks and
the album rankings, which the brief asks for.

## 3.1 Song

| Field | Where it is on the site | Rule |
|---|---|---|
| Title | The page heading | Not the text of a chart cell |
| Source path | `/singles/{artist}/{song}` | Unique |
| Artists | Links in the Artist field, in that order | The first link is the main artist. Text that is not a link is ignored |
| Album | The Album link | Empty when the field is absent |
| Lyrics | The Lyrics field | Line breaks kept. Empty when the field is absent |
| Year | The year cell on an artist page, on the singles row that links to this song | Empty when no such row exists. Not the year of the first chart week |
| Decade | Calculated from the year | Not stored as its own column |
| Region | The brief | Always `worldwide` |
| Rankings | The Chart History on the song page | Section 7.4 |
| Popularity | Calculated | Section 8 |

Genre and tags are not on these pages. They are not columns.

## 3.2 Artist

| Field | Where it is on the site | Rule |
|---|---|---|
| Source path | `/artists/{slug}` | Unique |
| Default name | The page heading | One row in the artist name table |

See Also is not stored. A name written beside a link, with no page of its own, is not an artist.

## 3.3 Album

| Field | Where it is on the site | Rule |
|---|---|---|
| Title | The page heading | |
| Source path | `/albums/{slug}/{album}` | Unique. The first slug may be an artist or `soundtrack` |
| Artists | Links in the album artist field only | Not the `performed by` links inside the track list |
| Release date | The Release Date field, the `content` value of the date | Empty when the field is absent, as on Saturday Night Fever |
| Year | The year of that release date | If there is no release date, the year cell on an artist page, on the album row that links to this album. Empty if neither exists |
| Tracks | Numbered lines of the Track List | Section 7.5 |
| Region | The brief | Always `worldwide` |
| Rankings | The Chart History on the album page | Same rule as songs |
| Popularity | Calculated | Same formula as songs |

## 3.4 What is not kept

- Images, including the chart picture and the artist picture.
- The peak and the week count printed on the page. The check compares them with the calculated
  values and records a difference. It does not store them.
- The credit line (`Pitbull feat. Ne-Yo, AfroJack & Nayer`) and any name that is not a link.
- See Also.
- Side labels (`Side one`) and notes that are not numbered (`Physical bonus track.`).
- Genre, tags, films, and any region other than worldwide.
- The text `performed by` on a track. The artists of a song are the Artist links on the song page.

---

# 4. Boundaries

Another agent is implementing [`../02-plan.md`](../02-plan.md) in this same folder. A branch checkout here would replace the files that agent is editing, so this work does not checkout a branch in this folder.

Phase 1 creates a git worktree: a second folder, with its own branch, linked to this repository. All script edits and commits of this work happen in that folder. The other agent keeps this folder and its own branch, and does not need to know about the worktree. The library branch is never checked out here, because one branch can be checked out in only one folder.

This work writes only:

- `scripts/music-library/`
- `.music-library/` (gitignored, section 5)
- one block in the root `.gitignore`
- the phase reports in this folder

It does not edit the app, the root `Makefile`, `aitu-backend/`, `aitu-frontend/`, `.database/`, or
the other plan and its checklist. The other checklist already names this folder as the worldwide
download for its question Q-5. Spain, Catalan, genre and tags stay with that question.

The scripts use the Python standard library only (`urllib`, `html.parser`, `sqlite3`). They do not
add a dependency to the backend.

---

# 5. Decisions

## 5.1 Decided in this plan

Each row can be changed by the user before the phase that uses it. The recommended choice is the
one written here.

| # | Choice | Why |
|---|---|---|
| D-1 | Wait 10 seconds between requests. One request at a time. A later run skips files already saved with status 200 | `robots.txt` asks for 10 seconds. About 5,200 week pages then take about 15 hours. Song, artist and album pages are a second, longer run. The real counts are measured in Phase 2, before that second run starts |
| D-2 | Save the HTML under `data/music-library/raw/` next to the repository, in folders that follow the site, with week files split by year | The brief asks for text files and for a hierarchy like the site, so one folder does not hold every week. HTML is kept so a later parse does not download again. The folder is outside the repository so an editor opened on the project does not watch the files (changed 2026-10-06; it was `.music-library/` inside the repository) |
| D-3 | The relational database is `data/music-library/library.sqlite`. The download log is `data/music-library/manifest.sqlite`. Neither file is the app database | The brief asks for a relational database and for no integration with the app. SQLite is one file, and it is the same kind of database the app plan chose for `.database/`. `MUSIC_LIBRARY_DIR` can point somewhere else |
| D-4 | A song or an album is unique by its source path, not by its title | The app context: two songs may share a title and stay two songs |
| D-5 | The ranking stored for popularity is the Chart History on the song or album page. A week page fills a missing week only, and only for a position the week page actually shows | The history includes positions such as 65, which the top-50 week page cannot show. Where both exist, they are compared |
| D-6 | The chart size N in the popularity formula is 100 | The history reaches at least position 98. The week page shows 50 rows, but the formula in the app plan uses the top 100. A position worse than 100 adds nothing |
| D-7 | The entities are the ones linked from the week pages, plus the album linked from those songs, plus the artist links on those song and album pages | The brief collects the rankings first, and then the pages of those songs and artists. Artist pages are read for the name and the year. Their other songs are not added. See Also is not followed. A track link to a song that never appears in the rankings does not create a song |
| D-8 | Decade is a view, calculated from the year. Popularity for all weeks is stored and can be rebuilt. Popularity for another time range is calculated when asked, and is not stored for every range | The app context says a filter by decade must recalculate popularity for that range. The rankings are small enough for SQLite to do that from an index |

## 5.2 To decide during the work

| # | Question | When |
|---|---|---|
| Q-1 | The site answers 403, 429 or 503, or the delay is not enough | The download phase stops, writes the last URL, and asks. The recommended next step is a longer delay, then the same command, which skips pages already saved |
| Q-2 | Many songs have no year on any artist page | They stay empty. Using the year of the first chart week would be a guess. Raise it only if the empty count is large |

---

# 6. Folders and files

```
scripts/music-library/
  README.md
  common.py              paths, the delay, the HTTP client, the HTML helpers
  download_charts.py     decade pages, year pages, week pages
  download_entities.py   song, artist and album pages
  build_library.py       raw HTML -> library.sqlite
  popularity.py          the formula, all-weeks scores, a time range
  checks.py              the comparisons of section 9
  fixtures/              a few saved pages, committed, used by the tests
  test_parse.py          parser tests, no network

data/music-library/             next to the repository, not in git
  raw/
    decades/1970s.html
    singles-charts/1978.html
    album-charts/1978.html
    singles-chart/1978/1978-02-11.html
    album-chart/1978/1978-02-11.html
    singles/bee-gees/stayin-alive.html
    artists/bee-gees.html
    albums/taylor-swift/folklore.html
    albums/soundtrack/saturday-night-fever.html
  manifest.sqlite
  library.sqlite
```

Week files sit under the year so `singles-chart/` is not one flat folder of thousands of files.
The path stored in the database is still the site path, `/singles-chart/1978-02-11`.

The download lives in `data/music-library/` beside the repository (the parent of the checkout), or in `MUSIC_LIBRARY_DIR` when that is set. On this machine that is `/home/david/Documents/projects/music/data/music-library`. It is not inside the repository, so it is not committed. `/.music-library/` stays in `.gitignore` so an old folder there is still ignored. The fixtures stay in git. They are small and the
tests need them with no network.

---

# 7. Download and database

## 7.1 Download

One process. Ten seconds after each response, including a failure. Identify the client as
`AImpromptuMusicLibrary/1.0 (personal local archive)`.

Do not download images, styles or scripts. Do not request `/search/` or `/singles-chart/current`.

A saved file with HTTP 200 is skipped. `--refresh` downloads it again. On 403, 429 or 503, retry
that URL three times with a longer wait (60 seconds, then 120, then 240). If it still fails, stop
the process and leave the manifest as it is. The next command continues with the missing URLs.

The manifest has one row per URL: the URL, the kind (`decade`, `year`, `week`, `song`, `artist`,
`album`), the source path, the file path, the HTTP status, the time, and the error text if any.

Phase 2 discovers the week URLs from the year pages. Phase 3 discovers song, artist and album URLs
from the week pages, then reads the saved song and album HTML for the extra album and artist links
of D-7. It does not need the database for that list. A small extract from the HTML is enough, and
it uses the same parser as the build.

## 7.2 Tables

Integer ids. The source path is unique. Names are stored as the site writes them, after decoding
HTML entities (`Stayin' Alive`, not `Stayin&#039; Alive`).

```
region
  id, code UNIQUE          -- one row: worldwide

artist
  id, source_path UNIQUE

artist_name
  id, artist_id, name, is_default
  -- this import writes one row per artist, is_default = 1

song
  id, source_path UNIQUE, title, year NULL, lyrics NULL,
  album_id NULL, region_id

song_artist
  song_id, artist_id, position     -- 1 is the main artist
  PRIMARY KEY (song_id, artist_id)

album
  id, source_path UNIQUE, title, release_date NULL, year NULL, region_id

album_artist
  album_id, artist_id, position
  PRIMARY KEY (album_id, artist_id)

album_track
  album_id, position, printed_number, title, song_id NULL
  PRIMARY KEY (album_id, position)
  -- position is 1..n in reading order
  -- printed_number is the number on that line, and may restart after a side label

chart
  id, kind UNIQUE          -- singles, albums

chart_week
  id, chart_date UNIQUE    -- YYYY-MM-DD, stored once

ranking
  id, chart_id, chart_week_id, position, song_id NULL, album_id NULL
  -- exactly one of song_id and album_id
  UNIQUE (chart_id, chart_week_id, song_id) where song_id is set
  UNIQUE (chart_id, chart_week_id, album_id) where album_id is set

popularity
  entity_kind, entity_id, region_id, score
  PRIMARY KEY (entity_kind, entity_id, region_id)
  -- entity_kind is song or album
  -- score is the all-weeks value, rebuilt by popularity.py

import_note
  id, entity_kind, source_path, message
```

Indexes: `ranking(song_id, chart_week_id)`, `ranking(album_id, chart_week_id)`, `song(title)`,
`artist_name(name)`.

A view `song_decade` returns the decade label from `song.year`: 1978 gives `70s`, 2004 gives
`00s`, 2017 gives `10s`, 2024 gives `20s`. A null year gives a null decade. The same view exists
for albums (`album_decade`).

`build_library.py` creates the tables, deletes the previous rows, and fills them from `raw/`.
The raw files stay. Running the build twice gives the same rows.

## 7.3 Who is created

From the week pages:

- every `/singles/...` link becomes a song, even if the song page later fails
- every `/albums/...` link becomes an album
- every `/artists/...` link becomes an artist

From a saved song page, if the page downloaded:

- the title, the lyrics and the album link replace the week-page title
- Artist links that were not on the week page are added (Ne-Yo on Give Me Everything)
- the album link is created even when that album is on no album chart

From a saved album page:

- the title, the release date and the album artist links
- the tracks (section 7.5)

From a saved artist page:

- the heading becomes the default artist name
- a year is copied onto a song or an album only when the row links to a song or an album that
  already exists

If two artist pages give two years for the same song, the earlier year is stored and an
`import_note` records both.

A song page that was not downloaded still keeps the title and the artists from the week page, with
empty lyrics and an empty year.

## 7.4 Rankings

For each saved song page, each Chart History row becomes a singles ranking: the date link
(`/singles-chart/YYYY-MM-DD`) and the position. Album history uses `/album-chart/YYYY-MM-DD` and
the albums chart.

After that, each week page is compared:

- the song or album is on the week page and in the history at the same position: nothing to add
- it is on the week page and missing from the history: insert the week-page position and write an
  `import_note`
- the positions differ: keep the history position and write an `import_note`

The date is inserted into `chart_week` once, the first time any ranking uses it.

## 7.5 Tracks

Read the Track List as lines. A line that does not start with a number is ignored. That drops
`Side one` and `Physical bonus track.`

For each numbered line, in reading order:

- `position` increases by one across the whole album
- `printed_number` is the number written on the line
- if the title is a link to `/singles/...` and that song exists, `song_id` is set and the title is
  the link text (`Exile`, not the following `featuring Bon Iver`)
- if the title is a link to a song that is not in the database, `song_id` stays empty and the title
  is still stored. The song is not downloaded
- if there is no song link (`The Lakes`), store the title and leave `song_id` empty

`performed by` links on a track do not create artists and do not change the song.

## 7.6 Parser

Use `html.parser`. Classify an anchor by its path prefix (`/singles/`, `/albums/`, `/artists/`,
`/singles-chart/`, `/album-chart/`), after converting a full URL to a path.

The tests in Phase 1 use fixtures that include:

- the Stayin' Alive song page (history starts at 65, album link, lyrics)
- the Give Me Everything artist field (two links)
- the 1978-02-11 row for Art Garfunkel (one artist link, extra names in the text)
- the Folklore track list (the bonus line ignored, The Lakes without a song, Exile without a
  featuring artist)
- one Saturday Night Fever track section (numbers restart, `performed by` is not an album artist)
- one album chart row with a full `https://` album URL

---

# 8. Popularity

The formula is copied from the app plan, section 15.6. It is not tuned here. The weights live in
one place in `popularity.py`.

For a song, use the singles rankings. For an album, use the album rankings. N is 100 (D-6). A week
with position `r` worse than N adds nothing.

```
points(r) = ((N + 1 - r) / N) ^ 2
S         = sum of points over the weeks in the time range
peak      = ((N + 1 - best rank) / N) ^ 3
P         = 100 * (0.6 * (1 - exp(-S / 10)) + 0.4 * peak)
```

`P` is rounded to one decimal place in the table. The default time range is every week. That score
is written into `popularity` for `worldwide`. The command can be run again and replaces those rows.

A time range is an argument, `--from YYYY-MM-DD --to YYYY-MM-DD`. It prints the scores. It does not
write a row per range. An index on the rankings makes that query fast at the size of this catalog
(the week count is a few thousand, and each song has a short history).

The same function is unit-tested with invented weeks, against the examples already calculated in
the app plan: 30 weeks at number 1 is about 97, 10 weeks at number 1 is about 78, one week at
number 1 is about 46. Those tests do not need the download.

---

# 9. Checks

`checks.py` reads `library.sqlite` and prints a short report. It does not change rows, except that
the build already wrote `import_note`. The report includes:

- counts of artists, songs, albums, weeks, rankings, songs with lyrics, songs with a year, songs
  with an album, albums with a release date
- Stayin' Alive: source path, year 1977, one artist (Bee Gees), album Saturday Night Fever, a
  ranking at 1977-12-10 position 65, a ranking at 1978-02-11 position 1, lyrics not empty
- Give Me Everything: artists Pitbull and Ne-Yo only, in that order
- Folklore: release date 2020-07-24, year 2020, 17 tracks, track 17 title The Lakes with no song,
  no track whose title is the bonus note
- region is worldwide on every song and album
- no genre column and no tag table (the schema check)
- the count of `import_note` rows, and the first differences between a printed peak and the best
  stored position, as a sample, not as a failure of the build

Phase 1 runs `test_parse.py` and the popularity unit tests. Those pass before any long download.

---

# 10. Phases

One phase is one agent session, except Phase 2 and Phase 3, which may run for many hours. Those
two commands are safe to stop and to start again. The phase is finished only when the manifest
has a status 200 for every URL of that phase, or when Q-1 stops the work.

Do not mark a download phase finished because the script was started.

## Phase 1: The scripts, the fixtures and the schema

Create the worktree of section 4 first, then work only in that folder. Create `scripts/music-library/`, the gitignore block, and the fixtures by downloading the few pages
named in section 7.6 (the delay still applies; this is a few minutes). Implement the parser, the
empty schema and the popularity unit tests. `test_parse.py` passes with no network after the
fixtures exist. No full chart download.

## Phase 2: The week pages

Download the six decade pages, every year page, and every dated week page for singles and albums.
Then print the real counts: weeks per chart, unique song paths, unique artist paths, unique album
paths, and the hours Phase 3 will need at 10 seconds per page. This count is the one later reports
use. The estimate before the download is about 2,600 weeks for each chart.

## Phase 3: The song, artist and album pages

Download the entities of D-7. Print how many pages were saved, how many song pages have lyrics, and
how many extra album and artist links were found beyond the week pages.

## Phase 4: The database

Run `build_library.py`. Run `checks.py`. The examples in section 9 hold. Differences are written
to `import_note` and to the phase report. Fix the parser if an example fails because the HTML was
misread. Do not invent a missing year or a missing artist.

## Phase 5: Popularity

Run `popularity.py` for all weeks. Confirm the unit examples still match. Print Stayin' Alive and
Folklore with their all-weeks score, their best position, and their week count, so the scores can
be read against the chart history. A second print uses `--from 1977-01-01 --to 1979-12-31` for
Stayin' Alive, to show that a time range changes the score. Document the command in the script
README.

---

# 11. What could go wrong

| Risk | What is done about it |
|---|---|
| The site blocks the download | D-1 and Q-1. Saved files are kept. The command continues later |
| A page changes its HTML | The raw HTML remains. The parser is fixed and the build is run again, with no new download |
| Two songs share a title | D-4. The path is the id |
| A featured name has no artist page | It is not an artist. Give Me Everything is the test |
| The history and a week page disagree | The history is kept. `import_note` records the week page value |
| Lyrics are long | They are text in SQLite. They stay inside `.music-library/` and are not committed |
| This work and the app agent edit the same file | Section 4. A separate worktree and branch. The only shared edit, at merge time, is the gitignore block |
| The popularity weights feel wrong later | They are the app plan's weights, in one function. Tuning stays with that plan's Q-6 |

---

# 12. How it is checked

- Phase 1: `python3 scripts/music-library/test_parse.py` from the repository root. No network.
- Phase 2 and Phase 3: the manifest counts, and a spot check that one saved file opens as the
  expected page (Stayin' Alive, Folklore, one week page).
- Phase 4 and Phase 5: `checks.py` and the popularity prints of section 9 and Phase 5.
- There is no app screen in this work. The check is the database and the printed report.

---

# 13. Not in this work

| Thing | Why |
|---|---|
| Import into the app, or any edit of `.database/` | The brief says there is no integration yet |
| Spain, Catalan, genre, tags | This site does not provide them. The app plan's Q-5 still owns those |
| A second name for one artist | The site gives one heading per artist page |
| Tuning the popularity weights | The app plan's Q-6 |
| Images | The brief asks for the text |
| The response file named in the brief | This plan is the document the next agent reads. A phase report records what the download found |
