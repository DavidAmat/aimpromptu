# Genres and tags of the public songs

The Public Library's songs have **genres** (one or two of 13: pop, rock, hip hop, r&b and soul,
electronic and dance, latin, indie, folk and singer-songwriter, country, jazz and blues, classical,
soundtrack, metal; plan section 15.3) and **tags** (fixed categories: films, video games, TV shows,
adverts, each with free values such as "Shrek"; [app context](../app/01-app-context.md), "Songs").
The chart downloads give neither ([reconciliation.md](reconciliation.md) section 3). This page says
where they come from: Wikidata, mapped onto the 13 genres, imported in implementation 02, Phase 18
(Q-5, then Q-11, answered 2026-10-19). A request can still give or change them
([requests.md](requests.md)), and the import never undoes that.

## 1. The source

**Wikidata** is open data (CC0). It gives a song's genres (P136) and its performers' genres. It has
229,348 items that are a song, a single or a musical work with a performer (P175); 119,000 of them
have genres of their own.

The queries go to **QLever** (`qlever.dev`, University of Freiburg), a public copy of Wikidata made
for large queries: the largest answers in 2 s. The Wikidata query service limited every client to
1 query a minute when this was built (2026-10-19). QLever stops a query after 30 s and refuses for
a few minutes when asked too fast, so the client asks once every 5 s. Every answer is kept with its
date in `data/music-library-genres/answers.sqlite` beside the repository, so a second run asks
nothing.

## 2. The match

A Wikidata song is matched to a public song by the identity rule of the regional import (its title
and one credited artist, [regional-sources.md](regional-sources.md)); the item's id is then kept as
a key of the song (`wikidata.org:Q…` in `song_keys`), so the next run finds it directly. 6,242
public songs match 8,297 items (a song and its single are two items; their genres join).

A **performer** of a matched item that is one of the song's credited artists stands for that
artist (2,016 artists). That lets the artist's other songs take its genres.

## 3. The map onto the 13 genres

Wikidata has hundreds of genres ("electropop", "Latin trap"); 514 reach the public songs. Each one
is mapped onto one or two of the 13, or none:

1. **A walk up "subclass of"** (P279) to the nearest of 26 root genres, each standing for one of
   the 13 (pop music for pop, rock music for rock, reguetón and Latin music for latin, disco and
   dance music for electronic and dance …). All roots at the nearest distance count: electropop is
   pop and electronic and dance; pop rock is pop and rock; indie rock, a root itself, is indie.
2. **Corrections by hand** where Wikidata's links say something the app does not mean: salsa and
   bachata are latin (Wikidata files them under dance music); nu metal, alternative metal and glam
   metal are metal (not rock); pop-punk is rock and pop; G-funk is hip hop; dance-pop is pop and
   electronic and dance; urban contemporary and gospel are r&b and soul; K-pop is pop; nova cançó
   and Celtic music are folk and singer-songwriter; Americana is country.
3. **None** where no genre of the 13 fits: reggae, dancehall, ska, Christmas music, "popular
   music", world music, stage and screen, ballad, experimental music. Flamenco and rumba are latin,
   as Wikidata files them.

The list, with the songs of each Wikidata genre and what it maps to, is the
[Phase 18 measure](../implementations/02-private-web-app/research/phase-18/genres-measure.json).

## 4. A song's genres

1. **Its own**: the genres of its matched items after the map;
2. else **its performer's**: the genres of a performer that stands for one of its artists (section
   2). A performer matched only by having the same name is not used: in a sample, 2 artists in 30
   were the wrong one;
3. else none.

**At most two**: the most frequent after the map. A second genre is kept only when it counts at
least half as often as the first, and a tie goes to the commoner genre (pop, rock, electronic and
dance, hip hop …). So The Black Eyed Peas, whose five Wikidata genres give hip hop four times and
latin once, are hip hop only.

| | Songs | With a genre |
|---|---:|---:|
| All public songs | 21,069 | 11,717 (56 %): 5,010 their own, 6,707 their performer's; 5,167 have two |
| `worldwide` | 9,047 | 6,754 (75 %) |
| `spain` | 12,870 | 6,414 (50 %) |
| `catalan` | 960 | 105 (11 %): Wikidata has few Catalan songs, and many Catalan artists have no genre |

Songs per genre: pop 4,465, rock 2,753, hip hop 2,742, latin 2,494, electronic and dance 1,720,
r&b and soul 1,507, country 819, folk and singer-songwriter 108, indie 106, jazz and blues 84, metal
73, classical 10, soundtrack 3.

## 5. Tags: films only

The links that put a song **in** a work: the work's soundtrack release is the song or lists it
(P406, then the album's tracklist P658 or the song's "part of" P361), the song is its theme music
(P942), or the song is "present in work" (P1441). "Recording or performance of" is left out: it
ties a concert film to every song the concert plays.

| Category | Songs | Works | Imported |
|---|---:|---:|---|
| Films | 119 | 88 (87 values: two films share a title) | yes: KPop Demon Hunters, Purple Rain, Encanto, Saturday Night Fever, Fame, Dirty Dancing … |
| TV shows | 24 | 20 | no (the user, 2026-10-19): a few, some of them Eurovision editions |
| Video games | 1 | 1 | no |
| Adverts | 0 | 0 | Wikidata has almost no adverts |

Each film is a value of **films**, named by its English label. The other categories come by
request.

## 6. The import

```bash
make genres-measure                       # read and count; writes nothing
make genres-import                        # the real .database/ (after make db-backup)
make genres-import ARGS="--database DIR"  # a copy
```

One transaction, about 2.5 s. **A song an accepted request named is left alone**: a metadata change
of a song, or a new song (a request writes a song's genres and tags as a whole). On every other
public song the import owns the genre and tag rows and writes them again on each run, so a second
run changes nothing and a corrected map applies at once. A film value no song uses any more is
deleted. No table changed (no Alembic revision).

**Run on the real `.database/` on 2026-10-19**, after `make db-backup`: 11,717 songs with a genre,
119 with a film, 8,297 keys; a second run wrote nothing; `make db-check` reports no problem.

## 7. The pages

**Public songs** offers the **Genre** chip (the 13, each with its songs) and the **Tag** chip
(the films under a heading "Films", each with its songs); a song's page lists its genres and its
tags ("Films: Saturday Night Fever"). Both chips show as soon as they have values (Phase 13).

## Where to look deeper

- The measure, the counts and Q-11: [Phase 18 report](../implementations/02-private-web-app/02-implementation-phase-18.md)
- The tables (`song_genres`, `tag_values`, `song_tags`, `song_keys`): [`paths-and-data.md`](../../documentation/services/backend/paths-and-data.md) section 6
- The other fields of a public song: [ontology.md](ontology.md)
- The code: `aitu-backend/src/aitu_backend/library/genres.py` (`ROOTS`, `HAND`, `TAG_LINKS`),
  `library/signals.py` (`Client.qlever`); the tests `test_genres.py`
