# Epic 11 — Range editing and re-recording

Replace a selected passage of an existing piece by re-recording it — optionally at a slower practice tempo — with a preview-first, non-destructive staged workflow.

Read first: `context/music/notation-logic/03-editing-logic.md` (the authoritative spec for this epic) and `project-features.md` "Timings when editing" and "General Flexibility of the pieces".

## Story 11.1 — Staged edit sessions

- Task 11.1.1 staged edit session: select a frame range on a track version, open a stage holding all replacement artifacts, accept/cancel semantics, exact column-count enforcement on accept.

## Story 11.2 — Slow re-recording

- Task 11.2.1 slow record flow: metronome at recording tempo, slowdown factors (original / 2x / 4x), trimming to expected beats, independent capture granularity.

## Story 11.3 — Preview and accept

- Task 11.3.1 replacement preview: transcribe the slow recording, scale timings to track tempo, render only the passage, listen/inspect/re-record/accept/cancel.

## Exit criteria

Manual trial from the editing-logic doc: a 4-beat range at 60 BPM re-recorded at 30 BPM lands back as exactly 4 beats, previewed before acceptance, original untouched on cancel.
