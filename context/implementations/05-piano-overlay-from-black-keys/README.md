# 05 — The piano overlay, found from the black keys

**State: opened, planned and completed 2026-09-14.** All three phases are done and the overlay of every example is found by the app. The brief is
[`05-prompt.md`](05-prompt.md), the plan is [`05-plan.md`](05-plan.md) and the status lookup is
[`05-checklist.md`](05-checklist.md). Phase reports go beside them as `05-phase-X-implementation.md`,
following
[`../../language/communication-implementation-plans.md`](../../language/communication-implementation-plans.md).

| File | What it is |
|---|---|
| [`05-prompt.md`](05-prompt.md) | The brief, in the user's own words |
| [`05-plan.md`](05-plan.md) | The plan: the model change and what it costs, the finder, the two routes and how they are scored, three phases |
| [`05-checklist.md`](05-checklist.md) | The status lookup |
| [`05-phase-1-implementation.md`](05-phase-1-implementation.md) | Phase 1: the black key finder, the truth, two families, the rectangles fall vertically, route A chosen |
| [`05-phase-2-implementation.md`](05-phase-2-implementation.md) | Phase 2: per-key borders in both services, the grid upgrade, the score board unchanged |
| [`05-phase-3-implementation.md`](05-phase-3-implementation.md) | Phase 3: the finder in the app, every example found, the one rectangle on the screen |
| [`../../../poc-piano-overlay/`](../../../poc-piano-overlay/README.md) | Phase 1's spike: the truth, the families, both routes and their scores |

## What it is for

Implementation 04 fits the piano overlay by placing one white key and repeating its width across the
picture. It cannot work: the cameras that record these videos are not square to the keyboard, so
perspective makes one white key wider than another and some pianos sit at a slight diagonal.

This replaces that one step with one rotatable rectangle over the piano area, the black keys found
inside it and extrapolated through the hands that cover them, and the white keys derived from the
black key pattern — or read directly from the thin dark lines between them, whichever scores better
over the example set.

## What it does not touch

[`../04-synthesia-to-notes/`](../04-synthesia-to-notes/README.md) stays live and stands whole apart
from its Story 2.1. The detector, the frame window rule, the annotation page, the score board and
Phases 3 to 5 all read the overlay through the same `Calibration`, and that model is what this work
changes — from one white key width for the whole keyboard to per-key borders. Section 5 of the plan
says what that costs before it is changed.

## The decisions

The V numbers stay one series, in
[`../04-synthesia-to-notes/04-decisions.md`](../04-synthesia-to-notes/04-decisions.md). This work
contradicted **V-09**, which said the app never finds the keyboard by itself. V-09 is superseded by
**V-37** — one rectangle from the user, every key inside it found by the app — and **V-38** says what
the overlay now is and which of two white key widths each threshold is measured in. Both were written
on 2026-09-14 at the user's direction. Phase 1 added **V-39** (the rectangles fall vertically, so the
lanes stay vertical), **V-40** (two families of black key placement, told apart by the black keys
alone) and **V-41** (route A ships, with its score).
