# Context

The goal is to create a clean, scalable SVG representation of a full 88-key grand piano keyboard
that will be used as an interactive component in a web application. During playback, individual
keys or chords will be highlighted to indicate which notes are currently sounding. To keep the
implementation simple and efficient, the application will not generate a different SVG for every
piano key. It renders four compositing layers: a white-key base, reusable pressed-white overlays,
one asset containing all normal black keys, and reusable pressed-black overlays.

The deliverables are therefore `piano-base.svg` (white keys only),
`piano-black-keys.svg`, `pressed-white-key.svg`, and `pressed-black-key.svg`. The pressed-key
assets must have transparent backgrounds and exactly match their corresponding key geometry.

Keep in mind, **the blue overlay will cover the original black key**, provided the pressed-key shape is opaque and rendered above the raw piano.

Do not think of this as “averaging pixels.” It is normal layer compositing:

```text
Top layer:    opaque blue C#3 key
Bottom layer: black C#3 key in piano.svg
Result:       blue C#3 key
```

Transparent areas reveal the piano underneath; the opaque blue area replaces the visible black colour.

## Best workflow for your illustrator

She should **not create 88 different SVG files**. Ask her to create only four assets:

```text
piano-base.svg
piano-black-keys.svg
pressed-white-key.svg
pressed-black-key.svg
```

### `piano-base.svg`

The complete set of white keys and keyboard frame, without black keys.

### `piano-black-keys.svg`

All normal black keys in one transparent-background SVG, aligned to `piano-base.svg`. Keeping this
separate lets the application redraw black keys above every pressed-white overlay.

### `pressed-white-key.svg`

Only one white key in its pressed/highlighted appearance:

* Transparent background.
* Blue key shape.
* Same dimensions and geometry as a white key in the base piano.
* Preferably fully opaque: `opacity="1"`.
* It may include the border, shadow and pressed-state details.

### `pressed-black-key.svg`

Only one black-key-shaped overlay, but coloured blue:

* Transparent background.
* Blue pressed-key shape.
* Same width, height and geometry as a black key.
* Fully opaque.
* It includes whatever outline or shading the pressed black key should have.

The fact that the underlying key is black does not matter. The blue SVG is painted afterward and covers it.

## Layer order

Render the layers in this order:

```text
1. White-key base
2. Pressed white-key overlays
3. Normal black-key layer
4. Pressed black-key overlays
```

The third layer is essential: a pressed white key may colour its full reusable rectangle, but the
normal black keys are painted afterward and remain visible above it.

For your example:

```text
C#3 → pressed black overlay
E3  → pressed white overlay
G#3 → pressed black overlay
```

Conceptually:

```html
<div class="piano">
  <img class="base" src="piano-base.svg">

  <img class="pressed white" src="pressed-white-key.svg">
  <img class="black-keys" src="piano-black-keys.svg">
  <img class="pressed black" src="pressed-black-key.svg">
  <img class="pressed black" src="pressed-black-key.svg">
</div>
```

Each pressed key is positioned over its corresponding key using an `x` coordinate.

## Important: do not use partial transparency

Suppose the pressed black-key overlay uses:

```css
opacity: 0.5;
```

The blue will mix with the original black and become dark or muddy.

Instead, use:

```css
opacity: 1;
mix-blend-mode: normal;
```

The SVG background remains transparent, but the actual blue key must be opaque.

## How to position the reusable overlays

Your code will need a coordinate table:

```javascript
const pianoKeyPositions = {
  "Do#-3": {
    type: "black",
    x: 523,
    y: 0,
    width: 14,
    height: 82
  },
  "Mi-3": {
    type: "white",
    x: 548,
    y: 0,
    width: 24,
    height: 130
  },
  "Sol#-3": {
    type: "black",
    x: 594,
    y: 0,
    width: 14,
    height: 82
  }
};
```

Then the frontend selects the correct reusable asset:

```javascript
function createPressedKey(note) {
  const key = pianoKeyPositions[note];

  const image = document.createElement("img");
  image.src =
    key.type === "black"
      ? "/pressed-black-key.svg"
      : "/pressed-white-key.svg";

  image.style.position = "absolute";
  image.style.left = `${key.x}px`;
  image.style.top = `${key.y}px`;
  image.style.width = `${key.width}px`;
  image.style.height = `${key.height}px`;

  return image;
}
```

## An even better SVG approach

Rather than stacking separate `<img>` elements, place the base piano and pressed shapes inside one parent SVG:

```xml
<svg viewBox="0 0 1400 200">
  <image href="piano-base.svg" x="0" y="0" />

  <!-- E3: white key -->
  <use
    href="pressed-key-assets.svg#pressed-white"
    x="548"
    y="0"
  />

  <image href="piano-black-keys.svg" x="0" y="0" />

  <!-- C#3: black key -->
  <use
    href="pressed-key-assets.svg#pressed-black"
    x="523"
    y="0"
  />

  <!-- G#3: black key -->
  <use
    href="pressed-key-assets.svg#pressed-black"
    x="594"
    y="0"
  />
</svg>
```

This keeps everything vector-based and allows the keyboard to scale without losing quality.

## What your illustrator should preserve

All four SVG assets must use compatible geometry:

* Same coordinate system or known dimensions.
* No background rectangle.
* No clipping that removes shadows or outlines.
* Black and white pressed templates aligned to the top-left reference point of their corresponding key.
* `preserveAspectRatio="none"` only when you intentionally want the overlay stretched.
* Prefer converting Illustrator effects to SVG-compatible fills, strokes and paths.

The illustrator does **not** need to name all the individual piano keys. The application owns the mapping from note name to horizontal position.

## Recommended final architecture

```text
Illustrator produces:
├── piano-base.svg
├── piano-black-keys.svg
├── pressed-white-key.svg
└── pressed-black-key.svg

Application contains:
├── canonical 88-note order
├── coordinate/type information for each key
└── overlay rendering logic
```

For each matrix frame:

```text
["Do#-3", "Mi-3", "Sol#-3"]
```

becomes:

```text
black overlay at Do#3 position
white overlay at Mi3 position
black overlay at Sol#3 position
```

This is substantially easier to maintain than generating 88 separate SVG files, while still producing exactly the rendering you need.
