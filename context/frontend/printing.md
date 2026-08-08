# Printing the sheet — the PDF export

A window is as wide as the reader dragged it. A sheet of A4 is 210 mm. The two can never show the
same line breaks, so a printed score is not a picture of the screen: it is the same music laid out
again for a different width.

The **PDF** button on the Rhythm tab's floating bar opens a panel that does exactly that, shows the
resulting pages, and writes them to a file.

## The rule that decides everything: re-wrap, never scale

Shrinking the on-screen sheet to fit A4 would keep every line break and make the notes too small to
read — and the smaller the window the reader happened to have, the worse the paper would be. So the
paper is treated as **a narrower available width**: the music re-wraps to it the way it re-wraps
when you drag the window in, and the lines are then dealt out down the pages. This is decision D5 in
the notation package, and pagination is built on top of it (D41).

Three things follow, and they are the whole reason the panel looks the way it does:

- **The margin is a real control, not a constant.** Narrower side margins give each line more room,
  so the music breaks in fewer places and the piece takes fewer pages. On the test piece: 14 mm →
  12 pages, 5 mm → 11 pages, 35 mm → 17 pages. Nothing changes size.
- **A line is never split across a page turn.** Pages are a budget of whole lines; a line taller
  than a page still gets a page to itself rather than being cut.
- **Where a line breaks, the next line starts at exactly that column.** Nothing is dropped at a
  break and nothing is printed twice.

## What the printed page carries over from the screen

Everything the reader decided, and — importantly — the **frame widths this render measured**, not a
fresh measurement. Frames are as wide as their contents, and silence is charged per group rather
than per column, so re-measuring for print would print the same piece with different spacing from
the one that was approved on screen.

That is why printing goes through one method on the renderer rather than through a call site that
lists options by hand:

```ts
renderer.renderPages(container, { pageSize: "a4", marginsMm, title, subtitle, pageNumbers })
```

What does **not** come across is the editing chrome — frame cells, the corner marks on annotated
stretches, the selection, the playhead, the timestamps. Each of those is a way of pointing at
something, and there is nothing on paper to point with.

## From pages to a file

The drawn pages are SVG: lines, rectangles, filled polygons and glyphs, and nothing else. So the
PDF is written as **vector**, operator by operator, rather than by photographing the page — it stays
sharp at any zoom, prints at the printer's own resolution, and a twelve-page score comes to about
450 kB, most of which is the music font travelling with the file.

Bravura is embedded, so the notes are the same shapes on any machine. The labels — the ruler, the
passage header, the title — are written in the PDF's built-in Helvetica, so they are the right size
and in the right place but not quite the same letterforms as on screen.

## Where to look deeper

- [../../documentation/services/frontend/score-pdf.md](../../documentation/services/frontend/score-pdf.md)
  — the files, the PDF object graph, the fonts, and how to check a file that comes out wrong
- [../../documentation/services/frontend/grid-notation.md](../../documentation/services/frontend/grid-notation.md)
  — the drawing package and how it is installed
- [rendering-pipeline.md](rendering-pipeline.md) — where frames become notation
