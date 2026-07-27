# Task 10.3.1 — Playlists

Spotify-like organization over library tracks, stored under `library/playlists/<slug>/metadata_library_playlist.json`.

## Subtask 10.3.1.1 — CRUD and ordering

Create/rename/delete playlists; add a track (choosing the promoted version by its promotion name when several exist); drag to reorder; remove entries. Add-to-playlist also reachable from the track list (existing or new playlist).

## Subtask 10.3.1.2 — Playing mode

Selecting a playlist opens a read-only flow: pick the starting track, its score renders in the performance view, and at the end a single Next click loads the following piece seamlessly — the concert use case. Order editable before starting.

## Subtask 10.3.1.3 — Nice to have: slicing

Playlist entries may reference a slice (time range) of a piece rather than the whole score. Skip until asked.

## Acceptance

Manual trial: an "all_about_avicii" playlist with 2 tracks, played through with Next.
