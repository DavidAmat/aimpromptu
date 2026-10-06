# Database

**Everything the app knows is in one folder, `.database/`, and nothing else is needed to run it**
(implementation 02, plan section 8). A person who clones the repository, unpacks a `.database/`
backup at its root and runs `make up` has every user, song, project and audio file. The code writes
nothing anywhere else.

`.database/` sits at the root of the repository and is ignored by git. `AITU_DATABASE_DIR` moves it.
On the Ubuntu machine it is a symbolic link to `/mnt/ssd2/aimpromptu/.database` (the large SSD), and
the backend container mounts that folder at `/database`. Every path in it is built by one module,
`aitu_backend/storage/paths.py`.

## What is stored

```text
.database/
  aitu.sqlite                    every record: users, projects and parts, audio files, the music
                                 library, versions, playlists, likes, requests (SQLite, WAL mode)
  VERSION                        the layout version (1); the app refuses a layout it does not know
  audio/<sha256>.<ext>           every audio file once, named by its content, never changed
  users/<userId>/
    vault/<projectId>/           layer 1: the Personal Vault, work in progress
    library/<projectId>/         layer 2: the Private Library
  public/<projectId>/            layer 3: the Public Library
  tmp/<userId>/<partId>/video/   temporary files of a user: a video, its frames, its reading
  lab/frame-examples/            the video reader's example records (Lab)
  history/<projectId>/           earlier states: parts/<partId>/v<N>/ before a splice or a new
                                 transcription replaced them
  jobs/                          reserved
```

**The bundles hold the music; the tables hold who owns what.** A project is a folder, the
**project bundle**, with the same layout in the three layers and in an export:

```text
<projectId>/
  project.json                   title, kind, owner, frameMs, origin, the parts in order and the
                                 source of each part's audio
  parts/<partId>/
    notes.pmn                    THE NOTES: the piano matrix notation of the part
    sheet.json                   what the reader decided on the piano sheet
    timeline.json                the audio timeline: which stored files, which ranges, in order
  staging/<sessionId>/           disposable edit sessions
  cache/<partId>/                derived, safe to delete: normalized.wav, waveform.json,
                                 piece-r<N>.flac/.wav (the joined audio of a part with cuts)
```

A normal project has one **part**. An integrated playlist (Phase 10) has one per sub-song. The uuid
of the routes of implementation 08 (`/audio/{uuid}`, `/pieces/{uuid}`, `/time/{uuid}`) is the id of
a part, and a project made by this app has the id of its first part. So the routes did not change
when the storage did ([backend/pieces-and-revisions.md](backend/pieces-and-revisions.md)).

Full tree, file by file, and every table:
[`../documentation/services/backend/paths-and-data.md`](../documentation/services/backend/paths-and-data.md).

## The rules

**Only what cannot be recreated is stored**, as before. `notes.pmn` is the engine's notes in
milliseconds, before any grid was involved. Everything else about the music (the matrix at any
`frameMs`, the gap distribution, the figures, the sheet) is a function of it and is rebuilt on
every request, so there is no state on disk that can disagree with what the screen shows.
`sheet.json` is the exception for the same reason inverted: it holds what a person chose. The
files in `cache/` are derived and are written again when they are missing.

**An audio file is stored once and never changes** (plan P-3). A duplicated project, a pasted
passage (Phase 8) or a project pulled from the Public Library points at the same file, so no audio
bytes are copied. An edit that makes new audio (a re-recorded passage, a passage put in) adds a new
file and points the timeline at it. The table `audio_refs` counts which project uses which file; a
file is deleted only when no project uses it, and nothing deletes one from the Personal Vault.

**The cuts are a timeline.** Since implementation 08 a cut is a range removed from the audio. It is
now the gap between two **segments** of the part's timeline (one stored file, several ranges of
it), with the `audioRevision` beside them. When a project is saved to the Private Library
(Phase 6), the audio is written again with only the ranges in use (Q-3).

**Every user's projects are under their own folder**, and every query is scoped by owner. Until the
login exists (Phase 4) every request acts as the master user, who is made on the first start from
`AITU_MASTER_USERNAME` (default `master`).

## Versions

Two different axes, and they are easy to confuse.

| | Means | Where |
|---|---|---|
| `music-version.json` + `history/<projectId>/parts/<partId>/v<N>/` | **The music changed**: a splice was accepted, or a new transcription replaced the notes. A snapshot keeps `notes.pmn`, `sheet.json` and `timeline.json`; the audio it names stays in the store | The part's folder; `.database/history/` |
| `audioRevision`, `notesRevision`, `handsRevision` | **One step changed**, so the later steps may be stale | `timeline.json`, the `notes.pmn` header, `sheet.json` |
| `alembic_version` | The tables changed shape | `aitu.sqlite` |

## Formats

- `notes.pmn` is the portable `.pmn` file, version 2: the columns of implementation 08 plus the
  revisions and the removed notes ([backend/piano-matrix-notation.md](backend/piano-matrix-notation.md)).
- Everything else in a bundle is JSON, camelCase, validated by Pydantic models.
- The tables are SQLAlchemy 2 models (`aitu_backend/db/models.py`), so the same code can move to
  Postgres in the cloud (plan P-2).
- Audio is stored as it arrived (`mp3`, `wav` ...); `normalized.wav` (16 kHz mono) is the engine's
  copy, in the cache.

## Migrations

The tables change only through Alembic revisions in `aitu_backend/db/migrations/versions/`. The app
brings the database to the newest revision when it starts. Revision `0001` makes every table of plan
section 8.6, so the later phases fill tables instead of adding revisions.

The pieces of the old store (`aitu-backend/data/audio/<uuid>/`) were moved once, in Phase 3, by
`scripts/migrate/to_database.py`: every note checked against the old file, safe to run twice, never
writing into the old store. Only that script reads `aitu-backend/data/`, which the user deletes
after checking the app; Phase 15 removes the code.

## Backup, restore, check

| Command | Does |
|---|---|
| `make db-backup` | `.database-YYYYMMDD-HHMMSS.tar.zst` beside `.database/`; SQLite's own backup first, so a running app gives a consistent copy |
| `make db-restore FILE=…` | unpacks a backup into an empty `.database/` |
| `make db-check` | the tables against the bundles and the audio store (`HASHES=1` also hashes every audio file) |
| `make db-reindex` | writes the rows of the projects, parts and audio files again from what is on disk |

In the cloud, `.database/` becomes the volume attached to the instance, or the tables move to
Postgres (plan section 8.7).

## Where to look deeper

- Path by path, table by table: [`../documentation/services/backend/paths-and-data.md`](../documentation/services/backend/paths-and-data.md)
- The notes file: [backend/piano-matrix-notation.md](backend/piano-matrix-notation.md)
- Parts, revisions and staleness: [backend/pieces-and-revisions.md](backend/pieces-and-revisions.md)
- `sheet.json` field by field: [`../documentation/services/backend/rhythm-and-annotations.md`](../documentation/services/backend/rhythm-and-annotations.md)
- Why so little is stored: [backend/time-model.md](backend/time-model.md)
- The plan of the storage: [implementations/02-private-web-app/02-plan.md](implementations/02-private-web-app/02-plan.md) section 8
