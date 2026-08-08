> Context: [context/music/transcription-quality.md](../../../context/music/transcription-quality.md)

# The transcription pipeline: modules, order, parameters

Everything between an audio file and the two hand matrices, as of **2026-08-02**. Exact
module paths, the parameters actually in force, and the endpoints that expose them.

---

## Order of operations

```text
audio
  -> engine                      transcription/engine.py         -> list[NoteEvent] in seconds
  -> events.json                 transcription/pipeline.py        the transcription, kept forever
  -> drop artifacts              transcription/artifacts.py       notes too short to be notes
  -> merge leaked re-onsets      transcription/leakage.py         phantom re-strikes
  -> place on the raw grid       transcription/events_to_matrix.py  SEMIFUSA
  -> clean sustains (whole kbd)  matrix/cleaning.py               input to the beam only
  -> split hands                 matrix/hands.py + hands/         at RAW granularity
  -> even out runs, per hand     matrix/isochrony.py
  -> collapse each hand          matrix/granularity.py            to the display granularity
  -> clean each hand             matrix/cleaning.py               Appendix B, per hand
  -> combine                     -> clean matrix
```

Two orderings in there are load-bearing and were each arrived at by fixing a real defect:

- **Artifacts before everything.** One phantom bass note an octave under a played octave
  makes the stack unholdable and forces the hand splitter into a wrong answer. Also before
  `leakage`, whose asymmetry test asks which other keys attacked alongside a suspect.
- **Hands before collapse.** Two attacks closer than one display column merge into one column
  when collapsed; the splitter then sees a chord where the player struck twice. Measured: 5
  such pairs in 984 attack groups on the reference file.

`recompute()` rebuilds all of this from `events.json` on every call, which is why a
granularity or BPM change is milliseconds and why no step needs an "edit" operation — a
different quantisation simply produces a different matrix.

---

## Files on disk

`data/audio/<uuid>/matrices/`:

| File | What it is |
|---|---|
| `events.json` | **The transcription**, in seconds. Never filtered in place. |
| `raw.npz` | The raw grid, at `RAW_GRANULARITY` |
| `raw-granularity.txt` | Which granularity `raw.npz` was written at |
| `raw-edited.flag` | Present once the grid was hand-edited; disables re-quantisation |
| `collapsed_<gran>.npz`, `clean_<gran>.npz`, `two-hands_<gran>_{right,left}.npz` | Derived |
| `hands_<gran>.json` | The compact hand map for that granularity |

**`raw-granularity.txt` is a safety file, not bookkeeping.** `RAW_GRANULARITY` is a constant
in the source, so before this file existed, changing it silently reinterpreted every grid
already on disk — a grid written as fusa read as semifusa puts every note at half its real
time. Artifacts that can be re-quantised never notice (they are rebuilt); a hand-edited one
cannot be rebuilt and would have been corrupted. **A missing file means fusa**, which is a
fact about the file, not a licence to assume today's constant.

---

## Parameters in force

### Engine

`RAW_GRANULARITY = Granularity.SEMIFUSA` (`transcription/events_to_matrix.py`), moved from
`FUSA` on 2026-08-02.

ByteDance thresholds are the package's own defaults, not overridden anywhere: `onset 0.3`,
`offset 0.3`, `frame 0.1`, 16 kHz, 10 s segments at 50 % overlap. Transkun has **no
thresholds at all** — the semi-CRF decodes note intervals directly.

### Artifacts — `transcription/artifacts.py`

| Parameter | Value | Why |
|---|---|---|
| `min_duration_seconds` | **0.020** | Sits in the empty band between the 4–16 ms artifact cluster and the 32 ms shortest real note |
| `coincidence_seconds` | 0.050 | The artifact is created by a struck chord; a short note alone is kept |
| `require_coincident_attack` | True | |

**Do not raise the floor.** See the module docstring: Transkun's key-release offsets are
34–85 ms, so 40 ms would delete a third of a Transkun transcription. There is a test.

### Leakage — `transcription/leakage.py`

Four conjunctive conditions: gap ≤ 40 ms, coincidence 40 ms with an asymmetry test, ≥ 3 ms
lag, ≥ 3 velocity drop. Tuned for precision — a false merge silently deletes a played note.

### Isochrony — `matrix/isochrony.py`

| Parameter | Value | Why |
|---|---|---|
| `min_onsets` | 4 | Three notes fit a constant spacing by accident |
| `gap_tolerance` | 0.2 | Per gap, against the **median of the gaps so far** |
| `min_gap_tolerance_columns` | 1.0 | A 5.07-column spacing snaps as 5 or 6; without this floor the snap's own quantisation reads as rubato |
| `max_span_columns` | 8 | A long rest ends a run |
| `max_span_error` | **0.15** | Beyond this the run is **refused**, not forced — see below |

Runs are found against the **median of the gaps already in the run**, not the mean of the
candidate window. Where a slow figure meets a fast one (`6,7,7,6,5,5,5…`) a window mean drags
the average up, swallows the first fast notes, and anchors the fast run to the wrong column.

`max_span_error` is the important one. Forcing a 1.27-column run into 1 ends it a quarter
short and the shortfall comes out as a rest inside the phrase. Refused runs produce a
`RunSuggestion` carrying the tempo that would have made them exact.

`IsochronyReports.suggested_bpm` **clusters** suggestions at 5 % and returns the
onset-weighted mean of the heaviest cluster — not the longest run's answer, because a run at
exactly 1.5 columns is undecidable (rounds to 2 → asks 237 BPM, to 1 → asks 119) and is often
the longest.

### Hands

Unchanged cost model (`hands/config.py`), but note the hole found on 2026-08-02 and still
open: `costs.py` charges the `octave` cost only when `len(events) == 2`, so an `F1+F2+F3`
stack pays nothing for splitting `F3` off. The artifact filter removes the usual cause; the
cost itself has not been generalised.

`TwoHands.hand_map()` now reads the map **off the two grids** in `(column, row)` order rather
than copying `inference.hand_map`. It has to: inference runs at semifusa and the persisted
hands are at semicorchea, so two onsets that collapse into one column would leave the string
one character too long and every hand after it off by one.

---

## Engines

Registered in `ENGINES` (`transcription/engine.py`); the Input tab shows every one and greys
out what is not installed.

| Name | Install | Notes |
|---|---|---|
| `bytedance` | `uv sync --extra transcription` | Default. Checkpoint downloaded to `~/piano_transcription_inference_data/` |
| `transkun` | `uv sync --extra transkun` | Weights ship inside the wheel. No thresholds. ~1.4× realtime on CPU |
| `basic-pitch` | — | Cannot install on 3.12 (tensorflow pin) |
| `silent` | — | Stub for tests |

**`uv sync` installs only the extras you name**, so `--extra transkun` alone uninstalls
ByteDance. For both: `uv sync --extra transcription --extra transkun`.

**Transkun must not be chunked.** `TransKun.transcribe` threads a `startPos` between
consecutive segments — the CRF continues its decode across the boundary. External 20 s chunks
with 4 s overlap shifted every onset by ~10 ms per chunk. It runs whole; progress comes from
wrapping `model.transcribeFrames`, which the internal loop calls once per segment.

Comparison on the reference passage (254.3–271.5 s): 122 notes agree, Transkun finds two
ByteDance misses (`D#3`, `D3` completing an octave) and loses four `A#2` attacks. **Differently
wrong, not better.**

---

## Endpoints added 2026-08-02

| Route | Returns |
|---|---|
| `GET /matrix/{uuid}/events` | `events.json` verbatim, plus `artifact` / `octaveBelow` per note and `artifactCount` / `octavePhantomCount`. **Flags rather than omits** — a filter you cannot see is a filter you cannot check |
| `GET /matrix/{uuid}/runs?granularity=&tempo_bpm=` | `{tempoBpm, granularity, moved, suggestedBpm, runs[]}` where each run carries `hand, column, seconds, onsets, playedSpan, printedSpan, applied, suggestedBpm` |

When converting a run's raw column to a display column, derive the ratio **from the
granularity hierarchy**, never from a ratio of frame counts — both counts are ceilings, so
14733/3684 gives 3 where the hierarchy says 4.

---

## Built but not wired: `matrix/tempo_map.py`

A piecewise clock for per-region tempo. Applied, 22 tests green, **nothing imports it yet.**

- Regions are keyed by **seconds, never by column** — a column number only means something
  under a tempo, so a region stored as "from column 2589" stops pointing at itself the moment
  it is applied.
- Column widths inside a region are **exact**; the **seam time** absorbs the rounding, moving
  to the nearest whole column (< 84 ms at 178 BPM). The first implementation did the opposite
  — stretched each region's width to land on the requested second — and a test caught that it
  shifted columns *before* the seam.
- `rebase_column(column, old, new, …)` carries an anchor across a change by time. One rule
  covers all three cases: before → maps to itself, after → moves correctly with no delta
  arithmetic, inside → lands on the moment it was written for.

Column-indexed metadata that will need rebasing (`grid-notation.json`):
`keyChanges.fromColumn`; `ottavas` / `clefChanges` (`fromColumn` + `toColumn`); `passages`
(`startColumn` + `endColumn`); `lyrics` / `fingers` / `texts` / `spellings` /
`stemDirections` (`column`). `hands_*.json` is regenerated, so it does not count.

**Still to do:** quantisation using the map, `matrices/tempo-map.json` persistence, rebasing on
change, the endpoint, map-aware `rowTimestamps` (`matrix/convert.py:dense_row_timestamps` is
still `i * step`), and the host wiring for the package's `onTempoRequest`.

---

## Running the tests

The backend venv is macOS-native and will not run in a Linux VM. From a clean container:

```bash
tar -czf src.tgz --exclude=__pycache__ src tests pyproject.toml   # in aitu-backend
python -m venv venv && venv/bin/pip install -U pip setuptools wheel
venv/bin/pip install fastapi 'pydantic>=2.9' numpy scipy tqdm python-multipart pytest httpx
PYTHONPATH=$PWD/src venv/bin/python -m pytest
```

**Two failures are pre-existing** and fail on an untouched tree:
`test_api_smoke.py::test_scores_returns_a_list` and
`test_transcription.py::test_changing_the_bpm_reinterprets_the_same_grid` (it asserts the frame
count is BPM-invariant, which stopped being true when `recompute` began re-quantising).
Everything else was green at **698 passed** on 2026-08-02.
