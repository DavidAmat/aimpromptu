# Task 7.4.2 — Matrix player · progress

Status: **done and browser-verified** on 2026-07-27.

## Delivered

The Matrix tab reuses Epic 8's `useMatrixPlayback` transport and WebAudio piano fallback. Play,
pause, restart and timestamp seek are available above the grid. A highlighted cursor row advances
from the AudioContext clock, automatically keeping the current row visible. Onsets trigger a tone;
the envelope decays across the note's sustain instead of re-striking every held cell.

## Verification

The imported five-note scale played from frame 0 to the end, the transport changed to Pause while
running, the frame/timestamp advanced, and no browser console error was emitted.

## Supervisor trial

Play the real recorded scale in Matrix. Each heard note should begin on its filled circle, continue
through its pale tail, and stop before the next note. Compare with the Piano Roll transcription
source, which uses the same engine and should sound identical.
