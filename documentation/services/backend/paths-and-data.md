> Context: [context/backend/api.md](../../../context/backend/api.md) ·
> [context/07-database.md](../../../context/07-database.md)

# Storage layout: every path and every file

There is no database. All persistence is the local filesystem under `aitu-backend/data/`, and
**every path literal is built in one module**: `aitu-backend/src/aitu_backend/storage/paths.py`. No
path string lives outside it. Folder *names* come from `schemas/naming.py`, so a rename policy is a
one-file change too.

`ensure_data_tree()` creates the tree on app startup. If storage is ever containerised the tree maps
one-to-one onto an object-store bucket; that is not now.

---

## 1. The tree

```text
aitu-backend/data/
  example-scores.json                  seed scores for GET /scores (text-notation MVP)
  audio/<uuid>/
    metadata.json                      name, source, lineage, frameMs
    original.<ext>                     as ingested
    normalized.wav                     what the model and the player read
    waveform.json                      min/max peaks for the waveform view
    matrices/
      events.json                      THE TRANSCRIPTION, in seconds. Kept forever.
      rhythm.json                      the reader's own decisions
      music-version.json               the current musical version number
      needs-rederivation.json          only on a piece nothing can rebuild
      audio-mismatches.json            windows where the recording no longer matches the sheet
    staging/<session-uuid>/            disposable; see §4
    history/v<N>/                      a musical state, before it was replaced
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
```

---

## 2. `data/audio/<uuid>/` — the working store

One uuid folder per ingested audio, whatever the source. Upload, browser recording and YouTube all
converge here, so nothing downstream has to ask where a recording came from.

`original.<ext>` is what arrived; `normalized.wav` is what ffmpeg produced and what every consumer
actually reads. A trimmed segment is a **physical child audio** with its own uuid folder and
absolute lineage back to its root source — not a remembered range — so it survives its parent being
deleted and can be trimmed again itself.

### `matrices/events.json`

The folder is called `matrices` for historical reasons and now holds one important file.

`events.json` is the engine's note events in seconds, before any grid was involved. **It is the only
artifact here that cannot be recreated**, and everything else about the music is a function of it
(D-03). The matrix is a derived, quantised view and is never stored.

Each event carries its start, its end, its MIDI note, and two flags a reader can set: `hand` (a
correction to the split) and `removed` (a note taken off the recording). Both are written onto the
event rather than kept as an overlay, because both change what the *neighbouring* notes are called.

An empty piece — created by `POST /audio/compose` — is an `events.json` with no events and
`durationSeconds: 0`, and no audio file at all.

### `matrices/rhythm.json`

The reader's decisions, which are the only things about a piece that are *not* derivable. One per
piece: a second reading replaces the first. Fields in
[`rhythm-and-annotations.md`](rhythm-and-annotations.md).

### `matrices/needs-rederivation.json`

Written by the 1.x migration for a piece that has no recorded events to rebuild from — a grid that
was hand-edited under the old model. The piece is **surfaced rather than converted**, because a grid
written under one set of assumptions and read under another puts every note at the wrong time. No
stored artifact is ever silently reinterpreted.

### `matrices/music-version.json` and `history/v<N>/`

The live piece is one `events.json`. Accepting an edit copies the **previous** musical state into
`history/v<N>/` and advances the counter in `music-version.json`.

A version here means *the music changed*, which is a different axis from the playground's version
folders — see §3.

### `matrices/audio-mismatches.json`

Windows where the recording no longer matches the sheet, after an audio splice failed. Recorded
rather than raised: the notes were written correctly and only the sound is behind, so the edit
succeeds and the discrepancy is reported.

---

## 3. `data/playground/` — versioned work

`v<N>_f<frameMs>` — for example `v2_f40`, "version 2, forty milliseconds a column".

The scheme was decided in P4.4 and the reasoning is worth keeping, because the name looks arbitrary
until you know it. A folder used to be `v2_gn`: a version number plus a **granularity code**, the
note figure one column stood for. There are no granularities any more (D-01), so the code had to be
replaced with something, and the choice was between dropping it (`v2`) and putting the frame length
in its place.

`v2_f40` won because of the idea the repository is built on: **a version is a musical state, and the
grid is a view of it.** `v1_gsc` and `v1_gn` were the same take collapsed two ways, which is why
saving at a second granularity pinned the version number instead of advancing it. That distinction
survives the refactor unchanged — the same recording at 20 ms and at 40 ms is the same playing on a
finer or a coarser grid — so the folder still has to say which view it holds. Dropping the suffix
would make two views of one state collide on one folder name.

A fractional frame length writes with the point removed, `f12_5` for 12.5 ms, because a dot in a
folder name invites a reader to treat what follows as an extension.

`schemas/naming.py` owns all of it: `slugify`, `frame_code`, `frame_from_code`, `version_folder`,
`parse_version_folder`, `matrix_filename`.

Matrices are `scipy.sparse` COO int8 saved as compressed `.npz` (`storage/matrix_store.py`); the
dense form exists only transiently. Hands are separate files.

---

## 4. `data/audio/<uuid>/staging/<session>/` — disposable sessions

Epic 11 range editing and Epic 13 composing. **Nothing outside this folder changes until the reader
accepts**, and cancel deletes the folder and that is the whole of it.

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

## 5. `data/library/` — what a performer plays from

Promotions are named and reversible: `storage/promotion.py` writes them, `storage/playlists.py`
owns the ordered lists, and `storage/browse.py` fills the computed fields the Library lists need at
read time rather than storing them.

---

## 6. `data/example-scores.json`

Seed scores for `GET /scores`, the text-notation MVP route. A JSON array of `MatrixScore` objects.
If it is missing, `/scores` answers `404` with a hint to run
`notebooks/dummy-matrix/01-generate-dummy-matrix.ipynb` or to create the file by hand.

Treat it as opaque persisted scores; it is not part of the wall-clock path.

---

## 7. Scripts that touch the tree

`aitu-backend/scripts/`, run with `uv run python scripts/<name>.py` from `aitu-backend/`:

| Script | What it does |
|---|---|
| `make_demo_pieces.py` | Writes two hand-built demo pieces into the store, so the right answer is known before you open anything |
| `migrate_to_time_matrix.py` | The 1.x to 2.0 migration; marks what it cannot rebuild |
| `inventory_artifacts.py` | What is on disk, per piece |
| `benchmark_hands.py` | Hand-split quality against a reference |

---

## 8. Where to look deeper

- [`time-matrix.md`](time-matrix.md) — the models these files hold
- [`rhythm-and-annotations.md`](rhythm-and-annotations.md) — `rhythm.json` field by field
- [`editing-and-compose.md`](editing-and-compose.md) — staging, history and the splice
- [`endpoints.md`](endpoints.md) — the routes that read and write all of it
