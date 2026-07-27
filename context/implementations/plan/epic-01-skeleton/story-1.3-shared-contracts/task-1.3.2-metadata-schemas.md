# Task 1.3.2 — Metadata schemas

Pydantic models for every metadata file the storage layer will write. Defined now so all epics write compatible files.

## Subtask 1.3.2.1 — Slugs and codes

- `artist_slug`, `track_slug`: lowercase, hyphenated, filesystem-safe.
- Granularity codes: `gb` blanca, `gn` negra, `gc` corchea, `gsc` semicorchea, `gf` fusa, `gsf` semifusa (prefix g = granularity). Versions: `v1`, `v2`, …
- Version+granularity folder name: `v2_gn`.

## Subtask 1.3.2.2 — metadata.json (per version+granularity folder)

Holds everything needed to re-render one saved matrix state:

- `tempoBpm`, `granularity`, `matrixProcessingStep`, `parentMatrix` (pointer to the matrix this one was derived from), source audio reference (uuid + optional time range), `keySignature`
- `annotations` block (empty for now; Epics 9 and 12 fill it: trills, tuplets, lyrics, fingers, cue-size passages, key-signature changes per passage) expressed as matrix indices (hand, column ranges, rows)

## Subtask 1.3.2.3 — metadata_track.json (per track folder in playground)

- `artistName`, `trackName`, slugs, creation date
- `versions`: history list — each entry: folder name, comment, created at, parent version

## Subtask 1.3.2.4 — metadata_library_track.json (per track in library)

- real artist/track names, promotion history (which playground version, promotion name like "Levels (Chill) - Avicii", date), support for multiple concurrently promoted versions, rollback pointers
- embeds the promoted version's `metadata.json` content in a section

## Acceptance

Models serialize/deserialize with sample fixtures committed as tests.
