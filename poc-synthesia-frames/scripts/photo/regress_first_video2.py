"""The first video: the long-static plate with the still-roll frames left out (V-43), and per-pixel diagnostics."""
import sys, time, json
import numpy as np
from concurrent.futures import ProcessPoolExecutor
from aitu_backend.video import store, geometry, notes as notes_module
U = 'ddd8bce8-3e3f-4262-9595-46aaf66de54b'
S = sys.argv[1]
TOL = 12.0
PROBES = [(300, 330), (300, 232), (300, 800), (150, 100), (450, 520)]   # (row, x)
def block(args):
    lo, hi, L, excluded = args
    prev = run = ssum = scount = nruns = None
    probes = {p: [] for p in PROBES}
    for i in range(lo, hi):
        f = store.load_frame(U, i)
        if prev is None:
            run = np.zeros(f.shape[:2], np.int32); ssum = np.zeros(f.shape, np.float64); scount = np.zeros(f.shape[:2], np.int32); nruns = np.zeros(f.shape[:2], np.int32)
        else:
            still = np.abs(f - prev).max(axis=2) < TOL
            run = np.where(still, run + 1, 0)
            long = run >= L
            if i not in excluded:
                ssum[long] += f[long]; scount[long] += 1; nruns[run == L] += 1
            for (r, x) in PROBES:
                if run[r, x] == L:
                    probes[(r, x)].append((i, f[r, x].round(0).tolist(), i in excluded))
        prev = f
    return ssum, scount, nruns, probes
if __name__ == '__main__':
    cal = store.load_calibration(U); count = store.frame_count(U); meas = store.load_measurement(U)
    upper = int(round(cal.upper_line)); travel = meas.scroll_speed.px_per_frame
    L = int(np.ceil(cal.upper_line / travel)) + 1
    series = np.array(meas.scroll_speed.series)
    still_pairs = np.where(np.abs(series) < 1.0)[0]
    excluded = set(still_pairs.tolist()) | set((still_pairs + 1).tolist())
    print('still-roll frames excluded:', len(excluded), ' of which after frame 2500:', sum(1 for i in excluded if i >= 2500))
    t0 = time.time()
    edges = np.linspace(0, count, 9).round().astype(int)
    with ProcessPoolExecutor(8) as pool:
        parts = list(pool.map(block, [(int(a), int(b), L, excluded) for a, b in zip(edges, edges[1:])]))
    ssum = sum(p[0] for p in parts); scount = sum(p[1] for p in parts); nruns = sum(p[2] for p in parts)
    for (r, x) in PROBES:
        runs_here = [q for p in parts for q in p[3][(r, x)]]
        print(f'probe row {r} x {x}: long-still runs start at frames {[(i, v, "excluded" if e else "") for i, v, e in runs_here][:12]}  ... {len(runs_here)} runs')
    old = np.load(f'data/audio/{U}/video/plate.npy')
    static = (ssum / np.maximum(scount, 1)[..., None]).astype(np.float32)
    holes = scount == 0
    static[holes] = old[holes]
    print(f'{time.time()-t0:.1f} s; holes {holes.sum()} ({holes.mean()*100:.3f}%) filled from p20; |static - p20| over the roll: median {np.median(np.abs(static[:upper]-old[:upper])):.1f} p99 {np.percentile(np.abs(static[:upper]-old[:upper]), 99):.1f}; share brighter by >8: {((static-old)[62:upper].max(axis=2) > 8).mean():.3f}')
    print('long-still runs per pixel over the roll: p10/50/90', np.percentile(nruns[62:upper], [10, 50, 90]))
    np.save(S + '/plate_static_first2.npy', static)
    from PIL import Image
    Image.fromarray(np.clip(static, 0, 255).astype(np.uint8)).save(S + '/first_static2.png')
