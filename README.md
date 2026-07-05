# AImpromptu (aitu)

Custom Spanish-solfège piano notation → sparse JSON score → VexFlow sheet music. Local POC.

## Services

| Service | Folder | Role |
|---------|--------|------|
| Backend | `aitu-backend/` | Parse text notation → sparse-COO JSON (`POST /sequence`, `GET /scores`) |
| Frontend | `aitu-frontend/` | Render JSON as sheet music (VexFlow) |

## Run locally

```bash
# Terminal 1
cd aitu-backend && uv sync && make serve

# Terminal 2
cd aitu-frontend && npm install && npm run dev
```

Backend: `http://127.0.0.1:8765` · Frontend: Vite dev server (default `http://localhost:5173`).

Override API URL: `VITE_AITU_API_URL=http://127.0.0.1:8765 npm run dev`

## Documentation

Platform and service docs live in [`context/`](context/00-index.md) (overviews) and [`documentation/`](documentation/README.md) (code-level detail). Start with [`context/00-project-complete-overview.md`](context/00-project-complete-overview.md).
