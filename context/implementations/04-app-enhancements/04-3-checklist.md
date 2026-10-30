# 04-3: Folders and metadata, and the whole song simplification by levels: checklist

The status lookup for this plan. The plan is [`04-3-plan.md`](04-3-plan.md), the brief is
[`04-3-prompt.md`](04-3-prompt.md). Each phase report is `04-3-implementation-phase-N.md`, written by the agent that
finishes the phase, following `context/guidelines/guidelines-implementation-plan.md` and
`context/guidelines/guidelines-communication-with-user.md`.

One phase is one agent session, on its own branch `feat/04-3-phase-N` made from `master` (plan section 7.3). Phases
3 and 4 branch after Phase 1 is merged (plan section 4.5). Every phase starts with its study and may change its own
tasks and later ones (plan section 7.2); a changed task is changed here and in the plan (section 10 of the plan says
why). Every phase also updates the documentation it makes stale and leaves `scripts/docs/check-links.py` passing.

Status letters: `[x]` complete, `[p]` in progress, `[b]` blocked, `[c]` cancelled, `[ ]` not started.

## Decisions

- [x] **The brief** (user, 2026-10-29; `04-3-prompt.md`): folders and metadata first, in one phase; then the whole
  song simplification by levels (easy, medium, hard; super hard later) in phases that need the user's action.
- [x] **Phase 1**: the user checks My projects, My Library and the info button in the browser (ok on 2026-10-29).
- [x] **Phase 2**: the user approves the gallery of patterns (approved on 2026-10-30, after review 6; plan section 10).
- [x] **The catalog and the frame numbers** (user, 2026-10-29, review 2 of Phase 2): plan section 5.10; Phase 2b
  comes before Phase 3 (confirmed by the user at the merge).
- [x] **Phase 3**: the user approves the three levels on the passages of 99 Red Balloons (2026-10-30).
- [x] **Phase 4**: where a level version is stored (plan section 5.8), confirmed with the user on 2026-10-30: a new
  project per level of the whole sheet, linked to its original by `projects.level_of` (not an edit copy); the
  patterns approved in Phase 3 when none is selected; a level per hand in the dialog; the AI test on the first minute
  of 99 Red Balloons only, hard for the right hand and medium for the left hand (plan section 10).

# [x] Phase 1: Folders, the pills and the metadata

- [x] Task 1.1 This checklist; the folder's `README.md`.
- [x] Task 1.2 Study: section 4.1 confirmed; the Save to library and Edit paths for folders; where a project has an
  artist; the three cases of the info button (report section 2).
- [x] Task 1.3 Revision `0008` (six tables) and the models, after the process check and `make db-backup`; the real
  database moved to it on 2026-10-29.
- [x] Task 1.4 The routes `/folders` and `/metadata`; the folder ids and the metadata in the rows of `GET /projects`
  and `GET /library/songs`; tests, and the rights table.
- [x] Task 1.5 **Add to my library** copies the public tags as private metadata; Edit, Save to library and Duplicate
  carry the metadata.
- [x] Task 1.6 The pills on both pages; **Folders** (the tree, open and close, indentation, New folder, the folder
  menu, drag and drop, "Folders…"); **Filter** (Artist and the primary keys).
- [x] Task 1.7 The info button and its dialog on the sheet page and on the song page of My Library (and **Info** in a
  row's `⋯`).
- [x] Task 1.8 Checks: `check:folders` (new), `check:projects`, `check:library`, `check:frames-page`,
  `check:enhance-dialog`; screenshots in `screenshots/04-3-phase-1/`; the documentation.
- [x] Task 1.9 The user checks both pages and the info button in the browser (ok on 2026-10-29; merged into
  `master`).
- [x] Task 1.10 After the user's first look: the metadata belongs to the song, never to one version. An edit copy
  shows and changes its song's metadata and folders of My Library; revision `0009` moved the copy's rows to the song
  (plan section 10, Phase 1, point 10).

# [x] Phase 2: The gallery of patterns

- [x] Task 2.1 The Chopin folder on Ubuntu (`/home/david/Documents/projects/music/chopin`, the user copies it).
- [x] Task 2.2 Sources: the PDFs, the kern files of the research, its pattern library and level texts.
- [x] Task 2.3 The passages the user named (Ballade No. 1 pages 10 and 12, Ballade No. 4 pages 41 to 56, the Waltzes).
- [x] Task 2.4 Leave out the left hands that run up and down like scales.
- [x] Task 2.5 The easy patterns of the brief drawn by the app's engine.
- [x] Task 2.6 The snapshots in `images/chopin_passages/`, each checked zoomed in.
- [x] Task 2.7 The gallery `gallery/04-3-phase-2/index.html` (two tabs, level pills) and `patterns.json`.
- [x] Task 2.8 The user's review, until approved (review 1: 30 drawn variations; review 2: the next task; reviews 3 to 6: right hands across Chopin's works, the stricter super hard; approved
  and merged into `master` on 2026-10-30).
- [x] Task 2.9 Every pattern in the app's notation (the Chopin ones from the kern), and the numbers inside each hand
  and level.

# [x] Phase 2b: Frame numbers on the sheet and in the range toolbox

Built on `feat/04-3-phase-2b` (2026-10-30); report [`04-3-implementation-phase-2b.md`](04-3-implementation-phase-2b.md).

- [x] Task 2b.1 Study: how the engine draws a line, how the page lays the SVG and the cursor, the range toolbox.
- [x] Task 2b.2 The frame number on the sheet: after the user's first look, a dashed line every 100 frames with the
  frame number and the time on top; also in the zoom and the print (drawn by the engine).
- [x] Task 2b.3 The range toolbox: the first and the last frame number of the selected range, in two fields that mark
  the stretch they name (the user's request).
- [x] (the user, during the phase) A decoration note lights at its own onset, not with the note before it.
- [x] Task 2b.4 Checks: `check:frames-page` with the numbers (passed), screenshots in `screenshots/04-3-phase-2b/`;
  the user checked the sheet page and approved it on 2026-10-30.

# [x] Phase 3: The level prompts, tested on 99 Red Balloons

- [x] Task 3.1 Study of 99 Red Balloons (`c0e39afe`): the passages of the two images and two or three more.
- [x] Task 3.2 The measures ported to the app's time, with tests.
- [x] Task 3.3 The grid of the song, measured on 99 Red Balloons and on one song played by a human.
- [x] Task 3.4 The prompts: a shared part and `easy.md`, `medium.md`, `hard.md`; a new `VERSION`; a place for the F1
  text of the patterns of a run and for the user's places by frame number (plan section 5.10).
- [x] Task 3.5 The plan of the song and its prompt.
- [x] Task 3.6 The check of a level run, with tests on recorded answers.
- [x] Task 3.7 Tests with the AI (the user asked first, with the cost). Hard right, medium left done on the four
  passages twice, with the user's three rules of review 1 ($1.58 in all), approved by the user; medium and easy run
  ($1.54), then written again with the steady rhythm of easy and medium ($1.68; report sections 14 and 15).
- [x] Task 3.8 The gallery `gallery/04-3-phase-3/`: the test passages, the patterns per level, the prompts, and the
  hard-right medium-left, medium and easy versions (`http://ubuntu:8097/gallery/04-3-phase-3/index.html`).
- [x] Task 3.9 The user's review, until the three levels are approved (approved on 2026-10-30; the AI's changes
  confirmed in `notes.pmn` and the Notes tab, report section 16).

# [x] Phase 4: The levels in the app

- [x] Task 4.1 Study; section 5.8 confirmed with the user (changed: the level copy's own link, revision `0010`).
- [x] Task 4.2 The dialog: the levels on a range and on the whole sheet, with the cost; the catalog of patterns and
  the references in the words (plan section 5.10).
- [x] Task 4.3 The run: `start_level`, `write_level`, the check, the feedback, the stand-in tests.
- [x] Task 4.4 Storing: a new project per level of the whole sheet; a range in place with one step of undo.
- [x] Task 4.5 Tests with the AI: the first minute of 99 Red Balloons (a temporary copy split at 60 s), hard for the
  right hand and medium for the left hand, through the app (the user, 2026-10-30): $0.88, 4 of 4 batches; a missing
  beam fault found and fixed (report section 8).
- [x] Task 4.6 Checks (`check:enhance-dialog` with the levels passes); the user checked the level and approved the merge (2026-10-30).
- [c] Task 4.7 The real runs on the whole of 99 Red Balloons: replaced by the first-minute test of task 4.5 (the user,
  2026-10-30). The whole song at a level is for the user to start from the dialog, when wanted.

# [x] Phase 5: Other AI models for the level runs (OpenAI), judged against Sonnet 5.5

- [x] Task 5.1 Prices and model ids of GPT-6 Luna, GPT-6.1 Terra, GPT-6.1 Sol from the internet (input, cached
  input, cache write, output; the caching rules of GPT-6, which bill the writes); a first estimate per song.
- [x] Task 5.2 `OpenAIComplete` in `sheet_llm.py` (the `openai` SDK, the Responses API, explicit cache breakpoints, the
  same `Call` measures and reasoning tokens), with tests without requests.
- [x] Task 5.3 The cache test with GPT-6 Luna: the system prompt read from the second request on; a fault fixed (the
  earlier turns of a conversation were not read: a breakpoint on every user message).
- [x] Task 5.4 The test set: 16 cases (4 passages × easy, medium, hard right with medium left, one forced pattern), run
  by Sonnet 5.5 and the three OpenAI models at `medium` (the user, 2026-10-30, after the `max` measures on the riff).
- [x] Task 5.5 The measures, and the cost and time extrapolated to a whole song.
- [x] Task 5.6 The judgment: by the agent itself, blind (the user, 2026-10-30: no judge through an API).
- [x] Task 5.7 The report `gallery/04-3-phase-5/index.html` (two tabs: the comparison, the examples), served.
- [x] Task 5.8 The user's decision (2026-10-30): the level runs use GPT-6.1 Terra at `medium`; the estimates of the
  dialog follow the benchmark; the page asks the user to add OpenAI credits when they run out (report section 9).
- [x] Every AI run moved to GPT-6.1 Terra at `medium`, each run measured once for the dialog's estimates (report
  section 10); approved by the user and merged into `master` (2026-10-30).

# [ ] Phase 6: Documentation and closing

- [ ] Task 6.1 The documentation still stale (the core's `README.md`, the frontend pages, the indexes; the model of
  the runs is now GPT-6.1 Terra at `medium`, Phase 5 report section 10).
- [ ] Task 6.2 `04-context.md`: a section for 04-3.
- [ ] Task 6.3 The final checks; the open points.
