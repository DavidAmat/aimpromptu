# Task 11.1.1 — Staged edit session

> **Rewritten 2026-08-12 for the wall-clock model.** See
> [`../../wall-clock-rewrite.md`](../../wall-clock-rewrite.md).

The container and the lifecycle for replacing a passage. Nothing outside the session folder changes
until the user accepts.

## Subtask 11.1.1.1 — Session model

`storage/staging.py`: a folder `data/audio/<uuid>/staging/<session_uuid>/` holding the untrimmed
take, the trimmed take, the take's own `events.json` from the transcription engine, the speed factor
used, and the target window. Sessions are disposable; cancel deletes the folder and nothing else.

The target window is stored **twice on purpose**: as `startFrame` / `endFrame` (what the user
clicked) and as `startSeconds` / `endSeconds` (what the splice uses). Frames depend on the `frameMs`
of the view the user had open; seconds do not. The seconds are computed once at session start and
frozen.

## Subtask 11.1.1.2 — Range selection

Reuse what the sheet already has: shift-pick a stretch of columns, and drag either corner mark to
move an edge (P7.13, P7.15). A range can also be typed as two timestamps in `mm:ss.cc`. The Piano
Roll and Notes Falling views select the same way and open the same session.

Show the window length in seconds next to the selection, because that number is what the player has
to fill.

## Subtask 11.1.1.3 — Accept: the splice

One operation, on `events.json`:

1. **Membership is decided by onset time only.** Every event whose onset falls in
   `[startSeconds, endSeconds)` is removed. An event that starts before the window and still sounds
   into it is not touched — it is a note the player struck earlier, and D-14 already handles how it
   prints.
2. The take's events are scaled by the session's factor and offset to `startSeconds`
   (`newOnset = startSeconds + takeOnset * factor`, durations scaled by the same factor).
3. A replacement note still sounding at `endSeconds` is cut there. Sustain is measurement (D-06); a
   note may not sound past the window it was recorded into.
4. Notes shorter than one frame after scaling are dropped (D-05).
5. The result is written as a **new version** of the piece: the music changed, so the version number
   advances (contract §8).

`frameCount` and `durationSeconds` are unchanged by construction. Assert it rather than trusting it.

## Subtask 11.1.1.4 — What happens to the editorial marks

Marks anchored **inside** the window — figure overrides, beam breaks, fingerings, hand corrections,
hidden notes — point at notes that no longer exist. They are dropped on accept, and the confirmation
says how many, per kind, before the user presses the button. Marks outside the window, the piece's
key, and every passage boundary are kept exactly as they are: no renumbering, because no column
moved.

A passage boundary that falls **inside** the window is kept too. Its frame is still a real moment in
time; the notes around it changed, the boundary did not.

## Subtask 11.1.1.5 — The audio

The window length is the same before and after, so the recording and the page cannot drift apart.
What the recording still contains is the old playing. Default: the trimmed take is stretched to the
window length, pitch preserved (`ffmpeg atempo`), and written over that stretch of the source audio,
so what you hear is what you see. The original file is kept in the version's history.

If the stretch factor is outside what `atempo` can do in one pass, or the user turns the audio
splice off, the piece keeps its original audio and the Rhythm tab marks that window as "audio does
not match the sheet here". Do not fail the edit because of the audio.

## Acceptance

Scenario test of the full lifecycle with a synthetic take: window unchanged in length, events
outside the window byte-identical, marks inside the window dropped and counted, cancel leaves the
piece untouched.
