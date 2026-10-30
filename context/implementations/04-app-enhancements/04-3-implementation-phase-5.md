# 04-3 · Phase 5: other AI models for the level runs (OpenAI), judged against Sonnet 5.5

Status: built on 2026-10-30 on branch `feat/04-3-phase-5` (from `master` `113c2cb`); the 16 cases run and judged, the
report served; the user chose GPT-6.1 Terra at `medium` for the level runs and the app uses it (section 9).

Audience: the agents of this plan (this phase when the user answers, and Phase 6). Technical.

# 1. Prices and model ids (task 5.1)

Sources, read on 2026-10-30: OpenAI's pricing page (`developers.openai.com/api/docs/pricing`), the model pages
(`.../docs/models/gpt-6-luna`, `gpt-6.1-terra`, `gpt-6.1-sol`), the prompt caching guide
(`.../docs/guides/prompt-caching`); Anthropic's prices from the `claude-api` skill (cached 2026-10-06) and
`sheet_llm.PRICES`. The ids were confirmed with `client.models.list()` and the user's key (the list also has
`gpt-6-astra` and `gpt-6-sol`).

| Model | API id | Largest effort | Input | Cached input (read) | Cache write | Output (reasoning included) |
|---|---|---|---|---|---|---|
| Sonnet 5.5 (baseline) | `claude-sonnet-5-5` | `max` (the app uses `high`) | $2.00 | $0.20 | $2.50 (5 min) | $10.00 |
| Opus 5.5 (the judge) | `claude-opus-5-5` | `max` | $4.00 | $0.20 | $5.00 (5 min) | $20.00 |
| GPT-6 Luna | `gpt-6-luna` | `max` | $0.10 | $0.01 | $0.125 (30 min) | $0.50 |
| GPT-6.1 Terra | `gpt-6.1-terra` | `max` | $1.00 | $0.05 | $1.25 (30 min) | $5.00 |
| GPT-6.1 Sol | `gpt-6.1-sol` | `max` | $2.00 | $0.10 | $2.50 (30 min) | $10.00 |

US dollars per million tokens, Standard tier, prompts up to 272K tokens (above: input and cache x2, output x1.5;
never reached here). Effort values of the three OpenAI models: `none` (not Sol), `low`, `medium` (default), `high`,
`xhigh`, `max`.

**OpenAI's prompt caching for GPT-5.6 and later** (GPT-6 and GPT-6.1 included), which differs from what the plan
assumed (the older rules: automatic, prefix in blocks of 128 tokens, free writes):

- Smallest cached prefix: 1,024 visible tokens. The whole rendered prefix must match.
- `prompt_cache_options.mode`: `implicit` (one breakpoint at the end of the last eligible message, every request) or
  `explicit` (breakpoints set on content parts with `prompt_cache_breakpoint: {"mode": "explicit"}`, up to four writes
  per request; no breakpoint, no caching). The top-level `instructions` cannot hold a breakpoint, so the system prompt
  goes in a developer message.
- **Writes are billed**: 1.25x the input price for 30 minutes (2.5x for 12 hours); reads 0.1x (0.05x for Terra and
  Sol). The tokens after the last breakpoint are plain input.
- `prompt_cache_key` is optional for these models (accounting, and no probing across users); `ttl` 30 min by default,
  a minimum lifetime.
- Usage: `input_tokens_details.cached_tokens` (reads) and `cache_write_tokens` (writes); plain input =
  `input_tokens - cached - written`. Reasoning: `output_tokens_details.reasoning_tokens`, billed as output.

# 2. The OpenAI client (task 5.2)

- `aitu_backend/sheet_llm.py`: `OpenAIComplete(model=, effort="max", cache_key=, ...)` with the contract of
  `ClaudeComplete` (`complete(system, messages) -> text`, `calls` of `Call`, `usd`); `Call.reasoning_tokens` (new,
  default 0); `OPENAI_PRICES`, `openai_price`. Responses API, streamed (`responses.stream(...).get_final_response()`),
  `store=False`, `max_output_tokens` 128,000, timeout 30 min.
- **Caching**: explicit mode, two breakpoints: after the system prompt (the developer message, identical in every
  request of a run: `levels.system_prompt`) and at the end of the last user message (a reply after a rejected answer
  then reads the whole conversation before it). An assistant turn sent back is its text only (OpenAI drops the
  reasoning items of earlier turns anyway). Every request of one client sends the same `prompt_cache_key`.
- The key: `OPENAI_API_KEY` of the environment, else read from the repository's `.env` (the container started before
  the user added the key; it is never printed or written elsewhere).
- A refusal (a `refusal` content part) raises `SkipWindow`, as Claude's; an answer cut by `max_output_tokens` is
  returned as it is (the check refuses it) with `stop_reason` `incomplete:max_output_tokens`.
- Dependency `openai>=3.41.0` in `pyproject.toml` and `uv.lock`; installed in the running container with `uv pip`.
- Tests: `tests/test_sheet_llm_openai.py` (3, a stand-in for the API): the body (developer message first, the two
  breakpoints, the key, `store`), the costs of a write and of a read, a refusal and a cut answer, the prices.
- The app does not use the client.

# 3. The cache test, with GPT-6 Luna (task 5.3)

The scratch runner `harness.py` (in `/home/app/04-3-phase-5/`, on the host `/mnt/ssd2/aimpromptu/home/04-3-phase-5/`)
runs one case with one model through `levels.write_level(span=...)`, as the app runs a range: the plan request of the
passage, then its batches with the check and at most 3 replies. The cache test: 99 Red Balloons f33-f1286 (the app
cuts it into 3 batches) at medium, GPT-6 Luna at `max`.

| Request | Plain input | Written | Read | Output (reasoning) | Seconds | USD |
|---|---|---|---|---|---|---|
| Plan | 3 | 8,122 | 0 | 6,293 (6,204) | 83 | 0.0042 |
| Batch 1, first reply | 3 | 2,383 | 6,520 | 71,626 (70,799) | 878 | 0.0362 |
| Batch 1, second reply | 3 | 3,421 | 6,520 | 15,705 | 196 | 0.0083 |
| Batch 2, first reply | 3 | 2,666 | 6,520 | 95,167 | 1,106 | 0.0480 |
| Batch 2, second reply | 3 | 3,625 | 6,520 | 3,781 | 43 | 0.0024 |
| Batch 3 | 3 | 4,611 | 6,520 | 2,373 | 25 | 0.0018 |

- The first request writes the system prompt and its own message (8,122 tokens: OpenAI's tokenizer counts the
  system prompt as 6,520 tokens, Claude's as 8,417); every later request reads the 6,520 tokens of the system prompt.
- **A fault, fixed**: a second reply after a rejected answer read only the system prompt, not the earlier turns. In
  explicit mode the API looks for a cached prefix only at the breakpoints of the request, and the client had moved
  its second breakpoint to the new last message. The client now marks every user message (at most 4 breakpoints).
  Checked with `cache_check.py` (Luna at `low`, a new key): the reply after feedback wrote 806 tokens and read 8,903
  (the system prompt and the first turn). Every later run shows the earlier turns read (for example Terra, riff, second
  reply: 8,308 read).
- `prompt_cache_key` separates caches: a request with a new key read nothing at first.
- At `max`, Luna thinks a lot: 70,000 to 95,000 tokens on a first reply, 15 to 18 minutes.

**Lost records** (an error of the agent, 2026-10-30: a leftover `rm -rf runs/*/luna/` in a shell command deleted the
folders of the Luna runs at `max`). The numbers above and below come from the monitor's lines in the session. Luna at
`max` on the riff at medium (`99rb-riff.medium`): plan 2 replies ($0.0027 + $0.0007; the first had a one-frame gap
between sections), batch accepted at the first reply (56,103 output tokens, 671 s, $0.0283); $0.032, 732 s in all. It
was run again afterwards for its answer: accepted at the second reply, $0.048, 19 minutes (the plan 2 replies, the
batch's first reply refused). Three more cases at `max` had ended before the deletion
(`99rb-riff.hard-medium` $0.036 611 s, `99rb-riff.easy` $0.048 824 s, `99rb-riff.forced-m15-m1` $0.053 1,051 s, all
accepted at the second reply); four were stopped (the user chose `medium` only, section 4).

# 4. Max against medium effort, and the user's decisions (2026-10-30)

The first case with every model (`99rb-riff.medium`: the riff f783-f1042, 10 s, at medium, the plan request then one
batch) showed the cost of `max`:

| Model (effort) | USD | Time | Output tokens of the batch's first reply | Replies |
|---|---|---|---|---|
| Sonnet 5.5 (`high`) | 0.150 | 1.3 min | 7,076 | 2 |
| GPT-6 Luna (`max`) | 0.032 | 12.2 min | 56,103 | 1 |
| GPT-6.1 Terra (`max`) | 0.193 | 7.3 min | 32,606 | 2 |
| GPT-6.1 Sol (`max`) | 0.256 | 8.5 min | 20,020 | 2 |
| GPT-6 Luna (`medium`) | 0.005 | 1.2 min | 4,959 | 2 |
| GPT-6.1 Terra (`medium`) | 0.028 | 0.6 min | 2,105 | 2 |
| GPT-6.1 Sol (`medium`) | 0.051 | 0.8 min | 1,644 | 2 |

A judge request (Opus 5.5 at `max`, scratch `judge.py`) on this case cost $1.30 (48,000 output tokens, 7.5 minutes).

The user's answers:

1. **Measure `medium` and project from it** (instead of 8 or 16 cases at `max`, which would pass the $7 of credits).
   The projection, from the riff and the passage after it (3 batches per model), scaled from Sonnet's measured
   whole song ($2.25 to $2.70, 25 to 30 minutes): Luna `medium` about $0.10 per song, Terra `medium` about $0.35, Sol
   `medium` about $0.60, all about 12 to 25 minutes; at `max`, Terra about $3.30 to $3.90 and Sol about $4.30 to $5.10,
   2.5 to 3 hours. The user then chose **`medium` only** for the 16 cases.
2. **No judge through an API**: the agent judges in its session. The scratch `judge.py` and its one request are not
   used. The agent's method: `report.py draw` draws the passage now and every answer with the app's engine;
   `blind.py` makes one image per case (the passage now, then the four answers under letters A to D in an order
   shuffled from the case id, with only the check's status) and prints the measures and declared lines by letter;
   the agent scores each answer before reading which model wrote it (`judged.py` -> `judgments.json`).
3. **The report** has two tabs: the comparison of cost, quality and time, and the examples (the passage now, the
   instructions of the run, Sonnet's version and each GPT model's version, drawn by the app).

Luna's runs at `max` on the other cases were stopped after the answer (4 ended, section 3).

# 5. The test set and the runs (tasks 5.4, 5.5)

`cases.json`: 16 cases, each one passage of one or two batches, both hands rewritten, through
`levels.write_level(span=...)` (the plan request of the passage, then its batches, the check, at most 3 replies):

| Passage | Song (project) | Frames | Batches |
|---|---|---|---|
| `99rb-riff` | 99 Red Balloons (`c0e39afe`) | f783-f1042 (10 s, the riff with the high chords) | 1 |
| `99rb-after` | 99 Red Balloons | f1042-f1414 (15 s) | 2 (f1042-f1377, f1377-f1414) |
| `7years` | 7 Years (`477086a0`, the edit copy, prompt 6) | f4252-f4872 (25 s, its busiest batch: 230 notes, L range 34) | 1 |
| `halleluyah` | Halleluyah, Pinchivi (`f198e0d5`, the vault project, a human cover) | f3462-f4003 (22 s) | 1 |

Each passage: `easy`, `medium`, `hard-medium` (right hard, left medium) with the level's default patterns (Phase 4),
and one forced pattern: `forced-m15-m1` (left medium 15 with right medium 1) on the riff and 7 Years,
`forced-e2-e2` (left easy 2 with right easy 2) on the passage after the riff and Halleluyah. Read only: no sheet of the
app changed. Every run of every model: `runs/<case>/<model>/calls.json` (each request: its last message, the reply, the
`Call`) and `result.json` (plan, batches with status, replies, errors, answer, drawn answer, declared lines, measures,
cost, time). Models: `sonnet` (Sonnet 5.5, `high`, `ClaudeComplete` as in the app), `luna-medium`, `terra-medium`,
`sol-medium`; on the riff at medium also `luna`, `terra`, `sol` at `max`. Runs with `run_many.py <model> <N>` (N cases at
a time) through `docker exec`.

| Model (effort) | Batches accepted | Replies per batch | Cost per passage | Time per passage | Output tokens per request | Total of the 16 cases |
|---|---|---|---|---|---|---|
| Sonnet 5.5 (`high`) | 20 of 20 | 1.70 | $0.269 | 2.5 min | 9,503 | $4.30 |
| GPT-6 Luna (`medium`) | 15 of 20 | 2.30 | $0.008 | 2.2 min | 3,990 | $0.13 |
| GPT-6.1 Terra (`medium`) | 20 of 20 | 1.90 | $0.041 | 1.0 min | 1,852 | $0.65 |
| GPT-6.1 Sol (`medium`) | 20 of 20 | 2.05 | $0.072 | 1.0 min | 1,469 | $1.16 |

Luna's 5 refused batches: `99rb-after.easy` and `.medium` (first batch), `7years.hard-medium`, `7years.forced-m15-m1`,
`halleluyah.forced-e2-e2` (missing melody notes, uneven pairs, notes off the grid, chords on a new bass).

**Per song** (`report.model_rows`): the plan request plus each model's cost and time per second of music times 195 s
(99 Red Balloons, 13 batches one after the other). Sonnet: $2.72 and 26 minutes, which matches its measured whole song
(Phase 4: $2.25 to $2.70, 25 to 30 minutes). Terra `medium` $0.33 and 9 minutes; Sol `medium` $0.58 and 9 minutes; Luna
`medium` $0.07 and 21 minutes (3.2 failed batches per song); Terra `max` $3.29 and 2.2 hours; Sol `max` $4.31 and 2.6
hours (from the riff only).

**Money spent in the phase**: OpenAI about $2.70 of the $7 (runs $2.42 recorded, plus about $0.30 of the Luna `max`
records lost, section 3); Anthropic $5.60 (Sonnet $4.30, the one judge request $1.30).

# 6. The judgment (task 5.6)

The agent judged the 16 cases blind (section 4), each answer on melody, level, pattern, playable, musical and overall,
0 to 10, with reasons that name frames (`judgments.json`). A batch the check refused counts as what the user gets: the
sheet now. Fault found on the way: `report.answer_sheet` first drew a refused batch with its last refused answer; it now
keeps the notes now (`status == "ok"` only); the one case judged before the fix (`99rb-after.medium`, answer D) was
scored as the notes now.

| Model (effort) | Overall | Level cases | Forced pattern | Melody | Level | Pattern | Playable | Musical | Best or tied |
|---|---|---|---|---|---|---|---|---|---|
| Sonnet 5.5 (`high`) | 7.4 | 7.3 | 7.5 | 8.1 | 7.6 | 7.5 | 7.4 | 7.6 | 9 of 16 |
| GPT-6 Luna (`medium`) | 5.2 | 5.4 | 4.8 | 6.4 | 5.2 | 5.3 | 5.4 | 6.0 | 2 of 16 |
| GPT-6.1 Terra (`medium`) | 7.6 | 7.6 | 7.8 | 8.4 | 7.7 | 7.7 | 7.6 | 7.4 | 11 of 16 |
| GPT-6.1 Sol (`medium`) | 7.0 | 7.1 | 6.8 | 8.3 | 6.9 | 6.9 | 6.9 | 7.2 | 4 of 16 |

What separated them (from the reasons): Sonnet's weak cases were a busy left hand on the riff (5) and a deep low reach at
easy on 7 Years (6); Sol more often made the left hand busier than the sheet now (7 Years medium, Halleluyah hard-medium)
and changed melody endings; Luna's refused batches leave the passage as hard as it was. The max-effort answers on the
riff are drawn in the report but not scored (the user chose `medium` only).

**Verdict (the agent's)**: GPT-6.1 Terra at `medium` matches Sonnet's quality on this set (7.6 against 7.4, within the
noise of one judge on 16 cases), with every batch accepted, at about an eighth of the cost and a third of the time per
song. Limits: one judge and 16 cases; the prompts were tuned on Sonnet (Phase 3); Sonnet ran at `high` and its
conversation turns are not cached (`ClaudeComplete` caches only the system prompt).

# 7. The report (task 5.7) and the checks

- `gallery/04-3-phase-5/index.html` (`report.py draw` and `page`), served at
  `http://ubuntu:8097/gallery/04-3-phase-5/index.html`: tab **Cost, quality and time** (verdict, summary, scores by
  criterion, medium against max on the riff, prices) and tab **The examples** (a pill per case; what the user asks in
  Enhance with AI, links to the prompts in `prompts/`, the passage now and each model's version drawn by the app's
  engine in `svg/`, with cost, time, measures, scores and reasons, the plan and the declared lines). Checked in
  Chrome; the drawings were looked at zoomed in during the judgment.
- The scratch scripts and data are copied to `gallery/04-3-phase-5/tools/` (`harness.py`, `run_many.py`,
  `report.py`, `blind.py`, `judged.py`, `summary.py`, `cases.json`, `criteria.md`, `judgments.json`).
- `pytest` (in the running container, CPU): `test_sheet_llm_openai.py` (4), `test_sheet_llm_frames.py`,
  `test_sheet_levels.py`, `test_sheet_levels_app.py`: 53 passed. `ruff check` on the changed files: no new finding (two
  findings were already on `master`).

# 8. Needed later

- **The user's decision** (task 5.8): which model the level runs use, and whether the app gets a choice of model. If
  Terra: `job.start_level` builds `OpenAIComplete(model="gpt-6.1-terra", effort="medium", cache_key=<part>|<level>)`
  instead of `ClaudeComplete`; the cost estimate (`job.level_cost`, $0.05 + $0.20 per batch) changes to about $0.01 +
  $0.025 per batch; `OPENAI_API_KEY` must be in the container's environment (today it is read from `.env` as a
  fallback); a refusal or an API error must keep the batch's notes as today. The page still says "AI".
- Phase 6 (documentation): the core's `README.md` (the OpenAI client, the caching rules of GPT-6), the dependency.

# 9. The user's decision: the level runs use GPT-6.1 Terra at medium (2026-10-30)

The user chose GPT-6.1 Terra at `medium` for the level runs, and asked that the page tell the user to add credits to
the OpenAI account when they run out, and that every estimate of minutes and money the app shows match what the
benchmark measured. The other runs (Write it all again, Simplify, a stretch with words) keep Sonnet 5.5: only the
level runs were compared.

**The estimates before and after.** The dialog shows two numbers before a level run. The money came from the backend
(`job.level_cost`: $0.05 for the plan and $0.20 per batch, measured with Sonnet in Phase 3); the minutes were computed in
the dialog itself (2 minutes per request, `EnhanceDialog.minutes`). Both were Sonnet's:

| Estimate | Before (Sonnet) | Measured with Terra `medium` (16 cases) | Now |
|---|---|---|---|
| Plan of the song | $0.05, (2 min) | $0.012, 8 s | $0.015, 10 s (`USD_LEVEL_PLAN`, `SECONDS_LEVEL_PLAN`) |
| A batch with all its replies | $0.20, (2 min) | $0.023, 41 s | $0.025, 45 s (`USD_LEVEL_BATCH`, `SECONDS_LEVEL_BATCH`) |
| 99 Red Balloons, both hands (13 batches) | $2.65, 28 min | about $0.33, 9 min (projected) | $0.34, 10 min |
| The user's new song (1.3 min, 4 batches) | $0.85, 10 min | $0.086, 2.6 min (one real run, below) | $0.12, 3 min |

`level_cost` now returns `batches` and `minutes` (`max(1, round((10 + 45 × batches) / 60))`) with `requests` and `usd`;
the dialog shows the backend's minutes (`LlmCost.minutes`), and "1 minute" in the singular.

**What changed in the code:**

- `job.LEVEL_MODEL = "gpt-6.1-terra"`, `LEVEL_EFFORT = "medium"`; `job._level_complete(part, level)` builds
  `OpenAIComplete` with `prompt_cache_key = "<part>|<level name>"`; `start_level` uses it (a `complete` given by a
  test still replaces it). `job.level_available()` (an OpenAI key and the SDK) guards the two level routes
  (`POST /sheet/{uuid}/llm/level`, `/level-copy`); the other routes keep `job.available()` (Anthropic).
- **No credits**: `sheet_llm.NoCredits`, raised by `OpenAIComplete` when the API answers `insufficient_quota`. A level
  run stops there (the batches already accepted are stored, as for any error), and the job's summary gets
  `credits: "openai"`. The page then says: "The sheet stays as it was. The AI has no credits left: add credits to the
  OpenAI account (platform.openai.com, Billing), then run it again." (or "The AI wrote 2 of 4 parts; the others stay
  as they were. ..." when some batches were stored). The SDK retries a 429 a few times before the error reaches the
  run (some seconds).
- `compose.yaml` passes `OPENAI_API_KEY` to the backend; until the container is created again, the backend reads it
  from `.env` (`sheet_llm._openai_key`).
- Tests: `test_a_level_runs_on_terra_and_the_estimate_follows_the_benchmark`,
  `test_a_level_that_runs_out_of_credits_says_so`, the costs of `test_the_routes_of_the_levels` (with `minutes`),
  `test_openai_complete_says_when_the_account_has_no_credits`. `test_sheet_llm_openai.py`, `test_sheet_levels_app.py`,
  `test_sheet_simplify.py`, `test_rights.py`: 40 passed. `tsc -b` and `eslint` clean; `check:enhance-dialog` all passed
  (its regex accepts "minute").

**A real run through the app's code** (the user's new song `2f133ebc`, saved to My Library during this work; a level
copy `81a6a129` "… · Medium (test of the new AI model)" made with `flow.level_copy`, then `job.start_level(level="medium",
hand="both")` with the default client): 4 of 4 batches accepted, $0.086, 157 s, against the estimate $0.12 and 3
minutes. The record names `gpt-6.1-terra`. Looked at zoomed: the left hand keeps its held chords where it was simple;
the right hand keeps the melody with fewer chords. The copy stays in My projects for the user.
