> Context: [context/07-database.md](../../../context/07-database.md) ·
> [context/backend/api.md](../../../context/backend/api.md) ·
> [context/backend/piano-matrix-notation.md](../../../context/backend/piano-matrix-notation.md)

# Storage layout: every path, every file, every table

Everything the app knows is in `.database/` (implementation 02, plan section 8): one SQLite file for
the records and folders beside it for the audio and the project bundles. The folder is
`.database/` at the root of the repository unless `AITU_DATABASE_DIR` names another one
(`aitu_backend/config.py`); on the Ubuntu machine `.env` names `/mnt/ssd2/aimpromptu/.database` (§7). Every path is built in one module,
`aitu-backend/src/aitu_backend/storage/paths.py`; its module docstring repeats the tree below.

`aitu-backend/data/` is the store before Phase 3. Only the migration (§9) reads it.

---

## 1. The tree

```text
.database/                                   or the folder AITU_DATABASE_DIR names
  aitu.sqlite (+ -wal, -shm)                 every record (§6), WAL mode
  VERSION                                    the layout version: 1
  audio/<sha256>.<ext>                       every audio file, once, never changed (§3)
  users/<userId>/
    vault/<projectId>/                       layer 1: the Personal Vault
    library/<projectId>/                     layer 2: the Private Library
  public/<projectId>/                        layer 3: the Public Library
  tmp/<userId>/<partId>/video/               the video of a part (§5)
  lab/frame-examples/<slug>.json             the Lab records; cache/<slug>.jpg derived
  history/<projectId>/parts/<partId>/v<N>/   earlier states of a part (§4.5)
  history/<projectId>/v<N>/                  earlier states of a Private Library project (§4.7)
  jobs/                                      reserved for job records
```

`ensure_database_tree()` makes the top folders when the app starts, after `database.engine()` has
made the folder, written or checked `VERSION`, and brought the tables to the newest Alembic revision
(`aitu_backend/db/database.py`). A `VERSION` this code does not know stops the app
(`LayoutVersionMismatch`).

---

## 2. The project bundle

```text
<projectId>/                                 under users/<id>/vault/, users/<id>/library/ or public/
  project.json                               §2.1
  parts/<partId>/
    notes.pmn                                THE NOTES of the part (§2.3). Kept forever.
    sheet.json                               the reader's decisions (§2.4)
    timeline.json                            the audio timeline (§2.2)
    music-version.json                       the number of the next history snapshot (§4.5)
    audio-mismatches.json                    windows where the recording no longer matches (§4.6)
    needs-rederivation.json                  only on a piece nothing could rebuild (pre-08)
  staging/<sessionId>/                       disposable edit sessions (§4.4)
  cache/<partId>/                            derived, safe to delete (§4.1)
    normalized.wav  waveform.json  piece-r<N>.flac  piece-r<N>.wav  scratch clips
    src-<sha256>.wav  sources-<key>.flac     only for a part of several files (§2.2)
```

A normal project has one part. **A project made by this app has the id of its first part**, so a
project of one part has one uuid, which is also the uuid of the routes of implementation 08
(`/audio/{uuid}`, `/pieces/{uuid}`, `/time/{uuid}`, `/matrix/{uuid}`). Those routes take the id of
a part (plan P-6). `storage/locate.py` finds the project, the owner and the layer of a part in the
`parts` and `projects` tables and keeps the answer in memory.

The functions that read and write a bundle are in `storage/bundle.py`: `create_project`,
`read_project` / `write_project` (which keeps the `projects` row in step), `read_timeline` /
`write_timeline` (which updates `audio_refs` and clears the stored step), `new_bundle_from`,
`duplicate_project`, `delete_project`, `list_parts`, `sync_audio_refs`, `step_changed`,
`last_change`. The `.aitu` export and import are in `storage/exchange.py` (§2.5). `audio/store.py` keeps the functions every older reader calls
(`get`, `read_metadata`, `update`, `set_cuts`, `rename`, `delete` ...) on top of them.

### 2.1 `project.json`

```json
{"schemaVersion": 1, "id": "538ae69c-…", "kind": "song", "title": "Come on Eileen",
 "subtitle": null, "artistText": null, "ownerId": 1, "frameMs": null,
 "origin": null, "basedOn": null,
 "createdAt": "2026-09-29T20:52:57.840070Z", "updatedAt": "2026-09-29T21:31:18.825003Z",
 "revision": 1,
 "parts": [{"id": "538ae69c-…", "subheader": null,
            "source": {"kind": "youtube", "format": "mp3",
                       "originalFilename": "Come On Eileen (Dexys Midnight Runners) - Piano Tutorial.mp3",
                       "durationSeconds": 263.500063, "sampleRate": 16000,
                       "url": "https://www.youtube.com/watch?v=PBWn6J1MSLY",
                       "sourceAudioUuid": null, "sourceTimeRange": null}}]}
```

| Field | Meaning |
|---|---|
| `kind` | `song` or `integratedPlaylist` (Phase 10) |
| `title` | The project's name; what the API calls `alias` |
| `subtitle`, `artistText` | The project's own lines (Phase 5); the sheet's printed title block is in `sheet.json` |
| `frameMs` | The column length a project made from scratch is meant to be read at (a view, D-01) |
| `origin` | What it was made from: `{"duplicateOf": id}`, `{"importedFrom": id}`, later the passages of From other projects |
| `basedOn` | The library project a vault project edits (plan section 10.6) |
| `parts[].subheader` | The title between the parts of an integrated playlist |
| `parts[].source` | Where the part's audio came from: `kind` (`upload`, `recording`, `youtube`, `segment`, `composed`), the extension of the file, its original name, its length and rate after normalization, the YouTube link, the lineage of a segment. These describe the **first** file |
| `parts[].source.files` | Every file of the part's audio in the order of the axis (Phase 5): `audio` (the hash), `name` (what the Source step shows; the file's name or the video's title at first), `kind`, `format`, `originalFilename`, `durationSeconds`, `url`. Written once a file is added, named, moved or removed; absent before, when the one file is described by the fields above (`bundle.source_files`) |

**What the API answers.** `GET /audio/` and `GET /audio/{uuid}` still answer the
`AudioMetadata` shape of implementation 08: `alias` is `title`, the source fields come from
`parts[].source`, `cuts` and `audioRevision` from the timeline, `createdAt` and `frameMs` from the
project. `updatedAt` is the newest modification time of the part's files and of `project.json`.
The links of a project to a song, an artist and a version are **not** in the bundle: they are rows
of a library (§6), because the same bundle can sit in two libraries under two songs.

### 2.2 `timeline.json`: the audio timeline

```json
{"schemaVersion": 1, "audioRevision": 1,
 "audio": {"27687c72…": {"format": "mp3", "frames": 26351}},
 "segments": [{"audio": "27687c72…", "fromMs": 3160, "toMs": 260220}]}
```

The part plays its segments one after the other; the time of the notes is the time of that joined
audio. `audio` names each stored file the part uses, with its extension and its length in 10 ms
frames, so the timeline reads without the database and a cut that reaches the end of the file is
still a cut. `toMs` is `null` for a segment that runs to the end of a file not measured yet
(between an upload and its normalization). Every range is on the 10 ms grid.

**The cuts of implementation 08 are the gaps between the segments of one file.** Above, the cuts
`[[0, 316], [26022, 26351]]` (frames) are the two ranges before 3,160 ms and after 260,220 ms.
`bundle.segments_for_cuts` and `bundle.cuts_of` convert both ways. `audioRevision` rises by one each
time the cuts change (`store.set_cuts`) or a file is added. A part with no audio (composed, empty)
has `"audio": {}` and refuses a cut.

**Several files** (**add audio**, Phase 5, `POST /audio/{uuid}/add`):

```json
{"schemaVersion": 1, "audioRevision": 3,
 "audio": {"9f3c…": {"format": "mp3", "frames": 20000}, "b71a…": {"format": "wav", "frames": 900}},
 "sources": ["9f3c…", "b71a…"],
 "segments": [{"audio": "9f3c…", "fromMs": 0, "toMs": 199000, "source": 0},
              {"audio": "b71a…", "fromMs": 500, "toMs": 9000, "source": 1}]}
```

`sources` lists the files of the Audio step laid end to end, in order (the same file may come
twice). That is the **axis** the Audio step shows (frames 0 to 20,900 above), and a cut is a range
of it, as before: here the cut `[19900, 20050]` crosses the join. `bundle.segments_for_axis` splits
the kept ranges where a file ends; each segment's `source` is the place of its file in `sources`, so
`bundle.cuts_of` reads the cuts back even when a file comes twice. A part of one file has no
`sources` and no `source` on its segments, so every timeline written before Phase 5 reads unchanged.
A part of several files has no single original; two derived files of its cache stand in for it
(`audio/sources.py`): `normalized.wav` is each file's own 16 kHz copy (`src-<sha256>.wav`) padded
to whole frames and joined, and `sources-<key>.flac` is the files decoded at 44.1 kHz (48 kHz when a
file is above it) and joined, which the Audio step plays (`?original=true`) and the joined audio of
the cuts is cut from. Each join of two files gets the 5 ms fade of a cut.

`replace_original` gives a part a new stored file and points every segment at it, keeping the cuts.
The joined audio and the peaks of the old file are deleted from the cache then. A part of several
files becomes a part of one file again (`sources` and `files` are dropped).

**Changing the list of files** (the Source step, `store.rename_file`, `reorder_files`,
`remove_file`, routes `/audio/{uuid}/files`). A name changes only `project.json`. A new order
permutes `sources`, `files` and the segments grouped by file, so each file keeps its own cuts and
its kept ranges move with it. Removing a file drops its segments; the store deletes the file when no
project uses it any more, and a part left with one file becomes a part of one file again (its
source fields then describe that file). Both raise `audioRevision`, refuse a stale `baseRevision`,
and delete the joined files of the cache, which are written again.

### 2.3 `notes.pmn`

The portable `.pmn` file, version 2 (plan P-5): the columns of implementation 08 plus the header of
the old `events.json` and the removed notes. Field by field, and why it keeps microseconds:
[`context/backend/piano-matrix-notation.md`](../../../context/backend/piano-matrix-notation.md).
The code still works in the shape of `events.json` (a list of note rows in seconds) and converts at
the file boundary: `pmn/events_file.read_payload` and `write_payload`, with `pmn/notes_file.py`.

Every writer except a new transcription goes through `pipeline.save_edit`, under
`pipeline.piece_lock(uuid)`; a new transcription writes the header itself. An empty piece
(`POST /audio/compose`) is a `notes.pmn` with no notes and `durationMs: 0`, and no audio file.

### 2.4 `sheet.json`

What was `matrices/rhythm.json`: the reader's decisions, the only things about a piece that are not
derivable. Fields in [`rhythm-and-annotations.md`](rhythm-and-annotations.md). Phase 3 adds two
optional fields, both empty until Phase 7: `lyricsPool` (the pasted lyrics not placed yet, one line
per piece) and `figuresFrom` (the figure the next figures transposition starts from). It records
the `handsRevision` it was saved for; when the notes' header differs, the Sheet step is `stale`.

### 2.5 The `.aitu` file: export and import

`storage/exchange.py`, `GET /projects/{id}/export` and `POST /projects/import` (Phase 5, plan
section 8.3). A zip of the bundle and the audio it uses:

```text
<title>.aitu
  export.json                  {"format": "aimpromptu-project", "version": 1, "exportedAt", "projectId"}
  project.json                 as in the bundle
  parts/<partId>/notes.pmn     sheet.json  timeline.json   (byte for byte)
  audio/<sha256>.<ext>         every file a timeline names, stored without compression
```

No cache, no staging, no history, no video. The import makes a new project in the importer's
Personal Vault (`bundle.new_bundle_from`: new ids, the same title, `origin: {"importedFrom": id}`)
and writes the part files as they came. It refuses (`ImportRefused`, `422`) a file that is not a
zip or has no `export.json` of this format, a version newer than its own, more than 10,000 members
or 2 GB, a part file that does not read as what it is (`notes.pmn` as a `.pmn`, `sheet.json` as a
saved reading, `timeline.json` as a timeline whose cuts read back), and an audio file that is
missing or whose SHA-256 is not its name; a failure deletes what it made and the audio files no
project uses. Members are read only by the names it expects, so no name in the zip becomes a path.
`tests/test_projects.py` checks export, import and export again give the same part files and audio.

---

## 3. `audio/`: the audio store

`audio/<sha256>.<ext>`: every audio file once, named by the SHA-256 of its content
(`storage/audio_files.py`). A file never changes. An upload is streamed into the store and hashed
on the way (`add_stream`); a file on disk is copied (`add_file`). Two parts with the same bytes share
one file.

| Table | Row |
|---|---|
| `audio_files` | `hash`, `format` (the extension), `duration_ms` (when measured), `size_bytes`, `created_at` |
| `audio_refs` | `(project_id, hash)`: the project uses the file in a timeline of its parts or in a history snapshot |

`delete_unused(hashes)` deletes a file only when no `audio_refs` row names it. `delete_project`
calls it, and so does **Save to library** for the files it replaced (below); nothing else deletes
audio. The Personal Vault never deletes a file, so every cut can be undone.

**Writing the audio again on save** (Phase 6, Q-3, `audio/compact.py`). When a project is saved to
the Private Library, each file a part's timeline uses only in part becomes a new file of the store:
the old file decoded at its own rate and channels, its kept frames joined with the 5 ms fade of a
cut (`piece_audio.write_joined`, as `piece-r<N>.flac` is made), FLAC, `<sha256>.flac`. Its 16 kHz
copy is the old 16 kHz copy with the same frames joined, so the engine's audio is the one the notes
were made from to the sample. The timeline then points at each file from its start to its end (no
cut), its `audio` entry has the number of kept frames, and `audioRevision` does not change: the
notes stay current. A part of several files keeps its files, their order and their names
(`parts[].source.files` takes the new hashes); a file cut away completely leaves the list; a file
used whole is not touched. `prepare` writes the new files first and changes nothing, so a failure
leaves the project as it was; `apply` then points the part at them, and the replaced files are
deleted once `audio_refs` says no project uses them.

**Download name.** `GET /audio/{uuid}/file?original=true` serves the stored file under the name the
user knows (the original file name, or the title) with the stored extension.

---

## 4. Inside a part

### 4.1 `cache/<partId>/`: derived files

| File | Content | Written |
|---|---|---|
| `normalized.wav` | The stored file at 16 kHz mono: the engine's input. For a part of several files, their 16 kHz copies joined (§2.2) | By the ingest (`ingest.finalize`) or **add audio**; again by `store.get` when it is missing and the part was measured |
| `src-<sha256>.wav`, `sources-<key>.flac` | A part of several files only: each file's 16 kHz copy, and the files joined at one rate (§2.2) | By **add audio**, and on the first request after they were deleted |
| `waveform.json` | Peaks for the waveform view | On request; deleted when the cuts or the audio change |
| `piece-r<N>.flac` | With cuts: the stored file decoded at its own rate, kept ranges joined, lossless | `PUT /audio/{uuid}/cuts`, or on the first request (`audio/piece_audio.py`) |
| `piece-r<N>.wav` | With cuts: `normalized.wav` with the kept ranges joined | Same |
| `range_*.wav`, `transcribe_range.wav` | Scratch clips of `GET /audio/{uuid}/range` and of a range transcription | On request |

The joined audio is joined exactly as the engine's input is (`frames.join_kept`): a 5 ms fade out and
in at each join, inside the kept samples. `GET /audio/{uuid}/file` serves it for a part with cuts;
`?original=true` serves the stored file.

### 4.2 The ingest

Upload, browser recording and YouTube converge on `audio/ingest.py`: `store.create` makes a project
of one part in the current user's Personal Vault, `store.save_original` streams the bytes into the
audio store, and `finalize` writes `normalized.wav`, records the length in frames in the timeline
and the length and rate in `project.json`. A failure deletes the whole project. A trimmed
**segment** (`ingest.create_segment`) is its own project whose one file is the WAV of the range.

### 4.3 The transcription and the edits

Unchanged in what they do since implementation 08; only the files moved. A new transcription of a
part with notes first copies `notes.pmn` and `sheet.json` into history (`snapshot_notes`) and
deletes `sheet.json`, whose marks are column numbers over the old notes.

### 4.4 `staging/<sessionId>/`: disposable sessions

Epic 11 range editing and Epic 13 composing. **Nothing outside this folder changes until the reader
accepts**, and cancel deletes the folder and nothing else. The sessions of every part of a project
share the project's `staging/` (the session id is unique).

| File | What it is |
|---|---|
| `session.json` | The window or the moment, the placement, the speed, the trim, the part (`audioUuid`) |
| `upload.<ext>` | The take as it arrived from the browser |
| `untrimmed.wav` | The take, converted |
| `selected.wav`, `trimmed.wav` | What the reader kept of it |
| `scaled.wav` | The take stretched into the window |
| `take_events.json` | The take transcribed, **as played** |
| `window.wav`, `window_slow.wav` | The original window, and a pitch-preserved slow copy to play along with |

Accepting a passage that changes the recording (a splice, a passage put in) writes the new
`normalized.wav` and stores it as a **new file** of the audio store (`store.replace_original`);
the old file stays for the history. Detail in [`editing-and-compose.md`](editing-and-compose.md).

### 4.5 `music-version.json` and the history

Two events copy the **previous** state of a part into
`.database/history/<projectId>/parts/<partId>/v<N>/` and advance the counter in
`music-version.json`. They share the counter, so two snapshots never share a folder.

| When | Function (`editing/history.py`) | What is copied |
|---|---|---|
| Accepting a range edit or a composed passage | `snapshot_current` | `notes.pmn`, `sheet.json`, `timeline.json` |
| A new transcription of a part that already has notes | `snapshot_notes` | `notes.pmn`, `sheet.json`, and a `snapshot.json` with the reason |

No audio is copied: the snapshot's `timeline.json` names the stored files, and `audio_refs` counts
them as used by the project, so they are never deleted under it.

### 4.6 `audio-mismatches.json`

Windows where the recording no longer matches the sheet, after an audio splice failed. Recorded
rather than raised: the notes were written correctly and only the sound is behind.

### 4.7 A project of the Private Library, and `history/<projectId>/v<N>/`

`library/flow.py` (Phase 6, plan sections 8.5 and 10.6;
[`context/music-library/private-library.md`](../../../context/music-library/private-library.md)).

**Save to library** (`flow.save`) checks every part's Sheet step is `ready` and no job writes its
notes, writes the audio again (§3), moves the folder `users/<id>/vault/<projectId>/` to
`users/<id>/library/<projectId>/` (one rename: the same ids, the same bundle), sets
`projects.layer = 'private'`, and deletes the temporary files: `tmp/<userId>/<partId>/` (a video
and its frames), `staging/`, and `history/<projectId>/parts/` (whose timelines name the audio just
replaced). Then `audio_refs` is synced, the replaced files are deleted, and the song, its artist
name and a `private_versions` row are written.

**A library project is never written in place.** `flow.open_edit` copies it into the vault
(`bundle.duplicate_project`; `basedOn` and `origin: {"editOf": id}`), or answers the copy already
open. **Replace the version** (`flow.save(replace=True)`) writes the audio of the copy again,
keeps the library project's state in its history (`flow.snapshot`), writes the copy's
`project.json` fields and its parts' files into it (`_write_into`: the library project keeps its id
and the ids of its parts, by position; a missing part is added, an extra one removed), clears its
cache and the hand split cache of its parts, and deletes the copy.

```text
history/<projectId>/v<N>/
  project.json                 as it was
  snapshot.json                {"version": N, "savedAt": "...", "reason": "replaced" | "restored"}
  parts/<partId>/notes.pmn  sheet.json  timeline.json  (audio-mismatches.json, needs-rederivation.json)
```

`flow.restore(projectId, N)` keeps the current state as the next `v<N>` first, then writes `v<N>`'s
files back the same way. No audio is copied: the snapshot's timelines name stored files, which
`audio_refs` counts for the project (`bundle._history_hashes` reads every `timeline.json` under
`history/<projectId>/`). Deleting a version (`flow.delete_version`) deletes its project, its whole
history and the audio no other project uses; its edit copy becomes an ordinary vault project.

---

## 5. `tmp/<userId>/<partId>/video/`: a video

A video belongs to the part whose audio came out of it (V-03) and is a temporary file of its owner
(plan section 8.5). Only `video/store.py` reads and writes it.

| File | |
|---|---|
| `source.mp4` | The download, or the video file the user uploaded (Phase 5), whatever its container (V-01) |
| `metadata_video.json` | Size, length, frames per second, `sampleMs` |
| `calibration.json` | The piano overlay, what was measured from it, and `measuredFor` (the overlay that measurement was made with, so **Read notes** measures again only after a new fitting). **The user's work** |
| `corrections.json` | Notes a person took off or put on by hand. **The user's work** |
| `plate.npy`, `frames/f000001.jpg`, `frames.jsonl`, `detection-report.json`, `notes.json`, `detection/` | Derived: thrown away and written again |

---

## 6. `aitu.sqlite`: the tables

SQLAlchemy 2 models in `aitu_backend/db/models.py`, one Alembic revision so far
(`db/migrations/versions/0001_initial.py`, which also writes the fixed lists). SQLite runs with
foreign keys on and in WAL mode. Every table of plan section 8.6 exists from Phase 3; most stay
empty until their phase.

| Group | Tables | Filled from |
|---|---|---|
| Users | `users` (`id`, `username`, `password_hash`, `role`: `master` or `user`, `disabled`), `sessions` | The master user on the first start (`db/users.py`, `AITU_MASTER_USERNAME`); passwords and sessions in Phase 4 |
| Projects | `projects` (`id`, `owner_id`, `layer`: `vault`, `private`, `public`, `kind`, `title`, `based_on`, `public_source_id`, `created_at`, `updated_at`, `step`), `parts` (`id`, `project_id`, `position`), `audio_files`, `audio_refs` | Phase 3 |
| Music library | `artists`, `artist_names` (several per artist, one default), `albums`, `songs` (`title`, `year`, `popularity`, `default_version`), `song_artists` (a song points to an **artist name**), `song_albums`. Each row has `scope` (`private`, `public`), `owner_id`, `public_id`, and `external_key` for the import of Phase 12 | The migration (private rows of the seed list); **Save to library** and `/library` (Phase 6, `library/rows.py`: names compared ignoring case and spaces); Phases 12, 13 |
| Versions | `song_versions` (fixed versions of a public song), `user_versions` (`user_versions/<user>/<name>/`), `private_versions` (a private song's version: a free name, unique in the song ignoring case, and its project) | The migration (`original`); Phase 6; Phase 14 |
| Metadata of a public song | `genres` (13, fixed), `song_genres`, `tag_categories` (4, fixed), `tag_values`, `song_tags`, `regions` (`worldwide`), `song_regions`, `chart_sources`, `chart_entries` | Phases 12, 13 |
| Playlists | `playlists`, `playlist_items` | Phase 10 |
| Social | `likes`, `library_shares` | Phases 13, 14 |
| Requests | `requests`, `request_items` (one decision each), `request_comments` | Phase 14 |

Two tables are not in the list of section 8.6 and follow from it: `parts` (a part must find its
project, P-6) and `song_genres` (a song has one or two genres). `projects.step` is the lowest step
its parts reached. Phase 3 fills it in the migration and in `db-reindex`; since Phase 5 a write of a
part's notes, sheet or timeline clears it (`bundle.step_changed`) and `GET /projects` works it out
again for the cleared rows (`db/tools.refresh_step`).

---

## 7. Where the data lives: `AITU_DATABASE_DIR` and the containers

**Natively**, `paths.database_dir()` returns `AITU_DATABASE_DIR` when it is set and not empty,
otherwise `<repository>/.database`. On the Ubuntu machine the folder is not inside the repository:
`.env` sets `AITU_DATABASE_DIR=/mnt/ssd2/aimpromptu/.database`, and the folder was made once by hand:

    mkdir -p /mnt/ssd2/aimpromptu/.database

There is no `.database` link in the repository. Phase 3 made one, and the user removed it on
2026-10-06: the editor followed the link and watched every file of the database. The `Makefile`
reads `AITU_DATABASE_DIR` from `.env` and exports it, so `make up`, `make test-backend` and the
`make db-*` commands all use the same folder.

**In the containers** (`compose.yaml`, project name `aimpromptu`) the backend sees the folder at
`/database` (`AITU_DATABASE_DIR=/database` inside), and the host variable chooses which host folder
is mounted there (default `./.database`). `make up` and `make test-backend` make that folder first
if it is missing, because Docker would make it as root.

| Host | Container | Why |
|---|---|---|
| The repository (`.`) | `/work/aimpromptu` | The code is the host's, so uvicorn (`--reload --reload-dir src`) and Vite reload on every edit; the tests also read `pocs/`, `context/` and `scripts/` |
| `${AITU_DATABASE_DIR:-./.database}` (on this machine `/mnt/ssd2/aimpromptu/.database`, from `.env`) | `/database` | Every record and every file of the app |
| `${AITU_DATA_DIR:-./aitu-backend/data}` | `/work/aimpromptu/aitu-backend/data` | The old store, for the migration only |
| `${HF_HUB_CACHE:-/mnt/ssd2/hf/data/hub}` | `/hf/hub` (`HF_HUB_CACHE`) | The MuScriptor weights (5.5 GB for `large`) |
| `${AITU_CACHE_DIR:-/mnt/ssd2/aimpromptu/home}` | `/home/app` | The ByteDance checkpoint and the torch cache |
| `./aitu-frontend` | `/work/aimpromptu/aitu-frontend` | The frontend code; an anonymous volume keeps the image's `node_modules` |

Both containers run as the host user, so every file in `.database/` belongs to that user. The
backend's port binds to `127.0.0.1` only; the page's port binds to `WEB_BIND` (default `0.0.0.0`,
the home network, since Phase 4). Every variable is listed in `.env.example`.

**The tests** never touch the real folder: `tests/conftest.py` points `AITU_DATABASE_DIR` at a
temporary folder before any test module loads, and at a new one for every test, copied from one
database migrated once per run.

---

## 8. Backup, restore, check, reindex

`aitu_backend/db/tools.py`, run on the host by the Makefile (they need `tar` with zstd, which the
image does not have):

| Command | Does |
|---|---|
| `make db-backup` | `.database-YYYYMMDD-HHMMSS.tar.zst` (UTC) beside `.database/`. SQLite's backup command copies the database first, so a running app gives a consistent copy; the rest is copied as it is. A file the app writes during the copy makes tar warn, and the backup is kept |
| `make db-restore FILE=…` | Unpacks into an empty (or missing) `.database/` |
| `make db-check` | `VERSION` and the revision; a row for every bundle and a bundle for every row; the parts of `project.json` against the `parts` rows; every `notes.pmn` readable; every file of every timeline present, with its row; `audio_refs` against the bundles; files with no row and rows with no file. `HASHES=1` also hashes every audio file. Exit 1 on a problem |
| `make db-reindex` | Writes the `projects`, `parts`, `audio_files` and `audio_refs` rows again from what is on disk, and the step of each project |

Measured on the 39 migrated projects: the backup is 1.08 GB and takes about 3 s; a restore into a
new folder passes `db-check` with every hash.

---

## 9. The migration of `aitu-backend/data/`

`scripts/migrate/to_database.py` (plan section 8.9), run once in Phase 3:

    cd aitu-backend
    AITU_DATABASE_DIR=/tmp/aitu-trial uv run --no-sync python ../scripts/migrate/to_database.py \
        --report /tmp/aitu-trial-report.json        # on a throwaway folder first
    uv run --no-sync python ../scripts/migrate/to_database.py --report ../migration-report.json

For each `data/audio/<uuid>/`: a project of one part with the same id; the audio file into the
store; `metadata.json` into `project.json` and the timeline; `matrices/events.json` into
`notes.pmn`, checked note by note (every id, key, time, hand, flag, the header, the length and the
title read back equal, or the piece fails); `rhythm.json` into `sheet.json` unchanged; the cache
files; `history/v<N>/` with a timeline instead of a copy of the audio; the video into `tmp/`. A piece
of the seed list (`scripts/seed/youtube-library/seed-state.json` and `library.json`) goes to the
master user's Private Library under a private song and artist, version `original`; the others to
the Personal Vault. `data/frame-examples/*.json` goes to `lab/frame-examples/`. The new files keep
the modification times of the old ones, so "when it changed" on the Projects page is unchanged.

It never writes into `data/`, skips a piece whose project exists (safe to run twice), and deletes
the partial project of a piece that fails, which the report names with the reason.

---

## 10. Scripts that touch the store

`aitu-backend/scripts/`, run with `uv run --no-sync python scripts/<name>.py` from `aitu-backend/`
(the local `.database/`), or with `docker compose exec backend python scripts/<name>.py`:

| Script | What it does |
|---|---|
| `make_demo_pieces.py` | Writes two hand-built demo pieces (`11111111-…`, `22222222-…`), so the right answer is known before you open anything |
| `bench_pieces.py` | Times the piece routes on a temporary copy of each piece (`POST /projects/{id}/duplicate`, deleted at the end) |
| `bench_payloads.py`, `bench_device.py`, `bench_stream.py`, `check_saved_hands.py` | Measurements of implementation 08, now on parts |
| `benchmark_hands.py` | Hand-split quality against a reference |

The browser scripts of `aitu-frontend/scripts/` (`check:flow`, `bench:sheet`, `time:flow`) reach a
piece through the API only: they find it in `GET /audio/`, copy it with
`POST /projects/{id}/duplicate` and delete the copy with `DELETE /audio/{id}`.

---

## 11. Where to look deeper

- [`context/07-database.md`](../../../context/07-database.md): the rules, in short
- [`context/backend/piano-matrix-notation.md`](../../../context/backend/piano-matrix-notation.md):
  `notes.pmn` field by field, and the revision chain
- [`context/backend/pieces-and-revisions.md`](../../../context/backend/pieces-and-revisions.md):
  parts, steps and staleness
- [`rhythm-and-annotations.md`](rhythm-and-annotations.md): `sheet.json` field by field
- [`editing-and-compose.md`](editing-and-compose.md): staging, history and the splice
- [`transcription-pipeline.md`](transcription-pipeline.md): what writes `notes.pmn`
- [`endpoints.md`](endpoints.md): the routes that read and write all of it
