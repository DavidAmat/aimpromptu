# Popularity

Popularity is a number from 0 to 100 that says how big a hit a song (or an album) was, worked out
from its chart history ([app context](../app/01-app-context.md), "Songs": Rankings and Popularity).
It sorts the Public Library's songs, an artist's songs and an artist's albums. The formula is plan
section 15.6; its weights were chosen in implementation 02, Phase 12, by objective criteria (Q-6,
[reconciliation.md](reconciliation.md) section 5); Phase 13 shows it on the pages. **A popularity
is relative to its region** (Phase 16): a song has one for `worldwide` (the US chart) and one for
each of `spain` and `catalan` it was on ([regional-sources.md](regional-sources.md)). A song no
chart of a region lists gets a popularity **inferred** from its official video's YouTube views
(Phase 17, section 6), always shown as approximate.

## 1. What the app context asks

- Only good places count: a song at place 2,000 adds nothing; a song in the top of the chart for
  many weeks is near 100.
- Reaching a high place quickly is a good sign; holding places 10 to 30 for many weeks is a good
  sign too, close to (perhaps a little below) a song in the top 10 for one week.
- **It depends on the time range.** The default is all time; "the popularity in the 80s" counts
  only the weeks of the 80s, worked out on the request, fast enough for a filter.

## 2. The formula

For each chart week where the song is at place `r` of a chart that lists `N` places:

```
points(r) = ((101 − r) / 100) ^ 8          place 1 → 1.0, place 10 → 0.47, place 20 → 0.18, place 40 → 0.02
S         = sum of points over the weeks (each chart with its weight)
peak      = ((101 − best place) / 100) ^ 3
P         = 100 × ( 0.6 × (1 − e^(−S / 10)) + 0.4 × peak )
```

A place outside the chart's `N` adds nothing. **Every place is scored against 100** (Phase 16), so
place 10 is worth the same in the Spanish top 20 of 2005 and in its top 100 of 2016: scored against
its own size, a top 10 song of 2002 to 2008 had a median of 11, one of the top 100 years 50; against
100, 43 and 50. The US chart is a top 100, so none of its scores moved. The plan's first formula had the power 2 for a
week's points; on the real chart history that made the top flat (218 songs at 95 or more) and a
place 20 for 20 weeks worth more than number 1 for one week. The user chose objective criteria over
a hand ranking (2026-10-16), and the power 8 meets them all:

| Example | Score |
|---|---|
| Number 1 for 30 weeks | 97.0 |
| Number 1 for 10 weeks | 77.9 |
| Number 1 for 1 week | 45.7 |
| Place 20 for 20 weeks | 39.8 |
| Place 80 for 3 weeks | 0.4 |
| Songs at 95 or more, of 9,107 | 44 |

`make popularity-check` measures the criteria again on the downloaded history (it writes nothing).

## 3. Where it is worked out

| When | What | How long |
|---|---|---|
| The import (`make public-import`) | `songs.popularity` and `albums.popularity` of every public row, all time | Part of the 2.5 s import |
| `make popularity-infer` (Phase 17) | `song_region_popularity` (`inferred`) of every song with no chart value in a region, from `song_signals` | Seconds, plus the signals it reads |
| The regional import (`make regional-import`, Phase 16) | `song_region_popularity` of every song of `spain` and `catalan`, all time; the weights of the number-ones lists | Part of the 5 s import |
| A list filtered by a decade | Every song's popularity from that decade's weeks only (1980-01-01 to 1989-12-31) | About 65 ms the first time, then kept with the list until a public row changes |
| One song's page | The stored all-time value | Nothing to work out |

The decade of a song comes from its **year**, and its popularity in that decade from the **chart
weeks** inside it. A song of 1979 that charted into 1980 is listed in the 70s, scored on its 1979
weeks. A private song has no popularity: a user's own library has no chart.

Recent hits stay on the chart much longer (a 2020s hit runs 60 to 112 weeks, an 80s hit about 25),
so they lead the all-time order, as in Billboard's own all-time ranking ("Blinding Lights" first). A
decade filter compares songs of the same years.

## 4. How the pages show it

- **Public songs**: a column, with one decimal (the biggest hits differ in the decimal: 99.8, 99.7).
  With a decade chosen, the column is "Popularity in the 80s"; with a region, "Popularity in
  Spain"; with both, "Popularity in Spain in the 80s" (on two lines). The list sorts by it.
- **A public song**: "83.3 of 100", all time ("Popularity worldwide" when it has a regional one too),
  one fact per region ("Popularity in Spain", "≈ 96.5 of 100" when it rests on number ones only, on
  an estimate or on YouTube views (section 6), with why on hover), and **On the charts**: each chart named with its region, its
  line, best place, weeks ("Weeks at number 1" for a list of number ones), when.
- **An artist**: its songs and its albums by popularity; an artist's own popularity, in the list
  of artists, is its most popular song's.

## 5. Per region (Phase 16)

A region's popularity is the **largest** of its charts' scores, not their sum: the charts of one
region overlap (the sales chart and Los 40 name the same hits). It is stored in
`song_region_popularity` with what it rests on, and `songs.popularity` stays the worldwide one.

| Rests on | When | How |
|---|---|---|
| `weeks` | A chart with places: the Spanish sales chart (2002 on), Los 40 (2004 on), the weekly top 10 of 1982 to 1996, the two APECAT top 30 (2018 on) | The formula above. A monthly list counts each month as 3 weeks: 4 (the weeks it covers) made 2.4 % of the Catalan songs score 95 or more |
| `number_ones` | A list of number ones only: the sales list 1959 to 2001, Los 40 1966 to 2003 | Each week at number 1 counts with its chart's weight, fitted where the full lists exist so a number one scored from its weeks at the top alone comes closest to its full score (3.00 and 7.90), then lowered together by 0.60 so that at most 1 % of `spain`'s songs score 95 or more: 1.80 and 4.74. The pages show "≈" |
| `estimated` | A song only Spotify Spain's weekly chart lists (kworb.net's totals: weeks, top 10 weeks, peak) | Its weeks spread over the places its totals allow, with one factor (1.15) fitted on the 4,057 songs that are also on the sales chart (mean error 7.0 points). A chart value always wins over it |

The Q-6 criteria on the Spanish sales chart alone: 47 of 6,539 songs at 95 or more, the order
follows the weeks at number 1 (0.63). The all-time `spain` order starts with number ones of the 60s
and 70s, which held the top three or four weeks; a decade filter compares songs of the same years.

With a region chosen, the Public songs list sorts by that region's popularity; with a region and a
decade, by its charts' weeks of that decade, worked out on the request
(`popularity.song_scores(start, end, region=...)`).

## 6. Inferred from YouTube views (Phase 17)

A song no chart of a region lists (a Catalan song with no place on the APECAT lists, a song a
request adds) has no chart value there. Its official video's views are a signal every song has, so
a relation fitted on the songs that have both gives it an approximate one.

**The signals** (`song_signals`, one row per public song, `make popularity-collect`): the official
video, its views and upload date, and the song's all-time Spotify streams where kworb.net lists
its artist (Q-10: the Spotify API gives no play count; it only finds the artist's Spotify id). The
video id comes free first: Los 40's links, Wikidata (YouTube video id P1651), Enderrock's yearly
top 100 of Catalan videos; else a YouTube search, 100 a day. Only an official upload counts: the
artist's channel, its "Topic" or Vevo channel, or a record label's channel when the title names the
artist and the song. Every answer is kept in `data/music-library-views/answers.sqlite` beside the
repository; **a view count is never kept more than 30 days** (the YouTube API Developer Policies):
`make popularity-refresh` reads them again (1 unit of the 10,000 a day per 50 videos), monthly.

**The relation** (`popularity.INFERRED`, chosen by the user on 2026-10-19 from the measures of
the [Phase 17 report](../implementations/02-private-web-app/02-implementation-phase-17.md)): a line
on the log of the views per year online, with a term per region, per decade of the song, per kind
of channel, the years between the song and the upload, and the log of the streams. On songs left
out of the fit it is **21 points from the chart value on average** (a guess of the region's median:
24), and keeps the charts' order only loosely (a rank correlation of 0.43). The values gather in the
middle (26 to 65 for nine songs in ten, where chart values run from 6 to 89): an inferred song is
never shown as a huge hit or as a flop.

| Rule | How |
|---|---|
| Who gets one | A song of `spain` or `catalan` that no chart of the region scores; `worldwide` for a song on no chart at all |
| A chart wins | The regional import replaces an inferred value when a chart lists the song; `make popularity-infer` removes one no longer wanted |
| Shown | "≈ 64.6 of 100", "Inferred from YouTube views: no chart of the region lists it" on hover; the lists sort by it; a decade filter does not use it (no weeks) |
| No video | No value (the song stays at 0) until a search finds one, another day |

## 7. Not yet

- A time range other than a decade (the last two years): the backend works it out
  (`popularity.song_scores(start, end)`); no page asks for it yet.
- An artist's popularity is its most popular song's worldwide one: a Spanish-only artist is at 0 in
  the artists list.
- An inferred value in a decade filter: it has no weeks, so "Popularity in the 10s" leaves it at 0.

## Where to look deeper

- The code: `aitu-backend/src/aitu_backend/library/popularity.py` (the formula, `DEFAULT`, the
  criteria, `INFERRED`), `catalogue.py` (the lists, the decade's popularity), `regional_import.py`
  (the regions: the weights, the month, the estimate), `signals.py` and `inferred.py` (Phase 17:
  the videos and streams, the fit, the inferred values)
- The fit's plots: [`research/phase-17/`](../implementations/02-private-web-app/research/phase-17/)
- The regions' sources and their gaps: [regional-sources.md](regional-sources.md)
- The tuning on the real data: [reconciliation.md](reconciliation.md) section 5 and the
  [Phase 12 report](../implementations/02-private-web-app/02-implementation-phase-12.md) section 5
- The routes: [`endpoints.md`](../../documentation/services/backend/endpoints.md) §7.3
- The plan: [02-plan.md](../implementations/02-private-web-app/02-plan.md) section 15.6
