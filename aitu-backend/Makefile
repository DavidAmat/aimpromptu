.PHONY: serve api

HOST ?= 127.0.0.1
PORT ?= 8765

# Run from repo root so `data/example-scores.json` resolves next to pyproject.toml.
# Use `python -m uvicorn` so we never exec `.venv/bin/uvicorn`; its shebang embeds the
# full path to Python and can be truncated (~127 bytes), yielding `.../bin/pyt` on long paths.
serve:
	uv run python -m uvicorn aitu_backend.main:app --host $(HOST) --port $(PORT) --reload

api: serve