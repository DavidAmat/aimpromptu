"""Time **Read notes** of the Video step, stage by stage (implementation 02, Phase 5, Q-8).

Q-8 asks whether the video reader can send its notes while it reads, as MuScriptor does. This runs
the whole reading of one video project and says how long each stage takes, and when the first and
the last notes of the piece are known, so the answer rests on a measurement.

It works on a **temporary copy**: the project is duplicated as the master user, the video folder
(the file, its metadata and its piano overlay; ``--keep-frames`` also its sampled frames) is copied
into the copy's temporary folder, the reading runs there, and the copy is deleted at the end. The
real project is only read.

Run inside the backend container, where the database is mounted::

    docker compose exec backend python scripts/bench_video_read.py b99bc3ae-30a5-4aa0-9b3b-8f11eea5fba7
"""

from __future__ import annotations

import argparse
import json
import shutil
import time
from collections import defaultdict

from aitu_backend.db.users import ensure_master_user
from aitu_backend.progress import CallbackProgress, ProgressEvent
from aitu_backend.storage import bundle, paths
from aitu_backend.video import piece, store

VIDEO_FILES = ("source.mp4", "metadata_video.json", "calibration.json")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("project", help="the id of a project with a video")
    parser.add_argument(
        "--keep-frames",
        action="store_true",
        help="copy the sampled frames too, so the sampling is not timed",
    )
    args = parser.parse_args()

    owner = ensure_master_user()
    copy = bundle.duplicate_project(args.project, owner_id=owner, title="bench (temporary)")
    try:
        source = paths.video_dir(args.project)
        target = paths.video_dir(copy.id)
        target.mkdir(parents=True, exist_ok=True)
        for name in VIDEO_FILES:
            if (source / name).is_file():
                shutil.copy2(source / name, target / name)
        if args.keep_frames:
            shutil.copytree(source / "frames", target / "frames")
        else:
            metadata = store.load_metadata(copy.id)
            store.save_metadata(metadata.model_copy(update={"frame_count": 0}))
        # Measured again, as for a piano fitted for the first time.
        calibration = json.loads((target / "calibration.json").read_text())
        calibration.pop("measurement", None)
        calibration.pop("measuredFor", None)
        (target / "calibration.json").write_text(json.dumps(calibration))

        first: dict[str, float] = {}
        last: dict[str, float] = defaultdict(float)
        started = time.perf_counter()

        def tick(event: ProgressEvent) -> None:
            now = time.perf_counter() - started
            first.setdefault(event.stage, now)
            last[event.stage] = now

        written = piece.read_and_write(copy.id, reporter=CallbackProgress(tick))
        total = time.perf_counter() - started
        notes = store.load_notes(copy.id)
        metadata = store.load_metadata(copy.id)
        print(f"video: {metadata.duration_seconds:.1f} s, {metadata.frame_count} frames")
        print(f"notes written: {written.notes}")
        print(f"{'stage':<10}{'from s':>10}{'to s':>10}{'length s':>10}")
        for stage, start in first.items():
            print(f"{stage:<10}{start:>10.1f}{last[stage]:>10.1f}{last[stage] - start:>10.1f}")
        print(f"{'total':<10}{'':>10}{total:>10.1f}")
        if notes is not None and notes.notes:
            starts = sorted(note.start for note in notes.notes)
            print(
                f"first note starts at {starts[0]:.2f} s of the video, last at {starts[-1]:.2f} s"
            )
    finally:
        bundle.delete_project(copy.id)


if __name__ == "__main__":
    main()
