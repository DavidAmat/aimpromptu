# Task 3.3.1 — Browser recording · progress report

Status: **done, pending your manual trial.** Date: 2026-07-27.

> UI verification was skipped per your instruction. Everything below type-checks, lints and builds,
> but **no one has watched the bars move yet** — that is the acceptance criterion and it is yours.

## Summary

| File | Role |
|------|------|
| `src/audio/useRecorder.ts` | MediaRecorder capture + live level meter |
| `src/components/audio/LiveLevelBars.tsx` | the SoundCloud-style bar plot |
| `src/components/audio/AudioRecorder.tsx` | the record -> preview -> name -> save flow |
| `src/components/audio/AudioUpload.tsx` | file picker + upload (Story 3.2's UI half) |
| `src/components/audio/AudioLibraryList.tsx` | "load from library", with delete |
| `src/audio/time.ts` | `mm:ss.mmm` formatting and parsing |

All four are wired into `/playground/input`, so the page is now real rather than a placeholder for
its audio half.

### Capture and the live meter

`MediaRecorder` produces the blob; a parallel WebAudio `AnalyserNode` produces the bar heights,
because **MediaRecorder exposes no amplitude at all**. Both read the same `MediaStream`, so the
bars cannot drift from the recording. Bar height is **RMS**, not peak — it tracks perceived
loudness, which is what makes a bar plot readable. Bars above 0.85 turn warning-orange as a
clipping hint. The meter keeps the last 96 windows and scrolls.

### The container problem, and how it is handled

The backend accepts `.mp3/.aac/.m4a/.wav` by suffix. Browsers disagree about what `MediaRecorder`
can encode, and **Chrome records only webm/opus**, which is not on that list.

`preferredMimeType()` picks the first supported container from wav -> mp4 -> aac -> webm, and
`fileNameFor()` maps it to a suffix. If the browser can only produce webm, `fileNameFor` returns
`null` and the UI says so explicitly:

> *"This browser can only record formats the backend does not accept (webm/opus). Record with
> another app and upload the file instead."*

**This is the open decision for you.** Two ways forward, both small:

1. **Add `.webm`/`.ogg` to the backend's accepted suffixes.** ffmpeg decodes opus fine, and
   everything downstream reads the normalized WAV anyway — so this is a one-line change to
   `formats.SUPPORTED_SUFFIXES` plus a test. Recording then works in every browser.
2. **Leave it.** Safari and Firefox can record mp4/wav; Chrome users upload instead.

I did **not** widen the accepted formats on my own: the task file lists the four suffixes as a
requirement, and adding a fifth is a requirements change. Say the word and it is two minutes.

### Save flow

Stop -> preview `<audio>` (listen before saving) -> name field -> **Save to library** or
**Discard**. Saving posts to `POST /audio/recording`, so the take is normalized and tagged
`source: "recording"` exactly like an upload. The library list refreshes and selects the new take,
which also becomes the Playground's working artifact.

## Errors found and how they were solved

1. **`react-hooks/set-state-in-effect` again**, in `AudioLibraryList`. Same fix as `useProgress`:
   the list state is now **tagged with the request token** and freshness is derived during render,
   so the effect contains no synchronous `setState`. Worth internalizing — this lint rule is an
   *error* in this repo and it will catch every naive fetch-in-effect.
2. **`@mui/icons-material/DeleteOutline` does not exist** in MUI v9; the icon is `DeleteOutlined`.
3. **Object URL leaks.** Every path that replaces or clears the preview revokes the previous URL
   first, and `teardown` stops the `MediaStream` tracks and closes the `AudioContext` — otherwise
   the browser keeps the microphone light on after the component unmounts.

## Deviations from the task file

- The task says "upload the blob to `POST /audio/upload`"; it goes to `POST /audio/recording`
  instead, which is the same ingest path with the correct `source`. `/upload` would have tagged
  every take as an upload.
- Added `AudioUpload` and `AudioLibraryList` here rather than in Epic 6: Story 3.1's "load from
  library" and Story 3.2's upload had no UI, and the acceptance trial needs to reload a saved
  recording from the library.

## Verification

```
npx tsc -b        # clean
npm run lint      # clean
npx vite build    # 547 kB / 175 kB gzipped
```

No automated runtime test: `MediaRecorder`, `getUserMedia` and `AudioContext` need a real browser
with a real microphone. The logic worth unit-testing (`preferredMimeType`, `fileNameFor`, the time
helpers) is pure and exported, so it can be covered when a frontend test runner is added — there
is none in this repo today, and adding one was outside this task.

## Manual trial for the supervisor — this is the acceptance criterion

1. `cd aitu-backend && make serve`, then `cd aitu-frontend && npm run dev`.
2. Open **Playground > Upload / Input** and allow microphone access.
3. Press **Record**. **Play Do Re Mi Fa Sol as slow negras at 60 BPM** — one note per second, no
   pedal, letting each note ring for its full second.
4. Watch the bars: five clear tall clusters separated by quieter stretches. The timer should read
   about `00:05.000` when you stop.
5. Press **Stop**, play the preview back, type `Do Re Mi at 60 BPM`, press **Save to library**.
6. The take appears in **Audio library** with a `recording` chip and a duration around `0:05`.
7. Click it: the **Range** panel loads its waveform — the same five clusters, now drawn from the
   backend's peaks. Press **Play range** and confirm the audio is your recording.

**If step 3 shows an error about webm/opus**, you are on Chrome and hitting the container issue
above — tell me which of the two options you want.

Keep this recording. It is the reference take for every later epic's trial: Epic 4 transcribes it,
Epic 7 shows it as a matrix, Epic 9 engraves it.

## For the next worker

- `useRecorder` is reusable as-is for **Epic 11's slow re-recording** (Story 11.2); it needs a
  metronome and a beat display layered on top, not a new capture path.
- Never call `fetch` in these components — everything goes through `src/api/audio.ts`.
- The `set-state-in-effect` pattern (tag state with its request key, derive during render) is now
  used in three places: `useProgress`, `AudioLibraryList`, `WaveformRangeSelector`. Copy it.
