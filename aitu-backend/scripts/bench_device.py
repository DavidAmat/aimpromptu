"""The engines on the CPU and on the GPU, from inside the backend container (implementation 08, Phase 3).

    make up                       # or: docker compose run --rm --no-deps backend ...
    docker compose exec backend python scripts/bench_device.py
    docker compose exec backend python scripts/bench_device.py --uuid 1a16a836 --skip-cpu

For one piece (Superestrella by default) it measures:

1. **ByteDance** on ``cpu`` and on ``cuda``: the time to build the engine, the time to transcribe
   the whole ``normalized.wav``, and how far apart the two lists of notes are. ByteDance is the
   baseline because it already took a ``device`` before this phase.
2. **MuScriptor** ``large`` on ``cuda``, with the settings Phase 1 chose (float16, batch 1, prelude
   forcing, conditioned on ``acoustic_piano``), through ``pmn.muscriptor.MuScriptorAssembler``. Its
   notes are compared with the ones Phase 1 got outside any container
   (``pocs/poc-muscriptor/out/full/large-float16-b1-prelude/notes.json``, Superestrella only).

"x real" is seconds of audio per second of processing. The answer is printed and written as JSON
to ``--out``.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import time
from pathlib import Path


from aitu_backend.storage import paths

SUPERESTRELLA = "a585f9eb-36a1-49a0-9f0c-2626f3d292da"
PHASE_1_NOTES = (
    paths.repo_root()
    / "pocs"
    / "poc-muscriptor"
    / "out"
    / "full"
    / "large-float16-b1-prelude"
    / "notes.json"
)
DEFAULT_OUT = (
    paths.repo_root()
    / "context"
    / "implementations"
    / "08-new-algorithm-notes-detection-muscriptor"
    / "measurements"
    / "phase-3-device.json"
)


def _piece(prefix: str) -> Path:
    matches = sorted(p for p in paths.audio_root().iterdir() if p.name.startswith(prefix))
    if len(matches) != 1:
        raise SystemExit(f"{len(matches)} pieces start with {prefix!r}")
    return matches[0]


def _sync() -> None:
    import torch  # noqa: PLC0415

    if torch.cuda.is_available():
        torch.cuda.synchronize()


def _compare(a: list[tuple[int, float]], b: list[tuple[int, float]], tol_ms: float) -> dict:
    """Notes of ``a`` with a note of the same key in ``b`` within ``tol_ms``, matched one to one."""
    by_key: dict[int, list[float]] = {}
    for key, on in b:
        by_key.setdefault(key, []).append(on)
    for ons in by_key.values():
        ons.sort()
    used: set[tuple[int, int]] = set()
    matched = 0
    worst = 0.0
    for key, on in sorted(a, key=lambda n: n[1]):
        ons = by_key.get(key, [])
        best, best_i = None, -1
        for i, other in enumerate(ons):
            if (key, i) in used:
                continue
            d = abs(other - on) * 1000.0
            if d <= tol_ms and (best is None or d < best):
                best, best_i = d, i
        if best is not None:
            used.add((key, best_i))
            matched += 1
            worst = max(worst, best)
    return {
        "notesA": len(a),
        "notesB": len(b),
        "matched": matched,
        "toleranceMs": tol_ms,
        "worstMatchedMs": round(worst, 3),
    }


def bytedance(wav: Path, device: str, duration_s: float) -> tuple[dict, list[tuple[int, float]]]:
    from aitu_backend.transcription.engine import ByteDanceEngine  # noqa: PLC0415

    t0 = time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()):
        engine = ByteDanceEngine(device=device)
    _sync()
    load_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()):
        events = engine.transcribe(wav)
    _sync()
    run_s = time.perf_counter() - t0
    notes = [(e.midi_note, float(e.start)) for e in events]
    return {
        "engine": "bytedance",
        "device": device,
        "loadS": round(load_s, 2),
        "transcribeS": round(run_s, 2),
        "xReal": round(duration_s / run_s, 2),
        "notes": len(notes),
    }, notes


def muscriptor(wav: Path, duration_s: float) -> tuple[dict, list[tuple[int, float]]]:
    import soundfile as sf  # noqa: PLC0415
    import torch  # noqa: PLC0415
    from muscriptor.transcription_model import TranscriptionModel  # noqa: PLC0415

    from aitu_backend.pmn.muscriptor import MuScriptorAssembler  # noqa: PLC0415

    data, rate = sf.read(str(wav), dtype="float32", always_2d=True)
    signal = torch.from_numpy(data.mean(axis=1).copy()).unsqueeze(0)

    t0 = time.perf_counter()
    model = TranscriptionModel.load_model("large", device="cuda", dtype="float16")
    _sync()
    load_s = time.perf_counter() - t0

    torch.cuda.reset_peak_memory_stats()
    assembler = MuScriptorAssembler()
    first_note_s = None
    t0 = time.perf_counter()
    # MuScriptor prints timing lines for every chunk with `print` (Phase 1 report, section 4).
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        for event in model.transcribe(
            (signal, rate),
            instruments=["acoustic_piano"],
            batch_size=1,
            prelude_forcing=True,
        ):
            if first_note_s is None and type(event).__name__ == "NoteStartEvent":
                first_note_s = time.perf_counter() - t0
            assembler.add(event)
    _sync()
    run_s = time.perf_counter() - t0
    notes = assembler.notes(end_ms=duration_s * 1000.0)
    pairs = [(int(k) + 21, float(on) / 1000.0) for k, on in zip(notes.key, notes.on_ms)]
    return {
        "engine": "muscriptor-large",
        "device": "cuda",
        "dtype": "float16",
        "loadS": round(load_s, 2),
        "transcribeS": round(run_s, 2),
        "firstNoteS": round(first_note_s or 0.0, 2),
        "xReal": round(duration_s / run_s, 2),
        "gpuPeakGB": round(torch.cuda.max_memory_allocated() / 1e9, 2),
        "notes": len(pairs),
    }, pairs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--uuid", default=SUPERESTRELLA, help="a piece uuid or its first letters")
    parser.add_argument("--skip-cpu", action="store_true", help="ByteDance on cuda only")
    parser.add_argument("--skip-muscriptor", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    import torch  # noqa: PLC0415

    piece = _piece(args.uuid)
    wav = piece / "normalized.wav"
    import soundfile as sf  # noqa: PLC0415

    duration_s = sf.info(str(wav)).duration
    result: dict = {
        "piece": piece.name,
        "durationS": round(duration_s, 2),
        "torch": torch.__version__,
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "runs": [],
    }
    print(f"{piece.name}  {duration_s:.1f} s  {result['gpu']}")

    by_device: dict[str, list[tuple[int, float]]] = {}
    for device in ([] if args.skip_cpu else ["cpu"]) + ["cuda"]:
        run, notes = bytedance(wav, device, duration_s)
        by_device[device] = notes
        result["runs"].append(run)
        print(json.dumps(run))
    if "cpu" in by_device:
        diff = _compare(by_device["cpu"], by_device["cuda"], tol_ms=1.0)
        result["bytedanceCpuAgainstCuda"] = diff
        print("bytedance cpu against cuda:", json.dumps(diff))

    if not args.skip_muscriptor:
        run, notes = muscriptor(wav, duration_s)
        result["runs"].append(run)
        print(json.dumps(run))
        if piece.name == SUPERESTRELLA and PHASE_1_NOTES.is_file():
            phase_1 = [
                (int(n["pitch"]), float(n["start"]))
                for n in json.loads(PHASE_1_NOTES.read_text())
                if n.get("instrument", "acoustic_piano") == "acoustic_piano"
            ]
            same = _compare(notes, phase_1, tol_ms=0.5)
            result["muscriptorAgainstPhase1Native"] = same
            print("muscriptor against the Phase 1 native run:", json.dumps(same))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(f"written {args.out}")


if __name__ == "__main__":
    main()
