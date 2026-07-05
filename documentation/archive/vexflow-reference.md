# VexFlow reference (archived)

> Historical reference migrated from `aitu-frontend/documentation/vexflow/README.md`.
> Describes an earlier **EasyScore / Factory** approach. Current rendering uses the
> low-level API in [piano-sheet.md](../services/frontend/piano-sheet.md).

---

# VexFlow Notes For This Project

This project uses VexFlow 5.0.0 to render professional music notation from the matrix score.

## Rendering Flow

The high-level VexFlow API used here is:

```ts
const vf = new Factory({
  renderer: { elementId: "output", width: 980, height: 230 },
});
const score = vf.EasyScore();
const system = vf.System({ x: 24, y: 36, width: 910 });

system
  .addStave({
    voices: [
      score.voice(score.notes("D#5/h, G#4/q, G#4/q", { stem: "up" })),
      score.voice(score.notes("D#4/h, C#4/h", { stem: "down" })),
    ],
  })
  .addClef("treble")
  .addTimeSignature("4/4");

vf.draw();
```

## Factory

`Factory` is VexFlow's high-level wrapper. It creates the renderer and keeps the rendering context shared by all objects created through it.

Important calls:

- `new Factory({ renderer: { elementId, width, height } })` creates an SVG renderer inside an existing DOM element.
- `vf.EasyScore()` creates the EasyScore parser/helper bound to the same rendering context.
- `vf.System(options)` creates a musical system, usually one or more staves formatted together.
- `vf.draw()` formats and draws the queued VexFlow elements.

In React, clear the target element before drawing. React Strict Mode can run effects twice in development, and VexFlow appends an SVG into the target element.

## EasyScore

`EasyScore` turns compact notation strings into VexFlow notes and voices.

Useful methods:

- `score.notes(line, options)` parses a comma-separated note string into note objects.
- `score.voice(notes, options)` wraps notes into a `Voice`.
- `score.beam(notes)` beams short notes. The MVP uses this to ligate adjacent eighth-note pairs.
- `score.tuplet(notes)` creates tuplets.

EasyScore notation examples:

- `C4/q` means C4 quarter note.
- `D4/8` means D4 eighth note.
- `E4/h` means E4 half note.
- `F4/w` means F4 whole note.
- `G4/q.` means dotted quarter note.
- `B4/8/r` means an eighth rest positioned around B4.
- `(C4 E4 G4)/q` means a quarter-note chord.

Stem direction can be supplied per parsed group:

```ts
score.notes("C5/q, D5/q", { stem: "up" });
score.notes("C4/h, B3/h", { stem: "down" });
```

The EasyScore wiki also supports note-level options like `A5[stem="up"]`. The current MVP lets VexFlow choose stems automatically because it renders one rhythmic stream per measure.

## System And Staves

`System` groups staves and voices and formats them together.

Important calls:

- `system.addStave({ voices })` adds one stave containing one or more voices.
- The returned stave supports `.addClef("treble")` and `.addTimeSignature("4/4")`.
- `system.addConnector()` can connect multiple staves, useful later for grand staff piano notation.
- `system.format()` and `system.draw()` exist, but `vf.draw()` handles drawing all factory-created elements in the current app.

## Compact horizontal layout

Each measure uses its own `System` with:

- `noJustification: true` so the formatter does not stretch note spacing to fill the stave width (see `Formatter.preFormat` when `justifyWidth <= 0`).
- `autoWidth: true` so the stave width shrinks to the minimum needed for that measure's notes.

After layout, the SVG `viewBox` and width are trimmed so the score does not leave a large empty margin to the right of the last note.

## Matrix Conversion Strategy

The matrix remains the source of truth:

```text
matrix data -> note events -> 4/4 EasyScore measures -> VexFlow SVG
```

`matrixToNotes()` scans each row and converts consecutive `1`s into one `NoteEvent`.

Example:

```ts
[1, 1]
```

becomes one event with `durationSteps = 2`.

Each event is converted to a VexFlow pitch:

- `Do -> C4`
- `Re -> D4`
- `Mi -> E4`
- `Fa -> F4`
- `Sol -> G4`
- `La -> A4`
- `Si -> B4`

The current MVP uses one voice per measure:

- The time signature is always `4/4`.
- At the current tempo and step size, each measure contains 8 matrix steps.
- Multiple rows starting at the same step become a chord, e.g. `(C4 E4)/8`.
- Rests are emitted only when the whole matrix is silent at that time.
- Consecutive eighth-note note pieces are beamed in pairs inside each measure. Rests break a beam group.
- Sustained notes are split when another note starts during the sustain. For example, `Do: [1, 1, 1]` plus `Re: [0, 0, 1]` renders as `Do/q` followed by `(Do Re)/8`.

This avoids overlapping rests: a rest should represent silence in the notation stream, not silence in one internal voice while another voice is sounding. Generated rests are split into plain `w`, `h`, `q`, and `8` values instead of dotted rests because VexFlow's strict voice formatter must see exact measure duration.

## Duration Mapping

At the current tempo and time step, one matrix step equals an eighth note:

```text
tempoBpm = 60
timeStepSeconds = 0.5
1 step = 0.5 beats = eighth note
```

Supported EasyScore duration mappings in the app:

- `0.5 beats -> 8`
- `1 beat -> q`
- `1.5 beats -> q.`
- `2 beats -> h`
- `3 beats -> h.`
- `4 beats -> w`

Durations that cannot be represented as one EasyScore note should eventually be rendered as tied notes. That is intentionally not implemented in this MVP.
