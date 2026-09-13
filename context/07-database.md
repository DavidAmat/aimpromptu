# Database

**There is no database.** All persistence is the local filesystem under `aitu-backend/data/`, and
every path is built in one module, `storage/paths.py`. No path string lives outside it.

## What is stored

```text
data/
  audio/<uuid>/                     one folder per ingested recording
    metadata.json  original.<ext>  normalized.wav  waveform.json
    matrices/
      events.json                   THE TRANSCRIPTION, in seconds. Kept forever.
      rhythm.json                   what the reader decided
      music-version.json            the current musical version
    staging/<session>/              disposable edit sessions
    history/v<N>/                   a musical state, before it was replaced
  playground/<artist>/<track>/v2_f40/    versioned work
  library/tracks/…  library/playlists/…  what a performer plays from
  example-scores.json               seed data for the text-notation MVP
```

Full tree, file by file:
[`../documentation/services/backend/paths-and-data.md`](../documentation/services/backend/paths-and-data.md).

## The one rule

**Only what cannot be recreated is stored.**

`events.json` is the engine's note events in seconds, before any grid was involved. Everything else
about the music — the matrix, the gap distribution, the figure of every note, the sheet — is a
function of it and is rebuilt on every request.

That is why the column length is a query parameter rather than a migration: reading the same piece
at 20 ms instead of 40 is another request, not another stored artifact, and **there is no state on
disk that can disagree with what the screen shows**.

`rhythm.json` is the exception, and for the same reason inverted: it holds the only things about a
piece that nothing can derive, because a person chose them. One per piece — a second reading
replaces the first.

## Versions

Two different axes, and they are easy to confuse.

| | Means | Where |
|---|---|---|
| `music-version.json` + `history/v<N>/` | **The music changed** — a splice was accepted | Beside `events.json` |
| `v<N>_f<frameMs>` playground folders | A saved state, at a given column length | `data/playground/…` |

The folder suffix exists because the same recording at 20 ms and at 40 ms is the same playing on a
finer or a coarser grid — the same distinction that used to be `v1_gsc` against `v1_gn`. Dropping it
would make two views of one state collide on one folder name.

## Formats

- Matrices are `scipy.sparse` COO int8 saved as compressed `.npz`; the dense form is transient.
  Hands are separate files.
- Everything else is JSON, camelCase, validated by Pydantic models in `schemas/`.
- Audio is normalised to `.wav` by ffmpeg; the original is kept beside it.

## Migration policy

No DDL and no migrations. One script exists, `scripts/migrate_to_time_matrix.py`, for the 1.x to 2.0
change — and its important behaviour is what it **refuses** to do: a piece with no recorded events
to rebuild from is flagged with `needs-rederivation.json` and surfaced, never converted. A grid
written under one set of assumptions and read under another puts every note at the wrong time, so a
warning the reader can see is the only honest answer.

## If this is ever containerised

The tree maps one-to-one onto an object-store bucket. `ensure_data_tree()` is the only thing that
creates directories, and it runs at app startup.

## Where to look deeper

- Path by path: [`../documentation/services/backend/paths-and-data.md`](../documentation/services/backend/paths-and-data.md)
- `rhythm.json` field by field: [`../documentation/services/backend/rhythm-and-annotations.md`](../documentation/services/backend/rhythm-and-annotations.md)
- Why so little is stored: [backend/time-model.md](backend/time-model.md)
