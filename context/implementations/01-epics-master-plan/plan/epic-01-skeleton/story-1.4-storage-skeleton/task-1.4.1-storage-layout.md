# Task 1.4.1 — Storage layout

Local file storage under `aitu-backend/data/`. See `context/07-database.md` (no database; files only). Lightweight files can be committed, heavy ones gitignored.

## Subtask 1.4.1.1 — Folder tree

```text
aitu-backend/data/
  audio/                  # raw audio working area, one uuid folder per input
    <uuid>/
      metadata.json       # file name alias, source (upload|recording|youtube), format
      original.<ext>
  playground/
    <artist_slug>/<track_slug>/
      metadata_track.json
      v1_gsc/
        metadata.json
        piano_matrix_v1_gsc.npz
  library/
    tracks/<artist_slug>/<track_slug>/
      metadata_library_track.json
      piano_matrix_<...>.npz
    playlists/<playlist_slug>/
      metadata_library_playlist.json
```

If storage is ever containerized this maps 1:1 to a MinIO bucket; not now.

## Subtask 1.4.1.2 — Matrix file format decision

Sparse matrices persist as `scipy.sparse` COO saved with `scipy.sparse.save_npz` (compressed `.npz`, int8 data). Rationale: tiny on disk, one-line load, trivially densified via `.toarray()`, native to the numpy/scipy stack already in the lockfile. Never persist dense grids; dense exists only transiently for JSON download/upload.

## Subtask 1.4.1.3 — Path helpers and gitignore

- `storage/paths.py`: functions for every path above (`audio_dir(uuid)`, `playground_version_dir(artist, track, version, gran)`, …). No path literals elsewhere.
- Folders auto-created on app startup.
- Gitignore: `data/audio/**` and `*.npz` heavier than trivial; keep `metadata*.json` and small example artifacts committed.

## Acceptance

Startup creates the tree; unit test exercises every path helper.
