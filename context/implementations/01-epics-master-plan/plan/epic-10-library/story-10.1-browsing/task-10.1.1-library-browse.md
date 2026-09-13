# Task 10.1.1 — Library browsing and management

> **Rewritten 2026-08-12 for the wall-clock model.** See
> [`../../wall-clock-rewrite.md`](../../wall-clock-rewrite.md).

## Subtask 10.1.1.1 — Promoted pieces

A list of promoted pieces from `library/tracks/`, showing real artist and piece names from the
metadata, and the promotion name when a piece has several versions. A search box that searches those
names, not slugs.

Each entry says whether a **saved rhythm** exists for that version. A piece with no saved rhythm
opens as unnamed figures and has to be named before it reads as music, which is a thing to know
before a concert rather than during one.

## Subtask 10.1.1.2 — Tags and filters

User-defined tags — genre, artist, mood — stored in `metadata_library_track.json`, shown as chips
that combine with the search.

## Subtask 10.1.1.3 — The playground list

The second list: everything under `playground/`, with rename and metadata editing. This is the
staging area before promotion.

Two things belong in this list and are already built: the `needsRederivation` warning for a piece
the migration could not carry over (P4.5, P7.6), and the version names, which now read `v2_f40` —
the number is the musical state and the suffix is the clock it was saved on. Show both, and never
guess at a folder written under the old granularity scheme; refuse it, as the backend does.

## Acceptance

Filters combine with the search; edits survive a restart; a piece flagged `needsRederivation` is
visibly marked and cannot be opened in the performance view.
