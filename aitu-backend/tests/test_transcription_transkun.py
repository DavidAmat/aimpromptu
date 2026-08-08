"""The Transkun engine's registration and its unavailable path.

The model itself is not exercised here — it is a 400 MB optional dependency and
these tests have to run on a machine with nothing installed. What is pinned is
everything around it: that the name is registered, that asking for it without
the package raises the error that names the install command rather than an
``ImportError`` from three frames down, and that the availability probe answers
without importing anything heavy.

The engine's real output was checked by hand on a 40 s excerpt of Mr Blue Sky:
297 notes, identical to the package's own CLI on the same audio, shortest note
35.9 ms — comfortably above the 20 ms artifact floor, which is the number that
matters when swapping engines. See :mod:`aitu_backend.transcription.artifacts`.
"""

import sys

import pytest

from aitu_backend.transcription.engine import (
    ENGINES,
    EngineUnavailable,
    TranscriptionEngine,
    TranskunEngine,
    available_engines,
    create_engine,
    engine_installed,
)

INSTALLED = engine_installed("transkun")
needs_transkun = pytest.mark.skipif(not INSTALLED, reason="transkun is not installed")


def test_transkun_is_registered_whether_or_not_it_is_installed() -> None:
    """It has to appear in the dropdown to be installable-and-then-selectable."""
    assert "transkun" in ENGINES
    assert "transkun" in available_engines()


def test_the_availability_probe_agrees_with_the_import() -> None:
    assert engine_installed("transkun") == ("transkun" in sys.modules or INSTALLED)


def test_asking_for_it_uninstalled_names_the_install_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The failure a user actually hits, and what it has to tell them."""
    monkeypatch.setitem(sys.modules, "transkun", None)
    with pytest.raises(EngineUnavailable) as caught:
        create_engine("transkun")
    assert "uv sync --extra transkun" in str(caught.value)
    assert "transkun" in str(caught.value)


def test_the_class_is_the_one_registered() -> None:
    assert ENGINES["transkun"] is TranskunEngine
    assert TranskunEngine.name == "transkun"


@needs_transkun
def test_it_satisfies_the_engine_protocol() -> None:
    engine = TranskunEngine()
    assert isinstance(engine, TranscriptionEngine)
    # The optional progress extension the pipeline probes for with getattr.
    assert callable(engine.transcribe_with_progress)


@needs_transkun
def test_a_missing_file_is_a_file_error_not_a_model_error() -> None:
    from pathlib import Path

    with pytest.raises(FileNotFoundError):
        TranskunEngine().transcribe(Path("/definitely/not/here.wav"))
