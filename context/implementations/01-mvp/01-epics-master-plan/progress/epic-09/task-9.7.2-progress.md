# Task 9.7.2 — Trills · progress

Status: **done** on 2026-09-13. Closes Story 9.7 and with it Epic 9.

## The rule

Two notes taking turns, a whole tone or less apart, the pair coming round at least three times —
Si-Do-Si-Do-Si-Do — evenly and with under 300 ms between notes. Measured **per hand** and on the
**raw attack times**, not on the grid: a trill often runs faster than one column, and a detector
reading column numbers would see a flat line of identical gaps and call anything a trill.

Deliberately the smallest rule that works. It says no to a scale, to two notes a third apart (that
is a tremolo, written differently), to an alternation that wanders in speed, and to anything with a
chord in the middle of it — a chord ends the run rather than being skipped over, so two short runs
either side of one do not join into a long one.

## What it does with what it finds

Nothing, until the reader says so. A missed trill costs a reader nothing and a wrong one hides notes
that were really played, so detection only ever offers (D-17).

Accepting one writes a mark into `rhythm.json` and the sheet is asked for again with it. The
alternations come off the page **on the backend**, before any figure is named, and one note is put
back at the run's start on the lower of the two pitches, sounding across the whole run. That
ordering is the whole trick: the printed length of a note is the gap to the next onset in the same
hand (D-14), so a held note collapsed in the browser would have printed as a semicorchea with `tr`
over it. The `tr` itself is a frame-anchored free text, which the drawing package already drew.

The recording is not touched. Playback still sounds every alternation (D-29), the piece keeps its
length, no column moves, and dropping the mark prints the notes again exactly.

## Where it is

- `aitu_backend/notation/trills.py` — the rule.
- `GET /time/{uuid}/trills` — suggestions. Writes nothing.
- `POST /time/{uuid}/score`, field `trills` — the collapse, in `_with_trills`.
- `schemas/rhythm.py`, `SavedRhythm.trills` — storage.
- Rhythm tab: **Find trills** under the sheet lists what was found, one chip each; the frames
  toolbox **Trill** tab marks a stretch by hand for an ornament the rule was too strict for.

## Manual trial

Record a trill, press **Find trills**, click the chip. The storm of noteheads becomes one held note
with `tr` over it, the note after it keeps its place, and playback still sounds every alternation.
**Print the alternations again** puts them back.

Tests: `tests/test_notation_trills.py` (14) and four in `tests/test_time_score_api.py`.
