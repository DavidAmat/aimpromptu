# AImpromptu (aitu)

**Piano recordings → clear, responsive HTML sheet music** — built for musicians and developers who want readable notation without PDF clutter.

Current POC: write music in **Spanish solfège text notation**, get a sparse JSON score from the backend, and render professional sheet music in the browser with VexFlow. Long-term goal: ingest YouTube URLs or audio uploads and produce the same responsive HTML score.

## Who it's for

- **Musicians** experimenting with solfège-based input and minimalist, barless layouts.
- **Developers** extending the sparse-matrix format, parsing pipeline, or VexFlow renderer.

Local development only — no hosted deploy, accounts, or database yet.

## Services

| Service | Folder | Role |
|---------|--------|------|
| Backend | `aitu-backend/` | Parse text notation → sparse-COO JSON (`POST /sequence`, `GET /scores`) |
| Frontend | `aitu-frontend/` | Render JSON as sheet music (VexFlow 5) |

Each service is its own git repo nested under this umbrella workspace.

## Run locally

```bash
# Terminal 1 — API on http://127.0.0.1:8765
cd aitu-backend && uv sync && make serve

# Terminal 2 — Vite dev server (default http://localhost:5173)
cd aitu-frontend && npm install && npm run dev
```

Override backend URL: `VITE_AITU_API_URL=http://127.0.0.1:8765 npm run dev`

## Documentation

| Start here | Purpose |
|------------|---------|
| [context/00-project-complete-overview.md](context/00-project-complete-overview.md) | One-shot orientation |
| [context/00-index.md](context/00-index.md) | Full map of all docs |
| [context/shared/notation-spec.md](context/shared/notation-spec.md) | Notation contract (single source) |
| [documentation/README.md](documentation/README.md) | Code-level detail tree |

Subrepo entry points: [aitu-backend/README.md](aitu-backend/README.md) · [aitu-frontend/README.md](aitu-frontend/README.md)
