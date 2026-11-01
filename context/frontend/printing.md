# Printing the sheet: the PDF export

*The rule of this page: the music is laid out again for the paper, never scaled. The backend draws the whole song at
the paper's width and deals whole lines onto the pages. The page shows them and writes the same vector PDF. This is
the new sheet (implementation 03, Phase 8). The old sheet's printing is at the end, as history.*

A window is as wide as the reader dragged it. A sheet of A4 is 210 mm. The two can never show the same line breaks,
so a printed score is not a picture of the screen: it is the same music laid out again for a different width.

The **Print to PDF** button (the printer icon, in the floating toolbox and in the header) opens the PDF dialog. It is
not shown on a passage. The dialog shows the pages, and **Download** writes them to a file.

## The rule that decides everything: re-wrap, never scale

Shrinking the on-screen sheet to fit A4 would keep every line break and make the notes too small to read. So the
paper is treated as **a narrower available width**. The backend lays the song out for that width, and the lines are
dealt out down the pages.

Three things follow:

- **The margins are real controls, not constants.** Narrower side margins give each line more room, so the music
  breaks in fewer places and the piece takes fewer pages. Nothing changes size.
- **A line is never split across a page turn.** Pages are a budget of whole lines. A line taller than a page gets a
  page to itself rather than being cut.
- **The paper is laid out by the backend, not measured from the screen.** The song is drawn once at the paper's
  width (`render_pages`, see [sheet-drawing.md](../../documentation/services/backend/sheet-drawing.md), section 8).
  The screen's zoom and window do not change the printed line breaks.

## The dialog

`pages/piece/sheet/frames/FramesPdfDialog.tsx` is titled **Download the sheet as a PDF**.

| Control | What it sets | Default | Limits |
|---|---|---|---|
| **Paper** | A4 or US Letter | A4 | |
| **Orientation** | Portrait or Landscape | Portrait | |
| **Side margins** | the margin on each side | 14 mm | 5 to 35 mm |
| **Top and bottom** | the margin at the top and at the bottom | 16 mm | 5 to 35 mm |
| **Size of the music** | the height of a printed staff | 6.5 mm | 5 to 8 mm, in steps of 0.25 |
| **Space between lines** | the white between one line's ink and the next | 6 mm | 1 to 20 mm, in steps of 0.5 |
| **Title** | printed on page one, and the file's name | the piece's name | |
| **Second line** | a line under the title | the project's subtitle | |
| **Number the pages** | the page numbers | on | |

- **Size of the music** and **Space between lines** are kept in this browser (the key `aitu.framesPdf.print`). The
  other controls last while the dialog is open.
- **Space between lines** is in millimetres on paper. It is not the screen's space between lines.
- The title takes 14 mm on page one, and the second line 6 mm more. The first page has that much less room.
- The pages in the dialog are shown at paper size, shrunk to fit the panel. The file is written at paper size.

## Lines to a page

The dialog asks the backend for the pages in staff spaces (a staff space is a quarter of **Size of the music**):
the width of a line, the height of a page, the height of the first page (less the title), and the gap between two
lines. The backend deals whole lines until the next one would not fit.

Measured in implementation 03, Phase 8A+++ on the 10 viewer songs on A4, with the defaults: 5 to 7 lines a page
(median 6), and 44 pages where a 7 mm staff with the screen's space gave 51. The user's copy of 7 Years went from 6
pages to 4 at the same settings.

## What is on the paper

Each page is the engraving of the song at the paper's width, as the backend draws it. The title and the page
numbers are the dialog's own text, drawn into each page element with the same rule: measured, never scaled.

## From pages to a file

The drawn pages are SVG: lines, filled shapes, paths and text. The notes are outlines, so no music font is needed.
The PDF is written as **vector**, operator by operator. It stays sharp at any zoom, and prints at the printer's own
resolution.

The labels and the lyrics are written in the PDF's base fonts: Helvetica or Times, with Symbol for a few signs. They
are the right size and in the right place, but not the screen's letterforms. The file is named after the title
(`pdfFilenameFor`) and carries it as its PDF title.

The writer and its checks are in [score-pdf.md](../../documentation/services/frontend/score-pdf.md).

## History: the old sheet's printing

The old sheet (vexflow-v2) printed through its own renderer and its own panel. Its page had a row of frame numbers
over each line, a title repeated on each page, and a music font embedded in the file. Those went in implementation 03,
Phase 10 (2026-10-27), with the old renderer. The rule above and the five lines to a page are what carried over: the
frame-number strip gave back about 36 px a line. The old renderer is kept in
[documentation/deprecated/grid-notation.md](../../documentation/deprecated/grid-notation.md).

## Where to look deeper

- [sheet-page.md](sheet-page.md): the **Print to PDF** button, in the header and the floating toolbox
- [rendering.md](rendering.md): how the sheet is drawn, by the backend and by the page
- [../../documentation/services/backend/sheet-drawing.md](../../documentation/services/backend/sheet-drawing.md):
  the pages (`render_pages`, section 8) and the route `GET /sheet/{audio_uuid}/pages`
- [../../documentation/services/frontend/score-pdf.md](../../documentation/services/frontend/score-pdf.md): the files,
  the PDF writer, and how to check a file that comes out wrong
