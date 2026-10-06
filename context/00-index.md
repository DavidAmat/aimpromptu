# Documentation index

Single table of contents for `context/` and `documentation/`. One line per file.

**New here?** Read [00-project-complete-overview.md](00-project-complete-overview.md) first, then
[backend/time-model.md](backend/time-model.md) — the second one is the idea every other file
assumes.

## Root

| File | Description |
|------|-------------|
| [../README.md](../README.md) | Project entry: what it does, the services, run locally, doc links |

## The app (`context/app/`)

| File | Description |
|------|-------------|
| [app/01-app-context.md](app/01-app-context.md) | **The app being built**, in the user's own words: projects, the three storage layers, the music library, playlists, Play mode. Its glossary is the vocabulary of every new page |

## Platform (`context/`)

| File | Description |
|------|-------------|
| [00-documentation-instructions.md](00-documentation-instructions.md) | Where to put new docs; the two-folder model; cross-linking rules |
| [00-index.md](00-index.md) | This file — map of all documentation |
| [00-project-complete-overview.md](00-project-complete-overview.md) | One-shot orientation for a fresh reader or LLM |
| [01-project.md](01-project.md) | What AImpromptu is, who uses it, the problem it solves |
| [02-tech-stack.md](02-tech-stack.md) | Locked versions from lockfiles, the containers, and the standing technical decisions |
| [02b-local-setup.md](02b-local-setup.md) | The Mac mini and the Ubuntu machine; section 12: AImpromptu on Ubuntu, the browser on the Mac through the tunnel |
| [03-services-overview.md](03-services-overview.md) | The two services and the renderer: roles, ports, how they connect |
| [04-local-development.md](04-local-development.md) | Run it in containers or natively, open it from the Mac, the checks, the troubleshooting table |
| [05-deployment.md](05-deployment.md) | STUB: POC local-only; no deploy flow yet |
| *(skipped)* `06-*-infrastructure.md` | No cloud provider; POC is local-only |
| [07-database.md](07-database.md) | `.database/`: SQLite and the project bundles, the audio store by hash, what is kept and why so little, backup and check |
| *(planned)* `08-security.md` | The login, the session cookie and the rights table; written by Phase 4 of 02 |
| [09-coding-conventions.md](09-coding-conventions.md) | Style grounded in ESLint and Python/uv idioms; LLM agent config inventory |

## Backend overview (`context/backend/`)

| File | Description |
|------|-------------|
| [backend/README.md](backend/README.md) | aitu-backend entry: the packages and what each is for |
| [backend/time-model.md](backend/time-model.md) | **The wall-clock model.** What replaced tempo, the five rules, what is dead |
| [backend/piano-matrix-notation.md](backend/piano-matrix-notation.md) | The piano matrix notation: the sparse form, `events.json` with ids and header, the wire columns, every adapter (`pmn/`) |
| [backend/muscriptor.md](backend/muscriptor.md) | **The transcription engine.** MuScriptor's settings and why, the GPU queue, the live stream of notes, the lag correction |
| [backend/pieces-and-revisions.md](backend/pieces-and-revisions.md) | The steps of a piece, the revisions, what makes a step stale, the `/pieces` routes, the saved hands |
| [backend/editing.md](backend/editing.md) | Re-recording a passage, and composing a piece from nothing |
| [backend/api.md](backend/api.md) | The HTTP surface: six routers and the shape of a session |
| [notation-and-parsing.md](../documentation/deprecated/notation-and-parsing.md) | Deprecated: the text-notation MVP path, deleted in implementation 02, Phase 1 |

## Frontend overview (`context/frontend/`)

| File | Description |
|------|-------------|
| [frontend/README.md](frontend/README.md) | aitu-frontend entry: the sections, the tabs, the data flow |
| [frontend/flow-page.md](frontend/flow-page.md) | **Projects and the steps of a project**: the five steps from the audio to the piano sheet, the editor's gestures, the timings |
| [frontend/pages.md](frontend/pages.md) | Routes, the shell, and the "position has one home" rule |
| [frontend/rendering.md](frontend/rendering.md) | How the sheet is drawn, what the app does *not* decide, the stale-`dist` trap |
| [frontend/annotations.md](frontend/annotations.md) | **The Sheet step**: the page, the defaults of a first write, the two selections, undo, saving |
| [frontend/annotations-notes.md](frontend/annotations-notes.md) | The note toolbox: figures, fingers, hand, beams, even spacing, decorations |
| [frontend/annotations-stretches.md](frontend/annotations-stretches.md) | The range toolbox (key, clef, octave, lyrics, spacing, speed, re-record) and brackets on the page |
| [frontend/annotations-sheet.md](frontend/annotations-sheet.md) | The sheet toolbox (title, key, figures, layout), the keyboard panel, Find trills |
| [frontend/printing.md](frontend/printing.md) | The PDF export: re-wrap to the paper, never scale; the margin is the control |
| [frontend/timestamps.md](frontend/timestamps.md) | UI rule: `mm:ss.cc`, frame labelled by start only, never wraps |

## Music (`context/music/`)

| File | Description |
|------|-------------|
| [music/notation-logic/02-notation-spec.md](music/notation-logic/02-notation-spec.md) | The text-notation contract, and the sparse-COO wire format every matrix still travels as |
| [music/transcription-quality.md](music/transcription-quality.md) | The four layers between audio and a printed figure; layer 4 is the one the wall clock removed |
| [music/piano_svg/01-piano-svg.md](music/piano_svg/01-piano-svg.md) | The 88-key SVG keyboard |

## Other context

| File | Description |
|------|-------------|
| [colors/color-palette.md](colors/color-palette.md) | The palette behind `ui/palette.ts` |
| [language/communication-style.md](language/communication-style.md) | How to write in this repository |
| [language/communication-implementation-plans.md](language/communication-implementation-plans.md) | How to report on an implementation plan: the walkthrough sections, the phase reports, the hand off |

## Implementations journal (`context/implementations/`)

| File | Description |
|------|-------------|
| [implementations/README.md](implementations/README.md) | **Start here.** The two groups (`01-mvp/`, `02-private-web-app/`), every implementation with its state, and the numbering rule |

### 02 — The private web app — LIVE

The app of [app/01-app-context.md](app/01-app-context.md): users, projects, the three storage layers,
the music library, playlists, Play mode, requests. Opened 2026-10-05.

| File | Description |
|------|-------------|
| [implementations/02-private-web-app/README.md](implementations/02-private-web-app/README.md) | What it is, and every file in the folder |
| [implementations/02-private-web-app/02-prompt.md](implementations/02-private-web-app/02-prompt.md) | The brief, in the user's own words |
| [implementations/02-private-web-app/02-plan.md](implementations/02-private-web-app/02-plan.md) | **The plan.** The structure of the app, the design system, `.database/`, users, projects, the sheet, the music library, sixteen phases |
| [implementations/02-private-web-app/02-checklist.md](implementations/02-private-web-app/02-checklist.md) | THE status lookup for this implementation, and the decisions Q-1 to Q-8 |
| `implementations/02-private-web-app/02-implementation-phase-N.md` | One report per finished phase |
| [implementations/02-private-web-app/public-library-build/README.md](implementations/02-private-web-app/public-library-build/README.md) | 02-a, the parallel work: the data of the Public Library from `musicchartsarchive.com` |

### 01-mvp — The MVP: one audio file to one piano sheet — CLOSED

Nine implementations, all closed or complete. Their rules and frozen decisions still bind new work.

#### 01 — Epics master plan — COMPLETE 2026-09-13

| File | Description |
|------|-------------|
| [implementations/01-mvp/01-epics-master-plan/README.md](implementations/01-mvp/01-epics-master-plan/README.md) | Status in one look |
| [implementations/01-mvp/01-epics-master-plan/plan/README.md](implementations/01-mvp/01-epics-master-plan/plan/README.md) | How the plan is organised; the epic list in implementation order |
| [implementations/01-mvp/01-epics-master-plan/plan/wall-clock-rewrite.md](implementations/01-mvp/01-epics-master-plan/plan/wall-clock-rewrite.md) | **Read before planning anything new.** The five rules, the splice rule, the verdict per epic |
| [implementations/01-mvp/01-epics-master-plan/plan/checklist.md](implementations/01-mvp/01-epics-master-plan/plan/checklist.md) | The status lookup of the fourteen epics |
| [implementations/01-mvp/01-epics-master-plan/plan/system-prompt-workers.md](implementations/01-mvp/01-epics-master-plan/plan/system-prompt-workers.md) | System prompt for worker LLMs implementing tasks |
| `implementations/01-mvp/01-epics-master-plan/plan/epic-NN-*/` | 14 epic folders, each with an index, story folders and task files |
| [implementations/01-mvp/01-epics-master-plan/progress/README.md](implementations/01-mvp/01-epics-master-plan/progress/README.md) | The progress journal: one report per task |
| [implementations/01-mvp/01-epics-master-plan/progress/RETROSPECTIVE.md](implementations/01-mvp/01-epics-master-plan/progress/RETROSPECTIVE.md) | **The journal, closed.** What the fourteen epics cost, what was cancelled, what held |
| [implementations/01-mvp/01-epics-master-plan/progress/2026-08-10-time-based-concept-closed.md](implementations/01-mvp/01-epics-master-plan/progress/2026-08-10-time-based-concept-closed.md) | The wall-clock refactor from start to close |
| [implementations/01-mvp/01-epics-master-plan/progress/plan-resume/README.md](implementations/01-mvp/01-epics-master-plan/progress/plan-resume/README.md) | The work committed after the refactor closed, reported late by Epic 14 |
| [implementations/01-mvp/01-epics-master-plan/progress/user_review/README.md](implementations/01-mvp/01-epics-master-plan/progress/user_review/README.md) | What to open and click, per epic |

#### 02 — VexFlow migration — CLOSED

| File | Description |
|------|-------------|
| [implementations/01-mvp/02-vexflow-migration/README.md](implementations/01-mvp/02-vexflow-migration/README.md) | Why we built our own renderer instead of drawing with VexFlow |
| [implementations/01-mvp/02-vexflow-migration/01-system-prompt-vexflow-v2.md](implementations/01-mvp/02-vexflow-migration/01-system-prompt-vexflow-v2.md) | The brief that created `@aimpromptu/grid-notation` |

#### 03 — Time-based concept refactor — CLOSED 2026-08-10

Wall-clock matrix columns and figure-as-label rendering. Spanned **two repositories**. The folder
is history, but `decisions.md` stays binding.

| File | Description |
|------|-------------|
| [implementations/01-mvp/03-time-based-concept/CLOSURE.md](implementations/01-mvp/03-time-based-concept/CLOSURE.md) | **Start here.** Why it closed, what shipped, what was dropped, the duplicated P8 numbering |
| [implementations/01-mvp/03-time-based-concept/README.md](implementations/01-mvp/03-time-based-concept/README.md) | Navigation and the cross-repo reporting rule |
| [implementations/01-mvp/03-time-based-concept/PRD.md](implementations/01-mvp/03-time-based-concept/PRD.md) | Why, what changes, what is out of scope, success criteria |
| [implementations/01-mvp/03-time-based-concept/decisions.md](implementations/01-mvp/03-time-based-concept/decisions.md) | **D-01 … D-34, frozen and still binding.** Every task cites these |
| [implementations/01-mvp/03-time-based-concept/contract.md](implementations/01-mvp/03-time-based-concept/contract.md) | Backend ↔ `@aimpromptu/grid-notation` data contract |
| [implementations/01-mvp/03-time-based-concept/plan.md](implementations/01-mvp/03-time-based-concept/plan.md) | Phases 0–8 as planned. Historical |
| [implementations/01-mvp/03-time-based-concept/checklist.md](implementations/01-mvp/03-time-based-concept/checklist.md) | The final state of every box, with the two cancellations |
| [implementations/01-mvp/03-time-based-concept/progress/README.md](implementations/01-mvp/03-time-based-concept/progress/README.md) | Where task reports go, including `vexflow-v2` work |
| [implementations/01-mvp/03-time-based-concept/progress/issues.md](implementations/01-mvp/03-time-based-concept/progress/issues.md) | Append-only log of anything contradicting a frozen decision |
| [implementations/01-mvp/03-time-based-concept/user-reviews.md](implementations/01-mvp/03-time-based-concept/user-reviews.md) | **What to open and click to see all of it** |

#### 04 — Synthesia to notes — Phases 1 to 4 complete

Reading a piano roll video into the same `events.json` the transcription model writes. Opened
2026-09-13. 02 moves the video reader into **From source** and its development pages into Lab.

| File | Description |
|------|-------------|
| [implementations/01-mvp/04-synthesia-to-notes/README.md](implementations/01-mvp/04-synthesia-to-notes/README.md) | What it is, and every file in the folder |
| [implementations/01-mvp/04-synthesia-to-notes/04-prompt.md](implementations/01-mvp/04-synthesia-to-notes/04-prompt.md) | The brief, in the user's own words |
| [implementations/01-mvp/04-synthesia-to-notes/04-plan.md](implementations/01-mvp/04-synthesia-to-notes/04-plan.md) | **The plan.** Terminology, storage, the HTTP surface, the algorithm, the five phases |
| [implementations/01-mvp/04-synthesia-to-notes/04-decisions.md](implementations/01-mvp/04-synthesia-to-notes/04-decisions.md) | **V-01 … V-43, frozen.** V-09 is superseded by V-37 |
| [implementations/01-mvp/04-synthesia-to-notes/04-checklist.md](implementations/01-mvp/04-synthesia-to-notes/04-checklist.md) | The status lookup for this implementation |
| [implementations/01-mvp/04-synthesia-to-notes/04-phase-1-implementation.md](implementations/01-mvp/04-synthesia-to-notes/04-phase-1-implementation.md) | Phase 1: the survey, the casuistry catalogue, the five detectors, the scroll speed |
| [implementations/01-mvp/04-synthesia-to-notes/04-phase-2-implementation.md](implementations/01-mvp/04-synthesia-to-notes/04-phase-2-implementation.md) | Phase 2: the detector in the app, the annotation page, the score board |
| [implementations/01-mvp/04-synthesia-to-notes/04-phase-3-implementation.md](implementations/01-mvp/04-synthesia-to-notes/04-phase-3-implementation.md) | Phase 3: a real video downloaded, sampled, calibrated, measured and read into `frames.jsonl` |
| `implementations/01-mvp/04-synthesia-to-notes/examples/` | 24 screenshots covering how these videos draw a rectangle; the backend reads them for Lab |

#### 05 — The piano overlay, found from the black keys — COMPLETE 2026-09-14

| File | Description |
|------|-------------|
| [implementations/01-mvp/05-piano-overlay-from-black-keys/README.md](implementations/01-mvp/05-piano-overlay-from-black-keys/README.md) | What it is, what it does not touch, and the decisions it changed |
| [implementations/01-mvp/05-piano-overlay-from-black-keys/05-prompt.md](implementations/01-mvp/05-piano-overlay-from-black-keys/05-prompt.md) | The brief, in the user's own words |
| [implementations/01-mvp/05-piano-overlay-from-black-keys/05-plan.md](implementations/01-mvp/05-piano-overlay-from-black-keys/05-plan.md) | **The plan.** The model change and its cost, the finder, the two routes and their score, three phases |
| [implementations/01-mvp/05-piano-overlay-from-black-keys/05-checklist.md](implementations/01-mvp/05-piano-overlay-from-black-keys/05-checklist.md) | The status lookup for this implementation |
| `implementations/01-mvp/05-piano-overlay-from-black-keys/05-phase-N-implementation.md` | Three phase reports: the finder and the route chosen, per-key borders, the finder in the app |
| `pocs/poc-piano-overlay/` | Phase 1's spike, under `pocs/`: scripts, truth, tables in `RESULTS.md` |

#### 06 — Varied implementations — first brief COMPLETE 2026-09-16

| File | Description |
|------|-------------|
| [implementations/01-mvp/06-varied-implementations/README.md](implementations/01-mvp/06-varied-implementations/README.md) | Undo and redo on the sheet, and the slider for the space between systems |
| [implementations/01-mvp/06-varied-implementations/06-checklist.md](implementations/01-mvp/06-varied-implementations/06-checklist.md) | The status lookup |

#### 07 — Enhancing the sheet — COMPLETE

| File | Description |
|------|-------------|
| [implementations/01-mvp/07-enhancing-the-sheet/07-00-context.md](implementations/01-mvp/07-enhancing-the-sheet/07-00-context.md) | The context every task of 07 starts from |
| [implementations/01-mvp/07-enhancing-the-sheet/07-01-new-enchancements-v1.md](implementations/01-mvp/07-enhancing-the-sheet/07-01-new-enchancements-v1.md) | The brief: nine tasks on the piano sheet |
| `implementations/01-mvp/07-enhancing-the-sheet/07-0N-implementation.md` | Four reports: tasks 1 to 6, zoom and lyrics, octave brackets, task 9 |

#### 08 — MuScriptor, the live piano roll, and the move to Ubuntu — COMPLETE 2026-10-01

| File | Description |
|------|-------------|
| [implementations/01-mvp/08-new-algorithm-notes-detection-muscriptor/README.md](implementations/01-mvp/08-new-algorithm-notes-detection-muscriptor/README.md) | What it is, and every file in the folder |
| [implementations/01-mvp/08-new-algorithm-notes-detection-muscriptor/08-prompt.md](implementations/01-mvp/08-new-algorithm-notes-detection-muscriptor/08-prompt.md) | The brief, in the user's own words |
| [implementations/01-mvp/08-new-algorithm-notes-detection-muscriptor/08-plan.md](implementations/01-mvp/08-new-algorithm-notes-detection-muscriptor/08-plan.md) | **The plan.** Terminology, the format, the flow page, revisions, the move, ten phases, decisions Q-1 to Q-7 (section 11) |
| [implementations/01-mvp/08-new-algorithm-notes-detection-muscriptor/08-checklist.md](implementations/01-mvp/08-new-algorithm-notes-detection-muscriptor/08-checklist.md) | The status lookup for this implementation |
| `implementations/01-mvp/08-new-algorithm-notes-detection-muscriptor/08-implementation-phase-N.md` | Ten phase reports, 0 to 9 |
| `implementations/01-mvp/08-new-algorithm-notes-detection-muscriptor/measurements/` | Raw measurements of Phases 2 to 9 |
| `pocs/poc-muscriptor/` | Phase 1's POC: MuScriptor's output, speed, lag, against ByteDance; `RESULTS.md` |

#### 09 — Minimal UI — folded into 02

| File | Description |
|------|-------------|
| [implementations/01-mvp/09-minimal-ui/09-minimal-ui-guidelines.md](implementations/01-mvp/09-minimal-ui/09-minimal-ui-guidelines.md) | **The rules for every screen**, and the pass of 13 checks every UI phase of 02 runs |
| [implementations/01-mvp/09-minimal-ui/09-prompt.md](implementations/01-mvp/09-minimal-ui/09-prompt.md) | The brief, absorbed by the 02 plan |

## Archive (`context/archive/`)

| File | Description |
|------|-------------|
| [archive/README.md](archive/README.md) | Historical context; pointer to the docs-migration kit |
| [archive/superseded/README.md](archive/superseded/README.md) | **Documents describing a model or screen the app no longer has**, with where each current answer lives |
| `archive/superseded/` | `01-matrix-notation-logic.md`, `03-editing-logic.md`, `app-shell.md`, `compose-panel.md`, `loaded-scores.md`, `rendering-pipeline.md` |
| `archive/docs-migration/` | The completed documentation migration kit: plan, checklist, templates, deletions log |
| `archive/TODO.md`, `archive/project-features.md`, `archive/project-implementation-organization.md` | The first notes and briefs of the project, from before the MVP; they describe the old model |
| [archive/piano-transcription-python-solutions.md](archive/piano-transcription-python-solutions.md) | The engine survey that chose ByteDance before MuScriptor replaced it |

## Documentation tree (`documentation/`)

| File | Description |
|------|-------------|
| [../documentation/README.md](../documentation/README.md) | Layout of the detail tree |
| [../documentation/services/README.md](../documentation/services/README.md) | Service detail index |

### Backend detail (`documentation/services/backend/`)

| File | Description |
|------|-------------|
| [../documentation/services/backend/endpoints.md](../documentation/services/backend/endpoints.md) | The whole HTTP surface, route by route, and what each obeys |
| [../documentation/services/backend/time-matrix.md](../documentation/services/backend/time-matrix.md) | Schema 2.0 field reference: envelope, ladder, passages, printed notes, layout hints |
| [../documentation/services/backend/events-to-sheet.md](../documentation/services/backend/events-to-sheet.md) | The derivation path, step by step, with the reason for each ordering |
| [../documentation/services/backend/transcription-pipeline.md](../documentation/services/backend/transcription-pipeline.md) | Engines, thresholds, the artifact and leakage filters, the measurement behind each number |
| [../documentation/services/backend/hand-inference-second-pass.md](../documentation/services/backend/hand-inference-second-pass.md) | The gated repair pass over the hand split |
| [../documentation/services/backend/rhythm-and-annotations.md](../documentation/services/backend/rhythm-and-annotations.md) | `rhythm.json` field by field: everything a reader decided |
| [../documentation/services/backend/editing-and-compose.md](../documentation/services/backend/editing-and-compose.md) | The replacement splice, and the one place a piece may change length |
| [../documentation/services/backend/paths-and-data.md](../documentation/services/backend/paths-and-data.md) | `.database/`: every path, the bundle, the timeline, every table, the migration, backup and check |
| [../documentation/deprecated/schemas.md](../documentation/deprecated/schemas.md) | Deprecated: the models of the deleted text-notation MVP |
| [../documentation/deprecated/sequence-logic.md](../documentation/deprecated/sequence-logic.md) | Deprecated: `matrix/text_notation.py`, now only a builder of test matrices |

### Frontend detail (`documentation/services/frontend/`)

| File | Description |
|------|-------------|
| [../documentation/services/frontend/components.md](../documentation/services/frontend/components.md) | The component tree, the routes, and where each piece lives |
| [../documentation/services/frontend/grid-notation.md](../documentation/services/frontend/grid-notation.md) | The renderer seam: every option passed in, and what went with the old editor |
| [../documentation/services/frontend/score-pdf.md](../documentation/services/frontend/score-pdf.md) | The PDF writer: SVG to operators, the embedded Bravura, how to check a bad file |

### Other (`documentation/`)

| File | Description |
|------|-------------|
| [../documentation/issues/README.md](../documentation/issues/README.md) | Troubleshooting runbooks |
| [../documentation/issues/piano-matrix-sustains-and-phantom-onsets.md](../documentation/issues/piano-matrix-sustains-and-phantom-onsets.md) | Held chords printing short; chords with a note too many |
| [../documentation/issues/hand-split-ledger-lines.md](../documentation/issues/hand-split-ledger-lines.md) | A hand printed far outside its own staff under a pile of ledger lines |
| [../documentation/issues/rhythm-figures-and-tempo.md](../documentation/issues/rhythm-figures-and-tempo.md) | **Retired.** An evenly played passage printing as mixed figures — the bug class the wall clock removed |
| [../documentation/implementations/README.md](../documentation/implementations/README.md) | Stable topic-based how-tos |
| [../documentation/deprecated/README.md](../documentation/deprecated/README.md) | Superseded or removed features (banner required) |
| [../documentation/archive/README.md](../documentation/archive/README.md) | Historical reference |
| [../documentation/archive/vexflow-reference.md](../documentation/archive/vexflow-reference.md) | Archived VexFlow EasyScore notes |

## The renderer's own documentation

`@aimpromptu/grid-notation` is documented in the sibling checkout, not here:
`../vexflow-v2/documentation/` — seven numbered files from quick start through annotations,
playback and integration.

## Subrepo pointers

| File | Description |
|------|-------------|
| [../aitu-backend/README.md](../aitu-backend/README.md) | Backend entry → links to `context/backend/` |
| [../aitu-frontend/README.md](../aitu-frontend/README.md) | Frontend entry → links to `context/frontend/` |
