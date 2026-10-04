"""Settings shared by every test."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _no_data_dir_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep ``AITU_DATA_DIR`` out of the tests.

    Many tests move the data folder by patching ``paths.backend_root`` to a temporary folder. A
    data folder set in the environment would win over that patch, and those tests would then write
    into the real library. A test of the variable itself sets it again with ``monkeypatch.setenv``.
    """
    monkeypatch.delenv("AITU_DATA_DIR", raising=False)
