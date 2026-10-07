# The range toolbox, and octave brackets on the page

What the Sheet step can say about a marked stretch of frames. The overview of the page, the
selections and undo is [annotations.md](annotations.md). Code:
`aitu-frontend/src/pages/piece/sheet/RangeToolbox.tsx` and `useRangeActions.ts`.

## The tabs

The panel is titled *Frames*, with the time of the stretch under it. Its first row says which staff
the stretch is about (**Both / Right / Left**). Then one tab per thing a stretch can carry; a tab
with a dot means this stretch already carries that setting.

| Tab | Reads the hand? | What it does |
|---|---|---|
| **Key** | No | The stretch gets its own key signature (✓), drawn on both clefs; 🗑 goes back to the key of the piece. **Key for this passage**: when another key prints fewer accidentals over the stretch than the one in force, a button names it ("Use Bb major here") and one press applies it |
| **Clef** | **Yes** | The hand prints a treble or a bass clef over the stretch, and goes back to its own after it. Where the clef rule (below) finds high left-hand runs in the stretch, a button offers it again: "Treble clef for the high left-hand notes (n)" |
| **Octave** | **Yes** | The four brackets (`8va`, `15ma`, `8vb`, `15mb`) per hand; the eye hides one, the bin removes it. Pressing the bracket already on removes it |
| **Spacing** | No | How much room the stretch takes, from 25 % to 400 % of what the page measured. The sheet redraws as the handle moves |
| **Speed** | No | Where the piece changes speed (below) |
| **Re-record** | No | Play the stretch again, over the recording. Undo cannot reach it, and the tab says so |

**Trill** and **Small** are in the note toolbox: they are statements about notes, so a selection
answers the hand and the columns at once.

## Speed

A piece played faster in one part than another names its notes wrongly there, because every figure
is named from one length (the highest pile of gaps). The **Speed** tab says, from the start of the
stretch, how fast that part goes **against the speed of the piece**: 100 % is the same speed, 120 %
a fifth faster. ✓ writes the change, 🗑 removes the one that starts here, and *Remove every speed
change* clears them all. The sheet is drawn again by itself.

The stored value is still a length in milliseconds for the main figure (`speedChanges` of
`sheet.json`, rule 3: no BPM); the percentage is how it is shown. Implementation 02, Phase 2 moved
this from the card *Does the piece change speed?* above the sheet into the toolbox.

## An octave bracket, once it is on the page

Four things can be done to a bracket without going back to the columns that made it.

**Pull either end.** A band runs along the dashed line and lights up under the pointer; its two ends
move the bracket by whole columns. A bracket pulled over another on the same hand takes it over.
The two ends are held one column apart, so a bracket can never invert. The drag is reported once,
when the pointer is let go; Command-Z puts the bracket back the length it was.

**Drop a tip on another line and every frame in between comes inside the bracket.** The sheet wraps,
so the frames you want next are often on the line below. While a tip is held, an amber band shows
every line the bracket would cover and a line shows the column the end would drop into. Nothing is
drawn on hover, and nothing is left on the page after.

**Click the band and you have the bracket, and only the bracket**, with a tip at each end to pull.
The corner marks are the way to the stretch: click one and the range toolbox opens on **Octave**.

**Hide it.** The eye in the Octave tab, or **Delete** with a stretch marked and no note picked,
takes the dashed line and the `8va` off the page and leaves the notes written where the bracket puts
them: a player who knows a passage is played an octave up does not need it said over every bar.
**Hiding is not removing**: a hidden bracket is still saved and still draws its corner marks, the
way back to it. The bin is the only way to remove one, and that puts the notes back where they
sound.

## Clefs, spacing and words

**A clef change is the honest answer to a hand that spends a page far outside its own staff**, and a
better one than an octave bracket where the passage is long: on the other clef the notes are written
where they sound. Nothing moves and nothing is renamed.

**The clef rule** (implementation 02, Phase 7, plan section 11.7): on a first write, a run of at
least four left-hand chords whose lowest note is two ledger lines or more above the bass staff (E4
and up) is written in the treble clef. One lower chord inside the run is kept in it, unless it
would sit under the treble staff; a shorter run keeps the bass clef and may take an `8va`; a very
low run takes an `8vb`. A bracket is never put over a passage the rule wrote in the treble clef: it
is cut where the clef changes. The numbers are `DEFAULT_CLEF_RULE` of the drawing package, measured
on the library ([rendering.md](rendering.md)). Each change is an ordinary clef change after that.

**Spacing is both staves, whichever hand is chosen.** A column is one slice of wall clock and the
two hands share it (D-22), so there is no widening a column for one hand.

**Words belong to the piece, not to a staff.** They are drawn above the right hand, in a block of
their own at the top of the line, above the octave brackets. Since implementation 02, Phase 7 they
are the lyrics pieces of the sheet toolbox's Lyrics tab ([annotations-sheet.md](annotations-sheet.md)),
placed by dragging and snapped to frames; the range toolbox has no Lyrics tab. In the Lyrics tab, a
stretch marked above the staves picks the pieces over it instead of opening this toolbox.

## Where to look deeper

- [annotations.md](annotations.md) — the page, the selections, undo and saving
- [annotations-notes.md](annotations-notes.md) — the note toolbox
- [rendering.md](rendering.md) — how brackets, clefs and words are drawn
