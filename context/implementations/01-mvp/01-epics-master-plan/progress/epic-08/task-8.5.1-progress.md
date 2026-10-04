# Task 8.5.1 — Drag note editing · progress

Status: **done and browser-verified** on 2026-07-27.

## Delivered

Both animated views stage pointer drags without touching persisted data. While dragging, all key
lanes show dashed landing guides and Spanish names. The drop chooses the nearest piano key and
frame, preserves note duration, clamps the result inside the piece, outlines the moved note, and
increments the Save badge.

Save converts each move to backend delete + onset + sustain operations and persists through the
same validator-backed endpoint as Matrix. Cancel discards all staged moves.

## Verification and manual trial

Browser drags in both views produced `Save (1)` and Cancel restored the original. For the real
trial, drag one deliberately wrong scale note to the right key/frame, Save, then verify the
correction in Matrix and by synthesized playback.
