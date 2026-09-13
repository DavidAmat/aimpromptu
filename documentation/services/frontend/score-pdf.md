> Context: [printing.md](../../../context/frontend/printing.md) · [grid-notation.md](grid-notation.md)

# Score PDF export

The **PDF** button on the Piano Sheet tab (its route is still `/playground/rhythm`). Lays the sheet out on paper, previews it, writes a vector PDF,
and downloads it. No new npm dependency: the PDF is written here.

## Files

| File | Does |
|---|---|
| `src/components/time/ScorePdfDialog.tsx` | The panel: paper, orientation, margins, title, page numbers, live preview, Download |
| `src/print/scorePdf.ts` | Walks the drawn pages, assembles the PDF, embeds the font, saves the blob |
| `src/print/drawPage.ts` | One `.grid-page` element → PDF drawing operators |
| `src/print/pdf.ts` | A ~120-line PDF writer: objects, streams, `FlateDecode`, xref |
| `src/print/opentype.ts` | Reads `head`/`hhea`/`hmtx`/`cmap` out of an OTF — enough to embed it and find a glyph |
| `public/fonts/bravura.otf` | Bravura, fetched only when a PDF is asked for. Licence beside it (OFL) |
| `vexflow-v2` → `GridNotationRenderer.renderPages()` | The seam. Draws the score again as paper pages |

`src/components/time/TimeScoreView.tsx` gained one prop, `onRendererChange`, which hands the live
`GridNotationRenderer` up to the page so the panel can print from it.

## The seam

`renderPages()` is a thin wrapper over the package's `renderScorePages`. It exists on the renderer,
not at the call site, so that a printed page cannot silently lose an option the screen was using.
In particular it passes **the frame widths this renderer already measured**. `renderScorePages` will
otherwise measure its own, and it does not know about `silenceGroupPx` or `frameGroup` — the two
numbers that decide how much room a silence gets — so the print would be spaced differently from the
screen.

Its print defaults, all overridable by the caller:

| Default | Why |
|---|---|
| `showTimestamps: false`, `frameCells: false`, `rangeMarkers: false` | ways of pointing at something; nothing on paper to point with |
| `frameLabels: false` | a column number is an address and nobody can click one on paper. Also gives back the 52 px strip reserved to hold the numbers — `GRAND_STAFF_TOP_PADDING` (60) becomes `GRAND_STAFF_TOP_PADDING_BARE` (24) |
| `runningHead: false` | the piece is named once, where it starts |
| `systemPadding: { bottom: 20 }` | on screen the page can grow downwards so the slack under the lower staff is set generously; on paper it is the difference between four lines and five |

`systemGap` (the panel's **extra space between lines**) is added on top of that padding. Together
these take a page of this score from three lines to five, with the staff gap inside each line
untouched. `resolveSystemPadding` is the single function both the paginator's budget and the drawing
go through, so a page can never be planned for a system taller than the one that gets drawn.

## How a page becomes PDF

Read through `getComputedStyle` and `getCTM`, never off the attributes: a colour may come from a
stylesheet and the brace is drawn inside a scaled group.

| SVG | PDF |
|---|---|
| `line`, `rect` (incl. `rx`), `circle`, `path` (`M L H V C Q Z`) | `m`/`l`/`c`/`re` + `S`/`f`/`B` |
| `fill`, `stroke`, `stroke-width`, `stroke-dasharray`, linecap/linejoin | `rg`/`RG`/`w`/`d`/`J`/`j` |
| `opacity`, `fill-opacity`, `stroke-opacity` | one `ExtGState` per distinct alpha |
| element transforms | `q … cm … Q` from `getCTM()` |
| `text` in Bravura | the embedded font, one glyph per `Tj`, at `getStartPositionOfChar(i)` |
| `text` in a sans/serif face | Helvetica / Helvetica-Bold / Times-Italic / Symbol, **one word per `Tj`** |
| the page's HTML title, running head and folio | measured with a `Range` per character; baseline from the font's ascent plus the browser's half-leading |

Two decisions worth knowing:

- **Per-glyph placement for notation, per-word for text.** A music glyph goes exactly where the
  engraver put it. A word does not: the labels are laid out in whatever sans face the machine has
  and the PDF writes Helvetica, so placing each letter at the browser's position would print
  Helvetica shapes with another font's letter spacing — visibly gappy. Each word is placed once and
  left to space itself: right inside the word, off by a hair at its end.
- **One transform per page.** `q 0.75 0 0 -0.75 0 H cm` — CSS pixels to points, and the y axis
  turned over, because a PDF measures up from the bottom of the sheet. Text then carries a negative
  y scale in its own matrix so glyphs come out the right way up. Nothing else in the converter has
  to know what size the paper is.

## Fonts in the file

Bravura is embedded whole (512 kB, Flate-compressed) as `Type0` / `Identity-H` /
`CIDFontType0` with `FontFile3 /Subtype /OpenType`, addressed by glyph id — the notes sit at
private-use code points that mean nothing outside the font, so there is no encoding worth
pretending to. `/W` lists only the glyphs the piece used. Verified against poppler and pdf.js.

The four text faces are the PDF built-ins, so they cost nothing: Helvetica, Helvetica-Bold,
Times-Roman and Times-Italic in `WinAnsiEncoding`, plus `Symbol` for the few mathematical signs the
labels use (`≈` in the passage header is the one that matters) which WinAnsi has no slot for.

## Checking a file

```bash
qpdf --check sheet.pdf                 # structure
pdffonts sheet.pdf                     # Bravura should read "CID Type 0C (OT) … emb yes"
pdftoppm -r 96 -png sheet.pdf page     # render with a second engine and look
```

The margin check that matters: render every page and confirm the ink bounding box stays inside the
margins. On the 8-page test piece at 14 mm sides and 16 mm ends, music ink starts at 14.6 mm from
the left, 17.2 mm from the right and 16.9 mm from the top on every page. Exclude the bottom 15 mm
from that measurement: the folio deliberately sits inside the bottom margin, as folios do.

To check that a line that breaks carries on below, read the systems off the DOM — every
`[data-system-index]` carries `data-start-frame` and `data-end-frame`, and they should tile the
piece with no gap and no overlap.

## Limits

- The preview is shrunk with a CSS `transform` to fit the panel. Every position written to the file
  is one the browser measured, so the shrink is taken off the wrapper for as long as the pages are
  being read. The wrapper is a plain ref, kept apart from the box the pages go in, precisely so it
  can be mutated for that moment.
- The panel's contents mount a render *after* it opens, so the host element is held as **state**,
  not a ref: an effect that read a ref on the first pass found nothing and never drew.
- Gradients, clip paths, images and filters are not translated. The drawing package emits none of
  them; anything added later that does will need a case here.
