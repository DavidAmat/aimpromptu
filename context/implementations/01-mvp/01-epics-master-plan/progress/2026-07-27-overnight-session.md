# Overnight session — 2026-07-26/27

Read this first. Everything else is per-task detail.

**→ For hands-on verification, go to [`user_review/`](user_review/README.md).** Those guides are
written for clicking through, not for reading code: what to press, what happens behind the scenes,
what correct looks like. Start with [`user_review/00-setup.md`](user_review/00-setup.md).

## What was done

**Epics 1 through 8, all tasks, across the overnight and continuation sessions.** The checklist is
truthful — `[x]` means done, and where a task needs your eyes the checklist line says so inline.

| Epic | Outcome |
|------|---------|
| 1 — Skeleton | Backend restructured into feature packages, tooling + pre-commit, MUI app shell with all routes, matrix and metadata contracts, storage tree |
| 2 — Matrix core | The whole engine: model, validator, collapse/upsample, Appendix B cleaning, Appendix C approximation, two-hands split, structural ops |
| 3 — Audio I/O | Audio store, upload + ffmpeg normalization + waveform peaks, browser recording, persisted physical segments with source lineage, YouTube via yt-dlp |
| 4 — Transcription | Engine interface (3 engines), real ByteDance model-segment progress, events → raw matrix, five-step pipeline, background jobs + SSE |
| 5 — Artifacts | Playground repository with `vN_gX` versions and lineage, library promotion with rollback |
| 6 — Input tab | All five input sources wired, physical segment creation/back-to-original, transcription settings, monotonic progress, Run → Matrix |
| 7 — Matrix tab | The grid (circles, edges, frozen headers, virtualized rows), explicit segment/full-track context and original times, step pills, JSON export/import, instant recompute, frame search, validator-backed editing, matrix player |
| 8 — Piano views | Reusable 88-key piano, waveform-backed roll, shared transport and synth/original-audio playback, falling-note view, drag editing |

**476 backend tests pass.** The full pinned pre-commit suite, `mypy`, `flake8`, `black`, `tsc -b`,
`eslint` and `vite build` are all clean.

## Second pass — the blockers researched and fixed

The first pass left three things unverified. All three were researched against the actual packages
and fixed; the findings are worth reading because two of them were traps.

### 1. Python 3.12 is correct — no change needed

Verified on PyPI (July 2026): **torch 2.13 ships macOS arm64 wheels for CPython 3.10–3.14**, and
so do numba and llvmlite (librosa's compiled dependencies). The project's existing pin,
`>=3.12.13,<3.13`, is fully supported on Apple Silicon and is the most battle-tested choice.
Nothing was changed.

Also verified: **`piano_transcription_inference` does not pin torch.** It requires matplotlib,
mido, librosa and torchlibrosa, nothing more. The task file's warning about "old pinned torch
versions" was wrong, and `pyproject.toml` now says so.

### 2. The checkpoint download would have failed silently on your Mac ⚠️

Reading the package's own `inference.py`: on first use it downloads its 165 MB model checkpoint
with **`os.system('wget ...')`**. **macOS does not ship `wget`.** That call would have failed
silently, left a zero-byte file, and then died inside `torch.load` with an error mentioning
nothing about a missing download.

**Fixed**: `transcription/engine.py` now downloads the checkpoint itself with the standard library
before constructing the model — with a progress bar, a size check, and a `.partial` file that is
discarded rather than left behind on a truncated download. Four tests cover it.

Also confirmed from the source, rather than assumed:

- `est_note_events` really is a list of `{midi_note, onset_time, offset_time, velocity}` — my
  original parsing was correct.
- `sample_rate` is 16000, matching what the audio store already produces.
- `transcribe(audio, None)` skips the MIDI write, as intended.
- **On Apple Silicon it runs on the CPU whatever you pass.** The package only calls
  `model.to(device)` when the string contains `"cuda"`, and its forward pass reads the device off
  the model's parameters — so `mps` would be accepted and quietly ignored. Documented in the
  docstring rather than papered over.

### 3. Chrome recording — decided, using the standard approach

Researched how recording apps handle this: **the normal answer is to accept webm/opus and convert
server-side with ffmpeg**, rather than polyfilling an encoder in the browser.

We already convert every upload with ffmpeg, so this was one line. `.webm` and `.ogg` are now
accepted formats. **Browser recording now works in Chrome, Safari and Firefox alike.** Verified end
to end in the sandbox: a real opus-encoded webm uploads, normalizes to mono 16 kHz, and reports the
right duration.

### 4. yt-dlp — now robust and actually exercised

It was being invoked as a bare `yt-dlp` on `PATH`, which only exists while the venv is active. Now
it runs as **`python -m yt_dlp` on the backend's own interpreter**, which works however the server
was started. yt-dlp installed cleanly in the sandbox, so that test now really runs instead of
skipping.

## What is still unverified

The real ByteDance engine has now run successfully on the local Mac against an eight-second
synthetic source. Its actual package mini-batch loop is instrumented rather than wrapped with an
invented timer. A longer musical recording is still the useful human quality trial because the
short fixture contains no piano performance and has only one model batch.

**The Epic 7 and Epic 8 UI has been browser-verified** with both an imported five-note scale and
physical audio/segment artifacts. Matrix editing and playback, Piano Roll playback, Falling
playback, drag staging/cancel, key highlighting, deep linking, segment/full-track switching and
original-time labels all worked with no browser-console errors. Musical A/B judgment against a
real performance remains the supervisor trial.

The remaining real-device and real-audio checks are collected in the `user_review/` guides. In
particular, use [guide 6](user_review/epic-08-piano-views.md) for the piano views.

## Continuation — Epic 7 finish and Epic 8

### Matrix editing and player

Story 7.4 is now complete. Edits are staged in the browser but every preview and save is rebuilt
and validated by the backend. A save keeps the original raw fusa matrix once as
`raw_before_edit.npz`, expands the edited clean matrix back to raw resolution, and persists the
derived result. The matrix player uses the same shared clock and piano fallback as Epic 8, so the
cursor, sounding cells and highlighted piano keys stay aligned.

### Piano views and playback

Epic 8 now has one 88-key piano component in horizontal and vertical orientations, generated key
geometry for MIDI 21–108, a waveform-watermarked Piano Roll, and an eight-beat windowed Falling
view. Playback can follow the normalized source audio when one exists or use a WebAudio piano-like
fallback; speed, range, BPM and granularity controls are shared. Both animated views support
staged pointer-drag correction with validator-backed Save and Cancel.

The checked-in piano SVGs are deliberate programmatic placeholders, as allowed by Task 8.1.1.
They can be replaced later without changing the key geometry or page components.

### Saved audio segments, time context and progress

A partial Input selection is now materialized before transcription. The backend creates a named,
physically trimmed audio item with a truncated waveform and root-source start/end metadata.
Re-trimming a segment retains absolute root times. Input offers **Back to original**, and every Run
forces a fresh transcription of the currently selected physical file, so a previous segment can
never reappear after choosing the full track.

Matrix visibly distinguishes **SEGMENT** from **ENTIRE TRACK**. Segment rows show both local time
and their corresponding original-source time.

The browser progress bar now maps every pipeline stage monotonically across one whole-job scale.
ByteDance reports each real model segment, fixing the old mismatch where terminal inference
advanced while the UI stayed at zero.

### Piano compositing correction

The keyboard uses four SVG layers: white base, pressed white keys, normal black keys, then pressed
black keys. This prevents a white highlight rectangle from covering neighbouring black keys.
Live browser inspection confirmed that ordering during playback.

Imported matrix JSON deliberately has no audio waveform. That optional request now returns a clean
`404` for the views' built-in fallback instead of logging a server exception.

### Runtime defect found

React development mode deliberately issued duplicate matrix requests. Both backend requests used
to write the same `.npz` archive directly, allowing one request to observe a half-written zip and
fail with `BadZipFile`. Matrix persistence now writes a sibling temporary archive and atomically
replaces the target. A regression test verifies the temporary file is cleaned up and the final
archive remains readable.

## The ligature decision — resolved

**The adjacency rule is binding.** Non-adjacent ties are never generated, and the algorithm is now
simply: *list the durations that can be written legally, and pick the one closest to what was
played.* Legal = a single figure, or two **adjacent** figures tied (a dotted note).

So 1.23 s at 60 BPM / semicorchea becomes a plain **negra** (1.00 s, 0.23 s away) rather than a
dotted negra (1.50 s, 0.27 s away). `negra + semicorchea` would have been nearer at 1.25 s, but
skips corchea and is never a candidate — which is the entire point of the rule.

The task file's acceptance criterion was corrected accordingly (its old expected answer *was* the
contradiction), and the rule is documented at three levels: the module docstring, the plan task
file, and [guide 5 §5.4](user_review/epic-02-matrix-core.md). Full write-up:
[`epic-02/task-2.3.2-followup-adjacency-rule.md`](epic-02/task-2.3.2-followup-adjacency-rule.md).

**No decisions are outstanding.**

## Delivery

The completed Epic 1–8 state, including the final segment/progress/piano corrections, is committed
to `master` and pushed after the full pinned pre-commit suite passed. The `.gitignore` excludes
runtime `data/`; no generated audio, matrices or model files are part of the commit.

## Where the plan stands

**Epics 1–8 are complete. Epics 9–14 are untouched.** This continuation explicitly stopped at the
Epic 8 boundary; no Epic 9 task was started.

## Environment notes for whoever works here next

- The sandbox runs **Python 3.10**; the Mac is 3.12 and that is the real target. All code avoids
  3.11+ syntax so the suite runs in both.
- `mypy` needs `--cache-dir=/tmp/...` in the sandbox (SQLite cannot write to the mounted volume).
- `vite build` needs `--outDir /tmp/...` in the sandbox (it cannot delete the existing `dist/`).
- Keep package `__init__.py` files free of eager imports — `matrix/__init__.py` re-exporting
  submodules created a circular import that hid behind import order for two epics.
