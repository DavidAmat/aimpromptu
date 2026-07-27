# Task 8.1.1 — Piano SVG assets and key highlighting

Implements `context/music/piano_svg/01-piano-svg.md` exactly — read it in full first.

## Subtask 8.1.1.1 — Assets

Four files in `aitu-frontend/public/piano/`: `piano-base.svg` (white keys only),
`piano-black-keys.svg` (all normal black keys), `pressed-white-key.svg` and
`pressed-black-key.svg` (blue, opaque fill, transparent background, geometry matching their
keys). The human will provide the illustrator assets; until then generate programmatic placeholder
SVGs with correct geometry so all dependent work proceeds.

## Subtask 8.1.1.2 — Coordinate table

`src/piano/keyPositions.ts`: for each of the 88 keys — type (white/black), x, y, width, height in the base SVG coordinate system. Black keys narrower (~70% ratio, confirm against the real asset; the human will provide measured white-key px widths). Derive programmatically from standard keyboard geometry, verified visually.

## Subtask 8.1.1.3 — Piano component

`<Piano pressedKeys orientation>` renders exactly four visual layers: white-key base, pressed
white overlays, all normal black keys, then pressed black overlays. This guarantees a highlighted
white key can never cover a neighbouring black key. Overlays use opacity 1 and normal blend. The
component supports horizontal and rotated-vertical orientation via a transform on the parent SVG.

## Acceptance

Manual trial: a demo page toggling arbitrary chords (e.g. Do#3+Mi3+Sol#3) shows correct blue
overlays in both orientations, scaling cleanly. Normal black keys remain visibly above a pressed
white key; pressed black keys remain the topmost layer.
