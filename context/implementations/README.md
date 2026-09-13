# context/implementations

Every piece of planned work this project has run, one folder each, numbered in the order it was
opened. A folder holds everything about that piece of work: what it was for, the plan, the
decisions, and the progress reports.

**Open a folder's own `README.md` first.** It says whether that work is live or closed.

| # | Folder | What it is | Opened | State |
|---|---|---|---|---|
| 01 | [`01-epics-master-plan/`](01-epics-master-plan/README.md) | The whole product, cut into 14 epics: skeleton, matrix engine, audio, transcription, artifacts, the Playground tabs, notation, library, range editing, annotations, live composing, documentation | 2026-07-27 | **Live.** Epics 1–11 built; Story 9.7 and Epics 12–14 remain. [`plan/checklist.md`](01-epics-master-plan/plan/checklist.md) is the status lookup |
| 02 | [`02-vexflow-migration/`](02-vexflow-migration/README.md) | The brief that created our own notation renderer, `@aimpromptu/grid-notation`, in a separate repository (`vexflow-v2`), instead of drawing with VexFlow | 2026-07-28 | **Closed.** The package exists and draws every sheet the app shows |
| 03 | [`03-time-based-concept/`](03-time-based-concept/CLOSURE.md) | The wall-clock refactor: a column became a slice of real time, the note figure became a label you choose, and tempo left the product entirely | 2026-08-08 | **Closed 2026-08-10.** Nothing here is waiting to be picked up; [`CLOSURE.md`](03-time-based-concept/CLOSURE.md) says what shipped and what was dropped |

## How to read this folder

- **"Where are we?"** → [`01-epics-master-plan/plan/checklist.md`](01-epics-master-plan/plan/checklist.md).
  It is the one status list for the project.
- **"Why does the app work this way?"** → [`03-time-based-concept/decisions.md`](03-time-based-concept/decisions.md)
  (D-01 … D-34, frozen and still binding) and
  [`03-time-based-concept/CLOSURE.md`](03-time-based-concept/CLOSURE.md).
- **"What must a new task respect?"** →
  [`01-epics-master-plan/plan/wall-clock-rewrite.md`](01-epics-master-plan/plan/wall-clock-rewrite.md).
  Five rules, written after the refactor. Read it before planning anything new.
- **"What to open and click to see it?"** →
  [`03-time-based-concept/user-reviews.md`](03-time-based-concept/user-reviews.md).

## Adding the next implementation

Give it the next number and a short title: `04-<short-title>/`. Inside, keep its own `README.md`,
its plan, its checklist and a `progress/` folder for the task reports. Do not add loose files at
this level and do not reuse another implementation's numbering — 03 says so explicitly, and the
duplicated "P8" it had to untangle is the reason.
