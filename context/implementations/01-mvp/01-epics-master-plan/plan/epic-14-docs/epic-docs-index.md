# Epic 14 — Final documentation

> **Complete 2026-09-13.** Report:
> [`../../progress/epic-14/task-14.1.1-progress.md`](../../progress/epic-14/task-14.1.1-progress.md).
>
> *Rewritten 2026-08-12 for the wall-clock model; the epic was unchanged in nature and larger in
> scope. See [`../wall-clock-rewrite.md`](../wall-clock-rewrite.md).*

Always last. While work is in progress only `context/` and the progress journal are kept current;
when the product is stable, `documentation/` is brought in line with the code, per
`context/00-documentation-instructions.md`.

Two things make this bigger than it was: the wall-clock model replaced most of what the older
documents describe, and the work done after the time-based plan closed has no reports at all.

## Story 14.1 — Documentation pass

- [x] Task 14.1.1 final documentation: rewrite the detail tree, refresh the context overviews, close
  the journal.
- [x] Task 14.1.2 fix the three defects that pass found.

## Exit criteria — met

> *A new reader can start at `context/00-project-complete-overview.md` and reach accurate detail
> files, and no document describes a screen or a concept the app no longer has.*

The overview was rewritten for the wall-clock app and now sends a reader to
[`context/backend/time-model.md`](../../../../backend/time-model.md) second, because everything else
assumes it. Every relative link in `context/` and `documentation/` resolves — 291 files checked, 27
broken found, zero left. Four banner-marked documents were resolved rather than left banner-marked:
two archived with a README mapping each to where its truth went, two rewritten to say what they now
cover.

**Three defects were found** by reading the documents against the code — `make test` did not run at
all, octave brackets were saved and silently dropped, and `npm run check:render` had been broken
since P6.9. Task 14.1.1 recorded them rather than fixing them, since a documentation pass does not
change application code; **all three were then fixed the same day** in
[`../../progress/epic-14/task-14.1.2-progress.md`](../../progress/epic-14/task-14.1.2-progress.md).
