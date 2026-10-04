"""The environment variables of :mod:`aitu_backend.config` (implementation 08, Phase 3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aitu_backend import config
from aitu_backend.storage import paths


def test_the_defaults_are_the_old_behaviour(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("AITU_DEVICE", "AITU_HOST", "AITU_PORT"):
        monkeypatch.delenv(name, raising=False)
    assert config.data_dir_override() is None
    assert paths.data_dir() == paths.backend_root() / "data"
    assert config.device() == "cpu"
    assert (config.host(), config.port()) == ("127.0.0.1", 8765)


def test_the_data_folder_moves(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AITU_DATA_DIR", str(tmp_path))
    assert paths.data_dir() == tmp_path.resolve()
    assert paths.audio_root() == tmp_path.resolve() / "audio"


def test_an_empty_variable_is_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AITU_DATA_DIR", "  ")
    monkeypatch.setenv("AITU_DEVICE", "")
    assert paths.data_dir() == paths.backend_root() / "data"
    assert config.device() == "cpu"


def test_the_device(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AITU_DEVICE", "CUDA")
    assert config.device() == "cuda"
    monkeypatch.setenv("AITU_DEVICE", "auto")
    assert config.device() in ("cpu", "cuda")
    monkeypatch.setenv("AITU_DEVICE", "mps")
    with pytest.raises(ValueError, match="AITU_DEVICE"):
        config.device()


def test_host_and_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AITU_HOST", "0.0.0.0")
    monkeypatch.setenv("AITU_PORT", "9000")
    assert (config.host(), config.port()) == ("0.0.0.0", 9000)


def test_an_engine_takes_the_device_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    from aitu_backend.transcription.engine import BasicPitchEngine, EngineUnavailable

    # basic-pitch is never installed on Python 3.12, so its constructor stops at the import;
    # what matters is that it asked the configuration first and refused a bad value.
    monkeypatch.setenv("AITU_DEVICE", "tpu")
    with pytest.raises(ValueError, match="AITU_DEVICE"):
        BasicPitchEngine()
    monkeypatch.setenv("AITU_DEVICE", "cpu")
    with pytest.raises(EngineUnavailable):
        BasicPitchEngine()
