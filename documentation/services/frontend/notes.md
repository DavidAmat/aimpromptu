> Context: [rendering-pipeline.md](../../../context/frontend/rendering-pipeline.md) · [notation-spec.md](../../../context/shared/notation-spec.md)

# notes

88-key mapping and key signatures in `aitu-frontend/src/music/notes.ts`. Mirrors
`build_grand_piano_rows()` in aitu-backend.

## buildGrandPianoRows() / GRAND_PIANO_ROWS

Same algorithm as backend:

- Start: `La-0`, `La#-0`, `Si-0`
- Octaves 1–7: full `CHROMATIC_NOTES` list per octave
- End: `Do-8`
- Assert 88 rows; cached as `GRAND_PIANO_ROWS`.

## rowIndexToCustomNote(rowIndex, rows?)

Uses `rows ?? GRAND_PIANO_ROWS`. Out of range → `Error`.

## customNoteToVexFlow(noteName)

Parse `"Do-3"` → base + octave at last `-`.

`SPANISH_TO_VEXFLOW` maps base to VexFlow letter + optional accidental:

| Spanish | Letter | Accidental |
|---------|--------|------------|
| Do | c | — |
| Do# | c | # |
| Re | d | — |
| … | … | … |
| Si | b | — |

Returns `{ key: "c/3", accidental?: "#" }`. Malformed/unknown → `Error`.

Accidental is **not** always drawn — `PianoSheet` uses `applyAccidentals` vs key signature.

## KEY_SIGNATURES

15 major keys for UI dropdown and VexFlow `addKeySignature`:

| label | accidentals (hint) | vex |
|-------|-------------------|-----|
| Do-Mayor | (empty) | C |
| Sol-Mayor | # | G |
| Re-Mayor | ## | D |
| La-Mayor | ### | A |
| Mi-Mayor | #### | E |
| Si-Mayor | ##### | B |
| Fa#-Mayor | ###### | F# |
| Do#-Mayor | ####### | C# |
| Fa-Mayor | b | F |
| Sib-Mayor | bb | Bb |
| Mib-Mayor | bbb | Eb |
| Lab-Mayor | bbbb | Ab |
| Reb-Mayor | bbbbb | Db |
| Solb-Mayor | bbbbbb | Gb |
| Dob-Mayor | bbbbbbb | Cb |

`label` is Spanish (shown in `SequenceComposer` select). `vex` is sent as `keySignature`
in API payloads and passed to VexFlow.

`PianoSheet` uses `accidentals.length` for layout room (`KEY_ACCIDENTAL_COUNT`).

## Pitch vs display example

`Fa#-5` → `{ key: "f/5", accidental: "#" }` → `vexKey: "f#/5"`.

In Sol-Mayor (`G`): F# is in the key → no sharp glyph.
In Do-Mayor (`C`): accidental shown.
