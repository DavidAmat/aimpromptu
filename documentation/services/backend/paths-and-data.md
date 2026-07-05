> Context: [api.md](../../../context/backend/api.md)

# Paths and data

Filesystem resolution in `aitu-backend/src/aitu_backend/paths.py`.

## repo_root()

```python
Path(__file__).resolve().parent.parent.parent
```

Resolves to `aitu-backend/` (parent of `src/`).

## scores_json_path()

```python
repo_root() / "data" / "example-scores.json"
```

Used by `GET /scores` in `main.py`.

## data/example-scores.json

- JSON array of `MatrixScore` objects (same schema as `POST /sequence` response).
- Sample data served at runtime; tracked in the backend subrepo git.
- If missing, `/scores` returns 404 with a hint to run
  `notebooks/dummy-matrix/01-generate-dummy-matrix.ipynb` or create the file manually.

Do not deep-read the file in docs work — treat it as opaque persisted scores.

## Notebooks (related)

`notebooks/dummy-matrix/01-generate-dummy-matrix.ipynb` can generate or refresh sample
scores. POC demos live under `notebooks/<theme>/` — one folder per thematic experiment.
