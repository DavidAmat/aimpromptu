# Progress reports — time-based concept

One report per task, **including tasks executed inside `vexflow-v2`**. That repository has its own
`progress/` folder; do not use it for this work. Everything about this refactor is tracked here so
the two-package order stays visible in one place.

## Naming

```
P<phase>.<task>-<slug>.md      e.g. P5.2-silence-compression.md
```

Special files:

| File | What goes in it |
|---|---|
| `issues.md` | Anything that contradicts a decision in `../decisions.md`. Append, never overwrite. |
| `P4.1-artifact-inventory.md` | Required before Phase 4 touches storage. |
| `P8.1-success-criteria.md` | One entry per criterion in `../PRD.md` §5. |

## What a report contains

1. **Task and decisions** — the id, and which `D-nn` it implements.
2. **What was built** — files added, changed, deleted. Paths, not prose.
3. **Decisions taken inside the task** — the small ones the plan left open, and why.
4. **Things believed that turned out false** — the most valuable section. Write it even when short.
5. **Tests** — what was added, what passes, what was deleted and why.
6. **`## Cross-repo change`** — only when you edited the repo your assignment did not name. Which
   repo, which files, why staying in yours was not enough. If the interface moved, `contract.md`
   must have been updated in the same task.
7. **Left open** — anything the next task inherits.

## Before you close a task

- Tick it in [`../checklist.md`](../checklist.md).
- If you worked in `vexflow-v2`, come back to `aimpromptu/` to do that.
- If something contradicted a decision, add it to `issues.md` and **stop** — do not reinterpret a
  `D-nn` on your own.
