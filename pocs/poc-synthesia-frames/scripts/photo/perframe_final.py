"""The per-frame reading with every fix in place: agreement (V-31) and the momentum rule."""
import sys, json
S = sys.argv[1]
sys.path.insert(0, S)
import numpy as np
from concurrent.futures import ProcessPoolExecutor
from aitu_backend.video import store, detector, momentum, reading
from aitu_backend.schemas.video import DetectedRun
U = 'b99bc3ae-30a5-4aa0-9b3b-8f11eea5fba7'
def chunk(idx):
    sys.path.insert(0, S)
    import extent_core, local_valleys
    extent_core.install(); local_valleys.install(14)
    plate = np.load(S + '/plate_static_full.npy')
    cal = store.load_calibration(U); cal.roll_top = 0; cal.guard_band = 56
    return [[r.model_dump() for r in detector.find_runs(store.load_frame(U, i), cal, plate=plate)] for i in idx]
if __name__ == '__main__':
    count = store.frame_count(U)
    idx = [list(range(a, min(a + 24, count))) for a in range(0, count, 24)]
    per_frame = []
    with ProcessPoolExecutor(8) as pool:
        for part in pool.map(chunk, idx):
            per_frame.extend([[DetectedRun.model_validate(r) for r in raw] for raw in part])
    travel = 20.22
    kept = refused = onsets = 0
    for i, runs in enumerate(per_frame):
        before = per_frame[i - 1] if i > 0 else []; after = per_frame[i + 1] if i + 1 < count else []
        k, r = momentum.apply(runs, before, travel, after, travel)
        on, sus = detector.window_rule(k, 515, travel)
        kept += len(k); refused += len(r); onsets += len(on)
    print(f'per-frame reading, all fixes: runs {sum(len(r) for r in per_frame)}  agreement (V-31) {reading.agreement(per_frame, travel):.3f}  momentum kept {kept} refused {refused}  onsets {onsets} ({onsets/189.2:.2f} a second)')
