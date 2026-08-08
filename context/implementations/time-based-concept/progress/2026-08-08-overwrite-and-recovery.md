# 2026-08-08 — twelve files were overwritten, and how they were put back

Not a task. This records an incident, because twelve files in `aitu-backend` are
reconstructions rather than the originals, and the next person to read them
should know that before trusting a detail.

## 1. What happened

A session opened on 2026-08-07 at 15:31 and copied `aitu-backend` into its own
sandbox to work from. It completed P4.1 and then paused.

Between 23:00 and 23:38 that evening **a second session finished the whole of
Phase 4** on the development machine: P4.2 through P4.8, with their reports and
the checklist ticked.

The first session resumed on 2026-08-08 and wrote its own version of P4.2 over
the top, from the copy it had taken eight hours earlier. It never re-read the
disk. **Twenty files were overwritten and five were moved aside.** The backend
was left mixed, and `make serve --reload` had already picked the clobbered code
up.

The cause is simple and worth stating plainly: work was done from a snapshot,
and the snapshot was not checked against the disk before writing. A long gap
between reading and writing is exactly when that check matters most.

## 2. What was recovered exactly

The second session had left its own transfer archives in `_to_delete/scratch/`,
which is what made most of this repairable.

| Files | Source |
|---|---|
| `transcription/pipeline.py`, `api/time_score.py` | its P4.5 archive, 23:23 |
| `storage/repository.py`, `tests/test_repository.py` | its P4.4–P4.8 archive, 23:38 |
| `layout/routes.ts`, `layout/PlaygroundLayout.tsx`, `music/granularities.ts` | its frontend snapshot, 23:00 |
| `matrix/ops.py`, `matrix/convert.py`, `tests/test_matrix_ops.py`, `tests/test_transcription_raw_events.py`, `tests/golden/notation/` | moved aside, not overwritten; moved back |

Two of the three frontend files turned out to predate its own P4.2, because the
snapshot was taken at 23:00 and P4.2 landed at 23:11. `routes.ts` came back with
seven Playground tabs, five of which have no route. That was corrected by hand
and is the one place where reading the file was not enough: it had to be opened
in a browser to be caught.

## 3. What was rebuilt, and how faithfully

Twelve files had no copy anywhere. They were rebuilt from
`P4.2-pipeline-rewired.md`, which lists every file it changed and describes what
each change was, and from the pre-Phase-4 baseline.

Six of them were **restored exactly**, because P4.2 either did not touch them or
touched them in a way the report pins precisely:

- `transcription/engine.py` and `tests/test_time_matrix_schema.py` were never
  changed by Phase 4. Restored from the baseline, verified against the report's
  statement that mypy still reports its six baseline errors, two of which live in
  `engine.py`.
- `tests/test_matrix_schemas.py` likewise: `matrix/convert.py` survived P4.2, so
  its converter tests were never removed.
- `transcription/time_pipeline.py` is the baseline plus one change the report
  names: the hand split is wrapped in a `two-hands` progress stage, so the bar
  does not skip the slowest step.

Six are **reconstructions**, faithful in behaviour but not guaranteed identical
in wording:

- `api/matrix.py` — five routes: engines, transcribe, progress, jobs, and
  `/{uuid}/events`. The report says the last one stayed and lost `rawGranularity`
  and `matchesGrid`.
- `api/__init__.py` and `matrix/__init__.py` — the notation router removed, and
  the module tables rewritten for what actually remains.
- `transcription/events_to_matrix.py` — the 1.x builder, the raw granularity
  constants and `column_count` removed; `shift_events`, `note_names_of` and the
  whole wall-clock half kept.
- `tests/test_transcription.py`, `test_transcription_artifacts.py`,
  `test_transcription_leakage.py`, `test_hands_persistence.py` — rewritten as the
  report describes, including the artifact test whose meaning changed (asking for
  the engine's events verbatim no longer places the 5.7 ms phantom, because a
  note shorter than one frame is refused whatever the artifact filter thinks).

## 4. Evidence that the result is right

The suite is **591 passing, 5 skipped, nothing failing**. The second session
recorded 589 passing; the two extra tests are in the rewritten
`test_transcription_artifacts.py`, which now pins the frame rule and the artifact
filter separately.

`flake8` reports nothing. `mypy` reports exactly the six errors that were present
before Phase 4 began, in the four files the report names, which is the fingerprint
that `engine.py`, `time_pipeline.py`, `time_score.py` and
`test_time_matrix_schema.py` are the originals rather than something rewritten.
`tsc -b` and `eslint` are clean in the frontend.

Checked in a browser against the real recording: the Playground has two tabs, the
peak plot draws 755 gaps between 756 right-hand notes with piles at 67, 120, 219,
337, 463, 674, 750 and 799 ms, and naming the 337 ms pile a negra writes a staff
of 2669 notes with beamed runs and no console errors. Those peak values are the
ones the second session recorded and the ones the proof of concept measured, so
the measurement path came through the rewiring and the recovery unchanged.

## 5. What was done to stop it happening again

**The refactor is committed.** Everything was uncommitted until now, across two
sessions and five days, which is the single reason a stale copy could destroy
work rather than conflict with it. Phases 0 to 4 are commit `9639aed` on the
branch `time-based-concept`, and each task commits from here.

`_to_delete/` is now in `.gitignore`, so the transfer archives and retired files
that make this kind of recovery possible do not enter the history.

Two operational notes for anyone working through the device bridge. Transfer
archives must be given task-specific names: this incident overwrote the second
session's `p42.tgz` with a file of the same name, which is why its P4.2 change
set was the one thing that could not be recovered. And git leaves `.git/*.lock`
files behind on this mount because it cannot unlink them; they are stale the
moment the command returns and have to be moved out of the way, or the next git
command refuses to run.

## 6. What is still uncertain

The six reconstructed files behave correctly and are covered by the suite, but
their comments and docstrings are mine rather than the second session's. If a
sentence in one of them reads oddly against `P4.2-pipeline-rewired.md`, the
report is the authority and the file is the copy.
