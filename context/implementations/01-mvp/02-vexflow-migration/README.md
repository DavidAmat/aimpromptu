# 02 — VexFlow migration

**Opened 2026-07-28. Closed.** The decision and the brief behind our own notation renderer.

Drawing piano sheets with VexFlow meant accepting VexFlow's world: measures, a time signature and
a tempo. We wanted a sheet drawn from a grid of time. So instead of bending VexFlow, we built a
separate package, `@aimpromptu/grid-notation`, in its own repository (`vexflow-v2`), using VexFlow
as a licensed reference rather than as a dependency.

| File | What it is |
|---|---|
| [`01-system-prompt-vexflow-v2.md`](01-system-prompt-vexflow-v2.md) | The full brief given to the agent that built the package: boundaries, licensing, research phase, and the vertical slices |

The package is what draws every sheet the app shows today. The refactor in
[`03-time-based-concept/`](../03-time-based-concept/CLOSURE.md) then took the beat out of it
entirely: no bars, no time signature, no metre, no tempo.
