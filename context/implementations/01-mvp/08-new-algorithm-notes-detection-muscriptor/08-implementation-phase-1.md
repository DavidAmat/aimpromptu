# 08 Phase 1: MuScriptor on Ubuntu, and what it outputs

The plan is [`08-plan.md`](08-plan.md) section 12, Phase 1. The status lookup is
[`08-checklist.md`](08-checklist.md). The POC is [`../../../../pocs/poc-muscriptor/`](../../../../pocs/poc-muscriptor/),
and its measured results are in its [`RESULTS.md`](../../../../pocs/poc-muscriptor/RESULTS.md). This report is
for the agents of later phases: it says what was done, what changed in the plan, and what Phase 2 to
Phase 4 must know.

# 1. What was done

| Task | Result |
|---|---|
| 1.1.1 checks | Driver 595.58.03 (CUDA 13.2), toolkit 12.9, Docker 29.3.1 with the `nvidia` runtime, `nvidia-ctk`, uv 0.11.3, Node 22.19.0, ffmpeg 6.1.1. `docker run --rm --gpus all nvidia/cuda:12.9.1-base-ubuntu24.04 nvidia-smi -L` sees the RTX 4090. Nothing missing |
| 1.1.2 data | `scripts/migrate/manifest.sh --summary` gives exactly the Phase 0 table: 10,626 files, same bytes per folder |
| 1.1.3 app | `uv sync --extra transcription --extra transkun`: torch 2.13.0+cu130, torchaudio 2.11.0+cu130, `torch.cuda.is_available()` true. `pytest`: **906 passed, 1 failed** (the known `test_the_worked_example_at_00_46_prints_three_equal_corcheas`, Phase 0 report 2.1). `vexflow-v2` and `aitu-frontend` build |
| 1.2.1 MuScriptor | Cloned to `/home/david/Documents/projects/music/muscriptor` at `7f213af` (0.3.0), `uv sync`. Its tests: 221 passed, 24 skipped (need weights). Web UI built with `npx -y pnpm@10.20.0` (it uses pnpm; `npm ci` fails) |
| 1.2.2 Hugging Face | `HF_TOKEN` is already exported in `~/.zshrc` (read token of `DavidAmat`). The user accepted the three licences. Weights in `HF_HUB_CACHE=/mnt/ssd2/hf/data/hub`: large 5.47 GB, medium 1.23 GB, small 0.41 GB |
| 1.2.3 their tools | `muscriptor transcribe` on 20 s: 5.0 s on the GPU. `muscriptor serve` runs on `127.0.0.1:8222` (large, float16), `/health` answers and `/transcribe` streams. The user opens it through the tunnel (walkthrough) |
| 1.3.1 to 1.3.6 | `pocs/poc-muscriptor/`, results in `RESULTS.md` |
| 1.3.7 | `RESULTS.md` section 1, this report, and the plan's section 3 and 9.1 |

`aitu-frontend/package-lock.json` changed by one line on `npm install`: the `../../vexflow-v2` entry now
says `0.42.0` instead of `0.15.0`. That is the real version of the sibling, so the change is kept.

# 2. The POC

Two environments, because the backend does not depend on MuScriptor until Phase 4:

- `0*_*.py` run in MuScriptor's venv: `cd ../muscriptor && uv run python ../aimpromptu/pocs/poc-muscriptor/scripts/<script>`.
- `1*_*.py` run in the backend venv: `cd aitu-backend && uv run python ../pocs/poc-muscriptor/scripts/<script>`.

`common.py` imports neither package at module level and sets `HF_HUB_CACHE` before `huggingface_hub`
is imported. `--uuid <prefix>` selects another library piece; Superestrella is the default. `out/` is
7.6 MB and is committed like the other POCs' `out/`.

Pieces measured: Superestrella `a585f9eb`, La Tortura `0815f602`, 7 Years `1a16a836`, Grace Kelly
`56543911`, Birds of a Feather `b80e6f5a`, The Winner Takes It All `fb0b0989`.

# 3. Findings that change the plan

The plan's section 3 and section 9.1 are updated. The details:

1. **No velocity.** `tokenizer/notes.py`: `EventRange("velocity", 0, 1)`. The plan said the velocity
   exists but is hidden; it does not exist. `NoteEvent.velocity` stays 64 for MuScriptor notes.
2. **Filters off for MuScriptor.** `artifacts.py` drops 0 to 4 notes per song. `leakage.py` merges
   none, because its `min_velocity_drop = 3` cannot pass with equal velocities. With
   `min_velocity_drop = 0` it would merge 19 to 58 same-key pairs per song, every one with a 0 ms gap:
   MuScriptor's retrigger rule (a new onset closes the open note of that key at the same instant) makes
   every repeated note "abut". Those are real notes. Phase 4 turns both off for the MuScriptor engine.
3. **The lag is per piece.** MuScriptor minus ByteDance, onset of matched notes: +15.3, -12.2, -16.0,
   -13.4, -16.8, +7.6 ms. MuScriptor's `detect_grid` refused all six pieces ("no fixed tempo", 2.8 to
   6.1 s RMS), so its own `onset_delay` is unavailable, and rule 3 forbids storing its BPM anyway.
   A spectral-flux envelope of `normalized.wav` at a 2 ms hop (`librosa.onset.onset_strength`,
   `hop_length=32, n_fft=512, lag=5`) puts ByteDance at -16 to -19 ms on every piece, and the
   MuScriptor-minus-ByteDance difference it gives matches the matched-pairs median within 6 ms. The
   Phase 4 rule: `lagCorrectionMs = round(best_lag(MuScriptor onsets) + 17)`, clipped to +-40 ms, and
   subtracted from every onset and release before saving. `best_lag` is `LAGS_MS[argmax]` of
   `11_lag.py:lag_curve` (lags from -80 to +80 ms, step 1 ms, onsets de-duplicated to 1 ms). The
   envelope needs the 2 ms hop: at 10 ms the answer can only be a multiple of 10 ms, because MuScriptor
   onsets sit on a 10 ms grid. Check the sign on one piece before relying on it: on Superestrella the
   correction is +15 ms, which moves the notes **earlier**.
4. **Speed.** float16 weights: same notes as float32, 2.2 times faster, 3.5 GB. Whole songs at 5.3 to
   8.6 x real with batch 1 and prelude forcing. `torch.compile(dynamic=True)` is slower. The user chose
   **batch 1 with prelude forcing** over batching (Q-7 in the plan's section 11).
5. **Conditioning stays.** It loses one chunk of Superestrella (30 to 35 s: 35 notes against 58 free),
   but it agrees more with ByteDance on 5 of 6 whole songs, and the free mode invents 70
   `electric_bass` notes and 70 `drums` hits on Superestrella.

# 4. Notes for later phases

**Phase 2 (the format).** MuScriptor times are exact multiples of 10 ms, so `onMs` and `lenMs` are
integers without rounding error, before the lag correction. After a per-piece correction they are
still integers, but no longer multiples of 10. Note lengths follow the key release (median 230 ms,
ByteDance 866 ms), so the dense matrix at 10 ms has far fewer sustain cells than a ByteDance piece.

**Phase 3 (containers).** The backend image needs the same torch build (`+cu130` wheels work on driver
595.58.03). The Hugging Face cache path used here is `HF_HUB_CACHE=/mnt/ssd2/hf/data/hub`, not
`HF_HOME`: `HF_HOME` would also move the token file, and the existing cache lives at that path. The
beat model of `beat_this` downloaded itself to `~/.cache/torch/hub/checkpoints/` (77 MB); the app does
not use it. MuScriptor's server pattern (one lock, one job at a time) matches the plan's single GPU
queue.

**Phase 4 (the engine).**

- Load with `TranscriptionModel.load_model("large", device="cuda", dtype="float16")`: 1.0 s from the
  SSD, 2.74 GB of weights, 3.5 GB peak at batch 1. Call `transcribe((tensor [1, T], 16000),
  instruments=["acoustic_piano"], batch_size=1, prelude_forcing=True)`.
- The generator yields `ProgressEvent(0, total)` first, then notes token by token (median 22 ms
  apart), then `ProgressEvent(k, total)` after the last note of chunk k. A chunk takes 0.67 s median
  (1.0 s max) on Superestrella. `NoteEndEvent` of a sustained note can come several chunks later.
- A note's end is known only when its `NoteEndEvent` arrives; the plan's `open` list of section 9.3
  covers that.
- MuScriptor prints timings to stderr with `print`, one line per chunk; the job should capture or
  silence stderr.
- The key and value cache is allocated for `max_gen_len = 2000` tokens per chunk: that, not the
  weights, is what makes batches expensive (17.6 GB at batch 8 in float32).
- Not measured, a possible later gain: CUDA graphs for the batch-1 decode step. At 7.8 x real a
  3.5-minute song takes about 27 s, and decoding is close to the memory limit of reading 2.7 GB of
  weights per token, so the gain is probably below 30%.

**Phase 7 (the live view).** Their UI's ideas are listed in `RESULTS.md` section 8.

**Needed later, at Phase 4.** Nothing new from the user: the token and the licences are in place.

# 5. The user's check

The user opened `muscriptor serve` (`127.0.0.1:8222`, large, float16) from the Mac through
`ssh -N -L 8222:localhost:8222 ubuntu`, transcribed Superestrella and judged the result good. The
server was then stopped; nothing of MuScriptor runs in the background.
