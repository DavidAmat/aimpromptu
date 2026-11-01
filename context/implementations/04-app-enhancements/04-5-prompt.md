# 04-5 · Brief: the left hand follows the chosen pattern

Written on 2026-10-31, at the end of the session that built the requests between the phases of 04-3, so that a new
session can take over. Section 1 is the user's request; section 2 is what that session built and where it stands;
section 3 is what the stored runs show and the likely cause; section 4 lists the points for the first discussion;
section 5 lists the other open work. The guidelines say how to work and how to report
([`guidelines-implementation-plan.md`](../../guidelines/guidelines-implementation-plan.md),
[`guidelines-communication-with-user.md`](../../guidelines/guidelines-communication-with-user.md)).

# 1. The request (the user's words, 2026-10-31)

> I'm seeing that the new rewriting of the left hand, for example, given some template patterns, is not working
> well.

The user asked for this brief in the same message: a new session takes it over, with the record of what the last
session built (the model selector, the batches, and the stop of a run, among others).

## 1.1 The request of the new session (the user, 2026-10-31, with a screenshot of `946c21f2`, left hand only, easy 1, 4 batches, Terra)

1. **Both hands as context.** When a run rewrites the left hand only (or the right hand only), the prompt must also
   show the other hand: when the left hand should start, what the melody does.
2. **Decisions passed from batch to batch.** Each batch explains in one or a few sentences the criteria it used for a
   pattern it found; the next batches get these explanations, and the list grows batch after batch, so the same
   passage gets the same decision everywhere. Songs are circular: a pattern introduced first and repeated later must
   stay the same.
3. **The strictness of a pattern.** Each selected pattern has one of two levels: **Suggested** (the default: used
   where the pattern is suitable) and **Strict** (the whole hand plays that pattern, everywhere). The user's words
   may change a pattern a little, for example easy 1 (Held triad, Fa4-La4-Do5): "first a low note Fa3 as a blanca,
   then Fa4-La4-Do5 as a blanca"; the AI joins the pattern and the words into one strict pattern and plays it the
   same way through the whole piece. With Strict, a left hand that does not follow the pattern everywhere is not
   accepted.
4. **The history of the runs.** When a run ends, the right of the sheet shows the history of the AI runs and their
   events, the latest first. A click on a run shows the decisions of each batch, with a sentence of the AI in very
   simple words: what it decided, why, and why it did not do something. The user can answer the AI ("this statement
   is incorrect, you did not understand this; try again without doing this") and run that batch again.
5. **Freedom to test.** The user allows changing the project and running the request again on the song until the
   prompt does what is asked.

# 2. What the last session built, and where it stands

Every item has a dated paragraph in section 10 of [`04-3-plan.md`](04-3-plan.md), with its code, tests and checks.
Read those paragraphs from "A request between phases: the AI starts only from the button" to the end.

| Item | Section 10 paragraph | State |
|---|---|---|
| The AI starts only from the button; the whole song tab offers a level per hand, with the gallery of patterns inside the dialog | "A request between phases: the AI starts only from the button..." | Committed (`ca67aca`) |
| The prompts know "an octava as a third or a fifth" | "The user's rule..." | Committed (`fb880bd`) |
| Audio: **Only keep the selected part**; the time of the moving edge | two paragraphs | Committed (`5f864dc`, `b542831`) |
| Note toolbox: **Duplicate**, **Unite**, **Alteration**; range toolbox: **Delete these frames** | two paragraphs | Committed (`8dd4370`, `ec9c510`) |
| The 04-4 brief **Copy this style** | (the brief itself) | Committed (`4dd31bf`); its sections 1.1 to 1.3 are not |
| Gallery: **Select all**, **Deselect all**, **Approved**; a hand with no pattern is declared `free` (`exact`, level prompts version 3) | "Select all, Deselect all and Approved..." | Not committed |
| The **Info** tab: title, subtitle and artist editable, also during an AI run | "The Info tab..." | Not committed |
| The **model** (GPT-6.1 Terra by default, GPT-6.1 Sol, Sonnet 5.5) and the **batches** of every run, drawn on the sheet in colours, with - and + | "The model and the batches of every run" | Not committed |
| **Unite** with any figures; the **panel of an AI run** at the right: each batch's state, **Stop**, **Revert** (one step of undo) | "Unite with any figures; the panel of an AI run..." | Not committed |

**The branch.** Everything is on `feat/04-3-enhance-dialog`. The first five rows are seven commits that are not on
`master` yet; the rest (36 changed files and 4 new ones: `AiRunPanel.tsx`, `batches.ts`, `test_sheet_batches.py`,
`check-ai-run-panel.mjs`) is not committed. The user has not yet said whether to commit and merge (section 4,
point 1). `.cursorignore`, `.cursorindexingignore` and `.vscode/` are the user's own files: never commit them unless
the user asks.

**The checks at hand-off.** All 1,332 backend tests pass (on the CPU, without `test_transcription_transkun.py`);
`tsc` and `eslint` are clean; `check:enhance-dialog` (50 steps) and `check:ai-run-panel` (8 steps, a faked run) pass;
the link check passes. **Stop**, **Revert**, the model choice and the batches have been tested only with stand-ins of
the AI. No real run has tested them yet.

**Known limits.** Pause and resume were not built: **Stop**, then a new run on what is left. **Stop** waits for the
batch the AI is writing, up to about a minute with Terra and 2.5 minutes with Sonnet 5.5. Undo of a level stored after
a title edit made during its run puts back the title of before the run.

# 3. What the stored runs show

The user's left-hand level runs are on copies of **20 de Enero** (La Oreja de Van Gogh), the last one on `946c21f2`
(also `0df15e84`, `7b9a41e4`, `b13cbcde`), and one on `c4d9ab95`. All of them use GPT-6.1 Terra at the easy level. The
record line of each `sheet.f1` keeps every level run (`levels`: the plan, the batches, the declared patterns). An earlier
version of a part may still be in its history (`history/<uuid>/parts/<uuid>/v*/`).

| When (UTC) | Patterns | The user's words, in short | What the AI declared |
|---|---|---|---|
| 10-30 20:07 | `left easy 1`, `left easy 12`, `left easy 2` | "Put some uniformity on the chords... keep the current style" | Plan sections 2 to 4 are `L=keep` ("keep the marked simple spans"); a pattern only in short gaps |
| 10-30 20:46 | `left easy 5` (Low note, then two notes rocking) | "Apply to ALL the left hand this pattern..." | `left easy 5` on 6 short stretches; `keep` on more than 25 |
| 10-30 21:22 | `left easy 5` | "...Do it for ALL the left hand like this, irrespective of whether currently we have blancas, negras, corcheas..." | The same: `keep` on most of the hand |
| 10-30 21:25 | `left easy 5`, `right easy 2`, `right easy 1` | the same words, both hands | The same for the left hand; the last batch failed after 3 replies |
| 10-31 09:22 | `left easy 1` (Held triad) | none; 8 batches | Plan "L=keep: the left hand is marked simple throughout"; `left easy 1` on 2 stretches; 2 batches failed |

**The likely cause.** The level rules the user set on 2026-10-30 (04-3 plan section 10, "Phase 3, the user's review
of the first run"; `prompt/levels/shared.md`, "A level simplifies the sheet: never harder than it is now") forbid
exactly what these words ask:

1. **Simple stretches stay as they are.** Where the left hand plays single notes inside one octava, or one small chord
   again and again, the app marks the stretch simple (`levels.simple_stretches`, `SIMPLE_NOTES = 3`,
   `SIMPLE_SPAN = 12`). The summary of the song shows it as `L simple (keep)`, the plan prompt offers `L=keep` for it,
   and each batch lists it with "keep their notes". The left hand of 20 de Enero is mostly simple by this measure.
2. **The check refuses more.** In `levels.check_level` (the block after "never harder than the sheet now"), a simple
   stretch may not get another note, chords where it plays single notes, or more onsets. In every chord, the left
   hand may not have more onsets than now, and at least 70 % of its onsets (`RHYTHM_SHARE`) must be onsets of the
   left hand now.
3. A low note followed by rocking corcheas over a held fifth adds onsets and notes, so the check refuses it. The AI
   learns from the feedback that `keep` passes, so it declares `keep`. The user's words cannot lift a rule of the
   check, and the prompt does not say which wins.

This is a hypothesis from the stored plans and declarations. The AI's replies and the check's feedback are not
stored (only the plan, the batches' status and replies count, and the declared lines), so the first step is to
confirm it: for example, run `check_level` on the stored result of a batch, or store the check's errors per batch in
the record from now on.

**Confirmed on 2026-10-31 (the new session, no AI request).** The run of 10-31 09:22 (`left easy 1`, no words)
planned `S1 f5-f2187 L=keep | The left hand is marked simple throughout`, and `check_level` refuses "chords where
the sheet plays single notes" in a simple stretch, so a held triad cannot be written there. Each level copy of 20 de
Enero was made from the copy before it, so each run started from a left hand an earlier run had made simpler, and the
share of left-hand columns inside simple stretches grew run after run: `d6211999` 36 %, `7b9a41e4` 64 %, `0df15e84`
67 %, `b13cbcde` 85 %, `946c21f2` 81 %. The left hand of the screenshot is the rocking corcheas of the `left easy 5`
runs, kept as `keep`, with `left easy 1` on 2 short stretches; its last two batches (f1673-f2187) failed after 3 replies
and kept the old notes. Other facts: the batch prompt already shows the other hand ("fixed") and a look-ahead of both
hands; the plan prompt shows the other hand only as hand-tracker measures, never its notes. Each batch is its own
conversation: it sees the plan (sections and a short why), the last 6 s of the batch before as written, and one
earlier passage like it as written; never the reasons of the batches before. `WindowLog.errors` collects the check's
refusals, but `start_level` does not store them, nor the prompts or the replies.

**Where the code is.**
- `aitu-backend/src/aitu_backend/sheet/llm/levels.py`: `simple_stretches`, `song_summary` (the `L simple (keep)` line), `plan_prompt`, `read_plan`, `batch_prompt`, `check_level`, `write_level`.
- `prompt/levels/` (`shared.md`, `easy.md`, `medium.md`, `hard.md`, `feedback.md`, `VERSION` = 3).
- `catalog/patterns.json`.
- `aitu-backend/src/aitu_backend/part_sheet/job.py`: `start_level`, and the `levels` entry of the record.
- `scripts/levels_gallery.py`: draws a part's passages and the AI's versions, in the container.
- The tests: `test_sheet_levels.py`, `test_sheet_levels_app.py`.
- The Phase 3 report ([`04-3-implementation-phase-3.md`](04-3-implementation-phase-3.md)), sections 11 to 15, tells
  how these rules came about.

# 4. Points for the first discussion

1. **The branch first.** Commit what is not committed on `feat/04-3-enhance-dialog`, then merge it into `master`
   after the user's ok, before any new work: the new work changes the same files (`levels.py`, the prompts, the
   dialog).
2. **The cases.** Ask the user which runs looked bad and what they expected, with a screenshot if possible. Section
   3 lists the runs found; confirm that they are the ones the user means, or get the others.
3. **What should win.** When the user ticks a pattern and asks for it "everywhere" (or for all the left hand), should
   it override the rules of section 3? For example, a choice in the dialog such as "Apply the pattern to the whole
   hand", which lifts the simple-stretch rule and the onset rules for that run. Another way is to let the user's
   words decide. The rules exist because the user asked for them on 2026-10-30: the first AI runs had invented new
   rhythms and made simple passages harder. The new behaviour must keep that protection when the user does not ask
   for a pattern everywhere.
4. **Seeing why an answer was refused.** Store each batch's check errors in the record (or show them in the run's
   panel), so the next bad run explains itself.
5. **The test.** One song (20 de Enero, on a temporary copy), the left hand at easy with `left easy 5`, a short
   stretch first. Give the cost and ask before every real run.

# 5. Other open work

- The 04-4 brief [`04-4-prompt.md`](04-4-prompt.md): **Copy this style**. Its six discussion points were raised and
  not answered; no plan yet. Its section 1.1 (a button to **stop a transcription** on the Notes page; the user's
  answer: nothing of the stopped run is kept) and section 1.2 (**the first paste does not work** in the app's text
  boxes, mostly in the words of **Enhance with AI**; not reproduced yet, the user's Mac browser is unknown) are not
  built.
- 04-3 Phase 6 (documentation and closing) is not started: [`04-3-checklist.md`](04-3-checklist.md).
- A real test of **Stop**, **Revert**, the model and the batches (section 2), when the user agrees to its cost.

**Rules that matter here** (the agent's memory has them too):
- Never start an AI run without asking; give the cost first.
- Test on a temporary copy, never on a library piece.
- A backend `.py` edit reloads the backend and kills a running AI job, so check that none runs first.
- The app may be running on the real database.
- Run pytest on the CPU.
- Give the user links as `http://ubuntu:<port>`, never file paths.
