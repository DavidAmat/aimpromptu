# 05, Phase 13: The AI, part 5: the history of AI runs, and `04-context.md`

The plan is [`05-plan.md`](05-plan.md); the checklist is [`05-checklist.md`](05-checklist.md). Wave D (with Phase 8).
Read: `part_sheet/runs.py` (all), `part_sheet/job.py` (`continue_level`, `again_batch`, the state changes of
`_level_work`), `sheet/llm/levels.py` (`write_again`), `prompt/levels/answer.md`, `api/sheet.py` (the four routes),
`aitu-frontend/src/pages/piece/sheet/frames/` (`AiHistoryPanel.tsx`, `AiRunDetail.tsx`, the waiting state and the
**History** button of `AiRunPanel.tsx`, `batches.ts`), `api/sheet.ts` (the four methods), and the 04-3 and 04-5 plans
and reports (only the sections named in the plan). No code was changed, no app was run.

## Docs changed

- `context/ai/run-history.md` (new, 153 lines): the first batch first and the states of a run; the log
  (`ai-runs/<id>.json`); the history panel and the run; an answer to the AI and **Write this batch again**; **Go on
  with the other batches**; the four routes with their status codes; what the history does not do.
- `documentation/services/backend/ai-levels.md`: section 9 (was a placeholder) now has five parts: `runs.py`, the states
  and the two jobs in `job.py`, `write_again`, the four routes, the page. The "Where to look deeper" list links to
  `run-history.md`.
- `documentation/services/backend/paths-and-data.md`: one line in the `parts/<partId>/` tree for `ai-runs/<runId>.json`.
- `context/implementations/04-app-enhancements/04-context.md`: a new section 8 for 04-3 and 04-5 (what changed in
  each, the decisions that bind, where the code is, the open points), linked to the `context/ai/` pages. Section 1's
  intro still says "State: done on 2026-10-28"; section 8 is the update.

## What was stale

- `ai-levels.md` section 9 was a placeholder ("Phase 13 adds ...").
- No page told the history of runs; the only text was the core README's per-phase section (not checked here).
- `04-context.md` had seven sections, all about 04 (the state line says so). Section 8 is new.
- The 05 plan (section 3.4) names the button **Write batch 1 again**. The code says **Write this batch again** (any
  batch, not only batch 1). The page uses the code's label.

## Code and docs that disagree in a way that looks like a bug (for the user)

- Question, not a bug found: `part_sheet/job.py`, `_level_work`: only a `BaseException` in the work sets a run to
  `stopped`. If the backend process stops while a run is `running` (a crash, not a Stop), the log stays `running`, and
  the history would show "The AI is writing" for a run that is not. Not checked whether something resets such a log at
  start-up (see "Not checked"). Please confirm.

## New terms for the glossary (Phase 20)

- **the log** (of a run): `ai-runs/<id>.json`, the request, the plan and each batch's conversation, written as it goes.
- **waiting** (a run's state): batch 1 is on the sheet, the others are not; **Go on** writes them.
- **an answer** (to the AI): the user's words about one batch; kept with the batch (`answers`).
- **Write this batch again**: the one batch written again with the answer; the sheet changes only when the check accepts.
- **record-N**: the id of a level run made before the log (only its record entry; no log to open).

## Not checked

- No run in the app (per the rules). The behaviour is from reading the code, the summary's keys, and the React labels.
- Whether a backend restart resets a log left at `running` (see the bug note above). Not found in the files read.
- The four `sheetApi` methods (`aiRuns`, `aiRun`, `continueRun`, `runBatchAgain`, `api/sheet.ts` lines 665 to 676) were
  read by grep, not in full.
- `check-names.py` on `paths-and-data.md`: six names are missing (`session.json`, `/hf/hub`,
  `scripts/migrate/to_database.py`, `AITU_DATA_DIR`, `bench_pieces.py`, `bench_payloads.py`). All six are in older
  lines of that page, not in my line (the `ai-runs/` line). Not mine; left as they are.
- `check-names.py` on `run-history.md` and `ai-levels.md`: no missing name.
- `check-names.py` also flags the path `../documentation/services/backend/ai-levels.md` in E13.5. It is a path relative
  to `context/` (the target file's folder), not to this report, so it is correct there.
- `check-links.py` after the edits: 544 files, one broken link, in `05-implementation-phase-8.md` line 74 (another
  phase's report, written in parallel). Not mine; left as it is.

## Pending edits for shared files

- **E13.1** `documentation/services/backend/endpoints.md`, section 1 (the table), after the row
  `POST | /sheet/{uuid}/llm/level-copy` and before `GET | /sheet/{uuid}/chords`: add these four rows.

  > | GET | `/sheet/{uuid}/llm/runs` | Implementation 04-5 (2026-10-31): the history of the AI runs of the part, the latest first, each in short (its request, its batches and their states, its cost). A level run made before the log comes from the record: `id` `record-N`, `log` `false`. 404 when the part has no notes. See [run-history.md](../../../context/ai/run-history.md). |
  > | GET | `/sheet/{uuid}/llm/runs/{run_id}` | Implementation 04-5: one run of the history whole: the request, the plan, the rules, and each batch's conversation (its messages, the check's refusals, `explain`, `rules`, `answers`). 404 "No such run." when the run has no log. |
  > | POST | `/sheet/{uuid}/llm/runs/{run_id}/continue` | Implementation 04-5: **Go on with the other batches** of a level run that waits after batch 1: a job, one step of undo. 202 `{jobId, status}`. 403 on a sheet the user cannot change; 404 no such run; 409 the AI works on the part, or the run is not waiting. |
  > | POST | `/sheet/{uuid}/llm/runs/{run_id}/batches/{k}/again` | Implementation 04-5: **Write this batch again** with the user's answer, body `{words}` (1 to 1000 characters); `k` counts from 0. A job, 202 `{jobId, status}`, one step of undo; the sheet changes only when the check accepts the reply. 400 empty words; 403; 404 no such run, or no conversation for `k`; 409 the AI works on the part. |

- **E13.2** `documentation/services/frontend/components.md`, section 3 (the table), after the row
  `` `frames/AiRunPanel.tsx` `` (the panel of an AI run, 2026-10-30): add these two rows.

  > | `frames/AiHistoryPanel.tsx` | The history of AI runs (implementation 04-5, 2026-10-31): opened from the sheet's ⋯ menu (**History of AI runs**) or from the run panel (**History**); a panel at the right, the runs latest first (the state, the batches written, the cost); a click opens one run; a run without a log shows its plan; `data-ai-history`, `data-history-run`, `data-ai-run-old` |
  > | `frames/AiRunDetail.tsx` | One AI run of the history (implementation 04-5): its title and the user's words, the rules the AI follows (`data-run-rules`), each batch (`BatchBlock`: its number in its colour, its time, its status, the explanation `data-run-explain`, the rules, the check's refusals `data-run-refused`, the user's answers `data-run-answer`), the answer box and **Write this batch again** (`run-again-N`), and **Go on with the other N batches** (`run-continue`) while it waits; `data-ai-run`, `data-state`; the run panel shows it compact |

- **E13.3** the same file, the row `` `frames/AiRunPanel.tsx` ``: after the words `**Stop**, then **Revert** and **Close**;`, insert:

  > a run of two batches or more waits after batch 1 (the title **Check batch 1**, the detail of `AiRunDetail` under the batches); after the run, **History** (`ai-run-history`) opens the history on the run;

- **E13.4** `context/00-index.md`, section "The AI (`context/ai/`)", after the row `| [ai/level-run.md](ai/level-run.md) | ...`: add

  > `| [ai/run-history.md](ai/run-history.md) | The history of AI runs: the log of each level run, the first batch first, an answer to the AI, a batch written again, Go on |`

- **E13.5** `context/00-index.md`, the row for `ai-levels.md` (the path `../documentation/services/backend/ai-levels.md`, about line 300): add ", the history of runs (the log)" to its description, after "the level run".

- **E13.6** `documentation/services/README.md`, the row of `ai-levels.md` (about line 15): add ", the history of runs (the log)" before the closing `|`, after "the level run".

- **E13.7** `context/ai/README.md`:
  (a) the table row **The history of runs**, last cell: replace `` `run-history.md` (Phase 13) `` by `[run-history.md](run-history.md)`.
  (b) in the list of pages, after the line `- [level-run.md](level-run.md): ...`, add:

  > `- [run-history.md](run-history.md): the history of AI runs: the log, the first batch first, an answer to the AI, a batch written again, Go on.`

  (c) delete the closing paragraph that begins "The other pages of the folder are written by the phases of the documentation refresh" (it is out of date: every page of the folder now exists).

- **E13.8** `context/ai/level-run.md` (Phase 12's page; not a file of this phase): in step 5 of "What the run does, in order", replace the code span `` `run-history.md` `` by the link `[run-history.md](run-history.md)` and delete ", in this folder" after it.

## Left for later phases

- Phase 20: the glossary terms above; the closing of the implementations journal (04-3 Phase 6 and 04-5 task 5.2 are
  closed by this refresh, as `04-context.md` section 8 says).
- Phase 20: `context/ai/README.md` and the core README's section 11 (the AI) may still name the old run kinds; not checked
  here.
