# The note toolbox

What the Sheet step can say about the notes picked on the sheet. The overview of the page, the
selections and undo is [annotations.md](annotations.md). Code:
`aitu-frontend/src/pages/piece/sheet/NoteToolbox.tsx` and `useNoteActions.ts`.

## The title

**Pick one note and the panel is titled with its name**, in solfège: `Do 4`, `Do-# 3`, `Re-b 5`.
Middle C is `Do 4`, the reckoning the keyboard, the roll and every tooltip use. Pick several and the
title counts them; the keyboard panel is where a chord is read. Under the title is the time of the
notes in the recording.

The name is **the one the sheet prints**, not one worked out from the key that was pressed. The same
black key is written `Do-#` in a sharp key and `Re-b` in a flat one, so the panel spells it against
the signature sounding at that column, through the same code the noteheads come from. An octave
bracket or a move to the other staff does not change it: the name is what the note **sounds**.
`npm run check:note-names` pins it.

## The controls

Every control is an icon or a short label, and its tooltip says what it does. A disabled one says
why in its tooltip.

| Row | Control | What it does |
|---|---|---|
| (top) | **The seven figures** | The shapes themselves, redonda to semifusa. The one every picked chord is drawn as is pressed; pressing another names all of them at once. Nothing moves in time (D-18). ⌫ goes back to the figures of the sheet |
| Finger | **1 to 5** | One number on every picked note, or on a single chord one number per note, low to high. ⌫ takes them off |
| Hand | **Right / Left** | Which hand plays them. Written onto the recording (below) |
| Beam | 🔗 | Beam every picked chord as one group, whatever the page's own rule makes of them. Needs two or more whole chords, all a corchea or shorter: a negra has no beam to share |
| Beam | ✂ | Start a new beam in front of them, or join it again. Refused unless the whole chord is picked |
| Beam | = | Set the picked run of one hand an equal distance apart |
| Beam | + / − | Open the even run further or close it. Disabled until = is pressed |
| Marks | 🎹 | A decoration: opens **Piano Edit**, a keyboard with the note in lavender and the decoration in pink. Click a key to say what sounds just before it |
| Marks | A− | Print the picked notes cue-sized, or full size again |
| Marks | *tr* | Write the picked notes as one held note with `tr` and a wavy line over it. Needs three onsets or more in one hand |
| (bottom) | 🗑 | Take them off the page, or press **Delete** (⌫ on a Mac). For a note the transcriber invented out of a pedal blur |

Two of these reach further than they look.

**Moving a note between hands also changes what its old and new neighbours are called.** A note's
printed length is the gap to the next onset in the same hand, so the correction is written onto the
recording (`PUT /time/{uuid}/hands`) rather than kept beside the drawing, and the sheet is asked for
again. Command-Z writes the old hands back.

**Taking a note off the page does the same to the note before it**, for the same reason: the
neighbour is lengthened to cover it, which is the point. It is a page edit until **Save**, which
also takes the note out of the matrix, so the roll and the falling view agree with the page.

Renaming a tresillo loses its `3`, on purpose: the name says "draw it as this".

## Even spacing

Each column is as wide as what is drawn in it, and **both staves share the column**, so a run of
even corcheas in one hand comes out unevenly spaced wherever the other hand needs room. The page is
not wrong when that happens, but a beam of equal notes that is not equally spaced reads as an
uneven performance. **=** sets every gap in the run to the widest gap it already had; **+** opens it
further and moves whatever the other hand plays underneath, which is the trade.

**− goes below even, and it is meant to.** The widest gap is usually wide because of the other
hand, so evening a run to it makes the whole run as wide as its worst moment. Below 100 % the notes
crowd and may touch; that is visible and one press back.

## Small print and decorations

**Cue size is asked for, never inferred.** A florid run set at full size crowds the other hand off
the system; set smaller it takes less width and reads as decoration. A **decoration** (grace note)
is never inferred and never played: nothing in a recording tells one from a very short note that
was really struck.

## Where to look deeper

- [annotations.md](annotations.md) — the page, the selections, undo and saving
- [annotations-stretches.md](annotations-stretches.md) — the range toolbox
- [`documentation/services/backend/rhythm-and-annotations.md`](../../documentation/services/backend/rhythm-and-annotations.md)
  — how each mark is stored
