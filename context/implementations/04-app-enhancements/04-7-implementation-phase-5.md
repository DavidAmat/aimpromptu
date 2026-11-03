# 04-7 Phase 5: The docs and the closing

Plan [`04-7-plan.md`](04-7-plan.md) sections 4.6, 4.7 and 5; checklist [`04-7-checklist.md`](04-7-checklist.md).
Branch `feat/04-7-open-points`. 2026-11-03. Done in the same session as Phases 3 and 4 (the plan allows 4 and 5
together).

State: done (2026-11-03). The user rebuilt the image; 04 is closed.

# 1. The six points of 04 (plan section 1)

| # | Point | How it ended |
|---|---|---|
| 1 | The clef of the left hand | The rule of 5 columns, 8va in the bass clef and 8vb in the treble clef, on every drawn sheet; measured, shown, the user's ok (Phases 2 and 3) |
| 2 | Hard and the figure check | Hard refuses figures shorter than a fusa; a decoration note is left out (Phase 4) |
| 3 | A Stop keeps the batches it accepted | Kept; a comment and the docs (Phases 4 and 5) |
| 4 | The temporary copies of 20 de Enero | Six TEMP projects deleted (Phase 1) |
| 5 | The octaves of the user's words | Closed in 8.5, no code (Phase 1) |
| 6 | From 04-6 | The Transkun tests pass on the CPU (Phase 1); **the image rebuild is the user's** (section 3) |

# 2. The docs changed

| Doc | What |
|---|---|
| `aitu-backend/src/aitu_backend/sheet/README.md` | section 9: the clef rule of 04-7 (`CLEF_MIN`, the states, `short_clefs` on every drawn sheet, `clefset`, `_grace_lines`, the study); `frames.check` and the AI's check (15ma refused, 8va allowed); what the LLM decides; `fit_clefs` |
| `context/ai/stretch.md` | the hard limits: no 15ma in the bass clef, 8va allowed, the shortest stretch drawn by the app |
| `context/frontend/annotations-stretches.md` | the Octave chips: 8va in the bass clef, 15ma off there; a clef set with the Clef chips is kept |
| `context/ai/level-run.md` | Stop keeps the batches, Revert takes the run back; Hard's shortest figure and the decoration-note exception; a row in the table of the limits |
| `context/ai/run-history.md` | a `stopped` run keeps its batches; Revert |
| `documentation/services/backend/ai-levels.md` | the shortest figure in the list of the checks |
| `04-context.md` | 8.5 (Hard, Stop, the copies) and 9.3 (Transkun) closed; section 10 for 04-7 |
| `../03-apply-poc-research/03-context.md` | section 2's row of the clef rules: changed by 04-7 |
| `04-5-checklist.md` | the clef line done, with a link |

`python3 scripts/docs/check-links.py`: 562 files, 0 broken links. `scripts/docs/check-names.py` on the ten docs: the
names it does not find are branch names and the history of removed code (Simplify), there before 04-7.

The state lines of [`README.md`](README.md), [`../README.md`](../README.md) and [`../../00-index.md`](../../00-index.md)
say 04 is closed, written after the image was rebuilt and checked (section 3).

# 3. The image

Checked on 2026-11-03: the image `aimpromptu-backend:dev` (`000e5ad1e0f3`, built 2026-10-25) has no `openai`
(`docker run --rm --entrypoint python aimpromptu-backend:dev -c "import openai"`: `ModuleNotFoundError`). The running
container has it installed by hand, so the app works today; a new container from the image would not run an AI
request. The rebuild restarts the backend (a running AI run stops), so the user runs it when the app is idle:

```sh
cd /home/david/Documents/projects/music/aimpromptu
docker compose build backend
docker compose up -d backend
```

After the user's word, the agent: `docker run --rm --entrypoint python aimpromptu-backend:dev -c "import openai"`
prints no error; `docker logs aimpromptu-backend-1` shows the startup; 9.3's line closed in `04-context.md` (and 10.4);
checklist 5.5; the state lines of the three READMEs: 04 closed.

# 4. What is left after 04

- Merge `feat/04-7-open-points` into `master` at the user's ok (no PR).
- 04-4 ("Copy this style") is a later implementation plan.

# 5. After the rebuild (2026-11-03)

- The user ran the rebuild. Image `aimpromptu-backend:dev` `66186ec78869` (2026-11-03 14:17); `docker run --rm
  --entrypoint python aimpromptu-backend:dev -c "import openai"`: openai 3.41.0.
- The backend runs from the new image: "Application startup complete", `/health` 200.
- The whole backend suite on the CPU in the new container: **1367 passed, 1 skipped, 0 failed**.

