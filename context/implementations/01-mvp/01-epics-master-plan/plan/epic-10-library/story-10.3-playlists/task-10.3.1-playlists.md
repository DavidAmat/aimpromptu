# Task 10.3.1 — Playlists

> **Rewritten 2026-08-12 for the wall-clock model.** Only the slice definition changed. See
> [`../../wall-clock-rewrite.md`](../../wall-clock-rewrite.md).

Stored under `library/playlists/<slug>/metadata_library_playlist.json`.

## Subtask 10.3.1.1 — Create, order, edit

Create, rename and delete playlists; add a piece, choosing the promoted version by its promotion
name when there are several; drag to reorder; remove entries. Adding to a playlist is also reachable
from the library list, for an existing playlist or a new one.

## Subtask 10.3.1.2 — Playing mode

Choosing a playlist opens the performance view on the first piece; one **Next** click loads the
following one. Order is editable before starting and not during.

## Subtask 10.3.1.3 — Nice to have: an excerpt instead of a whole piece

An entry may point at a stretch of a piece rather than all of it. The stretch is a **wall-clock
range in seconds**, stored as seconds and not as frames, so it stays correct if the piece is later
opened on a different `frameMs`. Skip until asked for.

## Acceptance

Manual trial: a two-piece playlist played through with Next, order changed before starting, and the
same playlist reopened after a restart.
