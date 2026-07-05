# Compose panel

`SequenceComposer` — interactive passage builder; calls `POST /sequence` and renders the
result locally.

## Inputs

| Field | Default / notes |
|-------|-----------------|
| Title | `"My passage"` |
| Tempo (BPM) | 60 |
| Time step (s) | 0.5 |
| Key signature | `KEY_SIGNATURES[0].vex` (`"C"` / Do-Mayor) |
| Right hand | `DEFAULT_SEQUENCE` (treble; one frame per line) |
| Left hand | `DEFAULT_LEFT_SEQUENCE` (optional; empty = one hand) |
| Lyrics | `DEFAULT_LYRICS` (optional; empty textarea = omitted) |

Key dropdown uses `KEY_SIGNATURES` from `notes.ts` (Spanish labels).

## Frame parsing

`parseFrames(text)`:

- Normalize `\r\n` → `\n`, trim each line.
- Strip trailing blank lines.
- One line = one time frame; blank line = silent frame `""`.

## Validation (client-side, before fetch)

- Right hand must have ≥1 frame.
- If left hand non-empty: `leftSequence.length === sequence.length` or error with counts.
- Lyrics: if textarea trimmed non-empty, parsed same as sequence; else `undefined` in body.

## POST /sequence

```typescript
fetch(`${apiBase}/sequence`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    title: title.trim() || undefined,
    tempoBpm,
    timeStepSeconds,
    keySignature,
    sequence,
    leftSequence,
    lyrics,
  }),
});
```

Non-OK: reads response text into error message. Success: `setScore` with `MatrixScore`.

## Result display

On success: optional title `<h3>`, local `LayoutControls`, `PianoSheet` — independent of
the global controls in `App.tsx`.

## Two-hand input

Separate text areas for right (treble) and left (bass). **Not** inline `__` separators —
the API takes `sequence` + `leftSequence` as parallel arrays. See
[notation-spec.md](../shared/notation-spec.md).

## Notation hints (in-UI)

The panel explains `*` onsets, plain sustains, `||` chords, blank silence, and that left
hand must match right-hand frame count.

## Where to look deeper

- [notation-spec.md](../shared/notation-spec.md) — text notation contract
- [endpoints.md](../../documentation/services/backend/endpoints.md) — API body/422
- [components.md](../../documentation/services/frontend/components.md) — `SequenceComposer` detail
- [rendering-pipeline.md](rendering-pipeline.md) — how the returned score renders
