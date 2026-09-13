> Context: [context/backend/time-model.md](../../../context/backend/time-model.md)

# From `events.json` to a drawn sheet

One stored file becomes a printed staff. This page follows that path step by step, names the module
each step lives in, and says why each step is where it is — several of the orderings were arrived at
by fixing a real defect and moving one of them re-creates it.

---

## 1. Why so little is stored

A transcription is expensive: tens of seconds of model inference on a five-minute recording.
Everything after it is arithmetic. So the expensive result is stored and **nothing else is**:

```text
events.json          the engine's note events, in seconds          KEPT FOREVER
  │
  ├─ the matrix at 40 ms      built per request
  ├─ the gap distribution     built per request
  ├─ the figure of each note  built per request
  └─ the drawn staff          built per request, in the browser
```

`aitu-backend/src/aitu_backend/transcription/pipeline.py` states the rule in its own docstring:
only the first arrow is expensive, and only its result is stored.

This is what makes `frameMs` a **query parameter instead of a migration**. Reading the same piece at
20 ms is another request, not another stored artifact, and there is no state on disk that could
disagree with what the screen shows. The cost is a second or two per request on a long piece, and
what it buys is a system with no stale state in it.

`events.json` holds the real onsets and releases in seconds, before any grid was involved, and it is
the only thing here that cannot be recreated (D-03). Every measurement reads it (D-07).

The one thing stored **beside** it is the reader's own decisions, in `rhythm.json` — see
[`rhythm-and-annotations.md`](rhythm-and-annotations.md). Those are not derivable from anything,
because a person chose them.

---

## 2. The path, in order

```text
audio
  └─ engine                    transcription/engine.py          notes in seconds
       └─ events.json          transcription/pipeline.py        stored, kept forever
            │
            ├─ drop removed    time_pipeline.impose_granularity_and_split
            ├─ drop artifacts  transcription/artifacts.py       notes too short to be notes
            ├─ merge leaks     transcription/leakage.py         phantom re-strikes
            ├─ group chords    transcription/grouping.py        on RAW times, 40 ms window
            ├─ snap to columns transcription/events_to_matrix.py  round(ms / frameMs)
            ├─ split the hands matrix/hands.py + hands/         D-31
            └─ pin corrections time_pipeline.pin_hands          the reader's answer, last
                 └─ two hand matrices
                      │
                      ├─ gaps          matrix/intervals.py      per hand, on raw times
                      ├─ peaks         matrix/peaks.py          the plot the reader clicks
                      ├─ ladder        matrix/ladder.py         one name fixes all nine
                      ├─ bands         matrix/bands.py          where the line between two falls
                      ├─ figures       notation/figures.py      one per printed note
                      └─ tresillos     notation/tuplets.py      three even gaps, marked
                           └─ TimeScorePayload                  GET /time/{uuid}/score
                                └─ @aimpromptu/grid-notation    the drawing, in the browser
```

---

## 3. Before the grid: what reaches it, and what does not

Three filters run on the events in seconds, and all three run there **because the judgement needs
seconds**. By the time events are columns, the evidence each one uses has been rounded away.

### Notes the reader took off

`impose_granularity_and_split` drops every event with `removed` set, and that is the **only** place
it happens. Doing it once means the gap plot, the sheet and the printed page agree about it without
any of them knowing the flag exists.

Removing a note is not cosmetic. A note's printed length is the gap to the next onset in the same
hand (D-14), so taking one off renames its neighbour.

### Artifacts — notes too short to have been played

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
keys attacked alongside a suspect note — artifacts in that answer are noise.

Nothing is deleted from `events.json`. The filter runs on the way out, so every rebuild gets it,
including recordings transcribed before it existed, and the raw falling view can still show what was
discarded.

### Leakage — phantom re-onsets

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

**Then onsets snap**: column index is `round(onset_ms / frameMs)` (D-02). Deterministic — the same
audio always produces the same columns, with no number for anybody to type in.

**Notes shorter than one column are dropped** (D-05), and **the sustain written into the grid is the
measured one, complete** (D-06). Nothing is capped here: a redonda has no length until the reader
names a peak, so the cap is applied when the score payload is built. The sustain is a measurement
and is never the printed length of the note — the two must never be derived from each other.

Cell values: `1` onset, `-1` sustain, `0` silence.

---

## 5. The hand split

`matrix/hands.py` calls into `hands/`, a beam dynamic program over onset groups with a cost model
(`hands/costs.py`), candidate partitions per group (`hands/candidates.py`) and a gated second pass
(`hands/refine.py`, documented in
[`hand-inference-second-pass.md`](hand-inference-second-pass.md)). The old `Do-4` threshold survives
as `hands/threshold.py`, kept as a baseline.

**It runs here and not later** (D-31), for one reason: gaps are measured per hand. The gap between a
right-hand run and a held left-hand chord is not a rhythm, and measuring it would bury the peak the
reader is meant to name. So the hands have to exist before anything is measured.

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
what they are — a correction laid over a guess — and it cannot make the search fail to converge or
quietly change decisions the reader did not ask about.

A pin is found by the raw time the note was played at, not by a column, **so it survives a change of
column length**: the same correction holds at 20 ms as at 40.

A pin is refused rather than merged when the far hand already strikes that key in that frame. The
two planes may not hold the same onset, and losing one would lose a note that was really played.

---

## 6. Measuring: gaps, peaks, ladder

### Gaps

`matrix/intervals.py` and `figures.gaps_of_hand`. Distances between consecutive attacks, **per
hand**, measured on the raw timestamps.

### Peaks

`matrix/peaks.py`. A Gaussian kernel density estimate over the gaps (`DEFAULT_BANDWIDTH_MS = 12.0`,
a 1 ms grid, gaps up to 1200 ms), with peaks kept when they hold at least 2 % of the gaps and are at
least 25 ms apart.

This is the picture the reader is asked to read, and the reason it exists at all is D-09: **the app
never chooses the ladder.** Interval statistics fix a ladder only up to a rational factor — a beat
and twice that beat explain the same gaps equally well, and on one real piece's second half two
candidates scored within 0.1 % of each other. So the app presents and the reader decides.

`peaks_of` also reports a warning when the gaps look like they came from a grid rather than from
playing, in plain language, because it is shown to the reader as written.

### The ladder

`matrix/ladder.py`. `build_ladder(anchor_figure, anchor_ms)` scales `FIGURE_NEGRAS` by the reader's
one choice, so naming a single peak fixes all nine figures by proportion (D-10).

`label_peaks` then says what every other pile becomes, with `percentOff` for each, so the
consequence of the choice is visible before it is committed. `_third_of` names a pile at a third of
the **negra** — and only the negra, within 8 % — as `corchea de tresillo`. Only the negra, because
two thirds of a negra is also a third of a blanca and the long half of a swung pair lands almost
exactly there; naming that a tresillo would tell a reader the piece is in triplets when it is
shuffled.

`shift_ladder` re-points the whole ladder by whole steps: `negra = 300` becomes `blanca = 300` and
everything below shifts with it (D-18). Purely a relabelling — positions do not move.

`bpm_of` and `header_label` produce the passage header, `negra = 320 ms · ≈188 BPM`. That printed
string is the only place a BPM appears in the product, and it is text rather than a stored quantity.

---

## 7. Naming each note

`notation/figures.py`, entered from `time_pipeline.to_score_payload`.

**Printed length is the time from this onset to the next onset in the same hand** (D-14), capped at
one redonda (D-15). Per hand, not per key: a chord is the group from D-04 and its length runs to the
next onset in that hand.

The accepted cost, stated plainly: a held note inside one hand is cut short when that hand plays
anything else. That is deliberate. The alternative fills the page with ties, rests and inner voices,
which is the ugliness being removed, and the player already knows the piece. There are **no ties**
(D-13) and **no rest glyphs** (D-16) — silence is read from the spacing and the dashed lines.

**The figure is the nearest by proportion, not by milliseconds** (D-11): compare
`|log2(gap / candidate)|`. With a negra of 320 ms, a 120 ms gap is exactly 40 ms from both 160 and
80 — a coin toss in absolute terms, and 25 % against 50 % proportionally, where corchea wins cleanly
and always.

### Where the line between two figures falls

`matrix/bands.py`, on by default through `weighted_figure_lines=True`.

The plain halfway rule printed a bass note held 397 ms as a negra where the score has a corchea. The
line now leans towards whichever of the two figures the passage actually plays more of:

```text
line between A and B  =  A * (B/A) ** ( pileA / (pileA + pileB) )
```

With even piles the exponent is ½ and this **is** the geometric mean, to the decimal, so a balanced
passage is drawn exactly as before. Piles are counted once inside the halfway bands — recounting
inside the new lines ratchets — per passage, both hands pooled, and clamped to 80/20 so a rare
figure keeps a fifth of the room on each side.

This is a refinement of D-11 rather than a departure from it, but it is a parameter because it is
the one place in the payload where a note's figure depends on notes other than itself.

### Tresillos

`notation/tuplets.py` (D-32). A ladder of halves has no name for three even notes filling one beat:
at a negra of 300 ms they land 100 ms apart, which is a bad corchea (150) and a bad semicorchea
(75). Forced onto the nearest figure they print as a ragged mix — the exact failure the wall-clock
model exists to remove, one level down.

The rule is deliberately narrow, because a wrong tresillo is worse than a missed one. Three notes in
a row in the same hand qualify only when their three gaps match each other within 12 % **and** that
gap is a third of a figure the ladder already knows, within 15 %. Requiring the gaps to match is
what says the player was dividing a beat into three rather than playing something else at a similar
speed. Groups do not overlap: six even notes are two tresillos, never four.

The three notes keep the ordinary figure one step below the one they divide — a tresillo of a negra
is three corcheas. The number 3 and its bracket are what make it a tresillo, so the glyphs stay
conventional, and `fitError` is zero for them. Dotted figures cannot be divided, because a dotted
figure already divides into three.

Tresillo ids are numbered across the whole piece, so the two hands cannot claim the same one.

### Trills

`notation/trills.py`, offered through `GET /time/{uuid}/trills` and never applied automatically. Two
notes a whole tone or less apart, the pair coming round at least three times, evenly and under
300 ms, measured on the raw attack times per hand.

Accepting one collapses the run to a held note with `tr` over it **on the backend, before any figure
is named** — not as an overlay, because the notes it replaces would otherwise still be named and
drawn. The alternations stay in `events.json` and playback still sounds every one of them (D-29), so
removing the mark prints them again.

---

## 8. Assembling the payload

`time_pipeline.to_score_payload`. It takes the two hands and one named ladder and returns a
`TimeScorePayload`.

Three things happen here that are worth knowing:

**Trailing silence is cut.** A recording often runs on for seconds after the playing stops, and
drawing that gives a page of empty staff. The recording is untouched; only the sheet stops where the
music does. When page edits are folded in (`POST /time/{uuid}/score`) the trim is done **first and
not repeated**, because trimming the edited hands could cut further — hiding the last note of a
piece would shorten it — and that renumbers every column, which every frame-keyed annotation depends
on not happening.

**Passages default to one.** A piece with no boundary drawn gets a single passage covering every
frame. Passages must tile with no gap and no overlap, and the payload's validator enforces it.

**Layout hints are frame counts, not durations.** The defaults — `frameGroup` 25, `frameMeasure` 100
— are one second and four seconds at 40 ms. A piece read at 20 ms should halve them to keep the
dashed lines in the same place on the clock.

---

## 9. The drawing

The payload is drawn by `@aimpromptu/grid-notation` in the browser, not by the backend. The backend
decides every figure; the renderer draws what it is told and applies the per-note overrides on top.

The seam and the package's own contract are in
[`../frontend/grid-notation.md`](../frontend/grid-notation.md).

Two layout rules from the same contract are worth naming here, because they explain something a
reader notices:

- **One `time → x` map for the whole system** (D-22), built from both hands' onsets merged. Every
  staff, ruler and overlay reads from that one map, so "which hand is limiting this region" is not a
  question anybody has to answer.
- **A beamed run is set tighter than the same notes unbeamed** (D-33). A beam carries the eye across
  a group, so full width makes a run read as loose separate notes. The cost, stated plainly: the
  width of a column now depends on the printed figure, so **renaming a passage moves the notes
  inside it**. Nothing outside it moves, which is the property that matters (D-21) — correcting the
  end of a piece must never make a reader re-read the beginning.

---

## 10. Where to look deeper

- [`time-matrix.md`](time-matrix.md) — every field of the payload
- [`endpoints.md`](endpoints.md) — the routes this path answers
- [`transcription-pipeline.md`](transcription-pipeline.md) — engines and their parameters
- [`hand-inference-second-pass.md`](hand-inference-second-pass.md) — the gated repair pass
- [`rhythm-and-annotations.md`](rhythm-and-annotations.md) — what is stored beside `events.json`
- [`decisions.md`](../../../context/implementations/03-time-based-concept/decisions.md) — D-01 … D-34
