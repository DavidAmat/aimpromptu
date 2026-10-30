# 04-3 · Phase 3: the level prompts, tested on 99 Red Balloons

Status: **in progress** (2026-10-30). Tasks 3.1 to 3.6 are built and tested without the AI. Task 3.7: the run of the
user's choice (hard for the right hand, medium for the left hand) was made twice on the four passages, with rules
added after each of the user's reviews (sections 11 and 12; $1.58 in all); it waits for the user's review. Easy and
medium come after it. Branch `feat/04-3-phase-3` from `master` (`f85fa92`).

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

- **Task 3.7** (the runner of section 11 is the scratch `run_levels.py`; the description below was the plan for it): a scratch runner with `ClaudeComplete` (Sonnet 5.5) calling `write_level` with
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

# 11. The first AI run: hard for the right hand, medium for the left hand (task 3.7)

The user's answer (2026-10-30): start with hard, because the sheet now is at the super hard level; a level per hand,
hard for the right hand and medium for the left hand, both hands written together (notes move to the hand where they
belong); the agent chooses the patterns; one run of about $0.6; easy and medium later, after this one is approved.

- **A level per hand** (`levels.hand_levels`, `level_name`): `level` is a level or `{"right": ..., "left": ...}`.
  The system prompt is the shared part, a short head ("The levels of this run: hard for the right hand, medium for
  the left hand"; the hands are written together), the section "The right hand at hard" of `hard.md` and "The left
  hand at medium" of `medium.md`. The check takes the limits of each hand from its level (`LIMITS`); new notes use the
  grid of their hand (semicorcheas for the right hand at hard). Test `test_a_level_per_hand_takes_each_hand_part_and_its_limits`.
- **The patterns**: right hard 1 (melody with small pieces of chords), hard 17 (melody in octavas), hard 15 (chords
  climbing in corcheas), hard 4 (scale run, for fills); left medium 15 (octava, then two beamed chords), medium 2 (low
  note, then two chords), medium 10 (octava, then an arpeggio), medium 7 (octava bass in negras).
- **The runner**: scratch `run_levels.py` (in the container: `ClaudeComplete`, Sonnet 5.5, effort high), the plan
  request on the whole song, then `write_level(windows=PASSAGES)`; every call kept in
  `gallery/04-3-phase-3/runs/hard-medium/calls.json`, the results in `runs.json` (read by `levels_gallery.py --runs`).

| Request | Input (new / cache read) | Output | Seconds | USD | Check |
|---|---|---|---|---|---|
| Plan of the song | 5,351 + 8,517 written to the cache | 1,627 | 12 | 0.048 | ok (7 sections) |
| f33-f539 | 2,883 / 8,517 | 11,984 | 84 | 0.127 | ok, first reply |
| f783-f1042 | 2,414 / 8,517 | 4,364 | 33 | 0.050 | ok, first reply (then found wrong, below) |
| f1042-f1414 | 4,600 / 8,517 | 17,709 | 124 | 0.188 | ok, first reply |
| f1826-f2296 | 4,981 / 8,517 | 10,781 | 72 | 0.120 | ok, first reply |
| f783-f1042 again, with the riff rule | | 7,025 | | 0.097 | ok, first reply |

Total $0.63 (the user's budget was about $0.6). The output is mostly thinking: 4,000 to 18,000 tokens per batch. The
system prompt is 8,517 tokens in the API's count (the estimate of section 6, 5,000, was low).

The plan the AI wrote: S1 f33-f812 L medium 2, R hard 1 (intro and first verse); S2 f812-f1242 L medium 10 (the riff);
S3 f1242-f1826 L medium 2 (the verse again); S4 f1826-f2542 L medium 7 (the chorus, octavas in negras); S5
f2542-f3177 L medium 10 (the riff again); S6 f3177-f4104 L medium 7; S7 f4104-f4880 L medium 2 (bridge and end).
The right hand keeps hard 1 everywhere.

**The riff, first reply**: the AI declared only the D#7 and D#6 of the high chords and kept E7 and E6 as E6 (the
melody rule accepts an octava), and the riff (the top notes of the left-hand chords, E4 and C#4) disappeared: the
left hand played an arpeggio around E3, the right hand only three E6. This is the case of the brief's image, so two
rules were added:

- `shared.md`: an artifact is left out, never kept an octava or two lower; where the right hand has only artifacts or
  nothing, the top notes of the left-hand chords (a riff, the melody of an intro) move to the right hand.
- `check_level`: `hidden_line` (left-hand columns of 2 notes or more whose top is C4 or higher, with no right-hand
  note within a negra apart from the declared artifacts) joins the melody line: each top note must be in the right
  hand at its pitch or an octava higher, or declared. The first reply now fails (19 top notes missing). Test
  `test_where_the_right_hand_has_only_an_artifact_the_left_hand_tops_go_to_the_right_hand`.

**The riff, second reply** (same plan): the six high chords declared artifacts; the right hand plays the riff an
octava higher (E5, C#5, landing on G#4-C#5 and B4-E5 blancas); the left hand plays E2-E3 or C#2-C#3, then the
arpeggio (medium 10). Two decoration notes are left where the AI kept the recording's quick E5 then C#5 three frames
apart: the app's rule draws a fusa or shorter before a note as a decoration note.

The other passages (looked at zoomed): the intro keeps a low note, then two chords (medium 2) all through; f1042-f1414
changes from medium 10 to medium 2 at f1246 as its plan says; the high passage brings the melody from E6-G#6 down an
octava with two-note chords under it, over octavas in negras (medium 7). Measures of the answers (left hand, moves per
negra): 0.92, 0.75, 0.60, 0.45 (the sheet now: 0.6 to 2.0); widest left-hand column 9 to 12.

# 12. The user's review 1 (2026-10-30) and the second run

The user looked at the first run and gave three rules:

1. **Never harder than the sheet now.** The sheet now is the super hard version; where a hand already plays single
   notes or one chord again and again (the intro's left hand: E2 in an uneven rhythm, then a held fifth per chord),
   it keeps its notes and only its rhythm becomes regular and symmetric. The first run had put a waltz there.
2. **The new left hand approximates the left hand now**: the same main onsets, simplified (a negra octava and two
   corcheas of the chord stay a negra octava, or the bass, and two corcheas of the chord), never an arpeggio in
   corcheas or a waltz where the hand did not play one.
3. **The riff is the line of the top notes** of the left-hand chords (Mi, Mi, Do#, Mi, Do#, four times), every note
   of it in the right hand; at hard, with the fifth or the third of the chord under each note for power (Do5 with Sol4
   or Mi4).

What changed:

- `levels.simple_stretches` (`Simple`, `SIMPLE_NOTES` 3 keys, `SIMPLE_SPAN` 12): per chord, a left hand that plays at
  most three keys inside one octava is simple. The first version asked for single notes or one identical chord and
  missed the intro's E2 run (one column is E2+E3); widened. Shown in the summary of the song (`L simple (keep): f33-f159
  E2+E3 · ...`) and in each batch ("Simple stretches of the left hand"). The pattern `keep` is allowed in the plan
  (`L=keep`) and in the declared lines. The check refuses another key, chords where the hand played single notes, and
  more onsets than now in a simple stretch. Only the left hand: the right hand keeps its melody by its own rule.
- The rhythm of the left hand (`RHYTHM_SHARE` 0.7): in each chord, the answer has at most as many left-hand onsets as
  now, and at least 70 % of its left-hand onsets are left-hand onsets now (within a frame).
- `shared.md`: a section "A level simplifies the sheet: never harder than it is now" (rules 1 and 2), the plan request
  asks for the pattern whose rhythm is nearest, and the riff paragraph reads the line of the highest notes (rule 3).
  `hard.md`: the right hand's powerful two-note chords (rule 3).
- Tests: `test_a_simple_left_hand_keeps_its_notes_and_only_a_regular_rhythm`, `test_the_left_hand_follows_its_rhythm_now`
  (23 in all, passed). The first run's answers checked again: all four now fail (the intro: 18 simple stretches made
  harder, 14 of 41 onsets on the left hand's onsets; the riff: 10 of 24).

**The second run** (`runs/hard-medium-2/`, the same patterns): the plan has 11 sections, with `keep` for the intro
(S1 f33-f539), a break (f4104-f4259) and the end (f4666-f4880). $0.79:

| Request | Replies | Output tokens | USD | What the check refused first |
|---|---|---|---|---|
| Plan | 1 | 1,975 | 0.056 | |
| f33-f539 | 2 | 8,520 + 1,420 | 0.134 | f419-f458: chords where the sheet plays single notes |
| f783-f1042 | 2 | 6,198 + 963 | 0.099 | two new notes off the grid (f820, f947) |
| f1042-f1414 | 3 | 21,891 + 1,865 + 2,076 | 0.385 | a bass E3 where C#m begins; one note off the grid |
| f1826-f2296 | 1 | 10,355 | 0.116 | |

Then the riff again with rule 3 (same plan; scratch `rerun2.py`): 2 replies, $0.156. The right hand plays E4, E4, C#4,
E4, C#4 four times, each with the fifth under it (B3-E4, G#3-C#4); the left hand plays E2-E3, then corcheas of the
chord (medium 10, in the rhythm it had); the six high chords are declared artifacts. Note: the scratch rerun parsed the
plan lines with a pattern that does not read `L=keep`, so the plan shown in that one batch prompt had no left-hand
pattern for the keep sections (the riff's own section was read correctly).

Looked at zoomed: the intro keeps E2 in negras then the held fifths in blancas; the high passage keeps octavas in
negras; f1042-f1414 follows the left hand's rhythm (a negra or corchea bass, then two or three notes of the chord).

# 13. Three new hard left-hand patterns from Ballade No. 4 (the user, 2026-10-30)

The user asked to add to the catalog the left hand of Ballade No. 4, page 41, the second line (bars 3 to 5), as
alternatives at hard: semicorcheas in half bars of 6/8, each starting with a low note, after which the hand stays in
one position over the chord, with a passing note now and then, and a far note reached by the fifth finger. Read from
`052-1-BH.krn` (kdump) and checked on the page; three patterns, at the end of the hard left level so that no approved
number changes (checked: 0 refs changed):

| Ref | Id | Bars | Notes |
|---|---|---|---|
| left hard 16 | `broken-octave-then-notes-around-the-top` | 3 (also 5, 6) | G2, G3, F3+B3, G3, E3, G3; then C3, G3, C4, A3, G3 |
| left hard 17 | `low-note-then-line-with-a-passing-note` | 4, first half | C2, G3, C4, D4, E4 (D4 a passing note) |
| left hard 18 | `pivot-note-with-a-reach-below` | 4, second half (also the end of bar 2) | F2, C4, A3, C4, D3, C4 (D3 by the fifth finger) |

Tools of Phase 2: `crop.py` (`ballade4p41-left-6`, bar 3, and `-7`, bar 4 with the clef and key in front; files
`images/chopin_passages/ballade4-left-6.png`, `-7.png`), `build.py` (three entries at the end of `PATTERNS`), the
drawings by `transcribe.passage` and the generated run script in the container (`transcribed/ballade4-left-6.*`,
`-7.*`). The app writes Mi natural as Fab and Si natural as Dob under four flats; the notes of the examples say it. The
gallery of patterns now has 113 patterns (left 53, right 60).

Serving: the server on port 8099 (not started by this phase) serves the folder `gallery/`, so the edition's snapshots
(`../../images/...`) did not load there. A server on port **8097** serves the whole folder `04-app-enhancements/`:
`http://ubuntu:8097/gallery/04-3-phase-2/index.html` and `http://ubuntu:8097/gallery/04-3-phase-3/index.html`.
