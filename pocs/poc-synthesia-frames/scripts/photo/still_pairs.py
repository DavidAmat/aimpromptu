"""Can a still-roll pair be told from the raw frames alone? The share of roll pixels that change between consecutive frames."""
import sys, json
import numpy as np
from concurrent.futures import ProcessPoolExecutor
from aitu_backend.video import store
S = sys.argv[1]
def chunk(args):
    U, upper, idx = args
    out = []
    prev = None
    for i in idx:
        f = store.load_frame(U, i)[:upper]
        if prev is not None:
            out.append(float((np.abs(f - prev).max(axis=2) >= 12).mean()))
        prev = f
    return out
if __name__ == '__main__':
    for U, upper, label in [('ddd8bce8-3e3f-4262-9595-46aaf66de54b', 560, 'first'), ('b99bc3ae-30a5-4aa0-9b3b-8f11eea5fba7', 515, 'photo')]:
        count = store.frame_count(U)
        idx = [list(range(max(0, a - 1), min(a + 48, count))) for a in range(0, count, 48)]
        change = []
        with ProcessPoolExecutor(8) as pool:
            for part in pool.map(chunk, [(U, upper, i) for i in idx]):
                change.extend(part)
        change = np.array(change[:count - 1])
        np.save(S + f'/change_{label}.npy', change)
        meas = store.load_measurement(U); series = np.array(meas.scroll_speed.series)
        if label == 'first':
            still = np.abs(series) < 1.0; moving = (series > 15) & (series < 19)
        else:
            vote = json.load(open(S + '/vote_per_pair.json')); voted = set(i for i, m, n in vote if n >= 6)
            moving = np.array([i in voted for i in range(len(change))]); still = np.zeros(len(change), bool); still[:15] = True; still[2:15] = True
        print(f'{label}: share of roll pixels changing by >= 12 levels between consecutive frames')
        print(f'   known moving pairs ({moving.sum()}): p1 {np.percentile(change[moving], 1)*100:.2f}%  p5 {np.percentile(change[moving], 5)*100:.2f}%  p50 {np.percentile(change[moving], 50)*100:.2f}%')
        print(f'   known still pairs ({still.sum()}): p50 {np.percentile(change[still], 50)*100:.3f}%  p95 {np.percentile(change[still], 95)*100:.3f}%  p99 {np.percentile(change[still], 99)*100:.3f}%')
        for thr in [0.001, 0.002, 0.005, 0.01]:
            print(f'   pairs under {thr*100:.1f}%: {(change < thr).sum()} of {len(change)}')
