"""Check the audio of a part at every join (implementation 02, Phase 8).

A part whose timeline has several entries (files added, passages pasted, takes recorded) plays them
joined end to end: the engine's ``normalized.wav`` (16 kHz) and the joined FLAC the page plays. This
script compares each entry of both with the range of its own stored file, sample by sample, away
from the 5 ms fade at each join, and says how far apart they are. It reads only.

    docker compose exec -T backend python scripts/check_joins.py <partId> [<partId> ...]

Exit 1 when an entry differs from its file (more than one step of 16-bit audio), or the joined audio
is not as long as the entries together.
"""

from __future__ import annotations

import json
import sys

import numpy as np

from aitu_backend.audio import formats, sources, store
from aitu_backend.audio.frames import FADE_MS, FRAME_MS, SAMPLE_RATE, SAMPLES_PER_FRAME
from aitu_backend.storage import audio_files

#: One step of 16-bit audio, and a little more for the rounding of a resampler.
TOLERANCE = 3.0 / 32768.0


def _compare(joined: np.ndarray, own: np.ndarray, start: int, length: int, fade: int) -> float:
    inner = slice(start + fade, start + length - fade)
    mine = own[fade : length - fade]
    theirs = joined[inner]
    size = min(len(mine), len(theirs))
    if size <= 0:
        return 0.0
    return float(np.max(np.abs(mine[:size] - theirs[:size])))


def check(part_id: str) -> dict:
    entry = store.get(part_id)
    timeline = entry.timeline
    assert timeline is not None
    items = timeline.items() if timeline.source_list() else []
    report: dict = {"part": part_id, "entries": len(items), "joins": max(0, len(items) - 1)}
    if not timeline.joined:
        report["note"] = "one whole file: nothing joined"
        report["ok"] = True
        return report

    _, normalized = formats.read_wav(entry.normalized_path)
    listen_path = sources.ensure_listen(part_id, timeline)
    rate, channels = sources._probe(listen_path)
    listen = sources._decode(listen_path, rate, channels)
    per_frame = rate * FRAME_MS // 1000
    total = sum(last - first for _, first, last in items)
    report["seconds"] = total * FRAME_MS / 1000.0
    report["playedRate"] = rate
    report["lengthsMatch"] = (
        len(normalized) == total * SAMPLES_PER_FRAME and len(listen) == total * per_frame
    )

    worst = []
    position = 0
    own16: dict[str, np.ndarray] = {}
    own44: dict[str, np.ndarray] = {}
    for content_hash, first, last in items:
        extension = timeline.audio[content_hash].format
        if content_hash not in own16:
            _, own16[content_hash] = formats.read_wav(
                sources.source_wav(part_id, content_hash, extension)
            )
            # A decoded MP3 can go a little past full scale; the 16-bit joined file stores it at
            # full scale. Compared as stored.
            own44[content_hash] = np.clip(
                sources._decode(audio_files.file_path(content_hash, extension), rate, channels),
                -1.0,
                32767.0 / 32768.0,
            )
        frames = last - first
        sixteen = _compare(
            normalized,
            own16[content_hash][first * SAMPLES_PER_FRAME :],
            position * SAMPLES_PER_FRAME,
            frames * SAMPLES_PER_FRAME,
            int(SAMPLE_RATE * FADE_MS / 1000),
        )
        played = _compare(
            listen,
            own44[content_hash][first * per_frame :],
            position * per_frame,
            frames * per_frame,
            int(rate * FADE_MS / 1000),
        )
        worst.append(
            {
                "at": round(position * FRAME_MS / 1000.0, 2),
                "file": content_hash[:8],
                "range": [first, last],
                "engine": round(sixteen, 6),
                "played": round(played, 6),
            }
        )
        position += frames
    report["entriesChecked"] = worst
    report["ok"] = report["lengthsMatch"] and all(
        item["engine"] <= TOLERANCE and item["played"] <= TOLERANCE for item in worst
    )
    return report


def main(parts: list[str]) -> int:
    reports = [check(part) for part in parts]
    print(json.dumps(reports, indent=2))
    return 0 if all(report["ok"] for report in reports) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
