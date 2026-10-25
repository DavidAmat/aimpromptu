# 03: Phase 4 report: the LLM step for the new sheet

Plan: [`03-plan.md`](03-plan.md) section 7, Phase 4. Checklist: [`03-checklist.md`](03-checklist.md). Branch
`feat/migrate-new-logic` (`master` had not moved since Phase 3, so nothing was merged in). Written 2026-10-25 on the
Ubuntu machine. No change visible in the app: no route or page uses the LLM step yet. **Done 2026-10-25**: the
user checked the gallery ([`gallery/phase-4/index.html`](gallery/phase-4/index.html)) and said "all good"; the two
decisions of section 11 were closed as section 11.3 says.

# 1. Summary

| Task | Result |
|---|---|
| 4.1 The API key | Created by the user (an individual Console organization, linked to the Max 5x credits, no card). Three test requests: a tiny one (18 input, 4 output tokens, 1.2 s), the reference request of 7 Years writing the cache ($0.029, 4.0 s, 9,080 cached tokens) and reading it ($0.009, 4.8 s) (section 6.1) |
| 4.2 `complete` | `aitu_backend/sheet_llm.py`, `ClaudeComplete`: the `anthropic` SDK 2.2.0, `claude-sonnet-5-5`, adaptive thinking at effort `high`, the system prompt cached, streamed requests, 4 SDK retries, a 600 s time limit, the server-side fallback, a refusal raised as `SkipWindow`, every request recorded with its cost (section 4) |
| 4.3 Prompt version 5 | `sheet/llm/prompt/frames/`: F1 frames in and out; the LLM decides hands, beam groups (plan section 3.11), clefs and 8va (the version 4 rules unchanged), ornaments and the armadura of passages; figures, grace notes and spelling are rules of the app; the reference figure has its own request with the peaks of the gaps in words; four examples, each checked by the checker (section 3) |
| 4.4 The checker and the fallback | `sheet/llm/frames.py`, `check_answer`: every onset once with a hand, beam groups of 2 to 8 consecutive notes of a hand (the maximum is a hard check), no 8va in the bass clef, no note four or more ledger lines above its staff, `orn` after an ornament; the phase 14 beam guard rewritten for the new sheet; a failed window keeps the algorithm, an exception stops the requests and keeps the algorithm for the rest (section 2) |
| 4.5 The 10 viewer songs | 150 of 150 windows accepted (125 at the first check), 179 requests, **$8.86** (median $0.77 per song, $0.51 to $1.73), 4 to 17 minutes per song. Same hand as the research's recorded Sonnet sheets on 96.3 to 99.8 % of the notes (the algorithm's starting hands: 88.7 to 99.1 %). The credits cover about 110 songs a month (section 6) |
| 4.6 Gallery | 10 passages, the algorithm and Sonnet side by side, drawn by the Phase 3 engine, every drawing checked zoomed in against the data (section 8) |

Two fixes outside the LLM step came from the gallery: the engine placed two clef changes of one column (one for a
grace note, one for its note) on top of each other (`engrave/frames.py`, section 8.2), and nearby 8va notes are now
joined into one 8va line (section 5.3).

# 2. The study and the design

## 2.1 What the bars chain did, and what no longer fits

The research chain (`llm/chain.py`, `song.py`, `windows.py`, frozen as the core) asks for F1 bars: Sonnet chose the
beat, the meter, the bars, the figures, the hands, the beams, the spelling and the clefs. Its windows were 8 bars of
the estimated tempo, and the last bar of each answer was decided again by the next window. Without compases, four
parts of that design no longer fit:

1. **Figures are a rule** (Phase 2), and they depend on the hands: a figure is the note's own length capped at the
   next onset of the *same hand*. The LLM decides the hands, so the figures can only be computed after its answer.
2. **Grace notes and spelling are rules** (Phase 2): the two-step rule, and rules 1 to 5 of the alteraciones.
3. **The reference figure** is the LLM's choice (plan section 3.3), from the histogram of the gaps in words.
4. **Bars and the "last bar decided again"** do not exist.

The bars chain stays in the core, unchanged, with its golden files (139 of 139 pass).

## 2.2 The new chain (`sheet/llm/frames.py`, `write_frames`)

1. **The reference request** (unless `quarter_ms` is given): the same system prompt (so it also writes the cache),
   a user message with the peaks of the gaps between onsets (`gap_peaks`: the measured onsets of the drawn columns,
   both hands, a histogram in twelfths of an octave, the share of the gaps within 12 % of each peak) and the first
   16 s of the song without hands and figures. The reply is `quarterMs=NNN` and a one-line reason; a value outside
   150 to 2,000 ms keeps the pulse estimate. The peaks are computed on `Note.on_ms`, not on the 40 ms columns: on
   columns 7 Years showed 160 and 200 ms as two peaks of one gap (about 175 ms).
2. **The algorithm** (`propose_frames`) with the starting hands and that reference figure: the fallback of a window
   and the source of the input's figures.
3. **Windows** (`windows_of`): from a window's first column, an end between 12 and 16 s later (at most 200 onsets;
   when the onsets come first, from 75 % of that point), at a column that no beam group of the algorithm crosses
   when one exists, then after the longest pause. The windows depend only on the notes and the algorithm, so they
   are known before any window request, and **each answer is kept whole**: nothing is decided twice (the bars
   chain decided about one bar in eight twice). Phase 5 can use the windows as the segments of the piece-by-piece
   view.
4. **One conversation per window**: the target (the notes without hands, `?:`, each with the figure the rule gives
   with the starting hands, spelled in the armadura in force), a look-ahead of 4 s, and from window 2 on the
   decided context (the last 4 s of the previous answer, with its hands, beams and clefs, and the range of each
   hand). The header gives the armadura and the clefs in force. At most 3 replies; a rejected reply gets the
   feedback and the model writes the whole answer again.
5. **The sheet** (`assemble`): each window's decisions (hand, beam group, ornaments, `orn`, 8va; clefs and
   armadura at the start and their changes) on the notes of the algorithm's sheet, matched by (column, key); for a
   failed window, the algorithm's decisions. Then the rules: figures from the lengths capped by the new hands
   (`assign_figures`), grace notes (`find_graces`), beam groups cut where the figures break them (`trim_beams`,
   section 5.1), the spelling (`respell`), the 8va join (section 5.3). `frames.check` holds on every result.

The input shows the figures of the starting hands so that the LLM can choose beam groups that the rule's figures
will keep. The LLM may move a note to the other hand; its figure is then computed again, and a group that the new
figures break is cut. The research found that showing Opus the algorithm's *hands* made it copy their errors (hands
98.8 % to 95.1 %); the input therefore shows no hand (`hands=True` shows them, for a run again on the numeric truth
in Phase 6, plan section 3.7).

## 2.3 Errors and credits

`complete` raising `SkipWindow` (a refusal) fails that window only. Any other exception (no key, the credits used
up, no network after the SDK's retries) gives that window status `error`, and every later window `skipped`: they
keep the algorithm, and `WindowLog.note` says why. The song still gets a valid sheet (a test checks both cases).
This is the behaviour of plan section 3.8: no alarm, the algorithm's sheet stays.

# 3. The prompt, version 5 (`sheet/llm/prompt/frames/`)

`instructions.md` (about 19,500 characters, 9,080 tokens with the cached prefix) is written from version 4:

- The task: the app's sheet, simpler than a classical score (no bars, meter, tempo, rests, dots or tuplets), and
  what the app computes by rule (figures, grace notes, accidentals, with the user's rules 1 to 5 in one paragraph).
- The input and output format: F1 frames, `?:` notes with the rule's figures, `L:`/`R:`, the tags `b`, `tr`,
  `mord`, `turn`, `arp`, `orn`, `8va`, `clef=`, `fN key=`.
- What the LLM decides: the hand rules of version 4 (hand.1 to hand.7, range.1 to range.5, worded without bars);
  **beam groups** beam.1 to beam.8 from plan section 3.11 (only eighths and shorter, consecutive notes of one hand,
  one figure per group with one odd note at an edge, at most 8 notes, cut at a jump, at a change of direction or a
  broken pattern, a repeated contour, a left-hand pattern never cut between the hands, repeated passages written
  the same way); the clef rules of version 4 unchanged (clef.L6 says "between two beam groups or at a pause"
  instead of "on a beat"); ornaments; the armadura of a passage (rule 6: only for a passage of about 5 s or more
  with many notes outside the armadura).
- The reference figure: the quarter usually the beat a listener taps, 400 to 750 ms in most songs (the research's
  proposed hint for pop, section 2.9 of `synthesis/02-llm-step.md`), avoiding most notes as fusas, halves or wholes.
- Four examples, input then answer: the A major arpeggio of version 4 (shared once, a cut at a jump, a left-hand
  figure of four eighths per group), the waltz of version 4 (bass and chords, clef changes, six eighths per group),
  and two pop passages of songs outside the test set: The Other Side at 84 s (an octave bass, groups of the shape
  low-high-low-high that end where the bass note changes) and La Tortura at 196 s (an arpeggio, one group for each
  rise and each fall). Each example's input was generated from its answer (no hand, no beam, the app's spelling),
  and `test_the_prompt_examples_pass_the_checker` runs the checker on all four pairs.
- How to answer, and what the checker checks.

`feedback.md` is the version 4 text. `VERSION` says what changed.

# 4. The Claude `complete` (`aitu_backend/sheet_llm.py`)

Outside the core, which imports no SDK (`test_imports_stay_inside_the_core`). One request:

```python
client.beta.messages.stream(
    model="claude-sonnet-5-5", max_tokens=64000,
    system=[{"type": "text", "text": instructions, "cache_control": {"type": "ephemeral"}}],
    messages=..., thinking={"type": "adaptive"}, output_config={"effort": "high"},
    betas=["server-side-fallback-2026-07-01"], fallbacks="default",
)
```

- **Streaming** with `get_final_message()`: no HTTP time limit on long answers. Client: `timeout=600`,
  `max_retries=4` (the SDK retries connection errors, 408, 409, 429 and 5xx with a growing wait).
- **The cache**: the instructions are the same for every request of every song; within 5 minutes a request reads
  them at a tenth of the price. In the runs, 1,618,445 cached tokens were read against 9,129 written.
- **A rejected answer goes back with its whole content** (the thinking blocks unchanged, as Sonnet 5.5's
  preserved thinking asks): `_content` maps a reply's text to its content blocks.
- **Refusals**: `stop_reason == "refusal"` raises `SkipWindow`. The server-side fallback (`"default"`, the
  recommended form for Sonnet 5.5 on the Claude API) first gives a declined request to another model when the
  category allows it. No request was refused in the runs.
- **Cost**: `price()` with the platform prices of 2026-10 (Sonnet 5.5: $2 input, $10 output, $2.50 cache write,
  $0.20 cache read per million tokens). Output tokens include the thinking.
- `ANTHROPIC_API_KEY` in `.env` (and `.env.example`); `compose.yaml` passes it to the backend container (it applies
  at the next `make up`). The backend image does not have `anthropic` yet: it is in `pyproject.toml` and `uv.lock`,
  and the image is rebuilt in Phase 5 (uv's Python, Phase 3 section 7.2). The SDK is imported only when a
  `ClaudeComplete` is made without a client, so the container's tests pass without it.

# 5. What the first full run changed

## 5.1 Beam groups of two figures (`one_figure`)

The first run on the 10 songs (`viewer-1`) kept only 1,569 of Sonnet's 2,044 beam groups as written (410 removed); in 7 Years,
35 of 242. Sonnet often beams a semicorchea with the corchea after it (a short-long pair, common in pop rhythms).
`trim_beams` used the algorithm's `_uniform`, which allows an odd note only next to two or more notes of the
group's own figure: the algorithm needed this for an octave played unevenly (a semifusa and a fusa under four
beams, Phase 2 section 13), and since the user's review the grace rule makes those acciaccaturas. The user's rule
itself is "one single note of another figure may open or close a group". `one_figure` (in the LLM step only; the
algorithm is unchanged) allows the odd note next to a single note of the group's figure when the two figures are one
step apart. Rebuilt from the logged replies (no new request): 1,857 groups kept as written (91 %), 76 cut, 111
removed; 7 Years 208 of 242. In the final run: 2,046 written, 1,888 kept (92 %), 56 cut, 102 removed.

## 5.2 The ledger line limits in the checker

The gallery showed Superestrella (cover) with 137 right-hand notes four or more ledger lines above the treble
staff without 8va, and 107 left-hand notes four or more above the bass staff; Moonlight Shadow 40, Halleluyah 5.
The prompt states both limits (clef.L3, the user's left-hand rule, and clef.6), but nothing checked them; the
algorithm treats clef.L3 as a hard limit (`BASS_LIMIT`). Both are now in the checker, with feedback that names the
rule (the first two places, then a count). A note already under 8va is not checked: only a 15ma line would lower it
more (Superestrella has left-hand notes up to B7, likely transcription noise). Only those three songs changed; they
were run again from their first rejected window (`--from-run viewer-1 --then-live`): 11 windows needed one more
reply, and every window was then accepted.

The alternative was measured too: the algorithm's clef and 8va rule (`clefs_and_ottavas`) on Sonnet's hands
(`assemble(clefs="rule")`, kept as an option). It gives fewer clef changes (Superestrella 94 against 154,
Halleluyah 6 against 16), but it writes Halleluyah's left-hand arpeggio in the treble clef with its low notes four
ledger lines below the staff, and leaves a single C#7 of Moonlight Shadow under six ledger lines. Neither is better
everywhere; Sonnet's clefs stay (the plan's design), with the checker's limits.

## 5.3 One 8va line instead of many (`join_ottavas`)

With the limit, Sonnet marks each high note with 8va, and the engine draws one short bracket per note (Superestrella:
25 brackets of one note). `join_ottavas` (in `assemble`): two 8va notes of one hand less than 2 s apart, in the
treble clef, with every note between them at C5 or higher (written no lower than C4, one ledger line below the
staff), put the notes between under 8va too. Superestrella: 64 8va lines to 15 (10 of four notes or more). Moonlight
Shadow keeps 21 one-note lines: isolated high notes in a melody that goes below C5 between them, where one line
would push the low notes far below the staff.

# 6. Measurements

## 6.1 The three test requests (task 4.1)

| Request | Input | Cache write | Cache read | Output | Seconds | Cost |
|---|---|---|---|---|---|---|
| "Reply with the single word OK" | 18 | 0 | 0 | 4 | 1.2 | - |
| The reference request of 7 Years | 919 | 9,080 | 0 | 447 | 4.0 | $0.029 |
| The same again | 919 | 0 | 9,080 | 528 | 4.8 | $0.009 |

Both reference replies chose a quarter of 480 ms for 7 Years ("runs 240 ms apart are eighths, chords 480 ms apart
quarters"); the research's Sonnet had read it at half speed (1,000 ms).

## 6.2 The 10 viewer songs (run `viewer-final`)

The logs, the F1 texts (Sonnet's and the algorithm's) and `summary.json` are in
`<database>/lab/sheet-llm/viewer-final/` (outside the repository: they hold passages of the private library).
`scripts/llm_sheet.py --viewer --from-run viewer-final` rebuilds every sheet from the logged replies without a
request. "Same hand" compares each note with the research's recorded Sonnet sheet of the song (phase 13, F1 bars,
prompt version 4), matched by key and column; it is agreement with another Sonnet reading, not with a printed score.

| Song | Notes | Quarter: Sonnet / research Sonnet / pulse estimate (ms) | Windows (first check) | Requests | Cost | Minutes | Same hand: Sonnet / algorithm | Notes moved from the starting hands | Beam groups written / kept |
|---|---|---|---|---|---|---|---|---|---|
| 7 Years | 1,458 | 480 / 960 / 1,000 | 15 (15) | 16 | $0.68 | 6.5 | 98.5 / 96.6 % | 60 | 242 / 208 |
| Superestrella (cover) | 1,503 | 440 / 400 / 882 | 14 (9) | 20 | $1.42 | 13.9 | 96.3 / 93.9 % | 69 | 172 / 153 |
| Halleluyah | 985 | 700 / 720 / 707 | 14 (11) | 18 | $0.71 | 7.1 | 97.1 / 92.6 % | 74 | 143 / 127 |
| Poker Face | 1,985 | 500 / 480 / 504 | 15 (13) | 18 | $0.84 | 7.3 | 99.8 / 98.8 % | 27 | 286 / 275 |
| Drivers License | 1,733 | 420 / 800 / 833 | 16 (14) | 19 | $0.51 | 4.1 | 98.7 / 96.9 % | 44 | 61 / 57 |
| Hips Don't Lie | 1,614 | 600 / 640 / 400 | 13 (10) | 17 | $1.02 | 9.5 | 96.4 / 88.7 % | 224 | 278 / 255 |
| Birds of a Feather | 1,449 | 580 / 800 / 571 | 14 (13) | 16 | $0.58 | 5.4 | 99.1 / 94.7 % | 70 | 164 / 158 |
| Moonlight Shadow | 2,384 | 480 / 480 / 467 | 16 (13) | 20 | $1.73 | 16.9 | 99.1 / 93.9 % | 140 | 338 / 306 |
| The One That Got Away | 1,618 | 420 / 800 / 428 | 15 (13) | 18 | $0.55 | 4.7 | 98.9 / 97.5 % | 46 | 97 / 95 |
| Shut Up and Dance | 1,992 | 460 / 480 / 937 | 15 (14) | 17 | $0.82 | 7.4 | 98.9 / 99.1 % | 38 | 265 / 254 |
| **Total** | 16,721 | | 150 (125) | 179 | **$8.86** | 82.7 | | 792 | 2,046 / 1,888 |

- **Tokens** (all requests): 482,024 input not cached, 1,618,445 cache read, 9,129 cache write, 755,019 output
  (thinking included). The output is about 85 % of the cost.
- **Time**: 28 s per request on average (5 to 62 s). A song takes 4 to 17 minutes; Phase 5's piece-by-piece view
  gets one window about every half minute.
- **Credits**: $0.89 per song on average (the median $0.77; the dense or high songs cost more, up to $1.73). The
  100 USD a month cover about 110 songs. The research estimated about $1 per song; the cache and the shorter
  answers (no bars, no figures to write) keep it below.
- **The reference figure**: Sonnet chose the research Sonnet's quarter or one within 10 % in 6 songs, and a quarter
  half as long in 3 (7 Years, Drivers License, The One That Got Away: the 400 to 750 ms hint; the research read
  them at half speed); Birds of a Feather 580 against 800.
- **Beam groups**: Sonnet writes shorter groups than the algorithm (sizes 2 / 3 / 4 / 5 / 6 / 7 / 8: 672 / 543 /
  468 / 134 / 54 / 26 / 39 in `viewer-1b`; the algorithm 318 / 270 / 194 / 171 / 159 / 136 / 146). The same beam
  decision as the research's Sonnet between consecutive short notes: 52.5 to 86 % (the algorithm 42 to 76 %); the
  research's groups follow the beat, which the new sheet has not.
- **Clefs, 8va, ornaments, armaduras** (final sheets): 170 clef changes (154 in Superestrella's cover, 16 in
  Halleluyah, none in the other 8) against the algorithm's 182; 527 notes under 8va against 761; 94 rolled chords
  (`arp`, 85 in Moonlight Shadow), no trill; no armadura change (the algorithm changes once, in Hips Don't Lie).
- Every sheet passes `frames.check`, and every onset cell of the matrix is kept (the round trip without the hand:
  the hands changed).

## 6.3 Offline checks before the key

- **An oracle** (`complete` that answers with the algorithm's own decisions) on the 10 songs: every window
  accepted except one where an algorithm group crosses a window end, every sheet valid, the round trip exact. It
  found two errors of the first version: the phase 14 beam guard counted short notes followed by a long gap (they
  have nothing to join; the guard now counts pairs of consecutive notes that could share a beam), and window ends
  inside the algorithm's beam groups (the end now avoids them).
- **The replay** of the research's recorded Sonnet sheets (`--replay`): 148 of 150 windows accepted after the
  stand-in drops recorded groups that a window end cuts. It was the baseline: the algorithm's starting hands agree
  with the recorded Sonnet on 88.7 to 99.1 % of the notes.

# 7. Tests and checks

| Check | Result |
|---|---|
| Backend, full run in the image **on the CPU** (`AITU_DEVICE=cpu`, `CUDA_VISIBLE_DEVICES=`) | 1,328 tests: 1,326 passed, 1 skipped (it needs a GPU), 1 failed: `test_the_worked_example_at_00_46_prints_three_equal_corcheas`, failing since Phase 0. The two Transkun tests that failed without a GPU in Phases 0 to 3 passed this time; 111 s |
| `tests/test_sheet_llm_frames.py` (new) | 15 tests: windows, the gap peaks and the reference reply, the checker (each kind of problem, the ledger limits), the chain (a valid sheet that keeps every onset, the context), a rejected reply and its feedback, a refused window and an error that stops the requests, hands moved by the LLM, beam groups cut by the figures and the pair rule, the beam guard, the 8va join, the four prompt examples, the Claude `complete` with a stand-in SDK client (parameters, cost, the content sent back, a refusal). They pass in the container without `anthropic` |
| `tests/test_sheet_engrave_frames.py` | 10 tests, one new: two clefs and a grace note between them do not overlap (it failed before the fix) |
| The golden files of the core | 139 of 139, unchanged |
| `flake8`, `black` on the new and changed files | clean |
| `scripts/docs/check-links.py` | passed (section 10) |

# 8. The gallery (task 4.6)

[`gallery/phase-4/index.html`](gallery/phase-4/index.html), built by `scripts/llm_gallery.py --run viewer-final`
(`--find` lists the passages where the two sheets differ most). Served with `python3 -m http.server 8715 --bind
0.0.0.0` from the `gallery/` folder: `http://ubuntu:8715/phase-4/`. A table per song, then 10 passages, each drawn
twice (the algorithm with the same reference figure, then Sonnet), the lines of the whole song that hold the
passage, the passage on a light band:

- **Beam groups**: a repeated bass pattern (Poker Face), an arpeggio that rises and falls (Halleluyah), short-long
  pairs (7 Years), chords grouped until the chord changes (Birds of a Feather).
- **Hands**: low chords of the accompaniment moved to the left hand (Hips Don't Lie, Moonlight Shadow, Drivers
  License, The One That Got Away).
- **Clefs and 8va** (a question): Superestrella (cover).
- **Figures of staccato notes** (a question): Shut Up and Dance.

## 8.1 The checks before showing it

Every drawing was screenshot at 2x and looked at; the doubtful places were checked against the data. This found:
the beam groups removed by the pair rule (section 5.1), the notes far above their staff (section 5.2), the
one-note 8va brackets (section 5.3), and the overlap of section 8.2. A large "8" on the right-hand staff of
Halleluyah looked like a stray glyph; it is a redonda chord C5-E5-G5 (three stacked whole notes).

## 8.2 Two clefs at one column (`engrave/frames.py`)

When a grace note sounds in one clef and its note in another (Superestrella, f1669 and f1675: a bass clef for the
grace note B3, a treble clef for the chord B4-D#5), the column gets two clef changes for one staff. The engine gave
room to the first one only, and drew it without the shift of the inner one, so it covered the grace note and the
inner clef. The room now counts every clef change of the staff at the column, and the outer clef stands before the
grace notes, which moved left of the inner clef. Test: `test_a_grace_note_between_two_clef_changes_overlaps_neither`.

# 9. Notes for later phases

- **Phase 5 (the Sheet step).** `write_frames(notes, ClaudeComplete(), on_window=...)` runs a part; the windows
  (`windows_of(algo.sheet)`) are the segments, known before the first request; `assemble(algo, parts)` with the
  parts decided so far and the algorithm's parts for the rest gives the sheet at any moment (about 0.2 s). The
  reference request comes first and changes every figure of the algorithm's sheet (a new `propose_frames`): the page
  should draw the algorithm's sheet with the pulse estimate at once, then redraw it whole when the reference figure
  comes back (about 5 s), before the first window (about 30 s later). The image must be rebuilt with `anthropic`
  (and uv's Python, Phase 3 section 7.2); `ANTHROPIC_API_KEY` is already in `compose.yaml`.
- **The hands go back to `notes.pmn`** (plan section 3.7): the final sheet's notes carry `on_ms`; `frames.cells_of`
  maps them to their onset cells, and a note's hand is its staff. A note dropped by `assemble` as a duplicate (two
  notes of one key and column moved into one hand) keeps its starting hand.
- **Running again on the numeric truth** (Phase 6): `write_frames(..., hands=True)` shows the hands to the LLM.
- **Cost control**: the run logs `usd` per request; a song costs $0.5 to $1.7. A cheaper setting to measure if
  needed: effort `medium` (not measured here).
- **Not used yet**: `assemble(clefs="rule")` (section 5.2); `windows_of(span=...)` for other window lengths.
- The scratch scripts (the oracle, the passage finder, the clef comparison, the screenshots) are not kept; their
  numbers are in sections 5 and 6.

# 10. Documentation

- `aitu-backend/src/aitu_backend/sheet/README.md`: the modules table and section 11 (the LLM step of the new sheet).
- `context/backend/README.md`: the new modules and the two commands.
- `.env.example` and `compose.yaml`: `ANTHROPIC_API_KEY`.
- [`03-plan.md`](03-plan.md): section 3.3 and 3.11 notes, Phase 4 tasks with what was done, section 8, section 11.
  [`03-checklist.md`](03-checklist.md), [`README.md`](README.md), `../README.md`, `../../00-index.md`: the state.

# 11. Decisions for the user

## 11.1 The left hand's clef changes (rule clef.L4)

The left hand of Superestrella's cover alternates low notes and high chords about twice a second. Rule clef.L4
(the user's rule of research phase 14, in the prompt since version 4) puts the low notes in the bass clef and the
high part in the treble clef, so the clef changes very often (154 changes in the song). Options: (a) keep the rule;
(b) let a passage that alternates stay in one clef with ledger lines (up to the four-line limit); (c) the algorithm's
clef rule on Sonnet's hands (fewer changes, 94, but other faults, section 5.2).

## 11.2 The figures of staccato notes

Short detached notes a corchea apart get the figure of their own length (the user's rule): fusas and semifusas
with three or four beams (Shut Up and Dance, 7 Years). Options: (a) keep the rule; (b) in a run of even gaps where
every note sounds shorter than the gap, the notes take the figure of the gap (classical scores write staccato
corcheas as corcheas). Option (b) is one change in `proposal.frames.assign_figures` and applies to the algorithm
and to Sonnet's sheets alike.

## 11.3 How they were closed

The user answered the gallery with "all good" (2026-10-25) and did not choose between the options. As in Phases 2
and 3, what the gallery showed stays: rule clef.L4 as written (11.1 a) and the figures of staccato notes from their
own length (11.2 a). Either can change later with one change: a passage that alternates kept in one clef is a cost
in the prompt's clef rules (or `assemble(clefs="rule")`), the staccato figures one condition in
`proposal.frames.assign_figures`.
