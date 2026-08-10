# 2026-08-10 — the time-based concept plan is closed

The refactor that replaced tempo with wall-clock time is finished, and the plan that carried it is
closed. This is the trail: what the change was, how it ran, what it cost, and what it leaves
behind.

The plan's own documents stay where they are, in
[`../time-based-concept/`](../time-based-concept/README.md). The
one to read is [`CLOSURE.md`](../time-based-concept/CLOSURE.md).

## What changed, in one paragraph

The app used to ask for a tempo and a note resolution, build a grid of note figures out of them,
and fit the playing into that grid. Even playing came out ragged, every time, because nobody plays
on a grid. Now the page is measured wall-clock time — a column is 40 ms of real time — and a figure
is a **label the reader chooses**, not the thing the layout is built from. You look at a picture of
the gaps in your own playing, click the one that repeats, name it, and everything else takes its
name from that. There is no BPM anywhere in the product.

## How it ran

| | |
|---|---|
| Started | 2026-08-06 |
| Closed | 2026-08-10 |
| Phases planned | 0–8 |
| Phases completed | 0–7, plus an unplanned Phase 8 of ten review-driven features |
| Repositories | `aimpromptu` and `vexflow-v2`, both on the branch `time-based-concept` |
| Renderer version | `@aimpromptu/grid-notation` 0.26.2 → **0.31.0** |
| Frozen decisions | D-01 … D-34, none re-litigated |
| Deviations logged | I-01 … I-06 in `progress/issues.md` |

Roughly a third of what shipped was never in `plan.md`: P7.12 through P7.15 and the whole of the
P8 review stream came from David opening the app and saying what was wrong with what he saw.

## The three things worth carrying forward

**1. The plan was not a complete description of the product.** P7.12 is the clearest case: the key
signature picker existed on a tab that P4.2 deleted, and nothing in `plan.md`, `decisions.md` or the
PRD mentioned it. It came back only because David noticed 242 accidentals that did not need to be
there. Before deleting a screen, list what only that screen could do.

**2. The defects that mattered were found by looking, not by testing.** The backend suite is 589
tests green, and neither of the two real bugs in the review stream — the hand-split search keeping
the wrong state, and the hand overlay silently renaming five other notes per move — was reachable
from it, because the suite tests pieces built to have known answers. Real music found both in an
afternoon.

**3. Uncommitted work is the only thing that can be lost.** On 2026-08-08 a session wrote a stale
copy of `aitu-backend` over another session's completed work. Twenty files were clobbered; twelve
had no copy anywhere and were rebuilt from a progress report. The refactor had been sitting
uncommitted for five days, which is the whole reason a stale copy could destroy instead of
conflict. Recovery is written up in
[`../time-based-concept/progress/2026-08-08-overwrite-and-recovery.md`](../time-based-concept/progress/2026-08-08-overwrite-and-recovery.md);
the twelve reconstructed files are named there, and that report is the authority over any comment
inside them.

## What it cost

Five screens were deleted with the tempo model: **Matrix**, **Piano Roll**, **Notes Falling**,
**Notes Falling (raw)** and **Music Notation**. There is no piano-roll view, no falling-notes view,
no hand-editing of a cell, and no matrix import or export. **Text notation** and **Matrix JSON** as
ways of making a piece without a recording are gone too.

This was accepted at the time (I-06) and is still the state today. Bringing any of them back on the
wall-clock path is a feature request, not unfinished work.

## What was dropped at closing

Two boxes were open and were cancelled rather than inherited, on David's call:

- **P1.7**, the check that inspects transcription data before it is drawn. Nothing guards that
  output today.
- **The sign-off phase**, and with it two of six success criteria: playback alignment measured over
  five minutes, and a formal record that every stored piece migrated. The migration itself ran and
  its warning flag is tested.

The reasoning is in `CLOSURE.md` §4: the app works, and a round of real piano music is a better next
input than a checklist run against the one piece we already understand.

## Documents written or corrected at closing

- `time-based-concept/CLOSURE.md` — new. What shipped, what was dropped, what replaces the plan.
- `time-based-concept/checklist.md` — final state, with the two cancellations and the P8 numbering
  resolved.
- `time-based-concept/progress/P8.1-P8.10-the-review-stream.md` — new; P8.9 and P8.10 had no report
  at all.
- `time-based-concept/user-reviews.md` — the walk now matches the app; its "not built" table had
  three entries that shipped weeks ago.
- `context/music/notation-logic/01`, `02`, `03` and `context/music/transcription-quality.md`, and
  `documentation/issues/rhythm-figures-and-tempo.md` — banners saying which parts describe a model
  the app no longer has.

## Next

A round of varied piano music through the app, collecting what is wrong or awkward. That list
becomes a new implementation plan with its own PRD, numbering and checklist, in its own folder.
This one is history.
