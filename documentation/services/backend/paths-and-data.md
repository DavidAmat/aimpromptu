> Context: [context/backend/api.md](../../../context/backend/api.md) ·
> [context/07-database.md](../../../context/07-database.md) ·
> [context/backend/piano-matrix-notation.md](../../../context/backend/piano-matrix-notation.md)

# Storage layout: every path and every file

There is no database. All persistence is the local filesystem under `aitu-backend/data/`, or under
the folder `AITU_DATA_DIR` names (`aitu_backend/config.py`). In the containers the variable chooses
which host folder is mounted at the default place (§7).

The roots and most paths are built in one module, `aitu-backend/src/aitu_backend/storage/paths.py`.
Three groups of file names live beside the code that owns them: the files of `matrices/`
(`events.json`, `rhythm.json`, `needs-rederivation.json`) in `transcription/pipeline.py`,
`normalized.wav` and `waveform.json` in `audio/store.py`, and the edited audio
(`piece-r<N>.flac`, `piece-r<N>.wav`) in `audio/piece_audio.py`. Folder *names* come from
`schemas/naming.py`, so a rename policy is a one-file change.

`ensure_data_tree()` creates the roots on app startup.

---

## 1. The tree

```text
aitu-backend/data/                     or the folder AITU_DATA_DIR names
  audio/<uuid>/
    metadata.json                      name, source, lineage, frameMs, cuts, audioRevision
    original.<ext>                     as ingested; never changed
    normalized.wav                     16 kHz mono: what the engine reads
    piece-r<N>.flac                    only with cuts: the edited audio every player plays
    piece-r<N>.wav                     only with cuts: normalized.wav with the cuts removed
    waveform.json                      min/max peaks for the waveform view (of the edited audio)
    matrices/
      events.json                      THE TRANSCRIPTION, in seconds of the piece. Kept forever.
      rhythm.json                      the reader's own decisions
      music-version.json               the current musical version number
      needs-rederivation.json          only on a piece nothing can rebuild
      audio-mismatches.json            windows where the recording no longer matches the sheet
    staging/<session-uuid>/            disposable; see §4
    history/v<N>/                      a musical state, before it was replaced
    video/                             only when the piece came from a video (implementations 04 to 07)
  playground/<artist-slug>/<track-slug>/
    metadata_track.json
    v2_f40/
      metadata.json
      piano_matrix_v2_f40.npz          or the per-hand variants
  library/
    tracks/<artist-slug>/<track-slug>/
      metadata_library_track.json
      piano_matrix_<...>.npz
    playlists/<playlist-slug>/
      metadata_library_playlist.json
  frame-examples/                      the video reader's example screenshots (implementation 05)
```

The files of `video/` and `frame-examples/` are listed in the docstring of `storage/paths.py`.

---

## 2. `data/audio/<uuid>/`: the working store

One uuid folder per ingested audio, whatever the source. Upload, browser recording and YouTube all
converge here, so nothing downstream has to ask where a recording came from.

`original.<ext>` is what arrived; `normalized.wav` is what ffmpeg produced (16 kHz mono) and what
the engine reads. A trimmed segment is a **physical child audio** with its own uuid folder and
absolute lineage back to its root source, not a remembered range, so it survives its parent being
deleted and can be trimmed again itself.

### 2.1 `metadata.json`

The entry of one audio (`AudioMetadata`, `schemas/metadata.py`): `uuid`, `alias`, `source`,
`format`, `originalFilename`, `durationSeconds`, `sampleRate`, `sourceUrl`, the lineage of a segment (`sourceAudioUuid`,
`sourceTimeRange`), `frameMs` (only on a composed piece) and `createdAt`.

Implementation 08 (Phase 4) added two fields for the selected region:

| Field | Default | Meaning |
|---|---|---|
| `cuts` | `[]` | The parts of the audio the user deleted: sorted `[startFrame, endFrame)` ranges of 10 ms time frames of the original. Validated on read: no range may overlap or touch the next. |
| `audioRevision` | `0` | Rises by one each time the cuts are saved with a change (`store.set_cuts`). A transcription records the revision it was made from in `events.json`, so a later cut makes its notes stale. |

`durationSeconds` in this file stays the length of the original. The API answers
(`GET /audio/`, `GET /audio/{uuid}`) report the length of the piece as `durationSeconds` and the
stored value as `originalDurationSeconds`.

### 2.2 The edited audio: `piece-r<N>.flac` and `piece-r<N>.wav`

The cuts first existed only as ranges, and every player was meant to jump over them. In practice
the other players still played the whole original, so on a cut piece the audio ran ahead of the
notes by the length of the cuts before the playhead. The user's rule (2026-09-29, Phase 6) is that
once the cuts are saved, the edited audio is the audio of the piece. The untouched original stays on
disk so the Audio tab can still show a cut and restore it.

`audio/piece_audio.py` therefore writes two files, named with the `audioRevision` they were made for:

| File | Content |
|---|---|
| `piece-r<N>.flac` | The original file, decoded at its own sample rate and channels, with the kept frames joined. FLAC because it is lossless and sample exact; an MP3 would add the encoder's delay (about 25 ms) at the start. |
| `piece-r<N>.wav` | `normalized.wav` with the kept frames joined: the engine's input, for `?normalized=true` and for the waveform. |

Both are joined exactly as the engine's input is (`frames.join_kept`): a 5 ms fade out and in at each
join, inside the kept samples. They are written by `PUT /audio/{uuid}/cuts`, or on the first request
when one is missing. Files of any other revision are deleted, and both are removed when the cuts are
removed. On "Come on Eileen" (two cuts, 263.50 s to 257.05 s) they took 0.7 s to write, 22 MB of
FLAC, and the length matched the notes' `durationSeconds`.

`GET /audio/{uuid}/file` serves them for a piece with cuts; only `?original=true` serves
`original.<ext>`. A change of the cuts also deletes `waveform.json`, which is then computed again
from the edited audio.

### 2.3 `matrices/events.json`

The folder is called `matrices` for historical reasons and now holds one important file.

`events.json` is the engine's note events in seconds, before any grid was involved. **It is the only
artifact here that cannot be recreated**, and everything else about the music is a function of it
(D-03). The matrix is a derived, quantised view and is never stored. Since implementation 08 the
times are in the time of the piece: the original minus its cuts.

Each event carries its start, its end, its MIDI note, and the flags a reader can set: `hand` (a
saved or corrected hand), `handGuessed` (a hand given by the quick rule) and `removed` (a note
removed from the recording). The flags are written onto the event rather than kept as an overlay,
because they change what the *neighbouring* notes are called.

**Schema `1.1`** (implementation 08, Phase 2) gives each event a stable `id` and the file a header at
the top level:

```json
{"schemaVersion": "1.1", "durationSeconds": 356.426312, "title": "…",
 "notesRevision": 2, "handsRevision": 2, "handsNotesRevision": 2, "audioRevision": 0,
 "engine": "muscriptor-large", "lagCorrectionMs": 7.0, "nextId": 5245,
 "events": [{"id": 2692, "midiNote": 60, "start": 4.843, "end": 5.133,
             "velocity": 64, "hand": "right"}, …]}
```

A `1.0` file reads with ids in file order and the default header, and is not rewritten until its
next save. What each field means and what makes each revision rise:
[`context/backend/piano-matrix-notation.md`](../../../context/backend/piano-matrix-notation.md#3-on-disk-eventsjson-pmnevents_filepy).

Every writer except a new transcription goes through `pipeline.save_edit`, under
`pipeline.piece_lock(uuid)`. A new transcription writes the header itself
(`pipeline.transcribe_audio`).

An empty piece, created by `POST /audio/compose`, is an `events.json` with no events and
`durationSeconds: 0`, and no audio file at all.

### 2.4 `matrices/rhythm.json`

The reader's decisions, which are the only things about a piece that are *not* derivable. One per
piece: a second reading replaces the first. Fields in
[`rhythm-and-annotations.md`](rhythm-and-annotations.md).

Since implementation 08 (Phase 5) the reading also records `handsRevision`: the `handsRevision` of
`events.json` it was saved for. `PUT /time/{uuid}/rhythm` sets it from `events.json` and ignores the
client's value. When the two numbers differ, the Sheet step of the piece is `stale`. A reading saved
before Phase 5 has no value, which reads as `0`. An edit made on the Sheet tab moves the reading's
number forward with the notes, so a current sheet stays current.

A new transcription deletes `rhythm.json`, after copying it to `history/v<N>/` (§2.6), because its
marks are column numbers over the old notes.

### 2.5 `matrices/needs-rederivation.json`

Written by the 1.x migration for a piece that has no recorded events to rebuild from: a grid that
was hand-edited under the old model. The piece is **surfaced rather than converted**, because a grid
written under one set of assumptions and read under another puts every note at the wrong time. No
stored artifact is ever silently reinterpreted.

### 2.6 `matrices/music-version.json` and `history/v<N>/`

The live piece is one `events.json`. Two events copy the **previous** state into `history/v<N>/` and
advance the counter in `music-version.json`. Both share that counter, so the two kinds of snapshot
never share a folder.

| When | Function (`editing/history.py`) | What is copied |
|---|---|---|
| Accepting a range edit or a composed passage | `snapshot_current` | `events.json`, `rhythm.json`, `normalized.wav`, `original.<ext>` |
| A new transcription of a piece that already has notes (implementation 08) | `snapshot_notes` | `events.json`, `rhythm.json`, and a `snapshot.json` with the reason. No audio, because a transcription does not change it. |

Before implementation 08 a new transcription deleted `rhythm.json` with no copy.

A version here means *the music changed*, which is a different axis from the playground's version
folders (see §3).

### 2.7 `matrices/audio-mismatches.json`

Windows where the recording no longer matches the sheet, after an audio splice failed. Recorded
rather than raised: the notes were written correctly and only the sound is behind, so the edit
succeeds and the discrepancy is reported.

---

## 3. `data/playground/`: versioned work

`v<N>_f<frameMs>`, for example `v2_f40`: "version 2, forty milliseconds a column".

The scheme was decided in P4.4 and the reasoning is worth keeping, because the name looks arbitrary
until you know it. A folder used to be `v2_gn`: a version number plus a **granularity code**, the
note figure one column stood for. There are no granularities any more (D-01), so the code had to be
replaced with something, and the choice was between dropping it (`v2`) and putting the frame length
in its place.

`v2_f40` won because of the idea the repository is built on: **a version is a musical state, and the
grid is a view of it.** `v1_gsc` and `v1_gn` were the same take collapsed two ways, which is why
saving at a second granularity kept the version number instead of advancing it. That distinction
survives the refactor unchanged: the same recording at 20 ms and at 40 ms is the same playing on a
finer or a coarser grid, so the folder still has to say which view it holds. Dropping the suffix
would make two views of one state collide on one folder name.

A fractional frame length writes with the point removed, `f12_5` for 12.5 ms, because a dot in a
folder name invites a reader to treat what follows as an extension.

`schemas/naming.py` owns all of it: `slugify`, `frame_code`, `frame_from_code`, `version_folder`,
`parse_version_folder`, `matrix_filename`.

Matrices are `scipy.sparse` COO int8 saved as compressed `.npz` (`storage/matrix_store.py`); the
dense form exists only transiently. Hands are separate files.

---

<a id="4-dataaudiouuidstagingsession--disposable-sessions"></a>

## 4. `data/audio/<uuid>/staging/<session>/`: disposable sessions

Epic 11 range editing and Epic 13 composing. **Nothing outside this folder changes until the reader
accepts**, and cancel deletes the folder and nothing else.

| File | What it is |
|---|---|
| `session.json` | The window or the moment, the placement, the speed, the trim |
| `upload.<ext>` | The take as it arrived from the browser |
| `untrimmed.wav` | The take, converted |
| `selected.wav`, `trimmed.wav` | What the reader kept of it |
| `scaled.wav` | The take stretched into the window |
| `take_events.json` | The take transcribed, **as played** |
| `window.wav`, `window_slow.wav` | The original window, and a pitch-preserved slow copy to play along with |

`take_events.json` is the transcription of the take at the speed it was played, never of the
stretched audio: a time-stretched recording is a different sound and the model would be reading an
artefact.

Detail in [`editing-and-compose.md`](editing-and-compose.md).

---

## 5. `data/library/`: what a performer plays from

Promotions are named and reversible: `storage/promotion.py` writes them, `storage/playlists.py`
owns the ordered lists, and `storage/browse.py` fills the computed fields the Library lists need at
read time rather than storing them.

---

## 6. `data/example-scores.json` (deleted)

The seed scores of `GET /scores` were deleted with the text-notation MVP in implementation 02,
Phase 1 (Q-4).

---

## 7. Where the data lives: `AITU_DATA_DIR` and the containers

Implementation 08 moved the app to an Ubuntu machine with a GPU and runs it in two containers
(Phase 3). The data had to stay on the host, readable and writable by the user, and the same folder
had to work natively and in a container. Two things make that possible.

**Natively**, `paths.data_dir()` returns `AITU_DATA_DIR` when it is set and not empty, otherwise
`aitu-backend/data`. The variable is read on every call, so a test can change it with
`monkeypatch.setenv`.

**In the containers** (`compose.yaml` at the repository root, project name `aimpromptu`), the
variable has another role: it chooses the host folder mounted over `aitu-backend/data`, and inside
the container it is empty, so the backend uses its default path.

| Host | Container | Why |
|---|---|---|
| The repository (`.`) | `/work/aimpromptu` | The code is the host's, so uvicorn (`--reload --reload-dir src`) and Vite reload on every edit; the tests also read `pocs/` and `context/` |
| `${AITU_DATA_DIR:-./aitu-backend/data}` | `/work/aimpromptu/aitu-backend/data` | The data folder |
| `${HF_HUB_CACHE:-/mnt/ssd2/hf/data/hub}` | `/hf/hub` (`HF_HUB_CACHE`) | The MuScriptor weights (5.5 GB for `large`), shared with the host's Hugging Face cache |
| `${AITU_CACHE_DIR:-/mnt/ssd2/aimpromptu/home}` | `/home/app` | The backend's home folder: the ByteDance checkpoint (`~/piano_transcription_inference_data/`) and the torch cache, kept so a new container does not download them again |
| `./aitu-frontend` | `/work/aimpromptu/aitu-frontend` | The frontend code; an anonymous volume keeps the image's `node_modules` in front of the host's |

The Python environment is in the image at `/opt/venv`, outside the mount, so the host's `.venv` and
the image's never mix. Both containers run as the host user (`UID` and `GID` from the Makefile), so
every file they write into the data folder belongs to that user, not to root. `make up` creates the
cache folder first, because Docker would create a missing one as root.

Both ports bind to `127.0.0.1` only: 8765 for the backend and 5173 for the page. The Mac reaches the
page through the SSH tunnel (`scripts/tunnel-from-mac.sh`), and the page reaches the backend through
Vite's `/api` proxy.

Every variable, with its default, is listed in `.env.example` at the repository root. Copy it to
`.env` to change one; `.env` is ignored by git.

---

## 8. Scripts that touch the tree

`aitu-backend/scripts/`, run with `uv run python scripts/<name>.py` from `aitu-backend/`, or with
`docker compose exec backend python scripts/<name>.py` against the live data in the container:

| Script | What it does |
|---|---|
| `make_demo_pieces.py` | Writes two hand-built demo pieces into the store, so the right answer is known before you open anything |
| `migrate_to_time_matrix.py` | The 1.x to 2.0 migration; marks what it cannot rebuild |
| `inventory_artifacts.py` | What is on disk, per piece |
| `benchmark_hands.py` | Hand-split quality against a reference |
| `check_saved_hands.py` | Implementation 08: the saved hands painted against the inference, on a copy of every piece |

---

## 9. Where to look deeper

- [`context/backend/piano-matrix-notation.md`](../../../context/backend/piano-matrix-notation.md):
  `events.json` schema 1.1 field by field, and the revision chain
- [`time-matrix.md`](time-matrix.md): the models these files hold
- [`rhythm-and-annotations.md`](rhythm-and-annotations.md): `rhythm.json` field by field
- [`editing-and-compose.md`](editing-and-compose.md): staging, history and the splice
- [`transcription-pipeline.md`](transcription-pipeline.md): what writes `events.json`
- [`endpoints.md`](endpoints.md): the routes that read and write all of it
