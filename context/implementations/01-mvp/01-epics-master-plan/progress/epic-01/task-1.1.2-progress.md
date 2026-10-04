# Task 1.1.2 — Backend tooling · progress report

Status: **done**. Date: 2026-07-26.

## Summary

**Pre-commit** — `.pre-commit-config.yaml` at the **repo root** (the git root is the monorepo root),
scoped with `files: ^aitu-backend/` and excluding `notebooks/` and `data/`:

| Hook | Config |
|------|--------|
| `black` 24.10.0 | `line-length = 100`, `target-version = py312` (in `pyproject.toml`) |
| `flake8` 7.1.1 | `aitu-backend/.flake8`, `extend-ignore = E501,E203,W503` |
| `mypy` v1.13.0 | `pyproject.toml`, pydantic plugin, `ignore_missing_imports = true` |
| pre-commit-hooks | trailing whitespace, EOF fixer, check-yaml/toml/merge-conflict |

flake8 has no `pyproject.toml` support, hence the separate `.flake8` file — deliberate, not an oversight.

mypy starts permissive (`ignore_missing_imports`) but with `check_untyped_defs`,
`warn_unused_ignores`, `warn_redundant_casts` and `no_implicit_optional` on, so untyped code
still gets checked. The pydantic plugin runs with `init_typed` and
`warn_required_dynamic_aliases`.

**Progress convention** — new module `src/aitu_backend/progress.py`. One interface, several sinks:

| Class | Use |
|-------|-----|
| `ProgressReporter` (Protocol) | what long-running functions accept |
| `NullProgress` | silent default (`default_reporter(None)`) |
| `TqdmProgress` | terminal bar, one per stage |
| `CallbackProgress` | forwards `ProgressEvent`s — Epic 4 pushes these onto the SSE queue |
| `MultiProgress` | fan-out (terminal + SSE at once) |

`ProgressEvent` is frozen and `to_dict()` emits the exact camelCase payload an SSE `data:` frame
carries (`stage`, `current`, `total`, `fraction`, `message`, `timestamp`), so tqdm and the UI share
one code path — the point of the subtask. Usage:

```python
with reporter.stage("collapse", total=len(columns)) as stage:
    for column in columns:
        ...
        stage.advance()
```

`reporter.iterate(items, "frames")` is the shorthand for the common loop.
`PROGRESS_THRESHOLD_SECONDS = 10.0` records the rule in code.

**Makefile** — added `lint` (flake8 + mypy), `format` (black), `test` (pytest) and `hooks`
(`pre-commit install`). `serve`/`api` unchanged.

**pyproject** — added a `[dependency-groups] dev` with pytest, httpx, black, flake8, mypy,
pre-commit, types-tqdm; `tqdm` and `python-multipart` are runtime deps. Added
`[tool.pytest.ini_options]` (`testpaths=tests`, `pythonpath=src`).

## Errors found and how they were solved

1. **mypy `sqlite3.OperationalError: disk I/O error.`** Only in the Linux sandbox: mypy's
   incremental cache is a SQLite file, and the mounted volume rejects the write pattern. Worked
   around locally with `--cache-dir=/tmp/mypycache`; **not** added to the Makefile, since it is a
   sandbox artifact, not a Mac one. If it ever appears on the Mac, add
   `MYPY_CACHE_DIR=/tmp/mypy-aitu` to the `lint` target.
2. **Two real mypy errors in `schemas/score.py`.** The `_check_hands` validator read
   `self.r_matrix.shape[1]` guarded only by a `bool` flag, which mypy cannot narrow through.
   Rebound to locals (`right, left = self.r_matrix, self.l_matrix`) and narrowed with
   `is not None`. Behaviour identical.
3. **black reformatted three files** on first run (`text_notation.py`, `progress.py`,
   `test_api_smoke.py`) — line-length only, no logic change.

## Deviations from the task file

- Pre-commit lives at the **repo root** as specified, but the tool configs it points at live in
  `aitu-backend/` (`pyproject.toml`, `.flake8`) so `make lint` and the hooks use the same files.
- Added `make hooks`; the task only named lint/format/test.

## Verification

```
black --config pyproject.toml src tests   # all done, no changes on a second run
flake8 --config .flake8 src tests         # clean
mypy --config-file pyproject.toml         # Success: no issues found in 22 source files
pytest                                    # 12 passed
```

`tests/test_progress.py` (6 tests) pins the reporter contract: stage open/advance/close event
sequence, `fraction` maths including the unknown-total case, the wire payload keys,
`iterate` advancing once per item, `MultiProgress` fan-out, and the `NullProgress` fallback.

## Manual trial for the supervisor

```bash
cd aitu-backend
uv sync
make hooks           # installs the git hook
make lint && make test
git commit --allow-empty -m "chore: check hooks"   # hooks must fire
```

`pre-commit` itself was **not** executed in the sandbox — it clones hook repos from GitHub, which
the sandbox network blocks. The three tools were run directly with the exact same configs, so the
hook run should be a formality; still, please confirm `make hooks` + a real commit works.

## For the next worker

- Never call `tqdm` in feature code — take a `ProgressReporter` and default it with
  `default_reporter(...)`.
- Epic 4 adds `SseProgress`: subclass `BaseProgress`, or just wrap `CallbackProgress` around an
  `asyncio.Queue.put_nowait`; `ProgressEvent.to_dict()` is already the frame body.
- Keep `make lint` green — mypy is configured over `src/` **and** `tests/`.
