# Agent prompt — Phase 2 (area: shared / backend / frontend)

Task ID: <FILL ME IN>   (e.g. P2b-1 backend overview, P2c-2 frontend detail)

You own ONE area of **AImpromptu (aitu)**. You produce both the high-level `context/<area>/…` overview
**and** the code-level `documentation/services/<service>/…` detail for that area, cross-linked both ways.

## Read first (in order)
1. `context/archive/docs-migration/project-context.md` — orientation primer.
2. `context/archive/docs-migration/documentation-migration-plan.md` §2, §4, §6 (gap analysis).
3. `context/shared/notation-spec.md` — the shared notation contract. **If your task is P2a you WRITE this
   file first;** everyone else links to it and must not restate it.
4. Your source files (checklist row). Respect line counts. **Never deep-read** notebooks, `data/*.json`,
   lockfiles, `node_modules`, `.venv`.

## Rules (binding)
- **English**; Spanish note names / key labels verbatim; English music terms English.
- **Code-truth wins** — read the implementing code and align docs to it. Named things to get right:
  the **onset normalization rule** (`sequence.py`), the **sparse-COO** field semantics (`schemas.py` /
  `types.ts`), the **beam rule** and **key-signature/accidental** behavior and **dotted-note
  decomposition** and **two-hand grand-staff wrap** (`matrixToNotation.ts`, `PianoSheet.tsx`), the
  **endpoints + 422 cases** (`main.py`).
- `context/<area>/<entity>.md` ≤ **~200 lines**; overflow detail → `documentation/`.
- **Cross-link both ways:** each `context/` overview ends with "Where to look deeper" → its
  `documentation/` detail + sibling entities; each `documentation/` file opens with `> Context:` up-link
  to its overview and, where relevant, to `context/shared/notation-spec.md`.
- Frontend: structure `context/frontend/` **by UI area** (app-shell, loaded-scores, compose-panel,
  rendering-pipeline) per plan Appendix-C guidance, not by file.
- **No secrets; no emojis; terse.**
- **Never change application code.** Docs (markdown) only.

## Migrate legacy sources
- The two subrepo READMEs are consumed *by reference* (verify vs code), then rewritten as short pointer
  READMEs (tasks P2b-3 / P2c-4) — no duplicated spec, just links into the new tree.
- `aitu-frontend/documentation/vexflow/README.md` → copy to `documentation/archive/vexflow-reference.md`,
  then `git rm` the original **in the frontend subrepo** (cross-git boundary: history won't follow; that's
  expected). Log it.

## Wrap up
1. Update `context/00-index.md` with one line per new file.
2. If you learned a platform-level fact, add one sentence to the matching `context/0X-*.md` + the index.
3. Append every consumed/moved/deleted source to `deletions-log.md` in the required shape.
4. Flip your checklist rows to `[x]` (or `[!]` + reason).
5. Final reply: files written, cross-links added, any open question + the safe default taken.
