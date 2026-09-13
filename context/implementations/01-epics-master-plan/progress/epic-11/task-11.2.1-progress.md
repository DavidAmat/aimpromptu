# Task 11.2.1 — Slow re-record flow · progress

Status: **done** on 2026-08-13. UI lives in the Frames toolbox Re-record tab (see 11.1.1).

## What was implemented

Four speeds: original, 2× slower, 4× slower, and Fit to the window. The window length in seconds
sits beside them, and 2×/4× also show the expected take length.

**Hear original** / **Hear slowed** play the marked window (slowed with `atempo`, pitch preserved).
An optional click track is a sound only; the interval is milliseconds (from the passage's named
gap × slowdown, or typed). Nothing about it is stored.

Recording reuses `useRecorder`. The take is stored untrimmed. Transcription finds the first onset;
the take is trimmed from there to `windowSeconds * slowdown` (or to the last note when Fit). The
untrimmed file stays in the session so the trim can be extended via PATCH `trimLengthSeconds`.

There is no capture granularity. The take is transcribed to events in seconds like everything else.

## Manual trial

Mark a 3-second stretch, choose 2× slower, turn the click track on, record a bit late, stop.
Transcribe: the take should be trimmed to about 6 seconds from its first note. Fit to the window
should measure the factor from the take instead of promising a length in advance.

## For the next worker

`PATCH /audio/{uuid}/edits/{session}` with `trimLengthSeconds` extends the trim without recording
again. The Re-record panel does not yet expose a trim slider; add it there if a reader asks to
keep more of an overrun.
