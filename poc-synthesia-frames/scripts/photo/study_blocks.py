"""The scroll speed from the sum of per-block correlations: the width cut into blocks so only the true shift aligns all of them."""
import sys, json
import numpy as np
from concurrent.futures import ProcessPoolExecutor
from aitu_backend.video import store, motion
U = 'b99bc3ae-30a5-4aa0-9b3b-8f11eea5fba7'
S = sys.argv[1]; plate_path = sys.argv[2]; BLOCKS = 16
def chunk(args):
    plate_path, upper, idx = args
    plate = np.load(plate_path)
    top = int(upper * motion.BAND_TOP_FRACTION)
    out = []
    for i in idx:
        f = store.load_frame(U, i)
        d = np.clip(np.abs(f[top:upper] - plate[top:upper]).max(axis=2) - 24, 0, None)
        out.append(np.stack([b.mean(axis=1) for b in np.array_split(d, BLOCKS, axis=1)]))
    return out
def align_blocks(a, b, max_lag):
    size = 1 << int(np.ceil(np.log2(max(4, a.shape[1] * 2))))
    corr = np.zeros(2 * max_lag + 1)
    for pa, pb in zip(a, b):
        pa = pa - pa.mean(); pb = pb - pb.mean()
        c = np.fft.irfft(np.fft.rfft(pb, size) * np.conj(np.fft.rfft(pa, size)), size)
        corr += np.concatenate([c[-max_lag:], c[: max_lag + 1]])
    lags = np.arange(-max_lag, max_lag + 1)
    k = int(np.argmax(corr))
    part = 0.0
    if 0 < k < len(corr) - 1:
        y0, y1, y2 = corr[k - 1], corr[k], corr[k + 1]
        den = y0 - 2 * y1 + y2
        part = 0.5 * (y0 - y2) / den if den != 0 else 0.0
    peak = float(corr[k]); second = float(np.max(np.delete(corr, slice(max(0, k - 3), k + 4))))
    return float(lags[k] + part), (peak / second if second > 0 else float('inf'))
if __name__ == '__main__':
    cal = store.load_calibration(U); upper = int(round(cal.upper_line)); count = store.frame_count(U)
    idx = [list(range(a, min(a + 24, count))) for a in range(0, count, 24)]
    profiles = []
    with ProcessPoolExecutor(8) as pool:
        for part in pool.map(chunk, [(plate_path, upper, i) for i in idx]):
            profiles.extend(part)
    shifts, sharps = [], []
    for a, b in zip(profiles, profiles[1:]):
        s, sh = align_blocks(a, b, max(4, upper // 3)); shifts.append(s); sharps.append(sh)
    series = np.array(shifts); sharp = np.array(sharps)
    for thr in [1.15, 1.3, 1.5, 2.0]:
        usable = series[(sharp > thr) & (np.abs(series) > 1)]
        q1, q3 = np.percentile(usable, [25, 75]) if usable.size else (0, 0)
        print(f'sharpness > {thr}: usable {usable.size:4d}  median {np.median(usable) if usable.size else 0:.3f}  q1 {q1:.3f} q3 {q3:.3f}  spread {(q3-q1)/np.median(usable)*100 if usable.size else 0:.2f}%')
    print('all pairs in 18..22:', int(((series > 18) & (series < 22)).sum()), 'median of those', round(float(np.median(series[(series > 18) & (series < 22)])), 3))
    np.save(S + '/series_blocks.npy', series); np.save(S + '/sharp_blocks.npy', sharp)
