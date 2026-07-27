# Task 13.1.1 — Composing live

## Subtask 13.1.1.1 — Empty piece and passage stage

Create a new empty track (empty matrix at chosen BPM/granularity). Record button opens a stage (reuse Task 11.1.1 sessions without a pre-existing target range): record, set BPM and granularity, view resulting notation, delete and re-record freely, or fix details via Matrix-tab editing — until the passage's sheet is clean.

## Subtask 13.1.1.2 — Insertion

When accepting a staged passage, the user chooses placement: append at a frame number or timestamp, or first select an existing frame range, open it in stage mode, edit/re-record, and overwrite that range on accept. Under the hood: Task 2.4.2 slice/insert/replace ops.

## Subtask 13.1.1.3 — Per-passage BPM conversion

A passage recorded at a slower BPM (e.g. 30) converts to the piece tempo (60) on insertion — the Task 11.3.1 scaling applied inside composition. Also allow changing the BPM/granularity of an already-inserted passage via re-staging.

## Acceptance

Manual trial: compose an 8-measure arrangement in two staged passages, one recorded at half speed.
