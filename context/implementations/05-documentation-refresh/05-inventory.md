# 05: The inventory of the documentation

The plan is [`05-plan.md`](05-plan.md); the status of the phases is in [`05-checklist.md`](05-checklist.md).
Written in Phase 1 (2026-11-01). One row per file in the scope of plan section 1, Phase 1.

**Missing** is the count of names that `scripts/docs/check-names.py` cannot find in the code (its rules are
in the script's first lines). It is a first count: a missing name may be stale, a name of another machine, or
a name that the checker does not know how to search. Each phase reads its own rows. **Covers** is the H1 title
of the page. **State** is `to check` until the owner phase sets it.

| File | Lines | Last change | Owner | Missing | Covers | State |
|---|---:|---|---|---:|---|---|
| [README.md](../../../README.md) | 76 | 2026-10-27 | 20 | 0 | AImpromptu (aitu) | `to check` |
| [aitu-backend/README.md](../../../aitu-backend/README.md) | 109 | 2026-10-27 | 20 | 2 | aitu-backend | `to check` |
| [aitu-backend/src/aitu_backend/sheet/README.md](../../../aitu-backend/src/aitu_backend/sheet/README.md) | 544 | 2026-10-30 | 2, 3, 9, 10 (their sections); 20 the map | 0 | aitu_backend.sheet: the product core of the new piano sheet chain | `updated` (Phase 2: sections 1, 2, 4, 12) |
| [aitu-frontend/README.md](../../../aitu-frontend/README.md) | 136 | 2026-10-27 | 20 | 1 | aitu-frontend | `to check` |
| [context/00-documentation-instructions.md](../../../context/00-documentation-instructions.md) | 91 | 2026-10-27 | 20 | 0 | Documentation instructions | `to check` |
| [context/00-index.md](../../../context/00-index.md) | 326 | 2026-10-28 | 20 | 2 | Documentation index | `to check` |
| [context/00-project-complete-overview.md](../../../context/00-project-complete-overview.md) | 248 | 2026-10-28 | 20 | 1 | AImpromptu (aitu) — complete project overview | `to check` |
| [context/01-project.md](../../../context/01-project.md) | 126 | 2026-10-28 | 20 | 0 | Project | `to check` |
| [context/02-tech-stack.md](../../../context/02-tech-stack.md) | 101 | 2026-11-01 | 9, then 20 | 1 | Tech stack (Phase 9: the AI row added; `allowedHosts` is an older name, not checked by Phase 9) | `updated` |
| [context/ai/README.md](../../../context/ai/README.md) | 66 | 2026-11-01 | 9 | 5 | The AI in the app: the kinds of run, the model, the AI mark (later pages named by the phases that write them) | `new` |
| [context/ai/whole-run.md](../../../context/ai/whole-run.md) | 92 | 2026-11-01 | 9 | 2 | The whole run: Enhance it again with AI, Write it all again, the windows, the check, Stop and Revert | `new` |
| [documentation/services/backend/ai-runs.md](../../../documentation/services/backend/ai-runs.md) | 150 | 2026-11-01 | 9, then 10 | 0 | The code of the AI runs: the model client, the job, the windows and the check, the prompt, the routes | `new` |
| [context/02b-local-setup.md](../../../context/02b-local-setup.md) | 577 | 2026-10-27 | 20 | 29 | Local setup: Mac Mini M4 + Ubuntu compute box | `to check` |
| [context/03-services-overview.md](../../../context/03-services-overview.md) | 119 | 2026-10-27 | 20 | 0 | Services overview | `to check` |
| [context/04-local-development.md](../../../context/04-local-development.md) | 200 | 2026-10-31 | 20 | 0 | Local development | `to check` |
| [context/05-deployment.md](../../../context/05-deployment.md) | 37 | 2026-10-18 | 20 | 0 | Deployment | `to check` |
| [context/07-database.md](../../../context/07-database.md) | 211 | 2026-10-30 | 14 (11 adds `level_of`) | 1 | Database | `updated` |
| [context/08-security.md](../../../context/08-security.md) | 124 | 2026-10-16 | 19 | 1 | Security | `updated` |
| [context/09-coding-conventions.md](../../../context/09-coding-conventions.md) | 118 | 2026-10-27 | 20 | 5 | Coding conventions | `to check` |
| [context/app/01-app-context.md](../../../context/app/01-app-context.md) | 243 | 2026-10-27 | 20 | 0 | AImpromptus | `to check` |
| [context/backend/README.md](../../../context/backend/README.md) | 96 | 2026-10-27 | 20 | 2 | aitu-backend | `to check` |
| [context/backend/api.md](../../../context/backend/api.md) | 121 | 2026-10-27 | 20 | 2 | HTTP API | `to check` |
| [context/backend/editing.md](../../../context/backend/editing.md) | 132 | 2026-11-01 | 6 (17 Recording in Sheet, 5 the note edits) | 0 | Editing a piece: paste, Recording in Sheet, and parts; the note edits (Phase 5) | `updated` |
| [context/backend/muscriptor.md](../../../context/backend/muscriptor.md) | 109 | 2026-10-06 | 15 | 0 | MuScriptor: the transcription engine | `to check` |
| [context/backend/piano-matrix-notation.md](../../../context/backend/piano-matrix-notation.md) | 213 | 2026-10-27 | 16 | 1 | The piano matrix notation: the stored form, the wire form, the adapters | `to check` |
| [context/backend/pieces-and-revisions.md](../../../context/backend/pieces-and-revisions.md) | 133 | 2026-10-27 | 15 | 0 | Pieces, steps and revisions | `to check` |
| [context/backend/time-model.md](../../../context/backend/time-model.md) | 155 | 2026-10-27 | 2 | 0 | The wall-clock model | `updated` |
| [context/colors/color-palette.md](../../../context/colors/color-palette.md) | 90 | 2026-10-06 | 20 | 0 | Colour palette | `to check` |
| [context/frontend/README.md](../../../context/frontend/README.md) | 115 | 2026-10-28 | 20 | 0 | aitu-frontend | `to check` |
| [context/frontend/annotations-notes.md](../../../context/frontend/annotations-notes.md) | 88 | 2026-11-01 | 5 | 0 | The note toolbox of the new sheet (the old page is in `archive/old-sheet-tools/`) | `rewritten` |
| [context/frontend/annotations-sheet.md](../../../context/frontend/annotations-sheet.md) | 147 | 2026-10-31 | 7 | 4 | The sheet toolbox, the keyboard panel, and trills | `to check` |
| [context/frontend/annotations-stretches.md](../../../context/frontend/annotations-stretches.md) | 97 | 2026-10-27 | 6 | 3 | The range toolbox, and octave brackets on the page | `to check` |
| [context/frontend/annotations.md](../../../context/frontend/annotations.md) | 142 | 2026-11-01 | 5 | 0 | The Sheet step: the hub of the new sheet's tools (the old sheet's sections are in `archive/old-sheet-tools/`) | `updated` |
| [context/frontend/lab.md](../../../context/frontend/lab.md) | 92 | 2026-11-01 | 19 | 0 | The Lab: the video reader's five tabs, the examples and the score board, the modules | `new` |
| [context/frontend/pages.md](../../../context/frontend/pages.md) | 154 | 2026-11-01 | 19 | 1 | Pages and the shell | `updated` |
| [context/frontend/play-mode.md](../../../context/frontend/play-mode.md) | 126 | 2026-11-01 | 19 | 0 | Play mode | `updated` |
| [context/frontend/playlists.md](../../../context/frontend/playlists.md) | 84 | 2026-10-15 | 17 (18 the playlists part) | 0 | From other projects, and the playlists | `updated` (18's part: section 3) |
| [context/frontend/printing.md](../../../context/frontend/printing.md) | 94 | 2026-10-27 | 8 | 0 | Printing the sheet — the PDF export | `to check` |
| [context/frontend/projects.md](../../../context/frontend/projects.md) | 286 | 2026-10-29 | 14 (4, 15, 16 adjust their step) | 0 | Projects and the steps of a project | `updated` |
| [context/frontend/folders-and-metadata.md](../../../context/frontend/folders-and-metadata.md) | 132 | new | 14 | 0 | The pills, the folders, the Filter, the metadata and the info dialog of My projects and My library | `new` |
| [context/frontend/recording-in-sheet.md](../../../context/frontend/recording-in-sheet.md) | 98 | 2026-10-27 | 17 | 0 | Recording in Sheet: the page of a passage | `to check` |
| [context/frontend/rendering.md](../../../context/frontend/rendering.md) | 104 | 2026-10-31 | 3 (backend half), 4 (frontend half) | 3 | Rendering: how the sheet is drawn | `to check` |
| [context/frontend/timestamps.md](../../../context/frontend/timestamps.md) | 49 | 2026-09-13 | 4 | 4 | Timestamps and frame labels — UI rule | `to check` |
| [context/music/notation-logic/02-notation-spec.md](../../../context/music/notation-logic/02-notation-spec.md) | 150 | 2026-10-27 | 16 (check only) | 4 | The text-notation contract | `to check` |
| [context/music/piano_svg/01-piano-svg.md](../../../context/music/piano_svg/01-piano-svg.md) | 253 | 2026-07-27 | 16 | 0 | Context | `to check` |
| [context/music/transcription-quality.md](../../../context/music/transcription-quality.md) | 161 | 2026-10-06 | 15 | 0 | Transcription quality: what goes wrong between audio and a printed figure | `to check` |
| [context/music-library/README.md](../../../context/music-library/README.md) | 38 | 2026-10-19 | 18 | 0 | The music library | `true` |
| [context/music-library/genres.md](../../../context/music-library/genres.md) | 126 | 2026-10-19 | 18 | 0 | Genres and tags of the public songs | `true` |
| [context/music-library/ontology.md](../../../context/music-library/ontology.md) | 126 | 2026-10-19 | 18 | 0 | The music library's ontology | `true` |
| [context/music-library/popularity.md](../../../context/music-library/popularity.md) | 156 | 2026-10-19 | 18 | 0 | Popularity | `true` |
| [context/music-library/private-library.md](../../../context/music-library/private-library.md) | 165 | 2026-10-29 | 18 | 1 | The Private Library | `updated` |
| [context/music-library/reconciliation.md](../../../context/music-library/reconciliation.md) | 223 | 2026-10-19 | 18 | 4 | The music library data, reconciled | `true` |
| [context/music-library/regional-sources.md](../../../context/music-library/regional-sources.md) | 169 | 2026-10-19 | 18 | 0 | The sources of the `spain` and `catalan` regions | `true` |
| [context/music-library/requests.md](../../../context/music-library/requests.md) | 172 | 2026-10-19 | 18 | 0 | Requests and the review | `true` |
| [documentation/README.md](../../../documentation/README.md) | 3 | 2026-07-05 | 20 | 0 | documentation | `to check` |
| [documentation/services/README.md](../../../documentation/services/README.md) | 38 | 2026-10-27 | 20 | 3 | documentation/services | `to check` |
| [documentation/services/backend/editing-and-compose.md](../../../documentation/services/backend/editing-and-compose.md) | 262 | 2026-10-27 | 6 (17 the Compose part) | 10 | Copy and paste, Recording in Sheet, and the parts of a project | `to check` |
| [documentation/services/backend/endpoints.md](../../../documentation/services/backend/endpoints.md) | 1303 | 2026-10-31 | shared: every phase its sections; 20 checks | 6 | Endpoints | `to check` |
| [documentation/services/backend/events-to-sheet.md](../../../documentation/services/backend/events-to-sheet.md) | 231 | 2026-10-28 | 16 | 4 | From the stored notes (`notes.pmn`) to the hand split the sheet starts from | `to check` |
| [documentation/services/backend/hand-inference-second-pass.md](../../../documentation/services/backend/hand-inference-second-pass.md) | 114 | 2026-08-13 | 16 | 0 | Hand inference: the page-level second pass | `to check` |
| [documentation/services/backend/paths-and-data.md](../../../documentation/services/backend/paths-and-data.md) | 549 | 2026-10-29 | 14 (8, 11, 13 add their parts) | 6 | Storage layout: every path, every file, every table | `updated` |
| [documentation/services/backend/rhythm-and-annotations.md](../../../documentation/services/backend/rhythm-and-annotations.md) | 401 | 2026-10-27 | 2 | 2 | `sheet.json`: the old sheet's reading, still read | `updated` (2 names kept on purpose: see the Phase 2 report) |
| [documentation/services/backend/sheet-f1.md](../../../documentation/services/backend/sheet-f1.md) | new | 2026-11-01 | 2 | 0 | The new sheet: the files of a part, the F1 text, how the algorithm makes it | `new` |
| [documentation/services/backend/time-matrix.md](../../../documentation/services/backend/time-matrix.md) | 59 | 2026-10-27 | 2 | 0 | The time matrix: what stays of schema 2.0 | `updated` |
| [documentation/services/backend/transcription-pipeline.md](../../../documentation/services/backend/transcription-pipeline.md) | 483 | 2026-10-27 | 15 | 8 | The transcription pipeline: modules, order, parameters | `to check` |
| [documentation/services/frontend/components.md](../../../documentation/services/frontend/components.md) | 581 | 2026-10-31 | shared: every phase its sections; 20 checks | 85 | The component tree: where each piece lives | `to check` |
| [documentation/services/frontend/score-pdf.md](../../../documentation/services/frontend/score-pdf.md) | 94 | 2026-10-27 | 8 | 3 | Score PDF export | `to check` |

61 files, 12020 lines, 204 missing names (first count).

## Code changed since 2026-10-28

`git log --since=2026-10-28 --numstat`: 58 commits. Summed per folder (up to five path parts). Lines are added and deleted lines; a file counts once per folder.

| Folder | Files | Added | Deleted |
|---|---:|---:|---:|
| `context/implementations/04-app-enhancements/gallery/04-3-phase-5/` | 142 | 12768 | 2 |
| `context/implementations/04-app-enhancements/gallery/04-3-phase-2/` | 262 | 11287 | 542 |
| `aitu-backend/src/aitu_backend/sheet/llm/` | 125 | 8108 | 188 |
| `context/implementations/04-app-enhancements/` | 20 | 4729 | 256 |
| `context/implementations/04-app-enhancements/gallery/04-3-phase-3/` | 18 | 4395 | 36 |
| `aitu-frontend/src/pages/piece/sheet/` | 18 | 2307 | 393 |
| `aitu-backend/tests/` | 12 | 2043 | 77 |
| `aitu-backend/src/aitu_backend/part_sheet/` | 6 | 1445 | 212 |
| `context/guidelines/` | 3 | 1362 | 0 |
| `aitu-frontend/src/components/folders/` | 11 | 1187 | 6 |
| `aitu-backend/src/aitu_backend/api/` | 6 | 915 | 46 |
| `aitu-frontend/scripts/` | 6 | 875 | 77 |
| `aitu-backend/src/aitu_backend/library/` | 4 | 740 | 43 |
| `aitu-backend/src/aitu_backend/sheet/levels/` | 4 | 658 | 0 |
| `context/implementations/05-documentation-refresh/` | 3 | 595 | 0 |
| `aitu-frontend/src/api/` | 6 | 392 | 9 |
| `context/implementations/04-app-enhancements/gallery/04-5/` | 9 | 397 | 0 |
| `aitu-backend/scripts/` | 2 | 359 | 17 |
| `aitu-frontend/src/pages/` | 1 | 249 | 95 |
| `aitu-frontend/src/pages/library/` | 2 | 250 | 62 |
| `aitu-backend/src/aitu_backend/sheet/engrave/` | 3 | 163 | 42 |
| `aitu-backend/src/aitu_backend/db/migrations/` | 3 | 179 | 0 |
| `aitu-backend/src/aitu_backend/` | 1 | 173 | 4 |
| `context/frontend/` | 5 | 123 | 46 |
| `aitu-backend/src/aitu_backend/db/` | 3 | 108 | 3 |
| `documentation/services/backend/` | 3 | 61 | 13 |
| `context/` | 5 | 38 | 15 |
| `context/music-library/` | 1 | 36 | 7 |
| `documentation/services/frontend/` | 1 | 31 | 10 |
| `aitu-backend/src/aitu_backend/sheet/` | 1 | 30 | 11 |
| `aitu-frontend/src/components/audio/` | 2 | 23 | 9 |
| `aitu-frontend/src/pages/piece/` | 2 | 23 | 6 |
| `aitu-backend/src/aitu_backend/sheet/sheet/` | 3 | 24 | 3 |
| `aitu-frontend/src/ui/` | 2 | 22 | 4 |
| `aitu-backend/` | 2 | 22 | 0 |
| `context/implementations/` | 1 | 14 | 5 |
| `context/implementations/03-apply-poc-research/` | 1 | 7 | 3 |
| `aitu-backend/src/aitu_backend/storage/` | 1 | 8 | 1 |
| `aitu-frontend/src/audio/` | 1 | 8 | 0 |
| `aitu-backend/src/aitu_backend/sheet/proposal/` | 1 | 3 | 2 |
| `aitu-backend/src/aitu_backend/auth/` | 1 | 3 | 1 |
| `aitu-frontend/` | 1 | 3 | 0 |
| `(root)/` | 1 | 3 | 0 |
| `context/implementations/04-app-enhancements/gallery/phase-4/` | 1 | 1 | 1 |
