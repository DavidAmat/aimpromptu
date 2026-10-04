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

# [x] Phase 2: The piano matrix notation format

Done 2026-09-28. Report: [`08-implementation-phase-2.md`](08-implementation-phase-2.md). Specification: [`../../backend/piano-matrix-notation.md`](../../backend/piano-matrix-notation.md).

## [x] Story 2.1: The `pmn` module
- [x] Task 2.1.1 **The sparse form**: `id`, `key`, `onMs`, `lenMs`, `hand`, as NumPy arrays. `pmn/notes.py`; times are float ms in memory (0.1 ms of the old pieces kept), plus `velocity` and `removed`.
- [x] Task 2.1.2 **The adapters**: `events.json`, dense matrix (whole and per hand), COO, columns, MIDI, MuScriptor events, portable `.pmn.json`. One module each under `pmn/`; `mido` added to the base dependencies.
- [x] Task 2.1.3 **Round-trip tests** for every adapter, including the matrix at 10 ms and at 40 ms. `tests/test_pmn.py`, 33 tests, including every `events.json` of the library.

## [x] Story 2.2: `events.json`
- [x] Task 2.2.1 **Stable ids**, given once and kept. `0..n-1` in file order for an old file; `nextId` for new notes; never reused.
- [x] Task 2.2.2 **The header**: `notesRevision`, `handsRevision`, `engine`, `audioRevision`, `lagCorrectionMs`, with old files read without a change on disk. Schema `1.1`, plus `nextId`; no revision is bumped yet (Phase 5).

## [x] Story 2.3: Faster payloads
- [x] Task 2.3.1 **The COO payload** built with NumPy instead of Python loops. Also: the cell check vectorised and no longer run 4 times per request, no second FastAPI validation, no `events.json` read per request. Same answers on all 34 pieces.
- [x] Task 2.3.2 **gzip** on responses. JSON only, level 5; audio and SSE untouched.
- [x] Task 2.3.3 **The table**: sizes and build times on all 34 transcribed pieces, before and after. Warm sheet request 24 to 19 ms median, sent at 56 KB instead of 634 KB; the first request (hand split) is still 0.56 s median.
- [x] Task 2.3.4 **The specification page**: `context/backend/piano-matrix-notation.md`.

# [x] Phase 3: Containers, the GPU in the backend, and the tunnel

Done 2026-09-28. Report: [`08-implementation-phase-3.md`](08-implementation-phase-3.md). Measurements: [`measurements/phase-3-device.json`](measurements/phase-3-device.json).

## [x] Story 3.1: Configuration
- [x] Task 3.1.1 **Variables**: `AITU_DATA_DIR`, `AITU_DEVICE`, host and port, with the current behaviour as the default. `aitu_backend/config.py` (`AITU_HOST`, `AITU_PORT`); `AITU_DEVICE` accepts `cpu`, `cuda`, `auto`; `tests/conftest.py` keeps `AITU_DATA_DIR` out of the tests; `tests/test_config.py`, 6 tests.
- [x] Task 3.1.2 **`.env.example`** with every name and no value. At the repository root; `/.env` is now ignored by git.
- [x] Task 3.1.3 **The lock file**: `torchaudio` aligned with `torch`. Nothing to change: 2.11 is the newest `torchaudio`, unpinned and built on the stable `abi3` interface; checked on the GPU. The lock now also holds the `muscriptor` extra (fastapi 0.141, uvicorn 0.54) and is resolved for Linux and Apple Silicon only.

## [x] Story 3.2: The containers
- [x] Task 3.2.1 **Backend Dockerfile**: Python 3.12, `uv`, `ffmpeg`, PyTorch with CUDA, the extras. Python 3.12.14, uv 0.11.3, ffmpeg, deno (for yt-dlp); `transcription`, `transkun`, `muscriptor` and the dev tools; runs as the host user; 10.4 GB.
- [x] Task 3.2.2 **Frontend Dockerfile**: Node and Vite with hot reload (development mode, Q-5), `vexflow-v2` through `additional_contexts`. Node 22; `vexflow-v2` built at `/work/vexflow-v2` so the `file:` link resolves unchanged.
- [x] Task 3.2.3 **`compose.yaml`**: GPU reserved, data mounted, Hugging Face cache on `/mnt/ssd2`, `.env`. The whole repository is mounted (plan section 10.3); ports published on 127.0.0.1 only.
- [x] Task 3.2.4 **Makefile**: `up`, `down`, `logs`, `test-backend`, `shell-backend`. Plus `ps` and `build`; the native `logs` is now `logs-native`.

## [x] Story 3.3: The GPU
- [x] Task 3.3.1 **From the container**: `nvidia-smi` and `torch.cuda.is_available()`. RTX 4090 seen, driver 595.58.03, torch 2.13.0+cu130, `AITU_DEVICE` resolves to `cuda`.
- [x] Task 3.3.2 **A baseline**: ByteDance on CPU against ByteDance on CUDA, on Superestrella. 53.6 s against 4.6 s (3.5 against 41 x real); 1,338 of 1,343 notes within 1 ms. MuScriptor `large` in the container: 25.3 s, 7.5 x real, 3.5 GB, the same 1,351 notes as the Phase 1 native run. Script `aitu-backend/scripts/bench_device.py`.
- [x] Task 3.3.3 **All backend tests** pass inside the container. `make test-backend`: 951 passed, 1 failed (the known one, Phase 0 report 2.1), the same as natively.

## [x] Story 3.4: One port from the Mac
- [x] Task 3.4.1 **The Vite proxy** for `/api`, and the frontend using a relative base, including the audio files and the SSE stream. Checked through 5173: JSON, gzip (45 KB instead of 612 KB), audio range answers (206), the progress stream; a 502 from the proxy reads as "Could not reach the backend".
- [x] Task 3.4.2 **`scripts/tunnel-from-mac.sh`**.
- [x] Task 3.4.3 **Playwright** on Ubuntu, and one screenshot of the current app taken by the agent. `npm run screenshot -- <path> [--piece <uuid>]` (`aitu-frontend/scripts/screenshot.mjs`), Chromium headless shell in `~/.cache/ms-playwright`; the piano sheet of `b99bc3ae` drawn with no console error.

# [x] Phase 4: MuScriptor in the backend, and the live stream

Done 2026-09-29 (code 2026-09-28). Report: [`08-implementation-phase-4.md`](08-implementation-phase-4.md). Measurements: [`measurements/phase-4-stream.json`](measurements/phase-4-stream.json). The container test run of 2026-09-28 crashed because of the processor; after the BIOS update of 2026-09-29 it passes (report section 4).

## [x] Story 4.1: The engine
- [x] Task 4.1.1 **`MuScriptorEngine`** and the `muscriptor` extra, its entry in `engine_installed()`. The extra itself was added in Phase 3 (the image needed it). `run_signal` takes the samples of the piece; `librosa` added to the extra.
- [x] Task 4.1.2 **Forced**: the default, first in the registry, the only one offered; ByteDance and Transkun kept and tested. `/matrix/engines` lists only `muscriptor`; the route refuses the others with 422.
- [x] Task 4.1.3 **The model registry** and the preload at startup. `transcription/models.py`; `AITU_PRELOAD_ENGINE=muscriptor-large` in `compose.yaml`; `GET /matrix/engine`.
- [x] Task 4.1.4 **One job at a time on the GPU**, with a "waiting" state. Plus: a second request for the same piece returns the running job.
- [x] Task 4.1.5 **The lag correction and the filters** as Phase 1 decided: `lagCorrectionMs` per piece from the audio envelope, both filters off for MuScriptor; `large`, float16, batch 1, prelude forcing (Q-7). +15 ms on Superestrella; no correction below 200 distinct onsets (report 2.2).

## [x] Story 4.2: The selected region
- [x] Task 4.2.1 **`cuts`** in `metadata.json`, as frame ranges of 10 ms, and `audioRevision`. `GET` and `PUT /audio/{uuid}/cuts`.
- [x] Task 4.2.2 **The frame table**: from a frame of the piece to a frame of the original audio, one lookup per frame or range. `audio/frames.py`.
- [x] Task 4.2.3 **The joined audio** in memory, with a 5 ms fade at each join and no change in the number of frames. Checked on Superestrella with a 5 s cut: no false note at the join.
- [x] Task 4.2.4 **A cut after a transcription** starts a new transcription, with the old notes in history (Q-2). The notes become stale; the next request transcribes again.

## [x] Story 4.3: The stream
- [x] Task 4.3.1 **The chunk messages** of the plan's section 9.3 on the progress stream. Plus messages inside a chunk every 0.25 s at most, and a final one (report 2.3).
- [x] Task 4.3.2 **Reconnect**: a page that connects late receives what was already sent. Numbered frames, `Last-Event-ID`, `GET /matrix/{uuid}/job`.
- [x] Task 4.3.3 **The history copy** of `events.json` and `rhythm.json` before a new transcription.

## [x] Story 4.4: The two split cache fixes
- [x] Task 4.4.1 **The job's hand split** kept in the split cache. Warmed on a thread after the save: 27 ms for the sheet 2 s after `done`, against 714 ms not warmed.
- [x] Task 4.4.2 **`GET /matrix/{uuid}/events`** using the split cache.

## [x] Story 4.5: Tests
- [x] Task 4.5.1 **A fake MuScriptor model** for the engine and the stream. `tests/test_muscriptor_engine.py`, `tests/test_audio_frames.py`, `tests/test_jobs.py`: 45 new tests, all pass natively.
- [x] Task 4.5.2 **One GPU test**, run only when a GPU is present. Passes natively (3.5 s) and in the container. `make test-backend` on 2026-09-29: 996 passed, 1 failed (the known one, Phase 0 report 2.1), no crash.

# [x] Phase 5: The piece API, revisions and the hand split as a step

Done 2026-09-29. Report: [`08-implementation-phase-5.md`](08-implementation-phase-5.md). Measurements: [`measurements/phase-5-saved-hands.json`](measurements/phase-5-saved-hands.json), [`measurements/phase-5-pieces.json`](measurements/phase-5-pieces.json).

## [x] Story 5.1: The endpoints
- [x] Task 5.1.1 **`GET /pieces/{uuid}/status`**: `missing`, `running`, `ready` or `stale` per step. Plus `enabled`, `reason` and `details` per step, `resume` (the step a piece opens on) and every revision; `pieces/status.py`.
- [x] Task 5.1.2 **`GET /pieces/{uuid}/notes`**: the columns. Plus `stale` and `guessed`; 4 ms, 11 KB sent for Superestrella.
- [x] Task 5.1.3 **`PATCH /pieces/{uuid}/notes`**: the operations, `baseRevision`, 409 on a mismatch, ids for added notes. Operations `move` (optional `key`), `delete`, `restore`, `add`, `hand`; optional `baseHandsRevision`; 422 with the reason, nothing written; the same-key rule; `pieces/edits.py`.
- [x] Task 5.1.4 **`POST /pieces/{uuid}/hands/predict`**: the hand string. Writes nothing; `replace` to predict the hands the user set as well; 1.2 to 1.5 s the first time, 9 ms again (cached).

## [x] Story 5.2: The revisions
- [x] Task 5.2.1 **The chain** of the plan's section 8.2, and `handsRevision` recorded in `rhythm.json`. `pipeline.save_edit` for every writer; new header field `handsNotesRevision`; the reading stamped by the backend on save.
- [x] Task 5.2.2 **The quick hand rule** for an added note. The closest pitch among the notes around it (1 s), marked `handGuessed`; `transcription/saved_hands.py`.
- [x] Task 5.2.3 **Tests** for every row of the table in section 8.3. `tests/test_pieces.py`, 30 tests; two rows differ from the plan on purpose (report section 2.2).

## [x] Story 5.3: The saved hands on the piano sheet
- [x] Task 5.3.1 **Read the saved hands** when every note has one; the old behaviour otherwise. The same cells as the inference on all 34 pieces, 17 ms against 670 ms (median).
- [x] Task 5.3.2 **The note under D-31** in `decisions.md`.
- [x] Task 5.3.3 **`PUT /time/{uuid}/hands`** writes the saved hands by note id, without computing the hand split again, and moves `rhythm.json` forward when it was current. 8 to 12 ms, then 33 to 36 ms for the sheet (Superestrella); the first move on an old piece saves every hand as drawn.

# [x] Phase 6: The flow page, the Source tab and the Audio tab

Done 2026-09-29. Report: [`08-implementation-phase-6.md`](08-implementation-phase-6.md). Checked in a headless Chromium on a temporary copy of Superestrella (report section 3); the user's own check in the browser is the walkthrough's HUMAN INTERVENTION.

## [x] Story 6.1: The flow page
- [x] Task 6.1.1 **The route** `/piece/:uuid/<step>`, and `/` going to `/piece/new`. Also `/piece` (the **Piece** entry of the top bar, first) opens the working piece; the app moved to a data router so a navigation can be blocked.
- [x] Task 6.1.2 **The five tabs**, enabled from the status endpoint, with the reason in a tooltip. A state icon per tab (ready, running, stale, missing); a tab that is not enabled in the address goes to the resume step.
- [x] Task 6.1.3 **Opening a piece** at its furthest ready step. `/piece/<uuid>` follows `resume`: `b99bc3ae` opens on Sheet, `a585f9eb` on Notes, a new audio on Audio.
- [x] Task 6.1.4 **The save bar** and the warning for unsaved changes. Save or discard asked on any in-app navigation (tabs, top bar, back button), the browser's warning on closing.

## [x] Story 6.2: The Source tab
- [x] Task 6.2.1 **Library, upload, YouTube** in one place. The library opens a piece where it was left; an upload or a download opens on the Audio tab.
- [x] Task 6.2.2 **The YouTube download as a job** with progress. `POST /youtube/jobs`, followed on `GET /matrix/progress/{jobId}` (stages `download`, `store`); 2.5 s for a 19 s video, click to Audio tab.

## [x] Story 6.3: The Audio tab
- [x] Task 6.3.1 **The canvas waveform** with zoom and a playhead. New `GET /audio/{uuid}/frames/peaks` (one min/max pair per 10 ms frame, 35 KB sent for Superestrella, 8 to 30 ms); zoom down to single frames; an overview strip.
- [x] Task 6.3.2 **Select, Delete, Restore**, and undo and redo. Snapped to 10 ms frames; edges with grips, the playhead moved only in the time ruler or by a double-click (report 2.4, after the user's first check); `src/audio/cuts.ts` follows the backend's `normalize_cuts`; `npm run check:cuts`.
- [x] Task 6.3.3 **Play selection, Play all** (jumping over cuts). Checked: 1.8 s played from 1 s before a 19 s cut stopped 0.73 s after its end.
- [x] Task 6.3.4 **Save and Transcribe**. Transcribe saves first, asks before replacing current notes, and opens the Notes tab, which follows the job (Notes, Hands and Sheet are placeholders until Phases 7 and 8).
- [x] Task 6.3.5 **The Playground Input page** without its engine choice.
- [x] After the user's check: **the edited audio is the audio of the piece** once cuts are saved (the original kept hidden, for the Audio tab only), and the piano roll's note panel (Spanish title, no text, To left hand / To right hand). Report section 2.8.

# [x] Phase 7: The Notes tab: the live piano roll visualization and the editor

Done 2026-09-30. Report: [`08-implementation-phase-7.md`](08-implementation-phase-7.md). Measurements: [`measurements/phase-7-roll.json`](measurements/phase-7-roll.json). Checked in a headless Chromium (`check:flow`, 52 checks); the user's own check in the browser is the walkthrough's HUMAN INTERVENTION.

## [x] Story 7.1: The canvas
- [x] Task 7.1.1 **Typed arrays and the per-key index**. `src/notes/rollNotes.ts`: one array per field, an index by onset (range query) and one by key (hit test, same-key neighbours).
- [x] Task 7.1.2 **Painting on the animation frame**, only the visible range, the playhead on its own layer. `PianoRollCanvas.tsx`, `rollPaint.ts`; one loop that runs only while something moves, one frame asked at a time (report 2.7).
- [x] Task 7.1.3 **The vertical piano keyboard** beside it, lit during playback. Drawn on the canvas, one row per key, rows fitted to the keys the piece uses (report 2.1).

## [x] Story 7.2: Live
- [x] Task 7.2.1 **The stream queue** and the growing rectangles. `liveFeed.ts`, `useLiveTranscription.ts`; drawn up to the smoothed frontier, 250 ms reveal; a reload receives everything sent so far.
- [x] Task 7.2.2 **The progress bar**, smoothed between chunks, with the time taken. `RollTimeBar.tsx`; notes, time elapsed and left; "Transcribed in 0:25" afterwards, on the backend's clock.
- [x] Task 7.2.3 **The final replace** with the saved notes. Same ids, in place; the view stays.

## [x] Story 7.3: Playback
- [x] Task 7.3.1 **The original audio** with the playhead, the scrub bar, double-click to seek, follow. The playhead moves in the time ruler and on the bar under the roll; the double-click adds a note (report 2.3).
- [x] Task 7.3.2 **Cuts** jumped over by the player, using the frame table. Not needed since the Phase 6 change: the file of the piece is the edited audio, in the time of the notes.

## [x] Story 7.4: The edit tools
- [x] Task 7.4.1 **Selection**: click, Command-click, band. Also Command-A and Escape.
- [x] Task 7.4.2 **Move and resize**, with 10 ms snap and the same-key overlap rule. Also Shift-drag to another key and the arrow keys; moves by 10 ms steps from where the note was (report 2.4).
- [x] Task 7.4.3 **Delete and add**.
- [x] Task 7.4.4 **Undo and redo** with `useEditHistory`. Named steps; undo works after a save too.
- [x] Task 7.4.5 **Save** as operations. `noteEdits.toOperations`; 409 offers **Reload the notes**; `npm run check:notes`.

## [x] Story 7.5: The measurements
- [x] Task 7.5.1 **60 frames per second with 10,000 rectangles**. 60 fps and 0 dropped frames, also with all 10,000 in view (2.7 ms per frame); `npm run bench:roll`.
- [x] Task 7.5.2 **No dropped frame at 100 chunks per second**. 0 of 360, also at 200 per second.

# [x] Phase 8: The Hands tab and the Sheet tab

Done 2026-10-01. Report: [`08-implementation-phase-8.md`](08-implementation-phase-8.md) (Story 8.2); Story 8.1 was done early, after the user's check of Phase 7: [`08-implementation-phase-7.md`](08-implementation-phase-7.md) sections 6 to 8. Measurements: [`measurements/phase-8-sheet-hand.json`](measurements/phase-8-sheet-hand.json). Checked in a headless Chromium (`check:flow`, 79 checks), and by the user in the browser on 2026-10-01 (the zoomed hand move included).

## [x] Story 8.1: The Hands tab
- [x] Task 8.1.1 **Predict hands**, and the colours on the rectangles and on the keyboard. A job with a real progress bar (`POST /pieces/{uuid}/hands/predict/job`, the hand inference reports its progress); the answer is unsaved until Save; unplaced notes stay red.
- [x] Task 8.1.2 **To right hand, To left hand**, `R` and `L`.
- [x] Task 8.1.3 **The filter**: both, right, left. The other hand faint and not pickable.
- [x] Task 8.1.4 **The dashed border** for a hand given by the quick rule. Painted for `guessed` notes while nobody changed their hand.
- [x] Task 8.1.5 **Save and Continue to the sheet**.

## [x] Story 8.2: The Sheet tab
- [x] Task 8.2.1 **`RhythmPage` inside the flow page**, otherwise unchanged. `pages/piece/SheetTab.tsx`; `RhythmPage` takes an optional `step` (the piece and the Sheet step's state from the flow page); no page title; the tab's tick follows a save and **Remove all**. `LaterStepTab` deleted.
- [x] Task 8.2.2 **The stale banner** and **Write the sheet** required again. A stale reading is loaded but not drawn; **Save** appears only after **Write the sheet**; a piece with no reading shows the backend's reason.
- [x] Task 8.2.3 **A hand move on the piano sheet**: measured part by part (request, build, transfer, drawing) against the target of 300 ms for a 3.5-minute piece. `npm run bench:sheet`: 438 to 252 ms on Elefants (3:53), 507 to 272 ms on the Superestrella tutorial; 599 ms on the largest piece (4,295 notes), where the drawing package is the largest part (report 3.3). Fixed on the way: 5 full redraws per move to 1, a deep copy in the sheet request with decorative notes removed (88 to 50 ms), the press render blocking the sheet request (`startTransition`). After the user's check (report section 6): a hand move on a zoomed sheet crashed the page (width read as 0), fixed; the octave bracket bug fixed in `vexflow-v2` (decision: option 3, no change to how it draws).

# [x] Phase 9: The checks, the documentation, and closing

Done 2026-10-01. Report: [`08-implementation-phase-9.md`](08-implementation-phase-9.md). Measurements: [`measurements/phase-9-flow.json`](measurements/phase-9-flow.json). `check:flow` 79 of 79; `make test-backend` 1,039 passed, 1 failed (the known one).

- [x] Task 9.1 **The whole flow** on Superestrella, a library piece and a new YouTube URL, with timings. `npm run time:flow`, all on temporary pieces: 33 s (Superestrella, 3:09), 60 s (a copy of The Winner Takes It All, 5:56, opened from the library and transcribed again), 31 s (a new YouTube URL, 2:21; download 3.8 s). First note 0.2 to 0.35 s, Predict hands 0.9 to 2.4 s, first piano sheet 0.55 to 1.0 s; the transcription is about 85% of the walk.
- [x] Task 9.2 **The documentation**: the engine, the format, the flow page, the containers, the tunnel; `context/02b-local-setup.md` updated. New `context/backend/muscriptor.md`, `context/backend/pieces-and-revisions.md`, `context/frontend/flow-page.md`; `04-local-development.md` rewritten; `02b-local-setup.md` section 12; the platform pages, the `documentation/` detail pages, the index and the three READMEs updated.
- [x] Task 9.3 **Q-4 applied**: the old Piano Roll tab removed, Notes Falling kept. The page and its two components deleted; `/playground/piano-roll` redirects to `/piece`; the Video to Notes links open the Notes tab.
- [x] Task 9.4 **The folder README** marked complete, and the row in `../README.md` updated.
