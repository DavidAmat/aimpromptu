# Task 1.3.2 — Metadata schemas · progress report

Status: **done**. Date: 2026-07-26.

## Summary

Two new modules and five committed fixtures.

### `schemas/naming.py` — slugs and folder codes

| Function | Behaviour |
|----------|-----------|
| `slugify(value)` | accent-folded, lowercase, hyphenated (`Beyoncé` -> `beyonce`, `AC/DC` -> `ac-dc`); raises on input with no slug-able characters |
| `granularity_code` / `granularity_from_code` | `gb gn gc gsc gf gsf` (+ `gr` for redonda), reusing `GRANULARITY_CODES` from Task 1.3.1 |
| `version_folder(2, NEGRA)` | `"v2_gn"` |
| `parse_version_folder("v2_gn")` | `(2, Granularity.NEGRA)`; rejects `v0_gn`, `gn_v2`, `v2-gn`, … |
| `next_version(folders)` | highest + 1, ignoring unparseable folders so a stray directory never blocks a save |
| `matrix_filename` | `piano_matrix_v1_gsc.npz`, or `…_left.npz` per hand |

Every folder name under `data/` is produced here, so a rename policy stays a one-file change.

### `schemas/metadata.py` — the four metadata files

| File | Model |
|------|-------|
| `metadata.json` (version folder) | `VersionMetadata` |
| `metadata_track.json` (playground track) | `TrackMetadata` |
| `metadata_library_track.json` (library track) | `LibraryTrackMetadata` |
| `metadata.json` (audio uuid folder) | `AudioMetadata` |
| `metadata_library_playlist.json` | `PlaylistMetadata` |

- **`VersionMetadata`** carries `tempoBpm`, `granularity`, `matrixProcessingStep`,
  `timeStepSeconds`, `parentMatrix` (folder + step + relative `.npz` path — the pointer that makes
  a sub-second recompute possible), `audio` (`audioUuid` + optional `timeRange`), `keySignature`,
  a `comment`, and the `annotations` block. `.folder` derives `v2_gsc` from its own fields, so the
  name and the contents can never disagree.
- **`Annotations`** is empty by default and holds `lyrics`, `fingers`, `passages` and `keyChanges`.
  Every entry anchors on a `MatrixAnchor` = `{hand, columns: {fromColumn, toColumn}, rows[]}` —
  **matrix indices, never rendered positions**, so an annotation survives a re-render, a
  transposition or a responsive re-wrap. `PassageAnnotation.kind` covers cue-size, tuplet, trill,
  acciaccatura and appoggiatura with a free-form `options` dict (`{"ratio": [3, 2]}` for a tuplet).
- **`TrackMetadata`** holds names, both slugs, dates and the `versions` history (folder, comment,
  created at, parent version, granularity, step), plus `latest()` and `version_folders()`.
- **`LibraryTrackMetadata`** holds tags and a `promotions` list. Each `Promotion` has a
  `promotionName` ("Levels (Chill) - Avicii"), the source version folder, the matrix filename, a
  date, an `active` flag — **several promotions can be active at once**, which is what "multiple
  concurrently promoted versions" requires — and `versionMetadata`, an embedded snapshot of the
  promoted version's `metadata.json` so a library entry survives deletion of the playground folder.
  `rollbackTo` names the promotion to fall back to.

### Fixtures

`tests/fixtures/` holds one committed sample per file — `metadata.json`, `metadata_track.json`,
`metadata_library_track.json`, `metadata_audio.json`, `metadata_library_playlist.json` — telling
one coherent story (an Avicii "Levels" transcription from YouTube audio, v1_gf raw -> v2_gsc
two-hands, promoted twice, in a playlist). Each is parsed, asserted field by field, re-serialized
with `model_dump(by_alias=True, mode="json")` and re-parsed to prove the round trip.

## Errors found and how they were solved

1. **`parse_version_folder("v0_gn")` succeeded.** The regex allowed a zero, while
   `version_folder()` rejected it — the two directions disagreed. `parse_version_folder` now
   rejects versions below 1 as well, so parse and build are exact inverses.
2. **`datetime` fields and JSON round-trips.** `model_dump(by_alias=True)` leaves `datetime`
   objects in place, so re-validating a dumped model is not a true file round trip. The fixture
   tests use `mode="json"`, which serializes to ISO strings — actually what lands on disk.

## Deviations from the task file

- Added **`PlaylistMetadata`** and **`AudioMetadata`**, which the task did not list. Both files
  appear in the Task 1.4.1 folder tree, so leaving them undefined would have meant a later epic
  inventing a shape.
- Added `TimeRange`, `ColumnRange`, `MatrixAnchor`, `AudioReference`, `ParentMatrix` as named
  models rather than inline dicts, so the same shape validates identically everywhere.
- `slugify` folds accents. Not specified, but "filesystem-safe" and a real music library imply it.

## Verification

```
pytest        # 60 passed (28 new in tests/test_metadata_schemas.py)
mypy          # Success: no issues found in 29 source files
flake8, black # clean
```

Beyond the fixture round trips: slug cases (accents, punctuation, slashes), granularity code
round trips for all seven values, malformed version folders, `next_version` with junk entries,
and the negative validations (backwards `timeRange`, backwards `columnRange`, finger 6).

## Manual trial for the supervisor

Nothing to click yet. To read a fixture as the models see it:

```bash
cd aitu-backend && uv run python -c "
import json
from aitu_backend.schemas.metadata import LibraryTrackMetadata
m = LibraryTrackMetadata.model_validate(json.load(open('tests/fixtures/metadata_library_track.json')))
print([p.promotion_name for p in m.active_promotions()])
print(m.find_promotion('Levels (Chill) - Avicii').version_metadata.folder)   # v2_gsc
"
```

Worth a skim: `tests/fixtures/metadata.json` is what a saved version folder will look like on disk.
If any field is wrong for how you actually work, say so now — changing it later means migrating files.

## For the next worker

- **Task 1.4.1**: build every path from `schemas/naming.py`. `matrix_filename()` and
  `version_folder()` already exist; do not re-derive folder names.
- **Epic 5**: `next_version(track.version_folders())` gives the next version number.
  `TrackMetadata.versions` is the history list — append, never rewrite.
- **Epics 9 and 12**: fill `Annotations`. The block is already persisted and already validated;
  anchor everything on matrix indices.
- These models are **not yet mirrored in TypeScript**. `src/api/library.ts` has hand-written
  approximations (`PlaygroundTrack`, `LibraryTrack`, `Playlist`) — reconcile them when Epic 5 or 10
  makes those endpoints real.
