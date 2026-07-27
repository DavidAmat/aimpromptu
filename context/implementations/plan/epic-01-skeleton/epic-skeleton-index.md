# Epic 1 — Skeleton

Set the structural foundation so every later epic only fills code into an already-designed shape. The project already exists (`aitu-backend`, `aitu-frontend`) with a single MVP page that renders text notation as sheet music; keep what is useful, restructure the rest.

Read first: `context/00-project-complete-overview.md`, `context/02-tech-stack.md`, `context/09-coding-conventions.md`.

## Story 1.1 — Backend skeleton

- Task 1.1.1 backend restructure: module layout (`matrix/`, `audio/`, `transcription/`, `storage/`, `notation/`, `api/`), migrate the existing `sequence.py` logic, FastAPI routers.
- Task 1.1.2 backend tooling: pre-commit with `black`, `flake8`, `mypy`; `tqdm` progress convention; Makefile targets.

## Story 1.2 — Frontend skeleton

- Task 1.2.1 app shell and navigation: sections (YouTube to Audio, Playground with its tabs, Piano Library), routing, typed API client, progress streaming plumbing.
- Task 1.2.2 UI kit and theme: MUI + MUI X as the standard component library, brand color palette as a `.ts` module.

## Story 1.3 — Shared contracts

- Task 1.3.1 matrix schemas: Pydantic + TS types for the piano matrix (sparse COO, processing step, hands), dense and sparse JSON export shapes.
- Task 1.3.2 metadata schemas: audio metadata (including persisted-segment lineage),
  `metadata.json`, `metadata_track.json`, `metadata_library_track.json`, slugs, granularity codes,
  version codes.

## Story 1.4 — Storage skeleton

- Task 1.4.1 storage layout: `aitu-backend/data/` tree (`playground/`, `library/`, `audio/`), uuid working folders, gitignore policy for heavy files, `paths.py` helpers.

## Exit criteria

Both services run locally with the new navigation shell, empty-but-wired endpoints, contracts importable from both sides, storage folders created on startup, pre-commit green.
