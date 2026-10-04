# Task 3.5.1 — YouTube to audio · progress report

Status: **done, pending your manual trial.** Date: 2026-07-27. This closes Epic 3.

## Summary

`audio/youtube.py` + `api/youtube.py` + the `/youtube` page.

| Endpoint | Role |
|----------|------|
| `POST /youtube/probe` | title, duration, uploader — **without downloading**, so the UI can prefill the name |
| `POST /youtube/download` | best audio -> mp3 -> the audio store |
| `POST /youtube/batch` | several URLs in order (the nice-to-have queue) |

Request body is `{url, fileName}` exactly as the task file specifies; `fileName` is an alias for
the model's `alias` field, so both spellings work and a test pins that.

The download shells out to `yt-dlp`:

```
yt-dlp --no-playlist --no-part --newline -f bestaudio/best -x --audio-format mp3
       --audio-quality 0 -o '<temp>/%(title)s.%(ext)s' <url>
```

into a `TemporaryDirectory`, then hands the mp3 to `ingest.ingest_path(..., source="youtube",
source_url=url)`. **A YouTube audio therefore ends up byte-for-byte identical in structure to an
upload**, apart from `source` and `sourceUrl` — same folder shape, same normalized WAV, same
waveform cache. Nothing downstream needs to know where it came from.

### Two decisions worth recording

**yt-dlp is used through its CLI, not its Python API.** The CLI is the stable, documented surface,
and — more importantly — its error messages are exactly what the user needs to read. Rate limits,
private videos, geo blocks and "Sign in to confirm you're not a bot" all arrive as sentences
written by people who know YouTube's behaviour better than I do. `_clean_error()` pulls the last
`ERROR:` line and surfaces it **verbatim**, which is what subtask 3.5.1.1 asks for.

**The URL is validated before any subprocess runs.** `YOUTUBE_URL` accepts `youtube.com/watch`,
`youtu.be`, `shorts`, `live`, and the `m.`/`music.` subdomains, and rejects everything else with a
`422`. This endpoint passes user input to a shell-less `subprocess` call, so the input is
constrained on principle rather than trusted — `file:///etc/passwd` and bare `not a url` are both
in the rejection test list.

Status codes: `422` invalid URL, `503` yt-dlp missing (names `uv sync` as the fix), `502` YouTube
refused (their problem, their wording).

### Progress

`download()` parses yt-dlp's `--newline` progress lines and advances a `ProgressReporter` stage, so
the same events drive a terminal bar today and the SSE stream once Epic 4 adds the job plumbing.
The endpoint itself is **synchronous** — a typical piano video takes seconds — and the UI shows an
indeterminate bar. Wrapping it in Epic 4's job machinery is a small change when long videos become
normal; the events are already there.

### Batch

`POST /youtube/batch` runs items in order and **reports each outcome separately**, so one
rate-limited URL does not abandon the rest of the queue. Marked nice-to-have in the task file; it
was ten lines once the single flow existed.

### UI

`/youtube` now has: URL field (probing the title on blur), name field (prefilled from the probe
but **never overwriting** what you typed), Download button, progress bar, a success alert with an
**Open in Playground** link that sets the working artifact, and the shared `AudioLibraryList`
below.

## Errors found and how they were solved

1. **mypy vs. monkeypatched lambdas.** Stubbing `ingest_path` with a lambda that returns a tuple
   made mypy lose the types of the unpacked variables. Rewritten to record into a dict inside a
   named function — clearer to read as well.
2. **The smoke test again.** `/youtube/queue` was in the `501` placeholder list; that route no
   longer exists (it became `/youtube/batch`). Updated with a comment.
3. **`--no-part`** was added after thinking about the temp directory: without it yt-dlp leaves
   `.part` files that the `*.mp3` glob would miss, turning a successful download into the
   "produced no mp3" error.

## Deviations from the task file

- The queue endpoint is `POST /youtube/batch`, not `GET /youtube/queue`. A `GET` queue implies
  server-side state and a background worker; there is neither, and a single-user PoC does not need
  one. The batch endpoint does the same job synchronously.
- Added `POST /youtube/probe`, which the task did not list. Subtask 3.5.1.2 wants a file-name
  input; prefilling it with the real video title is what makes that field pleasant.
- `yt-dlp>=2025.1.15` added to `[project.dependencies]`.

## Verification

```
pytest tests/test_youtube.py   # 30 passed, 1 skipped (yt-dlp absent in the sandbox)
pytest                         # 378 passed overall
mypy, flake8, black            # clean
npx tsc -b, npm run lint       # clean
```

**Nothing in the tests touches the network.** `yt-dlp` is stubbed at the subprocess boundary, so
they pin *our* behaviour — URL validation (7 accepted shapes, 7 rejected), progress-line parsing,
error wording and precedence, the ingest wiring including `alias`/`source_url`, the
"no mp3 produced" case blaming ffmpeg, and every endpoint status code including batch's
per-item reporting.

The one thing not covered is yt-dlp actually working, which only a real download proves — hence
the trial below.

## Manual trial for the supervisor — this is the acceptance criterion

`yt-dlp` was **not** installed in the sandbox, so this path has never really run. Please:

```bash
cd aitu-backend && uv sync && uv run yt-dlp --version   # confirm it installed
make serve
```

Then open **YouTube to Audio** and:

1. Paste a **piano-only** video URL (a solo cover, no vocals or backing — Epic 4 transcribes piano).
   Keep it short, a minute or two.
2. Tab out of the URL field: the name should fill in with the real video title.
3. Change the name to something you will recognize, e.g. `Levels (piano) - Avicii`.
4. **Download**. Expect a few seconds, then a green "Saved …" alert with the duration.
5. It appears in the list below with a `youtube` chip. Click **Open in Playground**, go to
   **Playground > Upload / Input**, and confirm the waveform draws and **Play all** plays it.
6. On disk: `aitu-backend/data/audio/<uuid>/` holds `original.mp3`, `normalized.wav`,
   `metadata.json` — and `metadata.json` has your alias plus the `sourceUrl`.

Worth trying deliberately: paste a **Vimeo** link (expect a clear `422`), and an
**age-restricted or private** video (expect yt-dlp's own message shown verbatim). If YouTube
rate-limits you, that message is the one you will see — tell me if it reads badly and I will
improve the wrapping.

## Epic 3 status

All five stories are implemented. The exit criterion — *"an audio can arrive via upload, mic
recording or YouTube URL; it lands in a uuid folder with metadata; the UI can show its waveform,
select and play a sub-range"* — is met in code and needs your trial to be confirmed in practice.

**Recommended order for tomorrow**: Story 3.2 (upload) first, since it is the least likely to
surprise; then 3.3 (recording — note the Chrome/webm question in that report); then 3.4 (range);
then this one. The five-note scale recording from the 3.3 trial is the reference take for every
later epic.

## For the next worker

- **Epic 4** consumes `StoredAudio.normalized_path` regardless of source. Nothing in the
  transcription path should branch on `source`.
- If long videos become normal, wrap `youtube.download` in Epic 4's job runner and stream the
  existing `ProgressReporter` events over SSE — no changes needed inside `youtube.py`.
- Keep using the CLI. If you switch to the Python API, you lose the verbatim error messages.
