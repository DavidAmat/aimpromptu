# Implementation plan

Organized breakdown of `project-features.md` into epics, stories, tasks and subtasks (Jira-like nomenclature, all local, no Jira).

How to navigate:

- `checklist.md` is the single status lookup for the whole project. Start here.
- Each epic is a folder `epic-NN-<shortname>/` with an `epic-<shortname>-index.md` summarizing its stories and tasks.
- Each story is a nested folder `story-N.M-<shortname>/`. Each task is one markdown file `task-N.M.K-<shortname>.md`. Subtasks are header sections inside the task file.
- Workers read `system-prompt-workers.md` before doing anything, then their assigned Epic > Story > Task file.
- Progress reports go to `../progress/` (one file per task worked on).

Current implementation boundary: **Epics 1–8 are complete and committed; Epic 9 has not started.**
The checklist is authoritative for status. Task files describe the current agreed requirements,
including requirement changes made during implementation.

Epic order (also the recommended implementation order):

1. `epic-01-skeleton` — project skeleton and foundations
2. `epic-02-matrix-core` — piano matrix engine
3. `epic-03-audio-io` — audio capture, upload, YouTube, storage
4. `epic-04-transcription` — audio to matrix pipeline
5. `epic-05-artifacts` — artifact repository and versioning
6. `epic-06-playground-input` — Playground Input tab
7. `epic-07-matrix-view` — Playground Matrix tab
8. `epic-08-piano-roll` — Piano roll and notes falling views
9. `epic-09-notation` — VexFlow music notation rendering
10. `epic-10-library` — Piano Library and playlists
11. `epic-11-editing` — range editing and re-recording
12. `epic-12-annotations` — lyrics, fingering, small notes (nice to have)
13. `epic-13-compose-live` — live composition (nice to have)
14. `epic-14-docs` — final documentation (always last)
