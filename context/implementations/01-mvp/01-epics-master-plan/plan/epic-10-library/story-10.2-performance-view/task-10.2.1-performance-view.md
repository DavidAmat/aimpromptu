# Task 10.2.1 — Performance view

> **Rewritten 2026-08-12 for the wall-clock model.** See
> [`../../wall-clock-rewrite.md`](../../wall-clock-rewrite.md).

`/library/play/:id`: what is open on the music stand.

## Subtask 10.2.1.1 — Read-only drawing

The piece drawn from its score payload with its saved rhythm applied — the ladder, the passages, the
key, the overrides, the beam breaks, the fingerings. The same drawing as the Rhythm tab with every
editing control removed: no toolbox opens on a click, no marked stretch, no Save bar, nothing
draggable.

It must load fast. If deriving the payload on request is too slow for a long piece, cache the
payload with the version rather than reintroducing a stored score file that can disagree with
`events.json`.

## Subtask 10.2.1.2 — Overlay toggles

Small unobtrusive switches for fingering, lyrics, tuplet and trill marks, and the dashed guides. The
fingering toggle can ship now — fingering exists (P8.1). The lyrics toggle ships disabled until
Epic 12.

## Subtask 10.2.1.3 — Following the music

Play the recording with the playhead moving along the staves, and click anywhere on the scrub bar to
move it: both already exist and both belong here, because a performer studying a piece wants to hear
the passage they are looking at. Space plays and pauses.

Scroll and browser zoom are the whole rest of the interaction. A **PDF** button opens the same
export the Rhythm tab has, for whoever prefers paper.

## Subtask 10.2.1.4 — Navigation

A back button to the library, and a **Next** button when the view was opened from a playlist.

## Acceptance

Manual trial: open a promoted piece, confirm no editing control is reachable, toggle the fingering
off and on, play from the middle of the page, and export the PDF.
