# `data/`: the old file store

Until implementation 02, Phase 3, everything the backend stored was in this folder, as plain files
with no database. Since Phase 3 the app stores everything in `.database/` at the repository root (a
SQLite database, the project bundles and the audio store; see
[context/07-database.md](../../context/07-database.md)). **The app reads and writes nothing here.**

The only code that reads this folder is the migration, `scripts/migrate/to_database.py` (from the
repository root), which copies each piece into `.database/` and never writes here. `AITU_DATA_DIR`
points it at another folder.

## What is here

```text
data/
  audio/<uuid>/                 one piece per uuid
    metadata.json               alias, source, format, duration, and the cuts when there are any
    original.<ext>              the file the user gave
    normalized.wav              16 kHz mono, the engine's input
    waveform.json, piece-r<N>.flac/.wav   derived, when present
    matrices/events.json        the notes (now parts/<partId>/notes.pmn)
    matrices/rhythm.json        the saved reading (now parts/<partId>/sheet.json)
    history/vN/                 earlier states (now .database/history/<projectId>/parts/<partId>/vN/)
    video/                      a Synthesia video and its reading (now .database/tmp/<userId>/<partId>/video/)
  frame-examples/*.json         the Lab records, committed (now .database/lab/frame-examples/)
  playground/, library/         the old Piano Library (.npz matrices, promotions, playlists),
                                empty; its code was deleted in Phase 3
```

The migration makes one project with one part per `audio/<uuid>/`, and the part keeps the uuid as
its id, so every link to a piece still works. `metadata.json` becomes `project.json` and
`timeline.json`, and the audio file goes to `.database/audio/<sha256>.<ext>`.

## When it goes

The user deletes this folder after checking the app on `.database/` (a human step at the end of
Phase 3). Phase 15 removes the code that reads it (`paths.data_dir`, the migration).
