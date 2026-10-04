# 08 Phase 4: MuScriptor in the backend, and the live stream

The plan is [`08-plan.md`](08-plan.md) sections 8, 9.1 to 9.3, 10.5 and section 12, Phase 4. The
status lookup is [`08-checklist.md`](08-checklist.md). This report is for the agents of later phases:
what was built, the choices made inside the phase, the measurements, and what Phases 5 to 9 must
know.

# 1. What was done

| Task | Result |
|---|---|
| 4.1.1 engine | `MuScriptorEngine` in `transcription/engine.py` (`name` is `muscriptor-<size>`), `engine_installed("muscriptor")`. `run_signal(samples, rate, reporter, first_id=...)` returns an `EngineRun` (events, lag correction, details) |
| 4.1.2 forced | `DEFAULT_ENGINE = "muscriptor"`, first in `ENGINES`; `SELECTABLE_ENGINES = ("muscriptor",)`; `GET /matrix/engines` lists only it (the Input page then hides its engine choice, no frontend change); `POST /matrix/transcribe` refuses any other engine with 422. ByteDance, Transkun, Basic Pitch and Silent stay and their tests pass |
| 4.1.3 registry | `transcription/models.py`: one MuScriptor model per `(size, device, dtype)`, one shared engine per `(name, device)` for the others (`engine.shared_engine`). `AITU_PRELOAD_ENGINE=muscriptor-large` (set by `compose.yaml`; `none` turns it off) loads it on a thread at startup and warms the lag measurement. `GET /matrix/engine` reports installed, device, loaded, waiting jobs and the preload error |
| 4.1.4 GPU queue | `transcription/jobs.py`: `submit(..., gpu=True)` runs on one worker thread in order of arrival, with a `waiting` stage ("Waiting for N other transcriptions to finish"). `key=` returns the waiting or running job of the same piece instead of a second one. The range-edit take (`POST /audio/{uuid}/edits/{session}/transcribe`) uses the queue too |
| 4.1.5 lag and filters | `transcription/lag.py` (Phase 1 rule, vectorised; section 2.2). `pipeline.filters_for(engine)`: no artifact or leakage filter for `muscriptor-*` pieces, both kept for every other piece. Large, float16, batch 1, prelude forcing, `acoustic_piano` only |
| 4.2.1 cuts | `metadata.json`: `cuts` (sorted `[startFrame, endFrame)` of 10 ms frames, validated) and `audioRevision`. `store.set_cuts` bumps the revision only on a change. `GET` and `PUT /audio/{uuid}/cuts` (normalize, 409 on an old `baseRevision`, 422 when nothing would be kept) |
| 4.2.2 frame table | `audio/frames.py`: `FrameTable` (`to_original`, `to_piece`, `range_to_original`, `rows`), one `searchsorted` per lookup |
| 4.2.3 joined audio | `frames.join_kept`: kept frames joined in memory, 5 ms linear fade out and in at each join inside the kept samples, frame count unchanged. MuScriptor gets the samples; an engine that reads a file gets a temporary WAV only when there is a cut |
| 4.2.4 cut after a transcription | Notes whose `audioRevision` differs from `metadata.json` are stale: `pipeline.notes_are_stale`, `current_events`; `run_pipeline` and the route transcribe again instead of reusing them; the cuts route reports `notesStale` |
| 4.3.1 chunk messages | `transcription/live.py` (`LiveNotes`), sent through `reporter.send` as `event: chunk` SSE frames (section 2.3) |
| 4.3.2 reconnect | Every frame kept and numbered (`id:`); each reader has its own position; `Last-Event-ID` resumes; `GET /matrix/{uuid}/job` finds the running job of a piece |
| 4.3.3 history | `history.snapshot_notes`: `events.json` and `rhythm.json` copied to `history/vN/` (no audio) before a new transcription replaces them |
| 4.4.1 and 4.4.2 split cache | `transcription/split_cache.py`, one cache for every reader, keyed `(uuid, frameMs, events.json mtime ns)`, one computation per key when two readers ask at once. `pipeline.split_of` and `warm_split`; `time_score._hands`, `pipeline.hands_of` and `GET /matrix/{uuid}/events` use it; the route warms it after saving |
| 4.5.1 fake model | `tests/test_muscriptor_engine.py`: `ReplayModel` replays the Phase 1 events of the first 20 s of Superestrella (`tests/fixtures/pmn`). Also `tests/test_audio_frames.py` and `tests/test_jobs.py` |
| 4.5.2 GPU test | `test_the_real_model_on_the_gpu_gives_the_phase_1_notes`: skipped unless CUDA is visible and the weights are already in the Hugging Face cache (a test never downloads 5.5 GB). Natively with `HF_HUB_CACHE=/mnt/ssd2/hf/data/hub`: passes in 3.5 s |

Checks, natively (`aitu-backend/.venv`): `pytest` all pass except the known
`test_the_worked_example_at_00_46_prints_three_equal_corcheas` (Phase 0 report 2.1); 45 new tests.
`black` and `flake8` clean on the changed files; `mypy`: no new error (the remaining ones are older:
two unused ignores in `engine.py`, the `time_score.py` and `hand` lines).

The test run inside the container (`make test-backend`) was done on 2026-09-29, after the hardware incident of section 4.

Also changed: `compose.yaml` and `.env.example` (`AITU_MUSCRIPTOR_MODEL`, `AITU_MUSCRIPTOR_DTYPE`,
`AITU_PRELOAD_ENGINE`), `config.py`, `pyproject.toml` (`librosa` in the `muscriptor` extra; the lock
gained only that line, 221 packages as before), `progress.py` (`send`), `store.py`
(`set_cuts`), `formats.py` (`sample_count`), `pmn/muscriptor.py` (`next_id`, `event_kind`).
Plan sections 6.2, 8.2, 9.1, 9.2, 9.3 and 10.5, and `context/backend/piano-matrix-notation.md`, are
updated.

# 2. Choices made inside the phase

## 2.1 The notes are in the time of the piece

The plan's section 6.2 said `onMs` is in ms "of the original audio timeline"; section 9.2 (Q-1) says
the piece is shorter by its cuts. The notes are stored in the time of the piece; the frame table maps
to the original for playback. For a piece with no cut (every piece today) the two are the same. Both
documents now say so.

## 2.2 The lag needs about a minute of music

On Superestrella the rule gives +15 ms on the whole song (Phase 1's answer), 13 to 15 ms on any 60 s
excerpt (about 220 distinct onsets), and anything from -7 to +17 ms on 20 s excerpts (about 70).
`lag.MIN_ONSETS = 200`: below it no correction is applied. librosa compiles itself on first use (7.7 s
in the container, then 0.3 s), so the preload calls `lag.warm_up()`.

## 2.3 The stream

- One message per chunk, as planned, **plus** messages inside a chunk at most every 0.25 s when a note
  started or ended, and one final message (`LiveNotes.finish`) for the notes MuScriptor closes after
  its last progress event; a note never closed ends at the end of the piece there, as in the saved
  notes. `done` counts whole chunks.
- Message: `{"type": "chunk", "done", "total", "upToMs", "durationMs", "open": {id, key, onMs},
  "closed": {id, key, onMs, lenMs}}`. `closed` holds only the rectangles closed since the previous
  message; `open` holds every one still sounding. Times are the engine's own (before the lag
  correction), ids are the saved ids.
- The final frame: `event: done`, `{"type": "done", "status", "error", "audioUuid", "revision",
  "lagCorrectionMs", "noteCount"}`. The Input page reads only `status` and keeps working.
- The split is not computed before `done` any more: the route warms the split cache on a thread after
  saving.

## 2.4 Revisions

A new transcription writes `notesRevision` (1, or one more than before), the `audioRevision` it was
made from, `engine` and `lagCorrectionMs`, and continues the ids after `nextId`. `handsRevision` is not
touched: what a new transcription does to it belongs to the chain of Phase 5.

## 2.5 Smaller points

- MuScriptor's `print` lines are silenced by shadowing `print` in its own three modules, not by
  redirecting the output of the whole server.
- A range transcription (`startSeconds`, `endSeconds`, the older path) ignores the cuts.
- `editing/preview.py` still applies the default filters to takes, which MuScriptor now transcribes.
  Phase 1 measured the effect as 0 to 4 notes per song; left as is.
- JSON of the SSE frames is compact (no spaces after separators).

# 3. Measurements

`aitu-backend/scripts/bench_stream.py`, through the HTTP routes of the backend container, on a
temporary uploaded copy of Superestrella (189 s), deleted afterwards. Raw answer:
[`measurements/phase-4-stream.json`](measurements/phase-4-stream.json).

| What | Value |
|---|---|
| First rectangle on the stream | 0.25 s after the request |
| `chunk` messages | 122; median gap 0.25 s, longest 0.27 s |
| Whole transcription, to `done` | 25.6 s (7.4 x real); the lag step 0.4 s |
| Lag correction | +15 ms (Phase 1: +15 ms) |
| Notes | 1,351; 1,346 with the same key and onset as the Phase 1 native run |
| Sheet request 2 s after `done`, 40 ms (warmed) | 27 ms |
| Sheet request, 20 ms (not warmed) | 714 ms |
| Sheet request at once after `done`, 40 ms | 766 ms (waits for the warm-up still running; an earlier run) |
| With a 5 s cut at 60 s | 24.8 s, 1,309 notes; every note before the join (343) and from 5.5 s after it (914) identical to the whole piece; no note at the join itself |

The 5 notes that differ from Phase 1 come from the audio, not the engine: the copy was converted
again by the container's ffmpeg 5.1, whose samples differ from the stored `normalized.wav` by at most
one unit on 0.17% of the samples.

Near the join, the whole piece has notes at 65.285 s (keys 54, 59, 63, 73) and the cut piece at
60.295 s (keys 54, 58, 61, 73): 10 ms later and two keys different, within the first chunk after the
join. No false note appears at the join.

# 4. The hardware incident, and what is left of Phase 4

On 2026-09-28 the two `make test-backend` runs in the container crashed: an "invalid opcode" inside
`libpython3.12` (exit 132), then a segfault in the hand split of an old test, and the machine froze
and restarted. The kernel had logged a machine check error earlier the same day. The cause was the
processor (Intel 13th/14th gen "Vmin Shift" instability, i9-14900KF on BIOS 1645), not the code of
this phase. The BIOS was updated to 1836 (Intel Default Settings) on 2026-09-29, and the user's
stress tests pass since.

**Closed on 2026-09-29.** After the BIOS update: `make up` healthy, `GET /matrix/engine` reports
`muscriptor-large (cuda, float16)` loaded with no error, and `make test-backend` gives 996 passed and
1 failed (the known `test_the_worked_example_at_00_46_prints_three_equal_corcheas`) in 32 s, with no
crash. Both GPU tests (`test_the_real_model_on_the_gpu_gives_the_phase_1_notes`,
`test_a_progressive_engine_reports_its_real_model_segments`) ran and passed in the container.

# 5. Notes for later phases

**Every phase.** After a BIOS reset, check that `make up` still gives a healthy backend and that
`GET /matrix/engine` shows `muscriptor-large (cuda, float16)` loaded. The backend container loads the
model (3.5 GB of GPU memory) at every start, including every `--reload` restart. Nothing of Phases 3
and 4 is committed yet.

**Phase 5 (piece API).**
- The revisions a transcription writes are in section 2.4; add the rest of the chain.
- `pipeline.notes_are_stale` and `jobs.active(f"transcribe:{uuid}")` give the `stale` and `running`
  states of the status endpoint.
- The saved hands must be read by `pipeline.split_of`'s compute, or the sheet must stop calling it;
  the split cache key already changes with every save of `events.json`.

**Phase 6 (Audio tab).** `GET` and `PUT /audio/{uuid}/cuts` exist, with the `kept` table and
`notesStale`. **Transcribe** is: `PUT` the cuts, then `POST /matrix/transcribe` (no `force` needed:
stale notes are transcribed again).

**Phase 7 (live view).** Listen to `chunk` on the progress stream (section 2.3), then read the saved
notes after `done`. `GET /matrix/{uuid}/job` finds a running job after a reload; frames carry `id:`
for `Last-Event-ID`. Playback maps piece time to original time with the `kept` table.
