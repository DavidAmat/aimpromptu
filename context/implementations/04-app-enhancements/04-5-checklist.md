# 04-5: The left hand follows the chosen pattern: checklist

The plan is [`04-5-plan.md`](04-5-plan.md), the brief [`04-5-prompt.md`](04-5-prompt.md). One branch,
`feat/04-5-pattern-strictness`. Status letters: `[x]` complete, `[p]` in progress, `[b]` blocked, `[c]` cancelled,
`[ ]` not started.

## Decisions

- [x] The first discussion (user, 2026-10-31): plan section 2.
- [x] Phases 1 to 4 in one session: [`04-5-implementation-phases-1-to-4.md`](04-5-implementation-phases-1-to-4.md).
- [ ] The user looks at the test runs (`http://ubuntu:8097/gallery/04-5/`) and decides the octave numbering of the words.

# [x] Phase 1: Backend: Strict and Suggested, the rules, the explanations, the log

- [x] 1.1 `strict` in the request, `run_refs`, the plan and the check (plan 3.1).
- [x] 1.2 Suggested: a simple stretch may take a pattern when not harder.
- [x] 1.3 The melody in the summary; the rules in the plan; the rules and `# explain` in the batches (plan 3.2).
- [x] 1.4 The log `ai-runs/<id>.json` and the routes (plan 3.3).
- [x] 1.5 Tests on stand-ins; all backend tests pass on the CPU.

# [x] Phase 2: Real runs of the prompt

- [x] 2.1 Temporary copies of 20 de Enero; a script that runs a level and draws it.
- [x] 2.2 Strict easy 1 with the user's words; Suggested easy 1; Strict easy 5.
- [x] 2.3 Prompt changes from what the runs show; the cost so far (at most $2).

# [x] Phase 3: Backend: the first batch first, continue, write a batch again

- [x] 3.1 A run of 2 batches or more waits after batch 1.
- [x] 3.2 `continue` and `batches/{k}/again`; tests.

# [x] Phase 4: The page

- [x] 4.1 Suggested | Strict on a ticked pattern.
- [x] 4.2 The run panel waiting after batch 1.
- [x] 4.3 The history of AI runs; the browser checks.

# [ ] Phase 5: A real run in the app, the documentation

- [p] 5.1 One real run through the page on a temporary copy (run D did the whole loop through the API; the page itself is checked with a faked run).
- [ ] 5.2 The documentation; the links check; the user's review and the merge.
