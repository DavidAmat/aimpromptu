# Epic 10 — Piano Library

> **Rewritten 2026-08-12 for the wall-clock model.** The epic survives almost unchanged; what it
> reads and how a version is named changed. See
> [`../wall-clock-rewrite.md`](../wall-clock-rewrite.md).

The section for the person at the piano: find a piece, open a clean page with nothing but the music
on it, and put pieces in order for a concert.

Read first: [`../wall-clock-rewrite.md`](../wall-clock-rewrite.md), then `project-features.md`
section "Piano Library". The library half of "Folder Structure for storage" is out of date on two
points: a transcription stores one file, `events.json`, and a saved version folder is
`v<N>_f<frameMs>`, not a granularity code (contract §8).

## Story 10.1 — Browsing and management

- Task 10.1.1 library browse: promoted tracks with tags, search by real names, filters; plus the
  playground list with rename and metadata editing, and the `needsRederivation` warning already
  surfaced there.

## Story 10.2 — Performance view

- Task 10.2.1 performance view: a blank read-only page drawing the piece with its saved rhythm, no
  editing controls, overlay toggles, and the PDF for whoever prefers paper.

## Story 10.3 — Playlists

- Task 10.3.1 playlists: create and order playlists, pick the promoted version by name, step to the
  next piece with one click.

## Exit criteria

Manual trial: promote two pieces, tag them, filter by tag, open one in the performance view and
scroll it end to end with no toolbox in sight, then build a two-piece playlist and step through it.
