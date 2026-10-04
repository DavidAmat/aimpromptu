# The journal, closed

**Written 2026-09-13 by Subtask 14.1.1.4.** The fourteen epics are done. This is a short look back
over the whole journal — what it produced, what it got wrong, and what is worth carrying into the
next plan.

The checklists stay exactly as they are, as the historical record of what shipped and what was
cancelled. This page does not replace them; it says what they add up to.

## The shape of it

| | |
|---|---|
| Opened | 2026-07-27 |
| Closed | 2026-09-13 |
| Epics | 14, all complete |
| Progress reports | 126, across three implementation folders |
| Backend | ~19,000 lines of Python, 40 test files, 765 tests |
| Frontend | ~17,000 lines of TypeScript |

Three implementation plans ran inside that window and the middle one changed the other two:

1. **Epics master plan** — the whole product, cut into fourteen epics.
2. **VexFlow migration** — the decision to build our own renderer. Closed early.
3. **Time-based concept** — the wall-clock refactor. Closed 2026-08-10, and it deleted the model
   Epics 1 to 9 had been built on.

## The one thing that mattered

The plan set out to build a piano-notation app and spent its middle third discovering that its
central abstraction was wrong.

A matrix column was doing two jobs — where a note sits, and what the note is worth — and because it
was both, its width had to come from a typed tempo. Every evenly played run printed ragged, and no
amount of work on the layers above it could have helped, because the arithmetic had no way out: a
run at 1.27 columns per note has to be written as some 1s and some 2s.

**Separating the two jobs is the project.** Everything readable about the app today follows from it,
and so does everything that was cheap to build afterwards. Epics 10 to 13 — the library, range
editing, annotations, composing — were all substantially easier than they would have been on the old
model, because "a column never moves" made every editorial mark a stable address.

### What that cost

Five screens, deleted. Two of them came back. Stories 9.1 to 9.6 were superseded after being built,
though what they promised — key signatures, transposition, octave and clef displacement, guides —
exists again on the new path.

That is the honest cost line, and it was worth paying. The alternative was a product that produced
the same wrong figure every time.

## What the journal got right

**Reports carry the reasoning, not the diff.** A reader a month later wants to know *why* the floor
is 20 ms and not 40, and the answer — Transkun returns 34 ms notes for a passage ByteDance calls
200 ms — is in the report and in the module docstring. Several times during this documentation pass,
a commit message was the only surviving record of a measurement, and it was enough.

**Measurements, not intuitions.** The strongest reports are the ones that quote a number: 78 events
under 16 ms and nothing between 16 and 32; 0.5 removes three phantoms of four and 0.6 deletes a real
note; the sheet went 2639 → 2638 → 2639 across a delete and a restore. The weakest are the ones that
assert a rule and move on.

**Cancellations are stated, with the reason.** Eight boxes were cancelled rather than left open, and
each one says why. "Dropped, not pending" is a useful thing to be able to read.

**Frozen decisions survived the whole project.** `decisions.md` (D-01 … D-34) was written during the
refactor and needed no amendment through Story 9.7 and Epics 10 to 14. Six things were escalated to
`progress/issues.md` — the log a worker writes to instead of reinterpreting a decision — and all six
were raised **during** the refactor and resolved by the supervisor. Nothing after it needed a
decision reopened, and the escalation rule is why: a worker who finds a contradiction stops, rather
than quietly deciding.

## What the journal got wrong

**The gap after 2026-08-10.** The refactor closed, said "the next input is a round of real playing",
and the round started the same afternoon. The work that came out of it was good and went straight
into the product — and it had no reports for a month, because the plan it belonged to had closed and
the epics it fed had not yet been rewritten.

Two documents written that morning, `CLOSURE.md` and `user-reviews.md`, then told readers that
features which existed did not. Task 14.1.1.3 wrote those reports and corrected both documents.

**The lesson is narrow and worth keeping:** a plan closing does not close the work. If work is
happening, it has a home to be reported in, even if that home is a dated folder with no plan
attached.

**Documentation was left for the end, and the end was late.** This epic found `time-matrix.md` still
marked "stub" from Phase 0, `endpoints.md` describing three routes when the app answers sixty-three, and
the frontend detail tree describing components deleted two months earlier. A new reader following
`00-project-complete-overview.md` would have been told the app renders text notation with VexFlow.

Keeping `documentation/` current continuously would have cost more in total. Whether it would have
cost less *usefully* is a real question — nobody read those files while they were wrong, which is
itself the argument for deferring them, and also the reason nobody noticed.

**Documentation found three bugs, and none had a failing test.** Reading each document against the
code showed that `make test` did not run at all, that octave brackets were sent by the page and
silently dropped by the backend, and that `check:render` — the only guard against a *silent*
rendering failure — had itself been silently failing for a month. All three were fixed the same day
([`epic-14/task-14.1.2-progress.md`](epic-14/task-14.1.2-progress.md)).

The pattern is worth more than the bugs. Each was a place where two sides of a seam disagreed and
**nothing was watching the seam**: a test runner that reported nothing rather than failing, a field
Pydantic dropped rather than rejected, a check that exited without anyone reading its output.
Writing down what each side claimed is what made the disagreements visible.

## What to carry forward

- **`decisions.md` stays binding.** A new plan that wants to change one of those decisions has to
  say which, and why, in its own document.
- **The five rules** in [`wall-clock-rewrite.md`](../plan/wall-clock-rewrite.md) are the shortest
  statement of what any new work must respect. Read before planning anything.
- **One module owns each thing.** Every path in `storage/paths.py`, every folder name in
  `schemas/naming.py`, every route in `layout/routes.ts`, the renderer behind one file. This held
  under heavy change and is the reason the refactor was possible at all.
- **One open item**: the data-safety check dropped as P1.7 with no failing case attached. Nothing
  currently guards the output of a transcription before it is drawn.
- **Silence is not success.** All three bugs above reported nothing rather than failing. A check
  whose output nobody reads is not a check.
- **Report while the work is happening.** See above.

## Where the record is

- [`../plan/checklist.md`](../plan/checklist.md) — every epic, story and task with its final state
- [`README.md`](README.md) — the journal, one report per task
- [`plan-resume/README.md`](plan-resume/README.md) — the month that had no reports, written late
- [`user_review/README.md`](user_review/README.md) — what to open and click, per epic
- [`../../03-time-based-concept/CLOSURE.md`](../../03-time-based-concept/CLOSURE.md) — the refactor,
  why it closed, and what happened next
