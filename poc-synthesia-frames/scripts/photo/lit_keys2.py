"""The strike ground truth, read where this rendering lights a key first: the top of the white keys, just under the black keys."""
import sys
import numpy as np
from concurrent.futures import ProcessPoolExecutor
from aitu_backend.video import store, geometry
U = 'b99bc3ae-30a5-4aa0-9b3b-8f11eea5fba7'
def chunk(args):
    idx, patches = args
    out = []
    for i in idx:
        f = store.load_frame(U, i)
        out.append([float(np.median((p := f[r0:r1, a:b]).max(axis=2) - p.min(axis=2))) for a, b, r0, r1 in patches])
    return out
if __name__ == '__main__':
    S = sys.argv[1]
    cal = store.load_calibration(U); upper = int(round(cal.upper_line)); depth = int(cal.black_depth)
    keys = geometry.keys(cal); count = store.frame_count(U)
    patches = []
    for k in keys:
        a, b = int(round(k.left)) + 3, int(round(k.right)) - 2
        r0, r1 = (upper + depth + 2, upper + depth + 14) if k.kind == "white" else (upper + 30, upper + depth - 20)
        patches.append((max(0, a), max(a + 1, b), r0, r1))
    idx = [list(range(a, min(a + 48, count))) for a in range(0, count, 48)]
    rows = []
    with ProcessPoolExecutor(8) as pool:
        for part in pool.map(chunk, [(i, patches) for i in idx]):
            rows.extend(part)
    sat = np.array(rows, dtype=np.float32)
    np.save(S + '/sat.npy', sat)
    print('saturation p50/p99 of the whole:', np.percentile(sat, [50, 99]))
    print('unlit p50 by kind: white', np.median(sat[:, [j for j, k in enumerate(keys) if k.kind == 'white']]), 'black', np.median(sat[:, [j for j, k in enumerate(keys) if k.kind == 'black']]))
