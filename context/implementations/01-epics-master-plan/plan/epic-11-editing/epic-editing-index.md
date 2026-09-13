# Epic 11 — Range editing and re-recording

> **Rewritten 2026-08-12 for the wall-clock model.** The original text was built on beats, a track
> BPM and a recording BPM, none of which exist now. The model and the rules every task here obeys
> are in [`../wall-clock-rewrite.md`](../wall-clock-rewrite.md). Git holds the old text.

Replace a passage of an existing piece by playing it again, as slowly as you need, without
disturbing anything outside it. Preview first, accept or cancel, original untouched on cancel.

**The rule that shapes the whole epic: the replacement occupies exactly the window it replaces.**
Mark 3 seconds of the sheet, play the passage in 6 seconds, and the take is scaled back into those
same 3 seconds when you accept. The piece keeps its length and its column count, so the recording
still lines up with the page and every editorial mark after the edited window keeps working.
`../wall-clock-rewrite.md` §3 explains why this is worth enforcing.

Read first: [`../wall-clock-rewrite.md`](../wall-clock-rewrite.md), then
[`../../time-based-concept/contract.md`](../../../03-time-based-concept/contract.md) §8 (what a piece
stores) and D-02, D-03, D-04, D-05, D-14 in
[`../../time-based-concept/decisions.md`](../../../03-time-based-concept/decisions.md).
`context/music/notation-logic/03-editing-logic.md` is **obsolete** and banner-marked; do not use it
as the spec for this epic any more.

## Story 11.1 — Staged edit sessions

- Task 11.1.1 staged edit session: mark a stretch on the sheet, open a disposable session holding
  the take and everything derived from it, accept by splicing into `events.json`, cancel by
  deleting the folder.

## Story 11.2 — Playing the passage again, slower

- Task 11.2.1 slow re-record flow: speed choice, optional click track derived from the piece's own
  ladder, hearing the original passage slowed, trimming the take to the expected length.

## Story 11.3 — Preview and accept

- Task 11.3.1 replacement preview: transcribe the take at the speed it was played, scale the event
  times into the window, redraw only that stretch of the sheet, listen, then accept or play it
  again.

## Exit criteria

Manual trial: mark a 3-second stretch of *Mr Blue Sky*, play it again at half speed so the take
lasts about 6 seconds, preview it, accept. The sheet shows the new notes inside the marked stretch
only; the piece's total length is unchanged to the millisecond; a note immediately after the window
keeps its exact onset; playback still follows the sheet; and pressing cancel instead of accept
leaves the piece bit-identical.
