# `data/` — local file store

There is no database. Everything the backend persists lives here, created on app
startup by `aitu_backend.storage.paths.ensure_data_tree()`.

```text
data/
  example-scores.json                       seed for GET /scores
  audio/<uuid>/
    metadata.json                           alias, source, format, duration
    original.<ext>                          the ffmpeg-normalized audio
  playground/<artist_slug>/<track_slug>/
    metadata_track.json                     names, slugs, version history
    v1_gsc/
      metadata.json                         everything needed to re-render this state
      piano_matrix_v1_gsc.npz               scipy.sparse COO, int8
  library/
    tracks/<artist_slug>/<track_slug>/
      metadata_library_track.json           tags, promotions, rollback pointer
      piano_matrix_<...>.npz
    playlists/<playlist_slug>/
      metadata_library_playlist.json
  examples/                                 small committed sample artifacts
```

Folder names come from `schemas/naming.py` (`slugify`, `version_folder`,
`matrix_filename`); paths come from `storage/paths.py`. Nothing else builds a path.

## What is committed

`metadata*.json` files are small and worth versioning, so they are **not** ignored.
Payloads are heavy and reproducible, so they are: `data/audio/**` and every `.npz`
except those under `data/examples/`. See the root `.gitignore`.

## Matrix file format

`scipy.sparse.save_npz` with a COO matrix of `int8`, shape **88 x N** (row = key,
col = time frame). Stored values are the cell values: `1` onset, `-1` sustain,
absent = silence. Dense grids are never persisted — dense exists only transiently
for JSON export and import. See `storage/matrix_store.py`.

If this ever gets containerized, the tree maps 1:1 onto a MinIO bucket. Not now.
