## Final recommendation

For your use case — **solo piano audio → exact piano keys, simultaneous note sets, onset, offset, duration, MIDI-like events, Python backend, local install, GPU available** — I would start with **ByteDance / Qiuqiang Kong `piano_transcription_inference`** as the core engine.

It is not the most-starred repo overall, but it is the best fit for **piano-specific transcription**: it is designed specifically to transcribe piano recordings into MIDI, supports `cuda` or `cpu`, outputs MIDI, and its underlying paper reports high-resolution onset/offset regression plus pedal transcription. The package is pip-installable and explicitly supports MP3 if `ffmpeg` is installed. ([GitHub][1])

The most popular general-purpose option is **Spotify Basic Pitch**: around **5.3k GitHub stars**, pip-installable, Apache-2.0, lightweight, polyphonic, and outputs MIDI plus note events. It is the best “safe default” for easy product integration, but it is **instrument-agnostic**, not piano-specialized. ([GitHub][2])

My practical pick:

**Use ByteDance `piano_transcription_inference` for your production piano pipeline, and benchmark Spotify Basic Pitch as a fallback/baseline.**

---

## What you actually need technically

You do **not** need to invent a new representation. The normal pipeline should be:

`video/audio file → extract audio → piano transcription model → MIDI/note events → your own active-key timeline`

The model gives you note events like:

```python
{
  "pitch": 60,          # MIDI note number, 60 = C4
  "start": 1.234,       # seconds
  "end": 1.812,         # seconds
  "duration": 0.578,
  "velocity": 91
}
```

Then you can compute, for any timestamp, the set of active keys:

```python
t = 3.250
active_notes = {note.pitch for note in notes if note.start <= t < note.end}
```

For performance, you should not scan all notes every frame. Use sorted onset/offset events and update an active set incrementally.

---

## Best approaches

| Option                                          |                                            Best for |                                             GPU |                             Output |           Popularity / maturity | My view                       |
| ----------------------------------------------- | --------------------------------------------------: | ----------------------------------------------: | ---------------------------------: | ------------------------------: | ----------------------------- |
| **ByteDance / `piano_transcription_inference`** |                                 Solo piano accuracy |                                     Yes, `cuda` |            MIDI + transcribed dict |    Specialized, research-backed | **Best fit for your project** |
| **Spotify Basic Pitch**                         |                          Easy, popular, general AMT | Runtime-dependent; mostly lightweight inference | MIDI, CSV note events, raw outputs |       Very popular: ~5.3k stars | Best fallback / baseline      |
| **Transkun**                                    | Modern piano transcription, event/interval decoding |                            Yes, `--device cuda` |                               MIDI | Less mainstream but interesting | Worth benchmarking            |
| **Omnizart**                                    |                 General music transcription toolkit |                Likely TensorFlow-based, heavier |                               MIDI |    ~1.9k stars, active releases | Good toolkit, less focused    |
| **Magenta Onsets & Frames**                     |                       Historical piano AMT baseline |                                  TensorFlow-era |                MIDI / NoteSequence |               Important but old | Avoid for new backend         |
| **MT3 / YourMT3-style models**                  |                      Multi-instrument transcription |                                Yes, but heavier |             MIDI / symbolic events |                  Research-grade | Overkill for solo piano       |

---

## 1. ByteDance `piano_transcription_inference`

This is the most directly aligned with your problem. The repo says it is a piano transcription inference package that lets users transcribe piano recordings to MIDI, and the usage example explicitly supports `device='cuda'` or `device='cpu'`. It also says `ffmpeg` is needed for MP3 files. ([GitHub][1])

Install:

```bash
pip install piano_transcription_inference
sudo apt-get install ffmpeg
```

Minimal Python:

```python
from piano_transcription_inference import PianoTranscription, sample_rate, load_audio

audio, _ = load_audio("input.mp3", sr=sample_rate, mono=True)

transcriptor = PianoTranscription(device="cuda")  # or "cpu"
transcribed_dict = transcriptor.transcribe(audio, "output.mid")
```

Why I like it for you:

It is **piano-specific**, not generic pitch detection. It was built for piano recordings, transcribes to MIDI, and the underlying ByteDance repo uses MAESTRO, a large aligned piano dataset. The paper reports onset F1 of **96.72%** on MAESTRO and pedal onset F1 of **91.86%**, which is exactly the kind of onset/offset/duration problem you care about. ([arXiv][3])

Main downside:

The package is older: Python 3.7 / PyTorch 1.4 were the original tested environment, although the docs say other versions may work. In practice, I would run it in a dedicated Docker image or conda environment, then benchmark it on your RTX 4090 machine. ([GitHub][1])

---

## 2. Spotify Basic Pitch

Basic Pitch is the most popular and easiest option. It is a Python library for automatic music transcription, pip-installable, lightweight, polyphonic, instrument-agnostic, and outputs MIDI. Its docs also say it can save predicted note events as CSV and return `note_events` programmatically. ([GitHub][2])

Install:

```bash
pip install basic-pitch
```

CLI:

```bash
basic-pitch ./out input.mp3 --save-note-events
```

Python:

```python
from basic_pitch.inference import predict

model_output, midi_data, note_events = predict("input.mp3")
```

Why it is attractive:

It is simple, maintained enough for practical use, Apache-2.0 licensed, and much more popular than the piano-specific repos: GitHub shows around **5.3k stars**. It accepts common audio formats including `.mp3`, `.ogg`, `.wav`, `.flac`, and `.m4a`, and resamples internally to 22,050 Hz. ([GitHub][2])

Main downside:

It is **not piano-specialized**. For your exact use case — dense chords, sustain pedal, fast arpeggios, overlapping notes — I would expect the ByteDance piano model to be a better first candidate. Basic Pitch is still an excellent baseline because it is easy and popular.

---

## 3. Transkun

Transkun is a newer piano transcription package with a simple CLI:

```bash
pip install transkun
transkun input.mp3 output.mid --device cuda
```

Its PyPI page says it transcribes expressive piano performance into MIDI, supports CUDA via `--device cuda`, and is based on event/interval modeling rather than only frame-level detection. ([PyPI][4])

Why it is interesting:

It is more recent than the ByteDance package, has a clean pip install, and the interval-based decoding is conceptually very aligned with your target: note start/end intervals rather than just frame activations.

Main downside:

It is less popular and less widely battle-tested than Basic Pitch or ByteDance. I would benchmark it, but I would not choose it as the first production default unless it clearly wins on your own audio.

---

## 4. Omnizart

Omnizart is a broader automatic music transcription toolkit. It supports pitched instrument transcription, drums, vocal melody, chords, beat tracking, and MIDI output. The docs show `pip install omnizart`, checkpoint download, and commands like `omnizart music transcribe <audio.wav>`. ([GitHub][5])

Why it may be useful:

It gives you a bigger MIR toolbox, not only piano note transcription. If later you want beat detection, chords, vocals, or multi-instrument support, it becomes interesting.

Main downside:

For a backend whose job is specifically **piano key events**, Omnizart is broader than needed. It also notes compatibility issues with ARM-based macOS, so I would use it on Linux if you test it. ([GitHub][5])

---

## 5. Magenta Onsets & Frames

Onsets & Frames is historically very important. It converts solo piano audio into MIDI/piano-roll and introduced the idea of using onset detection to improve frame-wise pitch prediction. ([Magenta][6])

But I would not choose it for a new backend. The Magenta repo itself says this repository is currently inactive and points users to MT3 for current transcription work. ([GitHub][7])

Use it only as historical reference or if you specifically want to reproduce old benchmarks.

---

## 6. MT3 / multi-instrument transformer models

MT3 is a multi-task, multi-track music transcription model using the T5X framework. It can transcribe either a piano checkpoint or a multi-instrument checkpoint, but the GitHub repo says local training is not easily supported and suggests using a Colab notebook for transcription. ([GitHub][8])

For your current project, I would not start here. It is much heavier operationally, more research-oriented, and unnecessary if your input is solo piano.

---

## Recommended backend architecture

Use this:

```text
1. Receive video/audio file
2. Extract mono WAV/MP3 audio with ffmpeg
3. Run piano_transcription_inference on GPU
4. Save MIDI
5. Parse MIDI into note intervals
6. Build active-key timeline
7. Return JSON to frontend/backend
```

Example output shape:

```python
[
  {
    "start": 0.512,
    "end": 1.044,
    "duration": 0.532,
    "midi_note": 60,
    "note_name": "C4",
    "velocity": 87
  },
  {
    "start": 0.514,
    "end": 1.030,
    "duration": 0.516,
    "midi_note": 64,
    "note_name": "E4",
    "velocity": 82
  }
]
```

And for simultaneous keys:

```python
[
  {
    "time": 0.50,
    "active_notes": []
  },
  {
    "time": 0.52,
    "active_notes": [60, 64, 67]
  },
  {
    "time": 1.05,
    "active_notes": []
  }
]
```

Use `pretty_midi` or `mido` after transcription. Mido is a Python library for working with MIDI messages and files, while `pretty_midi` is more convenient if you want note objects with `start`, `end`, `pitch`, and `velocity`. ([mido.readthedocs.io][9])

---

## Final decision

**Final pick: `piano_transcription_inference` by Qiuqiang Kong / ByteDance.**

It is the best match because you are not trying to transcribe arbitrary music; you are trying to detect **piano keys, chords, onsets, offsets, and durations**. It supports CUDA, produces MIDI, has a simple Python API, and is based on a piano-specific high-resolution model. ([GitHub][1])

**Benchmark plan:** run the same 20–30 piano clips through:

```text
1. piano_transcription_inference
2. Spotify Basic Pitch
3. Transkun
```

Then manually inspect: missing chord notes, false notes, onset timing, offset timing, sustain pedal behavior, and runtime. But as the first backend implementation, I would build around **ByteDance `piano_transcription_inference`**, with **Basic Pitch** as the fallback because it is the most popular and easiest to maintain.

[1]: https://github.com/qiuqiangkong/piano_transcription_inference "GitHub - qiuqiangkong/piano_transcription_inference · GitHub"
[2]: https://github.com/spotify/basic-pitch "GitHub - spotify/basic-pitch: A lightweight yet powerful audio-to-MIDI converter with pitch bend detection · GitHub"
[3]: https://arxiv.org/abs/2010.01815?utm_source=chatgpt.com "High-resolution Piano Transcription with Pedals by Regressing Onset and Offset Times"
[4]: https://pypi.org/project/transkun/ "transkun · PyPI"
[5]: https://github.com/Music-and-Culture-Technology-Lab/omnizart "GitHub - Music-and-Culture-Technology-Lab/omnizart: Omniscient Mozart, being able to transcribe everything in the music, including vocal, drum, chord, beat, instruments, and more. · GitHub"
[6]: https://magenta.withgoogle.com/onsets-frames "Onsets and Frames: Dual-Objective Piano Transcription"
[7]: https://github.com/magenta/magenta/blob/master/magenta/models/onsets_frames_transcription/README.md "magenta/magenta/models/onsets_frames_transcription/README.md at main · magenta/magenta · GitHub"
[8]: https://github.com/magenta/mt3 "GitHub - magenta/mt3: MT3: Multi-Task Multitrack Music Transcription · GitHub"
[9]: https://mido.readthedocs.io/en/stable/?utm_source=chatgpt.com "Mido - MIDI Objects for Python — Mido 1.3.2 documentation"
