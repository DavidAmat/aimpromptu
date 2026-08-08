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
| Layout | `src/aitu_backend/` package; hatchling wheel. Feature packages: `api/`, `matrix/`, `audio/`, `transcription/`, `storage/`, `notation/`, `schemas/` |
| Dependencies | `uv` + `uv.lock`; `uv sync` to install (runtime deps + the `dev` group) |
| Notation logic | Single source of truth: `matrix/text_notation.py` — do not duplicate parsing elsewhere |
| Key tables | Single source of truth: `matrix/keys.py` (88-key order, EN/ES names, MIDI) |
| JSON wire format | camelCase via Pydantic `Field(alias=...)` and `model_config` populate_by_name. Build models with **snake_case kwargs**; camelCase belongs in JSON payloads (the pydantic-mypy plugin rejects alias kwargs) |
| Paths | Centralized in `storage/paths.py`; backend root derived from `__file__`. No path literal elsewhere |
| Folder names | Built by `schemas/naming.py` (`slugify`, `version_folder`, `matrix_filename`) |
| API | One `APIRouter` per section in `api/`; `main.py` is a thin app factory. Endpoints owned by a later epic exist already and answer `501` |
| Progress | Anything >~10 s takes a `ProgressReporter` from `progress.py`; never call `tqdm` directly |
| Docstrings | Module-level and public functions; explain non-obvious domain rules |
| Notebooks | One thematic subfolder per POC under `notebooks/<theme>/` |

Formatting and static checks: **black** (line length 100), **flake8** (`aitu-backend/.flake8`,
ignoring E501/E203/W503), **mypy** (pydantic plugin, permissive on missing imports). Run
`make lint` / `make format` / `make test`; `make hooks` installs the repo-root pre-commit.

## Frontend (TypeScript / React)

| Convention | Detail |
|------------|--------|
| ESLint | Flat config in `eslint.config.js`: recommended JS, typescript-eslint recommended, react-hooks recommended, react-refresh vite preset |
| Ignores | `dist/` globally ignored by ESLint |
| Components | Functional components + hooks; no class components. **MUI** is the component library; layout props go in `sx` (MUI v9 dropped them as direct props) |
| Colors | Only from `src/ui/palette.ts` — no hex literal in a component or stylesheet. Anything that reads *against the page* (backgrounds, rules, label text) comes from `surface`, never a raw `grays.*`: that is what stopped views silently assuming a dark ground |
| Color scheme | The app is **light, always**. `mode: "light"`, plus `color-scheme: light` in `index.css` and a matching `<meta>` in `index.html`, so a dark OS or browser cannot re-tint it. No `prefers-color-scheme` branch anywhere |
| Requests | Only through `src/api/` (one module per backend router); no `fetch` in a component |
| Routes | Only from `src/layout/routes.ts`; no URL literal in a component |
| Music logic | Isolated under `src/music/` (`types`, `notes`, `matrixToNotation`); `types.ts` mirrors the backend `schemas/` and must stay in step with it |
| Rendering | VexFlow isolated in `PianoSheet.tsx` |
| Timestamps | Format only via `src/audio/time.ts` (`mm:ss.cc`, two decimals; a frame prints its **start** only — `f:N · mm:ss.cc`). Style via `timestampSx` / `FRAME_LABEL_WIDTH` in `src/ui/timestamps.ts`; a timestamp must never wrap. See [frontend/timestamps.md](frontend/timestamps.md) |
| Effects | Never call `setState` synchronously in an effect body (ESLint errors); derive state during render instead — see `src/hooks/useProgress.ts` |
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
