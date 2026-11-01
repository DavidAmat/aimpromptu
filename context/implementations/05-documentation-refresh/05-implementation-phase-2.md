# 05, Phase 2: how a sheet is made (the notes to `sheet.f1`): report

Plan: [`05-plan.md`](05-plan.md), section 6, Phase 2 (wave A). Checklist: [`05-checklist.md`](05-checklist.md).
Date: 2026-11-01. Branch `feat/05-docs-refresh`.

## Docs changed

- `documentation/services/backend/sheet-f1.md` (new): the files of a part and their path functions; the F1 frames text
  (header, columns, `[]xN`, every tag, the title and lyrics lines); the record line (`store.Record`); `Note` and `Sheet`;
  the algorithm `propose_frames` step by step with its constants; the figures and the spelling rules; the part-level
  build (`current`, `_compute`, `reapply`, `mark_settled`); the old marks (a pointer to core README section 17); tests.
- `aitu-backend/src/aitu_backend/sheet/README.md`: section 1, the diagram now shows the app's path (frames sheet, drawn by
  `engrave.frames.render_frames`), and says that the bars path is the research's; section 2, a note that the app calls
  the frames entries only, and `sheet/pmn.py` corrected to `sheet/sheet/pmn.py`; section 4, the heading and a note that
  `viewer/` is not in the repository, with `build.draw` named as the app's equivalent; section 12, "Sonnet" changed to
  "the AI" (2 places). Sections 6 to 9, 16 and 17: checked, names and paths exist, no change.
- `context/backend/time-model.md`: a link to `sheet-f1.md` in "Where to look deeper". The rest was checked against
  `proposal/beat.py`, `part_sheet/build.py` and `sheet/sheet/data.py` and is true.
- `documentation/services/backend/time-matrix.md`: a link to `sheet-f1.md` in section 4. Its names all exist.
- `documentation/services/backend/rhythm-and-annotations.md`: a link to `sheet-f1.md` in section 7 (section 8 of the new
  page says what the old file still gives the new sheet).

## What was stale

- Core README section 1: the diagram showed the bars sheet (`proposal.propose`, `llm.write_song`,
  `engrave.cursor.render_song`) as the app's path. The app uses none of them (only `scripts/draw_sheet.py` uses
  `render_song`; no module of the app imports `llm.chain` or `proposal.pipeline` from outside `sheet/`).
- Core README section 2: `sheet/pmn.py` is `sheet/sheet/pmn.py`.
- Core README section 4: `viewer/server.py` and `viewer/index.html` are not in git (0 tracked files).
- Core README section 12: "Sonnet" in two places (the model is not named in the page now).

## Code and docs that disagree in a way that looks like a bug (for the user)

- The names and docstrings of the AI run still say Sonnet: `part_sheet/store.py` (`ask_sonnet`, `asked`, `taken`, and the
  docstring "every window by Sonnet"), `part_sheet/build.py` (the `Drawn.windows` comment). `tests/test_sheet_llm_openai.py` exists, so the client may not be
  Anthropic's.
- The project's notes (the memory of 2026-10-29 to 31) say every AI run is on GPT-6.1 Terra at `medium`; the code's
  comments say Sonnet 5.5. Not confirmed here. Phase 9 must settle the model from the code before it writes the name
  (`02-tech-stack.md`, core README sections 5 and 11).

## New terms for the glossary (Phase 20)

- **sheet.f1**: the stored new sheet of a part (the F1 frames text with one record line on top).
- **sheet.pending**: the marker that asks the AI to write a part's sheet (a new transcription).
- **record line**: the `# aitu-sheet {...}` line that says how a stored sheet was written.
- **reference figure** (`quarterMs`): the length of one negra; the figures are named from it.
- **drawn column**: the column at which a chord is drawn (40 ms from its first onset, D-04).
- **starting hands**: the hands the sheet starts from (the saved hands, then the hand split).
- **settled**: a stored text that is the result of laying the sheet again on the current notes (no need to lay it again).

## Not checked

- Core README section 8 (the licence table): not compared with the files.
- `part_sheet/job.py` (the AI run) was not read; the record fields come from the `store.py` docstring and `Record`.
- Test contents: the test list in `sheet-f1.md` § 9 comes from the test names and from core README section 7, not from
  reading the tests. No test was run (the plan forbids running them in this phase).
- The tag list of section 2 of `sheet-f1.md` comes from the `f1.py` module docstring and `_apply_tag`'s names, not from a
  line-by-line read of `_apply_tag`.
- The names the checker lists in `rhythm-and-annotations.md` are deliberate, and so are not fixed:
  `GET /time/{uuid}/default-reading` (the route removed in Phase 10, named as removed) and `systemGap` (the field of the
  drawing package the page contrasts with `lineSpacing`).
- `context/frontend/pages.md:38` has a broken link to `lab.md` (not a file of this phase; Phase 19 creates it, or
  the link is fixed then). `python3 scripts/docs/check-links.py`: 514 files, 1 broken link, not mine.

## Pending edits for shared files

1. `context/00-index.md`, and `documentation/services/README.md`: add an entry for
   `documentation/services/backend/sheet-f1.md` in the list of the backend pages, after `time-matrix.md`, in the style of
   the entries there. The one-line text: "The new sheet: the files of a part, the F1 text, how the algorithm makes it".
2. `documentation/services/backend/endpoints.md`: none (no route changed by this phase).

## Left for later phases

- Phase 3: `documentation/services/backend/sheet-drawing.md` (the page `sheet-f1.md` and the core README name it as
  written by Phase 3; until it exists, both pages name it in plain text, not as a link); core README sections 10 and
  15; `context/frontend/rendering.md` (the backend half).
- Phase 9: core README sections 5 and 11 name the model (`claude-sonnet-5-5` and `sheet_llm.ClaudeComplete`), and
  `02-tech-stack.md`. The model question in "What is stale" above is for Phase 9.
- Phase 8: the undo of a part (`sheet.edits.json`, `edits.py`) belongs to the undo section of `sheet-page.md`;
  `sheet-f1.md` § 1 says only what the file is.
- Phase 14: `paths-and-data.md` can link to `sheet-f1.md` § 1 for the files of a part.

## Shared tree

- During this phase `aitu-backend/src/aitu_backend/sheet/README.md` changed on disk, with hunks in sections 5, 10, 11
  and 13 that were not mine. When I looked again, the diff held only my hunks. I did not revert or edit those hunks, and
  I committed only the diff of my edits. Phases 3 and 9 should check that their own edits to the README are in place.
