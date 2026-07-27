"""Background jobs with a live progress stream.

Transcription dominates the pipeline's runtime, so the UI cannot wait on a
synchronous request. A job runs the pipeline on a worker thread while
:func:`stream` yields the same :class:`~aitu_backend.progress.ProgressEvent`
objects the terminal's tqdm bar sees — one reporter, two audiences, exactly the
convention Task 1.1.2 set up.

In-memory only. This is a single-user local PoC: a restart loses job history,
which is fine because the *artifacts* are on disk and a finished job's result is
just a file read.
"""

from __future__ import annotations

import json
import queue
import threading
import uuid as uuid_module
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Iterator

from aitu_backend.progress import (
    BaseProgress,
    CallbackProgress,
    MultiProgress,
    ProgressEvent,
    TqdmProgress,
)

#: Sent as a named SSE event when a job finishes, however it finished.
DONE_EVENT = "done"

#: How long `stream` waits for the next event before emitting a keep-alive.
KEEPALIVE_SECONDS = 15.0

#: Finished jobs are kept so a late subscriber can still read the outcome.
MAX_REMEMBERED_JOBS = 50


@dataclass
class Job:
    """One background run."""

    id: str
    status: str = "running"  # running | done | error
    events: "queue.Queue[ProgressEvent | None]" = field(default_factory=queue.Queue)
    result: Any = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    #: Every event seen so far, so a subscriber that arrives late catches up.
    history: list[ProgressEvent] = field(default_factory=list)

    @property
    def finished(self) -> bool:
        return self.status in {"done", "error"}


_jobs: dict[str, Job] = {}
_lock = threading.Lock()


def _remember(job: Job) -> None:
    with _lock:
        _jobs[job.id] = job
        if len(_jobs) > MAX_REMEMBERED_JOBS:
            oldest = sorted(_jobs.values(), key=lambda item: item.created_at)
            for stale in oldest[: len(_jobs) - MAX_REMEMBERED_JOBS]:
                if stale.finished:
                    _jobs.pop(stale.id, None)


def get(job_id: str) -> Job | None:
    with _lock:
        return _jobs.get(job_id)


def submit(work: Callable[[BaseProgress], Any], *, mirror_to_terminal: bool = True) -> Job:
    """Run ``work(reporter)`` on a thread and return its :class:`Job`.

    ``work`` receives a reporter; everything it publishes reaches both the
    terminal bar and the SSE stream.
    """
    job = Job(id=str(uuid_module.uuid4()))
    _remember(job)

    def publish(event: ProgressEvent) -> None:
        job.history.append(event)
        job.events.put(event)

    reporters: list[BaseProgress] = [CallbackProgress(publish)]
    if mirror_to_terminal:
        reporters.append(TqdmProgress())
    reporter = MultiProgress(*reporters)

    def run() -> None:
        try:
            job.result = work(reporter)
            job.status = "done"
        except Exception as exc:  # Surface the message; the UI shows it.
            job.status = "error"
            job.error = str(exc) or exc.__class__.__name__
        finally:
            job.events.put(None)  # sentinel: no more events

    threading.Thread(target=run, name=f"aitu-job-{job.id[:8]}", daemon=True).start()
    return job


def stream(job_id: str) -> Iterator[str]:
    """Yield SSE frames for a job until it finishes.

    Emits the history first, so a subscriber that connects after the job started
    still sees where it is. Ends with a named ``done`` event carrying the final
    status — :func:`useProgress` on the frontend relies on that to distinguish a
    finished job from a dropped connection.
    """
    job = get(job_id)
    if job is None:
        yield _frame({"stage": "unknown", "message": f"No job '{job_id}'"}, event="error")
        yield _frame({"status": "error"}, event=DONE_EVENT)
        return

    for event in list(job.history):
        yield _frame(event.to_dict())

    while True:
        try:
            item = job.events.get(timeout=KEEPALIVE_SECONDS)
        except queue.Empty:
            if job.finished:
                break
            yield ": keep-alive\n\n"  # An SSE comment; the hook ignores it.
            continue
        if item is None:
            break
        yield _frame(item.to_dict())

    yield _frame({"status": job.status, "error": job.error}, event=DONE_EVENT)


def _frame(payload: dict[str, Any], event: str | None = None) -> str:
    prefix = f"event: {event}\n" if event else ""
    return f"{prefix}data: {json.dumps(payload)}\n\n"
