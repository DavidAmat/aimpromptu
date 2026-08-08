# 2026-08-02 — Transcription accuracy session

One sitting, driven by two screenshots of *Mr Blue Sky*: a passage of even semicorcheas
printing as a mix of corcheas and semicorcheas, and a phantom `Fa-1` under a played
`Fa-2`/`Fa-3` octave. It ended up touching the backend pipeline, two new Playground surfaces,
and `vexflow-v2`.

**Read this before picking up the tempo work.** The half-built piece is at the bottom.

Overview: [context/music/transcription-quality.md](../../music/transcription-quality.md).
Detail: [documentation/services/backend/transcription-pipeline.md](../../../documentation/services/backend/transcription-pipeline.md).
Runbook: [documentation/issues/rhythm-figures-and-tempo.md](../../../documentation/issues/rhythm-figures-and-tempo.md).

---

## What shipped

| # | Change | Where |
|---|---|---|
| 1 | `GET /matrix/{uuid}/events` — the transcription in seconds, served verbatim | `api/matrix.py` |
| 2 | **Notes Falling (raw)** tab — unquantised, click a note for its exact ms | `pages/playground/NotesFallingRawPage.tsx`, `hooks/useRawEvents.ts`, `music/gridFit.ts` |
| 3 | `RAW_GRANULARITY` fusa → semifusa, with a `raw-granularity.txt` sidecar | `transcription/events_to_matrix.py`, `pipeline.py` |
| 4 | Hand split moved to the **raw** grid; each hand collapsed and cleaned separately | `transcription/pipeline.py::derive` |
| 5 | **Per-hand run quantiser** with a refusal rule and a suggested tempo | `matrix/isochrony.py` |
| 6 | `GET /matrix/{uuid}/runs` + banner with a "Try N BPM" button | `api/matrix.py`, `hooks/useRunReport.ts` |
| 7 | **Artifact filter** — notes under 20 ms that coincide with an attack | `transcription/artifacts.py` |
| 8 | **Transkun** registered as a second engine | `transcription/engine.py`, `pyproject.toml` |
| 9 | Frame toolbox widened, tab strip wrapped | `components/notation/ScoreToolboxDragLayer.tsx` |
| 10 | **BPM tab** + `onTempoRequest` in the package | `vexflow-v2` **0.27.0** |

Suite ended at **698 passed**, with the same two pre-existing failures it started with.
`tsc` and `eslint` clean in both repos.

---

## Decisions, and why

**`events.json` is never filtered in place.** Artifacts and leakage run on the way out, so
every rebuild gets them — including files transcribed before the filters existed — and the
raw view can still show what was discarded. The `/events` route **flags** artifacts rather
than omitting them, with a "Show discarded" switch in the UI. A filter you cannot see is a
filter you cannot check.

**The artifact floor is 20 ms and must stay there.** Durations are bimodal with an *empty
band* between 16 and 32 ms on the reference file, so the threshold is measured rather than
chosen. It looks like there is headroom to 40 ms — there is not: Transkun's key-release
offsets are 34–85 ms. Test: `test_the_floor_stays_below_a_real_key_release`.

**A run that does not fit the grid is refused, not forced.** This was tried the other way
first. Forcing a 1.27-column run to 1 fragmented the passage into 9+12+7 notes with two
5-column holes — rests in the middle of a phrase, worse than the ragged figures. So it is
left as played and reports the tempo it wants.

**Annotations rebase by time, not by a delta.** Chosen over erase-inside because the
reference file has a key change at column 2588 and the natural seam is 2589 — an erase rule
loses a key signature over one column of slack.

**Transkun is not an upgrade.** 122 notes agree with ByteDance on the test passage; it finds
two misses and loses four attacks. It is registered so the two can be judged by ear.

---

## Things that were believed and turned out to be false

Worth recording, because each cost time and each is a plausible thing to believe again.

- **"The 8th/16th mix is a sampling problem."** It is integer arithmetic: 1.27 columns per
  note, twelve gaps that must sum to 15 whole columns.
- **"Per-hand onsets will fix the mix."** They will not. Checked directly: the whole run is
  in one hand and that hand's own onset columns alternate identically. Per-hand is right for
  *pedal and held notes* — a different, real problem — but not for this.
- **"A finer raw grid will fix it."** fusa → semifusa moved the spans from `{1:17, 2:7}` to
  `{1:18, 2:6}`. Aliasing, not resolution.
- **"The package needs a tempo map built."** It already has one. `FrameClock` accepts
  `frameTimestamps`, `GridScore` forwards them, the Time panel already reports a per-region
  step, and `shiftFrameTimestamps` exists for renumbering. The 0.26.2 note that
  `frameTimestamps` is "a no-op until the backend re-quantises against a tempo map" is
  exactly right — the missing half is the backend's.

---

## Half-built: per-region tempo

`matrix/tempo_map.py` is **applied and green (22 tests) but nothing imports it.**

Built: `TempoMap` with regions keyed by seconds; `spans` / `seconds_to_column` /
`column_to_seconds` / `row_timestamps`; `rebase_column`. Seams land on whole columns by moving
the **boundary time**, not by stretching widths — the first version stretched widths and a
test caught that it shifted columns *before* the seam, which is the one thing the feature must
not do.

`vexflow-v2` 0.27.0 has the BPM tab; it calls `onTempoRequest` and `aitu-frontend` does not
pass that callback yet, so the tab currently says the host cannot re-tempo a passage.

Remaining, in order:

1. Quantise through the map — `events_to_raw_matrix`, `approximation`.
2. Persist `matrices/tempo-map.json`; load it in `recompute`.
3. Rebase `grid-notation.json` column anchors when the map changes.
4. `GET`/`PUT` endpoint.
5. Map-aware `rowTimestamps` (`matrix/convert.py:dense_row_timestamps` is still `i * step`)
   so the package's clock and the falling/roll playback slow down in the region.
6. Wire `onTempoRequest` in `GridScore` / `NotationPage`, passing `beatsPerFrame` too.

Doing (3) also unblocks something parked in the 0.26.2 migration: `onMatrixStructurePatch` is
a blocking banner today precisely because nothing could rebase frame-indexed metadata after
the package's Insert/Remove frames gesture.

**Verification target.** On artifact `a1689618`, a **140 BPM** override from 218.1 s should
print f3079–f3094 as twelve uniform semicorcheas. 128 does not work — ratio 0.91 and two
attacks collide. Uniform maps must still reproduce 3624 columns exactly.

---

## Still open, not started

- **Tuplets.** Frames f3064–f3075 sit at 1.69 columns per note, which no tempo resolves.
  Needs a triplet subdivision in `Granularity` and a bracket in the renderer.
- **The `octave` cost only fires on two-note groups** (`hands/costs.py:453`), so an
  `F1+F2+F3` stack pays nothing for splitting `F3` off. The artifact filter removes the usual
  cause; the cost itself is unchanged.
- **Recompute went from sub-second to ~3 s** on a five-minute piece — `decode_matrix` scans 4×
  more columns at semifusa. Acceptable; optimise if it becomes annoying.
- **Better engines.** The augmented ByteDance checkpoint (Edwards & Dixon, ISMIR 2024, same
  architecture, reverb + pitch-shift augmentation, MAPS F1 88.4 vs 87.3) is a checkpoint swap
  and was never done. Aria-AMT is the strongest candidate for the octave problem but wants a
  GPU.

---

## Environment notes for the next agent

- The backend venv is **macOS-native**; tests must run in a Linux container from staged
  source. Recipe in the pipeline doc.
- `vexflow-v2`'s `dist/` is gitignored and served live through the `file:` symlink — **a
  source change with no rebuild silently serves stale bytes.** Its build also cannot run in a
  Linux VM (native rollup). Build on the Mac: `cd vexflow-v2 && npm run build`, then
  `make serve` in `aimpromptu` (which stops first).
- Zenodo and HuggingFace are blocked by the Cowork cloud proxy; PyPI is not. Model checkpoints
  have to be fetched on the Mac.
