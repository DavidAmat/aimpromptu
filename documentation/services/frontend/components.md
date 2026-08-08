> Context: [app-shell.md](../../../context/frontend/app-shell.md) · [rendering-pipeline.md](../../../context/frontend/rendering-pipeline.md)

# Components

React components in `aitu-frontend/src/components/`.

## Notation (`components/notation/`)

| Component | Role |
|-----------|------|
| `GridScore` | The score. A lifecycle shell around `GridNotationEditor` — see [grid-notation.md](grid-notation.md) |
| `PromoteDialog` | Promote a saved playground version into the library |

`GridScore` holds no React state beyond two refs. All drawing, selection,
toolboxes, playback and the resize handling belong to the editor; the component's
whole job is to build it once per piece and destroy it on unmount.

Removed with the VexFlow stack: `PianoSheet`, `ScoreStack`, `SequenceComposer`,
`LayoutControls`, `ScoreSheet`, `renderScore`, `KeySignaturePanel`, `OctavePanel`.
The spacing controls those needed have no equivalent — the score re-wraps at a
fixed size rather than being scaled, and zoom lives in the editor's own chrome.

## Elsewhere

| Directory | Contents |
|-----------|----------|
| `components/audio/` | Recorder, upload, waveform and range selection |
| `components/input/` | Text-notation input, matrix JSON input, transcription settings |
| `components/matrix/` | `MatrixGrid` — the matrix as a table |
| `piano/`, `playback/` | Keyboard, transport and the falling-note views |
| `ui/` | The shared kit: `PageContainer`, `SectionCard`, `Pill`, `TabBar`, theme |

## File layout

```
src/
  components/
    notation/
      GridScore.tsx
      PromoteDialog.tsx
  music/
    types.ts          # matrix contracts, mirrored from schemas/matrix.py
    gridNotation.ts   # the seam to @aimpromptu/grid-notation
    granularities.ts
    handMap.ts
```

Music logic stays under `music/`; the renderer is reached only through
`music/gridNotation.ts` and `components/notation/GridScore.tsx`, per
[09-coding-conventions.md](../../../context/09-coding-conventions.md).
