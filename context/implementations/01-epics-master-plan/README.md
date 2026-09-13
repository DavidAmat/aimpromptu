# 01 — Epics master plan

**Opened 2026-07-27. Complete 2026-09-13.** The original breakdown of the whole product into 14
epics, and the progress journal behind it. All fourteen are done; this folder is now the record of
how the product was built rather than a backlog.

| Folder | What is in it |
|---|---|
| [`plan/`](plan/README.md) | The plan itself: `checklist.md` (the status lookup), `wall-clock-rewrite.md` (the rules every remaining task obeys), one folder per epic, one file per task |
| [`progress/`](progress/README.md) | One report per task worked on, plus the dated session summaries, the late reports in `plan-resume/`, and the browser walkthroughs in `user_review/` |
| [`progress/RETROSPECTIVE.md`](progress/RETROSPECTIVE.md) | **The journal, closed.** What the fourteen epics produced, what the journal got right and wrong, what to carry forward |

## Status in one look

- **All fourteen epics are built.** Epics 1–9 were built first on a tempo-and-grid model; the
  [time-based concept refactor](../03-time-based-concept/CLOSURE.md) then replaced that model,
  deleted five screens that could not survive without a tempo, and rebuilt the sheet. Epic 10
  (Library), Epic 11 (range re-recording), Story 9.7 (trills), Epic 12 (lyrics, cue-size stretches,
  grace notes), Epic 13 (composing live) and Epic 14 (documentation) were all built afterwards, on
  the new model.
- **Three defects were found by Epic 14's documentation pass and fixed** on the same day, all listed
  under Epic 14 in the checklist: `make test` did not run at all, octave brackets were saved and
  silently dropped, and `npm run check:render` had been broken for a month. They were bugs in
  shipped code rather than leftover tasks.
- [`plan/checklist.md`](plan/checklist.md) is authoritative for every box.
- [`plan/TODO.md`](plan/TODO.md) holds loose notes from before the refactor — check them against
  the current app before acting on them.
