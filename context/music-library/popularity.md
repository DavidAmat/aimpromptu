# Popularity

Popularity is a number from 0 to 100 that says how big a hit a song (or an album) was, worked out
from its chart history ([app context](../app/01-app-context.md), "Songs": Rankings and Popularity).
It sorts the Public Library's songs, an artist's songs and an artist's albums. The formula is plan
section 15.6; its weights were chosen in implementation 02, Phase 12, by objective criteria (Q-6,
[reconciliation.md](reconciliation.md) section 5); Phase 13 shows it on the pages.

## 1. What the app context asks

- Only good places count: a song at place 2,000 adds nothing; a song in the top of the chart for
  many weeks is near 100.
- Reaching a high place quickly is a good sign; holding places 10 to 30 for many weeks is a good
  sign too, close to (perhaps a little below) a song in the top 10 for one week.
- **It depends on the time range.** The default is all time; "the popularity in the 80s" counts
  only the weeks of the 80s, worked out on the request, fast enough for a filter.

## 2. The formula

For each chart week where the song is at place `r` of a chart of size `N` (100 today):

```
points(r) = ((N + 1 − r) / N) ^ 8          place 1 → 1.0, place 10 → 0.47, place 20 → 0.18, place 40 → 0.02
S         = sum of points over the weeks (each chart with its weight; 1.0 today)
peak      = ((N + 1 − best place) / N) ^ 3
P         = 100 × ( 0.6 × (1 − e^(−S / 10)) + 0.4 × peak )
```

A place outside the chart's size adds nothing. The plan's first formula had the power 2 for a
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
  With a decade chosen, the column is "Popularity in the 80s", and the list sorts by it.
- **A public song**: "83.3 of 100", all time, beside its chart line (best place, weeks, when).
- **An artist**: its songs and its albums by popularity; an artist's own popularity, in the list
  of artists, is its most popular song's.

## 5. Not yet

- A popularity per region: each region's charts give its own (plan section 15.6); there is one
  chart today, under `worldwide` (Q-5).
- A time range other than a decade (the last two years): the backend works it out
  (`popularity.song_scores(start, end)`); no page asks for it yet.

## Where to look deeper

- The code: `aitu-backend/src/aitu_backend/library/popularity.py` (the formula, `DEFAULT`, the
  criteria) and `catalogue.py` (the lists, the decade's popularity)
- The tuning on the real data: [reconciliation.md](reconciliation.md) section 5 and the
  [Phase 12 report](../implementations/02-private-web-app/02-implementation-phase-12.md) section 5
- The routes: [`endpoints.md`](../../documentation/services/backend/endpoints.md) §7.3
- The plan: [02-plan.md](../implementations/02-private-web-app/02-plan.md) section 15.6
