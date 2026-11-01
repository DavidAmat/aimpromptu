# 05: The documentation refresh: plan

The status of every task is in [`05-checklist.md`](05-checklist.md). Each phase writes
`05-implementation-phase-N.md` beside this file. The rules of the documentation are in
[`../../00-documentation-instructions.md`](../../00-documentation-instructions.md); how to report is in
[`../../guidelines/guidelines-communication-with-user.md`](../../guidelines/guidelines-communication-with-user.md).

**For the agent of a phase: read sections 1 to 5, then only your phase in section 6.**

# 1. Context

The user's request (2026-11-01, Phase 5 of [04-5](../04-app-enhancements/04-5-plan.md)): bring every page of
`context/` and `documentation/services/` up to date with the app as it is now, in small phases, each one done by a
small AI model in one session. One phase is about one feature or one flow of the app. The big flows (the sheet, the
AI) are cut into several phases.

The last broad update of the documentation was implementation 03, Phase 10 (2026-10-27) and implementation 04,
Phase 5 (2026-10-28). Since then:

- **04-3** (2026-10-29 to 31): folders, the pills and the metadata of projects; frame marks on the sheet and frames in
  the range toolbox; the levels (the level copy, the catalog of patterns, the level run with its plan and batches);
  every AI run on GPT-6.1 Terra at `medium` (no longer Sonnet 5.5). Its documentation phase (04-3 Phase 6) never ran.
- **04-5** (2026-10-31): Strict and Suggested patterns, the rules and the explanations of a run, the first batch
  first, writing a batch again, the history of AI runs, the chords of a guitar guide ("Chords of the song"), a new
  left easy 1 (the other left easy patterns one number up).
- **04-4** is only a brief ("Copy this style"); it was not built. Do not document it as a feature.

What the survey of 2026-11-01 found (the phases confirm each point):

| Sign | Where |
|---|---|
| No `context/` page tells the AI features (Enhance with AI, Simplify, levels, patterns, the run history). They are told only in the implementation files and in the core README (`aitu-backend/src/aitu_backend/sheet/README.md`), section by implementation phase | Phases 9 to 13 |
| Nothing in `documentation/` tells how the backend draws the sheet (`sheet/engrave`, about 5,700 lines) | Phase 3 |
| `annotations-notes.md`, `annotations-stretches.md`, `annotations-sheet.md` describe the **old** sheet's toolboxes (a record). The new toolboxes are told only in `annotations.md` (276 lines, over the limit of about 200) | Phases 5 to 7 |
| `endpoints.md` has no `/llm/runs`, `/chords`, `/take-out` (to confirm); `components.md` has no `PatternCatalog`, `AiRunDetail`, `AiHistoryPanel` | every phase, for its own routes and components |
| Pages name Sonnet 5.5 as the model of the runs | Phase 9 (and every phase that finds it) |
| `projects.md` is 314 lines (over the limit) and has no folders or metadata | Phase 14 |
| The Lab (the video reader) seems to have no `context/` page | Phase 19 |

# 2. Decisions

Chosen by the orchestrator as defaults and accepted by the user (2026-11-01).

| Point | Decision |
|---|---|
| Where | This folder, `context/implementations/05-documentation-refresh/` |
| Branch | `feat/05-docs-refresh`, made from `master` after 04-5 was merged into it (2026-11-01). One commit per phase and per join, all on this branch (no other branch, no worktree). Merged into `master` at the user's ok |
| What a phase may change | Documentation only (`*.md`, plus `scripts/docs/` in Phase 1). **Never** a file under `aitu-backend/src`, `aitu-frontend/src`, `tests/` or any other code. A page that cannot be made true without a code change is reported, not patched around |
| The old sheet's pages | Moved to `context/archive/old-sheet-tools/` (history), by the phase that writes the new page in their place |
| The order | In **waves** (section 4.4): the phases of a wave run at the same time, each in its own session, on the same branch and working tree; a short **join** after each wave applies the edits of the shared files. Added at the user's ask, 2026-11-01 |
| What a phase says to the user | Only the HAND OFF (section 4.2, step 11). A short decision only when one is critical. Everything else goes into the phase's report file. The user's ask, 2026-11-01 |
| The model of the workers | A small model. Each phase is sized for it: about 3,000 to 8,000 lines of code read in parts, and at most about 8 doc files changed |

# 3. The shape of the documentation after the refresh

The pages to create, and the phase that creates each one. A phase may choose a better name; it says so in its report
and in the checklist.

| New page | What it tells | Phase |
|---|---|---|
| `documentation/services/backend/sheet-f1.md` | The files of a part (`notes.pmn`, `sheet.f1` and its record line), how the sheet is made from the notes (figures, beams, decoration notes, spelling, clefs and octave lines), the sheet laid again when drawn | 2 |
| `documentation/services/backend/sheet-drawing.md` | How the backend draws the sheet (`sheet/engrave`): the layout, the lines, the spacing, the glyphs, the lyrics, the frame marks, the SVG and the pages | 3 |
| `context/frontend/sheet-page.md` | The Sheet step's page: the header and `sheetButtons`, the floating toolbox, the zoom, the cursor and the recording, the frame marks, the AI mark, the roles | 4 |
| `context/ai/README.md` | The AI in the app: the kinds of run, the model and the cost, the AI mark, the pages of this folder | 9 |
| `context/ai/whole-run.md` | **Enhance it again with AI** / **Write it all again**: the windows, the prompt, the check, Stop and Revert | 9 |
| `documentation/services/backend/ai-runs.md` | The code of the AI runs: the jobs, the model client, the prompts and their versions, the costs, the routes | 9, 10 |
| `context/ai/stretch-and-simplify.md` | A stretch (both hands or one) and **Simplify** | 10 |
| `context/ai/levels.md` | The level copy, the catalog of patterns, the chords of the song | 11 |
| `documentation/services/backend/ai-levels.md` | The code of the levels: the catalog, the grid and the chords, the level run, the check, the log | 11, 12, 13 |
| `context/ai/level-run.md` | A level run: the plan, the rules, the batches, the check, Strict and Suggested, the explanations | 12 |
| `context/ai/run-history.md` | The history of AI runs: the log, the first batch first, an answer to the AI, a batch written again, Go on | 13 |
| `context/frontend/folders-and-metadata.md` | Folders, the pills (Folders, All, Filter), the metadata and the info button | 14 |
| `context/frontend/lab.md` | The Lab: the video reader's pages (only if no page tells it) | 19 |

The three `annotations-*` pages keep their names, but now tell the **new** toolboxes (Phases 5, 6, 7), and
`annotations.md` becomes the short hub of the Sheet step's tools (Phase 5).

# 4. How every phase works

## 4.1 Read first

1. This plan, sections 1 to 5, and your phase in section 6.
2. [`05-checklist.md`](05-checklist.md), and `05-inventory.md` (from Phase 1): the rows of your
   files.
3. [`../../00-documentation-instructions.md`](../../00-documentation-instructions.md): the two folders, the limits, the
   cross-links.
4. In the reports of the phases before, only what is left for you: `grep -n "Phase N\b" 05-implementation-*.md` (N your
   phase), and read those lines.

Do not read other phases' code. Do not read `communication-style.md` in full: section 4.3 below has its rules.

## 4.2 Steps

1. **What changed.** For each doc you own: `git log -1 --format=%cs -- <doc>`, then
   `git log --since=<that date> --oneline -- <the code paths of your phase>`. Read the implementation records your
   phase names (only the sections named).
2. **The docs.** Read the docs you own. List what each says about code, routes, fields, labels and behaviour.
3. **The code.** Start from the entry points your phase names. For a file over 400 lines, first list its functions
   (`grep -nE "^(def|class|async def) |^export |^function " <file>`), then read only the parts you need. Never read a
   file over 800 lines in full.
4. **The names.** Run `python3 scripts/docs/check-names.py <doc>` (Phase 1 writes it): it lists the names in
   backticks that the code no longer has.
5. **Write.** Fix what is false; add what is new; remove what describes code that is gone (move it to
   `context/archive/` if it is history worth keeping, or to `documentation/deprecated/` with a banner if it is a
   removed feature). `context/` pages: what it is and how it flows, at most about 200 lines. `documentation/`: the
   exact files, functions, fields, constants and routes. Cross-link both ways (`Where to look deeper` at the end of a
   `context/` page; `> Context:` at the top of a `documentation/` page). Add each new file to `context/00-index.md`
   (and a `documentation/` file also to `documentation/services/README.md`).
6. **Files you may write.** Other agents work in the same folder at the same time, so you write only:
   - the files your phase owns **in your wave** (section 4.4, table "The owner in each wave", then section 7);
   - the new files your phase creates;
   - your own lines of `05-checklist.md` and `05-inventory.md` (read the file just before you edit it; another agent
     may have changed it).

   Every other change (`endpoints.md`, `components.md`, `00-index.md`, `documentation/services/README.md`, a file
   another phase owns in your wave) goes into your report, section **Pending edits for shared files**: for each one,
   the file, where (the heading or the line to find), and the exact text to add or the exact change. The join of
   your wave applies them. Keep the order and the style of the target file in the text you write.
7. **Check.** `python3 scripts/docs/check-links.py`: no broken link in your files. A broken link in a file you do not
   write is not yours (another agent may be in the middle of its work): write it in the report, do not fix it.
   `check-names.py` on every file you touched lists no missing name, or the report explains each one.
8. **Report.** `05-implementation-phase-N.md`, at most about 80 lines, with these sections: Docs changed (one line
   each: what and why); What was stale; Code and docs that disagree in a way that looks like a bug (for the user);
   New terms for the glossary (for Phase 20); Not checked; Pending edits for shared files; Left for later phases
   (name the phase: "Phase 12: ...").
9. **Status.** Tick your tasks in the checklist, mark the phase `[x]` and put the link to your report on the
   phase's line; set the State of your files in the inventory (`true`, `updated`,
   `rewritten`, `new`, `archived`).
10. **Commit** on `feat/05-docs-refresh`, only your own files, named one by one:
    `git add <your files> && git commit -m "Docs 05, Phase N: <title>" -- <your files>`.
    Never `git add -A`, `git add .`, `git commit -a`, `git stash`, `git checkout`, `git switch`, `git reset` or
    `git rebase`: other agents share the working tree. If git says `index.lock` exists, wait a few seconds and try
    again. Do not merge, do not push.
11. **Your only output.** When the phase ends, your last message to the user is **only the HAND OFF**: no summary,
    no walkthrough, no list of changes (they are in the report). The HAND OFF is for a new agent in a new session
    that knows nothing yet; the plan and the checklist are enough for it.

    - When your wave has other phases not yet `[x]` in the checklist, or when you are the last one, the next step is
      the join of your wave. Your output is:

      ```text
      After Phases <the phases of your wave still open, or "none">:
      Read @context/implementations/05-documentation-refresh/05-plan.md and @context/implementations/05-documentation-refresh/05-checklist.md. Start working on the join of wave <W>.
      ```

    - The **join** ends with the hand offs of every phase of the next wave, one line each, to start at the same time
      in separate sessions:

      ```text
      Wave <W+1>: start these in parallel, each in its own session:
      Read @context/implementations/05-documentation-refresh/05-plan.md and @context/implementations/05-documentation-refresh/05-checklist.md. Start working on Phase <a>.
      Read @context/implementations/05-documentation-refresh/05-plan.md and @context/implementations/05-documentation-refresh/05-checklist.md. Start working on Phase <b>.
      ```

    - **A critical decision** (the docs cannot be made true without a choice of the user): instead of the HAND OFF,
      at most five lines: one line of context, the options (the recommended one first), one line each. The HAND OFF
      comes after the user answers. Anything else for the user (a doc that disagrees with the code, a point not
      checked) is not critical: it goes in the report only.

    This rule replaces the walkthrough of the communication guidelines for this plan.

## 4.3 How to write

- Plain, simple English. Short sentences. The simplest verb; no phrasal verbs.
- The app's terms, never a synonym: project, part, step (Source, Audio, Notes, Sheet), the sheet, frame, column,
  stretch, the note toolbox, the range toolbox, the sheet toolbox, the floating toolbox, the header,
  **Enhance with AI**, the AI, batch, the plan, rule, level (easy, medium, hard), pattern, **Strict**, **Suggested**,
  the record, My library, the Personal Vault, Public Library. The glossary is in
  [`../../app/01-app-context.md`](../../app/01-app-context.md).
- A page about the app says "the AI", never the model's name, except where it tells which model the code calls.
- Labels of the page are copied exactly from the code, in bold: **Write this batch again**.
- Spanish note names and figures stay Spanish (Do, Re, Fa#, blanca, negra, corchea); music terms stay English (onset,
  beam, tie, grand staff).
- Do not copy code. Name the file and the function: `part_sheet/runs.py`, `listing`.
- Never copy a value from `.env` (keys). Names of settings only.
- When you could not check a point, write it in the report under "Not checked". Do not guess.

## 4.4 Waves and parallel phases

Phases of one wave own different files, so they run at the same time. Before a phase starts, every phase of the
waves before it and their joins are done. A wave's order follows what a phase needs: Phase 10 adds to the page that
Phase 9 creates, Phase 15 and 16 change parts of the `projects.md` that Phase 14 splits, Phase 8 adds to the page of
Phase 4, Phases 12 and 13 add to the page of Phase 11.

| Wave | Phases (in parallel) | Then |
|---|---|---|
| 0 | 1 (done) | none |
| A | 2, 5, 9, 14, 18, 19 | join A |
| B | 3, 6, 10, 11, 15 | join B |
| C | 4, 7, 12, 16, 17 | join C |
| D | 8, 13 | join D |
| E | 20 (alone: it writes any file directly, the shared ones too; its only output is one line: the refresh is ready for the user's review and the merge) | none |

**The owner in each wave** of the files that several phases change (section 7 has the rest). A phase not named here
for a file sends its change as a pending edit (section 4.2, step 6).

| File | A | B | C | D |
|---|---|---|---|---|
| the core README `sheet/README.md` | 2 | 3 | none | none |
| `context/backend/editing.md` | 5 | 6 | 17 | none |
| `context/frontend/projects.md` | 14 | 15 | 16 | none |
| `context/frontend/rendering.md` | none | 3 | 4 | none |
| `context/frontend/annotations.md` (the hub) | 5 | none | none | none |
| `context/frontend/playlists.md` | 18 | none | 17 | none |
| `context/frontend/sheet-page.md` | none | none | 4 | 8 |
| `context/07-database.md` | 14 | 11 | none | none |
| `context/02-tech-stack.md` | 9 | none | none | none |
| `context/music-library/private-library.md` | 18 | none | none | none |
| `context/ai/README.md` | 9 | none | none | none |
| `documentation/services/backend/paths-and-data.md` | 14 | 11 | none | 13 |
| `documentation/services/backend/editing-and-compose.md` | none | 6 | 17 | none |
| `documentation/services/backend/ai-runs.md` | 9 | 10 | none | none |
| `documentation/services/backend/ai-levels.md` | none | 11 | 12 | 13 |
| `endpoints.md`, `components.md`, `00-index.md`, `documentation/services/README.md` | the join | the join | the join | the join |

**A join** (one agent, a small model):

1. Check that every phase of the wave is `[x]` in the checklist. If one is not, stop; your output is one line: the
   phases still open.
2. Read the section **Pending edits for shared files** of each report of the wave. Apply each edit to its file, in the
   order of the phases. Two edits in the same place: keep both, in the file's style.
3. `check-links.py` passes on the whole repo, now with no exception; `check-names.py` on each file you changed.
4. Write `05-implementation-join-<W>.md` (at most about 30 lines: the edits applied, any edit you could not apply and
   why). Tick the join in the checklist; set the line **Next:** to the next wave.
5. Commit: `Docs 05, join <W>`, your files named one by one (step 10 of section 4.2).
6. Your only output: the HAND OFF of the next wave (section 4.2, step 11).

# 5. Binding rules

- Documentation only (section 2). No change to the app's code, its tests or its data.
- No actions in the app: do not start it, click in it, run the AI or run the tests. The workers read the code and git.
- Do not change the implementation folders, except where a phase says so (Phase 13: `04-context.md`; Phase 20: the
  journals and the checklists of 04-3 and 04-5).
- `check-links.py` passes at the end of every phase.

# 6. Phases

Sizes are lines of code. Paths of the backend are under `aitu-backend/src/aitu_backend/`, of the frontend under
`aitu-frontend/src/`. "History" names the implementation records that tell how a part was built: read only the
sections named, to understand, not to copy.

Each phase below names its wave. When it names a file that another phase owns in that wave (section 4.4), the change
is a pending edit for the join, not an edit of the file.

## Phase 1: The inventory and the name check (wave 0)

- **Write `scripts/docs/check-names.py`.** Input: doc paths (default: every file in scope, below). For each name in
  backticks: a path (has `/` or ends in `.py`, `.ts`, `.tsx`, `.md`, `.json`, `.mjs`) is checked to exist from the
  repo root, from the two code roots, from the doc's folder, or by its file name in `git ls-files`; an identifier
  (`snake_case` with `_`, `CamelCase`, `name()`) is searched with `git grep -w` in `aitu-backend/src`,
  `aitu-frontend/src`, `aitu-backend/tests`, `aitu-frontend/scripts`, `scripts`; a route (`/sheet/{uuid}/llm/runs`,
  `GET /x`) by its last literal part in `aitu-backend/src/aitu_backend/api/`. Skip names with spaces, under 3
  characters, or only numbers. Print `doc:line  kind  name` for each missing one; exit 0. Mention it in
  `00-documentation-instructions.md`, beside the links check.
- **Scope**: `context/*.md`, `context/app/`, `context/backend/`, `context/frontend/`, `context/music/`,
  `context/music-library/`, `context/colors/`, `documentation/README.md`, `documentation/services/`, the core README
  `aitu-backend/src/aitu_backend/sheet/README.md`, `aitu-backend/README.md`, `aitu-frontend/README.md`, `README.md`.
  Out of scope: `context/guidelines/`, `context/language/`, `context/implementations/` (except where a phase says),
  `context/archive/`, `documentation/archive/`, `documentation/deprecated/`, `documentation/issues/`.
- **Write `05-inventory.md`**: one row per file in scope: file, lines, last change (git), the
  owner phase (from section 7), the count of missing names, one line on what it covers, State `to check`. Then a
  short section: what changed in the code since 2026-10-28 (`git log --since=2026-10-28 --stat`), summed per folder.
- Change no other doc. Size: no code to read.

## Phase 2: How a sheet is made (the notes to `sheet.f1`) (wave A)

- **Docs**: create `documentation/services/backend/sheet-f1.md`; update `documentation/services/backend/time-matrix.md`,
  `rhythm-and-annotations.md`, `context/backend/time-model.md`; the core README sections 1 to 9, 12, 16 and 17 (fix
  what is false, or replace a long outdated section by a link to the new page).
- **Code** (about 5,000): `sheet/proposal/` (`pipeline.py`, `frames.py`: `find_graces`, `lengthen_lone`; `beat.py`,
  `meter.py`, `rules.py`, `theory.py`); `sheet/sheet/` (`f1.py`, `data.py`, `frames.py`, `spelling.py`,
  `figures.py`); `part_sheet/build.py` (`_compute`, `reapply`, `mark_settled`); `part_sheet/store.py` (`Record`, the
  files of a part); `part_sheet/legacy.py` (the marks of the old sheets).
- **History**: [`03-context.md`](../03-apply-poc-research/03-context.md) section 3; 03 Phase 2 and Phase 9 reports;
  [`04-context.md`](../04-app-enhancements/04-context.md) sections 2 and 3.1.

## Phase 3: How the sheet is drawn (the backend) (wave B)

- **Docs**: create `documentation/services/backend/sheet-drawing.md`; update `context/frontend/rendering.md` (the
  backend half), the core README sections 10 and 15 (the drawing part).
- **Code** (about 5,900): `sheet/engrave/` (`layout.py` 2,649 and `vrv.py` 1,196 by function list; `frames.py`,
  `glyphs.py`, `svg.py`, `spacing.py` with `spacing_model.json`, `cursor.py`, `lyric_text.py` with
  `lyric_fonts.json`); `api/sheet.py`: `GET /{audio_uuid}` and `GET /{audio_uuid}/pages`.
- **History**: 03 Phase 3 and Phase 8 reports; [04-3 Phase 2b](../04-app-enhancements/04-3-implementation-phase-2b.md)
  (the frame marks).

## Phase 4: The sheet page (the frontend shell) (wave C)

- **Docs**: create `context/frontend/sheet-page.md`; update `context/frontend/rendering.md` (the frontend half),
  `context/frontend/projects.md` (its Sheet step section becomes a short summary with a link), `timestamps.md`
  (check), `components.md` (the page, the view, the hooks of `pages/piece/sheet/frames/`).
- **Code** (about 4,800, read in parts): `pages/piece/sheet/frames/FramesSheetPage.tsx` (1,645: its first comment,
  then the header, `sheetButtons`, the zoom, the recording), `FramesSheetView.tsx` (1,373: the cursor, the drag, the
  veil, the selection, the frame marks), `useFramesSheet.ts`, `geometry.ts`, `navigation.ts`;
  `pages/piece/SheetTab.tsx`, `pages/piece/sheet/SheetPage.tsx` (say if it is still used),
  `toolboxPlacement.ts`, `sheetConstants.ts`; `ui/FloatingBar.tsx`; `components/piece/AiMark.tsx`;
  `components/time/ScorePlayer.tsx`; `hooks/usePlayedNotes.ts`.
- **History**: [04 Phase 1](../04-app-enhancements/04-implementation-phase-1.md); 03 Phase 5 report;
  [`04-context.md`](../04-app-enhancements/04-context.md) section 3.3.

## Phase 5: The note toolbox (wave A)

- **Docs**: `context/frontend/annotations.md` becomes the hub of the Sheet step's tools (at most about 200 lines: one
  short section per toolbox, links); move `context/frontend/annotations-notes.md` to
  `context/archive/old-sheet-tools/` and write a new `annotations-notes.md` for the new note toolbox; update
  `context/backend/editing.md` (if it tells these edits), `endpoints.md` (the routes below), `components.md`.
- **Code** (about 3,500): `pages/piece/sheet/frames/FramesNoteToolbox.tsx` (the rows: figures, **Finger**,
  **Alteration**, **Hand**, **Beam**, **Grace**, **Duplicate**, **Unite**, **Marks**, take off the page; the buttons
  Enhance, Copy, Select), `readingTools.ts`, `pages/piece/sheet/PianoToolboxes.tsx` (the Piano toolbox);
  `api/sheet.py`: `/hands`, `/reading`, `/duplicate`, `/unite`, `/take-out`, `/remove`; `part_sheet/edits.py`
  (1,285: the function of each tool), `part_sheet/reading.py` (822, by function list), `editing/marks.py`.
- **History**: 03 Phases 6 and 7 reports; [04-3 Phase 2b](../04-app-enhancements/04-3-implementation-phase-2b.md)
  (decoration notes lit at their onset).

## Phase 6: The range toolbox, copy and paste (wave B)

- **Docs**: move `annotations-stretches.md` to `context/archive/old-sheet-tools/` and write a new one for the range
  toolbox; update `context/backend/editing.md` (Paste), `documentation/services/backend/editing-and-compose.md` (the
  splice), `endpoints.md`, `components.md`.
- **Code** (about 2,600): `pages/piece/sheet/frames/FramesRangeToolbox.tsx` (**Which staff** Both / Right / Left;
  the tabs Key, Clef, Octave; **Record this passage**, **Start a new part here**, Delete, Copy, Enhance, Select),
  `FrameRangeFields.tsx` (frames typed in), the copy and paste in `FramesSheetPage.tsx` (search
  `usePassageClipboard`, `pastePassage`); `api/sheet.py`: `/paste`, `/add`, `/remove`, `GET /stretch`;
  `editing/paste.py` (889, by function list), `part_sheet/lengths.py`, `editing/audio_splice.py`.
- **History**: 03 Phase 7 report; [04-3 Phase 2b](../04-app-enhancements/04-3-implementation-phase-2b.md) (frames
  in the range toolbox).

## Phase 7: The sheet toolbox: Info, Key, Transpose, Lyrics, View (wave C)

- **Docs**: move `annotations-sheet.md` to `context/archive/old-sheet-tools/` and write a new one for the sheet
  toolbox (its five tabs, the lyrics); `endpoints.md` (`/transpose`, `/words`), `components.md`.
- **Code** (about 2,300): `pages/piece/sheet/frames/FramesSheetToolbox.tsx`, `pages/piece/sheet/TransposeTab.tsx`,
  `LyricsTab.tsx`, `lyricsPieces.ts`, `frames/FramesLyricsToolbox.tsx`, `frames/useFramesLyrics.ts`,
  `frames/lyricsText.ts`; `api/sheet.py`: `/transpose`, `GET` and `PUT /words`; where the words are stored
  (`grep -rn "words" part_sheet/ storage/paths.py`).
- **History**: 03 Phase 8 report.

## Phase 8: Undo, redo, the preview and the PDF (wave D)

- **Docs**: `context/frontend/printing.md`, `documentation/services/frontend/score-pdf.md`; a short section "Undo and
  redo" in `context/frontend/sheet-page.md` (made in Phase 4); `endpoints.md` (`/undo`, `/redo`),
  `paths-and-data.md` (the history of a part, if it tells it).
- **Code** (about 2,200): `hooks/useEditHistory.ts`; `api/sheet.py`: `/undo`, `/redo`; `editing/history.py`; the
  snapshots in `part_sheet/store.py`; `pages/piece/sheet/frames/FramesPdfDialog.tsx`, `FramesPreviewDialog.tsx`;
  `print/drawPage.ts` (by function list), `print/pdf.ts`, `print/scorePdf.ts`.
- **History**: 03 Phase 6 (undo) and Phase 8 (paper) reports.

## Phase 9: The AI, part 1: the AI on the sheet, the whole run (wave A)

- **Docs**: create `context/ai/README.md`, `context/ai/whole-run.md`, `documentation/services/backend/ai-runs.md`;
  update `context/02-tech-stack.md` (the AI client and the model: GPT-6.1 Terra at `medium`; the names of the
  settings, never their values), the core README sections 5 and 11 (fix, or a link to the new pages),
  `endpoints.md` (`/llm`, `/llm/stop`, `/llm/revert`, `/llm/costs`, `/llm/batches`), `components.md`
  (`AiRunPanel`, `AiMark`).
- **Code** (about 4,800, read in parts): `sheet/llm/frames.py` (2,186, by function list: `write_frames`,
  `window_prompt`, `check_answer`, `places`, `declared`), `windows.py`, `chain.py`, `guards.py`, `prompts.py`,
  `song.py`; `sheet/llm/prompt/frames/` and its `VERSION`; the model client (`grep -rln "openai\|anthropic" .`);
  `part_sheet/job.py` (1,264, by function list: the live run, start, stop, revert, commit, `costs`);
  `pages/piece/sheet/frames/AiRunPanel.tsx`; the veil and the reveal in `FramesSheetView.tsx` (search `veil`).
- **History**: 03 Phase 4 report; [04 Phase 3](../04-app-enhancements/04-implementation-phase-3.md);
  [04-3 Phase 5](../04-app-enhancements/04-3-implementation-phase-5.md) (the models, section 10);
  [`04-context.md`](../04-app-enhancements/04-context.md) sections 2 and 3.2.

## Phase 10: The AI, part 2: a stretch, Simplify, the Enhance with AI dialog (wave B)

- **Docs**: create `context/ai/stretch-and-simplify.md`; add sections to `ai-runs.md`; the core README section 14;
  `endpoints.md` (`/llm/stretch`, `/llm/simplify`), `components.md` (`EnhanceDialog`, its tabs).
- **Code** (about 3,000): `pages/piece/sheet/frames/EnhanceDialog.tsx` (628: the tabs **A stretch** and **The whole
  song**; leave the levels part to Phase 11); in `sheet/llm/frames.py`: `write_stretch`, `stretch_request`, `splice`,
  `simplify_windows`, `simplify_prompt`, `check_simplify`, `write_simplify`; `part_sheet/job.py`: `start_simplify`;
  `part_sheet/edits.py`: `apply_stretch`, `apply_simplify`; the Enhance buttons of the note and range toolboxes.
- **History**: [04 Phase 4](../04-app-enhancements/04-implementation-phase-4.md);
  [`04-context.md`](../04-app-enhancements/04-context.md) section 2.

## Phase 11: The AI, part 3: levels, the catalog of patterns, the chords of the song (wave B)

- **Docs**: create `context/ai/levels.md` and `documentation/services/backend/ai-levels.md` (the catalog, its
  numbers, the approved set; the grid and the chords; the guide chords); `paths-and-data.md` (the level copy,
  `chords` in `project.json`); `context/07-database.md` (`level_of`); `endpoints.md` (`/levels/catalog`,
  `/llm/level-copy`, `/chords`); `components.md` (`PatternCatalog`, the levels part of `EnhanceDialog`).
- **Code** (about 3,000): `sheet/llm/catalog/patterns.json` and `examples/`; `sheet/levels/` (`grid.py`,
  `harmony.py`, `hands.py`); in `sheet/llm/levels.py`: the catalog loading, `guide_chords`; `level_of` in
  `db/models.py` and `api/projects.py`; `api/sheet.py`: the routes above; `pages/piece/sheet/frames/PatternCatalog.tsx`,
  `patterns.ts`, the levels part of `EnhanceDialog.tsx` (level, hands, patterns, **Suggested | Strict**, "Chords of
  the song"); where `chords` is saved (`grep -rn "chords" storage/ part_sheet/ api/sheet.py`).
- **History**: [`04-3-plan.md`](../04-app-enhancements/04-3-plan.md) sections 5.1, 5.8, 5.10; 04-3 Phases 2 and 4
  reports; [`04-5-plan.md`](../04-app-enhancements/04-5-plan.md) section 5 (the new left easy 1, the guide chords).

## Phase 12: The AI, part 4: the level run (wave C)

- **Docs**: create `context/ai/level-run.md` (the plan and its sections, the rules, the batches, the check and its
  limits per level, Strict and Suggested, the explanations, the cost); add sections to `ai-levels.md` (the
  functions, the constants, the prompt files and the version); `endpoints.md` (`/llm/level`).
- **Code** (about 3,000): `sheet/llm/levels.py` (1,686, by function list: `system_prompt`, `song_summary`,
  `plan_prompt`, `read_plan`, `read_rules`, `batch_prompt`, `read_declared`, `check_level`, `write_level`, `Talk`,
  the constants); `sheet/llm/prompt/levels/` (`shared.md`, `easy.md`, `medium.md`, `hard.md`, `feedback.md`,
  `VERSION`); `part_sheet/job.py`: `start_level`, `_level_work`; `api/sheet.py`: `/llm/level` and `LevelRequest`.
- **History**: 04-3 Phases 3 and 4 reports; [`04-5-plan.md`](../04-app-enhancements/04-5-plan.md) sections 3.1, 3.2;
  [04-5 report](../04-app-enhancements/04-5-implementation-phases-1-to-4.md) sections 2.1 and 4.

## Phase 13: The AI, part 5: the history of AI runs, and `04-context.md` (wave D)

- **Docs**: create `context/ai/run-history.md`; add the log (`ai-runs/<id>.json`) to `ai-levels.md` and
  `paths-and-data.md`; `endpoints.md` (`/llm/runs`, `/llm/runs/{id}`, `continue`, `batches/{k}/again`);
  `components.md` (`AiRunDetail`, `AiHistoryPanel`, the waiting state of `AiRunPanel`). Add to
  [`04-context.md`](../04-app-enhancements/04-context.md) a section for 04-3 and 04-5 (what changed, the decisions
  that bind, where the code is, the open points), linking to the new `context/ai/` pages (04-3 task 6.2).
- **Code** (about 1,500): `part_sheet/runs.py`; `part_sheet/job.py`: `continue_level`, `again_batch`;
  `sheet/llm/levels.py`: `write_again`; `sheet/llm/prompt/levels/answer.md`; `api/sheet.py`: the four routes;
  `pages/piece/sheet/frames/AiRunPanel.tsx`, `AiRunDetail.tsx`, `AiHistoryPanel.tsx`, `batches.ts`; the
  **History of AI runs** button in `sheetButtons`.
- **History**: [`04-5-plan.md`](../04-app-enhancements/04-5-plan.md) sections 3.3 to 3.5;
  [04-5 report](../04-app-enhancements/04-5-implementation-phases-1-to-4.md) sections 2.2, 2.3.

## Phase 14: Projects, folders, metadata, parts, Save to library (wave A)

- **Docs**: split `context/frontend/projects.md` (keep the steps of a project and the editor's gestures; at most about
  200 lines); create `context/frontend/folders-and-metadata.md`; update `context/07-database.md`,
  `paths-and-data.md` (the project bundle), `endpoints.md` (`/projects`, `/folders`, `/metadata`),
  `components.md`; check the Save to library part of `context/music-library/private-library.md`.
- **Code** (about 4,500): `pages/ProjectsPage.tsx`; `components/folders/` (`useFolderTree.tsx`, `InfoDialog.tsx`,
  `FilterBar.tsx`, `ViewPills.tsx`, `listFilter.ts`, `MoveFolderDialog.tsx`); `api/projects.py`, `api/folders.py`,
  `api/metadata.py`; the folder and metadata tables in `db/models.py` (by `grep`); `pages/piece/PiecePage.tsx`,
  `PieceResume.tsx`, `PartsPanel.tsx`, `SaveToLibraryDialog.tsx`; `editing/parts.py`; `storage/bundle.py` (955, by
  function list), `storage/paths.py`.
- **History**: [04-3 Phase 1](../04-app-enhancements/04-3-implementation-phase-1.md);
  [`04-3-plan.md`](../04-app-enhancements/04-3-plan.md) section 4.

## Phase 15: From the audio to the notes: Source, Audio, the transcription (wave B)

- **Docs**: `context/backend/muscriptor.md`, `context/backend/pieces-and-revisions.md`,
  `context/music/transcription-quality.md`, `documentation/services/backend/transcription-pipeline.md`; the Source and
  Audio parts of `projects.md`; `endpoints.md` (`/audio`, `/youtube`, `/pieces` status); `components.md`.
- **Code** (about 6,000, read in parts): `pages/piece/SourceTab.tsx`, `SourceFiles.tsx`, `VideoStep.tsx`,
  `AudioTab.tsx`; `components/audio/` (`CutWaveform.tsx`, `WaveformRangeSelector.tsx`); `api/audio.py`,
  `api/youtube.py`, `api/pieces.py`; `audio/store.py` (by function list); `transcription/pipeline.py` and `engine.py`
  (by function list).
- **History**: start from `git log --since=<the docs' dates>`; the 01-mvp 08 folder only if a doc names it.

## Phase 16: The notes and the hands: the Notes step, the piano roll, the hand split (wave C)

- **Docs**: `context/backend/piano-matrix-notation.md`, `documentation/services/backend/events-to-sheet.md`,
  `hand-inference-second-pass.md`, `context/music/piano_svg/01-piano-svg.md`; check only
  `context/music/notation-logic/02-notation-spec.md`; the Notes part of `projects.md`; `endpoints.md` (`/matrix`, the
  notes routes of `/pieces`); `components.md`.
- **Code** (about 6,000, read in parts): `pages/piece/NotesEditor.tsx`, `NotesTab.tsx`; `components/notes/`
  (`PianoRollCanvas.tsx`, `rollPaint.ts`); `notes/` (`liveFeed.ts`, `rollNotes.ts`, `noteEdits.ts`); `hands/`
  (`infer.py`, `refine.py`, `config.py`, by function list); `pmn/events_file.py`; `matrix/model.py`; `api/matrix.py`.
- **History**: `git log` since the docs' dates.

## Phase 17: Recording in Sheet, passages, Compose and parts (wave C)

- **Docs**: `context/frontend/recording-in-sheet.md`, `context/frontend/playlists.md` (the page "From other projects"
  and the parts of a project), `context/backend/editing.md` (Recording in Sheet), `editing-and-compose.md` (Compose),
  `endpoints.md` (`/passages`, `/projects/compose`, the parts routes), `components.md`.
- **Code** (about 3,500): `pages/piece/passage/PassagePage.tsx` and its folder; `api/passages.py`;
  `editing/passages.py` (864, by function list), `editing/compose.py`, `editing/parts.py`; `pages/compose/ComposePage.tsx`;
  the promotion in `part_sheet/lengths.py`.
- **History**: 03 Phase 8 report (the sheet through a change of a part's length); the core README section 16.

## Phase 18: The libraries, playlists, requests and the Public Library (wave A)

- **Docs**: `context/music-library/*` (8 files), the playlists part of `context/frontend/playlists.md`,
  `endpoints.md` (`/library`, `/public`, `/requests`, `/playlists`, `/shares`), `components.md`.
- **Method**: these pages were written on 2026-10-19 and 10-29. First `git log --since=2026-10-19 --stat` on the code
  below; check what changed, and run `check-names.py` on every page. Read the import code (`library/*_import.py`,
  `popularity.py`, `genres.py`) only where a page names it.
- **Code** (read only what changed or is named): `pages/library/`, `pages/public/`, `pages/requests/`;
  `api/library.py`, `public.py`, `requests.py`, `playlists.py`, `shares.py`; `library/requests.py` (1,876, by
  function list), `library/flow.py`.

## Phase 19: Play mode, the Lab, users and admin, the routes and the shell (wave A)

- **Docs**: `context/frontend/play-mode.md`, `context/frontend/pages.md` (the routes against `App.tsx`),
  `context/08-security.md`; create `context/frontend/lab.md` if no page tells the Lab; `endpoints.md` (`/auth`,
  `/admin`, `/video`, `/frame-examples`), `components.md` (play, video, layout, admin, login).
- **Code** (about 6,000, read in parts): `pages/play/`; `App.tsx`; `layout/` (`AppLayout.tsx`); `pages/video/`,
  `components/video/` (by component list); `api/video.py`, `api/frame_examples.py`; `video/` (by module list only);
  `auth/`, `api/auth.py`, `api/admin.py`; `pages/admin/UsersPage.tsx`, `pages/LoginPage.tsx`, `pages/dev/`.
- **History**: [01-mvp 04 Synthesia to notes](../01-mvp/04-synthesia-to-notes/README.md) README only, for the Lab.

## Phase 20: The platform pages, the READMEs, the indexes, the closing (wave E)

- **Docs**: `context/00-index.md`, `00-project-complete-overview.md`, `00-documentation-instructions.md` (the list of
  areas: add `context/ai/`), `01-project.md`, `02-tech-stack.md`, `02b-local-setup.md` (check), `03-services-overview.md`,
  `04-local-development.md` (the checks: `package.json` scripts, `Makefile` targets), `05-deployment.md`,
  `09-coding-conventions.md`, `app/01-app-context.md` (the glossary: the new terms of the phase reports),
  `context/backend/README.md`, `context/backend/api.md` (the routers of `api/__init__.py`), `context/frontend/README.md`,
  `colors/color-palette.md` (against `ui/palette.ts`), `documentation/README.md`, `documentation/services/README.md`,
  `aitu-backend/README.md`, `aitu-frontend/README.md`, `README.md`; at the top of the core README, a map of its
  sections and the pages that now tell each part.
- **Closing**: the journal of `context/implementations/README.md` and `00-index.md` (04-3, 04-5, 05); the checklists:
  04-3 Phase 6 and 04-5 task 5.2 closed with a link here; every row of the inventory has a final State;
  `check-names.py` on the whole scope; the links check.
- **Code**: `compose.yaml`, `Makefile`, `aitu-frontend/package.json`, `aitu-backend/pyproject.toml`,
  `api/__init__.py`, `ui/palette.ts`.

# 7. The owner of every page

One owner per file; another phase may add its own section (named in section 6). A file in scope not in this table
belongs to Phase 20.

| File | Owner |
|---|---|
| `context/00-*.md`, `01`, `02b`, `03`, `04`, `05`, `09`, `app/01-app-context.md`, `backend/README.md`, `backend/api.md`, `frontend/README.md`, `colors/color-palette.md`, `documentation/README.md`, `documentation/services/README.md`, the three service READMEs | 20 |
| `context/02-tech-stack.md` | 9 (the AI), then 20 |
| `context/07-database.md` | 14 (11 adds `level_of`) |
| `context/08-security.md` | 19 |
| `context/backend/time-model.md` | 2 |
| `context/backend/editing.md` | 6 (17 adds Recording in Sheet, 5 the note edits) |
| `context/backend/muscriptor.md`, `pieces-and-revisions.md` | 15 |
| `context/backend/piano-matrix-notation.md` | 16 |
| `context/frontend/rendering.md` | 3 (backend half), 4 (frontend half) |
| `context/frontend/sheet-page.md` (new) | 4 (8 adds undo) |
| `context/frontend/annotations.md`, `annotations-notes.md` | 5 |
| `context/frontend/annotations-stretches.md` | 6 |
| `context/frontend/annotations-sheet.md` | 7 |
| `context/frontend/printing.md` | 8 |
| `context/frontend/timestamps.md` | 4 |
| `context/frontend/projects.md` | 14 (4, 15, 16 adjust their step's part) |
| `context/frontend/folders-and-metadata.md` (new) | 14 |
| `context/frontend/recording-in-sheet.md` | 17 |
| `context/frontend/playlists.md` | 17 (18 the playlists part) |
| `context/frontend/play-mode.md`, `pages.md`, `lab.md` (new) | 19 |
| `context/ai/*` (new) | 9 to 13 |
| `context/music/transcription-quality.md` | 15 |
| `context/music/notation-logic/02-notation-spec.md`, `music/piano_svg/01-piano-svg.md` | 16 |
| `context/music-library/*` | 18 |
| `documentation/services/backend/endpoints.md`, `documentation/services/frontend/components.md` | shared: every phase its own sections; 20 checks the whole |
| `backend/sheet-f1.md` (new), `time-matrix.md`, `rhythm-and-annotations.md` | 2 |
| `backend/sheet-drawing.md` (new) | 3 |
| `backend/editing-and-compose.md` | 6 (17 the Compose part) |
| `backend/ai-runs.md` (new) | 9 (10 adds) |
| `backend/ai-levels.md` (new) | 11 (12, 13 add) |
| `backend/paths-and-data.md` | 14 (8, 11, 13 add their parts) |
| `backend/transcription-pipeline.md` | 15 |
| `backend/events-to-sheet.md`, `hand-inference-second-pass.md` | 16 |
| `frontend/score-pdf.md` | 8 |
| The core README `sheet/README.md` | 2, 3, 9, 10 their sections; 20 the map at its top |

# 8. Changes made by the phases

Each phase adds a dated paragraph here when it changes this plan (a new page name, a split, a point moved to another
phase).

**Waves and the only output** (the user, 2026-11-01, after Phase 1). The phases run in waves of parallel phases
(section 4.4), with a join after each wave for the shared files. At the end of a phase, the only output to the user is
the HAND OFF, or a very short critical decision (section 4.2, step 11). Phase 1 had already ended with a long
walkthrough; its report is unchanged.
