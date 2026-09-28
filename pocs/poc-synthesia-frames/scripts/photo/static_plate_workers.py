"""The long-static plate the way the app would build it: contiguous blocks of frames over worker processes."""
import sys, time
import numpy as np
from concurrent.futures import ProcessPoolExecutor
from aitu_backend.video import store
U = 'b99bc3ae-30a5-4aa0-9b3b-8f11eea5fba7'
TOL = 12.0
def block(args):
    lo, hi, L = args
    prev = None; run = None; ssum = None; scount = None
    for i in range(lo, hi):
        f = store.load_frame(U, i)
        if prev is None:
            run = np.zeros(f.shape[:2], np.int32); ssum = np.zeros(f.shape, np.float64); scount = np.zeros(f.shape[:2], np.int32)
        else:
            still = np.abs(f - prev).max(axis=2) < TOL
            run = np.where(still, run + 1, 0)
            long = run >= L
            ssum[long] += f[long]; scount[long] += 1
        prev = f
    return ssum, scount
if __name__ == '__main__':
    S = sys.argv[1]
    cal = store.load_calibration(U); count = store.frame_count(U)
    # a rectangle cannot stay still longer than the roll is tall: rows above the line over the travel, plus one
    L = int(np.ceil(cal.upper_line / 20.22)) + 1
    t0 = time.time()
    edges = np.linspace(0, count, 9).round().astype(int)
    with ProcessPoolExecutor(8) as pool:
        parts = list(pool.map(block, [(int(a), int(b), L) for a, b in zip(edges, edges[1:])]))
    ssum = sum(p[0] for p in parts); scount = sum(p[1] for p in parts)
    plate = (ssum / np.maximum(scount, 1)[..., None]).astype(np.float32)
    holes = scount == 0
    print(f'L = {L} frames, {count} frames over 8 workers in {time.time()-t0:.1f} s; pixels with no long-static value: {holes.sum()} ({holes.mean()*100:.4f}%)')
    ref = np.load(S + '/plate_static.npy')
    print('difference from the single-pass plate over the roll: median', np.median(np.abs(plate[:515] - ref)).round(2), ' p99', np.percentile(np.abs(plate[:515] - ref), 99).round(2))
    np.save(S + '/plate_static_workers.npy', plate)
