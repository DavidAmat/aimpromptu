# The music library's ontology

The music library is a catalogue of songs, artists, albums and versions, kept apart from the
projects ([app context](../app/01-app-context.md), "Music Library"). This page says what each
entity is, how the two scopes (private and public) share the same tables, how a private row stands
for a public one, and what the Public Library pages show. Built in implementation 02: the tables in
Phase 3, the Private Library in Phase 6, the public rows (imported) and their pages in Phase 13, the
requests that change them in Phase 14 ([requests.md](requests.md)).

## 1. The entities

| Entity | What it is | Table |
|---|---|---|
| **Artist** | A person or a band, with its own id | `artists` |
| **Artist name** | One way to write an artist: "The Jackson 5" and "Jackson Five" are two names of one artist. One name is the default | `artist_names` |
| **Song** | A piece of music, unique by its id: "Heaven" of Bryan Adams and "Heaven" of Avicii are two songs. A song points at artist **names**, each of which points at its artist | `songs`, `song_artists` |
| **Album** | Optional; its artists, its release date, its own chart history | `albums`, `album_artists`, `song_albums` |
| **Version** | A named pointer from a song to a project. Public: the fixed versions and the Other versions; private: free names | `song_versions`, `user_versions`, `private_versions` |
| **Songs playlist** | Songs in order, each on a version and maybe a stretch | `playlists`, `playlist_items` |

A **project** is the work (the piano sheet, its audio); a **song** is the catalogue entry; a
**version** joins them. Every version of a library has its piano sheet (the user's rule of
2026-10-16).

## 2. Two scopes, the same tables

Every row of the music library has a `scope`:

- **public**: the Public Library, one for everyone. Its rows have no owner; the master user changes
  them by accepting requests ([requests.md](requests.md), Phase 14). It starts from the chart download of Phase 12
  ([reconciliation.md](reconciliation.md)): 9,055 songs, 2,998 artists, 8,341 albums, imported into
  the real database on 2026-10-16; Phase 16 added the Spanish and Catalan lists
  ([regional-sources.md](regional-sources.md)): 21,069 songs and 7,032 artists after its import
  (2026-10-19).
- **private**: each user's own ontology ([private-library.md](private-library.md)). A user names
  songs and artists as they like; no other user sees them.

**A private row can stand for a public row**: its `public_id` names it. That link is made in two
ways (Phase 13):

- **Add to my library** on a public song, artist or playlist copies it into private rows;
- **Save to library** on a public song or artist chosen in the dialog.

A third way since Phase 14: an accepted request links the author's own song and artists to the
public ones it made or named. Either way the private row is found before one is made: the one already linked, or else the user's
own song of the same title and first artist (or artist of the same name), which gets the link. So a
song never appears twice in a user's library because it came from two sides. After the link there
is no sync: the private row stays the user's own, renamed as they like.

## 3. The metadata of a public song

The fields of plan section 15.3, and what the Public Library has of each today:

| Field | Rule | Today |
|---|---|---|
| Year, decade | The decade is worked out from the year (1978 is the 70s), never stored | 9,044 songs have a year (the 8 seed songs and 3 chart songs have none) |
| Artists | Through artist names | From the chart; 7 songs have none |
| Album | Optional | 8,581 song-album links |
| Region | Where the song was popular, not where the artist is from | `worldwide`: the 9,047 songs of the US chart (the 8 seed songs have no region). `spain`: 12,870 songs of the Spanish lists (Phase 16). `catalan`: 960 songs of the APECAT top 30 and the Catalan Spotify table, in practice songs in Catalan or from Catalan labels |
| Genre | One or two of 13 | None from the import (Q-5: Wikidata is the recommendation); given by request (Phase 14) |
| Tags | Fixed categories (films, video games, TV shows, adverts), free values | Given by request (Phase 14) |
| Rankings | The chart weeks and places | 160,810 song weeks |
| Popularity | 0 to 100 from the rankings, in any time range, one per region; inferred from YouTube views where no chart of the region lists the song (Phase 17) | [popularity.md](popularity.md) |
| Lyrics | The words, as the download gave them | 9,038 songs; kept for this personal version only |

## 4. Versions of a public song

As plan section 15.2 says, a public song has:

- **Fixed versions**: Hard, Medium, Easy, and custom names the master user accepted for that song
  only. **Default** is a pointer to one of them (Hard unless changed).
- **Other versions**: the app context's `user_versions/<user>/<version name>/`, one project per
  user and version name, shown grouped by username, each group by its likes.

A version's project lives in `.database/public/<projectId>/`. Every user reads it and plays it; only
the master user writes it. Versions arrive by accepted requests ([requests.md](requests.md)): a user
version by a **Version** request, then a fixed version by a **Fixed version** request that points
at that same project. The user whose project it is shows as its creator. A user likes a version
once; Other versions are sorted by likes, then by date.

## 5. Add to my library

**Add to my library** copies from the Public Library into the user's Private Library (plan section
15.1):

| On | What it adds |
|---|---|
| A song | The song and its artists (with every name), and the versions the user ticks (the Default one at first) |
| An artist | Every song of the artist that has a version, each on its default version |
| A playlist | A songs playlist of the user's own, with its songs pulled on the version each item names; songs with no version are left out |

A pulled version is a **copy** of the public project in `users/<id>/library/` (no audio bytes
copied), named as the public one ("hard", or "easy (anna)" for anna's user version), with
`public_source_id` pointing back. A version already pulled is not pulled again.

**Only songs with a version are added** (the user, 2026-10-16): a song of My library must have its
piano sheet, and a public song with no version has none. The button says so on hover.

## 6. The pages

| Page | Address | What is on it |
|---|---|---|
| Public songs | `/public/songs` | A search (title and artists, accents ignored), the filter chips Decade, Region, Genre and Tag (a chip shows only when it has values; each value says how many songs it leaves), a table sorted by popularity, year or title, one page at a time. With a region, the popularity column is that region's; with a decade, that decade's (of the region, when one is chosen). A song with no value in the region shown has "–" and comes last; with no region, **Popularity by region** lists the song's value in each of its regions. The address keeps all of it |
| A public song | `/public/songs/:id` | The byline (links to the artists), the facts (a popularity per region), **On the charts** (each chart named with its region: best place, weeks, the line of its places), **Versions**, **Other versions** (each with Play, a like, Add to my library), **Lyrics** on request. **Play** the default version; **Add to my library**; **Open in My library** once it is there |
| Public artists | `/public/artists` | A search on every name, a table sorted by popularity (the artist's most popular song), name or number of songs |
| A public artist | `/public/artists/:id` | Its other names, its songs and its albums by popularity, **Add to my library** |
| Public playlists | `/public/playlists`, `/public/playlists/:id` | The public songs playlists (made by accepted **Playlist** requests, Phase 14); one with **Play** (Play mode, `?from=public`) and **Add to my library** |

**Suggest a change** (a song's or an artist's `⋯`), **Propose a song** (Public songs) and **Ask for
a fixed version** (the user's own version) send requests (Phase 14, [requests.md](requests.md)).

**Search** (`⌘K`) also lists the most popular public songs and artists that match, and **Save to
library** suggests them under "Public library". A song of My library that stands for a public song
links to it ("In the Public library").

## Where to look deeper

- The routes: [`endpoints.md`](../../documentation/services/backend/endpoints.md) §7.3
- The tables: [`paths-and-data.md`](../../documentation/services/backend/paths-and-data.md) section 6
- The import and the identity of a public row: [reconciliation.md](reconciliation.md)
- Popularity: [popularity.md](popularity.md)
- Requests, the review and shared libraries: [requests.md](requests.md)
- The Private Library: [private-library.md](private-library.md)
- The code: `aitu-backend/src/aitu_backend/library/` (`catalogue.py`, `public.py`, `pull.py`),
  `api/public.py`; `aitu-frontend/src/pages/public/`
