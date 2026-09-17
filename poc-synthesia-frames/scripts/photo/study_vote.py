"""The travel voted for by the rectangles themselves (V-33): link every run to its self in the next frame and average the fall."""
import sys, json
import numpy as np
from concurrent.futures import ProcessPoolExecutor
from aitu_backend.video import store, detector, momentum
from aitu_backend.schemas.video import DetectedRun
U = 'b99bc3ae-30a5-4aa0-9b3b-8f11eea5fba7'
S = sys.argv[1]; plate_path = sys.argv[2]
def chunk(args):
    plate_path, idx = args
    plate = np.load(plate_path)
    cal = store.load_calibration(U)
    return [[r.model_dump() for r in detector.find_runs(store.load_frame(U, i), cal, plate=plate)] for i in idx]
if __name__ == '__main__':
    count = store.frame_count(U)
    idx = [list(range(a, min(a + 24, count))) for a in range(0, count, 24)]
    per_frame = []
    with ProcessPoolExecutor(8) as pool:
        for part in pool.map(chunk, [(plate_path, i) for i in idx]):
            per_frame.extend([[DetectedRun.model_validate(r) for r in raw] for raw in part])
    json.dump([[r.model_dump() for r in runs] for runs in per_frame], open(S + '/runs_static.json', 'w'))
    falls = []; per_pair = []
    for i, (a, b) in enumerate(zip(per_frame, per_frame[1:])):
        cand = [r for r in a if not r.clipped and not r.entering]
        links, _ = momentum.link(cand, b, +20.0)
        d = []
        for r, j in zip(cand, links):
            if j is None: continue
            o = b[j]
            if o.clipped or o.entering: continue
            d.append(o.y_top - r.y_top); d.append(o.y_bottom - r.y_bottom)
        falls.extend(d)
        if d: per_pair.append((i, float(np.mean(d)), len(d)))
    falls = np.array(falls, dtype=float)
    print('linked edges', falls.size, 'over', len(per_pair), 'pairs')
    print('fall: mean %.3f  median %.1f  central-50%% mean %.3f  std %.2f' % (falls.mean(), np.median(falls), falls[(falls >= np.percentile(falls, 25)) & (falls <= np.percentile(falls, 75))].mean(), falls.std()))
    print('histogram of falls 15..25:', {k: int((falls == k).sum()) for k in range(15, 26)})
    pp = np.array([m for _, m, _ in per_pair])
    print('per pair mean fall: quartiles', np.percentile(pp, [5, 25, 50, 75, 95]).round(2))
    # by thirds of the piece, to see a drift or a tempo change
    for lo, hi in [(0, 630), (630, 1260), (1260, 1892)]:
        sel = [m for i, m, n in per_pair if lo <= i < hi]
        print(f'  frames {lo}-{hi}: mean of per-pair means {np.mean(sel):.3f}  median {np.median(sel):.2f}')
    print('pairs 630-660:', [(i, round(m, 1), n) for i, m, n in per_pair if 630 <= i < 660])
    json.dump(per_pair, open(S + '/vote_per_pair.json', 'w'))
