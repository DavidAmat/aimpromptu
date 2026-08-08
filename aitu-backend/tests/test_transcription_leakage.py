"""The onset-leakage filter: phantom re-onsets in, one note out.

Every case here is either taken from `When I Was Your Man` (the file that
exposed the artifact) or is a minimal version of one, so a threshold change that
breaks real music breaks a test.
"""

import numpy as np

from aitu_backend.matrix.keys import note_to_row
from aitu_backend.transcription.engine import NoteEvent
from aitu_backend.transcription.events_to_matrix import events_to_time_matrix
from aitu_backend.transcription.leakage import LeakageConfig, merge_leaked_onsets


def event(midi: int, start: float, end: float, velocity: int = 80) -> NoteEvent:
    return NoteEvent(midi_note=midi, start=start, end=end, velocity=velocity)


# ------------------------------------------------------------------ the artifact


def the_bruno_mars_passage() -> list[NoteEvent]:
    """12.3 s of `When I Was Your Man`, verbatim from the stored transcription.

    Do-Mi chord, Sol, Do-Mi chord, Sol — quarter apart, eighths alternating. The
    engine split the Sol that starts at 11.8964 in two at the instant the second
    chord landed, and the second half quantised into the chord's own column, so
    the score printed a Do-Mi-Sol chord.
    """
    return [
        event(60, 11.4847, 12.3000, 89),  # Do-4
        event(64, 11.4850, 12.3000, 88),  # Mi-4
        event(55, 11.8964, 12.3000, 73),  # Sol-3, the real offbeat eighth
        event(64, 12.3067, 13.1200, 82),  # Mi-4, second chord
        event(60, 12.3073, 13.1200, 87),  # Do-4, second chord
        event(55, 12.3140, 12.7100, 66),  # Sol-3 PHANTOM: 14 ms after its own offset
        event(55, 12.7172, 13.5300, 74),  # Sol-3, the next real offbeat eighth
    ]


def test_the_phantom_sol_is_merged_back() -> None:
    merged, report = merge_leaked_onsets(the_bruno_mars_passage())

    assert report.merged == 1
    only = report.merges[0]
    assert only.midi_note == 55
    assert only.phantom_start == 12.3140
    assert only.kept_start == 11.8964

    sols = sorted((e for e in merged if e.midi_note == 55), key=lambda e: e.start)
    assert [e.start for e in sols] == [11.8964, 12.7172]
    # The survivor keeps the real onset and takes the phantom's offset, which is
    # what makes it a quarter-long G3 instead of two eighths.
    assert sols[0].end == 12.7100
    assert sols[0].velocity == 73


def test_the_phantom_no_longer_lands_in_the_chord_column() -> None:
    """The whole point, checked on the grid the score is drawn from."""
    events = the_bruno_mars_passage()
    sol, chord = note_to_row("Sol-3"), note_to_row("Do-4")

    dirty = events_to_time_matrix(events, 14.0, leakage=None).matrix
    clean = events_to_time_matrix(events, 14.0).matrix

    chord_columns = np.flatnonzero(dirty.grid[chord] == 1)
    # Before: the Sol is struck in the same column as the second chord.
    assert set(np.flatnonzero(dirty.grid[sol] == 1)) & set(chord_columns)
    # After: it is not struck in any column the chord is struck in.
    assert not set(np.flatnonzero(clean.grid[sol] == 1)) & set(chord_columns)
    # And no note was lost: both real Sol strikes are still there.
    assert len(np.flatnonzero(clean.grid[sol] == 1)) == 2


# ------------------------------------------------- what must NOT be merged


def test_a_genuine_chord_restrike_is_left_alone() -> None:
    """9.83 s of the same file: the whole D7 chord re-articulates.

    Re-3 clears the first two conditions — it abuts, and it has company its
    predecessor did not — and it is still a real strike. It survives because it
    sits *inside* the cluster's spread rather than trailing it, and because its
    velocity holds (97 -> 96) instead of collapsing.
    """
    events = [
        event(50, 8.0592, 9.8300, 97),  # Re-3, 135 ms ahead of the chord
        event(57, 8.1941, 9.8300, 96),
        event(60, 8.1945, 9.8300, 99),
        event(38, 8.1949, 9.8300, 91),
        event(57, 9.8376, 11.4942, 89),  # the whole chord again ...
        event(60, 9.8376, 11.4700, 93),
        event(50, 9.8385, 11.4947, 96),  # ... Re-3 included. NOT a phantom.
        event(38, 9.8401, 11.4986, 90),
        event(53, 9.8440, 11.4949, 89),
    ]
    merged, report = merge_leaked_onsets(events)

    assert report.merged == 0
    assert len(merged) == len(events)


def test_a_louder_restrike_is_left_alone() -> None:
    """22.99 s: the bass re-strikes slightly *harder*. Never a leak."""
    events = [
        event(43, 22.5763, 22.9900, 82),
        event(59, 22.9869, 23.8000, 82),
        event(62, 22.9903, 23.8000, 81),
        event(65, 22.9907, 23.8000, 83),
        event(55, 22.9937, 23.8000, 82),
        event(43, 22.9957, 23.8100, 83),  # +1 velocity, and inside the cluster
    ]
    _, report = merge_leaked_onsets(events)
    assert report.merged == 0


def test_a_repeated_note_alone_in_the_texture_is_left_alone() -> None:
    """Nothing else is struck, so there is no transient to have leaked."""
    events = [event(55, 0.0, 0.400, 80), event(55, 0.410, 0.800, 70)]
    _, report = merge_leaked_onsets(events)
    assert report.merged == 0


def test_a_real_gap_is_left_alone() -> None:
    """Half a second of silence is a released key, whatever else happens."""
    events = [
        event(55, 0.0, 0.400, 80),
        event(55, 0.900, 1.300, 60),
        event(60, 0.898, 1.300, 90),
        event(64, 0.899, 1.300, 90),
    ]
    _, report = merge_leaked_onsets(events)
    assert report.merged == 0


# -------------------------------------------------------------- properties


def test_the_filter_is_idempotent() -> None:
    once, first = merge_leaked_onsets(the_bruno_mars_passage())
    twice, second = merge_leaked_onsets(once)
    assert first.merged == 1
    assert second.merged == 0
    assert once == twice


def test_the_input_is_never_mutated() -> None:
    events = the_bruno_mars_passage()
    before = [(e.midi_note, e.start, e.end, e.velocity) for e in events]
    merge_leaked_onsets(events)
    assert [(e.midi_note, e.start, e.end, e.velocity) for e in events] == before


def test_disabling_the_filter_places_the_engine_output_verbatim() -> None:
    events = the_bruno_mars_passage()
    report = events_to_time_matrix(events, 14.0, leakage=None)
    assert report.leakage.merged == 0
    assert "leaked" not in report.describe()


def test_the_report_names_its_evidence() -> None:
    _, report = merge_leaked_onsets(the_bruno_mars_passage())
    text = report.merges[0].describe()
    for fragment in ("MIDI 55", "12.3140s", "co-onset", "lag", "velocity"):
        assert fragment in text
    assert "1 leaked re-onset(s) merged back" in report.describe()


def test_thresholds_are_configurable() -> None:
    """A caller who wants the old behaviour can ask for it."""
    events = the_bruno_mars_passage()
    off = LeakageConfig(min_velocity_drop=127)
    _, report = merge_leaked_onsets(events, off)
    assert report.merged == 0


def test_an_empty_or_single_event_list_is_returned_unchanged() -> None:
    for events in ([], [event(60, 0.0, 1.0)]):
        merged, report = merge_leaked_onsets(events)
        assert merged == events
        assert report.merged == 0
        assert report.describe() == "no leaked re-onsets found."


def test_the_filter_runs_by_default_in_the_time_build() -> None:
    report = events_to_time_matrix(the_bruno_mars_passage(), 14.0)
    assert report.leakage.merged == 1
    assert "1 leaked re-onset(s) merged" in report.describe()
