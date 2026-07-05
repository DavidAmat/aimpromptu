# AImpromptu (aitu) — Complete Project Overview

One-shot orientation. Paste this alone to get the whole project.

## What it is

AImpromptu turns a **custom text music notation** into rendered **sheet music**. Two services in one
**monorepo** (single git root; POC — future Docker packaging planned, not built yet):

- **aitu-backend** — Python 3.12 / FastAPI (`uv`, hatchling, module `aitu_backend`). Parses the notation
  and emits a compact **sparse-COO JSON score**. Deliberately notation-agnostic: it never emits VexFlow.
- **aitu-frontend** — React 19 + TypeScript + Vite 8 + **VexFlow 5**. Consumes the JSON and does **all**
  music rendering (staves, beams, dotted notes, key signatures, lyrics, one-hand treble, two-hand grand staff).

Status: **POC, local-only.** No cloud, deploy pipeline, database, auth, or AI. A single
`aitu-backend/data/example-scores.json` file backs `GET /scores`.

## The notation (shared contract — full detail in `context/shared/notation-spec.md`)

One line per **time frame**. `*Note` = onset (struck), `Note` = sustain, `A || B` = chord, blank = silence.
Names are **Spanish solfège + scientific octave** (`Do-4`=C4 … `La-0`=A0 lowest, `Do-8`=C8 highest), over
the canonical 88-key order rebuilt on both sides.

**Onset rule:** a sustain continues only through frames with no new onset; the first frame with any onset
ends all carried sustains at the previous frame. This disambiguates repeated cells (4 `Re-4` onsets = 4
notes; 1 onset + 3 sustains = one long note). Illegal input is normalized.

**Sparse-COO payload:** parallel arrays sorted by `(col,row)` — `rows`/`cols` mark active cells,
`onset[i]` = `rows[i]` (struck) or `-1` (sustain). Optional `lyrics` (time-frame-indexed; drawn even on
sustains/silences) and `keySignature` (VexFlow spec, e.g. `C`, `G`, `Bb`).

**One vs two hands:** either one `matrix` (treble) or `r_matrix` (treble) + `l_matrix` (bass), mutually
exclusive, with **equal frame counts** so hands align; two hands render as a braced grand staff.
`POST /sequence` takes separate `sequence` (right/treble) and optional `leftSequence` (left/bass) arrays.

## Flow

```
text notation ──POST /sequence──▶ aitu-backend (sequence.py: parse → onset-normalize → sparse-COO)
                                          │  JSON score (rows/cols/onset [+lyrics,+keySignature])
                                          ▼
aitu-frontend (matrixToNotation.ts: decode → note events → durations/dots → chord/rest timeline)
   └─▶ PianoSheet.tsx (VexFlow): staves, beams, accidentals vs key, dots, lyrics, line wrap, grand staff
GET /scores ──▶ example-scores.json ──▶ same rendering path
```

## Rendering nuances (code-truth; see `documentation/services/frontend/`)

- `durationBeats = steps * timeStepSeconds / (60 / tempoBpm)`; held note = fewest symbols (prefer one,
  optionally dotted); off-grid snapped with a console warning.
- Beams: VexFlow's tick-based `generateBeams` is NOT used (barless soft voice); beam every maximal run of
  ≥2 consecutive beamable notes (eighth-or-shorter, non-rest); lone eighth keeps its flag.
- Key signatures: accidental baked into the pitch (`Fa#-5`→`f#/5`); VexFlow's `applyAccidentals` decides
  the visible glyph vs the chosen key (e.g. `Fa#-5` shows no sharp in Sol-Mayor, does in Do-Mayor).
- Barless layout: no bar lines / time signature; key signature repeats each line; one-hand wraps by note
  count, two-hand wraps by aligned time-window column slices.

## API

- `GET /health` — liveness.
- `GET /scores` — serves `data/example-scores.json`.
- `POST /sequence` — `sequence` (text) + `tempoBpm`, `timeStepSeconds`, optional `title`/`lyrics`/
  `keySignature`/`leftSequence` (bass-clef left hand, matching frame count). Unknown notes / mismatched
  hands → `422`. Returns a score matching `/scores` items.

## Run locally

- Backend: `cd aitu-backend && uv sync && make serve` → uvicorn `127.0.0.1:8765`, docs `/docs`.
- Frontend: `cd aitu-frontend && npm install && npm run dev` → expects backend at `http://127.0.0.1:8765`
  (override via `VITE_AITU_API_URL`).

## Code map

- Backend: `sequence.py` (notation logic — single source of truth), `schemas.py` (Pydantic, camelCase),
  `main.py` (endpoints), `paths.py`, `data/example-scores.json`, `notebooks/<theme>/` (demos, one folder per POC).
- Frontend: `src/music/{types,notes,matrixToNotation}.ts`, `src/components/{PianoSheet,SequenceComposer,
  LayoutControls,ScoreStack}.tsx`, `src/App.tsx`.

## Conventions

- Backend: `src/` layout, notation logic centralized in `sequence.py`, camelCase JSON via Pydantic aliases,
  paths centralized in `paths.py`, `uv` + `uv.lock`.
- Frontend: functional React + hooks, ESLint flat config (typescript-eslint + react-hooks + react-refresh),
  music logic isolated under `src/music/`, rendering isolated in `PianoSheet.tsx`.

## Where to look next

- Platform: [01-project.md](01-project.md), [02-tech-stack.md](02-tech-stack.md), [04-local-development.md](04-local-development.md)
- Notation contract: [shared/notation-spec.md](shared/notation-spec.md)
- Backend overview: [backend/README.md](backend/README.md) · detail: [../documentation/services/backend/](../documentation/services/backend/)
- Frontend overview: [frontend/README.md](frontend/README.md) · detail: [../documentation/services/frontend/](../documentation/services/frontend/)
- Full index: [00-index.md](00-index.md)
