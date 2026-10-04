# Task 11.1.1 — Staged edit session · progress

Status: **done** on 2026-08-13. Implemented together with 11.2.1 and 11.3.1 as one flow.

## What was implemented

A disposable session lives at `data/audio/<uuid>/staging/<session_uuid>/`. It holds the frozen
window (`startFrame`/`endFrame` and `startSeconds`/`endSeconds`), the untrimmed take, the take's
`events.json`, and the speed factor. Cancel deletes the folder; nothing else is touched.

The splice is membership by onset only: notes that started before the window and still sound into
it are left alone. The take is scaled by the session factor and cut at `endSeconds`. Notes shorter
than one frame after scaling are dropped. `durationSeconds` is asserted unchanged.

Editorial marks anchored inside the window (figure overrides, beam breaks, hidden notes, fingerings)
are dropped and counted in the confirmation. Key, speed-change boundaries, and marks outside the
window stay. A passage boundary inside the window is kept.

Accept snapshots the previous `events.json` (and rhythm/audio when present) into
`data/audio/<uuid>/history/vN/` and advances `matrices/music-version.json`. The live piece is still
one `events.json` per audio uuid — playground `vN_f<frameMs>` folders are not involved.

Range picking is **not** new: the sheet still shift-picks columns and drags corner marks. The
Frames toolbox gained a **Re-record** tab beside Key and Octave; those two tabs are unchanged.
A range can also be typed as `mm:ss.cc`.

## Tests

`aitu-backend/tests/test_range_edit.py`: splice membership, scale/cut, short-note drop, outside
events byte-identical, mark dropping, cancel, accept duration, API start/cancel, typed timestamps,
preview+accept. 15 passing.

## Manual trial

On Rhythm, shift-pick about 3 seconds of a piece, open Frames → Re-record. The subtitle already
shows the stretch; the tab shows the window length in seconds. Cancel without recording: the piece
is unchanged. After a take (see 11.2.1 / 11.3.1), Accept: notes after the window keep their onsets;
the piece length is the same.

## For the next worker

- Do not change Key/Octave, shift-pick, or corner marks to "fix" re-record.
- Version history is under the audio uuid, not playground folders. If Epic 13 or library promotion
  needs those snapshots, read `editing/history.py`.
- Ottavas are not in backend `SavedRhythm`; they are only cleared in Rhythm local state on accept.
