.PHONY: serve api lint format test hooks

HOST ?= $(or $(AITU_HOST),127.0.0.1)
PORT ?= $(or $(AITU_PORT),8765)

# Run from the backend folder so `data/` resolves next to pyproject.toml.
# Use `python -m uvicorn` so we never exec `.venv/bin/uvicorn`; its shebang embeds the
# full path to Python and can be truncated (~127 bytes), yielding `.../bin/pyt` on long paths.
serve:
	uv run python -m uvicorn aitu_backend.main:app --host $(HOST) --port $(PORT) --reload

api: serve

# Static checks. Run before every commit (pre-commit runs the same tools).
lint:
	uv run flake8 --config .flake8 src tests
	uv run mypy --config-file pyproject.toml

format:
	uv run black --config pyproject.toml src tests

test:
	uv run pytest

# One-time setup of the git hooks defined in ../.pre-commit-config.yaml.
hooks:
	uv run pre-commit install
