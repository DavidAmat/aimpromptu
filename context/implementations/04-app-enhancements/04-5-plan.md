# 04-5: The left hand follows the chosen pattern: plan

The brief, with the user's request and the evidence, is [`04-5-prompt.md`](04-5-prompt.md). The status of every task
is in [`04-5-checklist.md`](04-5-checklist.md). Each phase writes `04-5-implementation-phase-N.md`. The guidelines:
[`guidelines-implementation-plan.md`](../../guidelines/guidelines-implementation-plan.md) and
[`guidelines-communication-with-user.md`](../../guidelines/guidelines-communication-with-user.md).

# 1. Context

A level run of **Enhance with AI** writes a hand again at a level (easy, medium, hard), with the patterns the user
ticks in the gallery. On copies of 20 de Enero, the left hand did not follow the patterns (`left easy 5`, then
`left easy 1`): the AI declared `keep` for most of the hand.

The cause is confirmed (brief section 3). On 2026-10-30, the user asked that a level never makes a passage harder:
where the left hand plays at most 3 keys inside an octava, the app marks the stretch simple, and the prompt and the
check keep its notes. Each level copy was made from the copy before, so the simple share of the left hand grew run
after run (36 % to 81 %), and a held triad was refused where the sheet plays single notes.

# 2. The user's answers (2026-10-31)

| Point | Answer |
|---|---|
| The branch | The work of 04-3 is committed and pushed (`433a39a` on `feat/04-3-enhance-dialog`). This work is on `feat/04-5-pattern-strictness`, made from it; both go to `master` after the user's ok. |
| Strict and Suggested | Each pattern ticked gets **Suggested** (default) or **Strict**. Strict: every chord of the hand plays the strict pattern (the user's words joined to it); the simple-stretch rule and the onset rules are lifted for that hand; `keep` is refused. Suggested: the simple-stretch rule stays, but a simple stretch may take a pattern when it is not harder (notes of the chord, no more onsets). |
| The rules between batches | The plan writes one **rule** per pattern; batches receive the rules and may add some. A run of several batches always **writes the first batch first and waits**: the user sees it on the sheet with the AI's explanation and rules, answers the AI and writes batch 1 again, or goes on with the other batches. |
| Writing a batch again | Only that batch, from the history, with the user's answer. |
| The tests | A few real runs on temporary copies of 20 de Enero: Strict easy 1 with the user's words, Suggested easy 1, Strict easy 5. At most $2 in total; ask before going over. |

# 3. Design

## 3.1 Strict and Suggested

- The request gets `strict: list[str]`, the refs ticked as Strict (a subset of `patterns`).
- A hand with a strict pattern: the plan may use only its strict refs for that hand (no `keep`, `free` or another
  ref); every batch declares the hand's strict refs over all its columns; the check lifts, for that hand, the
  simple-stretch rule, "more onsets than now" and `RHYTHM_SHARE`. The melody, the harmony, the grid and the level's
  limits (notes per column, span, hand motion) stay.
- Suggested (a hand with no strict pattern): as today, but a simple stretch declared with a pattern (not `keep`) may
  play other notes of the chord and chords where it played single notes, with no more onsets than now.
- The prompt says it in plain words: a strict pattern is played on every chord of the hand, the same way through the
  whole song; the user's words may change its shape (the user's example: on easy 1, "first a low note Fa3 as a
  blanca, then Fa4-La4-Do5 as a blanca"), and then the changed shape is the strict one.

## 3.2 Both hands, the rules and the explanations

- **Both hands in the plan.** The summary of the song shows, per stretch, the melody line of the right hand (its top
  notes, compact), also when the run rewrites the left hand only. Batches already show the other hand ("fixed") and
  a look-ahead of both hands.
- **The rules.** The plan answer adds, after the sections, one line per pattern it uses:
  `rule left easy 1: on each chord, the root in octava 3 as a blanca, then the triad in octava 4 as a blanca`
  (which notes by their role, octava, figures, order; the user's words joined). Every batch gets "The rules of this
  run" (the plan's and the ones earlier batches added, with where each came from) and must follow them; a batch may
  add `# rule: ...` for a new kind of passage (and the passage, when it comes again, is written the same way).
- **The explanation.** Every batch answer has one to three `# explain: ...` lines in very simple words: what the AI
  did, why, and what it did not do. The check asks for at least one.
- Level prompts version 4.

## 3.3 The history of the runs

- Every level run writes a log in the part's folder, `ai-runs/<run id>.json`, after the plan and after each batch:
  the request (level, hands, patterns, strict, words, model), the plan (prompt, replies, the check's refusals, the
  sections, the rules), and per batch its frames, state, the conversation (prompts and replies), the check's
  refusals, the explanation, the rules added, the declared lines, the target (F1 text) and the user's answers. The
  system prompt is stored once.
- Routes: `GET /sheet/{uuid}/llm/runs` (the runs, latest first, short) and `GET /sheet/{uuid}/llm/runs/{id}`.
- Older runs have only the record's `levels` entry (no log): the history shows them from it (plan, declared).

## 3.4 The first batch first

- A level run of 2 batches or more stops after the plan and batch 1: batch 1 is stored on the sheet (one step of
  undo), the log's state is `waiting`, and the run panel shows the explanation, the rules, an answer box,
  **Write batch 1 again** and **Go on with the other N batches**.
- `POST /sheet/{uuid}/llm/runs/{id}/continue`: a job writes the other batches with the stored plan and rules (one
  step of undo).
- `POST /sheet/{uuid}/llm/runs/{id}/batches/{k}/again` with the user's words: a job continues that batch's
  conversation ("The user's answer: ..."), checks the answer against the stored target, and puts it on the sheet in
  place of the batch (one step of undo, "Batch k written again with AI"). Its rules replace the batch's rules in the
  log. Any batch of a run that has a log can be written again from the history.

## 3.5 The page

- The gallery: a ticked pattern shows **Suggested | Strict** (Suggested by default).
- The run panel: the waiting state of 3.4.
- **The history of AI runs**: a sheet button (in `sheetButtons`) opens a panel at the right, the runs latest first;
  a click opens a run: the plan, the rules, each batch with its explanation, the check's refusals and an answer box
  with **Write this batch again**.

# 4. Phases

One branch, `feat/04-5-pattern-strictness`. The binding rules of the brief hold: no backend `.py` edit while an AI
job runs; temporary copies only; pytest on the CPU; links as `http://ubuntu:<port>`.

## Phase 1: Backend: Strict and Suggested, the rules, the explanations, the log

Code of 3.1, 3.2 and 3.3 (`levels.py`, `prompt/levels/`, `job.start_level`, a new `part_sheet/runs.py`, the routes),
with tests on stand-ins of the AI (`test_sheet_levels.py`, `test_sheet_levels_app.py`).

## Phase 2: Real runs of the prompt (scripts, no page)

On temporary copies of 20 de Enero (`946c21f2` and `d6211999`), from a script: Strict easy 1 with the user's words,
Suggested easy 1, Strict easy 5. Draw each result and compare it with the request, zoomed in; read the logs (the
explanations, the rules, the refusals); change the prompt and run again. At most $2 with Phase 5.

## Phase 3: Backend: the first batch first, continue, write a batch again

Code of 3.4, with tests on stand-ins.

## Phase 4: The page

Code of 3.5; `check:enhance-dialog`, `check:ai-run-panel` and a new `check:ai-history`.

## Phase 5: A real run in the app, the documentation

One real run on a temporary copy through the page (first batch, an answer, batch 1 again, go on). Update
`04-context.md`, the core README, `endpoints.md`, `components.md`, the links check. The user's review, then the merge.

# 5. Changes made by the phases

Each phase adds a dated paragraph here.

**Phases 1 to 4** (2026-10-31, one session,
[`04-5-implementation-phases-1-to-4.md`](04-5-implementation-phases-1-to-4.md)). The order changed: the real runs of
Phase 2 came before the page, while no backend edit could stop them, and the page was built during the runs. Two
small additions: the reader of an answer accepts a fence with trailing spaces (Terra wrote "``` " several times and
lost a reply each time), and the history also lists the level runs stored before the logs (from the record). The
runs showed two points for the user: the octave numbers of the user's words (easy 1 named "Fa4-La4-Do5" is drawn
F3-A3-C4), and chords that change every 1 or 2 negras, which a shape of two blancas does not fit. Run D fixed the
second point with one answer to the AI. Real runs cost about $0.47 of the $2.
