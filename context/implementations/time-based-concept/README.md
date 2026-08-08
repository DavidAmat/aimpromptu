# Time-based concept — the wall-clock matrix refactor

The piano matrix stops being a grid of *note figures* and becomes a grid of *milliseconds*.
Figures stop being the thing the layout is built from and become a label the user chooses. This
folder holds the requirements, the frozen decisions, the cross-package contract, the phased plan
and the progress trail for that change.

It touches **two repositories** and the order between them matters, so everything is tracked here
in one place — including work done inside `vexflow-v2`.

## Navigate

| File | What it is |
|---|---|
| [`PRD.md`](PRD.md) | Why we are doing this, what changes, what is explicitly out of scope |
| [`decisions.md`](decisions.md) | **D-01 … D-31** — the frozen decisions. Every task cites them; nothing is re-litigated in a task file |
| [`contract.md`](contract.md) | The data contract between `aitu-backend` and `@aimpromptu/grid-notation`. Freeze this before any code is written |
| [`plan.md`](plan.md) | Phases 0–8 with tasks, dependencies and exit criteria |
| [`checklist.md`](checklist.md) | **The status lookup.** Start here when picking up work |
| [`system-prompt-worker.md`](system-prompt-worker.md) | Template system prompt for an agent picking up one task or phase |
| [`progress/`](progress/README.md) | One report per task, including tasks executed inside `vexflow-v2` |

## The reporting rule (important)

Phases 5 and 6 are implemented in the **`vexflow-v2`** repository
(`@aimpromptu/grid-notation`). That repository has its own `plan/` and `progress/` folders — **do
not use them for this work.**

When you finish a task in `vexflow-v2`:

1. Come back to `aimpromptu/`.
2. Tick the task in [`checklist.md`](checklist.md).
3. Write the report in [`progress/`](progress/) using the naming below.
4. If you hit something that contradicts a decision, add it to `progress/issues.md` and stop —
   do not silently reinterpret a `D-nn`.

Progress file name: `progress/P<phase>.<task>-<slug>.md`, e.g. `progress/P5.2-silence-compression.md`.

## Origin

The measurement that motivated this lives in
[`../../../poc-onset-duration-distribution/`](../../../poc-onset-duration-distribution/) —
`RESULTS.md` there is the evidence base for D-07 (measure on raw times) and for the worked example
at 00:46 that shows the current pipeline printing three equal corcheas as
semicorchea / dotted corchea / semicorchea.

## Where to look deeper

- [`../../music/notation-logic/01-matrix-notation-logic.md`](../../music/notation-logic/01-matrix-notation-logic.md) — the notation model being replaced (Appendices A–D)
- [`../../music/transcription-quality.md`](../../music/transcription-quality.md) — the four layers between audio and a printed figure
- [`../../../documentation/issues/rhythm-figures-and-tempo.md`](../../../documentation/issues/rhythm-figures-and-tempo.md) — the runbook for "played evenly, prints ragged", which this refactor is meant to retire
- [`../plan/checklist.md`](../plan/checklist.md) — the original Epic 1–14 plan; this refactor supersedes parts of Epics 2, 4 and 9
