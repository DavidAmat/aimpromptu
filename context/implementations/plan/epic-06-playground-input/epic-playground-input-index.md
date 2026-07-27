# Epic 6 — Playground Input tab

The entry door of the Playground: choose an input source (upload, record, text notation, JSON,
audio library), optionally create a physically trimmed and named audio segment, set BPM and target
granularity, and launch the pipeline. Thin epic — it composes components from Epics 3 and 4.

Read first: `project-features.md` "Upload / Input tab"; `context/music/notation-logic/02-notation-spec.md`.

## Story 6.1 — Input sources UI

- Task 6.1.1 input sources: the five source modes wired into one tab, producing a working artifact uuid.

## Story 6.2 — Transcription settings

- Task 6.2.1 transcription settings: persisted audio-segment creation, BPM input, granularity
  dropdown, truthful model/pipeline progress, run + handoff to the Matrix tab.

## Exit criteria

Manual trial: each of the five sources ends with matrices loaded and the app auto-navigating to the Matrix tab with the working artifact set.
