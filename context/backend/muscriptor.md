# MuScriptor: the transcription engine

MuScriptor (Kyutai and Mirelo, 2026) turns the audio of a piece into notes. Since implementation 08
it is the only engine the user can use. ByteDance and Transkun stay in the code, with their tests,
but the backend refuses them. This page says how MuScriptor runs in the backend, what it sends while
it runs, and what it stores.

## 1. Why MuScriptor, and why these settings

The old default, ByteDance, gave notes that needed two filters (artifacts and leakage) and still had
false onsets. The user tested MuScriptor on Superestrella and judged it good. Phase 1 of
implementation 08 measured it on six pieces against ByteDance (81 to 98% of onsets agree within
50 ms on five of them; 65% on Superestrella, whose ByteDance notes are the noisiest) and chose the
settings ([`pocs/poc-muscriptor/RESULTS.md`](../../pocs/poc-muscriptor/RESULTS.md)):

| Setting | Value | Reason |
|---|---|---|
| Model size | `large` (1.4 billion parameters) | `medium` and `small` give a different transcription (84 to 86% agreement with `large`) |
| Weight type | `float16` | The same notes as `float32`, 2.2 times faster, 3.5 GB of GPU memory instead of 7 |
| Chunks | One 5-second chunk at a time, with prelude forcing | Prelude forcing carries the notes that still sound into the next chunk. Batching 8 chunks is 4 times faster but changes about 7% of the notes and cuts notes at the chunk borders (decision Q-7) |
| Instruments | `acoustic_piano` only | The project is for the piano (decision Q-3) |
| Filters | None | The artifact and leakage filters had no useful effect, and leakage would merge real repeated notes, since MuScriptor has no loudness |
| Device | The RTX 4090 of the Ubuntu machine (`AITU_DEVICE=cuda` in the container) | `large` on a CPU is far too slow for a live view |

**Speed.** On the RTX 4090, 5 to 9 times faster than the music: about 25 s for the 3:09 of
Superestrella, 21 s for a 2:21 piece, 50 s for the 5:56 of the longest piece of the library. The
first notes appear on the page about 0.3 s after **Transcribe**.

**Licence.** The weights are CC BY-NC 4.0 (non-commercial). The app is for personal use (decision
Q-6). They are gated on Hugging Face: the account behind `HF_TOKEN` accepted the licence once.

## 2. How it runs

```
POST /matrix/transcribe ──▶ the GPU queue (one job at a time) ──▶ MuScriptorEngine.run_signal
        │                                                                │
        │  202 + job id                       chunk messages, live ◀─────┤
        ▼                                                                ▼
GET /matrix/progress/{jobId}  (SSE)           lag correction ──▶ events.json ──▶ done
```

- **One model per process.** `transcription/models.py` keeps one loaded model per size, device and
  weight type. In the container, `AITU_PRELOAD_ENGINE=muscriptor-large` loads it when the server
  starts, so the first transcription does not wait, and a missing token is reported at once by
  `GET /matrix/engine`.
- **One job at a time on the GPU.** `transcription/jobs.py` runs transcriptions in order of
  arrival. A job that waits says so ("Waiting for N other transcriptions to finish"). A second
  request for the same piece gets the job that already runs.
- **What it hears is the selected region.** The cuts of the piece (ranges of 10 ms time frames the
  user deleted on the Audio tab) are removed in memory, with a 5 ms fade at each join, and no audio
  file is written. The notes are stored in the time of the piece, which is shorter by its cuts.
- **The lag correction.** MuScriptor's onsets can be late or early by a constant amount that changes
  from piece to piece (from 17 ms late to 22 ms early on six pieces). After the notes are known,
  `transcription/lag.py` finds the shift that puts the onsets best on the onset envelope of the
  audio and subtracts it, in whole milliseconds. Below 200 distinct onsets (about a minute of music)
  nothing is corrected, because the answer is not stable. No tempo is involved (rule 3).

## 3. The live stream

The progress stream of the job (`GET /matrix/progress/{jobId}`, Server-Sent Events) carries the notes
as they are found, so the Notes tab draws the rectangles while the transcription runs:

```json
{"type": "chunk", "done": 3, "total": 38, "upToMs": 15000, "durationMs": 189160,
 "open":   {"id": [41, 42], "key": [40, 52], "onMs": [14210, 14800]},
 "closed": {"id": [30, 31], "key": [39, 44], "onMs": [9900, 11000], "lenMs": [1200, 800]}}
```

- A message is sent at most every 0.25 s while notes start or end, not only once per chunk.
- `closed` holds the rectangles closed since the previous message; `open` every one still
  sounding, which the page draws up to `upToMs`.
- The ids are the ids the notes keep when they are saved. The times are before the lag correction;
  the page reads the saved notes once after the last frame, `event: done`.
- Every frame is numbered, so a page that connects late, or reloads, receives everything sent so
  far. `GET /matrix/{uuid}/job` finds the running job of a piece.

## 4. What it stores

`events.json` of the piece, in the piano matrix notation's stored form
([piano-matrix-notation.md](piano-matrix-notation.md)): one note per rectangle with its id, MIDI key,
start and end in seconds, and velocity 64 (MuScriptor has no loudness). The header records `engine`
(`muscriptor-large`), `lagCorrectionMs`, the `audioRevision` the notes were made from, and raises the
revisions, so the Hands and Sheet steps know they must be done again
([pieces-and-revisions.md](pieces-and-revisions.md)). The previous notes and reading are copied into
`history/vN/` first.

## 5. Settings

| Variable | Default | Meaning |
|---|---|---|
| `HF_TOKEN` | none | Hugging Face token; required for the gated weights |
| `AITU_MUSCRIPTOR_MODEL` | `large` | `small`, `medium` or `large` |
| `AITU_MUSCRIPTOR_DTYPE` | `float16` | `float32`, `float16` or `bfloat16` |
| `AITU_PRELOAD_ENGINE` | empty natively, `muscriptor-large` in the container | An engine to load at start; `none` turns it off |
| `AITU_DEVICE` | `cpu` natively, `cuda` in the container | `cpu`, `cuda` or `auto` |

`GET /matrix/engine` answers what is installed, the device, the loaded models, the jobs waiting and
the error of the preload, if any.

## Where to look deeper

- The engine in the pipeline, with ByteDance and Transkun:
  [`documentation/services/backend/transcription-pipeline.md`](../../documentation/services/backend/transcription-pipeline.md)
- The routes: [`documentation/services/backend/endpoints.md`](../../documentation/services/backend/endpoints.md)
- The measurements and the choice of settings: [`pocs/poc-muscriptor/RESULTS.md`](../../pocs/poc-muscriptor/RESULTS.md)
- The plan and the phase reports:
  [`implementations/08-new-algorithm-notes-detection-muscriptor/`](../implementations/08-new-algorithm-notes-detection-muscriptor/README.md)
- Code: `aitu-backend/src/aitu_backend/transcription/` (`engine.py`, `models.py`, `jobs.py`,
  `live.py`, `lag.py`, `pipeline.py`), `audio/frames.py`
