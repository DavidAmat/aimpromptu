# The history of AI runs: the log, the first batch first, an answer to the AI, a batch written again, Go on

> Context: [README.md](README.md). The code is in
> [documentation/services/backend/ai-levels.md](../../documentation/services/backend/ai-levels.md) (section 9: the log,
> the routes, `write_again`) and [paths-and-data.md](../../documentation/services/backend/paths-and-data.md) (the file
> of the log). The run itself: [level-run.md](level-run.md).

Every **level run** keeps a log of what it asked and what the AI answered. The user reads the log in the **History of
AI runs**. From there the user can answer the AI about one batch, write that batch again, or go on with the batches
that were not written yet. A level run of two batches or more writes its first batch and then waits for the user.

Only level runs have a log. A whole run, a stretch and Simplify do not appear in the history.

## 1. The first batch first

A level run of **two batches or more** does not write everything at once. It writes the plan and the first batch,
stores them on the sheet as one step of undo, and waits.

- The sheet shows batch 1 as the other batches show it: with its colour and its number.
- The run panel (**AiRunPanel**) says **Check batch 1**. It shows the AI's explanation and rules for batch 1, and the
  answer box of the batch.
- The run's state in the log is `waiting`. The job's summary says `waiting: true`.
- The user checks batch 1 on the sheet. If it is good, the user presses **Go on with the other N batches**.
- If the user presses **Revert** while the run waits, or after **Go on**, the sheet goes back to the state it had before
  batch 1 (the first snapshot of the part is kept for this).

A run of one batch has nothing to wait for. It is written in one go and is `done`.

## 2. The states of a run

The log's `state` is one of these. The history shows them in plain words:

| `state` | When | The history says |
|---|---|---|
| `running` | The job works on the run | The AI is writing |
| `waiting` | Batch 1 is stored and the other batches are not written | Waiting for you after batch 1 |
| `done` | The run ended with its batches written | Finished |
| `stopped` | The user pressed **Stop**, or the job ended with an error | Stopped |
| `failed` | The run ended with no batch written | Not written |

The batches have their own status: `ok` (**Written**), `failed` (**Kept as it was**: the check refused the answer, so
the sheet keeps the earlier notes), `error` (**Not written**: an error stopped the batch), and `open` (**Being
written**).

## 3. The log

- **Where.** In the part's folder, in `ai-runs/`: `<project>/parts/<partId>/ai-runs/<run id>.json`. The run id is 12
  hexadecimal characters. Each run has one file.
- **When.** The log is written when the run starts, after the plan, after each batch, and at the end. Each write goes to a
  temporary file that then replaces the log, so a half-written log is not read. A Stop leaves the log with the batches
  written before it.
- **What it holds.** The request (the level, the hand, the patterns, the Strict refs, the words, the model, the
  windows, the guide of the chords), the system prompt (once for the run), the plan, the batches, the rules of the run,
  the cost (`usd`) and the number of requests.
- **Each conversation** (the plan, and each batch) is the same kind of record: `k` (the batch's number from 0; the plan
  has `k` -1), `start` and `end` (the frames), `status`, `messages` (the prompts and the AI's replies), `errors` (the
  check's refusals, one list per reply), `target` (the notes of the batch as the sheet had them before the run, in F1
  text), `explain`, `rules`, `declared`, and `answers` (the user's answers, each with its time).

The code that writes and reads the log is `part_sheet/runs.py`. Its functions: `create`, `save`, `update`, `load`,
`listing`.

### Runs made before the log

A level run made before the history has no log. It has only its entry in the record's `levels` list. The history
lists it with the id `record-N`, shows its plan and what it declared, and says that the run was made before the
history kept the AI's explanations. Such a run cannot be opened as a log, so no batch of it can be written again.

## 4. The history

**The button.** The sheet's ⋯ menu has **History of AI runs** when the user may run the AI on the sheet. After a run,
the run panel has **History** (it opens the history on that run).

**The list.** The panel opens at the right of the sheet. The runs come the latest first. Each row shows the run's
title, the user's words, the date, the state (the table in section 2), how many batches are **Written** of all the
batches, and the cost. If there is no run, it says **No AI run on this sheet yet.**

**One run.** A click opens the run. The panel shows:

- the title, the user's words, the date, the cost and the number of requests;
- **The rules the AI follows**: the rules of the run, each with the reference of its pattern when it has one;
- each batch: its number (in its colour), its time, its frames, its status, the AI's explanation (`explain`, in simple
  words), the rules that batch added (**Rule for the next batches**), the check's refusals (**The check refused N
  answers of the AI**), and the user's answers (**You: …**);
- under each batch, an answer box, **Answer the AI: No, I want this…**, and the button **Write this batch again**.
- while the run waits, **Go on with the other N batches** at the foot.

The arrow at the top goes back to the list.

## 5. An answer to the AI, and Write this batch again

The user types an answer about one batch, for example "No, I want this". Up to 1000 characters. The button is enabled
when no other job runs on the part, the batch is not being written, and the run is not running.

The job (`again_batch`) does this:

1. It takes the batch's conversation from the log. A batch without a conversation (no target, no messages) cannot be
   answered: the request fails with 404.
2. It takes the sheet as it stood before this batch was written: the current sheet, with the batch's hands replaced by
   the batch's target.
3. `write_again` sends the conversation on: the batch's earlier messages, then the answer. The prompt is
   `prompt/levels/answer.md`: the user read the batch on the sheet and answers; write the whole batch again, with the
   `# explain:` lines and a `# rule:` line for each decision the next batches must follow.
4. Each reply is checked as a batch is checked in the run (the same check, the same limits). A refused reply goes back
   to the AI with the problems. Up to three replies in all.
5. **If the check accepts the reply**, the batch on the sheet is replaced by the new one, in its stretch of the two
   hands. This is one step of undo, labelled **Batch k written again with AI**. The batch's explanation and rules are
   the new ones. The rules that came from this batch are replaced in the run's rules (their source is `batch N`, N the
   batch's number).
6. **If the check refuses every reply**, the sheet does not change. The log keeps the earlier explanation, the earlier
   rules and the earlier status. The answer and the new conversation are kept in the log, and the summary says
   `level: failed`.

In both cases the user's answer is kept with the batch (its `answers` list). The cost and the requests of the job are
added to the run's totals. If the run is waiting, it keeps waiting.

## 6. Go on with the other batches

**Go on with the other N batches** starts the job `continue_level`. It writes the batches that the run has not
written yet, in their order. Each batch sees the batches before it, and the run's plan and rules. The job is one step
of undo, labelled `…, the other batches`. The run's state goes to `running` while the job works, and then to `done`,
`failed` or `stopped`: this step writes the rest, so it does not wait again.

It works only when the run is `waiting`. Another run, or a run that is not waiting, is refused (409).

## 7. The routes

All four are in `api/sheet.py`, under `/sheet/{audio_uuid}/llm/runs`. Each checks that the part has notes (else 404).

| Method and path | What it does | Answers |
|---|---|---|
| `GET /llm/runs` | The list of the runs, the latest first, each in short (its request, its batches and their states, its cost) | a list |
| `GET /llm/runs/{run_id}` | One run whole: the request, the plan, the rules, each batch's conversation | the log; 404 when there is no log for the id |
| `POST /llm/runs/{run_id}/continue` | **Go on with the other batches** | 202 `{jobId, status}`; 403 when the sheet cannot be changed; 404 when there is no such run; 409 when the AI works on the part or the run is not waiting |
| `POST /llm/runs/{run_id}/batches/{k}/again` | **Write this batch again**, body `{words}` (1 to 1000 characters); `k` counts from 0 | 202 `{jobId, status}`; 400 when the words are empty; 403; 404 when there is no such run or no conversation for batch `k`; 409 when the AI works on the part |

The job's summary for an answer has `again` (the batch's number), and `waiting` when the run waits.

## 8. What the history does not do

- An old run without a log is read only. Its plan and declared lines are the whole of what it shows, and no batch of it
  can be answered or written again.
- A reply that the check refuses three times is not on the sheet, and the sheet keeps the earlier batch (section 5).

## Where to look deeper

- [level-run.md](level-run.md): the run itself: the plan, the rules, the batches, the check, Strict and Suggested
- [levels.md](levels.md): what a level is, the catalog of patterns, the chords of the song
- [documentation/services/backend/ai-levels.md](../../documentation/services/backend/ai-levels.md): section 9, the code of
  the log, the routes and `write_again`
- [documentation/services/backend/paths-and-data.md](../../documentation/services/backend/paths-and-data.md): the
  `ai-runs/` folder of a part
- [README.md](README.md): the AI in the app, the kinds of run, the AI mark
