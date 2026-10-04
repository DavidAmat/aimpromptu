# Task 3.2.1 — Upload endpoint and formats · progress report

Status: **done**. Date: 2026-07-27. Built together with Task 3.1.1 — the two share one ingest path.

## Summary

`audio/formats.py` + `audio/ingest.py` + the upload half of `api/audio.py`.

### Upload

`POST /audio/upload` (multipart: `file`, optional `alias`) -> `201` with the audio metadata.
Format comes from the **filename suffix**: `.mp3`, `.aac`, `.m4a`, `.wav`. Anything else is a
`422` naming the supported set. `POST /audio/recording` is the same route with a different
`source`, so a browser capture and an upload cannot diverge.

`alias` defaults to the filename stem — almost always what the user meant — and stays editable.

### Normalization

`normalize_to_wav()` shells out to `ffmpeg` (subprocess, not a binding: one less wheel to build,
and the exact command shows up in logs):

```
ffmpeg -nostdin -y -i <original> -ac 1 -ar 16000 -acodec pcm_s16le normalized.wav
```

Mono 16 kHz is what `piano_transcription_inference` expects (Epic 4). **Both files are kept**:
the original because the user recognizes it, the normalized WAV because everything downstream —
transcription, waveform, range playback — reads only that. Normalizing once on ingest means no
later step has to care that the upload was an m4a.

`durationSeconds` and `sampleRate` are computed here and written into the metadata.

Failure handling: `FfmpegMissing` -> `503` with the `brew install ffmpeg` instruction;
`ConversionFailed` -> `422` with the last five lines of ffmpeg's stderr. In both cases
**the uuid folder is deleted before the error propagates** — a half-ingested audio in the library
is worse than a failed upload, and a test pins it.

### Waveform peaks

`GET /audio/{uuid}/waveform?points=N` -> `{points, min[], max[], durationSeconds, sampleRate}`,
cached as `waveform.json` next to the audio.

Computed with numpy over the normalized WAV: the samples are padded to a multiple of `points` and
reshaped, so it is two array reductions rather than a Python loop over buckets. Asking for more
buckets than there are samples returns one bucket per sample rather than padding with silence.

**The cache is only reused when it holds the requested number of points** — otherwise the endpoint
would hand back the wrong resolution, which is the kind of bug that looks like a rendering
problem for a week. `?refresh=true` forces recomputation.

`points` is bounded `1..20000` at the route, so a typo cannot ask for a million buckets.

The frontend never decodes audio to draw, as the task requires.

Also added: `slice_wav(source, target, start, end)`, which Story 3.4's range playback and Epic 6's
"transcribe only this range" both need.

## Errors found and how they were solved

Covered in the Task 3.1.1 report (the circular import and the `copyfileobj` typing) — the two
tasks were implemented in one pass. Specific to this task:

- **`scipy.io.wavfile` returns integer samples of varying width.** `read_wav` normalizes to
  `float32` in `[-1, 1]` by dividing by the dtype's max, so peak values are comparable across
  files regardless of bit depth.
- **Mono is enforced twice** — once by ffmpeg's `-ac 1`, once defensively in `read_wav` (mean
  across channels). The second guard matters because Story 3.3 may write a WAV directly.

## Deviations from the task file

- The task specifies the waveform query parameter as `points=N`; the Task 1.2.1 client had guessed
  `buckets`. Kept the task file's name and fixed the client.
- Added `refresh`, the `1..20000` bound, and `slice_wav`.

## Verification

```
pytest tests/test_audio_store.py   # 40 passed
pytest                             # 344 passed overall
mypy, flake8, black                # clean
```

The ffmpeg-dependent tests are marked `skipif(not ffmpeg_available())`, so the suite stays green
on a machine without it while still failing loudly if a conversion regresses where it *is*
installed. ffmpeg **is** present in the sandbox, so all of them actually ran.

Covered: every supported and unsupported suffix; WAV reading and duration; peak shape, bracketing
of a real 440 Hz sine, the more-buckets-than-samples case, dict round-trip, `points=0`; WAV
slicing and its backwards-range rejection; ingest normalizing to mono 16 kHz with the right
duration; explicit alias winning over the filename; **failed and unsupported ingests leaving no
folder**; waveform caching and recomputation at a different resolution; and the full HTTP round
trip.

The task's manual acceptance ("upload each supported format") is partly covered — only WAV is
exercised automatically, because generating a real MP3/AAC/M4A in a test needs an encoder. Please
try one of each by hand (below).

## Manual trial for the supervisor

**Record on the piano: Do Re Mi Fa Sol as slow negras at 60 BPM, one note per second, no pedal.**
Save it as mp3 and also export the same take as m4a and wav if you can — that covers the formats.

```bash
cd aitu-backend && uv sync && make serve
for f in take.mp3 take.m4a take.wav; do
  curl -s -F "file=@$f" 127.0.0.1:8765/audio/upload | python3 -m json.tool | grep -E 'alias|format|duration'
done
```

Each should return `201` with the right `format` and a `durationSeconds` matching the real length
(± a few hundredths). Then:

```bash
curl -s "127.0.0.1:8765/audio/<uuid>/waveform?points=200" | python3 -c "
import json,sys; w=json.load(sys.stdin)
print(w['points'], round(w['durationSeconds'],2), round(min(w['min']),2), round(max(w['max']),2))"
```

You should see `200`, the real duration, and min/max near ±1 for a loudly played take. Five clear
peaks separated by quiet stretches is what a five-note scale looks like — that is the check that
matters, and it is the same data Story 3.4's selector will draw.

Try a `.flac` too: it must be rejected with a `422` naming the supported formats.

## For the next worker

- **Story 3.4 (range selector)**: `GET /audio/{uuid}/waveform` is ready to draw from, and
  `formats.slice_wav` is ready behind the `/audio/{uuid}/range` placeholder.
- **Epic 4**: `StoredAudio.normalized_path` is mono at `formats.TRANSCRIPTION_SAMPLE_RATE`
  (16 kHz). If the engine wants a different rate, change that constant — it is the single source.
- Waveform peaks are already the piano-roll watermark data (Story 8.2); do not recompute them in
  the browser.
