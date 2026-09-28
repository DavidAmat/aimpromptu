"""Which row profile answers the scroll speed sharply on a sparse piece over a photo."""
import sys, json
import numpy as np
from concurrent.futures import ProcessPoolExecutor
from aitu_backend.video import store, motion
U = 'b99bc3ae-30a5-4aa0-9b3b-8f11eea5fba7'
S = sys.argv[1]; plate_path = sys.argv[2]
def chunk(args):
    plate_path, upper, idx = args
    plate = np.load(plate_path)
    top = int(upper * motion.BAND_TOP_FRACTION)
    out = []
    for i in idx:
        f = store.load_frame(U, i)
        d = np.abs(f[top:upper] - plate[top:upper]).max(axis=2)
        plain = d.mean(axis=1)
        binary = (d > 24).mean(axis=1)
        edge = np.abs(np.diff(d, axis=0, prepend=d[:1])).mean(axis=1)
        strong = np.clip(d - 24, 0, None).mean(axis=1)
        out.append((plain, binary, edge, strong))
    return out
if __name__ == '__main__':
    cal = store.load_calibration(U)
    upper = int(round(cal.upper_line))
    count = store.frame_count(U)
    idx = [list(range(a, min(a + 24, count))) for a in range(0, count, 24)]
    rows = []
    with ProcessPoolExecutor(8) as pool:
        for part in pool.map(chunk, [(plate_path, upper, i) for i in idx]):
            rows.extend(part)
    for v, name in enumerate(['plain (shipped)', 'binary', 'edge', 'strong']):
        profiles = [r[v] for r in rows]
        speed = motion.scroll_speed(profiles, cal.upper_line, 100.0)
        d = speed.model_dump(); series = np.array(d.pop('series'))
        np.save(S + f'/series_{name.split()[0]}.npy', series)
        print(f"{name:16s} usable {d['usable_pairs']:4d} still {d['still_pairs']:4d} median {d['px_per_frame']:.3f} q1 {d['q1']:.3f} q3 {d['q3']:.3f} stable {d['stable']}   share of all pairs in 18..22: {((series>18)&(series<22)).mean():.3f}")
