# Tech stack

Locked versions from lockfiles. Re-read `uv.lock` and `package-lock.json` when upgrading.

## Backend (`aitu-backend/`)

| Item | Version / constraint |
|------|----------------------|
| Python | 3.12.13 (`.python-version`); `requires-python >=3.12.13,<3.13` |
| Package manager | `uv` + `uv.lock` |
| Build | hatchling; wheel/sdist package `src/aitu_backend` |
| Web | FastAPI 0.136.1, uvicorn[standard] 0.47.0 |
| Validation | Pydantic 2.13.4 |
| Numerics | numpy 2.4.5, scipy 1.17.1 |
| Notebooks | ipykernel 7.2.0, jupyterlab 4.5.7, ipywidgets (dev/exploratory) |

Runtime entry: `uv run python -m uvicorn aitu_backend.main:app` (see `Makefile`).

## Frontend (`aitu-frontend/`)

| Item | Version / constraint |
|------|----------------------|
| Runtime | React 19.2.6, react-dom 19.2.6 |
| Language | TypeScript 6.0.3 |
| Bundler | Vite 8.0.13, `@vitejs/plugin-react` 6.0.1 |
| Notation | VexFlow 5.0.0 |
| Lint | ESLint 10.4.0 flat config: `@eslint/js`, `typescript-eslint` 8.x, `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`, `globals` |

Scripts: `npm run dev` (vite), `npm run build` (`tsc -b && vite build`), `npm run lint`, `npm run preview`.

## Cross-service

| Item | Value |
|------|-------|
| API default | `http://127.0.0.1:8765` |
| Frontend override env | `VITE_AITU_API_URL` (no trailing slash) |
| JSON field casing | camelCase on the wire (Pydantic aliases on backend; TS types on frontend) |
| CORS | Backend allows all origins (`*`) for local POC |

## Not used (POC)

- Docker / docker-compose
- Cloud provider SDKs
- SQL/NoSQL database drivers
- Auth libraries (OAuth, JWT, etc.)

## Where to look deeper

- Run commands: [04-local-development.md](04-local-development.md)
- Service roles: [03-services-overview.md](03-services-overview.md)
- Coding style: [09-coding-conventions.md](09-coding-conventions.md)
- Locked dependency detail: `aitu-backend/uv.lock`, `aitu-frontend/package-lock.json`
