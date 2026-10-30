# 04-3 · Phase 3: the level prompts, tested on 99 Red Balloons

Status: **in progress** (2026-10-30). Tasks 3.1 to 3.6 are built and tested without the AI; task 3.8 has its first
page (the test passages, the patterns proposed per level, the prompts). Task 3.7 (tests with the AI) waits for the
user's ok on the cost, the passages and the patterns. Branch `feat/04-3-phase-3` from `master` (`f85fa92`).

Audience: the agents of this plan (this phase when the user answers, and Phase 4). Technical.

# 1. What was built

| Part | Where |
|---|---|
| The grid of the song (task 3.3) | `aitu_backend/sheet/levels/grid.py`: `song_grid`, `Grid` (`points`, `on_grid`, `kind_of`, `beat_of`, `text`) |
| The chords of the song | `aitu_backend/sheet/levels/harmony.py`: `chords`, `Chord` |
| The measures (task 3.2) | `aitu_backend/sheet/levels/hands.py`: `track` (the research's tracker), `measure` -> `Measures`, `melody`, `columns`, `place_line` |
| The prompts (task 3.4) | `aitu_backend/sheet/llm/prompt/levels/`: `shared.md`, `easy.md`, `medium.md`, `hard.md`, `feedback.md`, `VERSION` (1) |
| The plan of the song (task 3.5), a batch, the check (task 3.6), a run in memory | `aitu_backend/sheet/llm/levels.py`: `system_prompt`, `song_summary`, `plan_prompt`, `read_plan`, `batch_prompt`, `check_level`, `read_declared`, `LIMITS`, `load_patterns`, `refs_in`, `to_notes`, `drawn`, `write_level` |
| Tests (no AI) | `tests/test_sheet_levels.py`: 19 tests (grid binary and ternary, chords, tracker and measures, refs in words, system prompt, the prompt's example parses, plan read, every rule of the check, a run with recorded answers and feedback) |
| The gallery (task 3.8, first page) | `scripts/levels_gallery.py` -> `gallery/04-3-phase-3/index.html` and `prompts/` |

Nothing in the app calls this code yet (Phase 4). No database change, no frontend change.

# 2. Study of 99 Red Balloons (task 3.1)

The project `c0e39afe` is one part (part id = project id). Its sheet (`build.current`) has 2,606 notes, frames 33 to
4879 (3:15), `quarterMs=600` (the AI's reference figure), key 4#. The record: prompt 5, $1.80, 32 requests, three
stretches by the user at f33-121, and one Simplify of the left hand (2026-10-28, 23 added, 10 left out).

Measures per 8 s (hand tracker, section 4): the left hand of the original moves 1 to 3.4 times per second in most of
the song, with chords of up to 8 notes and 41 semitones; the right hand moves up to 2.9 times per second. The high
chords: D#7-E7 (8va) at f863, f990, f2619, f2744; D#6-E6 at f926, f2681, f2807.

The test passages (in `levels_gallery.PASSAGES`):

| # | Frames | What | Why |
|---|---|---|---|
| 1 | f33-f539 | The intro | Calm: melody alone over a few bass notes (L 1.4 to 2.7 notes/s) |
| 2 | f783-f1042 | The riff with the high chords | The image `99-red-ballons-issue.png` (matched note by note): L chords E1-E2-B3-E4 etc., R only D#7-E7 and D#6-E6 |
| 3 | f1042-f1414 | After the riff | The image `whole-song-simplification.png` starts at f990 (its 8va chord) and goes on to about f1700 |
| 4 | f1826-f2296 | The right hand high | Melody around E6-G#6 with chords under it; L octavas moving about once per negra |

The structure: like_before on the right hand finds f2744-f2981 like f1073 and f2981-f3177 like f1101: the riff and
the passage after it come again at f2542-f3177.

# 3. The grid (task 3.3, plan section 5.3)

The first version tracked the negra (`beat.track` pulled to `quarterMs`). On 99 Red Balloons it wanders: the tracked
negra lasts 440 to 600 ms (median 480) and only 52 % of the onsets fall within one frame of a corchea point. The song's
pulse is 311 to 320 ms (the algorithm's own estimate is 317 ms), which is a corchea of the AI's negra of 600 ms: the
tracker pulled to 300 ms is steady, and 95 % of the onsets fall on a semicorchea point of it (table below).

The rule kept: track at the negra and at the corchea, measure the local tempo of each (a straight line fitted to
every 16 pulses; spread = 90th / 10th percentile of the fitted pulse length), keep the steadier one. When the negra
wins, the division is 2 or 3 by the share of onsets on the points (3 must win by 0.1). The grid goes on before the
first and after the last onset with the gap of the nearest four corcheas.

| Song | Tracked | Corchea | Spread negra / corchea | Drift (frames, median of 16-pulse fits) | Onsets on corcheas / semicorcheas (±1 frame) |
|---|---|---|---|---|---|
| 99 Red Balloons (`c0e39afe`, q=600) | corchea | 320 ms | 1.25 / 1.16 | 0.67 | 54 % / 95 % |
| 99 Red Balloons (library, q=317) | negra | 160 ms | 1.16 / 1.16 | 0.37 | 95 % / 100 % |
| 7 Years (library) | negra, ternary | 173 ms | 1.00 / 1.26 | 0.16 | 96 % / 100 % (binary: 68 %) |
| Halleluyah, Pinchivi (a human cover) | corchea | 360 ms | 1.24 / 1.10 | 0.78 | 89 % / 94 % |
| Chopin Prelude (vault, a human) | corchea | 280 ms | 1.34 / 1.22 | 1.02 | 92 % / 98 % |

All 37 songs of My Library and the vault were measured (scratch `grid4.py`); every song has 89 % or more of its onsets
on a semicorchea point except What Makes You Beautiful (92 %), Stay the Night (92 %) and the 7 Years copy `daf087e9`
(q=1000, 77 %). The "song played by a human" of the task is Halleluyah (Pinchivi): its drift is the largest of the
pop songs, and the grid still holds 89 % of its onsets on corcheas. 7 Years and 99 Red Balloons are steady (a
machine or a click): 7 Years is exactly 500 ms per negra.

Decision: a new note starts within 1 frame of a corchea point (easy, medium) or a semicorchea point (hard), or of an
original onset. The batch prompt lists the negras with their corcheas (`Grid.text`).

# 4. The measures (task 3.2) and the limits of the levels

`hands.py` is the research's tracker (`difficulty/hands.py`) on frames: one column per frame of a hand, a decoration
note joined to the next column of its hand, `orn` onsets out. Measures per hand: notes/s, columns/s, chord max and
mean, `span` (widest column), `reach` (widest range inside two negras), moves, `moves_s`, **`moves_q` (moves per
negra)**, moved semitones/s, big moves (> 7)/s, fast moves (< 0.25 s)/s, regular share, effort/s, notes per position,
`pattern` (share of negras whose shape repeats one of the two before, the Phase 2 right-hand study's measure).

Moves per second depend on the tempo: the brief's easy pattern (a low note, then the chord, each negra) moves once per
negra, 1.7 per second at 600 ms. Moves per negra separate the levels of the gallery (all 110 patterns measured,
scratch `gal_measure.py`, saved as `/home/app/04-3-phase-3/gallery_measures.json`):

| Left hand | moves per negra (median [range]) | span max | reach (range in two negras) |
|---|---|---|---|
| Easy (13 drawn, 1 Chopin) | 0.06 [0 - 0.6] | 9 | 10 [7 - 28] |
| Medium (10 drawn, 11 Chopin) | 0.19 [0 - 1.0] drawn, 0.55 [0 - 1.4] Chopin | 12 | 15 - 21 [9 - 31] |
| Hard (10 drawn, 5 Chopin) | 0.58 [0.1 - 1.0] drawn, 1.29 [0.5 - 2.0] Chopin | 12 | 22 - 28 [13 - 34] |
| Super hard (2 Chopin) | 1.96 | 12 | 27 - 46 |

Right hand: easy moves 0 to 0.2 per negra, medium 0 to 0.6, hard 0 to 3.0 (the pattern measure is weak on short
examples: many are 0).

`LIMITS` (in `levels.py`, told to the AI in each level's prompt):

| Level | R notes (short / negra or longer) | R span | L notes | L span | L reach | L moves per negra | New notes on | Shortest new figure |
|---|---|---|---|---|---|---|---|---|
| Easy | 1 / 1 | 0 | 3 | 9 | 24 | 0.75 | corcheas | semicorchea |
| Medium | 2 / 3 | 9 | 3 | 12 | 28 | 1.25 | corcheas | semicorchea |
| Hard | 3 / 4 | 12 | 4 | 12 | 31 | 2.0 | semicorcheas | any |

The right hand must not move more per negra than the sheet now (+0.1). Easy L reach 24 is lower than the gallery's
28 (`low-note-then-chord` keeps Do2/Sib1), because plan section 10 (review 1) asks the low note near its chord.

# 5. The chords

`harmony.chords`: per negra of the grid, a weight per pitch class (each note's sounding time in the negra, to the next
onset of its hand at most its figure; the lowest left-hand note + 1 negra of weight), matched with major, minor,
dominant seventh and diminished templates (score = inside - 0.6 outside, +0.15 when the bass is the root; a seventh
or dim must win by 0.12); same chords joined; a chord shorter than 2 negras joins the one before when it fits it within
0.2. On 99 Red Balloons: 145 chords, E - F#m - A - B every 2 to 3 seconds, as the song is.

# 6. The prompts and the answer (task 3.4)

- **System prompt of a run** = `shared.md` + `<level>.md` + "The patterns of this run" (the selected and named
  patterns, left hand first: ref, name, line, and the first `EXAMPLE_NEGRAS` = 8 negras of the first example's F1 text,
  both hands, with beams, clefs and 8va taken out). The same text for the plan request and every batch: cached. Sizes
  with 6 patterns: about 18,000 characters (about 5,000 tokens) per level.
- The open points of plan section 5.10 settled for this phase: the prompt gets **both hands** of a pattern's example
  (the other hand shows what it goes with), cut to 8 negras. Whether a run with no pattern selected uses default
  patterns of its level is left to Phase 4 (the dialog); Phase 3 uses the selection of `levels_gallery.SELECTION`.
- The prompts use the user's words, defined once for the AI: negra, corchea, octava, left-hand companion, pattern,
  decoration note, melody, artifact.
- **The answer** is F1 frames with hands and figures only; the app draws beams, clefs, 8va, accidentals and decoration
  notes by its rules (`levels.drawn`: answer -> `Notes` with the length of each figure -> `propose_frames`). Declared
  lines: `# pattern L f1042-f1440: left easy 2`, `# not melody f1084 E4: why`, `# artifact f863 D#7,E7: why`.
- The words of the user (`words`) go at the top of the plan request and of each batch; `refs_in` finds "medium 2",
  "left hard 3" (a number without a hand names it in each hand of the run). Frame places in the words reach the AI as
  written ("at frame 300" is the `f300` of the text).
- **Batches** of 16 to 24 s (`LEVEL_MS`), at most 260 onsets: a level answer writes every note of its hands, as a
  whole run's window does. Each batch sees: the plan (its sections marked), the chords, the grid, the measures now,
  the earlier passage like it as written (`like_before` on the original), the end of the previous batch as written
  (6 s), the target, the fixed hand (a run of one hand), the look-ahead.

Sizes on 99 Red Balloons: plan request about 9,700 characters (23 stretches of the summary); batches 3,600 (the riff)
to 7,100 characters (f1826-f2296).

# 7. The check (task 3.6)

`check_level` (plan section 5.5), in order: the format (F1, hands, only the hands of the run, frames inside the batch);
the **melody** (each note of the right hand's top line of the target at its frame ±1, same pitch or ±12, or declared;
"not melody" at most half of the line); an **artifact** is accepted only when it is more than an octava above the
median of the other melody notes within 3 s, or, when the melody line has nothing else near, more than an octava above
every other note of either hand within 3 s (a right-hand column goes with its artifact top note); the **harmony** (at
each chord whose first left-hand column is within a negra of its start, the lowest left-hand note is the original
bass or the root; left-hand notes outside the chord's tones and the original's pitch classes: at most 15 / 25 / 40 %);
**the level per column** (`LIMITS`); **hand motion** (L moves per negra, L reach; R not more than now); the **patterns**
declared for each hand rewritten, among the run's refs and of the right hand; **new notes** on the grid and not shorter
than the level's shortest figure.

Tried on a stand-in written by code (the melody in single notes; the bass, then the triad held, at each chord;
scratch `standin.py`) on the four passages: it passes on passages 1, 2 (riff, high chords declared artifacts) and 3;
on passage 4 it is refused because it called the melody around E6 artifacts (correct). Two rules changed on the way:
the artifact rule first looked only at the melody line (the riff's melody line is only the high chords), and the
moves were per second (section 4).

# 8. The gallery (task 3.8, first page)

`http://ubuntu:8099/04-3-phase-3/index.html` (the server of port 8099 serves the folder `gallery/`). Each passage: the
sheet now with a band (the segment of the whole song, as the page draws it), the chords, the measures of both hands;
then the patterns proposed per level (drawings of Phase 2) and the prompts (`prompts/system-<level>.md`,
`plan-easy.md`, `batch-easy-1042.md`). Checked at 2x: passages 2 and 3 match the two images of the brief; 18 images, 0
broken. With `--runs runs.json` the script adds the AI's version of each level under each passage.

# 9. Checks

| Check | Result |
|---|---|
| `pytest tests/test_sheet_levels.py` (in the running container: no GPU used, pure Python) | 19 passed |
| Existing code | not changed (new modules only) |

# 10. Needed later

- **Task 3.7** (after the user's ok): a scratch runner with `ClaudeComplete` (Sonnet 5.5) calling `write_level` with
  `windows=[passage]` for the four passages at each level, the plan request on the whole song once per level; save
  every reply and `Call`; write `runs.json` (`level|start` -> `text` of `levels.drawn` on the answer plus the original
  notes of the other hand outside the run, `measures`, `declared`, `replies`, `usd`, `model`) and rebuild the page.
  Estimate: about $0.06 per plan request and $0.08 to $0.15 per batch with retries, so about $0.6 per level and about
  $2 for the three (at most $3); Opus 5.5 on one passage if Sonnet 5.5 fails, about $0.3 more.
- **Phase 4**: `levels.drawn` passes the notes through `propose_frames`; the stored run must write the notes into
  `notes.pmn` (the rewritten hands' notes of the batch marked removed, the answer's notes added with the figure's
  length) and lay the sheet with `build.reapply`. The catalog data moves into the backend (`load_patterns` reads a
  folder with `patterns.json` and the F1 files). A run with no pattern selected: decide the default with the user.
- The grid of a stored song may be computed once per run (0.2 to 0.6 s per song).
