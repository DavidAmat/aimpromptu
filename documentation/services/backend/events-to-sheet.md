> Context: [context/backend/time-model.md](../../../context/backend/time-model.md)

# From the stored notes (`notes.pmn`) to the hand split the sheet starts from

One stored file becomes the two hands the sheet is written from. This page follows that path step by
step, names the module each step lives in, and says why each step is where it is: several of the
orderings were arrived at by fixing a real defect, and moving one of them re-creates it. From the
hands on, the sheet is the new sheet's core (`aitu_backend/sheet/`, its
[README](../../../aitu-backend/src/aitu_backend/sheet/README.md), sections 9 to 17).

Until implementation 03, Phase 10 (2026-10-27) this page also followed the old sheet: the gaps, the
peaks, the ladder the reader named, the figure of each note, the tresillos, the trills, the score
payload and its drawing by `@aimpromptu/grid-notation` in the browser. That code was removed with
the vexflow-v2 sheet (section 6); git history keeps this page as it was.

---

## 1. Why so little is stored

A transcription is expensive: tens of seconds of model inference on a five-minute recording.
Everything after it is arithmetic. So the expensive result is stored and **nothing else is**:

```text
notes.pmn            the engine's note events, in milliseconds     KEPT FOREVER
  │
  ├─ the matrix at 40 ms      built per request (cached per notes.pmn save)
  └─ the hand split           built per request (cached per notes.pmn save)
sheet.f1             the sheet the AI or the algorithm wrote          STORED (implementation 03)
  └─ the drawn staff          drawn per request by the backend (SVG)
```

`aitu-backend/src/aitu_backend/transcription/pipeline.py` states the rule in its own docstring:
only the first arrow is expensive, and only its result is stored.

This is what makes `frameMs` a **parameter instead of a migration**: the hand split at 20 ms is
another computation, not another stored artifact. The split is kept in memory in the shared split
cache (`transcription/split_cache.py`), keyed by the uuid, `frameMs` and the modification time of
`notes.pmn`, so any save of the notes is a new key and an old split is never served.

The sheet is the exception, since implementation 03: writing it costs an AI run, so `sheet.f1` is
stored. It never goes stale for the page: a sheet stored for older notes is laid again on the
current ones (`part_sheet.build`).

`notes.pmn` holds the real onsets and releases in milliseconds, before any grid was involved, and it is
the only thing here that cannot be recreated (D-03). Until implementation 02, Phase 3 this file was
`events.json`; the code still reads it in that shape (note rows in seconds), converting at the file
boundary. Every measurement reads it (D-07).

The reader's own decisions are part of `sheet.f1` now (figures set by hand, fingers, beams, lyrics,
titles). The old sheet kept them in `sheet.json` (until implementation 02, Phase 3, `rhythm.json`),
which is still read for its marks (see [`rhythm-and-annotations.md`](rhythm-and-annotations.md)).

---

## 2. The path, in order

```text
audio
  └─ engine                    transcription/engine.py          notes in seconds
       └─ notes.pmn            transcription/pipeline.py        stored, kept forever
            │
            ├─ drop removed    time_pipeline.impose_granularity_and_split
            ├─ drop artifacts  transcription/artifacts.py       notes too short to be notes
            ├─ merge leaks     transcription/leakage.py         phantom re-strikes
            ├─ group chords    transcription/grouping.py        on RAW times, 40 ms window
            ├─ snap to columns transcription/events_to_matrix.py  round(ms / frameMs)
            ├─ split the hands matrix/hands.py + hands/         D-31
            └─ pin corrections time_pipeline.pin_hands          the reader's answer, last
                 └─ two hand matrices                           pipeline.inferred_split
                      └─ one hand per note                      pipeline.starting_hands
                           ├─ the algorithm  sheet/proposal/    propose_frames, ~0.2 s a song
                           └─ the AI         part_sheet/job.py  POST /sheet/{uuid}/llm
                                └─ sheet.f1                     stored
                                     └─ the drawing             sheet/engrave/frames.py (SVG), GET /sheet/{uuid}
```

---

## 3. Before the grid: what reaches it, and what does not

Three filters run on the events in seconds, and all three run there **because the judgement needs
seconds**. By the time events are columns, the evidence each one uses has been rounded away.

### Notes the reader took off

`impose_granularity_and_split` drops every event with `removed` set before the split, so a note taken
off never pulls the hand split. The sheet reads the live notes (`starting_hands` and `part_sheet`
skip removed notes the same way).

Removing a note is not cosmetic. A note's figure is chosen from its length up to the next onset of
its hand, so taking one off can rename its neighbour.

### Artifacts: notes too short to have been played

`transcription/artifacts.py`. Transcribing an octave is the hardest thing a piano model does: every
partial of the upper note lands on an even partial of the lower one, so the model has to infer it
from the attack transient alone, and it sometimes invents a note an octave *below* the real bass.

The invented ones give themselves away by length. Measured on one real recording of 2751 events,
the durations are cleanly bimodal: 78 events between 4 and 16 ms, **nothing at all between 16 and
32 ms**, and 2673 at 32 ms and up. The short cluster is a separate population, not a tail.

The floor is **20 ms and must not be raised much**. It is tempting to push it to 40 ms and that
would be a trap: the ByteDance offsets it was measured against are long, because they follow the
pedal rather than the key. Transkun, on the same audio, returns 34–85 ms notes for a passage
ByteDance calls 200–1700 ms, so a 40 ms floor would silently delete a third of a Transkun
transcription.

**Artifacts run before everything else.** One phantom bass note under a played octave spans two
octaves, which no hand can hold, so the hand splitter is forced into a wrong answer and the whole
assignment unravels. It also runs before the leakage filter, whose asymmetry test asks which other
keys attacked alongside a suspect note, and artifacts in that answer are noise.

Nothing is deleted from `notes.pmn`. The filter runs on the way out, so every rebuild gets it,
including recordings transcribed before it existed, and the raw falling view can still show what was
discarded.

### Leakage: phantom re-onsets

`transcription/leakage.py`. A key that is already sounding "re-onsets" when another key is struck.
The lag test is **two-sided**, because on one real recording the phantoms arrived 1–12 ms *ahead* of
the cluster rather than behind it, and a rule fitted to one file let all four through.

The asymmetry test compares company rather than demanding none: a genuine chord re-strike also gains
neighbours, and what separates the two is *which* keys those are. The same chord shares its pitches;
a phantom's are disjoint.

By the time events are columns, a 14 ms seam and a genuine repeated note look identical, which is
why this cannot move later.

---

## 4. Onto the grid

`transcription/events_to_matrix.py`, one function: `events_to_time_matrix`.

**Chord grouping happens first, on raw times** (D-04). A group admits later onsets within the window
of the group's **first** onset, not of the previous one, so an arpeggio cannot chain indefinitely.
The whole group then snaps to one column together.

The window is a fixed `GROUP_WINDOW_MS = 40.0` and **not** the frame length. It used to follow
`frameMs`, and that was wrong in a way worth stating: it let the column length change the *music*.
At 10 ms it conjured 22 semifusas that do not exist at 40 ms, and it broke the promise that
`frameMs` is only layout.

**Then onsets snap**: column index is `round(onset_ms / frameMs)` (D-02). Deterministic: the same
audio always produces the same columns, with no number for anybody to type in.

**Notes shorter than one column are dropped** (D-05), and **the sustain written into the grid is the
measured one, complete** (D-06). Nothing is capped here. The sustain is a measurement for the hand
split; the figure the sheet prints is chosen later, by the sheet's own rules.

Cell values: `1` onset, `-1` sustain, `0` silence.

---

## 5. The hand split

`matrix/hands.py` calls into `hands/`, a beam dynamic program over onset groups with a cost model
(`hands/costs.py`), candidate partitions per group (`hands/candidates.py`) and a gated second pass
(`hands/refine.py`, documented in
[`hand-inference-second-pass.md`](hand-inference-second-pass.md)). The old `Do-4` threshold survives
as `hands/threshold.py`, kept as a baseline.

**It runs here and not later** (D-31). The old sheet measured its gaps per hand, so the hands had to
exist first; the new sheet starts from one hand per note (`pipeline.starting_hands`: a saved hand that
was not guessed stays, every other note takes the split's), and the AI reads those hands as a
suggestion it may change. So the hands still have to exist before anything is written.

It also runs **before any collapse used to happen** in the old model, and the reason is recorded
because it cost a defect: two attacks closer than one display column merge into one column when
collapsed, and the splitter then sees a chord where the player struck twice. Measured at 5 such
pairs in 984 attack groups on the reference recording. There is no collapse any more, but the
ordering principle survives.

### The reader's correction wins

`time_pipeline.pin_hands` runs **after** the inference and moves the notes a person assigned a hand
to onto that hand.

Applied afterwards rather than as a constraint inside the search, deliberately. The search would
give a better answer if it knew the pins while it worked, but applying them last is honest about
what they are (a correction laid over a guess), and it cannot make the search fail to converge or
quietly change decisions the reader did not ask about.

A pin is found by the raw time the note was played at, not by a column, **so it survives a change of
column length**: the same correction holds at 20 ms as at 40.

A pin is refused rather than merged when the far hand already strikes that key in that frame. The
two planes may not hold the same onset, and losing one would lose a note that was really played.

---

## 6. From the hands to the sheet

Everything after the hand split belongs to the new sheet and is described in its README
([`aitu-backend/src/aitu_backend/sheet/README.md`](../../../aitu-backend/src/aitu_backend/sheet/README.md)):

- **The algorithm** (`sheet/proposal/`, section 9): the drawn column of each chord, the figures (the
  nearest plain figure to the note's own length, not past the next onset of its hand), the spelling,
  grace notes, beam groups, the armadura, clefs and 8va. The reference figure is `quarterMs`, the
  pulse estimate of `proposal.beat` unless the AI or the user gives it.
- **The AI** (`sheet/llm/`, `part_sheet/job.py`, sections 11 and 12): a reference request, then one
  request per window, checked by the same rules.
- **The drawing** (`sheet/engrave/frames.py`, section 10): the backend lays out the frames sheet and
  answers SVG; the browser only shows it.
- **The user's marks and edits** (`part_sheet/`, sections 13 to 17), and the marks of an old
  `sheet.json` (section 17).

**What went in implementation 03, Phase 10.** The old path after the split: `matrix/intervals.py`
(the gaps), `matrix/peaks.py` (the peaks the reader clicked), `matrix/ladder.py` (one name fixed all
nine figures), `matrix/bands.py` (where the line between two figures fell), `matrix/passages.py`,
`aitu_backend/notation/` (figures, tresillos, trills, transpose, decorative notes), and
`time_pipeline.to_score_payload`, which built the `TimeScorePayload` that `@aimpromptu/grid-notation`
drew in the browser. The payload's fields are in
[`deprecated/time-matrix.md`](../../deprecated/time-matrix.md). The new sheet has no tresillos,
no ties, no silencios, no compases and no tempo (plan section 3.1 of implementation 03).

---

## 10. Where to look deeper

- [`aitu-backend/src/aitu_backend/sheet/README.md`](../../../aitu-backend/src/aitu_backend/sheet/README.md): the new sheet, sections 9 to 17
- [`time-matrix.md`](time-matrix.md): the frame and the figure names that stayed
- [`endpoints.md`](endpoints.md): the routes (`/sheet`, section 4.1)
- [`transcription-pipeline.md`](transcription-pipeline.md): engines and their parameters
- [`hand-inference-second-pass.md`](hand-inference-second-pass.md): the gated repair pass
- [`rhythm-and-annotations.md`](rhythm-and-annotations.md): the old `sheet.json`, still read
- [`decisions.md`](../../../context/implementations/01-mvp/03-time-based-concept/decisions.md): D-01 … D-34
