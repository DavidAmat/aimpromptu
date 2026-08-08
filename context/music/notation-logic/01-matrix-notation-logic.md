Here is how the documentation defines the matrix, what 0/1 means in practice, and how column timing is computed from BPM and the other required input.

## Matrix layout: rows, columns, and what “0 / 1” means

Conceptually the score is an **88 × N** matrix:

| Dimension | Meaning |
|-----------|---------|
| **Rows** (88) | Piano keys, bottom to top: `La-0` … `Do-8` |
| **Columns** (N) | Time frames — discrete steps along the timeline |

Each cell is either **active** (key sounding at that frame) or **inactive** (0 / silence / key not sounding).

The wire format is **sparse COO**, not a dense 0/1 grid. Active cells are listed in `rows`/`cols`, and **onset vs sustain** is encoded separately:

| Encoding | Meaning |
|----------|---------|
| Cell present + `onset[i] = rows[i]` | **Onset** — key struck at that column |
| Cell present + `onset[i] = -1` | **Sustain** — key still sounding, not struck again |
| No cell at `(row, col)` | **0** — not sounding (released or never played) |

So “released / not sounding” is **absence of a cell**, not a third value in the matrix. The early vision in `project-features.md` describes separate onset and sustain matrices; the implemented format merges them into one matrix plus the `onset` array.

---

## The two required timing inputs

Column duration is **not** derived from BPM alone. You always provide **two** values:

| Input | JSON field | Role |
|-------|------------|------|
| **Tempo** | `tempoBpm` | Beats per minute; **1 beat = one quarter note (“negra”)** |
| **Time step** | `timeStepSeconds` | **Seconds per column** (one time frame) |

Defaults in the compose UI: **60 BPM** and **0.5 s** per column.

`timeStepSeconds` is the direct answer to “how many seconds/ms between columns.” BPM is what converts that wall-clock duration into musical beats for notation.

---

## Formulas

### Wall-clock (seconds / milliseconds)

```
seconds_per_column   = timeStepSeconds
milliseconds_per_column = timeStepSeconds × 1000
```

### Musical duration of one column

```
beats_per_column = timeStepSeconds × (tempoBpm / 60)
```

Equivalent form used in rendering:

```
durationBeats = steps × timeStepSeconds / (60 / tempoBpm)
```

where `steps` = number of consecutive columns a note spans.

### Default example (from the docs)

With `tempoBpm = 60` and `timeStepSeconds = 0.5`:

| Quantity | Value |
|----------|-------|
| ms per column | **500 ms** |
| seconds per column | 0.5 s |
| beats per column | 0.5 × (60/60) = **0.5 beat** → **eighth note** |
| columns per quarter note | 2 columns |
| columns per whole note (4 beats) | 8 columns |

---

## Choosing resolution (linking BPM to column width)

`project-features.md` states that column width depends on **both** BPM and the chosen temporal resolution: you need enough columns to represent short values (fusas, semifusas) at the given tempo.

If you want each column to represent a fixed **musical** value (e.g. a sixteenth = 0.25 beats), solve for `timeStepSeconds`:

```
timeStepSeconds = beats_per_column × (60 / tempoBpm)
```

Examples:

| Target | BPM | `timeStepSeconds` | ms/column |
|--------|-----|-------------------|-----------|
| Eighth note (0.5 beat) | 60 | 0.5 | 500 ms |
| Eighth note (0.5 beat) | 120 | 0.25 | 250 ms |
| Sixteenth (0.25 beat) | 120 | 0.125 | 125 ms |
| Sixteenth (0.25 beat) | 60 | 0.25 | 250 ms |

Or, given `timeStepSeconds` and BPM, infer the musical grid:

```
beats_per_column = timeStepSeconds × (tempoBpm / 60)
```

The renderer’s finest grid is **sixteenth notes** (0.25 beats); anything off that grid is snapped with a warning.

---

## How this ties to note length in the matrix

A note’s duration is how many **consecutive columns** it occupies:

- **Onset** at column `c`
- **Sustain** cells on `c+1`, `c+2`, … while the key stays down
- **Release** = next column with no cell for that row (or an onset rule cuts the sustain earlier)

Example from the notation spec — `*Re-4` then `Re-4` across 2 frames → one note spanning **2 steps**:

```
durationBeats = 2 × 0.5 / (60/60) = 1.0 beat  →  quarter note
durationMs    = 2 × 500 = 1000 ms
```

---

## Summary

| Question | Answer |
|----------|--------|
| How many ms between columns? | `timeStepSeconds × 1000` |
| What must the user provide? | `tempoBpm` + `timeStepSeconds` (plus the sequence itself; optionally lyrics, key signature, left hand) |
| Is column width computed from BPM alone? | **No** — `timeStepSeconds` is an independent parameter you choose (or derive from a target note value via the formula above) |
| How do 0/1/onset/sustain work? | Active = 1; absent = 0/released; among actives, `onset` distinguishes struck vs sustained |

If you want, I can also walk through a concrete passage (e.g. your default sequence) column by column with ms and beat values at 60 BPM / 0.5 s.


----

# APPENDIX A: Terminology clarification

Good catch — this is a **unit confusion**, not a bug in the math. The docs assume **1 beat = 1 negra (quarter note)**. Your “1/8 of a beat” description actually matches **fusa**, not **semicorchea**.

## What “1 beat” means in this project

When we write `tempoBpm = 60`, we mean:

> **60 negras per minute**

So the reference unit is:

| Spanish | English | Beats |
|---------|---------|-------|
| **Negra** | Quarter note | **1 beat** |

Everything else is a fraction of that.

---

## Spanish names vs beats

| Spanish | English | As a fraction of **1 beat** (negra) | In decimal beats |
|---------|---------|--------------------------------------|------------------|
| Negra | Quarter | 1/1 | **1.0** |
| Corchea | Eighth | 1/2 | **0.5** |
| **Semicorchea** | **Sixteenth** | **1/4** | **0.25** |
| Fusa | Thirty-second | **1/8** | **0.125** |
| Semifusa | Sixty-fourth | 1/16 | 0.0625 |

So when the docs say “sixteenth note = 0.25 beats”, that is **semicorchea = ¼ of a negra**.

What you described — **1/8 of a beat** — is **fusa**, not semicorchea.

---

## Why it feels contradictory

People often count from the **redonda** (whole note) instead of the **negra**:

| Spanish | Fraction of a **redonda** |
|---------|---------------------------|
| Redonda | 1 |
| Blanca | 1/2 |
| Negra | 1/4 |
| Corchea | **1/8** |
| Semicorchea | **1/16** |
| Fusa | 1/32 |

So:

- Semicorchea = **1/16 of a redonda**
- Corchea = **1/8 of a redonda**
- Fusa = **1/32 of a redonda**

But in **beats** (negra = 1):

- Corchea = 1/2 beat
- Semicorchea = 1/4 beat
- Fusa = 1/8 beat

You likely mixed **“1/16 of a redonda”** (semicorchea) with **“1/8 of a beat”** (fusa). Different reference note, different fraction.

---

## Quick sanity check at 60 BPM

At 60 BPM, one negra = 1 second.

| Note | Beats | Duration |
|------|-------|----------|
| Negra | 1.0 | 1 s |
| Corchea | 0.5 | 0.5 s |
| Semicorchea | 0.25 | 0.25 s |
| Fusa | 0.125 | 0.125 s |

The default `timeStepSeconds = 0.5` at 60 BPM → **0.5 beat per column** → one column = **corchea**, not semicorchea.

---

## Tie-in to the code/docs

The renderer’s finest grid is `MIN_BEATS = 0.25`, i.e. **semicorchea** (¼ beat), not fusa (⅛ beat).

So the documentation is consistent **if** you accept: **beat = negra**. The confusing part is only the Spanish naming when you count from redonda or call semicorchea “1/8”.

If you want, I can add a small “beat = negra” terminology table to `context/notation-logic/01-matrix-notation-logic.md` so this is explicit in the docs.

# APPENDIX B: Sustained notes until some other note starts an onset

In order to simplify things, since our main goal is to produce neat piano sheets, we will adopt
the following rules to avoid long-sounding notes occupying a lot of space in the piano sheet.

The author that will play the song in piano will need to know this sustained period of the note whenever new notes start to sound after it, meanwhile that note is still sounding.

Let's exemplify this:
```text
C3 -> onset at 00:00 (duration 3 seconds)
C4 -> onset at 00:01 (duration 2 seconds)
```

The problem with this is that in the piano sheet if we let the C3 sound for 3 seconds and C4 sound in the middle of this sustained C3, it will be a chaos. To simplify this, we will only let a given note to keep sounding if it is played simultaneously on a chord and all the notes on that chord are sustained equally and no other note is played while these are sustained. In the moment in which a note is sustained but a given new note is pressed, then we will assume that this note is no longer sustained any more. This means that for this example we will do a cleaning step to simplify the durations:

```text
C3 -> onset at 00:00 (duration 1 seconds) -> this is because at 00:01 another onset starts while C3 was sustained
C4 -> onset at 00:01 (duration 2 seconds)
```

This is very typical in classical music, patters like:
```text
C3, C4 -> chord onset at 00:00 (duration 10 seconds)
D3 -> onset at 00:01 (duration 1 second)
E3 -> onset at 00:02 (duration 1 second)
```

So both C3 and C4 will be cleaned to have a duration of 1 second instead, even though they keep sounding as a sustained note for 10 seconds. 

NOTE: this only applies for sustained notes, whenever there is a new onset of that note this does not apply:

```text
C3, C4 -> chord onset at 00:00 (duration 10 seconds)
C3 -> onset at 00:01 (10 seconds) 
```

In this case we will treat C3,C4 chord as a 1 second duration chord and C3 as a new onset of 10 seconds duration (as long as no other new note is played).

## Amendment (2026-08-01): the rule is per hand, and runs after the split

"Another note" above means **another note of the same hand**. The rule exists because
one hand's fingers run out, so a key the *other* hand is playing is not an answer to
the question it asks.

For a while the pipeline applied it to the whole keyboard before splitting the hands,
which is the same rule with the wrong scope. In `When I Was Your Man` the left hand
holds a C2/C3 octave under a right-hand Do-Mi / Sol / Do-Mi / Sol figure; the right
hand's Sol, an eighth later, cut the octave from twelve columns to two, so the printed
left hand was staccato where the recording holds. The order is now:

```text
raw -> collapse -> split hands -> clean each hand, independently
```

The split still *decides* from a whole-keyboard clean — the beam's ergonomic cost model
reads a hand as pinned for as long as its keys sound, and it was tuned against those
shorter sustains — and then applies that decision to the uncleaned matrix. Cleaning
never adds, moves or removes an onset, so the decision transfers exactly.

Nothing about the rule itself changed. Within one hand, every example above still holds
verbatim, including the C3/C4 chord being cut to one second by the D3 that follows it —
provided the same hand plays them.

## Score-rendering rule: rests and chord duration

The rendered score is onset-led. These rules affect notation only; they do not rewrite the matrix:

1. A rest is allowed before the first onset of a measure. This supports delayed entrances and
   keeps the two hands aligned.
2. After a note or chord has entered, no visible rest may appear before the next onset in the same
   measure. The preceding event is treated as sustained up to that next onset.
3. Notes struck together are one chord and share one duration. If the matrix releases some chord
   members earlier than others, the score keeps the entire chord sounding until the next onset.
4. The last note/chord is first expanded toward the closing barline using one legal figure. For
   example, seven corcheas in a 4/4 measure make the final note a negra, filling the missing
   corchea without a rest.
5. If the final onset-to-barline span cannot be expressed by one legal figure, use the largest
   legal figure and a visible trailing rest only for the small remainder.
6. If an *interior* onset-to-onset span has a mathematically unwritable remainder, preserve its
   timing with an invisible spacer. Never draw a middle rest or repeat/tie the same note inside the
   measure.
7. Ties are never emitted. If an onset-to-onset span crosses a barline, the first event fills to
   that barline and any time before the next onset is a leading rest in the following measure.

This deliberately favours a light, playable page over reproducing every recorded key release.


# APPENDIX C: Approximating note duration to matricial columns

We need to take into account that whenever we are processing raw audio, it is very likely that timings of the durations of the onset of the notes are not perfect and not mathematical rounded. This means that, for example, if we are trying to convert a given "negra" in a BPM of 60 seconds and its duration was 1.01 seconds, it does not make any sense if we try to fill those 0.01 seconds into a new figure, we need to round it to the closest figures available on that temporal granularity.

For example if we have a BPM = 60 and a temporal granularity of semicorcheas (4 semicorcheas = 1 negra, 1 semicorchea lasts 0.25 seconds) if we have a note that is sustained for a duration of 1.23 seconds, we should always try to do the following to approximate it:

```text
C3 -> onset at 00:00 (duration 1.23 seconds)

Let's guess which figure it best suits:
blanca ? -> no, because it takes 2 seconds so it's very far from 1.23
negra ? -> no because it takes 1 second and we will have 0.23 seconds remaining
negra + corchea -> no because it takes 1.5 seconds (1 second + 0.5 seconds) but is still not ideal for 1.23 seconds

Since temporal granularity is semicorcheas, we aim to sum the time of a semicorchea:
negra + semicorchea -> 1 second + 0.25 seconds = 1.25 seconds which is 0.02s closer to 1.23 seconds (the actual duration)
```

When we say negra + corchea or negra + semicorchea we mean to apply a ligature to keep it sounding, not as an onset. In the temporal matrix this will be handled very easy in the column of C3 if the bpm = 60 and the temporal resolution is 0.25 (semicorchea)

C3 -> 1 -1 -1 -1 -1 0 0 0 0 0
(see that we have a first 1 indicating onset and then four -1's indicating sustained, each column is a sustain of 0.25 seconds)

### Greedy approach
So when we are constructing the potential candidates to approximate the 1.23 seconds of duration, we first need to see if a single figure can make up all the duration or be at least close to it. If the difference in seconds is smaller than the temporal resolution (semicorchea 0.25 seconds of resolution) (for example a 1.1 second in a temporal resolution of semicorchea, it will be counted as a 1 second) then we accept it. This is why we need to first attempt to have a single figure to make up most of the resolution. Whenever we can add another figure, we will follow the note hierarchy (first attempt a "redonda", then attempt a "blanca", then a "negra", then a "corchea", etc...). And always keep attempting to add a new sustained note until we reach an "error" in seconds that is smaller than the temporal resolution, meaning that if we were to add the minimum figure for that temporal resolution, we will distort more the melody than our current approximation with the minimum number of figures as possible.

You know that in music we can ligate a "negra" with a "corchea" if we want to produce a 1.5 seconds (this normally gets as a negra with a "dot" notation). Or for example I have seen cases in which we have a "blanca" with a dot, indicating that it is 3 seconds sustained in this case. So all of this is possible. What is not a valid ligature is to have a negra ligated with a semicorchea for example, never do this, respect the hierarchy and if there is not any valid ligature of the next figure in the hierarchy let's keep the main figure. Never do ligatures of more than 2 notes, maximum is 2 notes for a ligature, otherwise simply accept that in our matricial format we will lose some temporal information from the audio we are processing, it is ok. 

# APPENDIX D: Two hands

Knowing which note is played by each hand requires a problem of optimization by itself. Hence we will adopt a dummy split criteria, we will put whatever key that is C4 or above (D4, E4, ..., C5, ..., C6, ...) into the Right Hand matrix and the notes below the C4 (not included) to left hand. We will refine this logic in the future.

By default: right hand goes with *treble clef* and left goes with *bass clef* when we render the matrix into music notation.

# GENERAL NOTE

Always keep in mind that all the files that we are processing are played by a human. It's not played by a machine, and this means that the duration of the notes is not perfect, so they have to be approximated. Basically, all the pianists that play that piece interpret the timings, but they don't do it perfectly. It can happen that there is a mismatch in the duration of a note in seconds from what is actually indicated in the piano sheet. This is why, whenever we produce or provide the beats per minute, this is going to be very sensitive, because the audio file will be analyzed with these beats per minute. It can happen that there are some passages of the music file that are played faster, so we have to take into account that this won't be 100% perfect.
