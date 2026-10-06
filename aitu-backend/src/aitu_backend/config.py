"""The backend's settings, read from the environment (implementation 08, plan section 9.1).

Every value has a default that is the behaviour the backend had before the variable existed, so a
plain ``make serve`` on a laptop needs nothing set. The container sets what differs
(``compose.yaml``), and ``.env.example`` at the repository root lists every name.

=====================  ==================================  =========================================
Variable               Default                             Meaning
=====================  ==================================  =========================================
``AITU_DATABASE_DIR``  ``<repository>/.database``           Every record and every file of the app
                                                           (implementation 02, plan section 8)
``AITU_DATA_DIR``      ``aitu-backend/data``               The old file store, read only by the
                                                           migration to ``.database/`` (Phase 3)
``AITU_MASTER_         ``master``                          The username of the master user, made on
USERNAME``                                                 the first start (plan section 9.1)
``AITU_MASTER_         empty                               Its password, set while it has none
PASSWORD``
``AITU_DEVICE``        ``cpu``                             ``cpu``, ``cuda`` or ``auto`` (``cuda``
                                                           when torch sees a GPU, else ``cpu``)
``AITU_HOST``          ``127.0.0.1``                       Where ``python -m aitu_backend.main``
``AITU_PORT``          ``8765``                            listens
``AITU_MUSCRIPTOR_     ``large``                           MuScriptor's size: ``small``, ``medium``
MODEL``                                                    or ``large`` (Phase 1: ``large``)
``AITU_MUSCRIPTOR_     ``float16``                         Its weight type: ``float32``, ``float16``
DTYPE``                                                    or ``bfloat16`` (Phase 1: ``float16``)
``AITU_PRELOAD_        empty (nothing is preloaded)        An engine to load when the server starts,
ENGINE``                                                   for example ``muscriptor-large``
=====================  ==================================  =========================================

Read on every call, not once at import: a test sets a variable with ``monkeypatch.setenv`` and the
next call sees it, and nothing here imports torch unless ``auto`` has to be answered.
"""

from __future__ import annotations

import os
from functools import cache
from pathlib import Path

DEVICES = ("cpu", "cuda", "auto")

MUSCRIPTOR_SIZES = ("small", "medium", "large")
MUSCRIPTOR_DTYPES = ("float32", "float16", "bfloat16")

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def data_dir_override() -> Path | None:
    """``AITU_DATA_DIR`` as a path, or ``None`` when it is unset or empty."""
    value = os.environ.get("AITU_DATA_DIR", "").strip()
    return Path(value).expanduser().resolve() if value else None


def database_dir_override() -> Path | None:
    """``AITU_DATABASE_DIR`` as a path, or ``None`` when it is unset or empty."""
    value = os.environ.get("AITU_DATABASE_DIR", "").strip()
    return Path(value).expanduser().resolve() if value else None


DEFAULT_MASTER_USERNAME = "master"


def master_username() -> str:
    """The username the master user is created with when the database has none."""
    return os.environ.get("AITU_MASTER_USERNAME", "").strip() or DEFAULT_MASTER_USERNAME


def master_password() -> str | None:
    """The master user's first password, or ``None``. Read only while the user has no password."""
    value = os.environ.get("AITU_MASTER_PASSWORD", "")
    return value or None


def device() -> str:
    """The torch device the transcription engines run on: ``cpu`` or ``cuda``.

    ``cuda`` is returned as asked, even when no GPU is visible: a job that was told to use the GPU
    must fail loudly rather than run ten times slower on the CPU without saying so
    (``context/02b-local-setup.md``: "Do not silently fall back to CPU for GPU jobs").
    """
    value = os.environ.get("AITU_DEVICE", "cpu").strip().lower() or "cpu"
    if value not in DEVICES:
        raise ValueError(f"AITU_DEVICE must be one of {', '.join(DEVICES)}; got {value!r}")
    if value == "auto":
        return "cuda" if _cuda_available() else "cpu"
    return value


@cache
def _cuda_available() -> bool:
    try:
        import torch  # noqa: PLC0415
    except ImportError:
        return False
    return bool(torch.cuda.is_available())


def host() -> str:
    return os.environ.get("AITU_HOST", "").strip() or DEFAULT_HOST


def port() -> int:
    value = os.environ.get("AITU_PORT", "").strip()
    return int(value) if value else DEFAULT_PORT


def muscriptor_model() -> str:
    """The MuScriptor size. Phase 1 chose ``large``: the smaller ones give a different transcription."""
    value = os.environ.get("AITU_MUSCRIPTOR_MODEL", "").strip().lower() or "large"
    if value not in MUSCRIPTOR_SIZES:
        raise ValueError(
            f"AITU_MUSCRIPTOR_MODEL must be one of {', '.join(MUSCRIPTOR_SIZES)}; got {value!r}"
        )
    return value


def muscriptor_dtype() -> str:
    """The MuScriptor weight type. Phase 1: ``float16`` gives the same notes, 2.2 times faster."""
    value = os.environ.get("AITU_MUSCRIPTOR_DTYPE", "").strip().lower() or "float16"
    if value not in MUSCRIPTOR_DTYPES:
        raise ValueError(
            f"AITU_MUSCRIPTOR_DTYPE must be one of {', '.join(MUSCRIPTOR_DTYPES)}; got {value!r}"
        )
    return value


def preload_engine() -> str | None:
    """The engine to load at startup (``muscriptor-large``), or ``None`` to load on first use.

    ``none`` (or ``off``) is ``None`` too, so the container's default can be turned off in ``.env``.
    """
    value = os.environ.get("AITU_PRELOAD_ENGINE", "").strip().lower()
    return None if value in ("", "none", "off") else value
