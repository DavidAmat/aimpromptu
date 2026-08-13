# Task 14.1.1 — Final documentation

> **Rewritten 2026-08-12 for the wall-clock model.** See
> [`../../wall-clock-rewrite.md`](../../wall-clock-rewrite.md).

## Subtask 14.1.1.1 — The detail tree

Bring `documentation/services/backend/` and `documentation/services/frontend/` in line with the
code: the endpoints under `/time` and `/matrix`, the schema 2.0 models, `events.json` as the only
stored file, the derivation path from events to a drawn sheet, the storage layout with
`v<N>_f<frameMs>`, and the drawing package's own contract.

`time-matrix.md` is still marked "stub" and still says no pipeline builds a time matrix. It is the
first file to fix.

## Subtask 14.1.1.2 — The context overviews

Update `00-project-complete-overview.md`, `01-project.md`, `03-services-overview.md` and
`00-index.md`. Several documents already carry banners saying they describe a model the app no
longer has; decide for each whether to rewrite it or move it to `archive/`, and do not leave a
banner as the permanent answer.

## Subtask 14.1.1.3 — The gap after the plan closed

The work committed on `plan-resume` on 2026-08-10 has no progress reports: Piano Roll and Notes
Falling back on the wall clock, taking a note off the recording, note selection, the scrub bar, the
draggable playhead, both ends of a marked stretch. `user-reviews.md` and `CLOSURE.md` still say some
of these do not exist. Write the reports, then correct those two documents.

## Subtask 14.1.1.4 — Closing the journal

A short retrospective over `context/implementations/progress/`. The checklists stay as the
historical record of what shipped and what was cancelled.

## Acceptance

The index is complete, every documented command runs, and no document mentions a BPM input, a
granularity choice or the Matrix tab as if they existed.
