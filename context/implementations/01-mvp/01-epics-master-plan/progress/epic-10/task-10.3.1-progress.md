# Task 10.3.1 — Playlists · progress

Status: **done** on 2026-08-13.

## What was implemented

Playlists live at `data/library/playlists/<slug>/metadata_library_playlist.json`. The slug is
identity; renaming the display name never moves the folder.

CRUD is `GET/POST /library/playlists` and `GET/PATCH/DELETE /library/playlists/{slug}`. Each item
pins a promotion by name (`artistSlug`, `trackSlug`, `promotionName`). An unknown track or
promotion is a 404, so a playlist cannot point at something that is not in the library.

The Piano Library page has a Playlists card: create, rename, delete, add pieces (by promotion name
when there are several), drag or arrow-reorder, remove entries. Every Ready-to-play row also has
**Add to a playlist**, which can append to an existing list or create a new one.

**Play** opens the performance view on the first piece with `?playlist=` and `index=0`. **Next** on
the stand loads the following item. Order is editable on the library page and not during playing.

## Errors found

The smoke client hits the real `data/` tree, so `GET /library/playlists` must not assert an empty
list. It only checks that the response is a JSON array.

## Deviations

Excerpts (10.3.1.3) were skipped, as the task asked.

Creating a playlist whose name slug-collides with an existing one gets a suffix (`sunday-practice-2`)
rather than a 409. The slug is not a user-facing identifier.

## Manual trial

1. Promote two pieces (or two promotions of one piece). Create a playlist, add both, Play.
2. Confirm Next opens the second piece on the stand.
3. Back to the library, reorder before starting, Play again — the new first piece opens.
4. Restart the backend. The playlist is still there with the same order.

## For the next worker

Epic 10 is complete. Next is Epic 11 (range editing) unless Story 9.7.2 (trills) is merging first.
Do not invent a second score payload; the stand already uses the Rhythm tab's. Excerpts, if asked
for later, are a wall-clock range in seconds on `PlaylistItem`, not frames.
