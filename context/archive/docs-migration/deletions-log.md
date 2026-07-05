# Deletions & moves log (append-only)

One bullet per legacy file **deleted** or **moved** to `archive/`/`deprecated/`. Shape:

`` - `<source>` → `<destination or "deleted">` (task `<ID>`) — <one-line reason>. ``

- `context/archive/docs-migration/00-project-complete-overview.draft.md` → `context/00-project-complete-overview.md` (task `P1-3`) — kit draft promoted to active platform overview.
- `docs-migration.md` → `context/archive/docs-migration/docs-migration.md` (task `P0-7`) — original system prompt kept as historical record.

<!-- Expected entries once later phases run: -->
<!--
- `aitu-frontend/documentation/vexflow/README.md` → `documentation/archive/vexflow-reference.md` (task `P2c-3`) — legacy VexFlow reference; cross-git copy, original git rm'd in the frontend subrepo.
- `aitu-backend/README.md` → rewritten as pointer (task `P2b-3`) — spec content consumed into context/backend/ + documentation/services/backend/.
- `aitu-frontend/README.md` → rewritten as pointer (task `P2c-4`) — spec content consumed into context/frontend/ + documentation/services/frontend/.
-->
