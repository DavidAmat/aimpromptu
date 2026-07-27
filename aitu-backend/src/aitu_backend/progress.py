"""Progress reporting for backend work that can exceed ~10 seconds.

One code path serves both audiences: the terminal (``tqdm``) and the UI
(server-sent events, Epic 4). Long-running code never touches ``tqdm`` or
SSE directly — it takes a :class:`ProgressReporter` and calls
:meth:`ProgressReporter.advance`.

Typical use::

    def collapse(matrix, reporter: ProgressReporter | None = None) -> Matrix:
        reporter = reporter or NullProgress()
        with reporter.stage("collapse", total=len(columns)) as stage:
            for column in columns:
                ...
                stage.advance()

The default :class:`TqdmProgress` renders a terminal bar. Epic 4 adds an
``SseProgress`` that pushes the same :class:`ProgressEvent` objects onto an
asyncio queue consumed by ``GET /matrix/progress/{job_id}``.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Iterator, Protocol, TypeVar

T = TypeVar("T")

#: Anything slower than this (seconds, estimated) must report progress.
PROGRESS_THRESHOLD_SECONDS = 10.0


@dataclass(frozen=True)
class ProgressEvent:
    """One progress tick, serializable straight into an SSE ``data:`` frame."""

    stage: str
    current: int
    total: int
    message: str = ""
    timestamp: float = field(default_factory=time.time)

    @property
    def fraction(self) -> float:
        """Completion in ``[0, 1]``; ``0`` when the total is unknown."""
        if self.total <= 0:
            return 0.0
        return min(1.0, self.current / self.total)

    def to_dict(self) -> dict[str, Any]:
        """camelCase payload, matching the wire convention."""
        return {
            "stage": self.stage,
            "current": self.current,
            "total": self.total,
            "fraction": round(self.fraction, 4),
            "message": self.message,
            "timestamp": self.timestamp,
        }


class StageHandle(Protocol):
    """Handle yielded by :meth:`ProgressReporter.stage`."""

    def advance(self, step: int = 1, message: str = "") -> None:
        """Move the current stage forward by ``step`` units."""


class ProgressReporter(Protocol):
    """Minimal interface every long-running backend routine accepts."""

    @contextmanager
    def stage(self, name: str, total: int, message: str = "") -> Iterator[StageHandle]:
        """Open a named stage of ``total`` units; closes it on exit."""

    def emit(self, event: ProgressEvent) -> None:
        """Publish one event (called by the stage handle)."""


class _Stage:
    """Counter bound to one reporter; created by ``reporter.stage(...)``."""

    def __init__(self, reporter: "BaseProgress", name: str, total: int) -> None:
        self._reporter = reporter
        self._name = name
        self._total = total
        self._current = 0

    def advance(self, step: int = 1, message: str = "") -> None:
        self._current = (
            min(self._total, self._current + step) if self._total > 0 else self._current + step
        )
        self._reporter.emit(
            ProgressEvent(
                stage=self._name,
                current=self._current,
                total=self._total,
                message=message,
            )
        )


class BaseProgress:
    """Shared plumbing: stage bookkeeping plus an ``iterate`` convenience."""

    def emit(self, event: ProgressEvent) -> None:  # pragma: no cover - overridden
        raise NotImplementedError

    @contextmanager
    def stage(self, name: str, total: int, message: str = "") -> Iterator[_Stage]:
        handle = _Stage(self, name, total)
        self.emit(ProgressEvent(stage=name, current=0, total=total, message=message))
        try:
            yield handle
        finally:
            self.emit(ProgressEvent(stage=name, current=total, total=total, message=f"{name} done"))

    def iterate(self, items: Iterable[T], name: str, total: int | None = None) -> Iterator[T]:
        """Wrap an iterable so each item advances a stage of the same name."""
        materialized = list(items) if total is None else items
        count = total if total is not None else len(materialized)  # type: ignore[arg-type]
        with self.stage(name, count) as handle:
            for item in materialized:
                yield item
                handle.advance()


class NullProgress(BaseProgress):
    """Silent reporter — the default when a caller passes nothing."""

    def emit(self, event: ProgressEvent) -> None:
        return None


class TqdmProgress(BaseProgress):
    """Terminal reporter: one ``tqdm`` bar per stage."""

    def __init__(self) -> None:
        self._bars: dict[str, Any] = {}

    def emit(self, event: ProgressEvent) -> None:
        from tqdm import tqdm

        bar = self._bars.get(event.stage)
        if bar is None:
            bar = tqdm(total=event.total, desc=event.stage, leave=False)
            self._bars[event.stage] = bar
        bar.n = event.current
        if event.message:
            bar.set_postfix_str(event.message)
        bar.refresh()
        if event.total > 0 and event.current >= event.total:
            bar.close()
            self._bars.pop(event.stage, None)


class CallbackProgress(BaseProgress):
    """Reporter that forwards every event to a callable.

    Epic 4 uses it to push events onto the asyncio queue behind the SSE
    endpoint; tests use it to assert the exact event sequence.
    """

    def __init__(self, callback: Callable[[ProgressEvent], None]) -> None:
        self._callback = callback

    def emit(self, event: ProgressEvent) -> None:
        self._callback(event)


class MultiProgress(BaseProgress):
    """Fan out to several reporters (e.g. terminal + SSE at once)."""

    def __init__(self, *reporters: BaseProgress) -> None:
        self._reporters = reporters

    def emit(self, event: ProgressEvent) -> None:
        for reporter in self._reporters:
            reporter.emit(event)


def default_reporter(reporter: BaseProgress | None) -> BaseProgress:
    """Normalize an optional reporter argument to a usable object."""
    return reporter if reporter is not None else NullProgress()
