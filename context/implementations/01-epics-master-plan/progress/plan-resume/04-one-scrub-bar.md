# One scrub bar for every page, and the page stops running away

**Commits `a6ae2b2` and `b806ed2`, 2026-08-10.** Reported 2026-09-13 by Task 14.1.1.3.

## The sheet gets the same bar

It had a `LinearProgress` you could click, which **draws no handle** — nothing on the page looked
draggable, so scanning through five minutes of recording was a series of guesses.

`ProgressBar` now takes a position and a way to change one, rather than a transport. So the sheet
can use it over an `<audio>` element while the roll uses it over the synthesised clock, and a reader
learns **one control for the whole app**.

## Changing what you hear no longer rewinds

The toolbar stopped playback before applying a change to the source, the speed or the range, which
is right: the clock is anchored to a sound that is about to be replaced.

But it used `restart()`, which also **rewound to the start of the range**. Switching between the
original audio and the transcribed piano at 2:41 therefore threw the reader back to the beginning —
and comparing the two at one moment is precisely what that switch is for.

It now pauses where it is.

## Dragging the bar on the sheet was impossible to finish

Two separate things scrolled the page out from under the pointer, and both had to go.

**The one that mattered.** The playhead line follows the music onto each new stave, which is right
while the recording plays and **wrong while somebody is scrubbing**. A drag sweeps the line through
a hundred staves in a second, so the page chased it down, the bar left the window, and the gesture
ended wherever the pointer happened to lose it.

`TimeScoreView` now takes `followPlayhead` and only follows while the recording is sounding. The
stave index is still recorded when not following, so resuming does not jump on the first tick for a
line the reader is already looking at.

**The other.** The bar itself asked for a scroll when a gesture ended. It no longer does, anywhere —
`onAfterSeek` is gone rather than left unused, because **moving the recording and moving the reader
are two different things** and the bar only does the first.

## Space is how you arrive

It centres the cursor and plays from it, which it already did. So the sequence is now the one David
asked for: **drag to the moment you want, press Space, and the page comes to you.**

## Also

Fixes the long-standing lint error in `ScorePlayer`: the `controls` prop is a ref, so it is
`controlsRef`, which is what the rule was asking for. Lint clean for the first time.

## Verified

In a browser against a real recording.

On both animated views: a seek to 01:30.35 survives a source change and a speed change, and a change
made mid-play pauses without moving backwards.

On the sheet: dragging the handle to 38 % lands at 01:51.02 of 04:52.16 and the cursor scrolls into
view. A six-step drag from 5 % to 90 % of a five-minute piece holds `scrollY` at 1053 throughout and
the handle stays at y=179, landing at 04:22.94; Space then centres the cursor at 5395 and starts
playing. With the page deliberately scrolled to the top mid-playback, crossing a stave still brings
the line back, so following **during playback** is intact.
