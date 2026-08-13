"""Score aitu_backend.hands against the research benchmark it was ported from.

The 209 NBPS scenarios live in the `poc-piano-hand-prediction` repo, not here, so this
is a bridge rather than a test: it converts each scenario's dense matrix into a
``PianoMatrix``, runs whichever method is asked for, and scores the answer against the
same golden labels the PoC uses. Onset ids agree by construction (``c{col}:r{row}``),
so the comparison is note for note.

Run it when the cost model, the gate, the detector or the second pass changes. A number
that moves here is the only honest signal that the port still means what the research
said it meant.

    PYTHONPATH=src:<poc>/backend/src python3 scripts/benchmark_hands.py
"""

from __future__ import annotations

import argparse
import time

import numpy as np
from piano_hand_inference.scenarios import all_scenarios
from piano_hand_inference.scenarios.model import check_invariants
from piano_hand_inference.text_notation import parse_text_notation

from aitu_backend.hands import DEFAULT_CONFIG, decode_matrix, infer_hands
from aitu_backend.hands.figuration import detect
from aitu_backend.hands.staff import direction_of, ledger_lines
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.schemas.matrix import Granularity, MatrixProcessingStep

GRANULARITY = {
    "negra": Granularity.NEGRA,
    "corchea": Granularity.CORCHEA,
    "semicorchea": Granularity.SEMICORCHEA,
    "fusa": Granularity.FUSA,
}


def to_matrix(scenario) -> PianoMatrix:
    dense = parse_text_notation(scenario.notation)  # [time][key]
    grid = np.array(dense, dtype=np.int8).T  # (88, frames)
    return PianoMatrix.from_dense(
        grid,
        granularity=GRANULARITY[scenario.granularity],
        tempo_bpm=scenario.bpm,
        processing_step=MatrixProcessingStep.CLEAN,
    )


def severe(decoded, hand_of: dict[str, str], threshold: int = 3) -> int:
    """Onsets printed more than ``threshold`` ledger lines onto the other staff."""
    return sum(
        1
        for event in decoded.events
        if direction_of(event.midi, hand_of[event.onset_id]) == "across"
        and ledger_lines(event.midi, hand_of[event.onset_id]) > threshold
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--methods", default="beam,refine")
    args = parser.parse_args()

    scenarios = list(all_scenarios())
    baseline: dict[str, dict[str, str]] = {}

    for method in args.methods.split(","):
        config = DEFAULT_CONFIG.with_method(method)
        labelled = correct = exact = violations = sev = figures = broken = 0
        toward = away = 0
        started = time.perf_counter()
        for scenario in scenarios:
            matrix = to_matrix(scenario)
            result = infer_hands(matrix, config)
            hand_of = result.hand_of()
            decoded = decode_matrix(matrix)
            if method == args.methods.split(",")[0]:
                baseline[scenario.id] = dict(hand_of)

            golden = scenario.labels()
            hits = sum(1 for oid, hand in golden.items() if hand_of.get(oid) == hand)
            labelled += len(golden)
            correct += hits
            exact += int(bool(golden) and hits == len(golden))
            violations += len(check_invariants(scenario, hand_of))
            sev += severe(decoded, hand_of)
            found = detect(decoded, hand_of, config.figures)
            figures += len(found)
            broken += sum(1 for f in found if len({hand_of[o] for o in f.onset_ids}) > 1)
            for oid, hand in hand_of.items():
                base = baseline[scenario.id].get(oid)
                if base == hand or oid not in golden:
                    continue
                if hand == golden[oid]:
                    toward += 1
                elif base == golden[oid]:
                    away += 1
        elapsed = (time.perf_counter() - started) * 1000.0
        print(
            f"{method:8} accuracy={correct / labelled:.4f} exact={exact:3}/{len(scenarios)} "
            f"invariants={violations:2} severe={sev:3} figures={figures:3} broken={broken:2} "
            f"->correct={toward:3} ->wrong={away:3} {elapsed:7.0f} ms"
        )


if __name__ == "__main__":
    main()
