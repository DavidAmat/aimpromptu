"""The loaded models, kept for the life of the process (implementation 08, plan section 9.1).

Before this, every transcription built its engine again: the torch import, the weights read from the
disk and moved to the device, for every job. The registry keeps one engine per name and device, and
one MuScriptor model per ``(size, device, dtype)``. The first job pays the load (about 1 s for
MuScriptor ``large`` from the SSD, plus the torch import); the next ones start at once.

``AITU_PRELOAD_ENGINE=muscriptor-large`` loads the model when the server starts, on a background
thread, so the first transcription does not wait either. uvicorn runs with ``--reload`` in
development: an edit restarts the process and the model is loaded again (Phase 3 report, section 4).

The engines are shared, so they must be used by one job at a time. The GPU queue of
:mod:`aitu_backend.transcription.jobs` guarantees it for every transcription route.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable

from aitu_backend import config

__all__ = [
    "LoadError",
    "clear",
    "engine",
    "loaded",
    "muscriptor",
    "preload",
    "preload_error",
    "preload_in_background",
]

log = logging.getLogger(__name__)

#: Guards the dictionaries below; held only for a lookup or an insert.
_lock = threading.Lock()
#: Held while a model loads, so two jobs never load the same weights twice.
_load_lock = threading.Lock()
_models: dict[tuple[str, ...], Any] = {}
_engines: dict[tuple[str, str], Any] = {}
_preload_error: str | None = None

#: The Hugging Face page of each size, where the licence is accepted (a human step, Phase 1).
MODEL_PAGE = "https://huggingface.co/MuScriptor/muscriptor-{size}"


class LoadError(RuntimeError):
    """A model could not be loaded. The message says what to do, in plain words."""


def _silence(module_names: tuple[str, ...]) -> None:
    """Replace ``print`` in these modules only.

    MuScriptor prints a timing line for every chunk (Phase 1 and Phase 3 reports). Redirecting
    ``sys.stdout`` would silence every other thread of the server too, so the name ``print`` is
    shadowed inside MuScriptor's own modules instead.
    """
    import importlib  # noqa: PLC0415

    for name in module_names:
        try:
            module = importlib.import_module(name)
        except ImportError:
            continue
        module.print = lambda *args, **kwargs: None  # type: ignore[attr-defined]


def _load_muscriptor(size: str, device: str, dtype: str) -> Any:
    try:
        from muscriptor.transcription_model import TranscriptionModel  # noqa: PLC0415
    except ImportError as exc:
        raise LoadError(
            "MuScriptor is not installed. Install it with: uv sync --extra muscriptor "
            "(in aitu-backend/)"
        ) from exc
    _silence(
        (
            "muscriptor.transcription_model",
            "muscriptor.models.lm",
            "muscriptor.modules.conditioners",
        )
    )
    try:
        return TranscriptionModel.load_model(size, device=device, dtype=dtype)
    except Exception as exc:  # the Hugging Face errors say little about what to do
        raise LoadError(
            f"MuScriptor '{size}' could not be loaded on {device} ({exc.__class__.__name__}: "
            f"{exc}). The weights come from Hugging Face and are gated: accept the licence once on "
            f"{MODEL_PAGE.format(size=size)} and make sure HF_TOKEN is set for the backend."
        ) from exc


def muscriptor(size: str | None = None, device: str | None = None, dtype: str | None = None) -> Any:
    """MuScriptor's ``TranscriptionModel``, loaded once per ``(size, device, dtype)``."""
    size = size or config.muscriptor_model()
    device = device or config.device()
    dtype = dtype or config.muscriptor_dtype()
    key = ("muscriptor", size, device, dtype)
    with _lock:
        model = _models.get(key)
    if model is not None:
        return model
    with _load_lock:
        with _lock:
            model = _models.get(key)
        if model is None:
            model = _load_muscriptor(size, device, dtype)
            with _lock:
                _models[key] = model
            log.info("Loaded MuScriptor %s on %s (%s)", size, device, dtype)
    return model


def engine(name: str, build: Callable[[], Any]) -> Any:
    """The shared engine called ``name`` on the configured device, built by ``build`` once."""
    key = (name, config.device())
    with _lock:
        existing = _engines.get(key)
    if existing is not None:
        return existing
    built = build()  # outside the lock: MuScriptorEngine takes the lock itself to load its model
    with _lock:
        return _engines.setdefault(key, built)


def loaded() -> list[str]:
    """What is loaded, for the status route: ``muscriptor-large (cuda, float16)``."""
    with _lock:
        names = [f"{key[0]}-{key[1]} ({key[2]}, {key[3]})" for key in _models]
        names += [f"{name} ({device})" for name, device in _engines]
    return names


def preload(spec: str) -> None:
    """Load an engine now. ``spec`` is ``muscriptor-large`` (or ``muscriptor`` for the default
    size). Raises :class:`LoadError` or ``ValueError``."""
    name, _, size = spec.partition("-")
    if name != "muscriptor":
        raise ValueError(f"AITU_PRELOAD_ENGINE supports MuScriptor only; got {spec!r}")
    if size and size not in config.MUSCRIPTOR_SIZES:
        raise ValueError(f"Unknown MuScriptor size in AITU_PRELOAD_ENGINE: {spec!r}")
    muscriptor(size or None)
    # The lag measurement that ends every MuScriptor transcription compiles itself on first use.
    from aitu_backend.transcription import lag  # noqa: PLC0415

    lag.warm_up()


def preload_in_background(spec: str) -> threading.Thread:
    """:func:`preload` on a thread, so the server answers while the model loads."""

    def run() -> None:
        global _preload_error
        try:
            preload(spec)
            _preload_error = None
        except Exception as exc:  # reported by the status route, never fatal
            _preload_error = str(exc)
            log.error("Could not preload %s: %s", spec, exc)

    thread = threading.Thread(target=run, name="aitu-preload", daemon=True)
    thread.start()
    return thread


def preload_error() -> str | None:
    """Why the preload failed, or ``None``."""
    return _preload_error


def clear() -> None:
    """Forget every loaded model and engine. For tests."""
    global _preload_error
    with _lock:
        _models.clear()
        _engines.clear()
    _preload_error = None
