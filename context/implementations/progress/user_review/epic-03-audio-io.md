# 2 — Audio I/O (Epic 3)

**What this epic did:** every way of getting sound into the app — uploading a file, recording from
your microphone, downloading from YouTube — plus the waveform display and the range picker.

About 20 minutes. You will need a microphone, a piano, and one mp3.

Everything happens on **http://localhost:5173/playground/input**.

---

## 2.1 — Upload a file

Click the **Upload audio** tab.

1. Press **Choose an audio file** and pick any mp3 you have.
2. Leave the name blank the first time.
3. Press **Upload**.

**What you should see:** the file appears selected, and after a moment the **Range** panel on the
right draws its waveform.

> **What happens when you press Upload.**
> 1. The file is sent to the backend, which looks at the *extension* to decide the format.
> 2. It gets a folder of its own, named with a random id, under `aitu-backend/data/audio/`.
> 3. ffmpeg converts it once into a plain mono WAV. Both files are kept — yours, and the converted
>    one everything else reads.
> 4. The backend measures the loudness at a thousand points along the file and sends that back;
>    that list of numbers is what the waveform is drawn from. **Your browser never decodes the
>    audio** — it just draws numbers.

Check it landed on disk:

```bash
ls aitu-backend/data/audio/*/
# metadata.json  original.mp3  normalized.wav  waveform.json
```

Open one of those `metadata.json` files. It should read plainly: the name, where it came from,
the format, how long it is.

**Now try a bad file.** Rename any text file to `test.flac` and upload it.
→ A red message: *"'test.flac' has an unsupported extension. Supported: .mp3, .aac, .m4a, .wav,
.webm, .ogg"*. Not a crash.

---

## 2.2 — Record from the microphone ⭐

This is the important one — the recording you make here is reused by later guides.

Click the **Record** tab.

1. Press **Record**. Your browser asks for microphone permission — allow it.
2. **Play Do Re Mi Fa Sol on the piano — one note per second, at 60 BPM, no pedal**, letting each
   note ring for its full second.
3. Press **Stop** after about five seconds.

**What you should see while recording:**

- Bars marching across the meter, **tall where you play, short in the gaps**. Five clear clusters.
- The timer counting up. It should read around `00:05.000` when you stop.

> **What the bars are.** The recording and the meter read the same microphone stream at the same
> time. The bar height is the loudness of the last fraction of a second — so the bars cannot
> disagree with what is actually being recorded. Bars turn orange above about 85% as a "you are
> close to clipping" hint.

**After you stop:**

4. A small player appears — press play and listen back. This is before anything is saved.
5. Type a name: `Do Re Mi at 60 BPM`.
6. Press **Save to library**.

> **What happens when you press Save.** The recording is sent to the same place uploads go, tagged
> as a recording rather than an upload, and converted by ffmpeg exactly the same way. Chrome can
> only record in a format called webm/opus — that is fine, ffmpeg handles it, which is why the app
> accepts it. **Recording should work in Chrome, Safari and Firefox alike.**

7. Click the **Audio library** tab → your take is there, with a `recording` label and a `0:05`
   duration.
8. Click it → the **Range** panel draws its waveform: **five clear humps** separated by quieter
   stretches.

**Keep this recording.** Guides 3 and 4 use it.

---

## 2.3 — The range picker

With your recording still selected, look at the **Range** panel.

1. **Drag the left handle** rightwards. While you drag, a small black tooltip above it shows the
   time as `mm:ss.mmm`, live.
2. **Drag the right handle** leftwards. The selected middle shades purple.
3. Try dragging the left handle *past* the right one → it stops. They cannot cross.
4. Under the waveform, type `00:01.000` in **Start** and press Enter → the left handle jumps there,
   and the "N selected" text updates.
5. Type nonsense like `abc` in **End** and click away → the field snaps back to its previous value.
   The handle does not move. **A half-typed value never moves anything.**
6. Press **Play range** → a pink line sweeps across, and **stops exactly at the right handle**.
7. Press **Play all** → it plays the whole thing, ignoring the selection.

> **How playback works.** The audio was already downloaded to draw the waveform, so playing a range
> is just the browser seeking within the file it already has — no waiting, and the pink cursor is
> simply the current play position read many times a second. That is why the range plays instantly
> however many times you change it.

**Then check it is remembered:** click the **Matrix** tab and come back. Your selection should
still be there — the range is part of the "working piece", so guide 4 can transcribe just that
passage.

---

## 2.4 — YouTube

Go to **http://localhost:5173/youtube**.

1. Paste the URL of a **short, piano-only** video — a solo cover, no vocals or backing. One or two
   minutes.
2. Click into the **Name** field (or press Tab).
   → The name fills in automatically with the real video title.

> **What just happened.** The backend asked yt-dlp for the video's information *without*
> downloading it — just the title and duration — so the name field can be pre-filled. This is why
> there is a short pause and a little spinner.

3. Change the name to something you will recognize.
4. Press **Download**.

**What you should see:** a progress bar, then a green *"Saved …"* with the duration and an **Open
in Playground** button.

> **What happens during the download.** yt-dlp fetches the best audio-only stream, ffmpeg converts
> it to mp3, and then it enters the audio store exactly like an upload — same folder shape, same
> conversion, with the original YouTube link recorded in its metadata.

5. Press **Open in Playground** → back on the Input tab with that audio selected, waveform drawn.

**Then try two failures on purpose:**

- Paste a **Vimeo** link → *"...is not a YouTube URL. Expected a youtube.com/watch, youtu.be or
  youtube.com/shorts link."*
- Paste a **private or age-restricted** video → you should see YouTube's own explanation, passed
  through word for word. If that message reads badly, tell me — it is deliberately not paraphrased.

---

## What "working" looks like

- An mp3 uploads, gets a waveform, and lands in `data/audio/<id>/` with four files.
- A microphone recording shows five clusters of bars, saves, reloads from the library, and plays.
- Range handles drag with a live tooltip, cannot cross, accept typed times, reject nonsense, and
  **range playback stops at the right handle**.
- A YouTube URL pre-fills its title and downloads to mp3.
- Bad input produces a sentence, never a crash.

## If it goes wrong

| Symptom | Likely cause |
|---|---|
| Upload fails with 503 | ffmpeg is not installed — `brew install ffmpeg` |
| Microphone permission never asked | The page must be on `localhost` (it is) and not in an iframe |
| Bars do not move while recording | Check the browser console; the meter and the recorder share one stream |
| Recording saves but has no duration | ffmpeg could not read the container — tell me which browser |
| YouTube download fails | Read the message: it is yt-dlp's own. Rate limits are common and temporary |
| Waveform never loads | Look at the backend terminal — the peak computation logs any error |

Next: [3 — Transcription](epic-04-transcription.md)
