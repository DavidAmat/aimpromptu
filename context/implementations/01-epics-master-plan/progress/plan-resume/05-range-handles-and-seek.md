# Both ends of a marked stretch, and double-click to seek

**Commits `c22a1ea` and `5644d56`, 2026-08-10.** Reported 2026-09-13 by Task 14.1.1.3.

## Both ends of a marked stretch can be pulled to any frame

A range on the sheet is made by clicking groups, and **a group is about a second** — far coarser
than the note a reader is aiming at. Ending a selection on the redonda two frames past a boundary
meant either stopping short of it or dragging in everything up to the next boundary. There was no
way to say "up to there".

There are **two handles now**, one at each end of the dashed outline, and each moves the end it
holds to whatever frame is under the pointer. The rest of the range does not move.

**Positioned imperatively**, from `placeCursor` against the last render, the same way the playhead
is — because they move with redraws the host never asked for, a re-wrap or a change of width, and
React state holding pixels would be a frame behind every one of them.

**The grip is a square where the playhead's is a circle.** The two are often within a few pixels of
each other, and the shape is what says which one you are about to take hold of.

**The ends are clamped apart rather than allowed to cross.** An inverted range reads as empty
everywhere downstream — no key change, no bracket, nothing to apply — and a reader could not tell
that from a bug.

Needs `@aimpromptu/grid-notation` **0.32.0**, which paints the intersection of a group cell with the
range instead of only whole cells. Before that, dragging an end past a boundary made the
part-covered group vanish rather than fill partly.

### Verified

In a browser: a right end at f274 walks to f285 across a group boundary, drawing one whole cell and
one partial; a stepwise drag inside a group reads f99 → f92 → f91 → f83 → f82 — which is frames, not
groups.

## Double-click a blank part of the sheet and the recording goes there

Almost every pixel of a stave already answers to a click: a notehead picks a note, a group cell
picks a stretch of columns, the playhead and the two range handles are grabbed. **One gesture cannot
mean two things.**

What is left over is the strip above the top stave, the gaps between systems and the margins — which
is exactly where a reader points when they mean "here" and nothing else.

So the seek is the **second** click on ground that is otherwise inert. A single click there goes on
meaning nothing, and no gesture that already exists changes. The elements that *do* mean something
are **listed rather than inferred**: a double-click lands on whatever is under the pointer, and the
honest test for "is this blank" is "is it none of the things that answer to a click".

**The page does not scroll afterwards**, for the same reason the scrub bar no longer does: the
reader is looking at the place they just pointed at, and moving them to it would take that place
away. Space remains the one thing that brings the page to the line.

### Verified

In a browser: a double-click above the treble stave over frame 200 puts the recording at 00:08.42
with `scrollY` unmoved, a second one over frame 400 at 00:16.48, and a double-click on a group cell
leaves the position alone.
