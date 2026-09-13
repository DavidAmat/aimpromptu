# Task 3.3.1 — Browser recording

Record from the device microphone inside the Playground Input tab.

## Subtask 3.3.1.1 — Capture

MediaRecorder API; record to webm/opus or wav depending on browser support; on stop, upload the blob to `POST /audio/upload` (backend normalizes like any upload, `source = "recording"`).

## Subtask 3.3.1.2 — Live waveform

While recording, render a SoundCloud-style bar plot fed by the WebAudio AnalyserNode: one bar per short window, tall bars for loud moments. Purely visual feedback.

## Subtask 3.3.1.3 — Save flow

Stop -> preview player (listen before saving) -> name input -> save to the audio store, or discard. Saved recordings appear in the audio library.

## Acceptance

Manual trial (human in the loop): record a slow 5-note scale (Do Re Mi Fa Sol at ~60 BPM), see the bars react, save it, reload it from the library and play it back.
