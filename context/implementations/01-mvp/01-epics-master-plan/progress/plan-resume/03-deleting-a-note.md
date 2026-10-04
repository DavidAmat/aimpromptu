# A deleted note leaves the piano matrix, and Save is what decides it

**Commit `f7a9f34`, 2026-08-10.** Reported 2026-09-13 by Task 14.1.1.3.

## Why

Two half-measures were in the app at once and neither was right.

Deleting on the roll **wrote straight through** — no review, no undo before the fact. And on the
sheet, "off the page" was **only ever a drawing overlay**: the roll still showed the note and the
recording still had it.

Both are now the same act: staged, then kept.

## Staged, not applied

Marking a note on the roll or the falling view draws it **struck through in red** and puts a
floating bar on the page carrying **Save** and **Discard** — the same bar the sheet already keeps
its Save on, in the same place, for the same reason: these views run wider than the window, and a
button pinned under them means scrolling away from the notes you are deciding about.

**Nothing reaches the recording until Save.** This matters because taking a note off changes the gap
to its neighbour and therefore that neighbour's printed figure, so it is a decision about the piece
and deserves reviewing.

Staging is keyed by **pitch and start second** rather than by list index, because a save re-reads
the recording. An entry that returns a note to where it started is dropped rather than kept as a
no-op, so the bar's count stays honest.

## The sheet does the same thing

`save()` now also writes its hidden notes to the matrix. The drawing does not change — the figures
were already named with them excluded — but the roll, the falling view and the recording finally
agree with the page.

They stay in the saved reading too: a reading from before this still lists notes that are still
there, and dropping the field would un-hide them.

## Which meant Remove all had to grow

**Remove all** wipes reader decisions, and one of them now reaches into the recording. Clearing the
list alone would leave the notes gone with nothing on screen remembering them — the same failure
P8.4 fixed one layer up.

It now **puts them back on the recording before dropping the list.**

## Restoring cannot use the current matrix

Putting a note back cannot be resolved against the current matrix, because the note is not in it;
that is what removed means.

`PUT /time/{id}/removed` builds its lookup from a split **with every removal undone** when it is
asked to restore, which is the numbering the columns were written down at. One extra split, paid
only on an undo.

## Two routes write the same flag, on purpose

The two screens genuinely hold different things. A reader on the roll knows raw seconds
(`PUT /matrix/{id}/events/removed`); a reader on the sheet has clicked a notehead and knows a column
and a row (`PUT /time/{id}/removed`).

Same field, same consequences. Both drop the split cache, which the raw route was not doing.

## Colour

Selection moves from red to **lavender**. Red now means "about to be deleted", and with both in red
a reader could not tell a note they had picked from one they had marked.

## Verified

In a browser against a real recording. On the roll: band-select 21, Delete stages them with nothing
on disk, Discard clears it, Save writes exactly 21, Put back returns all 21 to zero. On the sheet:
off the page writes nothing, Save removes 1 from the matrix, Remove all restores it. Backend suite
green.
