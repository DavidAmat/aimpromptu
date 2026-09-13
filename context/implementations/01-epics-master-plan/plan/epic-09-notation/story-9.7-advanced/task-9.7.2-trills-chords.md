# Task 9.7.2 — Trills (nice to have)

> **Shipped 2026-09-13.** The rule, where it lives and what it draws are in
> [`../../../progress/epic-09/task-9.7.2-progress.md`](../../../progress/epic-09/task-9.7.2-progress.md).
> The threshold that was built is the pair coming round **three times** — six notes — rather
> than the six alternations this file asked for; three times over is what a reader recognises
> as a shake, and the two numbers are close enough that no real trill falls between them.
>
> **Rewritten 2026-08-12 for the wall-clock model.** The chord half of this task shipped in the
> refactor. See [`../../wall-clock-rewrite.md`](../../wall-clock-rewrite.md).

**Already done — chord grouping.** Notes played within 20 ms of the group's first note are one
chord, grouped on the raw times before anything is snapped, and non-chaining so a slow arpeggio
does not swallow the whole bar (D-04). Arpeggio ornament signs are not drawn, by design. Nothing
remains here.

**Also already answered — the undersampling warning.** The old text worried that a fast trill would
be undersampled by the grid. It cannot be: the grid is no longer where duration comes from, and
detection runs on the raw event times, which is what that warning asked for.

## Subtask 9.7.2.1 — Trill detection

Find two notes alternating continuously and quickly in the same hand, on raw times: at least six
alternations, both pitches within a whole tone of each other, gaps even within some tolerance. Print
`tr` over the lower note held for the length of the run, instead of the literal storm of notes.

Detection is a **suggestion**, not a rewrite: it proposes the mark, the reader accepts it. A missed
trill costs nothing, and a wrong one hides real notes.

## Subtask 9.7.2.2 — Storage

The mark lives in `rhythm.json` over a frame range, like every other editorial decision. The notes
stay in `events.json` untouched — playback still plays every one of them (D-29), and removing the
mark brings them back onto the page.

## Subtask 9.7.2.3 — Other ornaments

Still ignored by design. A performer interprets them; they cannot be inferred from audio.

## Acceptance

Manual trial: record a trill, accept the suggested mark, and see `tr` over one held note; playback
still sounds every alternation; removing the mark prints the notes again.
