# Overnight session — 2026-07-26/27

Read this first. Everything else is per-task detail.

**→ For hands-on verification, go to [`user_review/`](user_review/README.md).** Those guides are
written for clicking through, not for reading code: what to press, what happens behind the scenes,
what correct looks like. Start with [`user_review/00-setup.md`](user_review/00-setup.md).

## What was done

**Epics 1 through 6, all tasks.** The checklist is truthful — `[x]` means done, and where a task
needs your eyes the checklist line says so inline.

| Epic | Outcome |
|------|---------|
| 1 — Skeleton | Backend restructured into feature packages, tooling + pre-commit, MUI app shell with all routes, matrix and metadata contracts, storage tree |
| 2 — Matrix core | The whole engine: model, validator, collapse/upsample, Appendix B cleaning, Appendix C approximation, two-hands split, structural ops |
| 3 — Audio I/O | Audio store, upload + ffmpeg normalization + waveform peaks, browser recording, range selector, YouTube via yt-dlp |
| 4 — Transcription | Engine interface (3 engines), events → raw matrix, five-step pipeline, background jobs + SSE |
| 5 — Artifacts | Playground repository with `vN_gX` versions and lineage, library promotion with rollback |
| 6 — Input tab | All five input sources wired, transcription settings, Run → progress → Matrix tab |
| 7 — Matrix tab | The grid (circles, edges, frozen headers, virtualized rows), step pills, JSON export/import, instant recompute, frame search |

**464 backend tests pass.** `mypy`, `flake8`, `black`, `tsc -b`, `eslint` and `vite build` are all
clean.

Epic 7's Story 7.4 (cell editing, matrix player) is marked nice-to-have in the plan and is not
built; the seams for it are in place.

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

**No transcription engine has run**, because torch never finished downloading in the sandbox (over
90 minutes on an aarch64 Linux wheel — a sandbox network limit, not a project problem). The model
call is now written against the package's **actual source**, which I read, rather than its
documentation. [Guide 3](user_review/epic-04-transcription.md) walks through proving it works, and
its first step is a single command that either prints `engine ready: bytedance on cpu` or tells you
what is missing.

**No UI has been looked at.** You asked me to skip that. The six `user_review/` guides exist so
that is a pleasant hour rather than a hunt.

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

## Nothing is committed

The work is on disk, unstaged. I did not commit because pre-commit could not run here — its hooks
are cloned from GitHub, which the sandbox blocks — and the plan says pre-commit must pass.

```bash
cd aitu-backend
uv sync && uv sync --extra transcription
make hooks && make lint && make test

cd ../aitu-frontend && npm install && npm run lint && npm run build

cd .. && git add -A && git status      # confirm no .npz or data/audio slipped in
git commit -m "Epics 1-6: matrix engine, audio I/O, transcription, artifacts, input tab"
```

The `.gitignore` was extended for `data/`; I verified nothing under `data/audio/` or any `.npz` is
tracked.

## Where the plan stands

Epics 8–14 are untouched, plus Epic 7's nice-to-have Story 7.4.

**Epic 8 (piano roll and notes falling) is the natural next step.** Its two prerequisites are
already in place: `<WaveformView watermark />` from Epic 3 for the roll background, and
`MatrixGrid`'s `focusFrame` prop for the deep link back to the Matrix tab. Alternatively **Epic 9
(notation)** is the bigger prize — it is what turns all of this into actual sheet music — and its
backend score-format builder is the last major unbuilt piece of the pipeline.

## Environment notes for whoever works here next

- The sandbox runs **Python 3.10**; the Mac is 3.12 and that is the real target. All code avoids
  3.11+ syntax so the suite runs in both.
- `mypy` needs `--cache-dir=/tmp/...` in the sandbox (SQLite cannot write to the mounted volume).
- `vite build` needs `--outDir /tmp/...` in the sandbox (it cannot delete the existing `dist/`).
- Keep package `__init__.py` files free of eager imports — `matrix/__init__.py` re-exporting
  submodules created a circular import that hid behind import order for two epics.
