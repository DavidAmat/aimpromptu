# Task 4.1.1 — follow-up: engine, formats and yt-dlp verified against reality

Date: 2026-07-27, second pass. Supersedes the "unverified" caveats in
[`task-4.1.1-progress.md`](task-4.1.1-progress.md).

The first pass wrote the model integration from documentation and flagged it as unproven. This pass
read the packages' **actual source** and checked PyPI directly. Three findings, one of them a trap
that would have cost an afternoon.

---

## 1. Python 3.12 is right. No change.

Checked PyPI (July 2026):

| Package | Latest | macOS arm64 CPython tags |
|---------|--------|--------------------------|
| `torch` | 2.13.0 | cp310, cp311, cp312, cp313, cp314 |
| `numba` | 0.66.0 | cp311 … cp314 |
| `llvmlite` | 0.48.0 | cp311 … cp314 |
| `librosa`, `mido`, `torchlibrosa`, `piano_transcription_inference`, `yt-dlp` | — | pure Python |

**The project's `>=3.12.13,<3.13` pin is fully supported on Apple Silicon** and is the
most conservative of the working choices. Nothing changed.

**And `piano_transcription_inference` does not pin torch.** Its actual requirements are
`matplotlib, mido, librosa, torchlibrosa` — nothing more. The task file's warning that it "pins old
torch versions" (which drove the whole "isolate it in a separate venv" contingency) is simply not
true of version 0.0.6. `pyproject.toml` now records that, so nobody re-derives it.

---

## 2. ⚠️ The checkpoint download would have failed silently on macOS

From the package's own `inference.py`:

```python
if not os.path.exists(checkpoint_path) or os.path.getsize(checkpoint_path) < 1.6e8:
    create_folder(os.path.dirname(checkpoint_path))
    os.system('wget -O "{}" "{}"'.format(checkpoint_path, zenodo_path))
```

**macOS does not ship `wget`.** `os.system` ignores the exit code, so on David's Mac this would
have: printed a `command not found`, created an empty file, and then died three lines later inside
`torch.load` with an error mentioning nothing about a download. That is exactly the class of
failure that looks like "the model is broken".

**Fix** — `transcription/engine.py` gains:

| Name | Role |
|------|------|
| `checkpoint_path()` | mirrors the package's hardcoded location |
| `checkpoint_present()` | path exists **and** is at least 160 MB |
| `download_checkpoint(reporter)` | fetches it with `urllib`, reports progress, writes to `.partial`, size-checks, then renames |

`ByteDanceEngine.__init__` calls it before constructing the model, and passes the resolved path
explicitly so the package's own download branch never fires. A truncated download is deleted rather
than left to be mistaken for a valid one.

Four tests cover it: the path matches what the package looks for, an existing checkpoint is not
re-fetched, a truncated download raises and leaves nothing behind, and a good one is moved into
place with progress events.

---

## 3. The rest of the model integration was correct

Verified by reading `inference.py` and `utilities.py` rather than assuming:

| Claim | Verdict |
|-------|---------|
| `transcribe()` returns `est_note_events` | ✅ alongside `output_dict` and `est_pedal_events` |
| Each event is `{midi_note, onset_time, offset_time, velocity}` | ✅ exactly, from `RegressionPostProcessor` |
| `sample_rate` is 16000 | ✅ — the same rate the audio store already normalizes to |
| `transcribe(audio, None)` skips the MIDI write | ✅ guarded by `if midi_path:` |
| A device string (not a `torch.device`) is accepted | ✅ used only via `str(device)` and `map_location` |

**One thing that is not what it looks like**: the `device` parameter does **not** move the model to
an Apple GPU. The package only calls `model.to(device)` when the string contains `"cuda"`, and
`forward()` reads the device off the model's parameters — so passing `"mps"` is accepted and then
ignored. On Apple Silicon this runs on the **CPU**, which is fast enough for piano-length clips.
The docstring now says so instead of implying otherwise.

`available_engines()` was also rewritten: it used to *construct* each engine to test availability,
which for ByteDance means loading a 165 MB checkpoint into memory on every call to
`GET /matrix/engines`. It now checks whether the module is importable. A test asserts that probing
never constructs an engine.

---

## 4. Browser recording: webm/opus accepted (Chrome resolved)

Researched how recording apps handle Chrome's MediaRecorder, which produces only webm/opus: the
standard answer is **accept it and convert server-side with ffmpeg**, not polyfill an encoder in
the browser.

We already convert every upload with ffmpeg, so this was one line.

- `formats.SUPPORTED_SUFFIXES` += `.webm`, `.ogg`; media types added.
- `useRecorder.fileNameFor` maps those containers to honest suffixes, and names the file after the
  container the browser **actually produced** (`blob.type`) rather than what was requested.
- The "your browser can't record a format we accept" dead end is gone.

**Verified end to end in the sandbox**: a real opus-encoded webm posts to `/audio/recording`, comes
back `201`, normalizes to mono 16 kHz, and reports the right duration. Test:
`test_a_chrome_style_webm_recording_is_ingested`.

---

## 5. yt-dlp: no longer depends on PATH

It was invoked as a bare `yt-dlp`, which only exists on `PATH` while the venv is active. Now it
runs as **`[sys.executable, "-m", "yt_dlp"]`** — the backend's own interpreter, so it works however
the server was started. `yt_dlp_available()` checks the module is importable rather than probing
`PATH`.

yt-dlp installs cleanly (pure Python, one second), so its test now actually runs the binary instead
of skipping.

Also improved: the "produced no mp3" error now names ffmpeg and the brew command, since that is
what `-x --audio-format mp3` actually needs.

---

## Verification

```
pytest        # 449 passed (up from 439; 10 new)
mypy, flake8, black, tsc -b, eslint, vite build   # all clean
```

---

## Still needing the Mac

The model has still never produced a note — torch would not finish downloading in the sandbox (an
aarch64 Linux wheel, over 90 minutes). But the integration is now written against source I read
rather than docs I trusted, and the one genuine trap is removed.

[`user_review/epic-04-transcription.md`](../user_review/epic-04-transcription.md) is the guide.
Its first step is one command that either prints `engine ready: bytedance on cpu` or says what is
missing.
