# 04: App enhancements (the sheet page and the AI's sheet)

**State: done (2026-10-28).** Phases 1 to 4 checked by the user in the browser; Phase 5 (documentation and closing) closes it. **04-3** (the third brief, 2026-10-29: folders and metadata, then the whole song simplification by levels) is in progress: [`04-3-plan.md`](04-3-plan.md), branches `feat/04-3-phase-N`. Read [`04-context.md`](04-context.md) first: what this implementation changed, for later ones. One branch per phase, `feat/04-phase-N` (plan section 6.3).

Polish after implementation 03: on the sheet page, Command + scroll zoom, the AI symbol instead of the green badge,
the floating toolbox's buttons also in the header, a cursor that can be dragged, and a hidden floating toolbox that
comes back; a new logo, also the AI mark; in the sheet, a new decoration-note rule on every sheet, a prompt
(version 6) with rules of simplicity and an amateur pianist rule, run on 7 Years, and the Enhance with AI dialog with
Simplify left, right or both.

The brief is [`04-1-prompt.md`](04-1-prompt.md), the plan is [`04-plan.md`](04-plan.md) and the status lookup is
[`04-checklist.md`](04-checklist.md). Phase reports go beside them as `04-implementation-phase-N.md`, following
[`../../language/communication-implementation-plans.md`](../../language/communication-implementation-plans.md).

| File | What it is |
|---|---|
| [`04-context.md`](04-context.md) | **Read first for later work.** What implementation 04 changed, the decisions that bind, where the code is, the open points |
| [`04-1-prompt.md`](04-1-prompt.md) | The brief, in the user's own words, with the answers of the first discussion (2026-10-27) at its end, and the brief of the dialog (after the Phase 3 gallery) |
| [`04-2-prompt.md`](04-2-prompt.md) | The second brief: the new logo, traced to SVG, and the logo as the AI mark (branch `feat/04-logo`) |
| [`04-plan.md`](04-plan.md) | The plan: the decisions, the design notes, the binding rules, the method, five phases, the risks; its section 9 has the changes each phase made |
| [`04-checklist.md`](04-checklist.md) | The status lookup, and the open decisions |
| [`04-implementation-phase-1.md`](04-implementation-phase-1.md) | Phase 1: the sheet page |
| [`04-implementation-phase-2.md`](04-implementation-phase-2.md) | Phase 2: the decoration-note rule, the study of My library |
| [`gallery/phase-2/`](gallery/phase-2/index.html) | Phase 2: nine passages, the old rule and the new one |
| [`04-implementation-phase-3.md`](04-implementation-phase-3.md) | Phase 3: prompt version 6, the notes the AI adds and leaves out, the tests and the real run on 7 Years |
| [`gallery/phase-3/`](gallery/phase-3/index.html) | Phase 3: 7 Years with prompt 5 and with prompt 6, the image passages |
| [`04-implementation-phase-4.md`](04-implementation-phase-4.md) | Phase 4: the Enhance with AI dialog, a stretch of one hand, Simplify, the tests with the AI |
| [`gallery/phase-4/`](gallery/phase-4/index.html) | Phase 4: a stretch of one hand, Simplify left on 7 Years and Moonlight Shadow, before and after |
| [`04-implementation-phase-5.md`](04-implementation-phase-5.md) | Phase 5: the documentation, `04-context.md`, the final checks |
| [`screenshots/phase-1/`](screenshots/phase-1/) | Phase 1: the sheet page, from `check:frames-page` and `scripts/baseline-sheets.mjs` |
| [`images/`](images/) | The user's four examples: `abuse-decoration-notes.png`, `abuse-decoration-notes-right.png`, `left-patterns.png`, `complex-fast-notes.png` |

## 04-3: folders and metadata, and the whole song simplification by levels

Started 2026-10-29. One branch per phase, `feat/04-3-phase-N`; Phase 2 ran in parallel with Phase 1 in its own
worktree (plan section 7.4). Phases 1 and 2 are merged.

| File | What it is |
|---|---|
| [`04-3-prompt.md`](04-3-prompt.md) | The brief, in the user's own words |
| [`04-3-plan.md`](04-3-plan.md) | The living plan: folders, pills and metadata (Phase 1), the levels (Phases 2 to 4); section 10 has the changes each phase made |
| [`04-3-checklist.md`](04-3-checklist.md) | The 04-3 status lookup |
| [`04-3-implementation-phase-1.md`](04-3-implementation-phase-1.md) | Phase 1: folders, the pills (Folders, All, Filter) and the metadata, the info button |
| [`screenshots/04-3-phase-1/`](screenshots/04-3-phase-1/) | Phase 1: both pages and the dialogs, from `check:folders` |
| [`04-3-implementation-phase-2.md`](04-3-implementation-phase-2.md) | Phase 2: the sources, the patterns chosen, how the snapshots were cut and checked |
| [`gallery/04-3-phase-2/`](gallery/04-3-phase-2/index.html) | Phase 2: the gallery of patterns (a tab per hand, pills per level, the numbers) and `patterns.json`, the approved names Phase 3 uses |
| [`04-3-implementation-phase-2b.md`](04-3-implementation-phase-2b.md) | Phase 2b: frame marks on the sheet (a dashed line, the frame and the time every 100 frames), the frames in the range toolbox, decoration notes lit at their onset |
| [`screenshots/04-3-phase-2b/`](screenshots/04-3-phase-2b/) | Phase 2b: the marks on 99 Red Balloons (page and print), a song with lyrics, the range toolbox and a typed range |
| [`04-3-implementation-phase-3.md`](04-3-implementation-phase-3.md) | Phase 3: the grid, the chords, the measures, the level prompts, the plan of the song and the check |
| [`gallery/04-3-phase-3/`](gallery/04-3-phase-3/index.html) | Phase 3: the test passages of 99 Red Balloons, the patterns of each level, the prompts (and the AI's versions after task 3.7) |
| [`04-3-implementation-phase-4.md`](04-3-implementation-phase-4.md) | Phase 4: the level copy (`projects.level_of`), the catalog in the backend, the level run and its storing, the dialog, the first-minute AI test |
| [`images/chopin_passages/`](images/chopin_passages/) | The Chopin snapshots of the gallery, and the user's `ballade1-ex1.png` |
| [`images/99-red-ballons-issue.png`](images/99-red-ballons-issue.png), [`images/whole-song-simplification.png`](images/whole-song-simplification.png) | The user's two examples of a machine transcription that the levels must fix |
