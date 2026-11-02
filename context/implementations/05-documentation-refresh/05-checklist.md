# 05: The documentation refresh: checklist

The plan is [`05-plan.md`](05-plan.md). Branch `feat/05-docs-refresh`. Status letters: `[x]` complete, `[p]` in
progress, `[b]` blocked, `[c]` cancelled, `[ ]` not started.

**Done (2026-11-02).** Every phase and join is complete; the branch is merged into `master`.

The waves are in the plan, section 4.4: A (2, 5, 9, 14, 18, 19), B (3, 6, 10, 11, 15), C (4, 7, 12, 16, 17),
D (8, 13), then 20 alone. After each wave, a join applies the pending edits of the shared files.

Each phase, when done: its tasks `[x]`, the phase `[x]`, and the link to its report after the title, as
`Report: [05-implementation-phase-N.md](05-implementation-phase-N.md)`. Each phase changes only its own lines here.

## Decisions

- [x] The waves, the joins and the HAND OFF as the only output of a phase (the user, 2026-11-01, after Phase 1).
- [x] The defaults of plan section 2 (the folder, the branch, the old sheet's pages to the archive, one phase at a
  time): the user's ok (2026-11-01). 04-5 merged into `master` first; `feat/05-docs-refresh` made from `master`.

# [x] Phase 1: The inventory and the name check

Report: [05-implementation-phase-1.md](05-implementation-phase-1.md)

- [x] 1.1 `scripts/docs/check-names.py`; a line about it in `00-documentation-instructions.md`.
- [x] 1.2 `05-inventory.md`: every file in scope, its owner, its missing names, State `to check`.
- [x] 1.3 The code changed since 2026-10-28, per folder.

# [x] Phase 2: How a sheet is made (the notes to `sheet.f1`) (wave A)

Report: [05-implementation-phase-2.md](05-implementation-phase-2.md)

- [x] 2.1 New `documentation/services/backend/sheet-f1.md`.
- [x] 2.2 `time-matrix.md`, `rhythm-and-annotations.md`, `context/backend/time-model.md`.
- [x] 2.3 The core README sections 1 to 9, 12, 16, 17.

# [x] Phase 3: How the sheet is drawn (the backend) (wave B)

Report: [05-implementation-phase-3.md](05-implementation-phase-3.md)

- [x] 3.1 New `documentation/services/backend/sheet-drawing.md`.
- [x] 3.2 `context/frontend/rendering.md` (the backend half); the core README sections 10 and 15.

# [x] Phase 4: The sheet page (the frontend shell) (wave C)

Report: [05-implementation-phase-4.md](05-implementation-phase-4.md)

- [x] 4.1 New `context/frontend/sheet-page.md`.
- [x] 4.2 `rendering.md` (the frontend half), `timestamps.md` done; the Sheet step in `projects.md`: pending edit E4.1 for the join of wave C.
- [x] 4.3 `components.md`: the page, the view, the hooks: pending edits E4.2 and E4.3 for the join of wave C (the table already names the page, the view and the hooks).

# [x] Phase 5: The note toolbox (wave A)

Report: [05-implementation-phase-5.md](05-implementation-phase-5.md)

- [x] 5.1 `annotations.md` as the hub of the tools (about 200 lines at most).
- [x] 5.2 The old `annotations-notes.md` to `context/archive/old-sheet-tools/`; a new one for the note toolbox.
- [x] 5.3 `editing.md` (the note edits) done; `endpoints.md` and `components.md` by the join of wave A (pending edits in the report).

# [x] Phase 6: The range toolbox, copy and paste (wave B)

Report: [05-implementation-phase-6.md](05-implementation-phase-6.md)

- [x] 6.1 The old `annotations-stretches.md` to the archive; a new one for the range toolbox.
- [x] 6.2 `editing.md` (Paste, Delete these frames) and `editing-and-compose.md` done; `endpoints.md`, `components.md`, the hub `annotations.md` and `00-index.md`: pending edits for the join of wave B (the report, section Pending edits).

# [x] Phase 7: The sheet toolbox: Info, Key, Transpose, Lyrics, View (wave C)

Report: [05-implementation-phase-7.md](05-implementation-phase-7.md)

- [x] 7.1 The old `annotations-sheet.md` to the archive; a new one for the sheet toolbox and the lyrics.
- [x] 7.2 `endpoints.md` (`/transpose`, `/words`) and `components.md` checked, no change needed; the hub `annotations.md` and `00-index.md`: pending edits E7.1 and E7.2 for the join of wave C.

# [x] Phase 8: Undo, redo, the preview and the PDF (wave D)

Report: [05-implementation-phase-8.md](05-implementation-phase-8.md)

- [x] 8.1 `printing.md`, `score-pdf.md`.
- [x] 8.2 Undo and redo in `sheet-page.md` done; `endpoints.md` checked, no change; `paths-and-data.md`: pending edits E8.1 to E8.3 for the join of wave D.

# [x] Phase 9: The AI, part 1: the AI on the sheet, the whole run (wave A)

Report: [05-implementation-phase-9.md](05-implementation-phase-9.md)

- [x] 9.1 New `context/ai/README.md` and `context/ai/whole-run.md`.
- [x] 9.2 New `documentation/services/backend/ai-runs.md`.
- [x] 9.3 `02-tech-stack.md` (the AI client, the model) done. The core README sections 5 and 11, `endpoints.md`,
  `components.md`: pending edits for the join of wave A (the core README is Phase 2's file in wave A).

# [x] Phase 10: The AI, part 2: a stretch, Simplify, the Enhance with AI dialog (wave B)

Report: [05-implementation-phase-10.md](05-implementation-phase-10.md)

- [x] 10.1 New `context/ai/stretch-and-simplify.md`; sections 7 (a stretch) and 8 (Simplify) in `ai-runs.md`.
- [x] 10.2 The core README section 14; `endpoints.md`, `components.md`: pending edits for the join of wave B (the core
  README and `endpoints.md` are shared files; `components.md` needs no change).

# [x] Phase 11: The AI, part 3: levels, the catalog of patterns, the chords of the song (wave B)

Report: [05-implementation-phase-11.md](05-implementation-phase-11.md)

- [x] 11.1 New `context/ai/levels.md` and `documentation/services/backend/ai-levels.md`.
- [x] 11.2 `paths-and-data.md` (`levelOf`, `parts[].chords`) and `07-database.md` (checked: `level_of` already right); `endpoints.md` (`GET /sheet/{uuid}/chords`) and `components.md` (`PatternGallery`, `patterns.ts`) by pending edits for the join of wave B.

# [x] Phase 12: The AI, part 4: the level run (wave C)

Report: [05-implementation-phase-12.md](05-implementation-phase-12.md)

- [x] 12.1 New `context/ai/level-run.md`.
- [x] 12.2 Sections in `ai-levels.md` done; `endpoints.md`: pending edit E12.1 for the join of wave C (the report).

# [x] Phase 13: The AI, part 5: the history of AI runs, and `04-context.md` (wave D)

Report: [05-implementation-phase-13.md](05-implementation-phase-13.md)

- [x] 13.1 New `context/ai/run-history.md`; the log in `ai-levels.md` (section 9) and `paths-and-data.md`.
- [x] 13.2 `endpoints.md` (four rows), `components.md` (two rows, one changed), `00-index.md`, `context/ai/README.md`, `level-run.md`, `documentation/services/README.md`: pending edits E13.1 to E13.8 for the join of wave D.
- [x] 13.3 `04-context.md`: section 8 for 04-3 and 04-5.

# [x] Phase 14: Projects, folders, metadata, parts, Save to library (wave A)

Report: [05-implementation-phase-14.md](05-implementation-phase-14.md)

- [x] 14.1 `projects.md` split; new `context/frontend/folders-and-metadata.md`.
- [x] 14.2 `07-database.md`, `paths-and-data.md` done; `endpoints.md`, `components.md`, `private-library.md` by pending edits (the join of wave A); `private-library.md` checked.

# [x] Phase 15: From the audio to the notes: Source, Audio, the transcription (wave B)

Report: [05-implementation-phase-15.md](05-implementation-phase-15.md)

- [x] 15.1 `muscriptor.md`, `pieces-and-revisions.md`, `transcription-quality.md`, `transcription-pipeline.md`.
- [x] 15.2 The Source and Audio parts of `projects.md` done; `endpoints.md` by the join of wave B (E15.1 in the report); `components.md` checked, no change.

# [x] Phase 16: The notes and the hands: the Notes step, the piano roll, the hand split (wave C)

Report: [05-implementation-phase-16.md](05-implementation-phase-16.md)

- [x] 16.1 `piano-matrix-notation.md` (checked, no change), `events-to-sheet.md`, `hand-inference-second-pass.md`, `01-piano-svg.md`;
  `02-notation-spec.md` checked (three fixes).
- [x] 16.2 The Notes part of `projects.md` done; `endpoints.md` by the join of wave C (E16.1 in the report); `components.md` checked, no change.

# [x] Phase 17: Recording in Sheet, passages, Compose and parts (wave C)

Report: [05-implementation-phase-17.md](05-implementation-phase-17.md)

- [x] 17.1 `recording-in-sheet.md`, `playlists.md` (From other projects, the parts).
- [x] 17.2 `editing.md` (Recording in Sheet), `editing-and-compose.md` (Compose) done; `endpoints.md`, `components.md` checked, no change; `projects.md` section 6 label: pending edit E17.1 for the join of wave C.

# [x] Phase 18: The libraries, playlists, requests and the Public Library (wave A)

Report: [05-implementation-phase-18.md](05-implementation-phase-18.md)

- [x] 18.1 What changed since 2026-10-19; `check-names.py` on every page of `context/music-library/`.
- [x] 18.2 `context/music-library/*`, the playlists part of `playlists.md`, `endpoints.md` (checked, no change), `components.md` (a pending edit for the join: section 1.3).

# [x] Phase 19: Play mode, the Lab, users and admin, the routes and the shell (wave A)

Report: [05-implementation-phase-19.md](05-implementation-phase-19.md)

- [x] 19.1 `play-mode.md`, `pages.md`, `08-security.md` (corrected: the arrow keys, the step `hands`, the logout route, the `/dev/ui` route).
- [x] 19.2 New `context/frontend/lab.md` (no page told the Lab; it was one line in five pages).
- [x] 19.3 `endpoints.md`, `components.md`: pending edits for the join (E1 to E5 in the report, plus E6 for `00-index.md` and E7 for `projects.md`).

# [x] Phase 20: The platform pages, the READMEs, the indexes, the closing (wave E)

Report: [05-implementation-phase-20.md](05-implementation-phase-20.md)

- [x] 20.1 The platform pages `00` to `09`, the app context and its glossary.
- [x] 20.2 The READMEs (the folders, the services, the root); the map at the top of the core README.
- [x] 20.3 The journals; 04-3 Phase 6 and 04-5 task 5.2 closed; the inventory final.
- [x] 20.4 `check-names.py` on the whole scope; the links check.

# Joins

- [x] Join of wave A (after Phases 2, 5, 9, 14, 18, 19). Report: [05-implementation-join-A.md](05-implementation-join-A.md)
- [x] Join of wave B (after Phases 3, 6, 10, 11, 15). Report: [05-implementation-join-B.md](05-implementation-join-B.md)
- [x] Join of wave C (after Phases 4, 7, 12, 16, 17). Report: [05-implementation-join-C.md](05-implementation-join-C.md)
- [x] Join of wave D (after Phases 8, 13). Report: [05-implementation-join-D.md](05-implementation-join-D.md)
