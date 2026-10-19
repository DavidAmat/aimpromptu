# The sources of the `spain` and `catalan` regions

The app context asks for regions "from very local music to very worldwide music": `worldwide`,
`spain` and `catalan`, where a song counts in a region when it was popular there, whatever the
artist's country ("Dragostea Din Tei" in Spain). The Public Library has one chart today, the US
one, under `worldwide` ([reconciliation.md](reconciliation.md)). This page says which charts and
lists exist for Spain and for Catalonia from the 60s to today, what each gives, on what terms, and
which to download first. Written in implementation 02, Phase 16, from a research on the internet
on 2026-10-18; the full report, with a source for every fact, is
[`phase-16-spanish-and-catalan-charts.md`](../implementations/02-private-web-app/research/phase-16-spanish-and-catalan-charts.md).
The choice of sources is Q-9, answered on 2026-10-18 with the recommendation of section 6; section 7
says what was downloaded and imported.

## 1. What the research found

**Spain has a full weekly chart only from the week of 2001-12-30.** It is the official chart of
PROMUSICAE (the Spanish record industry): a top 20 until 2008, a top 50 from 2009, a top 100 that
counts streaming from 2015. Los 40 Principales, the radio list, gives all 40 places from
2004-01-03, and only the number one of each week from July 1966. Before 2002 the only complete
signal is the weekly number one (1959 to 2001), with two partial sets of deeper places: a weekly
top 10 for 1982 to 1996 (Spanish Wikipedia, with no source given) and top 20 scans for 1960 to 1965.
The 70s, and 1997 to 2001, have nothing below the number one as data.

**Catalonia has one measured chart, from September 2018.** APECAT (the Catalan record producers)
publishes a monthly top 30 of the songs in Catalan most played on 16 radios of Catalonia, counted
by BMAT, and a second top 30 of songs in any language from Catalan labels. Before 2018 there are
awards (from 1979 and 1994), one listener poll (1986), Enderrock's yearly top 100 of Catalan
videos on YouTube (from 2017) and a Viquipèdia table of the Catalan songs most played on Spotify.
No source measures "popular in Catalonia, in any language" with a history, so in practice
`catalan` is a region of songs in Catalan.

**No chart source has an open licence.** PROMUSICAE's sites allow "strictly private" use; Los 40
allows "personal and private" viewing and reserves text and data mining. This app runs only on the
home network and publishes nothing, which is what those words allow; it is a reading of the terms,
not legal advice. Wikipedia (CC BY-SA), Wikidata and MusicBrainz (CC0) are the only open ones.

## 2. The sources

| Source | Region | Years | What it gives | Size | Terms | Format | Pace |
|---|---|---|---|---|---|---|---|
| spanishcharts.com (Hung Medien), weekly singles | `spain` | 2001-12-30 to now | Weekly places; a page per song with all its weeks | 20 / 50 (2009) / 100 (2015) | "© PROMUSICAE & AGEDI"; robots allows | HTML, about 1,290 pages | 5 s, about 2 h |
| El Portal de Música (PROMUSICAE) | `spain` | 2009 week 34 to now; year-end 2009 to 2025 | Weekly places, peak, weeks; a top 50 of radios | 50 / 100 | Strictly private use allowed | HTML, about 900 pages | 5 to 10 s |
| promusicae.es PDFs | `spain` | 2004 to now | Weekly places; year-end 2004 to 2025 | 20 / 50 / 100 | Strictly private use allowed | About 1,300 PDFs with a text layer | 5 to 10 s |
| los40.com Lista 40 | `spain` | Number ones 1966-07-16 to 2003; full lists 2004 to now | Weekly places; a YouTube link and an Apple Music id on each row | 40 | Personal and private viewing only; text and data mining reserved | HTML, 61 year pages and about 1,190 weeks | 10 s, about 3.5 h |
| kworb.net, Spotify Spain | `spain` | 2013-04-28 to now | Per song: weeks, weeks in the top 10, peak, streams | Top 200 | Robots allows | One page | 1 request |
| English Wikipedia, number ones of Spain | `spain` | 1959 to now | The weekly number one (from Salaverri's book until about 1995) | 1 | CC BY-SA | About 68 pages | One at a time |
| Spanish Wikipedia, weekly top 10 | `spain` | 1982 to 1996 | Weekly places, no source given | 10 | CC BY-SA | 15 pages | One at a time |
| Discomanía (a blog) | `spain` | Number ones 1960 to 2016; top 20 PDFs mainly 1960 to 1965 | Number ones with their source; about 280 top 20s | 1 / 20 | No licence stated | One page and 404 PDFs | 5 s |
| APECAT / BMAT top 30, songs in Catalan | `catalan` | 2018-09 to now; year-end 2019, 2021 to 2025 | Monthly places | 30 | No licence; robots allows | 99 PDFs with a text layer | 2 to 3 s, minutes |
| APECAT / BMAT top 30, Catalan labels | `catalan` | The same | The same, songs in any language | 30 | The same | 99 PDFs | The same |
| Enderrock (magazine) | `catalan` | 2017, 2019 to 2024 | Yearly top 100 of Catalan videos on YouTube, with views; Spotify lists | 100 | CC BY-NC-ND | HTML articles | 2 to 3 s |
| Viquipèdia, Spotify top 100 | `catalan` | A snapshot of 2024-12; songs from 1974 | The 100 Catalan songs most played on Spotify | 100 | CC BY-SA | One page | 1 request |
| Viquipèdia, awards | `catalan` | 1979 to now | Winners only (Disc Català de l'Any, Premis Enderrock, Cerverí) | 1 to 3 a year | CC BY-SA | A few pages | One at a time |

Not downloadable, kept as hand work for later: the book *Sólo éxitos: año a año 1959-2002* by
Fernando Salaverri (each song's peak and weeks, year by year), Billboard's "Hits of the World" Spain
top 10 of the 70s (scans), the scans of the full Los 40 lists of 1981 to 1984, Ràdio Flaixbac's
weekly list (on air since about 1994, no archive found), Spotify's Spain and Barcelona charts (they
need a login, and Spotify forbids scraping).

## 3. The gaps per decade

| Decade | `spain`: best signal | `spain`: missing | `catalan`: best signal | `catalan`: missing |
|---|---|---|---|---|
| 60s | Number ones from 1959; top 20s 1960 to 1965; Los 40 number ones from 1966 | Places 1966 to 1969 | Catalan songs on the Spanish charts ("Cançó de matinada", number 1 in 1967) | Any Catalan list |
| 70s | Number ones (sales and Los 40) | Everything below number 1 | The same; Disc Català de l'Any from 1979 (albums) | Any ranked list |
| 80s | Weekly top 10 from 1982 (no source given); number ones | 1980 and 1981 places | The 1986 listener poll | Nine of ten years |
| 90s | Weekly top 10 to 1996; number ones | 1997 to 1999: number ones only | Awards from 1994 | Any ranked list |
| 00s | Weekly top 20 from 2002; Los 40 full lists from 2004 | 2000 and 2001: number ones only | Awards | Any ranked list |
| 10s | Weekly top 50 then top 100; Los 40; Spotify from 2013 | Nothing that matters | APECAT from 2018-09; Enderrock YouTube lists | 2010 to mid-2018 |
| 20s | Weekly top 100; Los 40; Spotify | Nothing that matters | APECAT monthly; Enderrock and Spotify yearly lists | Nothing that matters |

**What it means for popularity.** For `spain` most songs from 2002 get a popularity from weekly
places, as the US songs do. Before 2002 a song has its weeks at number 1 or nothing. For `catalan`
the chart gives a popularity only from 2018; for the four decades before, the inferred popularity
of Phase 17 (from YouTube views) is the main signal, and Enderrock's YouTube lists with their views
are a natural sample to fit it.

## 4. The formula needs two changes (Story 16.3)

Two observations of the research, to be checked on the real data as Q-6 was:

- **A chart's size changes the score of the same place.** With the power 8 of
  [popularity.md](popularity.md), place 10 of a top 20 is worth 0.008 a week and place 10 of a top
  100 0.47. Scoring every chart against a size of 100, with its real place, keeps place 10 at 0.47
  in every year; a smaller chart then only lacks the places it does not list, which are worth
  little (place 51 and below under 0.005 a week). The US chart is a top 100, so its scores do not
  move.
- **A source with no weekly places needs a stand-in**: a monthly list counts each month as about 4
  weeks; a list of number ones only counts each week at number 1 as the points a number 1 of the
  same chart earns on average in the years with full lists (2002 to now); a source of peaks and
  weeks only (kworb) gets points fitted on the songs that have both.

A region's popularity is the **largest** of its sources' scores, not their sum, because the sources
overlap (PROMUSICAE counts Spotify; Los 40 copied the sales list from 1967 to 1971). Each score keeps
its source, so a number from number ones only is never shown as a measured one.

## 5. Matching a song of a list to a public song

Lists give a title and an artist. The identity rule of Phase 12 (titles and names compared without
case or accents, an `external_key` per source) is the start. The open catalogues help less than
hoped for these songs:

- **MusicBrainz** finds the right recording for every song tried, at 1 request a second, but
  returns several copies of one song and rarely links a Spanish or Catalan recording to YouTube or
  Spotify.
- **Wikidata** has few of these songs: 3,744 songs in Spanish, 103 in Catalan (11 with a YouTube
  video id).
- **Los 40** gives a YouTube link on each row from 2004: the best free source of official videos
  for Phase 17.

## 6. The recommendation (Q-9)

Download first, in this order, about 2,800 requests, 6 to 8 hours, paced and resumable, into
`data/music-library-regions/<source>/` next to the repository:

1. spanishcharts.com, the weekly chart 2002 to now (El Portal and the PROMUSICAE PDFs if it blocks
   the script);
2. los40.com, the number ones from 1966 and the full lists from 2004;
3. kworb.net, the Spotify Spain page;
4. the 198 APECAT PDFs;
5. Wikipedia: the number ones of 1959 to 2001, the weekly top 10s of 1982 to 1996, the Viquipèdia
   Spotify table.

Later, if wanted: the top 20 PDFs of 1960 to 1965, the PROMUSICAE year-end lists, Enderrock's lists.
Hand work (the book, the scans) stays out.

## 7. What was built (2026-10-19)

**The download** (`make regional-download SOURCE=<source>`, `scripts/music-library-regions/`,
standard library only) saved every page once into `data/music-library-regions/<source>/raw/`, with
a `manifest.sqlite` of what it asked for, so a stopped run continues. It sent
`AImpromptuMusicLibrary/1.0 (personal local archive)` and stops on a refusal or a challenge page;
none came.

| Source | Pages | Time | What it read |
|---|---|---|---|
| spanishcharts.com | 1,293 weeks (2 dates answer HTTP 500) | 1 h 49 min at 5 s | 6,766 songs; top 20 to 2008, 50 to 2014, 100 from 2015 |
| los40.com | 61 year pages and 1,190 weeks | 3 h 29 min at 10 s | 4,042 songs: 1,942 number ones 1966 to 2003, 40 places from 2004 (each row with a YouTube id) |
| kworb.net | 1 page | 1 s | 7,459 songs with their Spotify totals and track ids |
| APECAT | 198 PDFs | 13 min at 3 s | 183 monthly lists of 30 in two series; 3 PDFs are images with no text, 2 repeat an earlier list |
| Wikipedia | 61 pages | 3 min at 3 s | 2,241 weekly number ones 1959 to 2001, 752 weekly top 10s 1982 to 1996, the 100 Catalan songs most played on Spotify |

**The build** (`make regional-build`) reads the saved pages again into one database per source
(`<source>/<source>.sqlite`: charts, songs, entries, totals), so a reader fix needs no download.

**The import** (`make regional-import`, `aitu_backend/library/regional_import.py`) writes the public
rows by the identity rule of Phase 12: a song is the public song with its key, else the one of the
same compared title that credits one of its artists, else a new song with its artists found by name
or made. Into the real `.database/` on 2026-10-19, after `make db-backup`, in 5 s: 12,014 songs and
4,034 artists made (21,069 public songs in all); 3,406 times a source's song was a song of the US
chart or the seed list; `spain` 12,870 songs, `catalan` 960; 158,709 chart weeks. A second run made nothing. Popularity per region:
[popularity.md](popularity.md) section 5.

Left as they are, for later: an artist written two ways becomes two artists ("Aitana", "Aitana
Ocaña"); merging is a request (Phase 14). The 100 songs of the Catalan Spotify table have the
region and no popularity (no places), like the Catalan songs before 2018: Phase 17 infers one from
YouTube views ([popularity.md](popularity.md) section 6).

## Where to look deeper

- The full research, with its sources:
  [`research/phase-16-spanish-and-catalan-charts.md`](../implementations/02-private-web-app/research/phase-16-spanish-and-catalan-charts.md)
- The formula today: [popularity.md](popularity.md)
- The identity rule and the US chart: [reconciliation.md](reconciliation.md)
- The plan: [02-plan.md](../implementations/02-private-web-app/02-plan.md) section 20, Phase 16
- The build of Phase 16, step by step: [02-implementation-phase-16.md](../implementations/02-private-web-app/02-implementation-phase-16.md)
- The code: `scripts/music-library-regions/` (`download.py`, `parse.py`, `build.py`, `test_parse.py`);
  `aitu-backend/src/aitu_backend/library/regional_import.py`, `tests/test_regional_import.py`
