> Context: [printing.md](../../../context/frontend/printing.md) · [rendering.md](../../../context/frontend/rendering.md)

# Score PDF export

The **PDF** button of a project's Sheet step (`/projects/:id/sheet`). It lays the sheet out on paper, previews it,
writes a vector PDF and downloads it. No npm dependency writes the PDF: the writer is this app's own code.

The panel is `pages/piece/sheet/frames/FramesPdfDialog.tsx` (implementation 03, Phase 8). It asks the backend for
the pages (`GET /sheet/{uuid}/pages`, whole lines at the printed staff of **Size of the music**, 6.5 mm by default,
with **Space between lines** in millimetres, 6 mm by default; Phase 8A+++), puts each one in a `[data-pdf-page]`
element with its title and number, and `scoreToPdf(host, { selector: "[data-pdf-page]" })` writes them.
`drawPage.ts` reads the engine's SVG: a glyph is a `<use>` of a `<path>` in `<defs>` (the path's own
`scale(1,-1)` applied), beams are `<polygon>`s, and lyrics are `<text>` with one `tspan` per line (a new line is
a new run). The clefs use the smooth curve `s`, now converted (`S`, `T`). No glyph is text, so Bravura is not
embedded (a base font stands in its unused slot): 7 Years on 4 A4 pages is about 60 kB.

The old sheet's panel (`components/time/ScorePdfDialog.tsx`), which printed the pages the vexflow-v2 package drew
(`GridNotationRenderer.renderPages()`, `.grid-page`), was removed in implementation 03, Phase 10 (2026-10-27),
with the package; its page is [deprecated/grid-notation.md](../../deprecated/grid-notation.md). The writer
still accepts `.grid-page` as its default selector and still embeds Bravura when a page draws music as text, so
the sections below that mention them describe what the writer can do, not what the new sheet sends it.

## Files

| File | Does |
|---|---|
| `src/pages/piece/sheet/frames/FramesPdfDialog.tsx` | The panel: paper, orientation, margins, size of the music, space between lines, title, page numbers, preview, Download |
| `src/print/scorePdf.ts` | Walks the drawn pages, assembles the PDF, embeds the font when a glyph needs it, saves the blob |
| `src/print/drawPage.ts` | One page element to PDF drawing operators |
| `src/print/pdf.ts` | A ~120-line PDF writer: objects, streams, `FlateDecode`, xref |
| `src/print/opentype.ts` | Reads `head`/`hhea`/`hmtx`/`cmap` out of an OTF, enough to embed it and find a glyph |
| `public/fonts/bravura.otf` | Bravura, fetched only when a PDF is asked for. Licence beside it (OFL) |

## How a page becomes PDF

Read through `getComputedStyle` and `getCTM`, never off the attributes: a colour may come from a
stylesheet and the brace is drawn inside a scaled group.

| SVG | PDF |
|---|---|
| `line`, `rect` (incl. `rx`), `circle`, `path` (`M L H V C Q Z`) | `m`/`l`/`c`/`re` + `S`/`f`/`B` |
| `fill`, `stroke`, `stroke-width`, `stroke-dasharray`, linecap/linejoin | `rg`/`RG`/`w`/`d`/`J`/`j` |
| `opacity`, `fill-opacity`, `stroke-opacity` | one `ExtGState` per distinct alpha |
| element transforms | `q … cm … Q` from `getCTM()` |
| `text` in Bravura (the old sheet; the new sheet draws no glyph as text) | the embedded font, one glyph per `Tj`, at `getStartPositionOfChar(i)` |
| `text` in a sans/serif face | Helvetica or Times, each normal, bold, italic (oblique) or both, or Symbol, **one word per `Tj`** |
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

When a page draws a glyph as text (the old sheet did; the new sheet does not), Bravura is embedded whole (512 kB, Flate-compressed) as `Type0` / `Identity-H` /
`CIDFontType0` with `FontFile3 /Subtype /OpenType`, addressed by glyph id — the notes sit at
private-use code points that mean nothing outside the font, so there is no encoding worth
pretending to. `/W` lists only the glyphs the piece used. Verified against poppler and pdf.js.

The eight text faces are the PDF built-ins, so they cost nothing: Helvetica, Helvetica-Bold,
Helvetica-Oblique, Helvetica-BoldOblique, Times-Roman, Times-Bold, Times-Italic and Times-BoldItalic in
`WinAnsiEncoding` (a serif face prints as Times, any other as Helvetica: the lyrics blocks of the new sheet can be
bold or italic in Lora, Geist or Montserrat, implementation 03 Phase 8A++), plus `Symbol` for the few mathematical signs the
labels use, which WinAnsi has no slot for.

## Checking a file

```bash
qpdf --check sheet.pdf                 # structure
pdffonts sheet.pdf                     # the new sheet embeds no Bravura; the text faces are base fonts
pdftoppm -r 96 -png sheet.pdf page     # render with a second engine and look
```

The margin check that matters: render every page and confirm the ink bounding box stays inside the
margins. Exclude the bottom 15 mm from that measurement: the folio deliberately sits inside the
bottom margin, as folios do. (The measured figures this section used to give, and the
`[data-system-index]` attributes it read, belonged to the old sheet's pages.)

## Limits

- The preview is shrunk with a CSS `transform` to fit the panel. Every position written to the file
  is one the browser measured, so the shrink is taken off the wrapper for as long as the pages are
  being read. The wrapper is a plain ref, kept apart from the box the pages go in, precisely so it
  can be mutated for that moment.
- Gradients, clip paths, images and filters are not translated. The backend's SVG emits none of
  them; anything added later that does will need a case here.
