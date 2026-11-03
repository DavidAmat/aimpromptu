# The level run: a plan, then batches, each checked

> Context: [README.md](README.md). The code of the run is in
> [documentation/services/backend/ai-levels.md](../../documentation/services/backend/ai-levels.md) (section 8: the
> functions, the constants, the prompt files). What a level is, the catalog and the chords: [levels.md](levels.md).

A **level run** writes one or both hands of a passage again at **Easy**, **Medium** or **Hard**, in the shape of the
patterns the user picked. It starts from the levels part of **Enhance with AI** (the tab **A stretch** for a range,
the tab **The whole song** for the song). The whole-song choice makes a **level copy**: a new project, and the
original does not change. Both start the same run.

The run is one job in the background. The sheet changes as each batch is accepted, and the user can stop it.

## What the run does, in order

1. **The plan** (one request to the AI). The AI reads a summary of the whole passage and splits it into **sections**.
   For each section it gives one pattern to each hand, and one **rule** for each pattern it used.
2. **The batches** (one request each, one after the other). The passage is cut into batches. The AI writes the
   notes of each batch again, and declares the patterns and the notes it leaves out.
3. **The check** (code, no AI). Every answer is checked against the level. A failed answer goes back to the AI with
   the problems, up to three replies in all.
4. **The store.** The accepted batches are written into the part as one step of undo (the label reads
   `Level easy with AI, the left hand`, or the levels of each hand). The batches that were not accepted keep the notes
   they had.
5. **The wait** (a run of two batches or more). The run writes the plan and the first batch, stores them, and waits.
   The user reads the first batch, may answer the AI, and then goes on. The waiting state and the history of the
   runs are told in [run-history.md](run-history.md).

Outcomes, as the job reports them: `ok` (stored), `failed` (no batch was accepted, so nothing changes), `stale` (the
notes changed while the AI worked, so nothing is stored), `gone` (the part was deleted).

**Stop** asks the run to stop at its next request. The batches it already accepted are kept and stored, on the level
copy (the song itself does not change). **Revert** takes the whole run back. This is the user's choice (2026-11-03,
implementation 04-7): a Stop does not throw the run away.

## The plan of the song

The plan request gets a **summary** of the passage. It is one line per stretch of 6 to 10 seconds, ending at a pause
(`SUMMARY_MS`). Each line gives:

- the frames and the clock of the stretch, and the chords the app found in it (`harmony.py`, no AI);
- how each hand plays now (the **measures** of the hand tracker: notes per second, the widest column, the range in
  two negras, the moves per negra);
- the **melody** of the right hand (up to 24 notes, `SUMMARY_MELODY`), even when only the left hand is rewritten;
- the **simple stretches** of the left hand, marked `keep` (not when the left hand is Strict);
- the earlier stretch that sounds the same, when there is one.

The answer is a block with one line per section. Each line gives the frames, the pattern of each hand (`L=left easy 2`,
`R=right easy 2`), or `keep` for a simple left hand, or `free` for a hand with no pattern, and a short why:

```text
S1 f33-f780 L=left easy 2 R=right easy 2 | the intro: the same shape, the melody alone
```

The code checks the answer (`read_plan`). The sections must cover the passage from its first frame to its last, with
no gap and no overlap. Every hand must have a pattern (or `keep`, or `free`). Each pattern must be one of the run's
patterns, of the right hand. A Strict hand uses only its Strict patterns. A rule line must follow for each pattern
used (`rule left easy 2: ...`, `read_rules`). When the user gave a guide's chords, the plan writes after each `|` the
chords of the section, in order.

The plan is kept whole in the run's log, with its conversation. It is checked at most three times. When the three
replies are not accepted, the run stops with `failed` and writes nothing.

## The rules of the run

A **rule** says how this song plays a pattern, or a decision a batch took for a kind of passage. For example: which
notes of the chord, in which octava, with which figures, and what happens when the chord changes before the shape
ends.

- The plan's rules come first. Each batch then gets **all** the rules of the run so far, under **The rules of this
  run**, and must follow them. Songs come back to what they played before, so the same passage is written the same
  way.
- A batch may add its own rule with a `# rule:` line. The next batches get it too (`Rule.source` is `batch 2`, for
  example).
- A user's words that change a pattern are part of its rule. The shared prompt says they change the pattern of this run.

## The batches

A **batch** is 16 to 24 seconds of music (`LEVEL_MS`), with at most 260 onsets (`LEVEL_ONSETS`), when the run has no
batch count of its own. The dialog may ask for a number of batches (`batches`): then the passage is cut into that many,
of about the same time (`split_windows`). The dialog's preview keeps each batch between 3 and 90 seconds
(`BATCH_MIN_S`, `BATCH_MAX_S`).

Each batch request holds, in this order:

- the user's words (of the utmost importance, when there are some);
- the plan, with the sections of this batch marked `>`;
- the rules of the run so far;
- the Strict patterns of this batch, when there are some;
- the chords of the batch (from the app's harmony);
- the simple stretches of the left hand, to keep (`keep`) or to play only where the pattern is not harder;
- the **grid** of the batch: the negras, with the other corcheas of each negra in brackets. A new note starts on one of
  these frames, or at the frame of a note the target already has (and, for a hand on the semicorchea grid, half way
  between two of them);
- how each hand plays now (the hand tracker);
- an earlier passage like this one, as the run wrote it, when there is one (the same passage is written the same way);
- the **decided context**: the last 6 seconds of the previous batch, as written (`CONTEXT_MS`), when that batch was
  accepted and ends where this one begins;
- the **target**: the notes of the batch as the sheet has them now. The AI writes them again;
- the **fixed** hand, when only one hand is rewritten. It must not be written, and the new hand must fit with it;
- a **look-ahead**: the next 4 seconds of notes, as they are now (`LOOKAHEAD_MS`). They must not be written.

The answer is one block: the two header lines, the notes of the batch (`L:` and `R:`), the `# pattern` lines (one per
hand and section, with its frames), the `# not melody` and `# artifact` lines for the melody notes left out, at least
one `# explain:` line, and any `# rule:` line. The explain lines are for the user. They say in simple words what the
batch did, why, and what it did not do.

A batch that is not accepted after its three replies keeps no answer. The run goes on with the next batch. The
exception is an error of the AI itself (for example, no credits): the run stops there, and the batches accepted so far
are stored.

## The check, and its limits per level

`check_level` reads the answer and returns the problems in plain words. Each rule below is one check.

- **Format.** The answer starts with `F1 frames`. Every note has a hand (`L` or `R`) of the hands rewritten, and a frame
  inside the batch. The fixed hand is not written.
- **The melody.** Each note of the right hand's top line stays at its frame, with its pitch or the same name an octava
  away. At easy and medium the note may move by one semicorchea. A note may be left out only when it is declared, and
  at most half of the top line may be declared (`MELODY_DROP_SHARE`). A note declared an **artifact** must sound more
  than an octava above the melody around it (within 3 seconds, `ARTIFACT_S`).
- **The riff.** When both hands are rewritten and the right hand has no melody there, the top notes of the left-hand
  chords are the melody. They must go to the right hand, at their pitch or an octava higher, or be declared.
- **The harmony.** At the start of each chord, the lowest left-hand note is the bass of the song or the root of the
  chord. Most left-hand notes are notes of the chord, or notes the sheet already has in that stretch. The share of
  notes outside them that is allowed depends on the level (see the table). A Strict hand is not asked for the bass of a chord
  shorter than two negras.
- **Notes per column and span**, per hand (the table below).
- **Hand motion.** The left hand moves at most the number of times per negra in the table, and covers at most the
  reach in two negras. The right hand must not move more than it does now (plus a tenth).
- **Patterns.** Each hand declares its pattern, of its own hand, from the run. A Strict hand declares only its Strict
  patterns, over all its columns.
- **Never harder than now.** For each simple stretch of the left hand (Suggested): no new notes outside the chord, no
  chords where the sheet plays single notes, and no more onsets. For each chord, the left hand has no more onsets than
  now, and at least 70 % of its onsets are onsets it has now. A Strict hand is not held to these two rules.
- **Time and figures.** Each new note starts on the grid of its hand. At easy and medium, no figure is shorter than a
  semicorchea and no two notes of one hand are closer than a semicorchea (a steady rhythm). At hard, no new note is
  shorter than a fusa (the user, 2026-11-03, implementation 04-7), except a note the app draws as a decoration note
  (one or two fusas or shorter just before a longer note): the check draws the answer once by the app's rules to know
  them.

The numbers per level (`LIMITS`, `OUTSIDE_SHARE`):

| | Easy | Medium | Hard |
|---|---|---|---|
| Right hand, notes per column (on a negra or longer / on shorter figures) | 1 / 1 | 3 / 2 | 4 / 3 |
| Right hand, span of a column (semitones) | 0 | 9 | 12 |
| Left hand, notes per column | 3 | 3 | 4 |
| Left hand, span of a column (semitones) | 9 | 12 | 12 |
| Left hand, reach in two negras (semitones) | 24 | 28 | 31 |
| Left hand, moves per negra | 0.75 | 1.25 | 2.0 |
| Left hand, new notes on | the corcheas | the corcheas | the semicorcheas |
| Left hand, share of notes outside the chord | 15 % | 25 % | 40 % |
| Shortest figure of a new note | semicorchea | semicorchea | fusa (a decoration note may be shorter) |
| Steady rhythm | yes | yes | no |

The right hand's new notes start on the semicorcheas at every level.

## Strict and Suggested

Each pattern the user ticks in the gallery is **Suggested** (the default: used where it suits the passage) or
**Strict** (the hand plays it on every chord of the whole song).

- A Strict hand plays its pattern the same way from the first chord to the last. It has no `keep` and no other
  pattern. The simple-stretch and onset rules do not hold for it, so it may have more or fewer onsets than now.
- The prompt asks that a Strict pattern keeps its figures through the song: a pattern in blancas stays in blancas, and
  a longer chord plays the same figure again. The check does not count figures; it reads only the notes and the
  declared patterns.
- Only the Strict patterns that were also ticked count. A Strict mark on a pattern not ticked is dropped.
- The plan and each batch say which pattern is Strict, in their own lines.

## The patterns of a run

- The run's patterns are the ones ticked in the catalog, plus the ones the user's words name (`left medium 2`). When a
  hand has none, it gets the **approved** patterns of its level (`defaults`), unless the user chose **Deselect all**:
  then the hand has no pattern, and the AI writes it by the rules of its level and the words only (`free`).
- Each pattern is given to the AI with its name, its line, and the first eight negras of its example
  (`EXAMPLE_NEGRAS`), with the other hand's notes that go with it. The AI copies the **shape** of the example (the
  rhythm, the order of the notes, how far apart they are), and plays this song's chords in it.
- The super hard patterns are in the catalog and the gallery. No level writes at super hard yet.

## The cost and the time

A level run uses the model of the setting by default; the dialog may choose another ([README.md](README.md), "The
model and the cost"). The estimate the dialog shows is about **$0.015 and 10 seconds** for the plan, and about **$0.025 and 45 seconds** for each
batch (`USD_LEVEL_PLAN`, `USD_LEVEL_BATCH`, `SECONDS_LEVEL_PLAN`, `SECONDS_LEVEL_BATCH`). These were measured with one model
(`llm_models.MEASURED_WITH`); the dialog's preview scales them by the ratio of the model chosen (`llm_models.ratio`). The cost of the run that was
spent is stored with the run (in USD, with the number of requests), and the step it makes in the part.

## Where to look deeper

- [documentation/services/backend/ai-levels.md](../../documentation/services/backend/ai-levels.md): section 8, the
  functions and constants of the run, and the prompt files
- [levels.md](levels.md): what a level is, the catalog, the grid, the chords of the song
- [stretch.md](stretch.md): a stretch of the sheet with the user's words
- [whole-run.md](whole-run.md): the other whole-song run, which rewrites the song in one kind of run
- [README.md](README.md): the AI in the app, the kinds of run, the model and the cost
