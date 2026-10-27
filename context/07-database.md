# Database

**Everything the app knows is in one folder, `.database/`, and nothing else is needed to run it**
(implementation 02, plan section 8). A person who clones the repository, unpacks a `.database/`
backup at its root (or into the folder `AITU_DATABASE_DIR` names) and runs `make up` has every user,
song, project and audio file. The code writes nothing anywhere else.

By default `.database/` sits at the root of the repository and is ignored by git.
`AITU_DATABASE_DIR` moves it. On the Ubuntu machine it is **not inside the repository**: `.env` sets
`AITU_DATABASE_DIR=/mnt/ssd2/aimpromptu/.database` (the large SSD), and the backend container mounts
that folder at `/database`. Phase 3 used a symbolic link named `.database` in the repository; the
user removed it on 2026-10-06, because the editor followed the link and watched every file of the
database. Every path in the folder is built by one module, `aitu_backend/storage/paths.py`.

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
  requests/<projectId>/          the copy of a project a request sent (Phase 14): read by its
                                 author and the master user, written by nobody
  tmp/<userId>/<partId>/video/   temporary files of a user: a video, its frames, its reading
  lab/frame-examples/            the video reader's example records (Lab)
  history/<projectId>/           earlier states: parts/<partId>/v<N>/ before a splice or a new
                                 transcription replaced them; v<N>/ of a Private Library project
                                 before **Replace the version** or a restore replaced it (Phase 6)
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
    sheet.json                   what the reader decided on the old piano sheet (vexflow-v2); since implementation
                                 03, Phase 9, its marks the new sheet keeps are in sheet.f1 (part_sheet/legacy.py);
                                 nothing writes a new one since Phase 10 (2026-10-27), which removed the old sheet
    sheet.f1                     the new piano sheet: F1 frames text and a record of how it was written
                                 (Sonnet or the algorithm, implementation 03, Phase 5; since Phase 7 also edited by
                                 the user, and the stretches the AI wrote again); the hands stay in notes.pmn
    sheet.pending                a new transcription asks Sonnet to write the sheet (removed when it starts)
    sheet.edits.json             the steps of undo and redo of the new sheet (implementation 03, Phase 6): each
                                 note's hand before and after, the notes taken off the page (Phase 7), the lines of
                                 sheet.f1 changed; not copied with the part
    timeline.json                the audio timeline: which stored files, which ranges, in order
  cache/<partId>/                derived, safe to delete: normalized.wav, waveform.json,
                                 piece-r<N>.flac/.wav (the joined audio of a part with cuts),
                                 listen-<stored name>.flac (the lossless copy a compressed file plays as)
```

A normal project has one **part**. An integrated playlist (Phase 10) has one per sub-song: **From
other projects** starts a part at each subheader, and a part can be split, joined, renamed and moved
([frontend/playlists.md](frontend/playlists.md)). The uuid
of the routes of implementation 08 (`/audio/{uuid}`, `/pieces/{uuid}`, and `/sheet/{uuid}` since implementation 03) is the id of
a part, and a project made by this app has the id of its first part. So the routes did not change
when the storage did ([backend/pieces-and-revisions.md](backend/pieces-and-revisions.md)).

Full tree, file by file, and every table:
[`../documentation/services/backend/paths-and-data.md`](../documentation/services/backend/paths-and-data.md).

## The rules

**Only what cannot be recreated is stored**, as before. `notes.pmn` is the engine's notes in
milliseconds, before any grid was involved. The matrix at any `frameMs` and the hand split are a
function of it and are rebuilt on request. The sheet is the exception: `sheet.f1` is stored,
because writing it costs an AI run and it holds what a person chose; a sheet written for older notes
is laid again on the current ones when it is drawn, so it never disagrees with them. (Until
implementation 03, Phase 10 the old sheet was rebuilt on every request, and only `sheet.json`, what
a person chose, was stored.) The
files in `cache/` are derived and are written again when they are missing.

**An audio file is stored once and never changes** (plan P-3). A duplicated project, a pasted
passage (Phase 8) or a project pulled from the Public Library points at the same file, so no audio
bytes are copied. An edit that makes new audio (a re-recorded passage, a passage put in) adds a new
file and points the timeline at it. The table `audio_refs` counts which project uses which file; a
file is deleted only when no project uses it, and nothing deletes one from the Personal Vault.

**The cuts are a timeline.** Since implementation 08 a cut is a range removed from the audio. It is
now the gap between two **segments** of the part's timeline (one stored file, several ranges of
it), with the `audioRevision` beside them. **Add audio** (Phase 5) puts another file at the end:
the timeline then lists its files in order (`sources`), the Audio step shows them end to end, and a
cut may cross the join. A pasted passage (Phase 8) is one more entry of that list: a range of
another stored file, put in where it was pasted (a file it lands inside comes twice, once on each
side of it), so a paste copies no audio. When a project is saved to the Private Library (Phase 6), each file it
uses only in part is written again with only the ranges in use (a new FLAC file of the kept ranges;
the timeline then has no cut, and nothing the user hears or reads moves), and the old file is
deleted once no project uses it (Q-3). In the Personal Vault nothing is deleted, so every cut can
be undone.

**A project moves as one file.** **Export** writes `<title>.aitu`: a zip of the bundle (without
its cache, staging, history or video) and the audio files it uses. **Import** makes a new project
in the importer's Personal Vault from it, checking every audio file against the hash in its name.
The format: [`paths-and-data.md`](../documentation/services/backend/paths-and-data.md) section 2.5.

**Every user's projects are under their own folder**, and every query is scoped by owner: a
request acts as the user of its session (Phase 4, [08-security.md](08-security.md)).

**Saving to the Private Library moves the bundle** from `users/<id>/vault/` to
`users/<id>/library/` with the same ids (Phase 6), deletes its temporary files (the video, the edit
sessions, the history of its parts) and files it under a song as a version (`private_versions`). A
library project is never written in place: **Edit** copies it into the vault (`basedOn` pointing
at it), and **Replace the version** writes the copy's files into it, keeping its ids, after keeping
its previous state in `history/<projectId>/v<N>/`
([music-library/private-library.md](music-library/private-library.md)). The master user
is made on the first start from `AITU_MASTER_USERNAME` (default `master`).

## Versions

Two different axes, and they are easy to confuse.

| | Means | Where |
|---|---|---|
| `music-version.json` + `history/<projectId>/parts/<partId>/v<N>/` | **The music changed**: a splice was accepted, or a new transcription replaced the notes. A snapshot keeps `notes.pmn`, `sheet.json`, `sheet.f1` and `timeline.json`; the audio it names stays in the store | The part's folder; `.database/history/` |
| `audioRevision`, `notesRevision`, `handsRevision` | **One step changed**, so the later steps may be stale | `timeline.json`, the `notes.pmn` header, the record of `sheet.f1` |
| `alembic_version` | The tables changed shape | `aitu.sqlite` |

`projects.step` (the step a project reached, for the Projects page) is not a version: it is a copy
of what the bundles say, cleared when a part's notes, sheet or timeline is written and worked out
again by the next list (Phase 5). Its check constraint still allows `hands`, the step implementation
03 removed; no row holds it, and no migration was made for it.

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
section 8.6, so the later phases fill tables. Revision `0002` (Phase 9) lets a project be a
`passage`: a passage being re-recorded, or one of its takes, kept as a hidden project of the
Personal Vault ([backend/editing.md](backend/editing.md)). Revision `0003` (Phase 12) adds what the
downloaded music library gives and section 8.6 had no place for: the lyrics of a song, the artists,
release date, chart history and popularity of an album
([music-library/reconciliation.md](music-library/reconciliation.md)). Revision `0004` (Phase 14)
lets a project be in the layer `request` (the copy a request sends) and a request be of the kind
`playlist` ([music-library/requests.md](music-library/requests.md)); the real database moved to it
on 2026-10-16, after `make db-backup`. Revision `0005` (2026-10-18) gives a request a conversation
like a pull request's: a comment's kind, its item, the comment it replies to, and its stretch of
the sheet (`request_comments`); the real database moved to it after `make db-backup`. Revision `0006`
(Phase 16) adds the regions `spain` and `catalan`, a song's popularity in each of them
(`song_region_popularity`, with what it rests on), and more than one key per public song or artist
(`song_keys`, `artist_keys`: one per regional source that names it)
([music-library/regional-sources.md](music-library/regional-sources.md)); the real database moved
to it on 2026-10-19, after `make db-backup`. Revision `0007` (Phase 17) adds `song_signals` (a
public song's official video, its views and its Spotify streams, with the day they were read) and a
fourth basis of a regional popularity, `inferred`, with the day it was worked out
([music-library/popularity.md](music-library/popularity.md) section 6).

**The running backend migrates the real database as soon as a new revision is in `src/`**: it
reloads on every change of a file there, and opens the database at the newest revision. Code of an
older branch then refuses that database (Alembic cannot find the newer revision), until the branch
with the revision is merged, or the database is brought back with `alembic downgrade`.

The pieces of the old store (`aitu-backend/data/audio/<uuid>/`) were moved once, in Phase 3, by
`scripts/migrate/to_database.py`, every note checked against the old file. The user deleted the old
store after checking the app, and Phase 15 removed the script; nothing reads `aitu-backend/data/`
any more.

## Backup, restore, check

| Command | Does |
|---|---|
| `make db-backup` | `.database-YYYYMMDD-HHMMSS.tar.zst` beside `.database/` (on this machine in `/mnt/ssd2/aimpromptu/`); SQLite's own backup first, so a running app gives a consistent copy |
| `make db-restore FILE=…` | unpacks a backup into an empty `.database/` |
| `make db-check` | the tables against the bundles and the audio store (`HASHES=1` also hashes every audio file) |
| `make db-reindex` | writes the rows of the projects, parts and audio files again from what is on disk |

In the cloud, `.database/` becomes the volume attached to the instance, or the tables move to
Postgres (plan section 8.7).

## Where to look deeper

- Path by path, table by table: [`../documentation/services/backend/paths-and-data.md`](../documentation/services/backend/paths-and-data.md)
- The notes file: [backend/piano-matrix-notation.md](backend/piano-matrix-notation.md)
- Parts, revisions and staleness: [backend/pieces-and-revisions.md](backend/pieces-and-revisions.md)
- The old `sheet.json` field by field: [`../documentation/services/backend/rhythm-and-annotations.md`](../documentation/services/backend/rhythm-and-annotations.md)
- Why so little is stored: [backend/time-model.md](backend/time-model.md)
- The plan of the storage: [implementations/02-private-web-app/02-plan.md](implementations/02-private-web-app/02-plan.md) section 8
