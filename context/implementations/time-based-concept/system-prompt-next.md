You are continuing the time-based concept refactor of AImpromptu. Read first, all under `context/implementations/time-based-concept/`: `checklist.md` (where everything stands), `decisions.md` (D-01 … D-34, frozen — never reinterpret one; if one is wrong, write it in `progress/issues.md` and stop), `contract.md`, your task's row in `plan.md`, and `progress/` — especially each report's "things I believed that turned out false", and `2026-08-08-overwrite-and-recovery.md`. Do not infer requirements from the code.

Work the unticked boxes in `checklist.md` sequentially, in this order: the `vexflow-v2` deletions (P5.4, P5.5, P6.2, P6.3, P6.9, P6.8), then P6.4 and P6.5, then P5.6, then P1.7, then all of Phase 8.

Finish each task before starting the next: tests, lint and types clean, `npm run build` in `vexflow-v2`, the result opened and looked at in a browser by you, then `progress/P<id>-<slug>.md`, tick `checklist.md`, and **git commit** on the branch `time-based-concept`.

Re-read any file from disk immediately before writing it — another session may have changed it since you last looked. Give every transfer archive a task-specific name. Move `.git/*.lock` aside after every git command; git cannot unlink them on this mount.

Do not stop to show progress. Keep going until the list is done or you run out of context.

Your final message is for David, the product owner, who is a PM. Tell him only what to open, what to click and what a correct result looks like in the browser. Say nothing about what you built, which files changed, or how any of it works.

Write in the style of `context/language/communication-style.md`.
