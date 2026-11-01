# 05, Phase 9: The AI, part 1: the AI on the sheet, the whole run

Wave A. Plan: [05-plan.md](05-plan.md) section 6, Phase 9. Checklist: [05-checklist.md](05-checklist.md).

## Docs changed

- `context/ai/README.md` (new, 66 lines): the AI in the app, the kinds of run (later pages named by their phase), the
  model and the cost (names of the settings only), the AI mark, the words of the states.
- `context/ai/whole-run.md` (new, 92 lines): **Enhance with AI**, **Write it all again**, the batches, the panel and its
  states, **Stop** and **Revert**, the windows, the check, the fallback, the limits.
- `documentation/services/backend/ai-runs.md` (new, 150 lines): the model client (`sheet_llm.py`), the job
  (`part_sheet/job.py`: `start`, `work`, `stop`, `commit`, `costs`), the windows and the check (`sheet/llm/frames.py`),
  the prompt folder and its version, the routes, the stored result.
- `context/02-tech-stack.md`: one row "AI (Enhance with AI)" after the GPU row: GPT-6.1 Terra at medium, the two other
  choices, the names of the two settings, the date of the change (implementation 04-3, Phase 5).

## What was stale

- `context/` had no page for the AI; the only account was the core README (sections 5 and 11) and the implementation
  files.
- `context/02-tech-stack.md` named no AI client and no model.
- The core README (sections 5 and 11, Phase 2's file in wave A, so pending) names Sonnet 5.5 as the product's model
  and version 6 of the prompt. Both are false now: every run uses GPT-6.1 Terra at medium (`job.MODEL`, `job.EFFORT`),
  and the prompt is version 7 (`PROMPT_VERSION` in `frames.py`).
- `endpoints.md` (shared, pending) says "Sonnet" in the sheet's description; the routes of Phase 9 are already there and
  right.

## Code and docs that disagree (for the user; not a doc fix)

- `aitu-backend/src/aitu_backend/sheet_llm.py`, the module docstring of `OpenAIComplete`: "The app does not use it yet".
  It is used by every run since implementation 04-3, Phase 5 (`job._complete`). A code comment; a code change would
  fix it.
- Two prompts in one folder: `sheet/llm/prompt/instructions.md` (frozen, the research's bars chain, read by
  `prompts.py`, not by the whole run) and `sheet/llm/prompt/frames/instructions.md` (version 7, the whole run's). The
  name is the same; the whole run does not read the first one. Worth a rename or a note in the code.
- Code comments and two messages still say "Sonnet" for any run: `part_sheet/job.py` (the `PartGone` text: "The part was
  deleted while Sonnet wrote its sheet."; many docstrings), `api/sheet.py`, `frontend/.../FramesSheetView.tsx` (a
  comment "The segment at Sonnet"). The PartGone text may reach a log or a message; the other ones are comments.

## New terms for the glossary (Phase 20)

- **Write it all again**: the tab "The whole song" button of the dialog that runs the whole run.
- **Enhance it again with AI**: the label of the button once the part was enhanced.
- **Being written**, **Written**, **Kept as it was**, **Waiting**: the states of a batch in the run's panel.
- **Batches**: the parts the song is written in (the dialog's count; of about the same time).
- **The AI mark**: the small logo before a song's name (green when enhanced, faint grey when it could be).

## Not checked

- The frontend code: I read the headers and the labels (`AiRunPanel.tsx`, `EnhanceDialog.tsx`, `AiMark.tsx`,
  `FramesSheetView.tsx` header, `FramesSheetPage.tsx` the label lines), not the bodies. The panel's wording is copied
  from its `STATE_WORDS` and its notices.
- The cost and time constants: named, not copied (they change with the measurements).
- `ClaudeComplete` internals: only its module docstring.
- `_llm_state` (the page's state of a part): named, its fields not listed.
- No run of the app, no AI call (the plan's rule).
- `check-names.py`: `context/02-tech-stack.md:33` names `allowedHosts`, not found in the code roots. The line is older
  than this phase; where it comes from is not checked; left for Phase 20.

## check-links and check-names

- `check-links.py`: 514 files, 1 broken link, not in my files: `context/frontend/pages.md:38` names `lab.md` (Phase 19's
  page, not yet written). My files have no broken link.
- `check-names.py` on my four files: 130 names, 8 missing. Expected: the later pages (`stretch-and-simplify.md`,
  `levels.md`, `level-run.md`, `run-history.md`, `context/frontend/sheet-page.md`, named as text in code style) and
  `allowedHosts` (above). No name of `ai-runs.md` or `whole-run.md` is missing.

## Pending edits for shared files

Each edit: the file, where, and the exact change. The join of wave A applies them in this order.

1. **`aitu-backend/src/aitu_backend/sheet/README.md`** (owner Phase 2 in wave A; Phase 9 owns sections 5 and 11). I
   edited it by mistake during this phase and put my edits back at once (the file's diff has only Phase 2's work now).
   - Section 5, the paragraph that begins "The core imports no LLM SDK.": replace it with
     > The core imports no LLM SDK. The product's `complete` functions are in `sheet_llm.py`: the OpenAI client (GPT-6.1
     > Terra at medium, the model of every run unless the user chooses another) and the Anthropic client (Sonnet 5.5, when
     > the user chooses it). The pages of the AI: `context/ai/README.md` and `documentation/services/backend/ai-runs.md`. A
     > `complete` that raises stops the chain with that error (the product decides retries and time limits).
   - Section 11, the sentence "`complete(system, messages) -> text`; the product's function is
     `aitu_backend.sheet_llm.ClaudeComplete` (Sonnet 5.5, outside the core).": replace "the product's function is
     `aitu_backend.sheet_llm.ClaudeComplete` (Sonnet 5.5, outside the core)" with "the product's functions are in
     `aitu_backend.sheet_llm` (GPT-6.1 Terra at medium by default, Sonnet 5.5 when chosen; section 5 above)".
   - Section 11, bullet "Frozen files": "(version 6, five examples checked by" → "(version 7 since implementation 04-3, the examples checked
     by". Then append to the bullet "Prompt 6" paragraph's end, or to the "Frozen files" bullet: "The prompt's history
     and the job that runs it: `documentation/services/backend/ai-runs.md`."
   - Section 11, the diagram line "`POST /sheet/{part}/llm ── part_sheet.job.start ── write_frames(on_start, on_part) with
     sheet_llm.ClaudeComplete`": replace "with sheet_llm.ClaudeComplete" by "with the chosen model's client (`job._complete`)".
   - Section 11, the sentence "Since implementation 04, Phase 3 the prompt is version 6 and the record says `6+hands`.":
     add at its end "Since implementation 04-3 (2026-10-30) version 7."
2. **`documentation/services/backend/endpoints.md`** (shared; section 4 "The sheet"). The routes of Phase 9 (`POST
   /sheet/{uuid}/llm`, `/llm/stop`, `/llm/revert`, `/llm/costs`, `/llm/batches`) are right: no change to them. Change the
   words "Sonnet" in the sheet's own description:
   - the row `GET /sheet/{uuid}?width=N`: "the segments of Sonnet's windows and their state, and what the page may do with
     Sonnet (section 4.1)" → "the segments of the AI's windows and their state, and what the page may do with the AI
     (section 4.1)".
   - the line "`is stored. While Sonnet writes it is the sheet of that moment.`" → "is stored. While the AI writes it, it is
     the sheet of that moment."
   - the bullet "`segments`: Sonnet's windows (`working`: at Sonnet now; `waiting`; `llm`; `algorithm`: a window that
     failed); empty on a sheet Sonnet never wrote." → "`segments`: the AI's windows (`working`: being written now;
     `waiting`; `llm`; `algorithm`: a window that failed); empty on a sheet the AI never wrote."
   - the bullet "`llm.auto`: a new transcription asked for Sonnet" → "asked for the AI".
   - the paragraph "The job stops asking Sonnet when the part is deleted." → "The job stops asking the AI when the part is
     deleted."
   - Other "Sonnet" words in sections 4 (the stretch and simplify rows, the level rows) belong to Phases 10 to 13.
3. **`documentation/services/frontend/components.md`** (shared; section 8, "The shared components and the tokens"):
   add one row at the end of its table:
   > | `components/piece/AiMark.tsx` | The AI mark before a song's name (implementation 03, Phase 5): green once the AI enhanced the sheet, faint grey when it could and has not, a spinner while a job works on it. Always the same width |

   (`frames/AiRunPanel.tsx`, `frames/EnhanceDialog.tsx` already have rows in section 3: no change.)
4. **`context/00-index.md`** (join): add a group `context/ai/` after the frontend entries, with two lines:
   - `context/ai/README.md`: the AI in the app: the kinds of run, the model and the cost, the AI mark.
   - `context/ai/whole-run.md`: the whole run: **Write it all again**, the batches, the panel, **Stop** and **Revert**.
5. **`documentation/services/README.md`** (join): in the backend list, add
   `backend/ai-runs.md`: the code of the AI runs: the model client, the job, the windows and the check, the prompt, the routes.

## Left for later phases

- Phase 10: write `context/ai/stretch-and-simplify.md` and add sections to `documentation/services/backend/ai-runs.md`. Then
  the row for it in `context/ai/README.md` ("`stretch-and-simplify.md` (Phase 10 writes it)") becomes a link, and the
  sentence in `whole-run.md` ("a page Phase 10 writes") is replaced by the link.
- Phases 11 to 13: the rows of `context/ai/README.md` for `levels.md`, `level-run.md`, `run-history.md` become links when
  their pages exist (the join of each wave edits the README, as in the pending edits above).
- Phase 4: `context/frontend/sheet-page.md` is named in `whole-run.md` as text; make it a link when Phase 4 has written it.
- Phase 20: `context/00-documentation-instructions.md` lists the areas: add `context/ai/`. The map at the top of the core
  README says "prompt version 6" in its header (line 13): update to version 7.
- Phase 20: the `allowedHosts` name in `context/02-tech-stack.md`.
