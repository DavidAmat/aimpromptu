# 02: Phase 18 report: Genres and tags from Wikidata

Plan: [`02-plan.md`](02-plan.md) sections 3.3 (Q-5, Q-11), 15.3 and 20, Phase 18. Checklist:
[`02-checklist.md`](02-checklist.md). Branch `feat/phase-18`, made from `master` at `d200126`.
Started 2026-10-19 on the Ubuntu machine; the app was running (`make up`, the backend reloads on
`src/` changes), so nothing that migrates went into `src/`.

**State: the measure is done (Story 18.1); Q-11 is raised and waits for the user.** No genre or tag
row has been written. The full list of the Wikidata genres found, with their counts and the
proposed map, is [`research/phase-18/genres-measure.json`](research/phase-18/genres-measure.json).

# 1. Summary

| Story | Result |
|---|---|
| 18.1.1 The read | `library/genres.py` (`make genres-measure`): every Wikidata song, single or musical work with a performer (229,348 items, 119,000 with genres of their own), each performer's labels and genres, each genre's "subclass of" links up to the roots, the links to films, TV programmes, video games and adverts. 72 queries to QLever, every answer kept in `data/music-library-genres/answers.sqlite` (120 MB). Matched by the identity rule: 6,242 public songs (8,297 items); 2,016 public artists through a matched item, 2,003 more by a name only one performer has |
| 18.1.2 The counts | 24 % of the public songs have genres of their own, 32 % more through their performer, 19 % more by the weaker name match; 25 % none (section 4). 514 Wikidata genres reach the public songs. Tags: 119 songs in 88 films, 24 in 20 TV programmes, 1 in a video game, 0 in adverts (section 6) |
| 18.1.3 Q-11 | Raised with the proposed map (section 5) and three questions (section 8) |
| `song_keys` | The item's key (`wikidata.org:Q…`) is kept by the import, not by the measure: the measure writes no row (plan step 1). `Index.find` already looks a key up first, so a second run finds the song by it |

# 2. Where the data comes from

**The Wikidata query service refused.** At 15:05 UTC it answered 429 to every query: "Aggressively
rate-limiting to 1 req / min - this rule was created during active wdqs outage". At that rate the
measure (about 70 queries) would take more than an hour, and the larger queries time out there
anyway (Phase 17: a filter on the item's address timed out).

**QLever** (`https://qlever.dev/api/wikidata`, University of Freiburg) is a public SPARQL endpoint
over the same Wikidata data. The largest query of the measure (229,348 items with their performers
and genres) answers in 1.8 s, 30 MB as TSV. Its limits, found on the way:

- **30 s per query**: a `UNION` of labels and other names (`skos:altLabel`) over all songs timed
  out, and so did any join of the songs with `?w wdt:P31/wdt:P279* wd:Q11424` (is a film). The
  module asks the two kinds of names separately, and reads the films, TV programmes, games and
  adverts once as sets (442,732 films, 385,433 TV programmes, 189,308 games) to classify the links
  on this machine;
- **too many requests**: after 59 queries one second apart it answered 429 for several minutes.
  `PACE["qlever.dev"]` is now 5 s; the run continued from the kept answers.

`signals.Client.qlever` asks QLever for TSV, keeps the answer under `qlever:<hash of the query>`,
and never keeps a refusal or a timeout (QLever answers a timeout with a JSON body). The data is CC0;
QLever states no terms beyond fair use.

# 3. What is read (`genres.read`)

| Query | What | Rows |
|---|---|---|
| Songs | `?item wdt:P31 ?c; wdt:P175 ?performer`, `OPTIONAL { ?item wdt:P136 ?genre }`, `?c` among `SONG_CLASSES` | 279,344 |
| Titles | `rdfs:label`, then `skos:altLabel`, in en, es, ca, mul | about 475,000 labels |
| Performers | labels and other names by blocks of 2,000; their genres | |
| Genres | "subclass of" (P279) from each genre, 8 levels at most; English labels | |
| Tags | the work sets; the links song → work (`SONG_LINKS`) and work → song (`WORK_LINKS`); a work's soundtrack release (P406) that lists the song (P658) or that the song is part of (P361) | |

`SONG_CLASSES` came from the classes of every item with a performer (QLever, grouped by P31): song,
single, musical work/composition, music track with vocals, music track without lyrics, audio track,
single release, 7″ single, translated song, promotional single. Left out: album (311,022), extended
play, film, the characters (fictional, film, TV, comics), concert tour, music video.

**The match** (`genres.match`) is Phase 17's: each title of the item with its performers' first
labels joined by `;`, through `regional_import.Index.find` (one title form and one credited
artist). Several items can match one song (a song item and its single); their genres join. A
performer of a matched item whose name is one of the song's credited artists **stands for that
artist** (2,016 artists), so the artist's other songs can take its genres. The weaker way: a
public artist whose name only one performer has (2,003 more). A sample of 30 of the weaker matches:
28 right, 2 wrong, both through another name (`skos:altLabel`): "Clarence" is another name of a
drummer called Bones; "Masterplan" is a German power metal band, probably not the chart's act. With
main labels only, the weaker match would be safer.

# 4. The counts (Task 18.1.2)

Each public song in one column: genres of its own (a matched item with a genre that maps to one of
the 13), else its performer's (an artist that a matched item stands for), else by the weaker name
match, else none. A song in two regions counts in both region rows; the total counts it once.

| Region | Songs | Own | Performer | By name | None |
|---|---:|---:|---:|---:|---:|
| `worldwide` (the US chart) | 9,047 | 3,633 (40 %) | 3,115 | 1,969 | 330 (4 %) |
| `spain` | 12,870 | 2,369 (18 %) | 4,029 | 2,248 | 4,224 (33 %) |
| `catalan` | 960 | 4 | 101 | 122 | 733 (76 %) |
| All public songs | 21,069 | 5,002 (24 %) | 6,696 (32 %) | 4,108 (19 %) | 5,263 (25 %) |

By decade (own / performer / by name / none):

| Decade | `worldwide` | `spain` | `catalan` |
|---|---|---|---|
| 1950s | | 3 / 0 / 5 / 4 | |
| 1960s | | 27 / 27 / 68 / 38 | |
| 1970s | 332 / 157 / 387 / 115 | 48 / 50 / 80 / 86 | 0 / 0 / 0 / 2 |
| 1980s | 752 / 405 / 825 / 118 | 185 / 159 / 255 / 151 | 0 / 0 / 0 / 1 |
| 1990s | 496 / 306 / 315 / 27 | 233 / 182 / 234 / 359 | 0 / 1 / 0 / 0 |
| 2000s | 553 / 404 / 185 / 8 | 355 / 416 / 551 / 762 | 0 / 0 / 2 / 6 |
| 2010s | 858 / 649 / 138 / 17 | 883 / 985 / 406 / 814 | 2 / 15 / 35 / 209 |
| 2020s | 642 / 1,193 / 118 / 44 | 456 / 1,397 / 245 / 837 | 2 / 85 / 85 / 515 |
| No year | 0 / 1 / 1 / 1 | 179 / 813 / 404 / 1,173 | |

Read from it: Wikidata covers the US chart well (96 % get a genre one way or another), Spain less
(67 %), Catalan songs hardly at all (24 %, and 4 songs of their own): Wikidata has few items for
Catalan songs, and many Catalan artists have no genre.

**The genres of the app** the songs would get (the two most frequent after the map; own genres
only, then with the performer's): pop 1,819 / 3,917; rock 1,460 / 2,760; electronic and dance 848 /
1,480; hip hop 787 / 3,505; r&b and soul 734 / 2,372; country 375 / 961; latin 316 / 2,682; indie
78 / 137; jazz and blues 45 / 179; folk and singer-songwriter 40 / 112; metal 24 / 41; classical
8 / 25; soundtrack 3 / 3. (Before the corrections of section 5.)

# 5. The proposed map

`genres.map_genres` walks "subclass of" from a Wikidata genre up to the nearest genres of
`ROOTS` (26 Wikidata genres, each standing for one of the 13: pop music for pop, rock music for
rock, hip-hop and rapping for hip hop, rhythm and blues, contemporary R&B, soul and funk for r&b and
soul, electronic music, dance music, EDM and disco for electronic and dance, Latin music and
reguetón for latin, independent music, indie pop and indie rock for indie, folk music, country
music, jazz, blues, classical music, art music, film score, soundtrack, heavy metal). The roots at
the smallest distance all count: "electropop" is under pop music and electronic music, so it is
proposed as both; "indie rock" is a root itself, so it is indie only. A song keeps at most two:
the most frequent after the map, a tie broken by the narrow genres first (metal, country, latin,
hip hop … rock, pop last), `genres.chosen`.

The 40 most frequent Wikidata genres (public songs with it as their own / through their performer
only) and what the walk proposes:

| Wikidata genre | Own | Performer | Proposed |
|---|---:|---:|---|
| pop music | 774 | 2,366 | pop |
| contemporary R&B | 435 | 1,594 | r&b and soul |
| reguetón | 154 | 1,823 | latin |
| hip-hop | 426 | 1,294 | hip hop |
| Latin trap | 27 | 1,291 | latin, hip hop |
| pop rock | 347 | 897 | rock, pop |
| Latin pop | 71 | 1,070 | latin, pop |
| trap music | 156 | 855 | hip hop |
| rock music | 308 | 679 | rock |
| country music | 304 | 621 | country |
| pop rap | 69 | 643 | hip hop |
| dance-pop | 209 | 415 | pop |
| Latin R&B | 4 | 596 | latin, r&b and soul |
| soul | 89 | 400 | r&b and soul |
| alternative rock | 155 | 334 | rock |
| rhythm and blues | 115 | 363 | r&b and soul |
| Southern hip-hop | 17 | 424 | hip hop |
| electropop | 106 | 249 | electronic and dance, pop |
| dancehall | 34 | 315 | none |
| urban contemporary | 7 | 326 | none |
| synth-pop | 181 | 147 | electronic and dance, pop |
| Latin hip-hop | 0 | 324 | latin, hip hop |
| electronic dance music | 73 | 242 | electronic and dance |
| dance music | 48 | 264 | electronic and dance |
| soft rock | 170 | 134 | rock, pop |
| gangsta rap | 28 | 275 | hip hop |
| hardcore hip-hop | 17 | 283 | hip hop |
| folk music | 22 | 265 | folk and singer-songwriter |
| jazz | 3 | 277 | jazz and blues |
| new wave | 123 | 146 | rock |
| hard rock | 143 | 110 | rock |
| funk | 63 | 187 | r&b and soul |
| urbano music | 0 | 249 | latin |
| alternative hip-hop | 29 | 199 | hip hop |
| disco | 115 | 101 | electronic and dance |
| country pop | 83 | 116 | country, pop |
| flamenco | 8 | 191 | latin |
| folk rock | 36 | 163 | rock |
| East Coast hip-hop | 13 | 186 | hip hop |
| house music | 63 | 136 | electronic and dance |

**The corrections proposed by hand** (the walk follows Wikidata's links, which are sometimes not
what the app means):

| Wikidata genre | Songs | The walk says | Proposed |
|---|---:|---|---|
| salsa, bachata | 107, 63 | electronic and dance (Wikidata files them under dance music) | latin |
| electro latino | 59 | electronic and dance | latin, electronic and dance |
| nu metal, alternative metal, glam metal | 47, 37, 40 | rock | metal |
| pop-punk | 101 | pop | rock, pop |
| G-funk | 43 | r&b and soul | hip hop |
| dance-pop | 624 | pop | pop, electronic and dance |
| urban contemporary, gospel music | 333, 129 | none | r&b and soul |
| K-pop | 60 | none | pop |
| nova cançó | 5 | none | folk and singer-songwriter |
| Americana | 16 | none | country |
| Celtic music | 21 | none | folk and singer-songwriter |
| ambient music | 24 | none | electronic and dance |
| Electropop (Q16836684, a second item) | 27 | none | electronic and dance, pop |

**Left as none** (no genre of the 13 fits): dancehall, reggae, reggae fusion, ska (491 songs in
all), popular music (116: Wikidata's word for "any popular song"), world music, Christmas music,
stage and screen, ballad, experimental music, avant-garde, psychedelic music, new age, Afrobeat,
easy listening, and "male" (Q6581097, a data error).

**Open in the map**: flamenco, new flamenco, rumba flamenca and Catalan rumba (348 songs) are walked
to latin, because Wikidata files flamenco under Latin music. In Spain "latin" usually means music
from Latin America; folk and singer-songwriter is the other choice.

# 6. The tags

Each link found, by the way it is written (public songs, works):

| Category | Way | Songs | Works |
|---|---|---:|---:|
| films | `<P2550` recording or performance of (the work is a recording of the song) | 179 | 186 |
| | `P406+album` a soundtrack release of the film lists the song | 104 | 76 |
| | `<P406` the song is the film's soundtrack release | 38 | 35 |
| | `<P658` tracklist, `P361>` part of, `<P942` theme music, `<P144` based on, `<P10664` featured tracks, `P1441>` present in work | 20, 18, 12, 7, 6, 4 | |
| tv_shows | `<P10664` featured tracks, `<P942` theme music, `P406+album`, `<P658`, `P361>`, `P1441>` | 18, 18, 5, 2, 2, 1 | |
| video_games | `<P144`, `<P942` | 1, 1 | |
| adverts | none (Wikidata has 91 TV adverts and 152 campaigns in all) | 0 | 0 |

**"Recording or performance of" gives concert films**, not songs in a film: "Live in Athens 1987",
"Play: The Videos", "City of Lover". "Featured tracks" of a TV programme is mostly the Eurovision
editions. Counting only the links that mean the song is **in** the work (`<P406`, `P406+album`,
`<P942`, `P1441>`):

| Category | Songs | Works | The works with most songs |
|---|---:|---:|---|
| films | 119 | 88 | KPop Demon Hunters 9, Purple Rain 8, Encanto 7, Saturday Night Fever 6, Fame 5, Dirty Dancing 4, Beauty and the Beast 4, Frozen 3, The NeverEnding Story 3 |
| tv_shows | 24 | 20 | Eurovision Song Contest 2022 3, Beverly Hills 90210 2, Dawson's Creek, The Golden Girls, Verano azul |
| video_games | 1 | 1 | |
| adverts | 0 | 0 | |

The Tag chip of Public songs lists every value in one menu, grouped by category, with no search
inside ([`FilterChip.tsx`](../../../aitu-frontend/src/ui/FilterChip.tsx)); 88 films fit it.

# 7. The import, as designed (Story 18.2, after Q-11)

- **No new revision.** `song_genres` and `song_tags` hold what is needed; where a genre came from is
  told by the requests instead of a column: an accepted request writes a song's genres and tags as
  a whole (`requests._write_song_fields` deletes them first). So the import **leaves alone every
  song an accepted request named** (a `metadata` item with `target: song`, `songId`; a `newSong`
  item, `made.songId`), and on every other public song it owns the genre and tag rows: it writes
  them again on each run, so a second run changes nothing and a corrected map applies.
- A tag value is made when a song needs it; a value no song uses any more is deleted.
- The item's key `wikidata.org:Q…` goes into `song_keys` for each matched song (Task 18.1.1).
- Run on a copy of `.database/`, then on the real one after `make db-backup`; `make db-check`.

# 8. Q-11, raised 2026-10-19

1. **The map**: the walk with the corrections of section 5 (recommended), or a review of the whole
   list ([`genres-measure.json`](research/phase-18/genres-measure.json), 514 genres). And flamenco:
   latin (as the walk) or folk and singer-songwriter.
2. **A song with no genre of its own**: A its performer's when a matched item ties the performer to
   the artist (recommended: 11,698 songs, 56 %); B also by a unique name, main labels only (about
   15,800, 75 %; about 1 wrong artist in 15 in the sample, mostly through other names); C none
   (5,002, 24 %).
3. **The tags**: A films only, from the soundtrack links (recommended: 119 songs, 88 films); B films
   and TV programmes (143 songs); C none for now, all by request.

# 9. Checks so far

| Check | Result |
|---|---|
| `test_genres.py` (new, 5) | A QLever answer read and kept, a refusal and a timeout not kept; the map to the nearest roots (both at a tie, a root itself first, a loop, none); the two genres a song keeps; the match of items and performers (two items of one song, a cover by another performer left out, a shared name not matched); the measure's counts and tags |
| `test_signals.py` | passes (the client changed) |
| `black`, `flake8`, `mypy` on `genres.py`, `signals.py`, the test | clean |

# 10. Learnings so far

- **The Wikidata query service can limit everyone at once** (1 query a minute during an outage);
  QLever serves the same data, much faster, with a 30 s limit and a rate limit of its own.
- **Ask QLever for TSV**, never a `UNION` of two large patterns, and classify large sets on this
  machine instead of joining them with `P31/P279*`.
- **A property can mean the opposite of what it looks like**: "recording or performance of" ties a
  concert film to each song it plays.
