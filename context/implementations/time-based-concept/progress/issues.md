# Issues — time-based concept

**Append only. Never overwrite an entry.**

Anything that contradicts a decision in [`../decisions.md`](../decisions.md) goes here, and the
worker who found it **stops** and waits for the human supervisor. A decision is not reinterpreted
inside a task.

Also record here any change to [`../contract.md`](../contract.md) made from a task, because a
contract that drifts only in code is what makes the parallel Phase 1–4 / Phase 5–6 split unsafe.

## Entry format

```
## I-nn — <short title>
Raised by: P<phase>.<task>, <date>
Decision(s) affected: D-nn
Status: open | resolved | withdrawn

**What was found.** ...
**Why it contradicts the decision.** ...
**Proposed alternative.** ...
**Resolution (filled by the supervisor).** ...
```

---

## I-01 — measured sustain cannot be capped at a redonda before a ladder exists

Raised by: P0.1, 2026-08-06
Decision(s) affected: D-06, D-09, D-15
Status: **resolved 2026-08-06.** D-06 rewritten; the cap moves to P3.3.

**What was found.** D-06 says the matrix stores measured sustain "capped at one redonda of the
active ladder", and P1.3 writes that sustain while building the matrix. At that moment no ladder
exists: D-09 says the user names the ladder, and the user only does that after seeing the peak plot,
which is computed from the finished matrix.

**Why it contradicts the decision.** The cap is defined in terms of a value that is not available at
the time the capped number has to be written. A piece can also carry several ladders (one per
passage, D-19), so "one redonda" is not a single number for the whole matrix.

**Proposed alternative.** Two options, both keep D-06's intent that a sustain longer than a redonda
is silence:

1. Store the full measured sustain in the matrix and apply the redonda cap when the score payload
   is built (Phase 3), where the passage and its ladder are known. The matrix then stays a pure
   measurement, which also matches D-03.
2. Cap at build time with a fixed wall-clock ceiling recorded in the envelope, and re-cap per
   passage later.

Option 1 needs no new field and keeps the matrix independent of any ladder choice.

**Resolution (filled by the supervisor).**

Option 1 of course, store the whole sustain an only when the user makes the decision on the peaks assignement you are able to know which note becomes a redonda so you can then cap its duration. Until the user has not make the assignment of 1 negra = X ms, you cannot know if a long sustain is a redonda or not.

---

## I-02 — the 2.0 envelope has no single-hand form, but the raw step produces one

Raised by: P0.1, 2026-08-06
Decision(s) affected: D-31, contract §2
Status: **resolved 2026-08-06.** Always two hands; `raw` dropped from the contract. New task P1.10.

**In plain words.** The pipeline builds one matrix for the whole keyboard first, and only splits it
into a right hand and a left hand afterwards (D-31). The new saved format in `contract.md` §2 always
asks for two matrices, one per hand, but it still lists `raw` as a valid step. The whole-keyboard
matrix that exists before the split has no right or left hand yet, so there is nowhere to put it.
The old format solved this with a single `matrix` field, which the new one removed.

**Why it contradicts the decision.** A `raw` matrix cannot be saved or sent at all in the new format.

**Proposed alternative.** Either bring back a single-matrix field, used only for the `raw` step, or
say that the new format describes only what reaches the sheet music renderer and keep the
whole-keyboard matrix in memory, never saved in that shape.

**Resolution (filled by the supervisor).**

Let's assume we will always receive two-hands. In case we want a one hand only, we can always do two-hands and put the lMatrix empty so all music is in rMatrix and have a simple flag that says "Hide Left Hand" or "Hide Right Hand" in Vexflow-V2. So the input matrix is always expected to show rMatrix and lMatrix. This way we totally drop this `raw` option. 

---

## I-03 — `alignWindowMs` cannot be applied by the renderer from the payload it receives

Raised by: P0.1, 2026-08-06
Decision(s) affected: D-24, D-25, contract §5
Status: **resolved 2026-08-06.** D-24 simplified; `alignWindowMs` removed; the whole pipeline uses
one window, `frameMs`.

**In plain words.** Two notes played almost together, say 15 ms apart, should be drawn one above the
other in the same place on the page. We told the sheet music renderer to use a 20 ms rule to decide
that. The renderer only receives column numbers, and one column is 40 ms wide, so it cannot tell
whether two notes were 15 ms or 35 ms apart. It cannot apply the rule it was given.

**Why it may not be a real problem.** The backend already groups notes played within 20 ms of each
other before it picks a column, so those notes already end up in the same column. Sharing a column
already means sharing a place on the page, and the renderer needs no milliseconds at all. The same
answer covers a note with no partner in the other hand: its column already says where it sits
between its neighbours.

**What is needed.** Confirm that the grouping looks at both hands together and not at each hand on
its own. If it does, the 20 ms number stays as information for the screen only, and P5.1 must be told
that the alignment already arrives done. If it does not, every printed note has to carry its real
time in milliseconds and the contract changes before Phase 5 starts.

**Resolution (filled by the supervisor).** Correct as read: there is no issue. Two notes played
15 ms apart *should* be drawn as a chord, and they already are, because they share a frame. The
20 ms window was only ever the grouping rule; from now on the whole pipeline uses one window and it
is `frameMs`. `alignWindowMs` is removed from the contract.

---

## I-04 — the 1.x builder is kept alive through Phases 1 to 3, against P1.8's "no code path accepts a tempo"

Raised by: P1.3, 2026-08-06
Decision(s) affected: none; this is a deviation from `plan.md` P1.3 and P1.8, not from a `D-nn`
Status: **confirmed 2026-08-06.** Keep the old code until the migration is proven; P1.5 and P1.6
move to P4.2.

**In plain words.** The plan says to delete the old code as soon as the new code exists. The part
that joins everything together, the transcription pipeline, is only rebuilt much later, in Phase 4.
Deleting the old code now would therefore leave the app unable to transcribe anything from the middle
of Phase 1 until the end of Phase 4.

**Why that matters here.** David checks this work in the browser and asked for a list of things to
try there. Three phases with an app that cannot transcribe makes that impossible, and it also removes
the chance to compare the new columns against the old ones on a real piece.

**What was done instead.** The new builder `events_to_time_matrix` was added alongside the 1.x
`events_to_raw_matrix`, which is unchanged and still used by `pipeline.py`. `PianoMatrix` gained an
optional `frame_ms`: when it is set the matrix is a time matrix, `time_step_seconds` comes from the
frame length and `beats_per_column` raises. When it is absent the matrix behaves exactly as before.
The whole existing test suite still passes with the same two pre-existing failures.

P1.8's no-tempo assertion is therefore written against `events_to_time_matrix`, not against the
module. Deleting the 1.x builder, the `frame_ms is None` branch and the `granularity` and
`tempo_bpm` fields belongs to P4.2 and P4.4, where the pipeline is rewired in the same task.

**Resolution (filled by the supervisor).** "You are doing the right approach to keep the code and
don't delete it until we are sure we migrated it and it works." P1.5 and P1.6 therefore move to P4.2,
where the pipeline is rewired in the same task.: You are doing the right approach to keep the code and don't delete it until we are sure we migrated it and it works

---

## I-05 — a raw event has no hand, but `GET /matrix/{uuid}/peaks` takes a `hand` filter

Raised by: P2.4, 2026-08-06
Decision(s) affected: D-08, D-31
Status: **resolved 2026-08-06.** Option 3: the hand split moves earlier, to the new task P1.9.
Everything downstream reads split hands.

**In plain words.** The plot of gaps that the user clicks on has to be measured one hand at a time.
Mixing the hands fills it with gaps between a right-hand run and a held left-hand chord, which nobody
would call a rhythm, and the peak the user is meant to name disappears under that noise.

The gaps are measured from the raw recorded note times, and at that moment we do not yet know which
hand played each note, because the hand split happens later in the pipeline. The endpoint takes a
`hand` parameter and has nowhere to read the answer from.

**The three ways out.**

1. **Look each note up in the two hand matrices already saved for that piece.** Every note is in
   exactly one of them, so the answer is there. The note keeps its exact recorded time; the saved
   matrices are asked only "which hand", never "when". This is what the proof of concept did, it
   works today, and the code already exists in `tests/test_matrix_peaks.py`.
2. **Read the saved hand map**, one letter per note. Cheaper, but it is tied to the old storage
   layout and P4.4 changes that layout underneath it.
3. **Wait for P4.3**, which moves the hand split earlier. After that the hand is known in the same
   place the notes are, and no lookup is needed.

Option 1 unblocks the peak plot now and is thrown away later by option 3. Option 3 is cleaner and
means the peak plot cannot exist until Phase 4.

**Resolution (filled by the supervisor).** Option 3, moved earlier rather than waited for: the split
happens right after the granularity is imposed, and from then on everything relies on the two
separate hands. The order is raw onsets, impose the granularity, split the hands, measure the peaks,
attach a figure to each duration in milliseconds. That is the whole pipeline, and it should read that
simply in the code. Recorded as the new task **P1.9**, and D-31 now carries the diagram.

---

## I-06 — P4.2's deletions cannot land while the five tempo-based tabs are still there

Raised by: P4.2, 2026-08-07
Decision(s) affected: none; this is a deviation from `plan.md`'s task order, not from a `D-nn`
Status: **resolved 2026-08-07.** The five tabs are retired inside P4.2. P7.11 is finished by it.

**What was found.** P4.2 deletes `matrix/granularity.py`, `matrix/approximation.py` and
`matrix/tempo_map.py`. Those modules are not used only by the pipeline. Five Playground tabs read
them through the `/matrix` and `/notation` routes, and all five still send a tempo and a granularity
on every request: Matrix, Piano Roll, Notes Falling, Notes Falling (raw) and Music Notation.

Deleting the modules therefore leaves five screens in the app that open and then fail.

**Why it is a problem for the plan rather than for a decision.** `plan.md` puts tab removal in P7.11
and `checklist.md` marks P7.11 blocked on P4.5, which comes after P4.2. Read literally, P4.2 cannot
be completed in the position it occupies.

**Why the blocker turned out to be conditional.** P7.11 was blocked on P4.5 because the older tabs
were the only way to open a stored artifact until the migration had run. P4.1 measured that
assumption on the real tree and it does not hold: there is exactly one stored artifact, its
`events.json` is intact, and the Rhythm tab already reads it directly with no migration step. So the
dependency was real when it was written and is no longer real for this data.

**Proposed alternatives.**

1. Retire the five tabs inside P4.2. The app keeps working, the old model leaves the repository in
   one piece of work, and P7.11 is finished early. The cost is that the piano-roll view, the
   falling-notes views and the grid editor disappear with no replacement.
2. Delete only `tempo_map.py`, which nothing imports, and leave the other two until the tabs go.
   Nothing breaks, but P4.2 stays open and the tempo-based model stays in the repository through the
   rest of Phase 4.
3. Rebuild Piano Roll and Notes Falling on the wall-clock path and retire only Matrix and Music
   Notation. Keeps the two views most useful for auditing a transcription, and is a larger task.

**Resolution (filled by the supervisor).** Option 1: retire the five tabs now, in P4.2. Recorded
here rather than decided by the worker, because removing five screens is a product choice.
