# Task 11.3.1 — Replacement preview and accept

> **Rewritten 2026-08-12 for the wall-clock model.** See
> [`../../wall-clock-rewrite.md`](../../wall-clock-rewrite.md).

## Subtask 11.3.1.1 — Transcribe first, scale second

Transcribe the take exactly as it was played. Never transcribe stretched audio: time stretching adds
artifacts that the engine reads as notes, and the whole point of playing slowly is to give the
engine a cleaner signal. Scale the resulting event times afterwards, which is arithmetic and cannot
invent a note.

## Subtask 11.3.1.2 — Preview the passage only

Redraw the marked stretch of the sheet with the take's notes in place, using the ladder of the
passage the window belongs to, so the user sees the figures that will actually print. This must be
fast: it is a few seconds of music, not a full score rebuild.

Show the take's own peak plot beside it. A wrong speed choice is obvious there — the peaks of the
scaled take should land on the same values as the passage's ladder, and a factor that is off by two
puts every peak one step away.

## Subtask 11.3.1.3 — Listening

Three things to play, from the same panel: the take at the speed it was played, the take scaled into
the window, and the original window it would replace.

## Subtask 11.3.1.4 — The decision loop

From the preview: play any of the three, change the speed factor and preview again without playing
the passage again, record another take, accept, or cancel. Re-recording keeps the same window; the
window is fixed at session start and is not editable here, because changing it would invalidate the
take already recorded.

## Subtask 11.3.1.5 — What accept says before it commits

One short confirmation listing: how many notes go, how many arrive, how many editorial marks inside
the window are dropped and of which kind, whether the audio will be spliced, and that the piece's
length does not change.

## Acceptance

Manual trial: a hard 3-second passage played again at 4 times slower, previewed, the factor
corrected once, accepted. In the final sheet the passage shows the new notes, the note after the
window has the same onset it had before to the millisecond, and playback follows the sheet.
