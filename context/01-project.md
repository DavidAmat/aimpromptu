# Project

## Name

**AImpromptu** (short: **aitu**). Two-service POC for custom piano notation → sheet music.

## What it does

A user writes music in a line-per-time-frame text notation using Spanish solfège. The backend converts
that text into a compact sparse JSON score. The frontend renders that JSON as conventional sheet music
with VexFlow — including beams, dotted notes, key signatures, lyrics, one-hand treble, and two-hand
braced grand staff.

The backend is **notation-agnostic**: it emits no VexFlow or visual markup. The frontend owns **all**
rendering decisions.

## Who uses it

Developers and musicians experimenting with a custom solfège-based input format for piano. Intended as a
local development POC, not a production product. No end-user auth, accounts, or hosted deployment yet.

## Problem domain

Standard music notation tools expect MIDI, MusicXML, or staff entry. This project explores an alternative:

1. **Text input** — one line per time frame, `*` for onsets, `||` for chords, Spanish note names with
   scientific octave (`Do-4`, `Fa#-5`, `La-0` … `Do-8` over 88 keys).
2. **Sparse matrix transport** — a dense 88×N piano matrix is mostly zeros; the wire format is COO arrays
   (`rows`, `cols`, `onset`) plus optional `lyrics` and `keySignature`.
3. **Barless rendering** — no measures or time signatures; durations derived from tempo and time-step;
   custom beam rules for a soft voice layout.

Two-hand piano (treble + bass clef, aligned frames) is supported via `leftSequence` on `POST /sequence`;
see [shared/notation-spec.md](shared/notation-spec.md).

## Repository layout

**Monorepo (POC).** Single git root at `aimpromptu/`. Deployable services live as folders; they are not
nested git repos. Documentation lives alongside code in `context/` and `documentation/`.

| Path | Role |
|------|------|
| `aitu-backend/` | Python/FastAPI service |
| `aitu-frontend/` | React/TS/Vite app |
| `context/` + `documentation/` | Platform and code-level docs |

**Future direction:** package `aitu-backend` and `aitu-frontend` as separate Docker containers with clearer
module boundaries. That modularization is planned, not built yet.

Historical folder names: `piano-matrix-generation`, `piano-matrix-notation`, workspace `music-rendering`
(now `aimpromptu`). Phase 0 renamed services to `aitu-*`.

## Planned scope (implementation plan)

Beyond the text-notation MVP, the project is planned end-to-end in
[implementations/plan/](implementations/plan/README.md): audio ingestion (upload / mic recording /
YouTube), automatic piano transcription into the 0/1/-1 matrix format with granularity collapsing
and cleaning, a Playground (matrix grid, piano-roll and notes-falling visualizations, VexFlow
notation with engraving rules), versioned artifact storage with promotion to a performer Library
with playlists, and passage re-recording/editing. See
[implementations/plan/checklist.md](implementations/plan/checklist.md) for status.

## POC boundaries (out of scope for now)

- Cloud hosting, CI/CD deploy, Docker images / container orchestration
- Database or persistent user scores (sample file only)
- Authentication, secrets management, network hardening
- AI / LLM features

See [05-deployment.md](05-deployment.md) (stub) and skipped platform files noted in [00-index.md](00-index.md).

## Where to look deeper

- Complete orientation: [00-project-complete-overview.md](00-project-complete-overview.md)
- Services and ports: [03-services-overview.md](03-services-overview.md)
- Notation contract: [shared/notation-spec.md](shared/notation-spec.md)
- Backend overview: [backend/README.md](backend/README.md)
- Frontend overview: [frontend/README.md](frontend/README.md)
