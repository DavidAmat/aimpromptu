# 05: The documentation refresh: checklist

The plan is [`05-plan.md`](05-plan.md). Branch `feat/05-docs-refresh`. Status letters: `[x]` complete, `[p]` in
progress, `[b]` blocked, `[c]` cancelled, `[ ]` not started.

**Next phase: Phase 1.** (Each phase changes this line when it ends.)

Each phase, when done: its tasks `[x]`, the phase `[x]`, and the link to its report after the title, as
`Report: [05-implementation-phase-N.md](05-implementation-phase-N.md)`.

## Decisions

- [x] The defaults of plan section 2 (the folder, the branch, the old sheet's pages to the archive, one phase at a
  time): the user's ok (2026-11-01). 04-5 merged into `master` first; `feat/05-docs-refresh` made from `master`.

# [ ] Phase 1: The inventory and the name check

- [ ] 1.1 `scripts/docs/check-names.py`; a line about it in `00-documentation-instructions.md`.
- [ ] 1.2 `05-inventory.md`: every file in scope, its owner, its missing names, State `to check`.
- [ ] 1.3 The code changed since 2026-10-28, per folder.

# [ ] Phase 2: How a sheet is made (the notes to `sheet.f1`)

- [ ] 2.1 New `documentation/services/backend/sheet-f1.md`.
- [ ] 2.2 `time-matrix.md`, `rhythm-and-annotations.md`, `context/backend/time-model.md`.
- [ ] 2.3 The core README sections 1 to 9, 12, 16, 17.

# [ ] Phase 3: How the sheet is drawn (the backend)

- [ ] 3.1 New `documentation/services/backend/sheet-drawing.md`.
- [ ] 3.2 `context/frontend/rendering.md` (the backend half); the core README sections 10 and 15.

# [ ] Phase 4: The sheet page (the frontend shell)

- [ ] 4.1 New `context/frontend/sheet-page.md`.
- [ ] 4.2 `rendering.md` (the frontend half), the Sheet step in `projects.md`, `timestamps.md`.
- [ ] 4.3 `components.md`: the page, the view, the hooks.

# [ ] Phase 5: The note toolbox

- [ ] 5.1 `annotations.md` as the hub of the tools (about 200 lines at most).
- [ ] 5.2 The old `annotations-notes.md` to `context/archive/old-sheet-tools/`; a new one for the note toolbox.
- [ ] 5.3 `editing.md` (the note edits), `endpoints.md`, `components.md`.

# [ ] Phase 6: The range toolbox, copy and paste

- [ ] 6.1 The old `annotations-stretches.md` to the archive; a new one for the range toolbox.
- [ ] 6.2 `editing.md` (Paste), `editing-and-compose.md`, `endpoints.md`, `components.md`.

# [ ] Phase 7: The sheet toolbox: Info, Key, Transpose, Lyrics, View

- [ ] 7.1 The old `annotations-sheet.md` to the archive; a new one for the sheet toolbox and the lyrics.
- [ ] 7.2 `endpoints.md` (`/transpose`, `/words`), `components.md`.

# [ ] Phase 8: Undo, redo, the preview and the PDF

- [ ] 8.1 `printing.md`, `score-pdf.md`.
- [ ] 8.2 Undo and redo in `sheet-page.md`; `endpoints.md`, `paths-and-data.md`.

# [ ] Phase 9: The AI, part 1: the AI on the sheet, the whole run

- [ ] 9.1 New `context/ai/README.md` and `context/ai/whole-run.md`.
- [ ] 9.2 New `documentation/services/backend/ai-runs.md`.
- [ ] 9.3 `02-tech-stack.md` (the AI client, the model); the core README sections 5 and 11; `endpoints.md`,
  `components.md`.

# [ ] Phase 10: The AI, part 2: a stretch, Simplify, the Enhance with AI dialog

- [ ] 10.1 New `context/ai/stretch-and-simplify.md`; sections in `ai-runs.md`.
- [ ] 10.2 The core README section 14; `endpoints.md`, `components.md`.

# [ ] Phase 11: The AI, part 3: levels, the catalog of patterns, the chords of the song

- [ ] 11.1 New `context/ai/levels.md` and `documentation/services/backend/ai-levels.md`.
- [ ] 11.2 `paths-and-data.md`, `07-database.md`, `endpoints.md`, `components.md`.

# [ ] Phase 12: The AI, part 4: the level run

- [ ] 12.1 New `context/ai/level-run.md`.
- [ ] 12.2 Sections in `ai-levels.md`; `endpoints.md`.

# [ ] Phase 13: The AI, part 5: the history of AI runs, and `04-context.md`

- [ ] 13.1 New `context/ai/run-history.md`; the log in `ai-levels.md` and `paths-and-data.md`.
- [ ] 13.2 `endpoints.md`, `components.md`.
- [ ] 13.3 `04-context.md`: a section for 04-3 and 04-5.

# [ ] Phase 14: Projects, folders, metadata, parts, Save to library

- [ ] 14.1 `projects.md` split; new `context/frontend/folders-and-metadata.md`.
- [ ] 14.2 `07-database.md`, `paths-and-data.md`, `endpoints.md`, `components.md`; `private-library.md` checked.

# [ ] Phase 15: From the audio to the notes: Source, Audio, the transcription

- [ ] 15.1 `muscriptor.md`, `pieces-and-revisions.md`, `transcription-quality.md`, `transcription-pipeline.md`.
- [ ] 15.2 The Source and Audio parts of `projects.md`; `endpoints.md`, `components.md`.

# [ ] Phase 16: The notes and the hands: the Notes step, the piano roll, the hand split

- [ ] 16.1 `piano-matrix-notation.md`, `events-to-sheet.md`, `hand-inference-second-pass.md`, `01-piano-svg.md`;
  `02-notation-spec.md` checked.
- [ ] 16.2 The Notes part of `projects.md`; `endpoints.md`, `components.md`.

# [ ] Phase 17: Recording in Sheet, passages, Compose and parts

- [ ] 17.1 `recording-in-sheet.md`, `playlists.md` (From other projects, the parts).
- [ ] 17.2 `editing.md` (Recording in Sheet), `editing-and-compose.md` (Compose), `endpoints.md`, `components.md`.

# [ ] Phase 18: The libraries, playlists, requests and the Public Library

- [ ] 18.1 What changed since 2026-10-19; `check-names.py` on every page of `context/music-library/`.
- [ ] 18.2 `context/music-library/*`, the playlists part of `playlists.md`, `endpoints.md`, `components.md`.

# [ ] Phase 19: Play mode, the Lab, users and admin, the routes and the shell

- [ ] 19.1 `play-mode.md`, `pages.md`, `08-security.md`.
- [ ] 19.2 New `context/frontend/lab.md` (if no page tells the Lab).
- [ ] 19.3 `endpoints.md`, `components.md`.

# [ ] Phase 20: The platform pages, the READMEs, the indexes, the closing

- [ ] 20.1 The platform pages `00` to `09`, the app context and its glossary.
- [ ] 20.2 The READMEs (the folders, the services, the root); the map at the top of the core README.
- [ ] 20.3 The journals; 04-3 Phase 6 and 04-5 task 5.2 closed; the inventory final.
- [ ] 20.4 `check-names.py` on the whole scope; the links check.
