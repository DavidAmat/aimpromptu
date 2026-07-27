# Task 6.1.1 — Input sources UI

One tab, five source modes (MUI tabs or segmented control):

## Subtask 6.1.1.1 — Upload audio

File picker -> `POST /audio/upload` (Task 3.2.1) -> waveform preview.

## Subtask 6.1.1.2 — Record audio

Embed the recording component (Task 3.3.1) with name-and-save into the audio library.

## Subtask 6.1.1.3 — Load from library

List saved audios (Task 3.1.1) with alias/duration/source; pick one to make it the working audio (e.g. predetermined pieces like a two-hand C-major scale).
Persisted segments appear as audio items too, but their lineage banner and truncated waveform make
them visually distinct from an entire track. **Back to original** loads the root source.

## Subtask 6.1.1.4 — Textual notation

Textarea accepting the text notation of `02-notation-spec.md` (including the `__` two-hand separator from `TODO.md`); posts to the existing parse endpoint and produces matrices directly (no transcription engine involved). Keep the current SequenceComposer behavior as the base.

## Subtask 6.1.1.5 — JSON import

Upload a matrix JSON previously downloaded from the Matrix tab (dense or sparse; the `sparse` metadata property tells which). Validated (Task 2.1.2 normalize) and loaded at its declared `matrixProcessingStep`.

## Acceptance

Every mode ends with the Playground "working artifact" context populated. Switching to notation or
matrix JSON clears any previously selected audio state so it cannot override the new artifact.
