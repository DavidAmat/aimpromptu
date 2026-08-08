> Context: [01-matrix-notation-logic.md](../../context/music/notation-logic/01-matrix-notation-logic.md) (Appendix B, and its 2026-08-01 amendment)

# Held chords that print short, and chords with a note too many

Two separate defects, found together on 2026-08-01 in
`When I Was Your Man - Bruno Mars — segment 00:04.00–03:53.14` around **12.3 s**
(semicorchea columns 54–71). The passage is a right-hand Do-Mi / Sol / Do-Mi / Sol
figure in eighths over a held left-hand Do-2/Do-3 octave. It printed with the octave
staccato *and* with a Do-Mi-Sol chord where the music has Do-Mi then Sol.

They look like one bug in the piano roll. They are not, and they were fixed in
different places.

---

## 1. A hand's sustain cut by the other hand's onset

**Symptom.** A left-hand chord that the recording holds prints as one or two frames.
The piano roll shows the collapsed matrix carrying a long sustain and the clean matrix
dropping it almost immediately.

**Cause.** Appendix B — *a sustain dies when any other key is struck* — was applied to
the whole keyboard, **before** the hands were split. "Any other key" then included keys
the other hand was playing:

```text
collapsed   Do-3   ..O-----------....     held, columns 56-67
clean       Do-3   ..O-..............     cut at 58 by a RIGHT-hand Sol-3
```

The rule is about one hand running out of fingers, so its scope is one hand. Cleaning
before the split let the melody amputate the accompaniment.

**Fix.** `transcription/pipeline.py::derive` now runs

```text
raw -> collapse -> split hands -> clean each hand, independently
```

with one wrinkle worth keeping straight. The beam hand-inference is *still* fed a
whole-keyboard clean, because its relocation model is `release_aware` — it reads a hand
as pinned for as long as its keys sound — and its 0.955 benchmark was measured on
cleaned input. So the split **infers from the cleaned view and paints the collapsed
one**, via `matrix.hands.split_hands(collapsed, infer_from=clean_view)`. That is sound
because cleaning only ever turns sustain cells into silence: it never adds, moves or
removes an onset, so onset ids (`c{column}:r{row}`) are identical in both matrices and
the assignment transfers exactly. `_repaint` raises rather than guessing if they ever
diverge.

`PipelineResult.clean` is now `combine(right, left)` — the union of the two per-hand
cleans — so the single-matrix view and the printed grand staff cannot contradict
each other.

**Blast radius.** Saved library versions store the matrix already cleaned, so they keep
the old, over-cut sustains until they are recomputed from `raw.npz` / `events.json`.
`api/library.py` and `notation/artifacts.py` split an already-clean matrix; per-hand
cleaning there is a no-op, because whole-keyboard cleaning is strictly more aggressive.

---

## 2. A phantom onset for a key that was already sounding

**Symptom.** A note the score plays *after* a chord appears *in* the chord, one column
early, while also still appearing in its correct place. Nothing in the matrix pipeline
put it there — it is in `events.json`, straight from the model.

**Cause.** Onset detection fires on broadband transients, and a piano chord is one. When
a chord lands on a pitch that is still ringing, the onset head can fire for the ringing
pitch too; the post-processor closes that note and opens a new one at the chord's
instant. The engine reported:

```text
Sol-3  11.8964 -> 12.3000  v73     one G3 ...
Sol-3  12.3140 -> 12.7100  v66     ... split in two, 14 ms later
Do-4   12.3067 -> 13.1200  v87   } the chord whose attack did it
Mi-4   12.3073 -> 13.1200  v82   }
```

**14 ms is not a re-articulation.** The damper has to fall and the hammer has to be
re-cocked; nobody re-strikes a key that fast. Quantised, the second event landed in the
chord's own column and the score printed a three-note chord.

**Fix.** `transcription/leakage.py`, applied inside `events_to_raw_matrix` so every
rebuild from a stored `events.json` gets it without re-running the model. Four
conditions, all required:

| # | Condition | What it rules out |
|---|-----------|-------------------|
| 1 | offset-to-re-onset gap ≤ 40 ms | notes with a real release between them |
| 2 | the suspect onset has company its predecessor did not | genuine chord re-strikes, where every voice repeats together |
| 3 | it trails *all* of that company by ≥ 3 ms | a chord member whose onset regression is a hair late |
| 4 | it is ≥ 3 velocity quieter than the note it merges into | a deliberate re-attack |

Each was added because the rule without it fired on a real note. Notably **gap alone is
worthless here**: this engine's offsets are weak, so 716 of the file's 1079 consecutive
same-pitch pairs abut within 20 ms, most of them genuine repeats. And condition 2 alone
is not enough either — it flags the D7 chord re-strike at 9.838 s, where Re-3 anticipates
the first chord by 135 ms and then re-strikes *with* the second. Conditions 3 and 4
rescue it (Re-3 sits inside the cluster's spread and holds v97 → v96).

On the reference file this keeps **8 of 1117 events (0.7%)**. That is deliberately
high-precision and low-recall: a surviving phantom is a visible wrong note that the
merge-onsets UI can fix, while a false merge silently deletes a note the player played.

---

## Verifying either fix on a real file

Recompute and read the two hands directly — no UI needed:

```python
from aitu_backend.transcription import pipeline
from aitu_backend.schemas.matrix import Granularity

result = pipeline.recompute(audio_uuid, tempo_bpm, Granularity.SEMICORCHEA)
print(result.hands.left.grid[note_to_row("Do-3"), 54:72])   # should hold, not stop at 58
print(result.hands.right.grid[note_to_row("Sol-3"), 54:72])  # onsets at 58, 62, 66, 70
```

Expected for this passage after both fixes:

```text
RIGHT  Sol-3   ....O-..O-..O-..O-      alternating with the chord, never inside it
       Do-4    --O-..O-..O-......
       Mi-4    --O-..O-..O-......
LEFT   Do-3    ..O-----------....      held until the left hand's next onset at 68
```

Regression tests: `tests/test_transcription_leakage.py` (the whole passage, verbatim,
plus the two real re-strikes that must survive) and
`tests/test_matrix_pipeline.py::test_a_held_bass_survives_a_melody_in_the_other_hand`
with its companion `..._is_still_cut_by_its_own_hand`.

## What is still not fixed

`Do-2` in this passage lasts two columns while `Do-3` above it lasts twelve. That is not
cleaning — the model gave `Do-2` a 0.364 s duration against `Do-3`'s 2.499 s, so the
octave is uneven at the source. Offset estimation is a separate problem from onset
leakage and is untouched here.
