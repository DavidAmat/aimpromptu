# Coding conventions

Grounded in existing configs and visible patterns across the codebase. Do not invent rules not reflected here.

## General

- **English** for code, comments, and docs output.
- **Spanish solfège** in notation strings and key labels where they match code (`Do`, `Re`, `Mi`, `Fa#`, `La#`, `Sol`, `Si`).
- **English music terms** in code comments and docs (`onset`, `sustain`, `treble`, `beam`, etc.).
- Terse, factual docstrings and README prose — preserve "nuances we got wrong before" notes from legacy READMEs when migrating detail.

## Backend (Python)

| Convention | Detail |
|------------|--------|
| Layout | `src/aitu_backend/` package; hatchling wheel |
| Dependencies | `uv` + `uv.lock`; `uv sync` to install |
| Notation logic | Single source of truth: `sequence.py` — do not duplicate parsing elsewhere |
| JSON wire format | camelCase via Pydantic `Field(alias=...)` and `model_config` populate_by_name |
| Paths | Centralized in `paths.py`; repo root derived from `__file__` |
| API | FastAPI route handlers in `main.py`; thin — delegate to `sequence.py` |
| Docstrings | Module-level and public functions; explain non-obvious domain rules |
| Notebooks | One thematic subfolder per POC under `notebooks/<theme>/` |

No enforced formatter config (no ruff/black in pyproject today). Match existing file style.

## Frontend (TypeScript / React)

| Convention | Detail |
|------------|--------|
| ESLint | Flat config in `eslint.config.js`: recommended JS, typescript-eslint recommended, react-hooks recommended, react-refresh vite preset |
| Ignores | `dist/` globally ignored by ESLint |
| Components | Functional components + hooks; no class components |
| Music logic | Isolated under `src/music/` (`types`, `notes`, `matrixToNotation`) |
| Rendering | VexFlow isolated in `PianoSheet.tsx` |
| Env vars | Typed in `vite-env.d.ts`; `VITE_*` prefix for client exposure |
| Strictness | TypeScript project references (`tsc -b` before vite build) |

Run `npm run lint` before committing frontend changes.

## Cross-service

| Convention | Detail |
|------------|--------|
| Score JSON | camelCase field names on the wire |
| Notation contract | Document once in `context/music/notation-logic/02-notation-spec.md.md`; link, do not copy |
| API docs | Backend OpenAPI at `/docs` when server is running |

## Documentation work

- Markdown only during migration (except Phase 0 rename).
- `context/<area>/*.md` ≤ ~200 lines; overflow to `documentation/`.
- Cross-link overviews down and detail files up (`> Context:`).
- Update [00-index.md](00-index.md) when adding files.

## LLM agent config (`.claude/`)

Root `.claude/` is **gitignored** today (see root `.gitignore`). Local inventory as of migration:

| Path | Contents |
|------|----------|
| `.claude/settings.local.json` | Bash permission allowlist only: `npx tsc *`, `npx --yes tsx -e ' *`, `npm run *` |

**Not present:** slash-commands, project skills, or agent definitions under `.claude/`.

### Recommended commands (not built — add if repeatability matters)

| Command | Purpose |
|---------|---------|
| `/start-local` | Run `uv sync && make serve` in `aitu-backend` and `npm run dev` in `aitu-frontend` (two terminals or a small script). |
| `/lint-frontend` | `cd aitu-frontend && npm run lint` |
| `/verify-backend` | `cd aitu-backend && uv sync && curl -s http://127.0.0.1:8765/health` |

### Recommended skills (not built)

| Skill topic | When to activate |
|-------------|------------------|
| Notation contract | Editing parsing or rendering — point at `context/music/notation-logic/02-notation-spec.md.md` |
| VexFlow rendering | Changes to `PianoSheet.tsx` or duration/beam logic |
| uv / FastAPI | Backend dependency or endpoint work |

To version-control agent config, remove `.claude/` from `.gitignore` and commit only non-secret files (`settings.json`, commands, skills).

## Where to look deeper

- ESLint config: `aitu-frontend/eslint.config.js`
- Backend models: [../documentation/services/backend/schemas.md](../documentation/services/backend/schemas.md)
- Doc placement: [00-documentation-instructions.md](00-documentation-instructions.md)
