# The sheet toolbox, the keyboard panel, and trills

What the Sheet step can say about the whole piece. The overview of the page, the defaults, undo and
saving is [annotations.md](annotations.md). Code: `aitu-frontend/src/pages/piece/sheet/SheetToolbox.tsx`,
`PianoToolboxes.tsx`, and the Trills panel in `SheetPage.tsx`.

## The sheet toolbox

Opened from the floating bar (the sliders icon, *Sheet toolbox*). Four tabs; every change in it is
one undo step, except zoom and the frame numbers, which are how the page is looked at and are not
saved.

| Tab | Content |
|---|---|
| **Title** | Title, subtitle and artist printed above the sheet. Each is written when you leave the field or press Enter, so a word is one undo step, not one per letter. An empty title prints the project's name. The PDF takes the title |
| **Key** | The key signature of the piece, on both clefs. It changes spelling only: no note moves. When another key would print fewer accidentals, a button offers it: *Use B major (5 fewer accidentals)* |
| **Figures** | The **main figure**: what the highest pile of gaps is called (blanca, negra, corchea, semicorchea, as icons). A negra on a first write. Changing it renames every note by proportion and moves nothing (D-18); the sheet is drawn again by itself |
| **Layout** | Space between notes, space between lines, size of marks, zoom (also ⌘ and scroll over the sheet), frame numbers on or off, *Hide decorative notes*, and *Group high notes under 8va (n)* |

Phase 7 of implementation 02 adds **Transpose** (notes and figures, which replaces **Figures**) and
**Lyrics**.

Notes on **Layout**:

- **Space between notes** is added to every column that carries a note and to no silence, so a held
  note still takes exactly the room the wall clock gives it. It is not a zoom. A stretch that needs
  more than the rest of the page is the range toolbox's **Spacing**.
- **Space between lines** is the white between one pair of staves and the next. It is vertical, so
  no column changes width. One line can also be spread on its own with the small handle between its
  two staves; that is keyed by a column, so it stays with the music when the page re-wraps.
- **Size of marks** sets how big every mark over and under the staff is drawn (fingering, words,
  `tr`), one number for all of them.
- **Frame numbers** (`f0`, `f100`) are how a mark is addressed; off to begin with, because they take
  most of the room above every staff and mean nothing musically.
- **Hide decorative notes** leaves off a sixteenth or shorter right before an eighth or longer, and
  the note before it runs on.
- **Group high notes under 8va** replaces the brackets on the page with the ones the notes ask for
  (the same rule as the first write). A bracket already open is what a second one has to beat.

## The keyboard panel

*Show the keyboard* in the `⋯` of the floating bar. It draws the keys sounding under the playhead,
the right hand in blue and the left in orange, with a number on every Do. Four colours, named in the
panel's legend: **RH onset** and **LH onset** are struck at the playhead; **RH sustain** and **LH
sustain** are still sounding from a note struck earlier, whose notehead is where it began. That is
why two keys of the same name can be lit where the page draws one notehead.

It edits as well as reports. Click a lit key and that note comes off the page. Click a dark one and
it is **added to the recording**, on the hand **Add to: Right / Left** says, taking the length that
hand is already holding. Command-Z reaches an addition.

## Trills

*Find trills* in the `⋯` asks the backend for runs where two notes take turns three times or more,
and lists them in a small panel: the two notes, the hand, the time. ✓ writes one as a trill. A
suggestion only: a missed trill costs nothing, a wrong one hides notes that were really played. A
trill prints as `tr` over the note with a wavy line to where the shake stops; every alternation
stays in the recording and still plays. *Print every trill as its notes* removes them all.

## Where to look deeper

- [annotations.md](annotations.md) — the page, the defaults, undo and saving
- [printing.md](printing.md) — Print to PDF
- [rendering.md](rendering.md) — how the sheet is drawn and wrapped
