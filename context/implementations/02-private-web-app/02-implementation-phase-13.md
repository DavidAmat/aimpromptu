# 02: Phase 13 report: The Public Library

Plan: [`02-plan.md`](02-plan.md) sections 6.1, 6.3, 15.1 to 15.6 and 17, and section 20, Phase 13.
Checklist: [`02-checklist.md`](02-checklist.md). Branch `feat/phase-13`, made from `master` at
`81affa9` (Phase 12 merged and pushed after the user's ok, 2026-10-16). Built 2026-10-16 on the
Ubuntu machine, while another process held 11 GB of the GPU: the backend tests ran on the CPU and no
check that transcribes was run (none was needed: nothing of the transcription changed).

The pages this phase writes are [`../../music-library/ontology.md`](../../music-library/ontology.md)
and [`../../music-library/popularity.md`](../../music-library/popularity.md); this report is the
detail behind them.

# 1. Summary

| Story | Result |
|---|---|
| 13.1 The import | `make public-import` on the real `.database/`, after `make db-backup` (`.database-20261016-151058.tar.zst`, 1.26 GB): 2,995 artists, 8,341 albums, 9,047 songs and the 8 seed songs not on the chart, 9,038 lyrics, 160,810 song weeks and 129,988 album weeks, in 2.7 s. A second run made 0 rows. `make db-check`: no problem. 23 of the 31 seed songs found on the chart, 8 added |
| 13.2 The pages | `/public/songs` (search on titles and artists, accents ignored; the chips Decade and Region, Genre and Tag once they have values, each value with its count; sort by popularity, year or title; one page at a time; all of it in the address), `/public/songs/:id` (facts, **On the chart** with the line of its places, **Versions**, **Other versions** by user, likes, lyrics, **Play**), `/public/artists` and one artist (songs and albums by popularity), `/public/playlists` and one playlist (**Play** in Play mode). The sidebar has a **Public library** group |
| 13.3 Pull | **Add to my library** on a song (the versions ticked, the Default one first), an artist (its songs with a version) and a playlist (a songs playlist of the user's own). Asked by the user at the start: only a song with a version is added; **Save to library** suggests public songs and artists and links the private row to the public one |
| 13.4 Documentation | `ontology.md` and `popularity.md` (new); the other pages of section 9 |

Checks (section 7): backend 1,120 tests on the CPU, only the 3 known CPU failures; the 11 new tests pass; `check:public` (new, 38 checks) and the browser checks of the pages it touches (`check:library`, `check:play`, `check:projects`, `check:compose`) pass; lint, build and `check-links.py` pass; `make db-check` reports no problem.

# 2. Two decisions asked at the start

Both were asked before any code, because each changes what is built. The user chose the
recommendation each time (2026-10-16).

1. **What Add to my library does on a song with no version.** No public song has a version before
   Phase 14 publishes one, and the user's rule of Phase 12 says a song of My library has its piano
   sheet. **Answer: only songs with a version are added.** The button is disabled with "No version
   yet: a song of your library needs its piano sheet" on hover; an artist adds its songs that have
   one; a playlist leaves the others out.
2. **Should Save to library suggest the Public Library's songs and artists.** The app context makes
   the Public Library "the source of truth for all the dropdowns". **Answer: yes**, and the private
   song or artist is linked to the public one (`public_id`), so Phase 14's Publish dialog knows which
   public song a private song is.

# 3. The design

## 3.1 The list in memory (`library/catalogue.py`)

The search must match a word anywhere in a title or an artist's name, ignoring case and accents.
SQLite's `LIKE` folds only ASCII letters, and a Python function in SQL costs a call per row on
every request. So the public songs and artists are read into memory once (about 0.3 s) and each
request filters and sorts that list.

| Request on the real data | Time |
|---|---|
| The fingerprint (below), every request | 4 ms |
| The first list after a start (reads the 9,055 songs) | 118 ms |
| A search ("beyonce": 70 songs) | 8 ms |
| The 80s by their popularity of the 80s, first time / again | 65 ms / 11 ms |
| An artists search, the suggestions | 4 ms, 6 ms |

**The list stays current by a fingerprint**: one SQL query of counts and sums of the public rows
(songs, their years, popularity and title lengths; the public artists' names; the links to artists,
regions, genres and tags; the versions). When it changes (an import from the host, a version placed,
a change in Phase 14) the list is read again. A change that leaves every count and sum equal is not
seen, so the code that changes public rows also calls `catalogue.forget()` (the import runs in
another process; it changes counts, so the fingerprint sees it). Rejected: a search column with a
migration (a new revision moves the real database at once, Phase 12's learning), and SQLite FTS5
(more machinery than 9,000 rows need).

**The popularity of a decade** is `popularity.song_scores(start, end)` on the decade's weeks, kept
with the list per range. The decade of a song is its year's; the score counts only that decade's
weeks (a song of 1979 that charted into 1980 is scored on its 1979 weeks).

**Facets**: each filter's values are counted over the songs the other filters leave, so a value
says what it would show.

## 3.2 One song, versions, likes (`library/public.py`)

A public version is a project of `.database/public/`. `place_version` puts a **copy** of a project
there as a fixed version (replacing the one of that name) or as a user version (one per user and
name), checks that it has its piano sheet and that the name is a simple name (lowercase letters,
digits, hyphens, at most 24 characters, plan section 15.2). It is the step Phase 14's acceptance
needs; this phase uses it in the tests and, through `library/public_fixture.py`, in `check:public`.

The like routes take their project as `public_project`, not `project_id`: the router's rights check
reads a `project_id` on a `PUT` as a write of that project, which only the master user may do on a
public one.

## 3.3 The pull (`library/pull.py`)

The pull copies the entities into private rows that keep `public_id`, and each chosen version's
project into `users/<id>/library/` (no audio bytes, P-3), with `public_source_id` pointing back.
Before a private row is made, the one that already stands for the public row is used: linked by
`public_id`, or the user's own song of the same title and first artist (or artist of the same
name), which gets the link then. This keeps "the same song does not appear twice" (app context)
when a user saved a song before it was in the Public Library, which is the case of the master
user's 30 songs: a pull of "7 Years" would add a version to their own "7 Years".

The names of pulled versions are the public ones: `hard`, and `easy (anna)` for anna's user
version, with ` 2` when taken. **Save to library** on a public song or artist uses the same lookup
(`find_private_song`, `private_song_for`, `private_artist_for`).

## 3.4 The pages

The pages use the shared components; two additions:

- `DataTable` has a **server mode** (`sort`, `onSortChange`, `paging`): the rows come sorted and
  cut by the backend, and the page controls show the whole count;
- `FilterChip`: a filter as a chip, its values with their counts in a menu, a cross to take it off.

The one new drawing is the **chart line** of a song (`ChartHistory`): its place each week, place 1
at the top, broken where the song left the chart for more than three weeks, the best place marked,
with the same numbers written beside it (best place, weeks, when). It is drawn at its real width up
to 640 px, so its words keep their size on a phone. Everything else is black, white and grey, as the
design system asks.

Popularity shows one decimal: the top songs differ in it (99.8, 99.7), and whole numbers made the
first three read "100".

`PageHeader` keeps at least 160 px for the title under 900 px: at 390 px the two buttons of a public
song hid its title.

# 4. Tests

| File | Tests | What |
|---|---|---|
| `test_public.py` (new) | 11 | Two users signed in through `/auth`, the public rows of `test_public_import`'s small download. The list: words in any order, accents, a decade and its facet counts, a region, an unknown region (`422`), by title, by year with no year last, pages. The popularity of a decade counts only its weeks (Billie Jean's 1983 weeks without its 2009 re-entry). One song: facts, album and track, chart, lyrics, no version, Add refused (`409`). An artist's songs and albums; Add refused with no version. Suggestions. A public version is a copy (the source stays in the vault), names refused, the list counts versions at once, likes once per user, a like on a project that is not a public version (`404`), every user reads and plays a public version but cannot write it (`403`). Add a song: the default version, the artists, `public_id`, `public_source_id`, no audio copied, the sheet ready, `inLibrary`; again (nothing new); another version by name ("easy (master)"); a version of another song (`404`). An artist and a playlist (the song without a version left out, the stretch kept, the same playlist when pulled again). Save to library on a public song (twice: one song, two versions; the artists linked) and with a public artist. A user's own song of the same title and artist is linked, not copied. The list sees a change of a public row |

# 5. The browser check `check:public`

`aitu-frontend/scripts/check-public.mjs` (`npm run check:public`), signed in as the master user, on
copies only: a duplicate of a version of My library ("7 Years") is placed twice, as Hard and as a
user version "easy", of the public song "Stayin' Alive", which the master user's library does not
have (the script refuses to run if it does). It walks the songs list, one song, a like, the lyrics,
Play mode, **Add to my library**, the song in My library with its link back, a song with no version,
the artist, the artists, a public playlist (placed by the same fixture) with **Add to my library**,
**Play** and **Close**, **Search**, **Save to library** on the public song, 390 px and dark. At the
end it deletes the pulled song and artist, the playlists, the public versions and the copies, and
checks that nothing is left. **38 checks passed**, no console error and no failed request other than the expected refusals; run three times in all, the last into [`screenshots/phase-13/`](screenshots/phase-13/).

# 6. Speed

The backend times are in section 3.1 (measured on the real data, the machine loaded by the other
process). In the browser a page of 50 songs, a search or a chip answers before the dimmed table is
noticed; the first list after a backend start reads the 9,055 songs once (118 ms). Play mode on a
public version is Play mode on any project (Phase 11: 650 to 765 ms to the first notehead).

# 7. The checks

| Check | Result |
|---|---|
| Backend, full run **on the CPU** (another process held 11 GB of the GPU) | 1,120 tests: 3 failed, the known `test_the_worked_example_at_00_46_prints_three_equal_corcheas` and the two Transkun tests that fail only without a GPU; the real-model test skips itself on the CPU; every other test passed. Phase 12: 1,107 |
| `test_public.py` (new) | 11 passed |
| `black`, `flake8`, `mypy` on the new and changed backend modules | clean |
| `tsc -b`, `npm run lint`, `npm run build` | clean; the chunk-size warning of Phase 0 |
| `check:public` (new), signed in | 38 checks passed, nothing left behind |
| `check:library`, `check:play`, `check:projects`, `check:compose` (the shared header, the table, Play mode, the save dialog and the song page changed) | 27, 32, all, 24 checks passed |
| `make public-import` on the real `.database/`, twice | the counts of section 1; the second run made 0 rows |
| `make db-check` on the real `.database/` | no problem, after the import and after every script |
| `scripts/docs/check-links.py` | passes |
| Checks that transcribe (`check:passage`, `check:flow` live, `time:flow`) | not run: the GPU was held, and nothing of the transcription changed |

# 8. The 13 checks of the 09 guidelines

Run on the six public pages, the save dialog's suggestions and Search, with the screenshots of
[`screenshots/phase-13/`](screenshots/phase-13/), taken by `check-public.mjs`.

| # | Check | Result |
|---|---|---|
| 1 | One sentence | Find a song of everyone's library, see how big a hit it was, and play or keep a version of it |
| 2 | Every sentence a label, control or fact | No sentence but "No version yet." and the empty states. The facts are label and value |
| 3 | Words above the first content | The title; on a song the byline (2 lines) |
| 4 | Very wide | The table is sized by its content; the facts in columns of 150 px or more; the chart line at most 640 px (shots 01, 03) |
| 5 | Narrow (390 px, shots 15, 16) | 0 px of sideways scroll; the header's buttons go under the title; the table scrolls inside itself; the page controls keep the range and the arrows |
| 6 | Longest, shortest, none | Long titles cut with "…" (full on hover); a song with no year says "Unknown", with no artist "No artist"; no album, region, genre or tag: the fact is not drawn; no version: "No version yet."; no chart week: no chart section; no public playlist: one line |
| 7 | Buttons say what happens | "Add to my library", "Add 1 version", "Open in My library", "Play", "Show lyrics", "Like this version" / "Remove your like" (tooltips), "Any decade" |
| 8 | Helper lines | One: "From the Public Library" under the Song field when a public song is chosen |
| 9 | Loading, empty, partial, error | Skeletons; the table dims while the next page loads; an error in the backend's words with **Try again**; a refused Add says why (409) |
| 10 | Tab through it | Chips, headers, rows, likes and menus are buttons; the chip menu takes the arrows |
| 11 | Internal names | None: no "facet", "scope", "external key", "pull". "Public library" and "My library" are the sidebar's words |
| 12 | First-time user | "Public songs", "Decade", "On the chart", "Versions", "Other versions" |
| 13 | Anti-patterns | No card grid, no badge per row: the versions are rows; colour stays out (the chart line is the text colour) |

| Shot | Page |
|---|---|
| 01 | Public songs, by popularity |
| 02 | A search and the Decade chip: "Popularity in the 70s" |
| 03 | One song: facts, the chart line, Versions (a like), Other versions |
| 04 | Its lyrics |
| 05 | Play mode on a public version |
| 06, 07, 08 | Add to my library: the dialog, the song added, the song in My library with "In the Public library" |
| 09 | A song with no version |
| 10, 11 | An artist; the artists searched |
| 12 | A public playlist |
| 13 | Search with public results |
| 14 | Save to library: the public suggestion |
| 15, 16, 17 | 390 px (a song, the songs); dark |

# 9. Open points

- **No public version or playlist exists** until Phase 14 accepts requests. Play, likes and **Add to
  my library** are therefore disabled or absent on every public song today; they were checked on
  temporary versions (section 5).
- **Genres, tags, `spain` and `catalan`**: still Q-5. Their chips appear by themselves once a song has
  one.
- **The lyrics** are shown on the public song page, as kept by Phase 12: fine for this personal
  version, not for a production one (reconciliation section 3).
- **A merge of public rows in Phase 14 must keep the merged row's key** (Phase 12's open point), and
  now also its `public_id` links: a private row pointing at a merged public row should point at the
  one kept.
- **Albums have no page**: an album is a fact of a song and a list of an artist. The plan names no
  album page.

# 10. Learnings for later phases

- **A router-level rights check reads every `project_id` path parameter**: a route that writes the
  user's own rows about a project they may only read (a like) must name its parameter otherwise.
- **A list of thousands that must search with accents is cheaper in memory than in SQLite**, kept
  current by a fingerprint of counts and sums.
- **A shared header can hide its title on a phone** when a page has two buttons: check 390 px on
  every new page, not only the new components.
- **A check that writes into the library must refuse to run when its target already exists** in the
  real library: the pull links a user's own song of the same title, so "7 Years" would have gained a
  version.
