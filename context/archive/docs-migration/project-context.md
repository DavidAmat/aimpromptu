# project-context.md — orientation primer for migration agents

Read this before touching anything. It saves you rediscovering the repo. ~150 lines.

## What AImpromptu (aitu) is

A two-service POC that turns a **custom text music notation** into rendered **sheet music**.

- **aitu-backend** (Python/FastAPI, module `aitu_backend`) — parses the notation, emits a compact
  sparse JSON score. Knows nothing about VexFlow or visual rendering.
- **aitu-frontend** (React 19 + TS + Vite + VexFlow 5) — consumes the JSON and does ALL rendering.

> Historical note: these were `piano-matrix-generation` and `piano-matrix-notation`; the workspace was
> `music-rendering`. The docs migration renames them (Phase 0). If you still see the old names in live
> code, Phase 0 hasn't run yet — do not "fix" them ad hoc; follow the checklist.

## Where the code lives

```
aitu-backend/
  src/aitu_backend/
    sequence.py   # 178 ln — SINGLE SOURCE OF TRUTH for notation logic:
                  #   text parsing (* onsets), onset-normalization rule, sparse-COO builder
    schemas.py    #  95 ln — Pydantic models: SparseMatrix, MatrixScore, SequenceRequest (camelCase JSON)
    main.py       # 105 ln — FastAPI app: GET /health, GET /scores, POST /sequence
    paths.py      #  12 ln — resolves data/example-scores.json
    __init__.py
  data/example-scores.json   # sample served by GET /scores (untracked)
  notebooks/<theme>/*.ipynb  # interactive demos, one thematic subfolder per POC — DO NOT deep-read; one-line mention only
  Makefile        # `make serve` → uv run python -m uvicorn aitu_backend.main:app --host 127.0.0.1 --port 8765 --reload
  pyproject.toml  # uv-managed; Python >=3.12.13,<3.13; hatchling build
aitu-frontend/
  src/
    music/
      types.ts            #  64 ln — SparseMatrix, MatrixScore, NoteEvent, VexPiece
      notes.ts            # 109 ln — 88-key row builder, Spanish→VexFlow map, KEY_SIGNATURES table
      matrixToNotation.ts # 251 ln — pipeline: sparse decode → note events → durations/dots → chord/rest timeline;
                          #          sparseToVexPieces (per clef), sliceMatrixColumns (two-hand aligned wrap)
    components/
      PianoSheet.tsx       # 382 ln — VexFlow rendering: staves, beam rule, accidentals, dots, lyrics, wrap, grand staff
      SequenceComposer.tsx # 254 ln — compose panel; POST /sequence (uncommitted/new)
      LayoutControls.tsx   # 109 ln — spacing / lyrics inputs (reused)
      ScoreStack.tsx       #  27 ln — lists loaded scores
    App.tsx                #  97 ln — fetch GET /scores, global layout state, mounts panels
    vite-env.d.ts          # env typing: VITE_AITU_API_URL (renamed from VITE_MATRIX_API_URL)
  documentation/vexflow/README.md  # 150 ln — legacy VexFlow reference → migrate to documentation/archive/
  package.json             # react 19, vexflow 5, vite 8, typescript ~6
```

## The domain model (learn this once)

**Text notation** — one line per **time frame**:
- `*Note` = **onset** (key struck), e.g. `*Do-4`. `Note` (no `*`) = **sustain** (still sounding, not re-struck).
- `A || B` = simultaneous notes in one frame (chord). Blank line = silent frame.
- Note names: **Spanish solfège + scientific octave** — `Do-4`=C4, `La-0`=A0 (lowest key), `Do-8`=C8
  (highest). 88-key canonical row order rebuilt on both sides. **Keep these names verbatim in all docs.**

**Onset rule (the subtle part):** a sustain continues only through frames with **no** new onset. The
moment any frame has an onset, every carried sustain ends at the previous frame. The builder normalizes
illegal input (sustain colliding with a foreign onset → sustain ends; a sustain with nothing to continue
→ promoted to onset). This is what disambiguates four `Re-4` cells: 4 onsets = 4 notes; 1 onset + 3
sustains = one long note.

**Sparse-COO payload:** a dense 88×N matrix is mostly zeros, so the score ships parallel arrays sorted by
`(col, row)`: `rows`/`cols` mark active cells, `onset[i]` = `rows[i]` for a struck onset or `-1` for a
sustain. The index→note table is intentionally omitted; the frontend rebuilds it. Optional: `lyrics`
(one entry per frame, time-indexed — drawn even over sustains/silences), `keySignature` (VexFlow spec like
`C`, `G`, `Bb`).

**One vs two hands:** a score is either **one hand** (`matrix`, treble clef) or **two hands** (`r_matrix`
right/treble + `l_matrix` left/**bass clef**), mutually exclusive. Both matrices must span the **same
number of time frames** (`shape[1]` equal) so the hands stay vertically aligned. Two-hand renders as a
braced grand staff. Text notation for two hands uses `__` to separate right (before) from left (after) on
a line; no `__` on a line = left hand silent that frame. Two-hand support is **in progress** in the
working tree (see `TODO.md`) — document the working-tree behavior; verify against code.

**Frontend rendering nuances (verify against `PianoSheet.tsx` / `matrixToNotation.ts`):**
- Durations: `durationBeats = steps * timeStepSeconds / (60 / tempoBpm)`; a held note is the fewest
  symbols, preferring one (optionally dotted) note; off-grid values snapped with a console warning.
- Beams: VexFlow's tick-based `generateBeams` is **not** used (barless soft voice). Instead beam every
  maximal run of ≥2 consecutive beamable notes (eighth or shorter, non-rest); a lone eighth keeps its flag.
- Key signatures: accidental is baked into the pitch (`Fa#-5`→`f#/5`); VexFlow's `applyAccidentals`
  decides the glyph vs the chosen key (e.g. `Fa#-5` in Sol-Mayor shows no sharp; in Do-Mayor it does).
- Barless layout: no bar lines / time signature; soft voice; key signature repeats each line; one-hand
  wraps by note count, two-hand wraps by time window (same column slice for both hands).

## API surface (verify against `main.py`)

- `GET /health` — liveness.
- `GET /scores` — reads `data/example-scores.json`.
- `POST /sequence` — body: `sequence` (text) + `tempoBpm`, `timeStepSeconds`, optional `title`, `lyrics`,
  `keySignature`, optional `leftSequence` (bass-clef left hand; must match `sequence` frame count).
  Returns the same shape as `/scores` items. Unknown notes / mismatched hands → **422**.

## How to run (verify against Makefiles)

- Backend: `cd aitu-backend && uv sync && make serve` → uvicorn on `127.0.0.1:8765`, docs at `/docs`.
  Use `python -m uvicorn` (the Makefile does) — long repo paths can truncate the console-script shebang.
- Frontend: `cd aitu-frontend && npm install && npm run dev` → expects backend at `http://127.0.0.1:8765`;
  `VITE_AITU_API_URL` overrides it (renamed from `VITE_MATRIX_API_URL`; not set in any `.env` today).

## Tech stack (locked — read lockfiles for exact pins)

- Backend: Python 3.12.13–3.12.x, FastAPI ≥0.115, uvicorn[standard] ≥0.32, Pydantic ≥2.9, numpy ≥2.4,
  scipy ≥1.17; hatchling build; `uv` + `uv.lock`; jupyter/ipykernel for notebooks.
- Frontend: React 19.2, react-dom 19.2, VexFlow 5, Vite 8, TypeScript ~6, ESLint 10 (`eslint.config.js`,
  flat config with typescript-eslint + react-hooks + react-refresh).

## Conventions to reflect (ground in configs, don't invent)

- Backend: `src/` layout, single-source-of-truth module (`sequence.py`), camelCase JSON via Pydantic
  aliases, terse docstrings, path resolution centralized in `paths.py`.
- Frontend: functional React + hooks, TS strict-ish, ESLint flat config; music logic isolated under
  `src/music/`, rendering isolated in `PianoSheet.tsx`. The READMEs are unusually detailed and note
  "nuances we got wrong before" — preserve that hard-won knowledge; don't flatten it.

## Traps

- Do **not** deep-read notebooks or `data/example-scores.json` (context bloat) — one-line mentions.
- The two subrepos have their **own git**; the root umbrella git is new. Moving files from a subrepo into
  root docs crosses git boundaries — history won't follow; copy + `git rm`, and log it.
- Both subrepos have **uncommitted** work; document the working tree, not `HEAD`.
- The notation contract is **shared** — write it once in `context/shared/notation-spec.md`; link, don't copy.
