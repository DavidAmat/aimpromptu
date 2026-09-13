> Context: [context/music/transcription-quality.md](../../../context/music/transcription-quality.md) ·
> [context/backend/time-model.md](../../../context/backend/time-model.md)

# The transcription pipeline: modules, order, parameters

Everything between an audio file and the two hand matrices. Exact module paths, the parameters
actually in force, and the measurement behind each of them.

Where this page is about *the parameters*, [`events-to-sheet.md`](events-to-sheet.md) is about *the
path* and carries the reasoning for the ordering. Read that one first if you want to know why the
steps are in this sequence.

---

## 1. Order of operations

```text
audio
  -> engine                      transcription/engine.py            list[NoteEvent] in seconds
  -> events.json                 transcription/pipeline.py          the transcription, kept forever
       |
  -> drop removed notes          time_pipeline                      the reader's deletions
  -> drop artifacts              transcription/artifacts.py         notes too short to be notes
  -> merge leaked re-onsets      transcription/leakage.py           phantom re-strikes
  -> group chords on raw times   transcription/grouping.py          fixed 40 ms window
  -> snap to columns             transcription/events_to_matrix.py  round(ms / frameMs)
  -> split hands                 matrix/hands.py + hands/           D-31
  -> pin the reader's hand fixes time_pipeline.pin_hands
       -> two hand matrices
```

**The pipeline used to have five steps and the middle three are gone.** They existed to move a
recording onto a grid whose spacing came from a tempo somebody typed in. There is no tempo (D-01),
so `collapse`, `clean` and `re-quantise` have nothing to do, and `matrix/granularity.py`,
`matrix/isochrony.py` and `matrix/tempo_map.py` were deleted with them.

Only the first arrow is expensive, and **only its result is stored**. Everything after it is a
function of `events.json` and a frame length, computed again on every request.

Two orderings are load-bearing and were each arrived at by fixing a real defect:

- **Artifacts before everything.** One phantom bass note an octave under a played octave makes the
  stack unholdable and forces the hand splitter into a wrong answer. Also before `leakage`, whose
  asymmetry test asks which other keys attacked alongside a suspect.
- **Hands before anything is measured** (D-31). Gaps are measured per hand, and the gap between a
  right-hand run and a held left-hand chord is not a rhythm — it would bury the peak the reader is
  meant to name.

---

## 2. Files on disk

`data/audio/<uuid>/matrices/` holds **one** file that matters:

| File | What it is |
|---|---|
| `events.json` | **The transcription**, in seconds. Never filtered in place. |

`raw.npz`, `raw-granularity.txt`, `raw-edited.flag`, `collapsed_<gran>.npz`, `clean_<gran>.npz`,
`two-hands_<gran>_*.npz` and `hands_<gran>.json` are all gone. A grid that is a pure function of a
file next to it is not worth storing, and a sidecar recording the tempo it was built at is not worth
keeping when no tempo takes part.

Full tree in [`paths-and-data.md`](paths-and-data.md).

---

## 3. Engines

Registered in `ENGINES` (`transcription/engine.py`). `GET /matrix/engines` reports which can
actually run, so the Input tab greys out what is not installed.

| Name | Install | Notes |
|---|---|---|
| `bytedance` | `uv sync --extra transcription` | **Default.** Checkpoint (165 MB) downloaded on first use to `~/piano_transcription_inference_data/` |
| `transkun` | `uv sync --extra transkun` | Weights ship inside the wheel. No thresholds — the semi-CRF decodes note intervals directly. About 1.4× realtime on CPU |
| `basic-pitch` | — | Cannot install on Python 3.12: basic-pitch 0.4.0 pins `tensorflow < 2.15.1` and cp312 wheels start at 2.16.1 |
| `silent` | — | Returns no notes. The whole UI and pipeline still run end to end without any model installed |

**`uv sync` installs only the extras you name**, so `--extra transkun` alone uninstalls ByteDance.
For both: `uv sync --extra transcription --extra transkun`.

### ByteDance onset threshold: 0.5, not the package default 0.3

`DEFAULT_ONSET_THRESHOLD = 0.5`, and this is the one engine parameter the project overrides.

The package's post-processor opens a note at any onset peak above the threshold **without checking
that the key is already inside a note it just opened**, which is where phantom re-onsets come from.
Swept over a whole recording of Chopin's Nocturne Op. 9 no. 1: 0.5 removes three of the four
phantoms and still finds all 38 notes of the printed bars; 0.6 takes the fourth but starts deleting
a real one.

The other thresholds are the package's own: offset 0.3, frame 0.1, 16 kHz, 10-second segments at
50 % overlap.

### Transkun must not be chunked

`TransKun.transcribe` threads a `startPos` between consecutive segments — the CRF continues its
decode across the boundary. External 20-second chunks with 4-second overlap shifted every onset by
about 10 ms per chunk. It runs whole; progress comes from wrapping `model.transcribeFrames`, which
the internal loop calls once per segment.

Comparison on one reference passage (254.3–271.5 s): 122 notes agree, Transkun finds two ByteDance
misses (`D#3` and `D3`, completing an octave) and loses four `A#2` attacks. **Differently wrong, not
better** — which is why it is offered beside ByteDance rather than as an upgrade.

---

## 4. Parameters in force

### Artifacts — `transcription/artifacts.py`

| Parameter | Value | Why |
|---|---|---|
| `min_duration_seconds` | **0.020** | Sits in the empty band between the 4–16 ms artifact cluster and the 32 ms shortest real note |
| `coincidence_seconds` | 0.050 | The artifact is created *by* a struck chord; a short note alone in silence is something else and is kept |
| `require_coincident_attack` | `True` | |

**Do not raise the floor.** ByteDance's offsets are long because they follow the pedal rather than
the key; Transkun reports true key release and returns 34–85 ms notes for a passage ByteDance calls
200–1700 ms. A 40 ms floor would silently delete a third of a Transkun transcription. There is a
test.

Nothing is deleted from `events.json`. The filter runs on the way out, so every rebuild gets it —
including recordings transcribed before it existed.

### Leakage — `transcription/leakage.py`

A key that is already sounding "re-onsets" on another key's attack. Six conjunctive conditions:

| Parameter | Value | Why |
|---|---|---|
| `max_gap_seconds` | 0.040 | Above this engine's 5–20 ms abutting gaps, far below the ~130 ms of the fastest repeated note anyone writes |
| `coincidence_seconds` | 0.040 | How close another key's attack must be to count as coincident |
| `max_overlap_seconds` | 0.010 | More overlap than this is not abutting; something else is going on |
| `lag_ahead_seconds` | **0.012** | How far *ahead* of the cluster the suspect may sit. Behind it, any distance |
| `min_company_margin` | **2** | How many *more* keys attack alongside the suspect than alongside the note it would merge into |
| `max_shared_company` | **0** | How many keys may attack alongside **both** |
| `min_velocity_drop` | 3 | The suspect must be quieter |

Three of these were changed after a real failure and the reasoning is worth keeping.

**The lag test is two-sided.** It used to be a one-sided `min_lag_seconds` of 3 ms, demanding the
suspect arrive *behind* the chord that caused it — because the phantom in the file it was fitted to
did (+6.7 ms). On the Chopin Nocturne, three phantoms arrive at −1.3, −8.2 and −11.5 ms, level with
the cluster or slightly ahead, and all three walked through. Which side of the attack a secondary
detection lands on is a property of the model's receptive field, not of the playing, so demanding
one sign was over-fitting to one file.

**The asymmetry test compares company instead of demanding none.** Demanding the predecessor have
*no* company at all is too literal: one phantom was let through because a single unrelated key
attacked 33 ms after its predecessor. A margin says what the rule always meant — the suspect is born
from a chord its predecessor was not part of. The margin is 2 rather than 1 because at 1 it fires on
a note whose predecessor merely had one fewer neighbour, which is noise.

**Counting company is not enough, and a fixture caught it.** When a whole D7 chord re-articulates,
each of its notes sees two more neighbours than its predecessor did and clears the margin. What
gives it away is *which* keys those are: the same ones both times, because it is the same chord
struck twice. A phantom cannot look like that — it is born from a chord its predecessor was not part
of, so the two sets are disjoint. Zero shared keys is the rule.

**The lag change and the threshold change ship together.** Paired with the old onset threshold of
0.3, the two-sided lag merged away a real `Fa4`, because a phantom sitting beside that note inflated
its company count. It is safe at 0.5, where that phantom never exists.

Tuned for precision throughout: a false merge silently deletes a played note.

### Chord grouping — `transcription/events_to_matrix.py`

`GROUP_WINDOW_MS = 40.0`, non-chaining: a group admits later onsets within the window of the
group's **first** onset, not of the previous one (D-04).

**The window is fixed and does not follow `frameMs`.** It used to, and that was wrong in a way worth
naming: it let the column length change the *music*. At 10 ms it conjured 22 semifusas that do not
exist at 40 ms, and it broke the promise that `frameMs` is only layout.

Grouping runs on raw times, before snapping, because two notes 39 ms apart can fall either side of a
column boundary — so "same frame = same chord" is phase-dependent and unreliable.

### Hands — `hands/`

A beam dynamic program over onset groups (`hands/beam.py`), with a cost model in `hands/costs.py`
and configuration in `hands/config.py`. `hands/threshold.py` keeps the old `Do-4` rule as a
baseline, reachable as `method="threshold"`.

`C_ledger` (`hands/staff.py`, weight `0.50`) charges the ledger lines an assignment forces onto the
page, with separate graces for running outward past your own staff (6 lines, free — that is
register) and across into the other hand's (2 lines). The gated second pass that repairs what a
group-by-group search structurally cannot see is documented in
[`hand-inference-second-pass.md`](hand-inference-second-pass.md).

**One known hole, still open.** `costs.py` charges the `octave` cost only when `len(events) == 2`,
so an `F1+F2+F3` stack pays nothing for splitting `F3` off. The artifact filter removes the usual
cause; the cost itself has not been generalised.

Runbook for a hand printed far outside its own staff:
[`../../issues/hand-split-ledger-lines.md`](../../issues/hand-split-ledger-lines.md).

---

## 5. Where the figure lines fall

`matrix/bands.py`, applied from `to_score_payload` with `weighted_figure_lines=True`.

The plain halfway rule printed a bass note held 397 ms as a negra where the score has a corchea. The
line between two figures now leans towards whichever of them the passage plays more of:

```text
line between A and B  =  A * (B/A) ** ( pileA / (pileA + pileB) )
```

With even piles the exponent is ½ and this **is** the geometric mean, to the decimal, so a balanced
passage is drawn exactly as before. Piles are counted once inside the halfway bands — recounting
inside the new lines ratchets: 447 ms, then 466, then the clamp — per passage, both hands pooled,
and clamped to 80/20 so a rare figure keeps a fifth of the room on each side.

---

## 6. Endpoints

| Route | Returns |
|---|---|
| `GET /matrix/engines` | Which engines can run here |
| `POST /matrix/transcribe` | `202` and a job id |
| `GET /matrix/progress/{jobId}` | SSE stream of real model-batch progress |
| `GET /matrix/jobs/{jobId}` | The same state, for pollers |
| `GET /matrix/{uuid}/events` | `events.json` plus `artifact` / `octaveBelow` per note and the counts. **Flags rather than omits** — a filter you cannot see is a filter you cannot check |
| `PUT /matrix/{uuid}/events/removed` | Take notes off the recording, by pitch and second |

`GET /matrix/{uuid}/runs` is gone: it belonged to the isochrony quantiser, which was deleted with
the tempo model.

Detail in [`endpoints.md`](endpoints.md#3-matrix--running-the-model).

---

## 7. Running the tests

From `aitu-backend/`:

```bash
make test
```

State on 2026-09-13: **769 passed, 1 failed** in about 15 seconds. The failure,
`test_time_score_payload.py::test_the_worked_example_at_00_46_prints_three_equal_corcheas`, is
pre-existing on a clean checkout and unrelated to any recent work — it was already recorded in the
Epic 13 report.

`pyproject.toml` sets `pythonpath = ["src", "."]`. The second entry is not decoration:
`tests/test_migration.py` imports `scripts.migrate_to_time_matrix` and `scripts/` has no
`__init__.py`, so without it collection fails before a single test runs and `make test` reports
nothing at all. That was the state until 2026-09-13.

---

## 8. Where to look deeper

- [`events-to-sheet.md`](events-to-sheet.md) — why the steps are in this order
- [`time-matrix.md`](time-matrix.md) — what the two hand matrices become
- [`hand-inference-second-pass.md`](hand-inference-second-pass.md) — the gated repair pass
- [`../../issues/piano-matrix-sustains-and-phantom-onsets.md`](../../issues/piano-matrix-sustains-and-phantom-onsets.md) — the runbook
