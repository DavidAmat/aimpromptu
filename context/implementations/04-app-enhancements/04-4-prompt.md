# 04-4 · Brief: copy this style

Written on 2026-10-30, at the end of implementation 04-3, from the user's request in the chat. Section 1 is the
request in the user's words; section 2 lists what already exists in the app and may be reused; section 3 lists the
points to settle in the first discussion. The guidelines say how to work and how to report
([`guidelines-implementation-plan.md`](../../guidelines/guidelines-implementation-plan.md),
[`guidelines-communication-with-user.md`](../../guidelines/guidelines-communication-with-user.md)).

# 1. The request (the user's words)

> What is left to do is that I select a given stretch. For example, I select only the right hand. After I do some
> manual modifications, I say, "Take this as the reference rhythm, figures, alterations, and way of writing the notes
> and alterations for the rest of the song." Whenever, for example, the right hand sees the same pattern of the song
> being played that is similar to this reference pattern that we select, we are going to change all the parts of the
> right hand (in order to match this reference section that we have highlighted).
>
> This should appear whenever we select a given range and we click on the AI button. Then we will have another tab on
> the top that says **"Copy this style"** so that I will be able to select also whether I want to affect both hands,
> right or left, and whether I want to put some words. Let's not put any level, because at the end, what we are
> trying to do is match similar passages in the song and make similar changes.
>
> The passages don't need to be exactly the same. This is very important to highlight. It is very important also to
> highlight that the song may repeat these kinds of passages and add some modifications. They make slight
> modifications, but the overall look of the passage should be copied from these decisions that we make in these
> passages that we use as a reference.

What this means for the design, in short:

- **The reference** is a stretch the user selected and edited by hand: its rhythm, its figures, its alterations (the
  spelling, such as Sib for La#), the way its notes are written (chords, octaves or thirds, beams, decoration notes,
  fingers...). It is the user's model of how this kind of passage should look.
- **The similar passages** are the other places of the song that play the same kind of passage: repeated, with slight
  changes (another note here and there, a different ending, a little more or less ornament). They are found by
  similarity, not by exact equality.
- **The change**: in each similar passage, the chosen hand or hands are written again so that they look like the
  reference, while each passage keeps what is really its own (its own notes where they differ, its harmony).
- **The dialog**: a new tab **Copy this style** in **Enhance with AI** when a range is selected: Both / Right / Left,
  and the user's optional words. **No level.**

# 2. What exists today (at the end of 04-3)

Read [`04-context.md`](04-context.md) and [`04-3-plan.md`](04-3-plan.md) (section 10 lists the late changes of 04-3).
The pieces most likely to be reused:

- **Enhance with AI** (`aitu-frontend/src/pages/piece/sheet/frames/EnhanceDialog.tsx`): two tabs (A stretch, The
  whole song) that share one layout: the hands, then how (a level, or the user's words), the cost and the minutes,
  the gallery of patterns inside the dialog. A third tab fits there.
- **The AI runs** (`aitu-backend/src/aitu_backend/part_sheet/job.py`): one job per part, every run with GPT-6.1 Terra
  at `medium` effort (`sheet_llm.OpenAIComplete`; the user's decision of 2026-10-30); a run that runs out of OpenAI
  credits says so on the page. The estimates of cost and minutes come from `job.costs`.
- **The level run** (`aitu_backend/sheet/llm/levels.py`): a plan of the song, then batches that each see the batches
  written before them and **the earlier passage most like this one** (`like_before`: "a chorus is written the same way
  each time"), a check by code with feedback, the answers drawn by the app's rules, and the storing through
  `edits.change_notes` (the notes into `notes.pmn`, one step of undo). Finding similar passages and keeping them alike
  is already a part of it.
- **A stretch with the user's words** (`sheet/llm/frames.py`, `write_stretch`): one request that may change pitches,
  figures and hands of a stretch, with the user's words above every other rule.
- **The user's marks of the sheet** (F1 frames text): `fix` (a figure set by hand), `sp` (a spelling set by hand,
  2026-10-30), `fg3` (a finger), beam groups, `asgrace`/`nograce`, ornaments. They are never sent to the AI today
  (`_strip_marks`): the reference's marks are exactly what this feature must carry over, so this is a point to design.
- **The note toolbox** (Duplicate, Unite, Alteration, Move) and **the range toolbox** (frame numbers, Delete these
  frames): the manual edits the user makes on the reference before asking.
- **The prompts** (`sheet/llm/prompt/frames/instructions.md` version 7, `levels/` version 2): the rules of simplicity,
  the user's rule "an octave as a third or a fifth".

The last 04-3 changes are on the branch `feat/04-3-enhance-dialog` until the user approves them; branch the new
implementation from `master` after that branch is merged (ask the user if it is not merged yet).

# 3. Points for the first discussion

The guidelines ask for a short discussion of the critical points before the plan. Likely ones:

1. **How similar passages are found**: by the hand's rhythm and contour, by the harmony, by `like_before`, by the AI,
   or a mix; how similar is "similar enough", and whether the user sees the list of matches (with their frame
   numbers) and can untick some before the run.
2. **What is copied**: the figures and the rhythm, the spelling, the chord shapes (octaves, thirds), beams and
   decoration notes, fingers; and what each passage keeps of its own (its different notes, its ending).
3. **Code or AI**: some of it may be a rule of code (spelling, beams, figures on matching notes), some needs the AI
   (a passage with slight changes); the cost and the time before the run, as the dialog shows today.
4. **Undo and review**: one step for all the passages changed, or one per passage; how the user sees what changed.
5. **The test case**: a song of the user where a passage repeats with changes (the user's choice), on a temporary
   copy, as the earlier phases did.
