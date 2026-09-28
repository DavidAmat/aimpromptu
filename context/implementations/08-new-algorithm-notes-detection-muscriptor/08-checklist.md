# 08: MuScriptor, the live piano roll, and the move to Ubuntu: checklist

The status lookup for this implementation. The plan is [`08-plan.md`](08-plan.md), and the brief is
[`08-prompt.md`](08-prompt.md). Each phase report is `08-implementation-phase-N.md`, written by the
agent that finishes the phase.

One phase is one agent session. A story is ticked only when every task under it is done.

Status letters: `[x]` complete, `[p]` in progress, `[b]` blocked, `[c]` cancelled, `[ ]` not started.

## Decisions

The plan's section 11. All seven were answered by the user on 2026-09-28.

- [x] **Q-1** After a cut, the piece is shorter. The audio and the piano matrix notation share one axis of 10 ms time frames, and a cut is a range of frames (plan section 9.2).
- [x] **Q-2** A cut after a transcription starts a new transcription. The old notes go into history.
- [x] **Q-3** Piano only: every transcription is conditioned on `acoustic_piano`.
- [x] **Q-4** Notes Falling stays. The old Piano Roll tab is removed in Phase 9.
- [x] **Q-5** The frontend container runs in development mode.
- [x] **Q-6** The non-commercial licence is acceptable: the app is for personal use.
- [x] **Q-7** One chunk at a time (batch 1, prelude forcing, float16), not batching. Answered after Phase 1.

# [x] Phase 0: Commit and push from the Mac, and move to Ubuntu (on the Mac)

Done 2026-09-28. Report: [`08-implementation-phase-0.md`](08-implementation-phase-0.md). The clone on Ubuntu and the data copy are run by the user from the walkthrough; Phase 1 task 1.1.2 checks them.

## [x] Story 0.1: A clean commit
- [x] Task 0.1.1 **The ignore rules**: the `poc-synthesia-frames` rules of the root `.gitignore` now start with `pocs/`, and a new block ignores weights, audio, video and `__pycache__` under `pocs/`. Done 2026-09-28 while writing the plan: `pocs/` adds 167 files and about 13 MB, and `git check-ignore` confirms the video is ignored.
- [x] Task 0.1.2 **The broken paths**: `aitu-backend/tests/test_matrix_peaks.py:266` and the POC scripts and README commands that assumed the POC folders were at the root. Six code paths and 34 documents fixed. The fixed test path revealed one test that was already failing before the move (report section 2.1).
- [x] Task 0.1.3 **The size check**: `git add -A --dry-run`, then the total size of what would be added. Stop if anything over 5 MB is not expected. 211 files, 14.4 MB, largest 0.77 MB.
- [x] Task 0.1.4 **Commit and push** `master`, including the moved `pocs/`, `context/02b-local-setup.md`, the modified communication guide and this folder. Confirm `vexflow-v2` (`plan-resume`) is clean and pushed.

## [x] Story 0.2: The data
- [x] Task 0.2.1 **The manifest**: every gitignored file to copy, with its size, in the phase report (`aitu-backend/data/audio/`, the ignored `pocs/poc-synthesia-frames` outputs, `context/implementations/04-synthesia-to-notes/examples/`).
- [x] Task 0.2.2 **The copy script**: `scripts/migrate/push-data-to-ubuntu.sh <ubuntu-repo-path>`, using `rsync` over the `ubuntu` SSH alias, safe to run twice, and printing a count and a size at the end.

## [x] Story 0.3: The handover to Ubuntu
- [x] Task 0.3.1 **The instructions**: in the walkthrough, the commands to open Cursor on Ubuntu, clone `aimpromptu` and `vexflow-v2` side by side, and run the copy script from the Mac.
- [x] Task 0.3.2 **Ubuntu to Mac access** (optional, recommended): the steps to enable Remote Login on the Mac and authorise the Ubuntu key, and the Mac's LAN address.

# [x] Phase 1: MuScriptor on Ubuntu, and what it outputs (on Ubuntu)

Done 2026-09-28. Report: [`08-implementation-phase-1.md`](08-implementation-phase-1.md). Results: [`../../../pocs/poc-muscriptor/RESULTS.md`](../../../pocs/poc-muscriptor/RESULTS.md).

## [x] Story 1.1: The machine
- [x] Task 1.1.1 **The checks**: `nvidia-smi`, the driver and CUDA versions, Docker, the NVIDIA Container Toolkit, `uv`, Node, `ffmpeg`. Anything missing goes to HUMAN INTERVENTION. Nothing missing; the GPU is seen from a container (`nvidia/cuda:12.9.1-base-ubuntu24.04`).
- [x] Task 1.1.2 **The data**: compare the copied files with the Phase 0 manifest. Identical: 10,626 files, same bytes per folder.
- [x] Task 1.1.3 **The app, natively**: `uv sync` with the extras and `make test` in the backend; `npm install && npm run build` in `vexflow-v2`; `npm install && npm run build` in the frontend. 906 passed, 1 known failure (Phase 0 report 2.1); both builds pass.

## [x] Story 1.2: MuScriptor out of the box
- [x] Task 1.2.1 **Clone and install** beside the project, with `uv sync`. `../muscriptor` at `7f213af`; its tests pass (221 passed, 24 skipped for missing weights); web UI built with pnpm.
- [x] Task 1.2.2 **Hugging Face**: the licence accepted for `muscriptor-large` and `HF_TOKEN` in a gitignored `.env` (human step). The Hugging Face cache on `/mnt/ssd2`. Licences accepted for the three sizes; `HF_TOKEN` is already in `~/.zshrc` (the `.env` for Compose is Phase 3); weights in `HF_HUB_CACHE=/mnt/ssd2/hf/data/hub`.
- [x] Task 1.2.3 **Their tools**: `muscriptor transcribe` on a short file, and `muscriptor serve` opened from the Mac through a tunnel. CLI: 20 s in 5 s. The user opened the web UI through `ssh -N -L 8222:localhost:8222 ubuntu`, transcribed Superestrella and judged it good.

## [x] Story 1.3: The POC `pocs/poc-muscriptor/`
- [x] Task 1.3.1 **The output format**: the first 20 seconds of Superestrella, on CPU and on GPU, raw events saved as they come. Same 102 notes on both; times on a 10 ms grid; no velocity.
- [x] Task 1.3.2 **Speed and memory**: `small`, `medium`, `large`; float32, float16, bfloat16; batch size 1 against larger batches; with and without `torch.compile`. `large` float16 batch 1: 7.8 x real, 3.5 GB, same notes as float32; batch 8: 34 x real, 7% of notes change; compile slower.
- [x] Task 1.3.3 **The lag**: MuScriptor's `onset_delay` against a direct onset detection on the audio. Their `onset_delay` refused all six pieces; the lag changes per piece (+15 to -17 ms against ByteDance) and is measured per piece from the audio envelope.
- [x] Task 1.3.4 **Conditioning**: every run on `acoustic_piano`, and one short check without it to confirm that no piano note is lost. One chunk of Superestrella loses notes, but conditioning agrees more with ByteDance on 5 of 6 whole songs; Q-3 unchanged.
- [x] Task 1.3.5 **The whole song against ByteDance**: counts, onsets that agree within 50 ms, both piano roll visualizations as pictures. Six pieces: 81 to 98% agreement, Superestrella 65% (its ByteDance version is the noisiest).
- [x] Task 1.3.6 **The filters**: `artifacts.py` and `leakage.py` on MuScriptor notes, helpful or harmful. Both off for MuScriptor (no effect, and leakage would merge real repeated notes without velocity).
- [x] Task 1.3.7 **`RESULTS.md`** and the learnings in the phase report, with a recommendation for the model size, the dtype, the batch size, the lag and the filters. Report: [`08-implementation-phase-1.md`](08-implementation-phase-1.md); plan sections 3 and 9.1 updated.

# [ ] Phase 2: The piano matrix notation format

## [ ] Story 2.1: The `pmn` module
- [ ] Task 2.1.1 **The sparse form**: `id`, `key`, `onMs`, `lenMs`, `hand`, as NumPy arrays.
- [ ] Task 2.1.2 **The adapters**: `events.json`, dense matrix (whole and per hand), COO, columns, MIDI, MuScriptor events, portable `.pmn.json`.
- [ ] Task 2.1.3 **Round-trip tests** for every adapter, including the matrix at 10 ms and at 40 ms.

## [ ] Story 2.2: `events.json`
- [ ] Task 2.2.1 **Stable ids**, given once and kept.
- [ ] Task 2.2.2 **The header**: `notesRevision`, `handsRevision`, `engine`, `audioRevision`, `lagCorrectionMs`, with old files read without a change on disk.

## [ ] Story 2.3: Faster payloads
- [ ] Task 2.3.1 **The COO payload** built with NumPy instead of Python loops.
- [ ] Task 2.3.2 **gzip** on responses.
- [ ] Task 2.3.3 **The table**: sizes and build times on all 34 transcribed pieces, before and after.
- [ ] Task 2.3.4 **The specification page**: `context/backend/piano-matrix-notation.md`.

# [ ] Phase 3: Containers, the GPU in the backend, and the tunnel

## [ ] Story 3.1: Configuration
- [ ] Task 3.1.1 **Variables**: `AITU_DATA_DIR`, `AITU_DEVICE`, host and port, with the current behaviour as the default.
- [ ] Task 3.1.2 **`.env.example`** with every name and no value.
- [ ] Task 3.1.3 **The lock file**: `torchaudio` aligned with `torch`.

## [ ] Story 3.2: The containers
- [ ] Task 3.2.1 **Backend Dockerfile**: Python 3.12, `uv`, `ffmpeg`, PyTorch with CUDA, the extras.
- [ ] Task 3.2.2 **Frontend Dockerfile**: Node and Vite with hot reload (development mode, Q-5), `vexflow-v2` through `additional_contexts`.
- [ ] Task 3.2.3 **`compose.yaml`**: GPU reserved, data mounted, Hugging Face cache on `/mnt/ssd2`, `.env`.
- [ ] Task 3.2.4 **Makefile**: `up`, `down`, `logs`, `test-backend`, `shell-backend`.

## [ ] Story 3.3: The GPU
- [ ] Task 3.3.1 **From the container**: `nvidia-smi` and `torch.cuda.is_available()`.
- [ ] Task 3.3.2 **A baseline**: ByteDance on CPU against ByteDance on CUDA, on Superestrella.
- [ ] Task 3.3.3 **All backend tests** pass inside the container.

## [ ] Story 3.4: One port from the Mac
- [ ] Task 3.4.1 **The Vite proxy** for `/api`, and the frontend using a relative base, including the audio files and the SSE stream.
- [ ] Task 3.4.2 **`scripts/tunnel-from-mac.sh`**.
- [ ] Task 3.4.3 **Playwright** on Ubuntu, and one screenshot of the current app taken by the agent.

# [ ] Phase 4: MuScriptor in the backend, and the live stream

## [ ] Story 4.1: The engine
- [ ] Task 4.1.1 **`MuScriptorEngine`** and the `muscriptor` extra, its entry in `engine_installed()`.
- [ ] Task 4.1.2 **Forced**: the default, first in the registry, the only one offered; ByteDance and Transkun kept and tested.
- [ ] Task 4.1.3 **The model registry** and the preload at startup.
- [ ] Task 4.1.4 **One job at a time on the GPU**, with a "waiting" state.
- [ ] Task 4.1.5 **The lag correction and the filters** as Phase 1 decided: `lagCorrectionMs` per piece from the audio envelope, both filters off for MuScriptor; `large`, float16, batch 1, prelude forcing (Q-7).

## [ ] Story 4.2: The selected region
- [ ] Task 4.2.1 **`cuts`** in `metadata.json`, as frame ranges of 10 ms, and `audioRevision`.
- [ ] Task 4.2.2 **The frame table**: from a frame of the piece to a frame of the original audio, one lookup per frame or range.
- [ ] Task 4.2.3 **The joined audio** in memory, with a 5 ms fade at each join and no change in the number of frames.
- [ ] Task 4.2.4 **A cut after a transcription** starts a new transcription, with the old notes in history (Q-2).

## [ ] Story 4.3: The stream
- [ ] Task 4.3.1 **The chunk messages** of the plan's section 9.3 on the progress stream.
- [ ] Task 4.3.2 **Reconnect**: a page that connects late receives what was already sent.
- [ ] Task 4.3.3 **The history copy** of `events.json` and `rhythm.json` before a new transcription.

## [ ] Story 4.4: The two split cache fixes
- [ ] Task 4.4.1 **The job's hand split** kept in the split cache.
- [ ] Task 4.4.2 **`GET /matrix/{uuid}/events`** using the split cache.

## [ ] Story 4.5: Tests
- [ ] Task 4.5.1 **A fake MuScriptor model** for the engine and the stream.
- [ ] Task 4.5.2 **One GPU test**, run only when a GPU is present.

# [ ] Phase 5: The piece API, revisions and the hand split as a step

## [ ] Story 5.1: The endpoints
- [ ] Task 5.1.1 **`GET /pieces/{uuid}/status`**: `missing`, `running`, `ready` or `stale` per step.
- [ ] Task 5.1.2 **`GET /pieces/{uuid}/notes`**: the columns.
- [ ] Task 5.1.3 **`PATCH /pieces/{uuid}/notes`**: the operations, `baseRevision`, 409 on a mismatch, ids for added notes.
- [ ] Task 5.1.4 **`POST /pieces/{uuid}/hands/predict`**: the hand string.

## [ ] Story 5.2: The revisions
- [ ] Task 5.2.1 **The chain** of the plan's section 8.2, and `handsRevision` recorded in `rhythm.json`.
- [ ] Task 5.2.2 **The quick hand rule** for an added note.
- [ ] Task 5.2.3 **Tests** for every row of the table in section 8.3.

## [ ] Story 5.3: The saved hands on the piano sheet
- [ ] Task 5.3.1 **Read the saved hands** when every note has one; the old behaviour otherwise.
- [ ] Task 5.3.2 **The note under D-31** in `decisions.md`.
- [ ] Task 5.3.3 **`PUT /time/{uuid}/hands`** writes the saved hands by note id, without computing the hand split again, and moves `rhythm.json` forward when it was current.

# [ ] Phase 6: The flow page, the Source tab and the Audio tab

## [ ] Story 6.1: The flow page
- [ ] Task 6.1.1 **The route** `/piece/:uuid/<step>`, and `/` going to `/piece/new`.
- [ ] Task 6.1.2 **The five tabs**, enabled from the status endpoint, with the reason in a tooltip.
- [ ] Task 6.1.3 **Opening a piece** at its furthest ready step.
- [ ] Task 6.1.4 **The save bar** and the warning for unsaved changes.

## [ ] Story 6.2: The Source tab
- [ ] Task 6.2.1 **Library, upload, YouTube** in one place.
- [ ] Task 6.2.2 **The YouTube download as a job** with progress.

## [ ] Story 6.3: The Audio tab
- [ ] Task 6.3.1 **The canvas waveform** with zoom and a playhead.
- [ ] Task 6.3.2 **Select, Delete, Restore**, and undo and redo.
- [ ] Task 6.3.3 **Play selection, Play all** (jumping over cuts).
- [ ] Task 6.3.4 **Save and Transcribe**.
- [ ] Task 6.3.5 **The Playground Input page** without its engine choice.

# [ ] Phase 7: The Notes tab: the live piano roll visualization and the editor

## [ ] Story 7.1: The canvas
- [ ] Task 7.1.1 **Typed arrays and the per-key index**.
- [ ] Task 7.1.2 **Painting on the animation frame**, only the visible range, the playhead on its own layer.
- [ ] Task 7.1.3 **The vertical piano keyboard** beside it, lit during playback.

## [ ] Story 7.2: Live
- [ ] Task 7.2.1 **The stream queue** and the growing rectangles.
- [ ] Task 7.2.2 **The progress bar**, smoothed between chunks, with the time taken.
- [ ] Task 7.2.3 **The final replace** with the saved notes.

## [ ] Story 7.3: Playback
- [ ] Task 7.3.1 **The original audio** with the playhead, the scrub bar, double-click to seek, follow.
- [ ] Task 7.3.2 **Cuts** jumped over by the player, using the frame table.

## [ ] Story 7.4: The edit tools
- [ ] Task 7.4.1 **Selection**: click, Command-click, band.
- [ ] Task 7.4.2 **Move and resize**, with 10 ms snap and the same-key overlap rule.
- [ ] Task 7.4.3 **Delete and add**.
- [ ] Task 7.4.4 **Undo and redo** with `useEditHistory`.
- [ ] Task 7.4.5 **Save** as operations.

## [ ] Story 7.5: The measurements
- [ ] Task 7.5.1 **60 frames per second with 10,000 rectangles**.
- [ ] Task 7.5.2 **No dropped frame at 100 chunks per second**.

# [ ] Phase 8: The Hands tab and the Sheet tab

## [ ] Story 8.1: The Hands tab
- [ ] Task 8.1.1 **Predict hands**, and the colours on the rectangles and on the keyboard.
- [ ] Task 8.1.2 **To right hand, To left hand**, `R` and `L`.
- [ ] Task 8.1.3 **The filter**: both, right, left.
- [ ] Task 8.1.4 **The dashed border** for a hand given by the quick rule.
- [ ] Task 8.1.5 **Save and Continue to the sheet**.

## [ ] Story 8.2: The Sheet tab
- [ ] Task 8.2.1 **`RhythmPage` inside the flow page**, otherwise unchanged.
- [ ] Task 8.2.2 **The stale banner** and **Write the sheet** required again.
- [ ] Task 8.2.3 **A hand move on the piano sheet**: measured part by part (request, build, transfer, drawing) against the target of 300 ms for a 3.5-minute piece.

# [ ] Phase 9: The checks, the documentation, and closing

- [ ] Task 9.1 **The whole flow** on Superestrella, a library piece and a new YouTube URL, with timings.
- [ ] Task 9.2 **The documentation**: the engine, the format, the flow page, the containers, the tunnel; `context/02b-local-setup.md` updated.
- [ ] Task 9.3 **Q-4 applied**: the old Piano Roll tab removed, Notes Falling kept.
- [ ] Task 9.4 **The folder README** marked complete, and the row in `../README.md` updated.
