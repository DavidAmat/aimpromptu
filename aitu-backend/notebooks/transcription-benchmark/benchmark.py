"""Run every installed engine over the same clips and compare.

Not a unit test — a judgement aid. The plan says the human decides which engine
wins on real recordings, so this prints what a human needs to decide: how long
each took, how many notes it found, and where the two disagree.

Usage::

    cd aitu-backend
    uv run python notebooks/transcription-benchmark/benchmark.py <clip.wav> [more.wav ...]

    # or every audio already in the store:
    uv run python notebooks/transcription-benchmark/benchmark.py --store

Install engines first:

    uv sync --extra transcription      # bytedance (default)
    uv sync --extra basic-pitch        # the fallback
"""

from __future__ import annotations

import argparse
import time
from collections import Counter
from pathlib import Path

from aitu_backend.audio import store
from aitu_backend.matrix.keys import build_grand_piano_rows, midi_to_row
from aitu_backend.transcription.engine import (
    ENGINES,
    EngineUnavailable,
    NoteEvent,
    create_engine,
)

KEY_NAMES = build_grand_piano_rows()


def describe(events: list[NoteEvent]) -> str:
    if not events:
        return "no notes"
    pitches = Counter()
    for event in events:
        try:
            pitches[KEY_NAMES[midi_to_row(event.midi_note)]] += 1
        except ValueError:
            pitches["<off keyboard>"] += 1
    common = ", ".join(f"{name} x{count}" for name, count in pitches.most_common(5))
    span = max(event.end for event in events) - min(event.start for event in events)
    return f"{len(events)} notes over {span:.2f}s — most common: {common}"


def first_notes(events: list[NoteEvent], count: int = 8) -> str:
    """The opening notes, which is what you actually recognize by eye."""
    names = []
    for event in sorted(events, key=lambda item: item.start)[:count]:
        try:
            names.append(f"{KEY_NAMES[midi_to_row(event.midi_note)]}@{event.start:.2f}s")
        except ValueError:
            names.append(f"MIDI{event.midi_note}@{event.start:.2f}s")
    return " ".join(names) or "—"


def run(clips: list[Path]) -> None:
    engines = {}
    for name in ENGINES:
        if name == "silent":
            continue
        try:
            engines[name] = create_engine(name)
        except EngineUnavailable as exc:
            print(f"[skip] {name}: {exc}")
        except Exception as exc:  # a model that fails to load
            print(f"[skip] {name}: {exc}")

    if not engines:
        print("\nNo engines installed. Try: uv sync --extra transcription")
        return

    for clip in clips:
        print(f"\n=== {clip.name} " + "=" * max(0, 60 - len(clip.name)))
        for name, engine in engines.items():
            started = time.perf_counter()
            try:
                events = engine.transcribe(clip)
            except Exception as exc:
                print(f"  {name:<14} FAILED: {exc}")
                continue
            elapsed = time.perf_counter() - started
            print(f"  {name:<14} {elapsed:6.2f}s  {describe(events)}")
            print(f"  {'':<14} first: {first_notes(events)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("clips", nargs="*", type=Path, help="WAV files to transcribe")
    parser.add_argument(
        "--store", action="store_true", help="use every normalized audio in the audio store"
    )
    args = parser.parse_args()

    clips = list(args.clips)
    if args.store:
        clips += [entry.normalized_path for entry in store.list_all() if entry.has_normalized()]
    if not clips:
        parser.error("Give at least one clip, or pass --store")

    run(clips)


if __name__ == "__main__":
    main()
