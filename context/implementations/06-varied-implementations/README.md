# 06 — Varied implementations

**State: opened and first brief completed 2026-09-16.** A folder for the smaller pieces of work asked for on top of the
finished product, one plan at a time. The first brief is [`06-prompt.md`](06-prompt.md), the plan is
[`06-plan.md`](06-plan.md) and the status lookup is [`06-checklist.md`](06-checklist.md). Phase
reports go beside them as `06-phase-X-implementation.md`, following
[`../../language/communication-implementation-plans.md`](../../language/communication-implementation-plans.md).

| File | What it is |
|---|---|
| [`06-prompt.md`](06-prompt.md) | The brief, in the user's own words |
| [`06-plan.md`](06-plan.md) | The plan: undo and redo on the sheet, and the space between lines |
| [`06-checklist.md`](06-checklist.md) | The status lookup |
| [`06-phase-1-implementation.md`](06-phase-1-implementation.md) | Phase 1: the history, one press is one step, the hand swap through the backend |
| [`06-phase-2-implementation.md`](06-phase-2-implementation.md) | Phase 2: the gap reached from the browser renderer, the slider, saved with the piece |
| [`06-phase-3-implementation.md`](06-phase-3-implementation.md) | Phase 3: the four pages, every check, and what no check covers |

## What it is for

Two things, asked for together:

- **Undo and redo** on the sheet of the Playground's Rhythm page. Command-Z takes the last edit
  back, Shift-Command-Z puts it back, and the two are buttons beside **Write the sheet**. Every edit
  that lives in the page's own state is one step; the edits that write to the recording either go
  back through the backend or say plainly that they do not.
- **The space between lines** — a slider beside the Key signature that sets how much white space
  there is between one set of pentagrams and the next, so a piece with high notes can be given room
  and a plain one can be tightened up.

## What it does not touch

No frozen decision. Section 4 of the plan checks the seven that a reader would ask about, one by
one. The space between lines is vertical, so it is nowhere in the `time → x` map the whole layout
model rests on, and undo restores a previous set of the same values the page already stores.

## The decisions

None added. If one becomes necessary it goes in
[`../03-time-based-concept/decisions.md`](../03-time-based-concept/decisions.md) as the next D
number, which is where every binding decision about this product lives.
