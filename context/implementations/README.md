# context/implementations

Every piece of planned work this project has run, one folder each, numbered in the order it was
opened. A folder holds everything about that piece of work: what it was for, the plan, the
decisions, and the progress reports.

**Open a folder's own `README.md` first.** It says whether that work is live or closed.

| # | Folder | What it is | Opened | State |
|---|---|---|---|---|
| 01 | [`01-epics-master-plan/`](01-epics-master-plan/README.md) | The whole product, cut into 14 epics: skeleton, matrix engine, audio, transcription, artifacts, the Playground tabs, notation, library, range editing, annotations, live composing, documentation | 2026-07-27 | **Complete 2026-09-13.** All 14 epics built. [`plan/checklist.md`](01-epics-master-plan/plan/checklist.md) is the status lookup; [`progress/RETROSPECTIVE.md`](01-epics-master-plan/progress/RETROSPECTIVE.md) closes the journal |
| 02 | [`02-vexflow-migration/`](02-vexflow-migration/README.md) | The brief that created our own notation renderer, `@aimpromptu/grid-notation`, in a separate repository (`vexflow-v2`), instead of drawing with VexFlow | 2026-07-28 | **Closed.** The package exists and draws every sheet the app shows |
| 03 | [`03-time-based-concept/`](03-time-based-concept/CLOSURE.md) | The wall-clock refactor: a column became a slice of real time, the note figure became a label you choose, and tempo left the product entirely | 2026-08-08 | **Closed 2026-08-10.** Nothing here is waiting to be picked up; [`CLOSURE.md`](03-time-based-concept/CLOSURE.md) says what shipped and what was dropped |
| 04 | [`04-synthesia-to-notes/`](04-synthesia-to-notes/README.md) | Reading a piano roll video — the Synthesia kind, where rectangles fall onto a keyboard — into the same `events.json` the transcription model writes | 2026-09-13 | **Live.** Five phases: research, evaluation against hand-annotated examples, video download and frame sampling, the piece, the sheet. [`04-checklist.md`](04-synthesia-to-notes/04-checklist.md) is the status lookup |
| 05 | [`05-piano-overlay-from-black-keys/`](05-piano-overlay-from-black-keys/README.md) | Fitting the piano overlay onto a keyboard the camera is not square to: one rotatable rectangle, the black keys found inside it, the white keys derived from them | 2026-09-14 | **Complete 2026-09-14.** Three phases in one day: the route measured and chosen (route A, from the black keys), per-key borders in both services, the finder in the app with every example found. Replaced Story 2.1 of 04; V-09 superseded by V-37. [`05-checklist.md`](05-piano-overlay-from-black-keys/05-checklist.md) is the status lookup |
| 06 | [`06-varied-implementations/`](06-varied-implementations/README.md) | The smaller pieces of work asked for on top of the finished product, one brief at a time. The first: undo and redo on the sheet, and a slider for the space between one set of pentagrams and the next | 2026-09-16 | **First brief complete 2026-09-16.** Three phases in one day. [`06-checklist.md`](06-varied-implementations/06-checklist.md) is the status lookup |

## How to read this folder

- **"Where are we?"** → [`01-epics-master-plan/plan/checklist.md`](01-epics-master-plan/plan/checklist.md).
  It is the one status list for the project. Every epic is done; three defects are open under
  Epic 14.
- **"How did we get here, and what did it teach us?"** →
  [`01-epics-master-plan/progress/RETROSPECTIVE.md`](01-epics-master-plan/progress/RETROSPECTIVE.md).
- **"Why does the app work this way?"** → [`03-time-based-concept/decisions.md`](03-time-based-concept/decisions.md)
  (D-01 … D-34, frozen and still binding) and
  [`03-time-based-concept/CLOSURE.md`](03-time-based-concept/CLOSURE.md).
- **"What must a new task respect?"** →
  [`01-epics-master-plan/plan/wall-clock-rewrite.md`](01-epics-master-plan/plan/wall-clock-rewrite.md).
  Five rules, written after the refactor. Read it before planning anything new.
- **"What was added after the product was finished?"** →
  [`06-varied-implementations/`](06-varied-implementations/README.md), one brief at a time.
- **"What is being built now?"** → [`04-synthesia-to-notes/04-plan.md`](04-synthesia-to-notes/04-plan.md),
  with its own frozen decisions in
  [`04-synthesia-to-notes/04-decisions.md`](04-synthesia-to-notes/04-decisions.md) (V-01 … V-43),
  and [`05-piano-overlay-from-black-keys/05-plan.md`](05-piano-overlay-from-black-keys/05-plan.md),
  which replaces the piano overlay of 04.
- **"What to open and click to see it?"** →
  [`03-time-based-concept/user-reviews.md`](03-time-based-concept/user-reviews.md).

## Adding the next implementation

Give it the next number and a short title: `07-<short-title>/`. Inside, keep its own `README.md`,
its plan, its checklist and a `progress/` folder for the task reports. Do not add loose files at
this level and do not reuse another implementation's numbering — 03 says so explicitly, and the
duplicated "P8" it had to untangle is the reason.
