# Epic 5 — Artifacts and versioning

The persistence layer for musical work: the playground repository (artist/track slugs, version+granularity folders, track history) and promotion into the library with rollback. Built right after transcription so every UI epic saves through it from day one.

Read first: `project-features.md` sections "Folder Structure for storage" and "Metadata"; Task 1.3.2 schemas; Task 1.4.1 layout.

## Story 5.1 — Playground repository

- Task 5.1.1 artifact repository: save/load piano matrices as `vN_gX` folders with `metadata.json`, maintain `metadata_track.json` history with comments, overwrite-vs-new-version decision, parent-matrix tracking.

## Story 5.2 — Promotion to library

- Task 5.2.1 library promotion: promotion dialog flow, editable promotion version names, multiple concurrent promoted versions, `metadata_library_track.json` history and rollback.

## Exit criteria

From any Playground tab a matrix state can be saved as a version, listed, reloaded, and promoted to the library; history survives restarts and rollback restores the previous promoted version.
