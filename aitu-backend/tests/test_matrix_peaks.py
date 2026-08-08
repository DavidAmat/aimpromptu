"""Measuring the rhythm: gaps, peaks and the ladder built from a named peak.

The regression in `test_snapping_before_measuring_splits_a_peak_in_two` is the reason D-07 exists.
It must never be deleted, weakened or skipped.
"""

import json
from pathlib import Path

import numpy as np
import pytest

from aitu_backend.matrix.intervals import (
    IntervalSet,
    attack_times_seconds,
    check_measured_on_raw_times,
    intervals_from_events,
    intervals_ms,
)
from aitu_backend.matrix.ladder import (
    bpm_of,
    build_ladder,
    header_label,
    label_peaks,
    nearest_figure,
    shift_ladder,
)
from aitu_backend.matrix.peaks import density_grid, find_peaks, gaussian_kde, peaks_of
from aitu_backend.matrix.time_grid import frame_of_seconds
from aitu_backend.schemas.time_matrix import FigureName
from aitu_backend.transcription.engine import NoteEvent

RANDOM = np.random.default_rng(20260806)


def note(start_ms: float, midi: int = 60, length_ms: float = 100.0) -> NoteEvent:
    return NoteEvent(midi_note=midi, start=start_ms / 1000.0, end=(start_ms + length_ms) / 1000.0)


def swung_run(count: int = 200, long_ms: float = 211.0, short_ms: float = 125.0) -> list[NoteEvent]:
    """A shuffle: alternating long and short halves of a 337 ms beat, with human jitter.

    This is the shape the measurement found on the real piece. The jitter is what makes the peaks
    peaks rather than single values, and it is what snapping destroys.
    """
    events, clock = [], 0.0
    for index in range(count):
        events.append(note(clock))
        clock += (long_ms if index % 2 == 0 else short_ms) + RANDOM.normal(0.0, 6.0)
    return events


# --------------------------------------------------------------------------- intervals


def test_a_chord_counts_as_one_attack():
    attacks = attack_times_seconds([note(0, 60), note(8, 64), note(15, 67), note(400, 72)])
    assert attacks.tolist() == pytest.approx([0.0, 0.4])


def test_gaps_are_the_distances_between_attacks():
    assert intervals_ms([0.0, 0.337, 0.548]).tolist() == pytest.approx([337.0, 211.0])
    assert intervals_ms([0.5]).size == 0
    assert intervals_ms([]).size == 0


def test_a_range_measures_only_the_attacks_inside_it():
    """A passage's first gap starts at its own first attack, never reaching into the one before."""
    events = [note(0), note(500), note(1000), note(1500)]
    whole = intervals_from_events(events)
    part = intervals_from_events(events, start_seconds=1.0, end_seconds=2.0)
    assert whole.count == 3
    assert part.count == 1
    assert part.attack_count == 2


def test_a_range_that_ends_before_it_starts_is_refused():
    with pytest.raises(ValueError, match="must end after"):
        intervals_from_events([note(0)], start_seconds=2.0, end_seconds=1.0)


def test_an_empty_stretch_describes_itself_without_failing():
    empty = intervals_from_events([], start_seconds=0.0, end_seconds=10.0)
    assert empty.count == 0
    assert empty.median_ms == 0.0
    assert "no gaps" in empty.describe()


# --------------------------------------------------------------------------- D-07


def test_snapping_before_measuring_splits_a_peak_in_two():
    """**The D-07 regression. Never delete this test.**

    The same playing, measured two ways. On raw times the shuffle shows the peaks that are really
    there. On snapped columns every one of them splits, because a 337 ms gap becomes 8 or 9 columns
    of 40 ms depending on where the pair happens to fall, and the user is then asked to name a peak
    that does not exist.
    """
    events = swung_run(count=400)

    raw_gaps = intervals_from_events(events).values_ms
    raw_peaks = peaks_of(raw_gaps)
    raw_centres = [peak.centre_ms for peak in raw_peaks]
    assert len(raw_peaks) == 2
    assert raw_centres[0] == pytest.approx(125.0, abs=8.0)
    assert raw_centres[1] == pytest.approx(211.0, abs=8.0)

    # The same events, snapped to 40 ms columns first, then measured. `peaks_of` would refuse
    # these, which is the point of the guard, so the density is built directly here.
    columns = np.array([frame_of_seconds(event.start) for event in events], dtype=float)
    snapped_gaps = np.diff(columns) * 40.0
    grid = density_grid()
    snapped_peaks = find_peaks(snapped_gaps, grid, gaussian_kde(snapped_gaps, grid, 12.0))

    snapped_centres = [peak.centre_ms for peak in snapped_peaks]
    assert len(snapped_peaks) > len(raw_peaks)
    assert any(abs(centre - 120.0) < 6.0 for centre in snapped_centres)
    assert any(abs(centre - 160.0) < 6.0 for centre in snapped_centres)
    assert any(abs(centre - 200.0) < 6.0 for centre in snapped_centres)
    assert any(abs(centre - 240.0) < 6.0 for centre in snapped_centres)


def test_gaps_taken_from_columns_are_refused_outright():
    """The guard that stops the split above from ever reaching the user."""
    from_columns = np.array([320.0, 200.0, 320.0, 360.0, 120.0, 320.0, 240.0, 680.0])
    with pytest.raises(ValueError, match="snapped columns"):
        check_measured_on_raw_times(from_columns)
    with pytest.raises(ValueError, match="snapped columns"):
        peaks_of(from_columns)


def test_a_handful_of_gaps_is_not_enough_to_accuse_anyone():
    """Three round numbers can happen by chance; forty cannot."""
    check_measured_on_raw_times(np.array([320.0, 400.0, 240.0]))


def test_real_playing_passes_the_guard():
    check_measured_on_raw_times(intervals_from_events(swung_run(count=100)).values_ms)


# --------------------------------------------------------------------------- peaks


def test_a_peak_reports_how_much_of_the_data_it_holds():
    peaks = peaks_of(intervals_from_events(swung_run(count=400)).values_ms)
    assert sum(peak.share for peak in peaks) == pytest.approx(1.0, abs=0.05)
    assert all(peak.lo_ms < peak.centre_ms <= peak.hi_ms for peak in peaks)
    assert all(peak.mass > 0 for peak in peaks)


def test_a_pile_too_small_to_name_is_not_offered():
    """One stray gap among four hundred is not a rhythm the user should be asked about."""
    events = swung_run(count=400) + [note(999_000, 60)]
    centres = [peak.centre_ms for peak in peaks_of(intervals_from_events(events).values_ms)]
    assert all(centre < 900 for centre in centres)


def test_nothing_to_measure_gives_no_peaks():
    assert peaks_of(np.empty(0)) == []


# --------------------------------------------------------------------------- ladder


def test_naming_one_peak_fixes_every_figure():
    ladder = build_ladder(FigureName.NEGRA, 320.0)
    assert ladder.ms_by_figure[FigureName.NEGRA] == 320.0
    assert ladder.ms_by_figure[FigureName.CORCHEA] == 160.0
    assert ladder.ms_by_figure[FigureName.SEMICORCHEA] == 80.0
    assert ladder.ms_by_figure[FigureName.BLANCA] == 640.0
    assert ladder.ms_by_figure[FigureName.DOTTED_NEGRA] == 480.0
    assert len(ladder.ms_by_figure) == 9


def test_the_anchor_does_not_have_to_be_the_negra():
    ladder = build_ladder(FigureName.CORCHEA, 160.0)
    assert ladder.ms_by_figure[FigureName.NEGRA] == 320.0


def test_a_gap_between_two_figures_is_decided_by_proportion_not_by_milliseconds():
    """D-11, the 120 ms case. In milliseconds it is a coin toss; in proportion it is not."""
    ladder = build_ladder(FigureName.NEGRA, 320.0)
    assert abs(120.0 - 160.0) == abs(120.0 - 80.0)
    fit = nearest_figure(120.0, ladder)
    assert fit.figure == FigureName.CORCHEA
    assert fit.fit_error == pytest.approx(abs(np.log2(120.0 / 160.0)))


def test_both_halves_of_a_swung_pair_are_corcheas():
    """D-12. This is the whole reason the dotted corchea is banned from the vocabulary."""
    ladder = build_ladder(FigureName.NEGRA, 337.0)
    assert nearest_figure(211.0, ladder).figure == FigureName.CORCHEA
    assert nearest_figure(125.0, ladder).figure == FigureName.CORCHEA


def test_the_preview_labels_every_peak_so_the_choice_can_be_judged():
    peaks = peaks_of(intervals_from_events(swung_run(count=400)).values_ms)
    labels = label_peaks(peaks, build_ladder(FigureName.NEGRA, 337.0))
    assert [label.fit.figure for label in labels] == [FigureName.CORCHEA, FigureName.CORCHEA]
    assert all(label.fit.percent_off >= 0 for label in labels)


def test_a_figure_shift_renames_without_moving_anything():
    """D-18. Every millisecond value is kept; only the names change."""
    ladder = build_ladder(FigureName.NEGRA, 300.0)
    longer = shift_ladder(ladder, 1)
    assert longer.anchor_figure == FigureName.DOTTED_NEGRA
    assert longer.anchor_ms == 300.0
    two_steps = shift_ladder(ladder, 2)
    assert two_steps.anchor_figure == FigureName.BLANCA
    assert two_steps.ms_by_figure[FigureName.NEGRA] == 150.0


def test_a_shift_past_the_end_of_the_vocabulary_is_refused():
    with pytest.raises(ValueError, match="leaves the vocabulary"):
        shift_ladder(build_ladder(FigureName.REDONDA, 1280.0), 1)


def test_the_header_prints_the_ladder_and_its_tempo_equivalent():
    """D-20. This replaces the old tempo mark."""
    ladder = build_ladder(FigureName.NEGRA, 320.0)
    assert bpm_of(ladder) == pytest.approx(187.5)
    assert header_label(ladder) == "negra = 320 ms · ≈188 BPM"


def test_an_impossible_ladder_is_refused():
    with pytest.raises(ValueError):
        build_ladder(FigureName.NEGRA, 0)
    with pytest.raises(ValueError):
        nearest_figure(0, build_ladder(FigureName.NEGRA, 320.0))


# --------------------------------------------------------------------------- shape


def test_an_interval_set_describes_itself_in_a_sentence():
    events = [note(0), note(337), note(548)]
    measured = intervals_from_events(events)
    assert isinstance(measured, IntervalSet)
    assert measured.values_ms.tolist() == pytest.approx([337.0, 211.0])
    assert measured.describe() == (
        "2 gaps from 3 attacks between 0.00 s and 0.55 s, median 274.0 ms."
    )


# --------------------------------------------------------------------------- the real piece

POC_DATA = Path(__file__).resolve().parents[2] / "poc-onset-duration-distribution" / "data"


def load_poc_grid(name: str) -> np.ndarray:
    stored = np.load(POC_DATA / name, allow_pickle=True)
    grid = np.zeros(tuple(stored["shape"]), dtype=np.int8)
    grid[stored["row"], stored["col"]] = stored["data"]
    return grid


def right_hand_events_of_segment_a() -> list[NoteEvent]:
    """The right hand of *Mr Blue Sky*, first section, from the stored transcription.

    The hand of each event is read from the two one-hand matrices the app saved, which are a
    partition of the transcription: every onset is in exactly one of them. The event keeps its exact
    float onset time, so the matrices are consulted for identity only and never for timing.
    """
    payload = json.loads((POC_DATA / "events.json").read_text())
    right, left = (
        load_poc_grid("two-hands_semicorchea_right.npz"),
        load_poc_grid("two-hands_semicorchea_left.npz"),
    )
    # The stored grids were written at a semicorchea step; recover it from the raw column count.
    raw_columns = load_poc_grid("raw.npz").shape[1]
    tempo_bpm = raw_columns * 0.0625 * 60.0 / float(payload["durationSeconds"])
    step = 0.25 * 60.0 / tempo_bpm

    events: list[NoteEvent] = []
    for entry in payload["events"]:
        row = entry["midiNote"] - 21
        if not 0 <= row < 88:
            continue
        column = int(round(entry["start"] / step))
        for delta in (0, -1, 1, -2, 2):
            candidate = column + delta
            if not 0 <= candidate < right.shape[1]:
                continue
            if right[row, candidate] == 1:
                events.append(
                    NoteEvent(midi_note=entry["midiNote"], start=entry["start"], end=entry["end"])
                )
                break
            if left[row, candidate] == 1:
                break
    return events


@pytest.mark.skipif(not POC_DATA.exists(), reason="the PoC transcription is not in this checkout")
def test_the_real_piece_reproduces_the_measured_peak_table():
    """Phase 2's exit criterion, on the recording the whole refactor was designed from.

    ``poc-onset-duration-distribution/RESULTS.md`` reports six peaks for the right hand of the first
    section. This is the ported code producing the same six, to the millisecond, along with the same
    shares. If this drifts, the plot the user is asked to read has changed and the decisions taken
    from it need revisiting.
    """
    measured = intervals_from_events(right_hand_events_of_segment_a(), end_seconds=217.0)
    assert measured.count == 528

    found = peaks_of(measured.values_ms)
    assert [round(peak.centre_ms) for peak in found] == [125, 212, 337, 463, 674, 799]
    assert [peak.mass for peak in found] == [29, 87, 265, 41, 42, 23]

    dominant = found[2]
    assert dominant.median_ms == pytest.approx(337.2, abs=0.1)
    assert dominant.share == pytest.approx(0.502, abs=0.001)


@pytest.mark.skipif(not POC_DATA.exists(), reason="the PoC transcription is not in this checkout")
def test_naming_the_dominant_peak_a_negra_makes_the_swing_pair_two_corcheas():
    """The result the user is meant to see after one click, on the real piece."""
    measured = intervals_from_events(right_hand_events_of_segment_a(), end_seconds=217.0)
    found = peaks_of(measured.values_ms)
    ladder = build_ladder(FigureName.NEGRA, found[2].median_ms)

    named = {round(label.peak.centre_ms): label.fit.figure for label in label_peaks(found, ladder)}
    assert named[125] == FigureName.CORCHEA
    assert named[212] == FigureName.CORCHEA
    assert named[337] == FigureName.NEGRA
    assert named[674] == FigureName.BLANCA
    assert header_label(ladder) == "negra = 337 ms · ≈178 BPM"
