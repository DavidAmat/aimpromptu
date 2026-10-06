"""Background jobs with a live progress stream.

Transcription dominates the pipeline's runtime, so the UI cannot wait on a
synchronous request. A job runs the pipeline on a worker thread while
:func:`stream` yields the same :class:`~aitu_backend.progress.ProgressEvent`
objects the terminal's tqdm bar sees — one reporter, two audiences, exactly the
convention Task 1.1.2 set up.

Implementation 08 (plan sections 9.1 and 9.3) added three things:

* **One job at a time on the GPU.** A job submitted with ``gpu=True`` runs on one
  shared worker thread, in the order it arrived. While another GPU job runs, it
  is ``waiting`` and its stream says so. Before this, two transcriptions could
  load two models and write the same ``events.json``.
* **Named messages.** Beside the progress ticks, the work can publish named
  messages through ``reporter.send(name, payload)``: the live notes of a
  transcription are ``event: chunk`` frames. A page that only knows the progress
  ticks never sees them, because an ``EventSource`` delivers a named event only
  to a listener of that name.
* **Any number of readers.** Every frame is kept in the job's ``frames`` list and
  numbered (the SSE ``id:``). A reader keeps its own position in that list, so a
  page that connects late, or reconnects after a reload, first receives every
  frame already sent, in order, and then the new ones. ``Last-Event-ID`` resumes
  after a given frame. Before this, the frames went through one queue, and two
  readers took frames from each other.

A job can also carry a ``key`` (the audio uuid of a transcription): while a job
with that key is waiting or running, submitting another one returns the first,
so a double click or a second tab cannot start the same transcription twice.

**An owner** (implementation 02, plan section 18): a job records the user who started it, runs in
that user's context (so a piece it makes belongs to them), and is followed only by them and the
master user. Two users never join each other's job through a key.

In-memory only: a restart loses job history, which is fine because the *artifacts* are on disk and
a finished job's result is just a file read.
"""

from __future__ import annotations

import collections
import contextvars
import json
import threading
import uuid as uuid_module
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Iterator

from aitu_backend.auth import context
from aitu_backend.progress import (
    BaseProgress,
    CallbackProgress,
    MultiProgress,
    ProgressEvent,
    TqdmProgress,
)

#: Sent as a named SSE event when a job finishes, however it finished.
DONE_EVENT = "done"

#: The stage a job reports while it waits for the GPU.
WAITING_STAGE = "waiting"

#: How long `stream` waits for the next event before emitting a keep-alive.
KEEPALIVE_SECONDS = 15.0

#: Finished jobs are kept so a late subscriber can still read the outcome.
MAX_REMEMBERED_JOBS = 50


@dataclass
class Job:
    """One background run."""

    id: str
    status: str = "running"  # waiting | running | done | error
    result: Any = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    #: What the job is about, for example the audio uuid of a transcription. See :func:`submit`.
    key: str | None = None
    #: The user who started it; ``None`` outside a request (a script, a test).
    owner_id: int | None = None
    #: Every frame sent so far, ``(SSE event name or None, payload)``, in order. The index of a
    #: frame is its SSE ``id``.
    frames: list[tuple[str | None, dict[str, Any]]] = field(default_factory=list)
    #: The last progress tick, for the polling route.
    latest: ProgressEvent | None = None
    #: Extra fields of the final ``done`` frame, from the ``describe`` of :func:`submit`.
    summary: dict[str, Any] = field(default_factory=dict)
    _changed: threading.Condition = field(default_factory=threading.Condition, repr=False)

    @property
    def finished(self) -> bool:
        return self.status in {"done", "error"}

    @property
    def history(self) -> list[ProgressEvent]:
        """The progress ticks sent so far (the named messages left out)."""
        return [
            ProgressEvent(
                stage=payload["stage"],
                current=payload["current"],
                total=payload["total"],
                message=payload.get("message", ""),
                timestamp=payload.get("timestamp", 0.0),
            )
            for name, payload in list(self.frames)
            if name is None
        ]

    def publish(self, name: str | None, payload: dict[str, Any]) -> None:
        with self._changed:
            self.frames.append((name, payload))
            self._changed.notify_all()

    def _finish(self, status: str, error: str | None = None) -> None:
        with self._changed:
            self.status = status
            self.error = error
            self._changed.notify_all()


_jobs: dict[str, Job] = {}
_lock = threading.Lock()


def _remember(job: Job) -> None:
    """Keep the job. Called with ``_lock`` held."""
    _jobs[job.id] = job
    if len(_jobs) > MAX_REMEMBERED_JOBS:
        oldest = sorted(_jobs.values(), key=lambda item: item.created_at)
        for stale in oldest[: len(_jobs) - MAX_REMEMBERED_JOBS]:
            if stale.finished:
                _jobs.pop(stale.id, None)


def get(job_id: str) -> Job | None:
    with _lock:
        return _jobs.get(job_id)


def active(key: str) -> Job | None:
    """The waiting or running job with this key, or ``None``."""
    with _lock:
        for job in _jobs.values():
            if job.key == key and not job.finished:
                return job
    return None


# ------------------------------------------------------------------ the GPU queue


class _GpuQueue:
    """One worker thread that runs the GPU jobs one after the other, in the order they arrived."""

    def __init__(self) -> None:
        self._waiting: collections.deque[tuple[Job, Callable[[], None]]] = collections.deque()
        self._changed = threading.Condition()
        self._busy = False
        self._worker: threading.Thread | None = None
        #: The number of jobs before each waiting job, as last told to it.
        self._told: dict[str, int] = {}

    def put(self, job: Job, run: Callable[[], None]) -> None:
        with self._changed:
            self._waiting.append((job, run))
            if self._worker is None or not self._worker.is_alive():
                self._worker = threading.Thread(target=self._loop, name="aitu-gpu", daemon=True)
                self._worker.start()
            self._tell_positions()
            self._changed.notify_all()

    def _tell_positions(self) -> None:
        """Say to every waiting job how many jobs are before it. Called with the lock held."""
        ahead = 1 if self._busy else 0
        for position, (job, _) in enumerate(self._waiting):
            before = ahead + position
            if before == 0 or self._told.get(job.id) == before:
                continue
            self._told[job.id] = before
            job.status = "waiting"
            _tick(
                job,
                ProgressEvent(
                    stage=WAITING_STAGE,
                    current=0,
                    total=0,
                    message=(
                        "Waiting for 1 other transcription to finish"
                        if before == 1
                        else f"Waiting for {before} other transcriptions to finish"
                    ),
                ),
            )

    def _loop(self) -> None:
        while True:
            with self._changed:
                while not self._waiting:
                    self._changed.wait()
                job, run = self._waiting.popleft()
                self._told.pop(job.id, None)
                self._busy = True
                job.status = "running"
                self._tell_positions()
            try:
                run()
            finally:
                with self._changed:
                    self._busy = False
                    self._tell_positions()

    def waiting(self) -> int:
        with self._changed:
            return len(self._waiting)


_gpu = _GpuQueue()


def waiting_on_gpu() -> int:
    """GPU jobs waiting behind the running one."""
    return _gpu.waiting()


def _tick(job: Job, event: ProgressEvent) -> None:
    job.latest = event
    job.publish(None, event.to_dict())


def submit(
    work: Callable[[BaseProgress], Any],
    *,
    mirror_to_terminal: bool = True,
    gpu: bool = False,
    key: str | None = None,
    describe: Callable[[Any], dict[str, Any]] | None = None,
) -> Job:
    """Run ``work(reporter)`` on a thread and return its :class:`Job`.

    ``work`` receives a reporter; everything it publishes reaches both the
    terminal bar and the SSE stream. ``gpu=True`` puts the job in the GPU queue.
    With a ``key``, a job with the same key that is still waiting or running is
    returned instead of starting a second one. ``describe(result)`` gives extra
    fields for the final ``done`` frame (a transcription adds its ``revision``).
    """
    user = context.current()
    owner = user.id if user is not None else None
    with _lock:
        if key is not None:
            for existing in _jobs.values():
                if existing.key == key and existing.owner_id == owner and not existing.finished:
                    return existing
        job = Job(id=str(uuid_module.uuid4()), key=key, owner_id=owner)
        _remember(job)
    # The work runs with the request's context: the user it acts as, above all.
    request_context = contextvars.copy_context()

    reporters: list[BaseProgress] = [
        CallbackProgress(lambda event: _tick(job, event), on_message=job.publish)
    ]
    if mirror_to_terminal:
        reporters.append(TqdmProgress())
    reporter = MultiProgress(*reporters)

    def run() -> None:
        try:
            job.result = request_context.run(work, reporter)
            if describe is not None:
                job.summary = dict(describe(job.result))
            job._finish("done")
        except Exception as exc:  # Surface the message; the UI shows it.
            job._finish("error", str(exc) or exc.__class__.__name__)

    if gpu:
        _gpu.put(job, run)
    else:
        threading.Thread(target=run, name=f"aitu-job-{job.id[:8]}", daemon=True).start()
    return job


def stream(job_id: str, after: int | None = None) -> Iterator[str]:
    """Yield SSE frames for a job until it finishes.

    Emits every frame already sent first, so a subscriber that connects after the
    job started still sees where it is and receives every live note. ``after`` is
    the ``id`` of the last frame the reader already has (the ``Last-Event-ID``
    header of a reconnecting ``EventSource``). Ends with a named ``done`` event
    carrying the final status — :func:`useProgress` on the frontend relies on
    that to distinguish a finished job from a dropped connection.
    """
    job = get(job_id)
    if job is None:
        yield _frame({"stage": "unknown", "message": f"No job '{job_id}'"}, event="error")
        yield _frame({"type": DONE_EVENT, "status": "error"}, event=DONE_EVENT)
        return

    position = 0 if after is None else max(0, after + 1)
    while True:
        with job._changed:
            if position >= len(job.frames) and not job.finished:
                job._changed.wait(timeout=KEEPALIVE_SECONDS)
            batch = job.frames[position:]
            finished = job.finished and position + len(batch) >= len(job.frames)
        if not batch and not finished:
            yield ": keep-alive\n\n"  # An SSE comment; the hook ignores it.
            continue
        for name, payload in batch:
            yield _frame(payload, event=name, frame_id=position)
            position += 1
        if finished:
            break

    yield _frame(
        {"type": DONE_EVENT, "status": job.status, "error": job.error, **job.summary},
        event=DONE_EVENT,
    )


def _frame(payload: dict[str, Any], event: str | None = None, frame_id: int | None = None) -> str:
    prefix = f"event: {event}\n" if event else ""
    if frame_id is not None:
        prefix += f"id: {frame_id}\n"
    return f"{prefix}data: {json.dumps(payload, separators=(',', ':'))}\n\n"
