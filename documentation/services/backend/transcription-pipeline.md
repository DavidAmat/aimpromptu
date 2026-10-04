> Context: [context/music/transcription-quality.md](../../../context/music/transcription-quality.md) ·
> [context/backend/time-model.md](../../../context/backend/time-model.md) ·
> [context/backend/piano-matrix-notation.md](../../../context/backend/piano-matrix-notation.md)

# The transcription pipeline: modules, order, parameters

Everything between an audio file and the two hand matrices. Exact module paths, the parameters
actually in force, and the measurement behind each of them.

Where this page is about *the parameters*, [`events-to-sheet.md`](events-to-sheet.md) is about *the
path* and carries the reasoning for the ordering. Read that one first if you want to know why the
steps are in this sequence.

Since implementation 08 the engine is **MuScriptor**, and it is the only engine a reader can choose.
ByteDance and Transkun stay in the code with their tests, and the pieces they transcribed keep the
filters that were tuned for them, but no route starts them any more.

---

## 1. Order of operations

```text
audio (normalized.wav, 16 kHz mono)
  -> the selected region         audio/frames.py                    kept frames joined in memory, 5 ms fades
  -> engine                      transcription/engine.py            MuScriptor; live `chunk` frames on the stream
  -> lag correction              transcription/lag.py               MuScriptor only; subtracted from every time
  -> events.json                 transcription/pipeline.py          the transcription, kept forever
       |
  -> drop removed notes          time_pipeline                      the reader's deletions
  -> drop artifacts              transcription/artifacts.py         not on muscriptor-* pieces
  -> merge leaked re-onsets      transcription/leakage.py           not on muscriptor-* pieces
  -> group chords on raw times   transcription/grouping.py          fixed 40 ms window
  -> snap to columns             transcription/events_to_matrix.py  round(ms / frameMs)
  -> split hands                 matrix/hands.py + hands/           D-31, or paint the saved hands
  -> pin the reader's hand fixes time_pipeline.pin_hands
       -> two hand matrices      kept in transcription/split_cache.py
```

**The pipeline used to have five steps and the middle three are gone.** They existed to move a
recording onto a grid whose spacing came from a tempo somebody typed in. There is no tempo (D-01),
so `collapse`, `clean` and `re-quantise` have nothing to do, and `matrix/granularity.py`,
`matrix/isochrony.py` and `matrix/tempo_map.py` were deleted with them.

Only the first part is expensive, and **only its result is stored**. Everything after `events.json`
is a function of that file and a frame length. It is computed again whenever `events.json` changes,
and otherwise served from the shared split cache (§4.4).

Two orderings are essential and were each found by fixing a real defect:

- **Artifacts before everything.** One phantom bass note an octave under a played octave makes the
  stack impossible to hold with one hand and forces the hand splitter into a wrong answer. Also
  before `leakage`, whose asymmetry test asks which other keys attacked alongside a suspect.
- **Hands before anything is measured** (D-31). Gaps are measured per hand, and the gap between a
  right-hand run and a held left-hand chord is not a rhythm: it would hide the peak the reader is
  meant to name.

**When every placed note has a saved hand** (implementation 08, Phase 5), the last two steps are
replaced: `saved_hands.split_with_saved_hands` builds the whole keyboard with the same grouping,
snapping and filters, then paints each run of cells with the hand saved on its note. No inference
runs. On the 34 pieces of the library this paints exactly the cells the inference drew, at 40 ms and
at 20 ms, in 17 ms median instead of 670 ms.

---

## 2. Files on disk

`data/audio/<uuid>/matrices/` holds **one** file that matters:

| File | What it is |
|---|---|
| `events.json` | **The transcription**, in seconds of the piece. Never filtered in place. Schema `1.1` since implementation 08: note ids and a header of revisions (`engine`, `lagCorrectionMs`, `audioRevision` and the others). |

A new transcription of a piece that already has notes first copies `events.json` and `rhythm.json`
to `history/vN/` (`editing/history.py`, `snapshot_notes`), then writes the new notes and deletes
`rhythm.json`, because the reading's column numbers point at notes that no longer exist.

`raw.npz`, `raw-granularity.txt`, `raw-edited.flag`, `collapsed_<gran>.npz`, `clean_<gran>.npz`,
`two-hands_<gran>_*.npz` and `hands_<gran>.json` are all gone. A grid that is a pure function of a
file next to it is not worth storing, and a sidecar recording the tempo it was built at is not worth
keeping when no tempo takes part.

Full tree in [`paths-and-data.md`](paths-and-data.md). Every field of `events.json` in
[`context/backend/piano-matrix-notation.md`](../../../context/backend/piano-matrix-notation.md).

---

<a id="engines"></a>

## 3. Engines

Registered in `ENGINES` (`transcription/engine.py`). `DEFAULT_ENGINE = "muscriptor"` and
`SELECTABLE_ENGINES = ("muscriptor",)`: `GET /matrix/engines` lists only MuScriptor, and
`POST /matrix/transcribe` refuses every other name with `422`.

| Name | Install | State | Notes |
|---|---|---|---|
| `muscriptor` | `uv sync --extra muscriptor` | **Default, the only one selectable** | Weights (5.5 GB for `large`) from Hugging Face, gated: the account of `HF_TOKEN` must have accepted the licence |
| `bytedance` | `uv sync --extra transcription` | Kept, not selectable | Checkpoint (165 MB) downloaded on first use to `~/piano_transcription_inference_data/` |
| `transkun` | `uv sync --extra transkun` | Kept, not selectable | Weights ship inside the wheel. No thresholds: the semi-CRF decodes note intervals directly. About 1.4× realtime on CPU |
| `basic-pitch` | none | Not installable | Cannot install on Python 3.12: basic-pitch 0.4.0 pins `tensorflow < 2.15.1` and cp312 wheels start at 2.16.1 |
| `silent` | none | Kept, not selectable | Returns no notes. Before implementation 08 it let the whole UI and pipeline run without any model installed; now only the tests use it |

**`uv sync` installs only the extras you name**, so `--extra transkun` alone uninstalls the others.
For all three: `uv sync --extra muscriptor --extra transcription --extra transkun`. The container
image installs them all.

### 3.1 MuScriptor: the settings in force

MuScriptor (Kyutai and Mirelo, 2026) is a decoder-only transformer. It reads 5-second chunks of
16 kHz mono audio and writes note tokens: a note start, a note end, and a progress event at the end
of each chunk. `MuScriptorEngine` (`transcription/engine.py`, Phase 4) runs it with the settings
Phase 1 measured and the user chose:

| Setting | Value | Why |
|---|---|---|
| Size | `large` (`AITU_MUSCRIPTOR_MODEL`) | `medium` and `small` are faster but give a different transcription (agreement 0.84 to 0.86 with `large`), not a faster copy |
| Weight type | `float16` (`AITU_MUSCRIPTOR_DTYPE`) | The same notes as `float32`, 2.2 times faster, 3.5 GB of GPU memory instead of 7.1 |
| Batch | 1 chunk at a time | Required by prelude forcing |
| Prelude forcing | on | Without it the model guesses which notes continue from the previous chunk: 7% of the notes change and 40 notes end on a chunk border in 2 minutes |
| Instruments | `acoustic_piano` only (Q-3) | Without conditioning, Superestrella gains 70 `electric_bass` notes and 70 `drums` hits |
| Velocity | 64 for every note | MuScriptor has no loudness |

The name stored in the header of `events.json` is `muscriptor-<size>`, for example
`muscriptor-large`. MuScriptor prints a timing line for every chunk; those `print` calls are
silenced inside MuScriptor's own modules only (`models._silence`), not by redirecting the output of
the whole server.

### 3.2 The model registry and the preload

Before implementation 08 every job built its engine again: the torch import, then the weights read
from disk and moved to the device. `transcription/models.py` keeps one MuScriptor model per
`(size, device, dtype)` and one shared engine per `(name, device)` for the others, for the life of
the process. Loading `large` from the SSD takes about 1 s, plus the torch import.

`AITU_PRELOAD_ENGINE=muscriptor-large` loads the model on a background thread when the server
starts, and also compiles librosa for the lag measurement (7.7 s the first time, then 0.3 s).
`compose.yaml` sets it; natively it is empty and the first transcription loads the model. `none`
disables it. `GET /matrix/engine` reports what is loaded and, in plain words, why a preload failed.
uvicorn runs with `--reload` in development, so an edit under `src/` restarts the process and the
model loads again.

`AITU_DEVICE` chooses the device: `cpu` by default natively, `cuda` in the container. `cuda` is
returned as asked even when no GPU is visible, so a job told to use the GPU fails loudly instead of
running ten times slower on the CPU.

### 3.3 The GPU queue

The engines are shared, so only one job may use them at a time. `transcription/jobs.py` runs every
job submitted with `gpu=True` on one worker thread, in order of arrival. A queued job has the status
`waiting` and sends a `waiting` stage ("Waiting for N other transcriptions to finish"). Two routes
use the queue: `POST /matrix/transcribe` (only when the model has to run) and the range-edit take
(`POST /audio/{uuid}/edits/{session}/transcribe`). A second request for a piece that is already
waiting or running returns the same job.

### 3.4 The selected region

A cut is a range of 10 ms time frames of the original audio, saved in `metadata.json`
(`PUT /audio/{uuid}/cuts`). The engine hears **the piece**: `pipeline._transcribe_piece` reads
`normalized.wav`, and `frames.join_kept` joins the kept frames in memory. At each join a 5 ms linear
fade out and a 5 ms fade in, inside the kept samples, avoid a click that could be read as a note,
without changing the number of frames. MuScriptor receives the samples directly
(`MuScriptorEngine.run_signal`), so no audio file is written. An engine that reads a file receives a
temporary WAV of the piece, only when there is a cut.

The notes are stored in the time of the piece, which is shorter than the original by the cuts. The
header records the `audioRevision` they were made from; a later cut makes them stale, and the next
transcription request transcribes again instead of reusing them. With a 5 s cut at 60 s of
Superestrella, every note before the join and from 5.5 s after it was identical to the whole piece,
and no note appeared at the join.

A range transcription (`startSeconds`, `endSeconds`) is the older path: it slices the WAV and
ignores the cuts.

### 3.5 The lag correction

MuScriptor's onsets can all carry the same small lag. It is constant within a piece but changes
between pieces: in Phase 1 it went from 17 ms late to 22 ms early against ByteDance on six pieces.
MuScriptor's own fix needs a beat grid, which the project does not store (D-01) and which refused
all six pieces anyway. `transcription/lag.py` therefore measures the lag on the audio itself:

1. A spectral-flux onset envelope of the audio at a 2 ms hop (`librosa.onset.onset_strength`,
   `hop_length=32`, `n_fft=512`, `lag=5`).
2. For each candidate lag from -80 to +80 ms, the onsets are shifted by it and the envelope is
   read at the moved onsets. The lag with the highest mean is `best`.
3. The envelope peaks a little after the physical onset. Measured with ByteDance's onsets, that bias
   is 16 to 19 ms on every piece, so 17 ms (`ENVELOPE_BIAS_MS`) is added back.

`lagCorrectionMs = round(best + 17)`, clipped to ±40 ms, is **subtracted** from every onset and
release before saving, never below 0. On Superestrella it is +15 ms, so the notes move 15 ms
earlier. The step costs about 0.4 s for a 3-minute piece.

**The 200-onset minimum.** On 20 s excerpts of Superestrella (about 70 distinct onsets) the rule
gave anything from -7 to +17 ms; on 60 s excerpts (about 220) it gave 13 to 15 ms. A wrong correction
of 20 ms is worse than none, because the lag itself is at most about 20 ms. Below `MIN_ONSETS = 200`
distinct onsets no correction is applied, and a short piece is saved as MuScriptor wrote it.

The live `chunk` frames carry the times before the correction, because it is known only at the end.
The page reads the saved notes after `done`.

### 3.6 No filter on MuScriptor pieces

`artifacts.py` and `leakage.py` (§4) were tuned for ByteDance. Phase 1 measured them on six pieces
of MuScriptor notes. The artifact filter drops 0 to 4 notes per song. The leakage filter would merge
real repeated notes, because MuScriptor has no velocity and closes a note at the next onset of its
key (a gap of 0 ms).

Both filters run inside the hand split, on every read, so the decision is made from the `engine` in
the header of `events.json` (`pipeline.filters_for`):

| `engine` in the header | Artifacts | Leakage |
|---|---|---|
| `muscriptor-*` | off | off |
| `bytedance`, `transkun`, or `null` (a file written before schema 1.1) | on | on |

`GET /matrix/{uuid}/events` follows the same rule: it labels no artifact on a MuScriptor piece. One
exception remains: `editing/preview.py` still applies the default filters to a range-edit take,
which MuScriptor now transcribes. Phase 1 measured the effect as 0 to 4 notes per song, so it was
left as it is.

### 3.7 The live stream

While MuScriptor decodes, `transcription/live.py` (`LiveNotes`) reads the same events as the
assembler (`pmn/muscriptor.py`, `MuScriptorAssembler`) and sends `event: chunk` frames on the
progress stream: one when a chunk ends, one at most every 0.25 s inside a chunk when a note started
or ended, and a last one for the notes MuScriptor closes after its last chunk. The ids are given in
the order the notes start, from the piece's `nextId`, so the ids of the live frames are the ids of
the saved notes. Frame format, `id:` and `Last-Event-ID`:
[`endpoints.md`](endpoints.md#34-get-matrixprogressjobid).

The hand split is not computed before `done`. After saving, the route prepares the split cache on a
thread (`pipeline.warm_split`), so `done` is not delayed by 0.3 to 4.3 s.

### 3.8 Measured speed

Measured in the backend container on the RTX 4090, on Superestrella (`a585f9eb`, 189 s). "× real" is
seconds of audio per second of processing.

| Engine | Device | Load | Transcribe | × real | Notes |
|---|---|---:|---:|---:|---:|
| MuScriptor `large`, float16, batch 1, prelude forcing | cuda | 1.0 s | 25.3 s | 7.5 | 1,351 |
| ByteDance | cuda | 1.2 s | 4.6 s | 41.4 | 1,340 |
| ByteDance | cpu | 7.2 s | 53.6 s | 3.5 | 1,343 |

Through the HTTP routes (Phase 4): the first rectangle arrives 0.25 s after the request, 122 `chunk`
frames follow with a median gap of 0.25 s, and `done` arrives after 25.6 s, of which the lag step is
0.4 s. MuScriptor is about 5 times slower than ByteDance on the GPU, but a reader sees the notes
appear from the first second. The user listened to its transcription of Superestrella in Phase 1
and judged it good. The user also chose one chunk at a time over batching (Q-7), which keeps prelude
forcing and is the reason it is not faster: batching reaches 21.6 × real at 4 chunks, but changes 7%
of the notes.

### 3.9 ByteDance (kept, not selectable): onset threshold 0.5, not the package default 0.3

`DEFAULT_ONSET_THRESHOLD = 0.5`, and this is the one ByteDance parameter the project overrides.

The package's post-processor opens a note at any onset peak above the threshold **without checking
that the key is already inside a note it just opened**, which is where phantom re-onsets come from.
Swept over a whole recording of Chopin's Nocturne Op. 9 no. 1: 0.5 removes three of the four
phantoms and still finds all 38 notes of the printed bars; 0.6 removes the fourth but starts deleting
a real one.

The other thresholds are the package's own: offset 0.3, frame 0.1, 16 kHz, 10-second segments at
50 % overlap.

### 3.10 Transkun (kept, not selectable) must not be chunked

`TransKun.transcribe` passes a `startPos` between consecutive segments: the CRF continues its decode
across the boundary. External 20-second chunks with 4-second overlap shifted every onset by about
10 ms per chunk. It runs whole; progress comes from wrapping `model.transcribeFrames`, which the
internal loop calls once per segment.

Comparison on one reference passage (254.3–271.5 s): 122 notes agree, Transkun finds two ByteDance
misses (`D#3` and `D3`, completing an octave) and loses four `A#2` attacks. **Differently wrong, not
better.** That is why it was offered beside ByteDance rather than as an upgrade, before MuScriptor
replaced both.

---

## 4. Parameters in force

The artifact and leakage filters below apply only to pieces that MuScriptor did not transcribe
(§3.6). Chord grouping and the hand split apply to every piece.

### 4.1 Artifacts: `transcription/artifacts.py`

| Parameter | Value | Why |
|---|---|---|
| `min_duration_seconds` | **0.020** | Sits in the empty band between the 4–16 ms artifact cluster and the 32 ms shortest real note |
| `coincidence_seconds` | 0.050 | The artifact is created *by* a struck chord; a short note alone in silence is something else and is kept |
| `require_coincident_attack` | `True` | |

**Do not raise the floor.** ByteDance's offsets are long because they follow the pedal rather than
the key; Transkun reports true key release and returns 34–85 ms notes for a passage ByteDance calls
200–1700 ms. A 40 ms floor would silently delete a third of a Transkun transcription. There is a
test.

Nothing is deleted from `events.json`. The filter runs on the way out, so every rebuild gets it,
including recordings transcribed before it existed.

### 4.2 Leakage: `transcription/leakage.py`

A key that is already sounding "re-onsets" on another key's attack. Six conjunctive conditions:

| Parameter | Value | Why |
|---|---|---|
| `max_gap_seconds` | 0.040 | Above this engine's 5–20 ms abutting gaps, far below the ~130 ms of the fastest repeated note anyone writes |
| `coincidence_seconds` | 0.040 | How close another key's attack must be to count as coincident |
| `max_overlap_seconds` | 0.010 | More overlap than this is not abutting; something else is happening |
| `lag_ahead_seconds` | **0.012** | How far *ahead* of the cluster the suspect may sit. Behind it, any distance |
| `min_company_margin` | **2** | How many *more* keys attack alongside the suspect than alongside the note it would merge into |
| `max_shared_company` | **0** | How many keys may attack alongside **both** |
| `min_velocity_drop` | 3 | The suspect must be quieter |

Three of these were changed after a real failure and the reasoning is worth keeping.

**The lag test is two-sided.** It used to be a one-sided `min_lag_seconds` of 3 ms, demanding the
suspect arrive *behind* the chord that caused it, because the phantom in the file it was fitted to
did (+6.7 ms). On the Chopin Nocturne, three phantoms arrive at −1.3, −8.2 and −11.5 ms, level with
the cluster or slightly ahead, and all three passed the test. Which side of the attack a secondary
detection lands on is a property of the model's receptive field, not of the playing, so demanding
one sign was over-fitting to one file.

**The asymmetry test compares company instead of demanding none.** Demanding that the predecessor
have *no* company at all is too literal: one phantom was accepted because a single unrelated key
attacked 33 ms after its predecessor. A margin says what the rule always meant: the suspect is born
from a chord its predecessor was not part of. The margin is 2 rather than 1 because at 1 it fires on
a note whose predecessor merely had one fewer neighbour, which is noise.

**Counting company is not enough, and a fixture showed it.** When a whole D7 chord re-articulates,
each of its notes sees two more neighbours than its predecessor did and clears the margin. What
identifies it is *which* keys those are: the same ones both times, because it is the same chord
struck twice. A phantom cannot look like that. It is born from a chord its predecessor was not part
of, so the two sets are disjoint. Zero shared keys is the rule.

**The lag change and the threshold change ship together.** Paired with the old onset threshold of
0.3, the two-sided lag merged away a real `Fa4`, because a phantom sitting beside that note inflated
its company count. It is safe at 0.5, where that phantom never exists.

Tuned for precision throughout: a false merge silently deletes a played note. Since Phase 5 the note
that absorbs a phantom is a copy of the original note, so it keeps its `id` and its `hand`.

### 4.3 Chord grouping: `transcription/events_to_matrix.py`

`GROUP_WINDOW_MS = 40.0`, non-chaining: a group admits later onsets within the window of the
group's **first** onset, not of the previous one (D-04).

**The window is fixed and does not follow `frameMs`.** It used to, and that was wrong in a way worth
naming: it let the column length change the *music*. At 10 ms it created 22 semifusas that do not
exist at 40 ms, and it broke the promise that `frameMs` is only layout.

Grouping runs on raw times, before snapping, because two notes 39 ms apart can fall either side of a
column boundary. "Same frame = same chord" is therefore phase-dependent and unreliable.

Since Phase 5 the build also records `event_ids`: for each onset cell `(column, row)`, the id of the
note that owns it. Every mapping between a split and the notes uses it (the sheet's hand route,
**Predict hands**, the saved hands), instead of matching a row and a rounded start time.

### 4.4 Hands: `hands/`, the saved hands, and the split cache

A beam dynamic program over onset groups (`hands/beam.py`), with a cost model in `hands/costs.py`
and configuration in `hands/config.py`. `hands/threshold.py` keeps the old `Do-4` rule as a
baseline, reachable as `method="threshold"`. The beam loop and the refine rounds report progress
through `hands/progress.py`, which the `two-hands` stage of a job shows in hundredths.

`C_ledger` (`hands/staff.py`, weight `0.50`) charges the ledger lines an assignment forces onto the
page, with separate allowances for running outward past your own staff (6 lines, free: that is
register) and across into the other hand's (2 lines). The gated second pass that repairs what a
group-by-group search structurally cannot see is documented in
[`hand-inference-second-pass.md`](hand-inference-second-pass.md).

**One known hole, still open.** `costs.py` charges the `octave` cost only when `len(events) == 2`,
so an `F1+F2+F3` stack pays nothing for splitting `F3` off. The artifact filter removes the usual
cause on ByteDance pieces; the cost itself has not been generalised.

**The saved hands** (D-31, changed in implementation 08, Phase 5). `pipeline.split_of` paints the
saved hands when every live note that the sheet places at 40 ms has one
(`saved_hands.split_with_saved_hands`), and runs the inference otherwise. A note the sheet cannot
place (shorter than one column, or sharing its column with another note of its key) does not count.
`saved_hands.quick_hand` gives a hand to a note added after the hands were saved: the hand of the
closest pitch among the notes that start within 1 s or still sound at its onset, then middle C. Such
a hand is marked `handGuessed`.

**The split cache** (`transcription/split_cache.py`, Phase 4). The split costs 0.3 to 4.3 s on the
Ubuntu machine (0.56 s median). Before Phase 4 the transcription job computed it and discarded it,
and `GET /matrix/{uuid}/events` computed it on every call. Now every reader asks one cache, keyed
`(uuid, frameMs, mtime of events.json in ns, ...)`, holding 8 entries. A new transcription or any
saved edit is a new key, and `save_edit` also calls `split_cache.forget(uuid)`, because two saves can
fall in the same clock tick. Two requests for the same key at the same time compute it once. The
value is shared and must be treated as read-only.

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
passage is drawn exactly as before. Piles are counted once inside the halfway bands (recounting
inside the new lines ratchets: 447 ms, then 466, then the clamp), per passage, both hands pooled,
and clamped to 80/20 so a rare figure keeps a fifth of the room on each side.

---

## 6. Endpoints

| Route | Returns |
|---|---|
| `GET /matrix/engines` | `{"muscriptor": true}`: the engines the page may offer |
| `GET /matrix/engine` | The one engine: installed, device, loaded, waiting jobs, load error |
| `POST /matrix/transcribe` | `202` and a job id. `422` for any engine other than `muscriptor` |
| `GET /matrix/{uuid}/job` | The waiting or running transcription of a piece |
| `GET /matrix/progress/{jobId}` | SSE stream: progress, `event: chunk` live notes, `event: done` |
| `GET /matrix/jobs/{jobId}` | The same state, for pollers |
| `GET /matrix/{uuid}/events` | `events.json` plus `id`, `hand`, `artifact` / `octaveBelow` per note and the counts. **Flags rather than omits**: a filter you cannot see is a filter you cannot check |
| `PUT /matrix/{uuid}/events/removed` | Mark notes as removed from the recording, by pitch and second |
| `GET /pieces/{uuid}/notes` | The saved notes as columns, with the revisions |

`GET /matrix/{uuid}/runs` is gone: it belonged to the isochrony quantiser, which was deleted with
the tempo model.

Detail in [`endpoints.md`](endpoints.md#3-matrix--running-the-model).

---

## 7. Running the tests

From `aitu-backend/`, natively:

```bash
make test
```

Or in the backend container, from the repository root:

```bash
make test-backend
```

State at the end of implementation 08, Phase 8: **1,039 passed, 1 failed**, in the container and
natively. The failure,
`test_time_score_payload.py::test_the_worked_example_at_00_46_prints_three_equal_corcheas`, existed
before implementation 08 on a clean checkout and is unrelated to it.

MuScriptor is tested without a GPU: `tests/test_muscriptor_engine.py` uses `ReplayModel`, which
replays the Phase 1 events of the first 20 s of Superestrella (`tests/fixtures/pmn`). Two tests run
the real model (`test_the_real_model_on_the_gpu_gives_the_phase_1_notes`,
`test_a_progressive_engine_reports_its_real_model_segments`). They are skipped unless CUDA is visible
and the weights are already in the Hugging Face cache, because a test never downloads 5.5 GB.

`pyproject.toml` sets `pythonpath = ["src", "."]`. The second entry is required:
`tests/test_migration.py` imports `scripts.migrate_to_time_matrix` and `scripts/` has no
`__init__.py`, so without it collection fails before a single test runs and `make test` reports
nothing at all. That was the state until 2026-09-13.

---

## 8. Where to look deeper

- [`events-to-sheet.md`](events-to-sheet.md): why the steps are in this order
- [`time-matrix.md`](time-matrix.md): what the two hand matrices become
- [`hand-inference-second-pass.md`](hand-inference-second-pass.md): the gated repair pass
- [`context/backend/piano-matrix-notation.md`](../../../context/backend/piano-matrix-notation.md):
  the stored notes, the ids and the revisions
- [`endpoints.md`](endpoints.md): the routes that start and follow a transcription
- [`../../issues/piano-matrix-sustains-and-phantom-onsets.md`](../../issues/piano-matrix-sustains-and-phantom-onsets.md): the runbook
- `context/implementations/08-new-algorithm-notes-detection-muscriptor/`: the plan and the phase
  reports behind every MuScriptor number on this page
