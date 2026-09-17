# What a reader can say about a piece

Every editorial decision the app offers, where the control is, and what it changes. None of it
changes the recording except where this page says so.

## The two selections, and the two toolboxes

There are two ways to pick something on the sheet, and each opens its own panel **beside what you
picked**. Both panels can be dragged, and once dragged they stay where you put them.

- **Noteheads** — click one, ⌘-click to add, or drag a rubber band across the staves. Opens the
  **note toolbox**; every control applies to the whole set. It also **takes the recording to where
  those notes are** — the first column of the set, when several are picked — so the keyboard panel
  draws the chord you just clicked instead of whatever the cursor was standing on. The page does not
  scroll: you are already looking at the notes.
- **A stretch of time** — click above the staves. The stretch **starts where you clicked** and runs
  for one group, which is a starting point to drag from; shift-click another cell to extend it.
  Opens the **frames toolbox**, which is about a stretch rather than about notes. Its first row is
  **Applies to: Both / R / L** — pick one hand and the purple highlight shrinks to that hand's
  staff, and **Clef** and **Octave** act on that hand alone.

**Either selection can be handed to the other**, from the button in the panel's own title bar. On
the note toolbox **Select frames** marks the stretch from the first picked note to the last,
whichever hand they are on — and when they are all on one hand, that hand's pill is already pressed
when the frames toolbox opens. On the frames toolbox **Select notes** picks every note that *begins*
inside the stretch, on the staves **Applies to** names, and opens the note toolbox on them. They are
two ways of saying the same thing about the same music, so picking it twice by eye — once on the
staves and again on the ruler — was work the page could do exactly. The button is greyed when the
stretch holds no notes on the hand it is about, and neither direction leaves the other selection
behind: what you hand over is what is picked.

A stretch that carries an edit draws **two corner marks in its own colour**, so it can be seen
without being selected. Click a corner to open that stretch again; each edit it holds has its own
**Remove**. Hovering a corner used to outline its whole stretch as well — that is gone. A
pointer on its way to the ruler crosses a corner, so an outline appeared around some unrelated
stretch and was then replaced by your own purple band, which reads as the page picking something by
itself and changing its mind. The corner's tooltip names the columns, which is the same answer in
words and does not draw over the music to give it.

Both ends of a marked stretch can be pulled to any column. A group is about a second, far coarser
than the note a reader is aiming at, so without handles there was no way to say "up to there".

**The frames toolbox opens to the left of where the stretch starts**, or below the staves when there
is no room there — and then it stays there. Dragging a stretch's handle does not move it; only
dragging the panel does. A stretch grows to the right as you drag its right-hand handle, so a panel on that
side is a panel the stretch ends up underneath — and you would have to drag the panel away to finish
the gesture you were in the middle of. The note toolbox still opens to the right, because a set of
noteheads is the size it is.

## About notes

The panel is controls rather than prose: seven shapes, five numbers, two letters and four icons,
with the sentences in the tooltips.

**Pick one note and the panel is titled with its name**, in solfège — `Do 4`, `Do-# 3`, `Re-b 5`.
Middle C is `Do 4`, which is the reckoning the keyboard, the roll and every tooltip already use, and
the column is still under it. Pick several and the title counts them instead: a chord is three notes
at one moment, and three names in a title is a list rather than an answer — the keyboard under
**Show piano** is where a chord is read.

The name is **the one the sheet prints**, not one worked out from the key that was pressed. The same
black key is written `Do-#` in a sharp key and `Re-b` in a flat one, so the panel spells it against
the signature sounding at that column, through the same code the noteheads come from. An octave
bracket does not change it and neither does sending the note to the other staff: both of those move
where a note is *drawn*, and the name is what it **sounds**. `npm run check:note-names` pins it.

| Control | What it does |
|---|---|
| **The seven figures** | A row of the shapes themselves — redonda to semifusa. The one every picked chord is drawn as is filled in; pressing another names all of them at once. Nothing moves in time. The ⌫ beside them goes back to what the score called them |
| **Fingering 1–5** | One number per note. Several on a chord print stacked, low to high. ⌫ takes them off |
| **Hand: R / L** | Which hand plays them. Corrects the split |
| **Beam: 🔗** | Beam every picked chord as one group, whatever the page's own rule makes of them. Needs two or more whole chords, all a corchea or shorter — a negra has no beam to share |
| **Beam: ✂** | Cut the beam in front of them. Refused unless the whole chord is picked — a beam holds every note of a chord |
| **Beam: =** | Set the picked run an equal distance apart, whatever the other hand needs at those moments |
| **Beam: + / −** | Open the even run further, or close it back. Disabled until **=** has been pressed, because until then there is no one distance to be a multiple of |
| **Decoration** | Opens **Piano Edit**: a keyboard with the note being decorated in lavender and the decoration in pink. Click a key to say what sounds just before it. Every one of them leans on its note |
| **Small** | Print the picked notes cue-sized. It reads the hand off the selection, so nothing has to be said twice |
| **Trill** | Write the picked notes as one held note with `tr` and a wavy line over it. Needs three onsets or more in one hand |
| **🗑** | Take them off the page, or press **Delete** (⌫ on a Mac). For a note the transcriber invented out of a pedal blur. Command-Z brings them back |
| **Octave brackets** | Four chips per hand over any stretch you mark, in the frames toolbox. The bracket begins just before the first note it covers and its hook falls just after the last one, so which notes are inside it is never a matter of judgement. Either end can be pulled on the sheet itself, and the whole bracket can be hidden — see below |

Two of these are worth testing carefully, because they reach further than they look.

**Moving a note between hands also changes what its old and new neighbours are called.** A note's
printed length is the gap to the next onset in the same hand, so check the two notes either side of
the one you moved. The correction is written onto the recording rather than kept as an overlay, so
everything downstream follows it.

**Taking a note off the page does the same thing**, for the same reason — the neighbour is
lengthened to cover it, which is the point. It is staged rather than applied: a floating bar carries
**Save** and **Discard**, and nothing reaches the recording until Save.

Renaming a tresillo loses its `3`, on purpose. The name says "draw it as this" and the bracket says
the opposite.

## About stretches

| Tab | Reads the hand pills? | What it does |
|---|---|---|
| **Key** | No | A stretch can have its own signature. It is drawn on both clefs whatever hand is chosen |
| **Clef** | **Yes** | The hand prints a treble or a bass clef over the stretch, and goes back to its own after it |
| **Octave** | **Yes** | The four brackets, an eye that hides one and a trash that removes it. Narrow to one hand and the panel stops asking which hand twice |
| **Spacing** | No | A handle setting how much room the stretch takes, from a quarter to four times what the page measured. The sheet redraws as the handle moves |
| **Lyrics** | No | A line of words drawn above the right hand across the stretch. The block is dragged where you want it, its right edge folds the words into more lines, and a handle sets the text size |
| **Re-record** | No | Play the stretch again, over the recording |

**Trill** and **Small** used to be here and are now in the note toolbox. Both are statements about
notes — "these notes are a shake", "these notes are decoration" — so a selection answers the hand
and the columns at once, and the panel stopped asking for either.

### An octave bracket, once it is on the page

Three things can be done to a bracket without going back to the columns that made it.

**Pull either end.** A band runs along the dashed line and lights up under the pointer; its two ends
are `ew-resize` and each moves the bracket by whole columns. A bracket pulled over another on the
same hand takes it over — enlarge an `8va` across a `15ma` and the `15ma` is gone. The other hand is
never touched, and the two ends are held one column apart so a bracket can never invert. The drag is
reported once, when the pointer is let go, so the sheet is rebuilt once per gesture; Command-Z puts
the bracket back the length it was.

**Drop a tip on another line and every frame in between comes inside the bracket.** The sheet wraps,
so the frames you want next are as often on the line below as further right; the frame under the tip
is read from the whole page, not from the line the tip is drawn on. It works both ways — drag the end
tip back up to an earlier line and the bracket gives those frames back. While you are dragging, the
dashed line on the line you started from runs to the margin, because there is no more room on it to
show; let go and the sheet redraws with the bracket across both.

**While you are holding a tip the page shows where it would land.** An amber band over every line
the bracket would cover, a solid line at the column the end would drop into with its number beside
it, and fainter lines at the columns either side, so moving a little to the right is a step you can
see rather than a guess. It is amber rather than the purple a marked stretch is painted in: both are
often on the page at once, and two purple bands over one passage read as one selection. All of it is
gone the moment you let go — nothing is drawn on hover, and nothing is left on the page.

**Click the band and you have the bracket, and only the bracket.** The box around the dashed line
stays lit, with a tip at each end to pull, until you pick something else or press anywhere else on
the sheet. It used to hand the columns under it to the frames toolbox as well, so one press made two
selections — the bracket you were reaching for, and a purple stretch painted over it — and the two
got in each other's way. **The corner marks are still the way to the stretch**: click one and the
frames toolbox opens with the **Octave** pill on the right hand or the left.

**Hide it.** The eye in the Octave pill, or **Delete** with a stretch marked and no note picked,
takes the dashed line and the `8va` off the page — and leaves the notes written exactly where the
bracket puts them. That is the point: a player who already knows a passage is played an octave up
does not need it said over every bar, and above the right hand is the most crowded strip on the
page. Un-shifting the notes would be a different edit and would give a reader asking for less ink a
wall of ledger lines instead.

**Hiding is not removing.** A hidden bracket is still in the reading, still saved with the piece,
and still draws its corner marks — which are the way back to it. The trash beside the eye is the
only way to remove one, and that does put the notes back where they sound.

**A clef change is the honest answer to a hand that spends a page far outside its own staff**, and a
better one than an octave bracket where the passage is long: under a bracket the notes are written
an octave from where they sound and the reader has to keep that in mind, while on the other clef
they are written exactly where they sound. Nothing moves and nothing is renamed — a clef decides
which lines the noteheads are drawn on and nothing else.

**Spacing is both staves, whichever hand is chosen.** A column is one slice of wall clock and the
two hands share it — that is the whole of what makes them line up (D-22) — so there is no such thing
as widening a column for one hand. The panel says so.

**Words are hand-independent**: they belong to the piece rather than to a staff. They are drawn
**above the right hand**, in a block of its own at the top of the line — above the octave brackets,
because a bracket's height comes from the highest note it covers and so there is no distance from
the staff at which words are safe. The column numbers are left off over the columns a lyric covers,
so the two kinds of text in that strip cannot print over each other.

**The block is the reader's.** Drag it anywhere; drag its right edge to narrow it and the words wrap
into more lines; the **Text size** handle in the tab sets how large they are. Everything is still
keyed by the columns, so the words travel with their music when the page re-wraps, and **Put the
block back over its stretch** clears the placement. A block that has been moved stops widening its
own columns, because it is not over them any more.

A lyric nobody has moved never widens the layout beyond making room for its own words, because the
spacing of the page comes from the notes and never from an annotation.

**Even spacing costs width, and that is the point.** Each column is as wide as what is drawn in it
and **both staves share the column**, so a run of even corcheas in one hand comes out unevenly
spaced wherever the other hand needs room at one of those moments. The page is not wrong when that
happens — the space really is being used — but a beam of equal notes that is not equally spaced
reads as an uneven performance, which is the worse lie. **=** sets every gap in the run to the
widest gap it already had; **+** opens it further. It moves whatever the other hand plays underneath,
which is the trade.

**− goes below even, and it is meant to.** At 100 % nothing has to give way, because every gap is
then the sum of the widths its columns asked for. But the widest gap in a run is usually wide
because of the *other* hand — a four-note chord with accidentals under one of these notes — so
evening a run to it makes the whole run as wide as its worst moment. Below 100 % the notes crowd and
may touch. That is visible, it is one press back, and it is your call rather than the page's.

**Cue size is asked for, never inferred.** A florid run in one hand set at full size crowds the
other hand off the system; set smaller it takes less width and reads as decoration, which is what it
is. It may move the notes inside the mark and nothing outside it.

## About the whole piece

The ladder — `corchea = 217 ms · ≈138 BPM` — is printed at the **very top of each system**, above
the frame numbers. It used to sit just over the treble staff, which is also where an octave bracket
goes, so a piece opening under `8va` printed the two through each other.

- **Name the beat** — click a bar in the peak plot, give it a name, write the sheet.
- **Write it one step longer / shorter** — the same playing in longer or shorter note values.
  Neither reading is more correct; pick the one that is easier to read.
- **Key signature** — the app measures a suggestion from the notes and you accept or change it. A
  transcription has no key, so everything used to print in C; on one real piece that was 242
  accidentals that did not need to be there.
- **Smaller / Larger** — how big every mark over and under the staff is drawn. One number rather
  than one per kind, because a reader crowding a dense passage wants all of them smaller.
- **Spread one line** — the small handle between the two staves of a line, dragged or arrowed. It
  opens out **that line and no other**, for the one wide chord or the passage reaching down that
  needs the room. Keyed by a column, so it stays with the music when the page re-wraps.
- **Space between lines** — a slider beside the key signature. The number on it is the white space
  itself: at 0 one set of pentagrams sits directly under the one above, and the default is 72. One
  fixed gap cannot be right for every piece — most sheets are mostly white space, and on a piece
  with high notes a low note of the left hand and a high note of the next line's right hand reach
  towards each other through it until the two runs of ledger lines meet. It is vertical, so no
  column changes width and no note moves.
- **Group high notes under 8va** — the app proposes brackets from how far outside its staff a hand
  is written, and you keep, move or clear them. **A bracket already open is what a second one has
  to beat**: a passage that has really changed register gets its own, but one high note inside an
  open `8va` is carried by it rather than given a `15ma` of its own. How far out a note is is
  measured under the bracket you are already reading, never against the bare staff.
- **Show frame numbers** — a pill beside **Show piano**, **off to begin with**. The column numbers
  over the guides — `f0`, `f100` — are how a mark on this page is addressed and how you say where
  something is, so they are one click away; they are also fifty-two of the sixty pixels above every
  staff, spent on numbers that mean nothing musically. The dashed guides and the stretches you can
  select stay either way, and turning them off makes every line shorter.
- **Space between notes** — a second slider beside the key signature, from 0 to 48 pixels. Each
  column is already as wide as what is drawn in it, which reads a texture well and is tighter than a
  player wants when the next thing to happen is a blanca. This is added to **every column that
  carries a note and to no silence**, so the notes open up and a held note still takes exactly the
  room the wall clock gives it. It is not a zoom. A stretch that needs more than the rest of the
  page is still the **Spacing** pill's job.
- **Trills** — the app finds alternating runs and offers them. A suggestion only: a missed trill
  costs nothing, a wrong one hides notes that were really played. A trill prints as `tr` over the
  note with a wavy line running to where the shake stops.
- **The keyboard panel edits, as well as reports** — **Show piano** draws the keys sounding under
  the playhead, the right hand in blue and the left in orange, with a **number on every Do** so a
  key can be named without counting. Four colours, named in the panel's own
  legend: **RH onset** and **LH onset** are struck in the column under the cursor, **RH sustain** and
  **LH sustain** are still sounding from a note struck earlier — whose notehead is back where it
  began, not under the cursor. That is why two keys of the same name can be lit where the page draws
  one notehead. Click a lit key and that note comes off the page. Click a dark one and it is **added to the recording**, on whichever hand the **Add
  note R / L** pills say, taking the length that hand is already holding. Command-Z reaches an
  addition; the note is marked removed again, which takes it out of the matrix, the gaps and the
  sheet.

## Taking it back

**Command-Z takes the last edit back, Shift-Command-Z puts it back**, and the two are also buttons
beside **Write the sheet** saying what they are about — *Undo: Octave bracket*. Control-Z and
Control-Y on Windows. In a text field the keys do what they do in any text field, so typing
Command-Z in **Words** takes back what you typed.

**One press is one step**, however many things it changed. Taking a note off the page also clears
its fingering, and one undo brings both back — whether the notes went by the trash button or by the
**Delete** key, because both are the same call. The key stands down while you are typing in a field,
where Backspace already means something.

Four edits are written onto the **recording** rather than onto this page. Command-Z reaches one of
them, and the other three say so where they are:

| Edit | Does Command-Z reach it? |
|---|---|
| **A note added on the keyboard panel** | **Yes.** It is marked removed again, and the sheet is drawn again from the recording |
| **A hand swap** | **Yes.** The hand each note had before is written back, and the sheet is drawn again from the corrected recording — which is the only honest undo, because a note's printed length is the gap to the next onset in the same hand and moving one renames its neighbours |
| **A re-record** | Not undoable. It writes over a window of the recording and may splice the audio. Accepting it also forgets every step taken until then, because a step from before it would point into a passage that is not there any more |
| **Placing a passage** | Not undoable, for the same reason, and it moves every mark after the insertion point as well |
| **Remove all** | Not undoable. It deletes the file and puts notes back on the recording, so an undo that restored the screen would say the file had come back too |

Reading a piece back from disk, and the first sheet of a piece taking the page's own octave-bracket
proposal, are not steps either. Neither is something the reader did, and a Command-Z that emptied
the page on arrival would be the worst possible first impression of an undo.

## Keeping it

**Save this rhythm with the piece**, on a small bar that **floats over the sheet** and follows you
down the page. Drag it by its grip, put it away, bring it back.

The bar exists because of a real failure: a long piece went unsaved simply because the button was
past every stave.

Everything is stored in one file beside the recording, `rhythm.json`, and **none of it is in the
recording**. Losing it does not change the music; it costs a person their reading of the piece.

**Remove all** clears every editorial decision and forgets the saved reading, so a reload does not
bring it back. It takes two presses and disarms itself. One of those decisions reaches into the
recording — hidden notes — so it puts those notes back before dropping the list.

Transcribing the piece again clears the reading on purpose: it is a set of column numbers over the
notes that were there before, and a new transcription is a different set of notes.

## Why a column number is a safe address

Every mark above is keyed by column, and **a column never moves** as long as the piece's wall-clock
length does not change. That is what lets a fingering survive a ladder change, a re-recorded
passage, a change of key, and a reload.

The two places length does change are composing and inserting a passage, and there marks move with
their notes in the same write — see [`../backend/editing.md`](../backend/editing.md).

## Where to look deeper

- [`documentation/services/backend/rhythm-and-annotations.md`](../../documentation/services/backend/rhythm-and-annotations.md)
  — `rhythm.json` field by field
- [rendering.md](rendering.md) — what the renderer does with them
- [`../implementations/03-time-based-concept/user-reviews.md`](../implementations/03-time-based-concept/user-reviews.md)
  — the click-by-click walk through all of it
