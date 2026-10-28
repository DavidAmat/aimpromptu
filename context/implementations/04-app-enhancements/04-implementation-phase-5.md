# 04 · Phase 5: documentation and closing

Technical report, for the agents of later implementations. Plan: [`04-plan.md`](04-plan.md) Phase 5. Branch
`feat/04-phase-5` (from `master` at `7479b68`). Documentation only: no code file, no database change, no AI call.

State: done (2026-10-28); waiting for the user's ok to merge.

# 1. What was done

| Task | Result |
|---|---|
| 5.1 The documentation still stale | Section 2 |
| 5.2 `04-context.md` | [`04-context.md`](04-context.md): what 04 changed, the decisions that bind, the code, the rules for a new change, the reports, the checks, the open points; [`03-context.md`](../03-apply-poc-research/03-context.md) points at it (a note at the top, the grace-notes row of section 2, prompt 6 in 3.2, `EnhanceDialog` in 3.3) |
| 5.3 The final checks, the open points | Sections 3 and 4 |

# 2. The documentation (task 5.1)

Phases 2 to 4 had already written most of it (the core's `README.md` sections 9, 11, 12 and 14, `rendering.md`,
`components.md`, `endpoints.md`, `context/backend/README.md`, `04-local-development.md`). A search for the old words
(sparkle, `EnhanceStretchDialog`, version 5, the badge, the confirmation of a whole run, the old grace rule) found
what was still stale:

| File | Change |
|---|---|
| `aitu-backend/src/aitu_backend/sheet/README.md` | The opening says what implementation 04 changed and where; section 2 lists `check_answer(hand=)`, `write_stretch`, `write_simplify`, `check_simplify`; section 12 says every stored sheet is laid again when drawn (`_settled`, `beam_pairs`); section 13 says the record is `6+hands` since prompt 6 |
| `context/frontend/projects.md` | The AI mark is the logo (not the sparkle); the Enhance with AI dialog (a stretch of both hands or one; Simplify left, right, both; Write it all again; the costs) in place of the confirmation of a whole run |
| `context/frontend/annotations.md` | The new sheet: the decoration-note rule; the stretch opens the dialog (Both, Right, Left: one hand fixed); the whole song and Simplify; Write it all again with prompt 6's note changes; the steps of undo of a whole run and of Simplify |
| `context/frontend/rendering.md` | The hooks of Phases 1 and 4; the checks `check:frames-page` and `check:enhance-dialog` |
| `context/frontend/README.md` | Simplify in the list of what a reader does; `POST /sheet/{id}/llm/simplify` in the data flow |
| `context/00-project-complete-overview.md`, `context/01-project.md` | Implementations 03 and 04 in "How it was built"; Simplify and the header in the Sheet row |
| `documentation/services/backend/events-to-sheet.md` | Prompt 6 and Simplify in "From the hands to the sheet" |
| `context/implementations/README.md`, `context/00-index.md`, [`README.md`](README.md) | 04 done, `04-context.md` and `04-2-prompt.md` listed, every report and gallery; 03 no longer "LIVE" in the index |
| [`04-plan.md`](04-plan.md), [`04-checklist.md`](04-checklist.md) | Status done; section 9 has prompt 04-2 (the logo, not listed before) and Phase 5 |

Not changed on purpose: `annotations-notes.md`, `annotations-sheet.md` and `annotations-stretches.md` describe the
old sheet as the record; the phase reports of 03 and of Phases 1 to 4 are records too.

# 3. Checks (task 5.3)

| Check | Result |
|---|---|
| `pytest` (CPU, GPU hidden) | 1,272 tests; all pass but the two known Transkun tests (they load their weights only on the GPU) |
| `npm run build` (`tsc -b`, `vite build`), `npm run lint` | pass |
| Browser checks on temporary copies, one at a time | `check:frames-page`, `check:enhance-dialog`, `check:frames-sheet`, `check:frames-edit` (10 hand moves, median 284 ms), `check:frames-tools`, `check:frames-toolbox`: all passed |
| `scripts/docs/check-links.py` | 0 broken links |

# 4. The open points

In [`04-context.md`](04-context.md) section 7:

- 7 Years in My library (`1a16a836`) still holds the prompt 5 sheet (checked in the database: `prompt` `5`, written
  2026-10-25). The prompt 6 sheet is on the edit copy in the Personal Vault (`477086a0`: `prompt` `6+hands`,
  `added` 4, `leftOut` 2); the library version changes when the user saves that copy to the library.
- The other songs keep prompt 5 sheets until the user runs the AI on them.
- A Simplify run is not saved batch by batch (a backend reload loses it), like a whole run.
- Simplify's estimate is low on dense songs (Moonlight Shadow $0.10 estimated, $0.21 measured).
