# 04-5: Phases 1 to 4: report

Phases 1 to 4 of [`04-5-plan.md`](04-5-plan.md) were done in one session (2026-10-31), on
`feat/04-5-pattern-strictness` (made from `feat/04-3-enhance-dialog` at `433a39a`, which was committed and pushed
first, the user's answer). The results of the real runs are at `http://ubuntu:8097/gallery/04-5/`.

# 1. The cause, confirmed

The run of 10-31 09:22 planned `S1 f5-f2187 L=keep | The left hand is marked simple throughout`. The check refused a
held triad in a simple stretch ("chords where the sheet plays single notes"). The simple share of the left-hand
columns grew from copy to copy (`d6211999` 36 %, `7b9a41e4` 64 %, `0df15e84` 67 %, `b13cbcde` 85 %, `946c21f2` 81 %),
because each level copy was made from the copy before. Brief section 3 has the details.

# 2. What was built

## 2.1 Backend (`sheet/llm/levels.py`, prompt version 4)

- `STRICT`, `strict_refs`. `system_prompt(..., strict)` marks each pattern "(Strict)" or "(Suggested)" and adds
  "Strict for the left hand: ...". `shared.md` has two new sections, "Strict and Suggested" and "The rules of the run
  and your explanations", plus the `# explain:` line in the answer example.
- `song_summary(..., strict_left)` shows `R melody: ...` for every stretch (at most `SUMMARY_MELODY = 24` notes), also
  for a run of the left hand only. It drops `L simple (keep)` when the left hand is Strict.
- `plan_prompt(..., strict)`: a section "Strict patterns" and the request for one `rule <ref>: ...` line per pattern.
  `read_plan(..., strict, rules=True)` refuses a non-Strict ref for a Strict hand and a missing rule. `read_rules`
  and `Rule` (text, source `plan` or `batch N`, ref).
- `batch_prompt(..., rules, strict)`: "The rules of this run", a "Strict: ..." section per Strict hand, the simple
  stretches only for a hand that is not Strict (with the Suggested way out), and `# explain:` / `# rule:` in the
  answer. `read_declared` reads `explain` and `rules`.
- `check_level(..., strict, explain)`. A Strict hand declares only its Strict refs over all its columns (within 2
  frames); the simple-stretch, onset-count and `RHYTHM_SHARE` rules are lifted for it. Suggested: a simple stretch
  covered by a declared pattern (not `keep`) may play other notes of its chord (the app's `c.tones`, or the stretch's
  own pitch classes) and chords where it played single notes. It still may not have more onsets. `explain=True`
  asks for at least one `# explain:` line (`write_level` and `write_again` pass it).
- `Talk` (one conversation: messages, status, errors, target F1, explain, rules, declared) and `_conversation` (a
  refused last reply is not stored twice). `write_level` keeps `run_rules` (the plan's, then each accepted batch's
  `# rule:` lines) and passes them to every batch. It also takes `on_talk`, `written_before`, `done_before`,
  `first_index` and `count` (a run that goes on after batch 1).
- `write_again`: it continues a batch's conversation with `prompt/levels/answer.md` and the user's words, then checks
  the reply against the stored target, with the chords of the sheet "before" (the sheet now with the batch's hand
  put back as its target).
- `frames._block` accepts a fence with trailing spaces ("``` \n"). Terra wrote this several times, and each time cost
  one refused reply ("a frames line starts with f<column>, not '```'"). The fallback stops at the next fence.

## 2.2 Backend (`part_sheet`)

- `runs.py`: `ai-runs/<12 hex>.json` in the part's folder. `create`, `save` (atomic), `update` (put a Talk), `load`,
  `listing`. The listing shows the logs, plus the record's `levels` entries without a log (`record-N`, with their plan
  and declared lines), latest first.
- `job.start_level(..., strict, first)`. `first` (the routes pass it): a run of 2 batches or more writes the plan and
  batch 1, stores it ("..., batch 1"), and sets the log to `waiting` (`waiting` in the summary).
- `job.continue_level` and `_level_work`, the job shared with `start_level`. It reads the plan and rules from the log
  and the batches written from the sheet, and puts the first snapshot back in `_meta` (Revert goes back to before
  batch 1). The step is "..., the other batches".
- `job.again_batch`: one batch with the user's words. The step is "Batch k written again with AI". The log gets the
  new conversation, `answers`, and the batch's rules replaced. A refused answer keeps the earlier explanation, and the
  batch on the sheet does not change.
- Routes: `GET /sheet/{uuid}/llm/runs`, `GET .../llm/runs/{id}`, `POST .../llm/runs/{id}/continue`,
  `POST .../llm/runs/{id}/batches/{k}/again` (`words` 1 to 1000 characters). `LevelRequest.strict`.

## 2.3 Page

- `PatternCatalog.tsx`: a ticked pattern shows **Suggested | Strict** (`data-strictness`; the click does not untick).
  `EnhanceDialog.tsx` sends `strict`, and the line of the patterns says "(Strict)".
- `AiRunDetail.tsx`: one run with the rules, each batch's explanation, rules, refusals and answers, an answer box with
  **Write this batch again**, and **Go on with the other N batches** while it waits. `runTitle` is in `patterns.ts`.
- `AiRunPanel.tsx`: at the end of a run with a log, the detail replaces the plain list of batches. The title is
  "Check batch 1" while the run waits. **History** opens the history on the run. The count comes from the summary.
- `AiHistoryPanel.tsx`: opened from `⋯` > **History of AI runs**. It lists the runs (latest first); a click opens one,
  and a run without a log shows its plan.
- `useFramesSheet`: `RunSummary.run` and `waiting`, and `reloadSheet` (a job started from a panel).

# 3. Tests and checks

- Backend: `test_sheet_levels.py` (Strict lifts the rules and covers the hand; Suggested lets a simple stretch take a
  pattern; the plan of a Strict hand and its rules; an answer must explain, and its rules reach the next batch) and
  `test_sheet_levels_app.py` (the log and the routes; batch 1, an answer, batch 1 again, go on, Revert to before
  batch 1). The full suite passes on the CPU in the backend container, without `test_transcription_transkun.py`.
  Note: `make test-backend` runs a fresh image, which has no `openai` (2 known failures). The running container has it,
  so the suite was run with `docker exec`.
- Browser: `check:enhance-dialog` (3 new steps for Strict), `check:ai-run-panel`, and the new `check:ai-history`
  (11 steps on a faked run). All pass.

# 4. The real runs (GPT-6.1 Terra, 4 batches, on temporary copies)

| Run | Copy of | Request | Result | Cost |
|---|---|---|---|---|
| A | `946c21f2` | easy 1 Strict, the user's words as written ("Fa3, then Fa4-La4-Do5") | The plan uses easy 1 everywhere; every batch is accepted; the triads are an octava above the pattern's drawing (F3-A3-C4) | $0.072 |
| A2 | `946c21f2` | the same, with the register named (Fa2, then Fa3-La3-Do4) | The right register; on chords of 2 negras the low note is alone | $0.078 |
| B | `d6211999` | easy 1 Suggested, no words | Held triads over the busy left hand, the simple stretches kept | $0.096 |
| C | `d6211999` | easy 5 Strict, no words | Low note and rocking corcheas on almost every chord | $0.107 |
| D | `946c21f2` | as A2, through batch 1 first, an answer, batch 1 again, go on | The answer became a rule, and batches 2 to 4 followed it | $0.112 |

Total about $0.47 of the $2 the user allowed. The temporary copies (A `47999e53`, A2 `952d4480`, B `8e1c50a8`,
C `07b1c431`, D `3ed5bde6`) are kept until the user has looked at the pages; delete them after.

Findings:
1. **The octaves of the user's words.** The user named the chord of easy 1 "Fa4-La4-Do5", but the app draws it as
   F3-A3-C4. The AI follows the words literally. This is a decision for the user (one numbering, or a prompt rule).
2. **Chords that change every 1 or 2 negras.** The app's chords of 20 de Enero change often, so a shape of two
   blancas does not fit. The AI then plays the low note alone. The answer of run D fixed it for the whole song. The
   loop works as the user asked.
3. The easy limits (`left_reach` 24 within two negras, `left_moves` 0.75) refuse about one reply per batch for "low
   root, then triad", and the AI then raises a root an octava. This is expected.

# 5. Open for Phase 5

- The documentation (`04-context.md` or a 04-5 context, the core README, `endpoints.md`, `components.md`), the links
  check, the user's review, and the merge of both branches.
