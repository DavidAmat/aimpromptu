# The music library data, reconciled

The Public Library starts from data built by a parallel piece of work: the chart history, songs,
artists, albums and lyrics of `musicchartsarchive.com`, in `library.sqlite`
([how it was built](../implementations/02-private-web-app/public-library-build/02-a-public-library-build-implementation.md)).
That database has its own tables. The app has the tables of plan section 8.6
([07-database.md](../07-database.md)). This page says how one becomes the other: the mapping, what
each side lacks, how a row keeps its identity across runs, and what the import does. Written in
implementation 02, Phase 12; the import into the real `.database/` is Phase 13.

## 1. The two databases

| | `library.sqlite` (the download) | `.database/aitu.sqlite` (the app) |
|---|---|---|
| Where | `data/music-library/` beside the repository; never written by the app | `.database/` (`AITU_DATABASE_DIR`) |
| Ids | Integers of one build; the **source path** (`/singles/bee-gees/stayin-alive`) is the identity | Integers of the app; `external_key` holds the source's identity |
| Rows | 2,995 artists, 9,113 songs, 8,341 albums, 290,798 chart weeks | Public rows (`scope = 'public'`, no owner) beside each user's private rows |

**The chart is one country's chart.** The site's weekly singles chart matches the US Hot 100 (the
week of 1978-01-07, for example, is the Hot 100 of that week). This is an inference from the data;
the site does not name its chart. The download calls its region `worldwide`, and the app keeps that
code, because `worldwide` is the app's default region; the chart's row is named after the site, so
a later chart of another country is a second row beside it (section 6).

## 2. The mapping

Each table of the download, the app table it goes to, and what is not kept.

| Download | App | How |
|---|---|---|
| `artist` (`source_path`) | `artists` | `external_key` = `musicchartsarchive.com` + the path; `scope = 'public'` |
| `artist_name` (one per artist, `is_default = 1`) | `artist_names` | The one name, as the default. No other name is invented; more names come by request (Phase 14) |
| `song` (`title`, `year`, `album_id`, `region_id`) | `songs` (`title`, `year`), `song_albums`, `song_regions` | The year as given (the decade is worked out from it, never stored). A re-entry joins its song (section 4.3) |
| `song.lyrics` | `song_lyrics` (**new**) | The text as given; 9,038 songs after the joins |
| `song_artist` (`position`) | `song_artists` | Through the artist's default name, as the app context asks (a song points at an artist **name**). Position 1 of the source is position 0 of the app |
| `album` (`title`, `release_date`, `year`) | `albums` (`title`, `year`, `release_date` **new**) | |
| `album_artist` | `album_artists` (**new**) | Through the default name, as for a song |
| `album_track` with a song | `song_albums` (`track_number`) | The track's place in the album's reading order |
| `album_track` with no song | not kept | 99,934 track lines name a song that is not in the download. The Public Library is a library of songs; a title with no song row has no page to open |
| `song.album_id` | `song_albums` | The album of the song's page, with no track number when its track list does not name the song |
| `region` (`worldwide`) | `regions`, `song_regions` | Every imported song gets `worldwide`, the region of its chart |
| `chart` (`singles`, `albums`) | `chart_sources` | Two rows: `musicchartsarchive.com singles` and `… albums`, region `worldwide`, size 100, weight 1.0 |
| `chart_week` + `ranking` of songs | `chart_entries` (`week`, `rank`) | One row per song and week; the date table is not needed, the week is a date |
| `ranking` of albums | `album_chart_entries` (**new**) | The same, for albums |
| `popularity` | `songs.popularity`, `albums.popularity` (**new**) | Not copied: worked out again by the app's formula from the chart weeks, so a tuned formula applies (section 5) |
| `import_note` (48 rows) | not kept | A record of the build (which year or position was kept when two pages disagreed); it changes no value. It stays in the download |
| `song_decade`, `album_decade` (views) | not kept | The app works the decade out from the year |
| `album_track.printed_number`, `title` | not kept | The number printed on the line restarts after a side label; the reading order is kept instead |

## 3. The gaps

**What the download gives and section 8.6 had no place for.** Revision `0003` adds only these
(the import needs each one, and nothing else changes):

| Added | Why |
|---|---|
| `song_lyrics` (`song_id`, `text`) | The words of 9,104 songs. The Lyrics tab of the sheet toolbox (plan section 11.5) can start from them. A table of its own, so a list of songs does not read 16 MB of words |
| `album_artists` | An album has artists of its own, which are not always the artists of each of its songs (8,510 links in the download) |
| `album_chart_entries` | The album chart history (129,988 weeks): the popularity of an album, to sort an artist's albums |
| `albums.release_date`, `albums.popularity` | 6,382 albums have a release date; every album gets a popularity |

**What section 8.6 has and the download does not give.**

| Missing | Count | What happens |
|---|---|---|
| Genre | every song | Empty. A source is Q-5 (section 6) |
| Tags (films, video games, TV shows, adverts) | every song | Empty. The app context says the values come by request (Phase 14) |
| Regions `spain` and `catalan` | every song | Not created yet. Q-5 |
| A year | 3 songs, 157 albums | Empty; the decade is then empty too. Nothing is invented |
| An artist | 7 songs, 3 albums | No artist: the source credited a page that is not an artist page. Fixed by request |
| Any chart week | 6 songs, 291 albums | Popularity 0.0 |
| 8 songs of the seed list | section 7 | Added from the seed list, title and artist only |

**The lyrics are copyrighted text.** Keeping them is fine for this personal app on the home
network, as the YouTube download is. A production version must not publish them (app context:
features that are not legal stay out of production).

## 4. Identity

### 4.1 The rule

A downloaded row is found by its **`external_key`**: the site's name, then its source path, as in
`musicchartsarchive.com/singles/bee-gees/stayin-alive`. The path is the download's own identity: two
songs may share a title ("Heaven" of Bryan Adams and of Avicii), never a path. The site's name in
front keeps the keys of a second source apart. Only public rows have a key; a private row pulled
from the Public Library (Phase 13) points at the public row through `public_id` instead.

**Artist names.** The site writes each artist one way: no two of its 2,995 artists have the same
name once case, punctuation, "the" and "&" are ignored. So each artist arrives with one name, and
names written several ways ("The Jackson 5", "Jackson Five") come later, by request.

### 4.2 Running it again

The import can run again on a newer download. It never undoes what a person changed in the app
(Phase 14 lets the master user correct titles, names and credits):

- a row with a known key is not made again;
- a row the run makes gets everything the source gives (its fields and its links);
- a row that exists only gets the fields that are still empty: a year, a release date, the lyrics.
  A title, a name, an artist or an album link is never written again;
- the chart history belongs to the source, so the weeks of its two charts are written again every
  run, and every popularity is worked out again from them.

Checked on the real download: a second run makes 0 rows and changes no count (section 8).

### 4.3 A song that charted again is one song

134 songs of the download are a song charting again: "Billie Jean [re-release]" (2009),
"All I Want For Christmas Is You [seasonal]", "25 Or 6 To 4 [re-recorded version]". The app
context asks that the same song not appear twice, and a piano version is made of a song, not of one
of its chart runs. So:

- **66 have their first run in the download** (same title without the bracket, same first artist):
  they join that song, which gets their chart weeks (no week is shared) and keeps its own key, title,
  year and artists;
- **68 first charted before 1976**, where the download starts ("White Christmas"): each keeps its
  row, with the bracket taken out of the title.

The rule is applied again on each run, so the joined songs stay joined with no stored list. It
reads only songs, and only the three re-entry words: the brackets of three album titles are part
of their name ("The Beatles [White Album]").

## 5. Popularity

The formula of plan section 15.6 is `aitu_backend/library/popularity.py`, with every weight a
parameter. Run on the download, it gives the parallel work's stored score to the decimal for all
8,341 albums and for the 8,981 songs that were not joined (the 66 joined songs have more weeks, so a
higher score). A time range is applied to the weeks before the sum: the popularity of every song
for the 80s takes 46 ms, for all weeks 212 ms (2,179 and 9,041 songs), so a filter by decade can
work it out on each request.

**What the real data showed about the plan's weights:**

- **The top is flat.** 218 songs score 95 or more, and 2 songs and 44 albums score 100.0. A sort
  by popularity cannot tell the biggest hits apart.
- **A long run counts as much as many weeks at number 1.** "Lose Control" (Teddy Swims: 1 week at
  number 1, 112 weeks on the chart) scores 100.0; "Last Night" (16 weeks at number 1) 99.7.
- **Held between 10 and 30.** Place 20 for 20 weeks scores 65, number 1 for one week 46; the app
  context puts the first one close to, perhaps a little below, the second.

**The weights the app uses (Q-6).** The plan asked to tune the weights on a list the user ranks by
hand. The user chose objective criteria instead (2026-10-16). The criteria come from the app
context, and each is measured on the chart history (`make popularity-check`):

| Criterion | Plan's weights | App's weights |
|---|---|---|
| Number 1 for 30 weeks near 100, clearly above 10 weeks | 97.0 and 77.9 | 97.0 and 77.9 |
| Place 20 for 20 weeks close to, at most, number 1 for one week (45.7) | 65.1 | 39.8 |
| Place 80 for 3 weeks near 0 | 1.2 | 0.4 |
| At most 1 % of the songs at 95 or more | 218 of 9,107 | 44 |
| Among the songs that reached number 1, the score follows the weeks at number 1 (Spearman, 1 = same order) | 0.48 | 0.58 |
| Billboard's all-time Hot 100 top 10 (November 2021; the 8 in the download), places with the weeks up to then | 1, 8, 5, 28, 4, 14, 24, 3 | 1, 8, 4, 17, 15, 22, 23, 3 |

The app's weights differ from the plan's in **one number**: the power of a week's points is 8, not
2. Place 1 is still worth 1.0 a week; place 10 is worth 0.47 (was 0.83), place 20 0.18 (was 0.66),
place 40 0.02. Both sets place Billboard's own all-time top 10 near the top, so the order of the
biggest hits agrees with the chart's owner; only the app's weights meet the app context's examples
and leave the top spread.

**What stays.** Recent hits stay on the chart much longer (a 2020s hit runs 60 to 112 weeks, one of
the 80s about 25), so they lead the all-time order: Billboard's ranking does the same ("Blinding
Lights" is its first). A popularity inside a time range (a decade filter) compares songs of the
same years.

## 6. What is still open (Q-5)

- **Q-5**: the genres, and the tags. Genres could come from Wikidata, mapped to the 13 genres of
  the app.
- **The regions** (the region part of Q-5, then Q-9) are Phase 16: five Spanish and Catalan sources,
  imported by the same identity rule, each source keeping its own key in `song_keys`
  ([regional-sources.md](regional-sources.md)). 1,104 songs of the Spanish sales chart are songs
  of the US chart; the seed songs not on the US chart got the `spain` region and a year where a
  Spanish list has them ("Superestrella").
- **Q-6** is answered: the app's weights, by the criteria of section 5.

The options and the recommendations are in the
[Phase 12 report](../implementations/02-private-web-app/02-implementation-phase-12.md).

## 7. The seed list

The 31 songs of the starting library (`scripts/seed/youtube-library/library.json`) are checked
every run, by title and artist with case, punctuation and a leading "the" ignored, and a closing
`(…)` allowed ("Stronger" is "Stronger (What Doesn't Kill You)"). Two pieces need a hand rule: ELO
is "Electric Light Orchestra" on the chart, and "99 Red Balloons" charted in the US as "99
Luftballons". A piece with no artist takes the most popular song of that title.

**23 are found. 8 are not on the chart**, because they were hits in Europe and not in the US:
"1973", "Stay the Night" and "Bonfire Heart" (James Blunt), "Grace Kelly" (Mika), "Moonlight
Shadow" (Mike Oldfield), "2002" (Anne-Marie), "Superestrella" (Aitana) and "Club Can't Handle Me"
(the list gives David Guetta). The import adds each with the title and artist of the list and
nothing else: no year, no region, popularity 0.0, key `seed:<title>|<artist>`. Three artists are
new (Mika, Mike Oldfield, Aitana).

## 8. The import

`aitu_backend/library/public_import.py` (`make public-import`), run on the host because the
download is not inside the containers:

```bash
make public-import                                    # the real .database/ (Phase 13)
make public-import ARGS="--database /path/to/a/copy"  # a copy of .database/, to try it
```

It reads the download read only (`mode=ro&immutable=1`), writes in one transaction, and prints what
it made, what was already there, and the seed list. On an empty database and on a copy of the real
one (32 private songs, untouched): 2,995 artists, 8,341 albums, 9,047 songs and 8 from the seed
list, 9,038 lyrics, 160,810 song weeks and 129,988 album weeks, in about 2.5 s. A second run: 0
rows made, the same counts.

**Run on the real `.database/` on 2026-10-16** (Phase 13, after `make db-backup`): the same counts in
2.7 s; a second run made 0 rows; `make db-check` reports no problem. The Public Library pages read
these rows ([ontology.md](ontology.md)).

## Where to look deeper

- The tables: [`paths-and-data.md`](../../documentation/services/backend/paths-and-data.md) section 6
- The download: [`public-library-build/`](../implementations/02-private-web-app/public-library-build/)
- The plan: [02-plan.md](../implementations/02-private-web-app/02-plan.md) sections 8.6, 15.3, 15.5 and 15.6
- The Private Library, the other scope of the same tables: [private-library.md](private-library.md)
- The code: `aitu-backend/src/aitu_backend/library/public_import.py`, `popularity.py`;
  `db/migrations/versions/0003_public_library_fields.py`; the tests
  `test_public_import.py`, `test_popularity.py`
