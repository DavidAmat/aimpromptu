# Task 5.1.1 — Playground artifact repository

`storage/repository.py` + `api/library.py` (playground half): versioned storage of piano matrices.

## Subtask 5.1.1.1 — Save

`save_version(artist, track, matrix, comment, overwrite=False)`:

- resolve/create `playground/<artist_slug>/<track_slug>/`
- folder `vN_gX` from next version number + granularity code; `overwrite=True` rewrites the existing `vN_gX` instead
- write `piano_matrix_vN_gX.npz` + `metadata.json` (BPM, granularity, processing step, parent matrix pointer, annotations block)
- append to `metadata_track.json` history with the user comment ("what changed and why")
- the same version may exist at several granularities (`v1_gsc`, `v1_gn`) — same musical content, different collapse

## Subtask 5.1.1.2 — Load and list

- `list_tracks()`, `list_versions(artist, track)` (from `metadata_track.json`), `load_version(...) -> PianoMatrix + metadata`
- search by real `artistName`/`trackName`, not slug

## Subtask 5.1.1.3 — Edit lineage

Edits apply to the matrix being iterated on, never to the source base matrix. Saving an edited matrix records `parentMatrix`; going "back to original" means loading the parent, not undoing.

## Subtask 5.1.1.4 — Endpoints

REST for save (with overwrite/new-version flag + comment), list, load, rename alias, edit track metadata.

## Acceptance

Scenario test mirroring the `avicii/levels` example tree from `project-features.md` (v1_gsc, v1_gn, v2_gn).
