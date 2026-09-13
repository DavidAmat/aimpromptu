# Time-based concept — the wall-clock matrix refactor

> **CLOSED on 2026-08-10.** This folder is history, not a worklist. Start with
> [`CLOSURE.md`](CLOSURE.md): what shipped, what was dropped on purpose, and what replaces this
> plan. Nothing here is waiting to be picked up, and the next piece of work is a **new**
> implementation plan in its own folder.

The piano matrix stopped being a grid of *note figures* and became a grid of *milliseconds*.
Figures stopped being the thing the layout is built from and became a label the user chooses. This
folder holds the requirements, the frozen decisions, the cross-package contract, the phased plan
and the progress trail for that change.

It touched **two repositories** and the order between them mattered, so everything is tracked here
in one place — including work done inside `vexflow-v2`. Both repositories are on the branch
`time-based-concept`.

## Navigate

| File | What it is |
|---|---|
| [`CLOSURE.md`](CLOSURE.md) | **Read this first.** Why the plan closed, what shipped, what was dropped and why, and the P8 numbering |
| [`checklist.md`](checklist.md) | The final state of every box, including the two cancellations |
| [`PRD.md`](PRD.md) | Why we did this, what changed, what was explicitly out of scope |
| [`decisions.md`](decisions.md) | **D-01 … D-34** — the frozen decisions. Still valid, still cited; a new plan that wants to change one has to say which and why |
| [`contract.md`](contract.md) | The live data contract between `aitu-backend` and `@aimpromptu/grid-notation`. §8 is the on-disk layout |
| [`user-reviews.md`](user-reviews.md) | What to open and click in the browser to see all of it. Kept current after closing |
| [`plan.md`](plan.md) | Phases 0–8 as they were planned. Historical: about a third of what shipped was never in it |
| [`system-prompt-worker.md`](system-prompt-worker.md) | The system prompt used for agents working one task of this plan |
| [`progress/`](progress/README.md) | One report per task, including tasks executed inside `vexflow-v2` |
| [`progress/issues.md`](progress/issues.md) | I-01 … I-06: everything that contradicted a frozen decision |
| [`progress/2026-08-08-overwrite-and-recovery.md`](progress/2026-08-08-overwrite-and-recovery.md) | The twelve backend files that were destroyed and rebuilt. **Authoritative over any comment inside them** |

The session trail for the whole refactor is
[`../progress/2026-08-10-time-based-concept-closed.md`](../01-epics-master-plan/progress/2026-08-10-time-based-concept-closed.md).

## The reporting rule (while this plan was live)

Phases 5 and 6 were implemented in the **`vexflow-v2`** repository
(`@aimpromptu/grid-notation`). That repository has its own `plan/` and `progress/` folders and they
were deliberately not used: everything about this refactor is reported here, so the two-package
order stays visible in one place.

Progress file name: `progress/P<phase>.<task>-<slug>.md`.

Keep this rule for any future plan that spans both repositories. It is the reason the cross-repo
order is reconstructable at all.

## Origin

The measurement that motivated this lives in
[`../../../poc-onset-duration-distribution/`](../../../poc-onset-duration-distribution/) —
`RESULTS.md` there is the evidence base for D-07 (measure on raw times) and for the worked example
at 00:46 that showed the old pipeline printing three equal corcheas as
semicorchea / dotted corchea / semicorchea. That example is now a regression test.

## Where to look deeper

- [`../../music/transcription-quality.md`](../../music/transcription-quality.md) — the four layers between audio and a printed figure. Layers 1–3 still hold; layer 4 is what this refactor replaced
- [`../../archive/superseded/01-matrix-notation-logic.md`](../../archive/superseded/01-matrix-notation-logic.md) — the notation model that was replaced, banner-marked as obsolete
- [`../../../documentation/issues/rhythm-figures-and-tempo.md`](../../../documentation/issues/rhythm-figures-and-tempo.md) — the runbook this refactor retired
- [`../plan/checklist.md`](../01-epics-master-plan/plan/checklist.md) — the original Epic 1–14 plan; this refactor superseded parts of Epics 2, 4 and 9
