"""Finding the accompaniment figure: where is the pattern, and how long is one turn of it?

An accompaniment figuration is not a repeated *tune*. Chopin's left hand in the Fantaisie-Impromptu
climbs; Schubert's changes its bass note every bar; a nocturne's spreads and contracts. What
repeats is the **shape**: the same number of notes, at the same rhythmic spacing, tracing the same
contour, transposed to wherever the harmony has moved. Engravers make that shape visible by
breaking the beam at the bottom of each turn, which is the same thing said in ink.

So a figure is detected on four properties, in this order:

1. **isochrony** — the notes come at one steady spacing. Gaps are allowed, because a gap is often
   exactly the symptom we are hunting: a note the optimiser handed to the other hand.
2. **period** — a number of slots ``P`` such that consecutive turns trace the same shape.
3. **shape agreement, relative to each turn's own anchor** — this is what lets the harmony move
   underneath without the figure being declared broken.
4. **enough turns** — three, so that a coincidence between two bars is not a pattern.

Detection is deliberately run *before* any hand decision is judged, and gaps in one hand's stream
are filled from the other hand only when the contour predicts a note there. That is what makes the
result usable as evidence: the figure is defined by the music, not by the assignment we are trying
to score.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from itertools import pairwise
from statistics import median
from typing import Any

from aitu_backend.hands.config import FigureModel
from aitu_backend.hands.events import DecodedMatrix, NoteEvent

LEFT = "left"
RIGHT = "right"
HANDS = (LEFT, RIGHT)


@dataclass
class Figure:
    """One detected figuration."""

    seed_hand: str
    """The hand whose stream the figure was found in. Not a verdict — just where we looked."""

    period: int
    ioi: float
    slots: list[list[str]]
    """``slots[i]`` is the onset ids occupying grid slot ``i`` (usually one, sometimes none)."""

    absorbed: set[str] = field(default_factory=set)
    """Onsets pulled in from the other hand because the contour predicted a note there."""

    match: float = 0.0
    coverage: float = 0.0
    n_cycles: int = 0
    start_time: float = 0.0
    end_time: float = 0.0
    pitch_lo: int = 0
    pitch_hi: int = 0

    @property
    def onset_ids(self) -> list[str]:
        return [oid for slot in self.slots for oid in slot]

    @property
    def confidence(self) -> float:
        """How much this figure should be allowed to influence anything.

        Long, complete, well-matched figures speak loudly; a marginal three-turn fragment with
        holes in it barely whispers.
        """
        turns = min(1.0, (self.n_cycles - 1) / 4.0)
        return max(0.0, self.match * self.coverage * turns)

    def phase_of(self) -> dict[str, int]:
        return {oid: i % self.period for i, slot in enumerate(self.slots) for oid in slot}

    def cycle_of(self) -> dict[str, int]:
        return {oid: i // self.period for i, slot in enumerate(self.slots) for oid in slot}

    def to_dict(self) -> dict[str, Any]:
        return {
            "seedHand": self.seed_hand,
            "period": self.period,
            "ioi": round(self.ioi, 4),
            "cycles": self.n_cycles,
            "match": round(self.match, 3),
            "coverage": round(self.coverage, 3),
            "confidence": round(self.confidence, 3),
            "startTime": round(self.start_time, 3),
            "endTime": round(self.end_time, 3),
            "pitchRange": [self.pitch_lo, self.pitch_hi],
            "onsets": self.onset_ids,
            "absorbed": sorted(self.absorbed),
        }


# --------------------------------------------------------------------------------------
# step 1 — one hand's stream, laid on a steady grid
# --------------------------------------------------------------------------------------


BOTH = "both"


def _hand_slots(
    decoded: DecodedMatrix, hand_map: dict[str, str], hand: str
) -> list[tuple[float, list[NoteEvent]]]:
    """``(time, events)`` for every onset group in which this hand strikes something.

    ``hand=BOTH`` returns the merged stream. That third pass exists for one specific failure: a
    figure the optimiser divided roughly in half is a minority of *both* hand streams, so neither
    is complete enough to recognise, and the figure vanishes exactly when it most needs finding.
    The merged stream sees it whole. Dense two-hand textures do not survive this pass, because
    their slots carry two notes at once and the chordal-fraction test throws them out.
    """
    out: list[tuple[float, list[NoteEvent]]] = []
    for group in decoded.groups:
        mine = (
            list(group.events)
            if hand == BOTH
            else [e for e in group.events if hand_map[e.onset_id] == hand]
        )
        if mine:
            out.append((group.time_seconds, mine))
    return out


def _unit_spacing(times: list[float]) -> float | None:
    """The steady note spacing of a stream, or None if it has no steady spacing."""
    diffs = [b - a for a, b in zip(times, times[1:]) if b > a]
    if len(diffs) < 3:
        return None
    smallest = min(diffs)
    # the unit is the smallest spacing that a decent share of the stream actually uses;
    # a figure interrupted by longer rests still has its unit at the short end.
    near = [d for d in diffs if abs(d - smallest) <= 0.2 * smallest]
    if len(near) < max(3, 0.25 * len(diffs)):
        return float(median(diffs))
    return float(median(near))


def _runs_on_grid(
    slots: list[tuple[float, list[NoteEvent]]], unit: float, params: FigureModel
) -> list[list[list[NoteEvent] | None]]:
    """Cut the stream into maximal runs that sit on a grid of ``unit`` seconds.

    Every element of a run is one grid slot: the events struck there, or ``None`` for a hole.
    Holes matter — a hole is where a note may have gone missing to the other hand.
    """
    runs: list[list[list[NoteEvent] | None]] = []
    current: list[list[NoteEvent] | None] = []
    tol = params.ioi_tolerance * unit

    for index, (time, events) in enumerate(slots):
        if not current:
            current = [events]
            continue
        gap = time - slots[index - 1][0]
        steps = round(gap / unit) if unit > 0 else 0
        if (
            steps < 1
            or abs(gap - steps * unit) > tol * max(1, steps)
            or (steps - 1 > params.max_gap_slots)
        ):
            if len(current) >= 4:
                runs.append(current)
            current = [events]
            continue
        current.extend([None] * (steps - 1))
        current.append(events)
    if len(current) >= 4:
        runs.append(current)
    return runs


# --------------------------------------------------------------------------------------
# step 2 — the period, and whether the shape really repeats
# --------------------------------------------------------------------------------------


def _slot_pitch(events: list[NoteEvent] | None) -> float | None:
    """One number per slot. The lowest note is the right choice: it is the note engravers break
    the beam on, and it is the most stable member of a spread chord."""
    if not events:
        return None
    return float(min(e.midi for e in events))


def _score_period(
    pitches: list[float | None], period: int, params: FigureModel
) -> tuple[float, int]:
    """``(agreement, turns)`` for one candidate period.

    Each turn is compared with the one before it, *after* subtracting each turn's own anchor, so a
    figure whose harmony moves still counts as the same shape.
    """
    n_cycles = len(pitches) // period
    if n_cycles < params.min_cycles:
        return 0.0, n_cycles

    shapes: list[dict[int, float]] = []
    anchors: list[float | None] = []
    for c in range(n_cycles):
        turn = pitches[c * period : (c + 1) * period]
        known = {k: p for k, p in enumerate(turn) if p is not None}
        if not known:
            shapes.append({})
            anchors.append(None)
            continue
        anchor = min(known.values())
        anchors.append(anchor)
        shapes.append({k: p - anchor for k, p in known.items()})

    # --- the beam break: the turn's lowest note must sit at a settled phase -----------------
    low_phases = [min(shape, key=lambda k: shape[k]) for shape in shapes if len(shape) >= 2]
    if len(low_phases) < params.min_cycles:
        return 0.0, n_cycles
    modal = Counter(low_phases).most_common(1)[0][1]
    if modal / len(low_phases) < params.min_anchor_consistency:
        return 0.0, n_cycles

    # --- and the turn has to cover some ground ----------------------------------------------
    spans = [max(shape.values()) - min(shape.values()) for shape in shapes if len(shape) >= 2]
    if not spans or median(spans) < params.min_cycle_span:
        return 0.0, n_cycles

    # --- consecutive turns must sit on top of each other, not end to end --------------------
    ranges = [
        (anchors[c], anchors[c] + max(shapes[c].values()))
        for c in range(n_cycles)
        if anchors[c] is not None and len(shapes[c]) >= 2
    ]
    if len(ranges) >= 2:
        overlaps = [min(a[1], b[1]) - max(a[0], b[0]) >= 0 for a, b in pairwise(ranges)]
        if sum(overlaps) / len(overlaps) < params.min_cycle_overlap:
            return 0.0, n_cycles

    agreed = compared = 0
    for c in range(1, n_cycles):
        a, b = shapes[c - 1], shapes[c]
        if anchors[c - 1] is not None and anchors[c] is not None:
            if abs(anchors[c] - anchors[c - 1]) > params.max_anchor_drift:
                return 0.0, n_cycles
        for k in set(a) & set(b):
            compared += 1
            if abs(a[k] - b[k]) <= params.shape_tolerance:
                agreed += 1
    if compared == 0:
        return 0.0, n_cycles
    return agreed / compared, n_cycles


def _best_period(pitches: list[float | None], params: FigureModel) -> tuple[int, float, int]:
    """The smallest period that explains the run well. Smallest matters: a four-note figure also
    'repeats' every eight slots, and reporting eight would halve the turn count and blur the
    phase structure the cost relies on."""
    best = (0, 0.0, 0)
    for period in range(params.min_period, params.max_period + 1):
        if len(pitches) // period < params.min_cycles:
            break
        match, cycles = _score_period(pitches, period, params)
        if cycles * period < params.min_onsets:
            continue
        if match >= params.min_match and match > best[1] + 1e-9:
            best = (period, match, cycles)
            if match > 0.98:
                break  # a clean fit at the smallest period; no need to look wider
    return best


# --------------------------------------------------------------------------------------
# step 3 — recover the notes the other hand took
# --------------------------------------------------------------------------------------


def _modal_shape(pitches: list[float | None], period: int) -> tuple[dict[int, float], float]:
    """The figure's canonical turn (median offset from its own anchor) and its drift per turn.

    Only *complete* turns are used to build the shape when there are enough of them. An
    incomplete turn has a misleading anchor — if the note that went missing is the low one, the
    turn appears to start higher than it does — and letting those into the median poisons exactly
    the prediction we need to recover the missing note.
    """
    n_cycles = len(pitches) // period
    turns = [pitches[c * period : (c + 1) * period] for c in range(n_cycles)]
    complete = [t for t in turns if all(p is not None for p in t)]
    source = (
        complete if len(complete) >= 2 else [t for t in turns if sum(p is not None for p in t) >= 2]
    )

    per_phase: dict[int, list[float]] = {}
    for turn in source:
        known = {k: p for k, p in enumerate(turn) if p is not None}
        if len(known) < 2:
            continue
        anchor = min(known.values())
        for k, p in known.items():
            per_phase.setdefault(k, []).append(p - anchor)
    shape = {k: float(median(v)) for k, v in per_phase.items()}
    if not shape:
        return {}, 0.0
    floor = min(shape.values())
    shape = {k: v - floor for k, v in shape.items()}

    anchors = [a for a in (_anchor_of(turn, shape) for turn in turns) if a is not None]
    drift = float(median([b - a for a, b in pairwise(anchors)])) if len(anchors) > 1 else 0.0
    return shape, drift


def _anchor_of(turn: list[float | None], shape: dict[int, float]) -> float | None:
    """Where this turn sits, inferred from whichever of its notes survive.

    Subtracting the canonical shape from every known note gives one estimate of the anchor per
    note; their median is robust to a note being missing, including the low one.
    """
    estimates = [p - shape[k] for k, p in enumerate(turn) if p is not None and k in shape]
    return float(median(estimates)) if estimates else None


def _predict(pitches: list[float | None], slot: int, period: int) -> float | None:
    """What pitch the contour expects in an empty slot.

    Taking the pitch of the same phase in the nearest turn is not enough: a figure that climbs
    (Schubert) or whose harmony moves (Chopin) is a different pitch every turn, and the naive
    prediction misses by exactly the drift. The turn's canonical shape plus the anchor carried
    forward at the observed drift gets it right.
    """
    shape, drift = _modal_shape(pitches, period)
    phase = slot % period
    if phase not in shape:
        return None
    anchor = _anchor_at(pitches, period, slot // period, shape, drift)
    return None if anchor is None else anchor + shape[phase]


def _anchor_at(
    pitches: list[float | None],
    period: int,
    cycle: int,
    shape: dict[int, float],
    drift: float,
) -> float | None:
    """The anchor of a turn: measured if any of its notes survive, extrapolated otherwise."""
    n_cycles = max(1, len(pitches) // period)
    if 0 <= cycle < n_cycles:
        here = _anchor_of(pitches[cycle * period : (cycle + 1) * period], shape)
        if here is not None:
            return here
    known = [
        (abs(c - cycle), c, _anchor_of(pitches[c * period : (c + 1) * period], shape))
        for c in range(n_cycles)
    ]
    known = [k for k in known if k[2] is not None]
    if not known:
        return None
    _distance, reference, anchor = min(known)
    return anchor + drift * (cycle - reference)


def _group_at(decoded: DecodedMatrix, stamp: float, tol: float):
    best = None
    for group in decoded.groups:
        delta = abs(group.time_seconds - stamp)
        if delta <= tol and (best is None or delta < best[0]):
            best = (delta, group)
    return None if best is None else best[1]


def _extend(
    run_slots: list[list[NoteEvent] | None],
    pitches: list[float | None],
    period: int,
    start_time: float,
    unit: float,
    decoded: DecodedMatrix,
    params: FigureModel,
) -> tuple[float, set[str]]:
    """Grow the figure past the stream it was found in, one whole turn at a time.

    A figure that migrates from one hand to the other — Schubert's left hand climbing out of the
    bass staff, half of it handed to the right hand by the optimiser — is only ever detected as
    its tail, because detection starts from one hand's notes. Extending by extrapolated turns and
    absorbing whatever hand actually played them recovers the rest, and that matters: the repair
    must know the figure begins in the bass, or it will 'fix' the beginning instead of the end.
    """
    absorbed: set[str] = set()
    tol = params.ioi_tolerance * unit

    for direction in (-1, 1):
        for _ in range(16):
            shape, drift = _modal_shape(pitches, period)
            if len(shape) < 2:
                break
            n_cycles = len(pitches) // period
            if direction < 0:
                predicted_anchor = _anchor_at(pitches, period, -1, shape, drift)
                base_time = start_time - period * unit
            else:
                predicted_anchor = _anchor_at(pitches, period, n_cycles, shape, drift)
                base_time = start_time + n_cycles * period * unit
            if predicted_anchor is None:
                break

            found: list[tuple[int, NoteEvent]] = []
            for k in range(period):
                if k not in shape:
                    continue
                group = _group_at(decoded, base_time + k * unit, tol)
                if group is None:
                    continue
                target = predicted_anchor + shape[k]
                near = [e for e in group.events if abs(e.midi - target) <= params.absorb_tolerance]
                if near:
                    found.append((k, min(near, key=lambda e: abs(e.midi - target))))
            if len(found) < max(2, (2 * len(shape)) // 3):
                break

            block: list[list[NoteEvent] | None] = [None] * period
            block_pitches: list[float | None] = [None] * period
            for k, event in found:
                block[k] = [event]
                block_pitches[k] = float(event.midi)
                absorbed.add(event.onset_id)
            if direction < 0:
                run_slots[:0] = block
                pitches[:0] = block_pitches
                start_time = base_time
            else:
                run_slots.extend(block)
                pitches.extend(block_pitches)
    return start_time, absorbed


def _absorb(
    run_slots: list[list[NoteEvent] | None],
    pitches: list[float | None],
    period: int,
    start_time: float,
    unit: float,
    decoded: DecodedMatrix,
    hand_map: dict[str, str],
    hand: str,
    params: FigureModel,
) -> set[str]:
    """Pull the other hand's notes into the figure where a hole sits and the contour fits.

    Only holes are considered. A note the other hand plays *alongside* the figure is its own
    business; a note standing exactly where the figure has a gap, at the pitch the figure was
    going to play, is the figure's.
    """
    by_time: dict[int, list[NoteEvent]] = {}
    for group in decoded.groups:
        by_time[group.column] = list(group.events)
    times = {round(g.time_seconds, 6): g for g in decoded.groups}

    absorbed: set[str] = set()
    for index, slot in enumerate(run_slots):
        if slot:
            continue
        expected = _predict(pitches, index, period)
        if expected is None:
            continue
        stamp = round(start_time + index * unit, 6)
        group = times.get(stamp)
        if group is None:
            candidates = [
                g
                for g in decoded.groups
                if abs(g.time_seconds - stamp) <= params.ioi_tolerance * unit
            ]
            if not candidates:
                continue
            group = min(candidates, key=lambda g: abs(g.time_seconds - stamp))
        for event in group.events:
            if hand_map[event.onset_id] == hand:
                continue
            if abs(event.midi - expected) <= params.absorb_tolerance:
                absorbed.add(event.onset_id)
                run_slots[index] = [event]
                pitches[index] = float(event.midi)
                break
    return absorbed


# --------------------------------------------------------------------------------------
# detection
# --------------------------------------------------------------------------------------


def detect(
    decoded: DecodedMatrix,
    hand_map: dict[str, str],
    params: FigureModel,
) -> list[Figure]:
    """Every figuration visible in this reading of the music, both hands."""
    figures: list[Figure] = []
    streams = (*HANDS, BOTH) if params.merged_stream else HANDS
    for hand in streams:
        slots = _hand_slots(decoded, hand_map, hand)
        if len(slots) < params.min_period * params.min_cycles:
            continue
        unit = _unit_spacing([t for t, _ in slots])
        if unit is None or unit <= 0:
            continue

        offset = 0
        for run in _runs_on_grid(slots, unit, params):
            # locate this run's start time back in the stream
            first_events = next(s for s in run if s)
            start_time = min(e.onset_time for e in first_events)

            filled = sum(1 for s in run if s)
            if filled < params.min_period * params.min_cycles:
                continue
            if 1.0 - filled / len(run) > params.max_gap_fraction:
                continue
            chordal = sum(1 for s in run if s and len(s) > 1)
            if chordal / filled > params.max_chordal_fraction:
                continue

            pitches = [_slot_pitch(s) for s in run]
            period, match, cycles = _best_period(pitches, params)
            if period == 0:
                continue

            run_copy: list[list[NoteEvent] | None] = list(run)
            absorbed = _absorb(
                run_copy, pitches, period, start_time, unit, decoded, hand_map, hand, params
            )
            start_time, grown = _extend(
                run_copy, pitches, period, start_time, unit, decoded, params
            )
            absorbed |= grown
            # re-score with the recovered notes in place: a figure that only looked ragged
            # because a note was taken from it should now read as clean
            period2, match2, cycles2 = _best_period(pitches, params)
            if period2:
                period, match, cycles = period2, match2, cycles2

            usable = cycles * period
            run_copy = run_copy[:usable]
            if not any(run_copy):
                continue
            events = [e for s in run_copy if s for e in s]
            if not events:
                continue

            figures.append(
                Figure(
                    seed_hand=hand,
                    period=period,
                    ioi=unit,
                    slots=[[e.onset_id for e in s] if s else [] for s in run_copy],
                    absorbed={
                        a
                        for a in absorbed
                        if any(a == e.onset_id for s in run_copy if s for e in s)
                    },
                    match=match,
                    coverage=sum(1 for s in run_copy if s) / max(1, len(run_copy)),
                    n_cycles=cycles,
                    start_time=min(e.onset_time for e in events),
                    end_time=max(e.end_time for e in events),
                    pitch_lo=min(e.midi for e in events),
                    pitch_hi=max(e.midi for e in events),
                )
            )
            offset += len(run)

    return _deduplicate(figures)


def _deduplicate(figures: list[Figure]) -> list[Figure]:
    """Both hands' streams can find the same figure. Keep the more confident reading."""
    kept: list[Figure] = []
    for figure in sorted(figures, key=lambda f: -f.confidence):
        mine = set(figure.onset_ids)
        if any(len(mine & set(other.onset_ids)) > 0.6 * len(mine) for other in kept):
            continue
        kept.append(figure)
    return sorted(kept, key=lambda f: (f.start_time, f.pitch_lo))


def owner_of(figure: Figure, hand_map: dict[str, str]) -> str:
    """The hand that holds most of the figure — the one the pattern belongs to.

    An exact tie is decided by whoever started it, which is the hand that would have to give up
    least to keep going. (``seed_hand`` can be ``BOTH`` for a figure found in the merged stream,
    so it is never a valid answer here.)
    """
    ids = figure.onset_ids
    counts = Counter(hand_map[oid] for oid in ids)
    if counts[LEFT] != counts[RIGHT]:
        return counts.most_common(1)[0][0]
    if figure.seed_hand in HANDS:
        return figure.seed_hand
    return hand_map[ids[0]] if ids else LEFT


def summarise(figures: list[Figure]) -> dict[str, Any]:
    return {
        "count": len(figures),
        "onsets": sum(len(f.onset_ids) for f in figures),
        "periods": dict(sorted(Counter(f.period for f in figures).items())),
        "absorbed": sum(len(f.absorbed) for f in figures),
        "meanConfidence": (
            round(sum(f.confidence for f in figures) / len(figures), 3) if figures else 0.0
        ),
    }


detect_figures = detect


__all__ = [
    "BOTH",
    "Figure",
    "detect",
    "detect_figures",
    "owner_of",
    "summarise",
]
