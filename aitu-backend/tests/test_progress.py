"""ProgressReporter contract: stage lifecycle, fractions, fan-out."""

from aitu_backend.progress import (
    CallbackProgress,
    MultiProgress,
    NullProgress,
    ProgressEvent,
    default_reporter,
)


def test_stage_emits_open_advance_and_close() -> None:
    events: list[ProgressEvent] = []
    reporter = CallbackProgress(events.append)

    with reporter.stage("collapse", total=3) as stage:
        stage.advance()
        stage.advance(2, message="halfway")

    assert [(e.stage, e.current, e.total) for e in events] == [
        ("collapse", 0, 3),
        ("collapse", 1, 3),
        ("collapse", 3, 3),
        ("collapse", 3, 3),
    ]
    assert events[-1].message == "collapse done"


def test_fraction_and_wire_payload() -> None:
    event = ProgressEvent(stage="clean", current=1, total=4)
    assert event.fraction == 0.25
    payload = event.to_dict()
    assert payload["stage"] == "clean"
    assert payload["fraction"] == 0.25
    assert set(payload) == {"stage", "current", "total", "fraction", "message", "timestamp"}


def test_fraction_is_zero_without_a_total() -> None:
    assert ProgressEvent(stage="x", current=5, total=0).fraction == 0.0


def test_iterate_advances_once_per_item() -> None:
    events: list[ProgressEvent] = []
    reporter = CallbackProgress(events.append)

    assert list(reporter.iterate(range(3), "frames")) == [0, 1, 2]
    assert [e.current for e in events] == [0, 1, 2, 3, 3]


def test_multi_progress_fans_out() -> None:
    left: list[ProgressEvent] = []
    right: list[ProgressEvent] = []
    reporter = MultiProgress(CallbackProgress(left.append), CallbackProgress(right.append))

    with reporter.stage("split", total=1) as stage:
        stage.advance()

    assert len(left) == len(right) == 3


def test_default_reporter_falls_back_to_null() -> None:
    assert isinstance(default_reporter(None), NullProgress)
    explicit = NullProgress()
    assert default_reporter(explicit) is explicit
