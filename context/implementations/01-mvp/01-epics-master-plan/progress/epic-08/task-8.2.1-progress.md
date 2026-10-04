# Task 8.2.1 — Piano Roll layout · progress

Status: **done and browser-verified** on 2026-07-27.

## Delivered

The Piano Roll loads the shared two-hand dense matrix, fits the entire vertical keyboard to the
view height, and lays note rectangles on key-calibrated lanes. Time uses horizontal distance;
every frame has a dashed numbered guide. Left/right hand colors use the shared palette. Playback
locks and follows the horizontal scroll.

The original waveform uses `<WaveformView watermark />`. A saved segment already owns a physically
trimmed waveform, so no browser-side range slicing or hidden offset is needed. BPM and granularity
use the same fast recompute path as Matrix. “Open this frame in Matrix” passes a frame query deep
link.

## Verification and manual trial

The imported `Do Re Mi Fa Sol` scale rendered as a staircase aligned to C4–G4 and deep-linked back
to frame 0. Use the real recording to verify the faint waveform peaks sit under the corresponding
onsets.
