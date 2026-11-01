> Context: [printing.md](../../../context/frontend/printing.md) · [rendering.md](../../../context/frontend/rendering.md)

# Score PDF export

The **Print to PDF** button of a project's Sheet step (`/projects/:id/sheet`). It asks the backend for the pages, shows
them, writes a vector PDF and downloads it. No npm dependency writes the PDF: the writer is this app's own code.

## The panel and the pages

The panel is `pages/piece/sheet/frames/FramesPdfDialog.tsx` (implementation 03, Phase 8). It asks
`GET /sheet/{uuid}/pages` with the paper in staff spaces (a space is a quarter of **Size of the music**):

- `width`: (paper width − 2 × side margin) / space, less 8 (the SVG's own margins: `SVG_MARGINS`);
- `height`: (paper height − 2 × top and bottom margin) / space;
- `first`: the same, less the title block (14 mm for the title, 6 mm more for the second line);
- `gap`: **Space between lines** / space.

The request waits 220 ms after the last change, so a drag does not lay the piece out at every pixel. The answer is one
`svg` per page. Each goes into a `[data-pdf-page]` element with its title and its number. Then
`scoreToPdf(host, { selector: "[data-pdf-page]", title })` writes them.

`print/drawPage.ts` reads that SVG. A glyph is a `<use>` of a `<path>` in `<defs>`, and the path's own `scale(1,-1)` is
applied. Beams and the other shapes are `<polygon>`, `<path>` and `<rect>`. Lyrics are `<text>`, with one `tspan` per
line. The path converter reads the smooth curves `S` and `T` and turns them into the PDF's own curves.

## Files

| File | Does |
|---|---|
| `src/pages/piece/sheet/frames/FramesPdfDialog.tsx` | The panel: paper, orientation, margins, size of the music, space between lines, title, second line, page numbers, the pages, Download |
| `src/print/scorePdf.ts` | Walks the page elements, assembles the PDF with the base fonts, saves the blob (`saveBlob`, `pdfFilenameFor`) |
| `src/print/drawPage.ts` | One page element to PDF drawing operators (`drawPage`, about 650 lines) |
| `src/print/pdf.ts` | A ~115-line PDF writer: objects, streams, `FlateDecode`, the cross-reference table |

## How a page becomes PDF

Everything is read through `getComputedStyle` and `getCTM`, never off the attributes. A colour may come from a
stylesheet, and a brace is drawn inside a scaled group.

| SVG | PDF |
|---|---|
| `line`, `rect` (incl. `rx`), `circle`, `path` (`M L H V C Q S T Z`) | `m`/`l`/`c`/`re` + `S`/`f`/`B` |
| `fill`, `stroke`, `stroke-width`, `stroke-dasharray`, linecap/linejoin | `rg`/`RG`/`w`/`d`/`J`/`j` |
| `opacity`, `fill-opacity`, `stroke-opacity` | one `ExtGState` per distinct alpha |
| element transforms | `q … cm … Q` from `getCTM()` |
| a glyph (`<use>` of a path) | the path, drawn with the use's transform |
| `text` in a sans or serif face | Helvetica or Times, each normal, bold, italic (oblique) or both, or Symbol; **one word per `Tj`** |
| the title and the number (HTML) | measured with a `Range` per character; baseline from the font's ascent plus the browser's half-leading |

Two decisions worth knowing:

- **Notes are placed where the engraver put them; words are placed once.** A music glyph goes exactly where the engraver
  put it, so it is drawn as a path. Labels and lyrics are laid out in whatever sans face the machine has, and the PDF
  writes Helvetica or Times. Placing each letter at the browser's position would print Helvetica shapes with another
  font's spacing, visibly gappy. So each word is placed once, at its first letter, and left to space itself. A space,
  or a new line of a lyric, starts a new word.
- **One transform per page.** `q 0.75 0 0 -0.75 0 H cm`: CSS pixels to points (96 px to 72 pt), and the y axis turned
  over, because a PDF measures up from the bottom of the sheet and a browser measures down. Text then carries a negative
  y scale in its own matrix, so its glyphs come out the right way up. Nothing else in the converter has to know the size
  of the paper.

## Fonts in the file

No music font is embedded. The notes are paths, so they are the same shapes on any machine.

Text is written in nine base fonts, which every PDF reader has, in `WinAnsiEncoding` (`PDF_BASE_FONTS` in
`drawPage.ts`):

- `Helvetica`, `Helvetica-Bold`, `Helvetica-Oblique` and `Helvetica-BoldOblique` for a sans face;
- `Times-Roman`, `Times-Bold`, `Times-Italic` and `Times-BoldItalic` for a serif face (the lyrics blocks can be bold or
  italic in Lora, Geist or Montserrat, and a serif one prints as Times);
- `Symbol` for the few mathematical signs the labels use, which WinAnsi has no slot for.

The old sheet's Bravura embedding (a `Type0` font with `CIDFontType0`, and `public/fonts/bravura.otf`) left with the old
renderer in implementation 03, Phase 10 (2026-10-27). The writer has no code for it now.

## Checking a file

```bash
qpdf --check sheet.pdf                 # structure
pdffonts sheet.pdf                     # the new sheet embeds no font: the text faces are base fonts
pdftoppm -r 96 -png sheet.pdf page     # render with a second engine and look
```

The margin check that matters: render every page and confirm the ink bounding box stays inside the margins. Exclude the
bottom 15 mm from that measurement: the folio sits inside the bottom margin on purpose, as folios do.

## Limits

- The pages in the panel are shrunk with a CSS `transform` to fit it (`PREVIEW_WIDTH`, 460 px). **Download** takes that
  transform off the wrapper while the pages are read, so every position in the file is one the browser measured. The
  wrapper is a plain ref, kept apart from the box the pages go in, so it can be changed for that moment.
- Gradients, clip paths, images and filters are not translated. The backend's SVG emits none of them today. Anything
  added later that does will need a case in `drawPage.ts`.

## Where to look deeper

- [printing.md](../../../context/frontend/printing.md): the rule, the dialog's controls and the lines to a page
- [sheet-drawing.md](../backend/sheet-drawing.md): the pages on the backend (`render_pages`, section 8)
- [components.md](components.md): the modules of the sheet page
- [../../deprecated/grid-notation.md](../../deprecated/grid-notation.md): the old sheet's drawing package (removed in
  implementation 03, Phase 10)
