# Task 10.1.1 — Library browse · progress

Status: **done** on 2026-08-13.

## What was implemented

The Piano Library page lists two things.

**Ready to play** is `library/tracks/`. Real artist and piece names, plus the promotion name when
a piece has more than the default. Search matches those names, not slugs. Each promotion says
whether a saved rhythm exists (`data/audio/<uuid>/matrices/rhythm.json`). Tag chips come from
`GET /library/tags` and combine with the search. Edits to tags and playground names are the
existing metadata files, so they survive a restart.

**Playground** is everything under `playground/`. Version chips read `v2_f40`. Folders the old
`v2_gn` scheme left behind are omitted from the list; loading one is still a 422, as
`parse_version_folder` already refused. Rename changes display names only. Open loads the linked
audio into the working artifact and goes to the Playground — never the performance view.

`needsRederivation` is computed at list time from the audio folder, not stored on the track
metadata. A flagged promotion cannot be opened in `/library/play/:id`; the button is disabled and
a direct URL shows the reason instead of the (still placeholder) performance page.

Playlists stay a Story 10.3 placeholder.

## Errors found

None that changed the approach. Black was run only on the files this task touched; a full-tree
format would have rewritten unrelated modules that are not yet black-clean.

## Deviations

Rhythm and rederivation flags are extra fields on the list DTOs (`LibraryTrackEntry`,
`PlaygroundTrackEntry`), filled in `storage/browse.py`. They are not written to
`metadata_library_track.json` or `metadata_track.json`. Same pattern as `AudioEntry` on
`GET /audio`.

Performance view (10.2) is still a placeholder, but it now refuses a flagged piece so the
acceptance criterion holds before that story lands.

## Manual trial

1. Promote two playground pieces. Give one a custom promotion name (e.g. "Levels (Chill) - Avicii").
2. Tag one `edm`, the other `classical`. Filter by tag; search the promotion name; both should
   combine.
3. Confirm each row says **Rhythm saved** or **Needs naming**.
4. Rename a playground piece; reload the page — the new names are still there, the folder is not.
5. Flag a piece `needsRederivation` (or open one the migration marked). The warning shows, **Open**
   is disabled, and `/library/play/<artist>--<track>` does not show the performance placeholder.

## For the next worker

Story 10.2 draws the read-only score. Play ids are `artistSlug--trackSlug` with
`?promotion=<name>`. Use `libraryApi.getTrack` and the saved rhythm the same way the Rhythm tab
does. Do not invent a second score payload. Playlists are Task 10.3.1.
