"""Jobs: one GPU job at a time, the named messages, and readers that arrive late (implementation 08,
Phase 4, plan sections 9.1 and 9.3)."""

from __future__ import annotations

import json
import threading
import time

from aitu_backend.transcription import jobs


def parse(frames: list[str]) -> list[tuple[str | None, int | None, dict]]:
    """``(event, id, payload)`` of each SSE frame; keep-alive comments left out."""
    out = []
    for frame in frames:
        if frame.startswith(":"):
            continue
        event = frame_id = None
        data = ""
        for line in frame.strip().splitlines():
            if line.startswith("event: "):
                event = line[len("event: ") :]
            elif line.startswith("id: "):
                frame_id = int(line[len("id: ") :])
            elif line.startswith("data: "):
                data = line[len("data: ") :]
        out.append((event, frame_id, json.loads(data)))
    return out


def wait(job: jobs.Job, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while not job.finished:
        assert time.monotonic() < deadline, "the job did not finish"
        time.sleep(0.005)


def test_gpu_jobs_run_one_at_a_time_in_order() -> None:
    running = 0
    most = 0
    order: list[int] = []
    lock = threading.Lock()
    release = threading.Event()

    def work(number: int):
        def run(reporter) -> int:
            nonlocal running, most
            with lock:
                running += 1
                most = max(most, running)
            release.wait(5)
            time.sleep(0.01)
            with lock:
                running -= 1
                order.append(number)
            return number

        return run

    submitted = [
        jobs.submit(work(n), gpu=True, mirror_to_terminal=False) for n in range(3)
    ]
    time.sleep(0.05)
    assert [job.status for job in submitted[1:]] == ["waiting", "waiting"]
    assert jobs.waiting_on_gpu() == 2
    release.set()
    for job in submitted:
        wait(job)
    assert most == 1
    assert order == [0, 1, 2]


def test_a_waiting_job_says_how_many_are_before_it() -> None:
    release = threading.Event()
    first = jobs.submit(lambda r: release.wait(5), gpu=True, mirror_to_terminal=False)
    second = jobs.submit(lambda r: None, gpu=True, mirror_to_terminal=False)
    third = jobs.submit(lambda r: None, gpu=True, mirror_to_terminal=False)
    time.sleep(0.05)
    release.set()
    for job in (first, second, third):
        wait(job)
    waiting = [
        p
        for e, _, p in parse(list(jobs.stream(third.id)))
        if p.get("stage") == "waiting"
    ]
    assert [p["message"] for p in waiting] == [
        "Waiting for 2 other transcriptions to finish",
        "Waiting for 1 other transcription to finish",
    ]


def test_a_second_job_with_the_same_key_is_the_first_one() -> None:
    release = threading.Event()
    first = jobs.submit(
        lambda r: release.wait(5), key="transcribe:x", mirror_to_terminal=False
    )
    again = jobs.submit(lambda r: None, key="transcribe:x", mirror_to_terminal=False)
    assert again is first
    assert jobs.active("transcribe:x") is first
    release.set()
    wait(first)
    assert jobs.active("transcribe:x") is None
    later = jobs.submit(lambda r: None, key="transcribe:x", mirror_to_terminal=False)
    assert later is not first
    wait(later)


def test_named_messages_travel_beside_the_ticks_and_the_done_frame_carries_the_summary() -> (
    None
):
    def work(reporter) -> int:
        with reporter.stage("transcribe", total=2) as stage:
            reporter.send("chunk", {"type": "chunk", "done": 1})
            stage.advance()
            reporter.send("chunk", {"type": "chunk", "done": 2})
            stage.advance()
        return 7

    job = jobs.submit(
        work, mirror_to_terminal=False, describe=lambda result: {"revision": result}
    )
    wait(job)
    frames = parse(list(jobs.stream(job.id)))
    chunks = [payload["done"] for event, _, payload in frames if event == "chunk"]
    assert chunks == [1, 2]
    ids = [frame_id for _, frame_id, _ in frames if frame_id is not None]
    assert ids == list(range(len(ids)))
    event, _, done = frames[-1]
    assert event == "done"
    assert done == {"type": "done", "status": "done", "error": None, "revision": 7}
    # The polling route reads the last tick, not a named message.
    assert job.latest is not None and job.latest.stage == "transcribe"


def test_two_readers_each_receive_every_frame() -> None:
    """Before Phase 4 the frames went through one queue, so two readers took them from each other."""
    started = threading.Event()
    release = threading.Event()

    def work(reporter) -> None:
        for number in range(5):
            reporter.send("chunk", {"n": number})
            if number == 1:
                started.set()
                release.wait(5)

    job = jobs.submit(work, mirror_to_terminal=False)
    started.wait(5)
    results: list[list] = [[], []]

    def read(slot: int) -> None:
        results[slot] = parse(list(jobs.stream(job.id)))

    readers = [threading.Thread(target=read, args=(slot,)) for slot in (0, 1)]
    for reader in readers:
        reader.start()
    time.sleep(0.05)
    release.set()
    for reader in readers:
        reader.join(5)
    for frames in results:
        assert [p["n"] for e, _, p in frames if e == "chunk"] == [0, 1, 2, 3, 4]


def test_a_reader_that_reconnects_resumes_after_its_last_frame() -> None:
    def work(reporter) -> None:
        for number in range(4):
            reporter.send("chunk", {"n": number})

    job = jobs.submit(work, mirror_to_terminal=False)
    wait(job)
    resumed = parse(list(jobs.stream(job.id, after=1)))
    assert [p["n"] for e, _, p in resumed if e == "chunk"] == [2, 3]
    assert resumed[-1][0] == "done"
