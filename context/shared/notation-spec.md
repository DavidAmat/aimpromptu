# Notation contract

Single source of truth for the music format shared by **aitu-backend** (parser) and
**aitu-frontend** (renderer). Both services link here; do not restate this spec elsewhere.

## Text notation

One list entry per **time frame** (one line in the compose UI). Within a frame:

| Token | Meaning |
|-------|---------|
| `*Note` | **Onset** — the key is struck (e.g. `*Do-4`, `*Fa#-5`). |
| `Note` (no `*`) | **Sustain** — same key keeps sounding, not struck again (e.g. `Re-4`). |
| `A \|\| B` | Simultaneous notes in one frame (chord). |
| empty string `""` | Silent frame. |

Example sequence (8 frames):

```
*Do-4 || *Mi-4    # frame 0: chord, both struck
*Re-4             # frame 1: Re-4 onset
Re-4              # frame 2: Re-4 sustain (→ one 2-frame note with frame 1)
*Mi-4             # frame 3: Mi-4 onset
Mi-4              # frames 4–6: sustain
Mi-4
Mi-4
*Fa#-5            # frame 7: new onset
```

### Note names

Spanish solfège + scientific octave: `Do-4`, `Fa#-5`, `La#-0`. Chromatic set:
`Do`, `Do#`, `Re`, `Re#`, `Mi`, `Fa`, `Fa#`, `Sol`, `Sol#`, `La`, `La#`, `Si`.

Octave numbering: `La-0` = A0 (lowest key), `Do-8` = C8 (highest). The 88-key row
order is canonical (`La-0` … `Do-8`) and rebuilt identically on both sides — see
`build_grand_piano_rows()` / `buildGrandPianoRows()`.

## Onset rule

A sustain continues only through frames with **no** new onset. The moment any frame
has an onset, every carried sustain ends at the previous frame.

The builder normalizes illegal input:

- Sustain colliding with a foreign onset in the same frame → sustain dropped; only
  the onset remains.
- Sustain with no note to continue (key never struck) → promoted to onset.

This disambiguates four `Re-4` cells: four onsets = four notes; one onset + three
sustains = one long note.

Implemented in `aitu-backend/src/aitu_backend/sequence.py` (`sequence_to_sparse_payload`)
and mirrored on decode in `aitu-frontend/src/music/matrixToNotation.ts`
(`activeCellsToNoteEvents`).

## Sparse-COO payload

A dense 88×N matrix is mostly zeros. The score ships three parallel arrays sorted by
`(column, row)`:

| Field | Meaning |
|-------|---------|
| `format` | Always `"binary-coo"`. |
| `shape` | `[rowCount, columnCount]` — rowCount is 88. |
| `rows[i]` / `cols[i]` | Active cell at `(rows[i], cols[i])`; all other cells are 0. |
| `onset[i]` | `rows[i]` when the cell is a struck onset; `-1` when it is a sustain. |

The row index → note-name table (`rows` on `MatrixScore`) is intentionally omitted;
the frontend rebuilds the canonical 88-key order.

### Score metadata (camelCase JSON)

| Field | Required | Meaning |
|-------|----------|---------|
| `tempoBpm` | yes | Beats per minute. |
| `timeStepSeconds` | yes | Seconds per matrix column (one time frame). |
| `matrixEncoding` | no | `"sparse-coo"` (default). |
| `title` | no | Display title. |
| `lyrics` | no | One entry per time frame (see below). |
| `keySignature` | no | VexFlow key spec (`C`, `G`, `Bb`, …). Omitted = no key sig drawn. |

## One hand vs two hands

Mutually exclusive matrix forms — exactly one is present:

| Form | Fields | Rendering |
|------|--------|-----------|
| One hand | `matrix` | Single treble clef. |
| Two hands | `r_matrix` + `l_matrix` | Braced grand staff: right/treble above, left/bass below. |

Both matrices must span the **same number of time frames** (`shape[1]` equal) so the
hands stay vertically aligned.

`POST /sequence` accepts optional `leftSequence` (same frame count as `sequence`):
`sequence` is the right hand (treble), `leftSequence` is the left hand (bass clef).
The same notation, onset rule, lyrics, and key signature apply to both clefs unchanged.

Text input uses **separate** right-hand and left-hand text areas (not inline `__`
separators). See [compose-panel.md](../frontend/compose-panel.md).

## Lyrics

Optional parallel list — one entry per time frame, same order as matrix columns.
Empty string `""` = no syllable on that frame.

Lyrics are **time-indexed**, not note-indexed: the renderer draws each non-empty
entry at that frame's horizontal position whether the frame is a struck note, a
sustain, or a silence. See [piano-sheet.md](../../documentation/services/frontend/piano-sheet.md).

```
sequence  →  ["*Do-4 || *Mi-4", "*Re-4", "Re-4", "*Mi-4", "Mi-4", "Mi-4", ""]
lyrics    →  ["Ho",             "la",    "la",   "dron",  "",      "de",   ""]
```

## Where to look deeper

- Backend parsing: [notation-and-parsing.md](../backend/notation-and-parsing.md) →
  [sequence-logic.md](../../documentation/services/backend/sequence-logic.md)
- Backend schemas: [schemas.md](../../documentation/services/backend/schemas.md)
- Frontend decode/render: [rendering-pipeline.md](../frontend/rendering-pipeline.md) →
  [matrix-to-notation.md](../../documentation/services/frontend/matrix-to-notation.md),
  [piano-sheet.md](../../documentation/services/frontend/piano-sheet.md)
