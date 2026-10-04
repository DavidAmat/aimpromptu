# Implementation progress journal

One report per worked task: `epic-NN/task-N.M.K-progress.md`. Written by the worker LLM at the end of each task, per `../plan/system-prompt-workers.md`.

Each report contains: summary of the implementation, main errors and their solutions, any agreed deviation from the plan (architectural / software / feature-level), manual trial instructions and outcomes, and notes for the next worker.

Current project status lives in `../plan/checklist.md` — always look there first; this folder is the narrative behind the checkboxes.

**The journal is closed.** All fourteen epics shipped; [`RETROSPECTIVE.md`](RETROSPECTIVE.md) is the
look back over the whole of it — what the epics produced, what the journal got right, what it got
wrong, and what to carry forward.

## Session summaries

When several epics are worked in one sitting, a dated summary at the top level says what happened,
what could not be verified, and what decisions are waiting on the human supervisor. Read the
summary before the individual reports.

- [2026-07-27 — overnight + continuation session](2026-07-27-overnight-session.md): Epics 1–8.
- [2026-07-27 — Epic 9 notation session](2026-07-27-epic-09-session.md): Stories 9.1–9.6.
- [2026-08-02 — transcription accuracy session](2026-08-02-transcription-accuracy-session.md): raw falling view, artifact filter, per-hand run quantiser, Transkun, tempo-map groundwork.
- [2026-08-10 — the time-based concept plan is closed](2026-08-10-time-based-concept-closed.md): the wall-clock refactor end to end, what it cost, what was dropped at closing, and what the next plan should carry forward.

## Reports written late

- [`plan-resume/`](plan-resume/README.md): the work committed between 2026-08-10 and 2026-08-12,
  immediately after the refactor closed and before the remaining epics were rewritten. It belonged
  to no epic and had no reports for a month. Six reports, written by Task 14.1.1.3 on 2026-09-13,
  reconstructed from commits — which in this repository carry the reasoning as well as the change.

  That gap is also why two documents written on the morning of 2026-08-10, `user-reviews.md` and
  `CLOSURE.md`, said that features which exist did not. Both have been corrected.
