# Task 11.1.1 — Staged edit session

The container object and lifecycle for a passage replacement.

## Subtask 11.1.1.1 — Session model

`storage/staging.py`: a staged replacement folder (under the track's playground folder, e.g. `staging/<session_uuid>/`) holding: original raw recording, trimmed recording, recording tempo + slowdown factor, capture granularity, temporary transcribed matrix, matrix converted to track tempo, rendered passage notation, optional tempo-compressed audio preview. Sessions are disposable; cancel deletes the folder.

## Subtask 11.1.1.2 — Range selection

UI to select the target range on the current version (frame numbers or timestamps; reuse the range/frame selectors). Range metadata (selected beats, frames) fixed at session start.

## Subtask 11.1.1.3 — Accept semantics

On accept: force the temporary matrix to exactly the target column count (trim excess, pad tail with silence), then `replace_range` (Task 2.4.2) into the main matrix, save as overwrite-or-new-version via the Epic 5 dialog, regenerate downstream artifacts (clean, hands, score). On cancel: nothing changes.

## Acceptance

Scenario test of the full session lifecycle with a synthetic replacement matrix.
