# context/implementations

Every piece of planned work this project has run. The work is in two groups, and each group is a
numbered folder:

- **`01-mvp/`** holds the nine implementations that built the MVP: one audio file to one piano
  sheet, for one person. All of them are closed or complete. Their decisions and rules still bind
  new work.
- **`02-private-web-app/`** is the work being built now: the app of
  [`../app/01-app-context.md`](../app/01-app-context.md), with users, projects, the three storage
  layers, the music library and Play mode.

**Open a folder's own `README.md` first**, when it has one. It says whether that work is live or
closed.

## 01-mvp: the MVP

| # | Folder | What it is | Opened | State |
|---|---|---|---|---|
| 01 | [`01-epics-master-plan/`](01-mvp/01-epics-master-plan/README.md) | The whole product, cut into 14 epics: skeleton, matrix engine, audio, transcription, artifacts, the Playground tabs, notation, library, range editing, annotations, live composing, documentation | 2026-07-27 | **Complete 2026-09-13.** All 14 epics built. [`plan/checklist.md`](01-mvp/01-epics-master-plan/plan/checklist.md) is the status lookup; [`progress/RETROSPECTIVE.md`](01-mvp/01-epics-master-plan/progress/RETROSPECTIVE.md) closes the journal |
| 02 | [`02-vexflow-migration/`](01-mvp/02-vexflow-migration/README.md) | The brief that created our own notation renderer, `@aimpromptu/grid-notation`, in a separate repository (`vexflow-v2`), instead of drawing with VexFlow | 2026-07-28 | **Closed.** The package exists and draws every sheet the app shows |
| 03 | [`03-time-based-concept/`](01-mvp/03-time-based-concept/CLOSURE.md) | The wall-clock refactor: a column became a slice of real time, the note figure became a label you choose, and tempo left the product entirely | 2026-08-08 | **Closed 2026-08-10.** [`CLOSURE.md`](01-mvp/03-time-based-concept/CLOSURE.md) says what shipped and what was dropped |
| 04 | [`04-synthesia-to-notes/`](01-mvp/04-synthesia-to-notes/README.md) | Reading a piano roll video (the Synthesia kind, where rectangles fall onto a keyboard) into the same `events.json` the transcription model writes | 2026-09-13 | **Phases 1 to 4 complete; Phase 5 (the piano sheet) not started.** 02 moves the video reader into **New project → From source** and its development pages into Lab (decision Q-4). [`04-checklist.md`](01-mvp/04-synthesia-to-notes/04-checklist.md) is the status lookup |
| 05 | [`05-piano-overlay-from-black-keys/`](01-mvp/05-piano-overlay-from-black-keys/README.md) | Fitting the piano overlay onto a keyboard the camera is not square to: one rotatable rectangle, the black keys found inside it, the white keys derived from them | 2026-09-14 | **Complete 2026-09-14.** Replaced Story 2.1 of 04; V-09 superseded by V-37. [`05-checklist.md`](01-mvp/05-piano-overlay-from-black-keys/05-checklist.md) is the status lookup |
| 06 | [`06-varied-implementations/`](01-mvp/06-varied-implementations/README.md) | Smaller pieces of work asked for on top of the finished product, one brief at a time. The first: undo and redo on the sheet, and a slider for the space between one set of staves and the next | 2026-09-16 | **First brief complete 2026-09-16.** [`06-checklist.md`](01-mvp/06-varied-implementations/06-checklist.md) is the status lookup |
| 07 | [`07-enhancing-the-sheet/`](01-mvp/07-enhancing-the-sheet/07-00-context.md) | Enhancements of the piano sheet in four reports: the first six tasks, zoom and lyrics, octave brackets, and a last set of tools | 2026-09 | **Complete.** No checklist: [`07-00-context.md`](01-mvp/07-enhancing-the-sheet/07-00-context.md) is the context, [`07-01-new-enchancements-v1.md`](01-mvp/07-enhancing-the-sheet/07-01-new-enchancements-v1.md) the brief, and `07-01` to `07-04-implementation.md` the reports |
| 08 | [`08-new-algorithm-notes-detection-muscriptor/`](01-mvp/08-new-algorithm-notes-detection-muscriptor/README.md) | MuScriptor as the only transcription engine, the live piano roll and its editor, the hand split as a visible step, one flow page from audio to piano sheet, and the move to the Ubuntu machine with containers and one SSH tunnel | 2026-09-28 | **Complete 2026-10-01.** Ten phases. [`08-checklist.md`](01-mvp/08-new-algorithm-notes-detection-muscriptor/08-checklist.md) is the status lookup |
| 09 | [`09-minimal-ui/`](01-mvp/09-minimal-ui/09-minimal-ui-guidelines.md) | The rules for a minimal UI, and a brief to clean every page | 2026-10-04 | **Folded into 02.** The brief was never built on its own; 02 Phase 1 and every later UI phase apply [`09-minimal-ui-guidelines.md`](01-mvp/09-minimal-ui/09-minimal-ui-guidelines.md) and its pass of 13 checks |

## 02-private-web-app: the app being built now

| # | Folder | What it is | Opened | State |
|---|---|---|---|---|
| 02 | [`02-private-web-app/`](02-private-web-app/README.md) | The app of the app context: the design system and the sidebar shell, `.database/`, users and login on the home network, projects and the Personal Vault, the Private and Public Libraries, the sheet toolbox, copy and paste, Recording in Sheet, playlists, Play mode, requests and the Admin panel | 2026-10-05 | **Live.** Sixteen phases, 0 to 15. [`02-checklist.md`](02-private-web-app/02-checklist.md) is the status lookup |
| 02-a | [`02-private-web-app/public-library-build/`](02-private-web-app/public-library-build/README.md) | A parallel piece of work: the data of the Public Library, downloaded from `musicchartsarchive.com` into `data/music-library/` (next to the repository) | 2026-10-05 | **Live**, run by another agent. 02 Phase 12 reconciles it |

## How to read this folder

- **"What is being built now?"** → [`02-private-web-app/02-plan.md`](02-private-web-app/02-plan.md)
  and its checklist [`02-checklist.md`](02-private-web-app/02-checklist.md).
- **"What must a new task respect?"** →
  [`01-mvp/01-epics-master-plan/plan/wall-clock-rewrite.md`](01-mvp/01-epics-master-plan/plan/wall-clock-rewrite.md)
  (five rules, written after the refactor),
  [`01-mvp/03-time-based-concept/decisions.md`](01-mvp/03-time-based-concept/decisions.md)
  (D-01 … D-34, frozen and still binding), and section 11 of
  [`01-mvp/08-new-algorithm-notes-detection-muscriptor/08-plan.md`](01-mvp/08-new-algorithm-notes-detection-muscriptor/08-plan.md).
  Section 4 of the 02 plan checks them one by one and says which three it changes.
- **"How did the MVP get here, and what did it teach us?"** →
  [`01-mvp/01-epics-master-plan/progress/RETROSPECTIVE.md`](01-mvp/01-epics-master-plan/progress/RETROSPECTIVE.md)
  and [`01-mvp/03-time-based-concept/CLOSURE.md`](01-mvp/03-time-based-concept/CLOSURE.md).
- **"How should a screen look?"** →
  [`01-mvp/09-minimal-ui/09-minimal-ui-guidelines.md`](01-mvp/09-minimal-ui/09-minimal-ui-guidelines.md).
- **"What to open and click to see the MVP?"** →
  [`01-mvp/03-time-based-concept/user-reviews.md`](01-mvp/03-time-based-concept/user-reviews.md).

## The numbering rule

A path here is `NN-group/NN-implementation/`.

- **A group** is a large stage of the product. It gets the next free number at this level:
  `01-mvp/`, `02-private-web-app/`, then `03-<short-title>/`. A group is closed when its work is
  complete; it is not reopened.
- **An implementation** inside a group gets the next free number in that group. `01-mvp/` holds
  `01` to `09`. When a group is one implementation, as `02-private-web-app/` is, its files sit at the
  top of the group folder.
- **A parallel piece of work** inside an implementation takes the number of its parent and a letter,
  in its own subfolder: `02-a` is `02-private-web-app/public-library-build/`.
- **The files of an implementation** start with its number: `NN-prompt.md` (the brief, in the
  user's words), `NN-plan.md`, `NN-checklist.md` (the status lookup), and one report per phase,
  `NN-implementation-phase-N.md`. Each folder also has a `README.md` that says its state.

Do not add loose files at this level, and do not reuse another implementation's number. 03 explains
why in [`CLOSURE.md`](01-mvp/03-time-based-concept/CLOSURE.md): a duplicated "P8" had to be
untangled by hand.
