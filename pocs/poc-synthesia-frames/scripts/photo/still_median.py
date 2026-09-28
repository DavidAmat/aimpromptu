"""The plate as the median of what stands still: over spread frames where the roll moves, each pixel
counts only when it did not change across the neighbouring frames (no moving edge on it)."""
import sys, json, time
sys.path.insert(0, sys.argv[1])
import numpy as np
from concurrent.futures import ProcessPoolExecutor
S = sys.argv[1]; which = sys.argv[2]; PICKS = int(sys.argv[3]) if len(sys.argv) > 3 else 150
U = 'b99bc3ae-30a5-4aa0-9b3b-8f11eea5fba7' if which == 'photo' else 'ddd8bce8-3e3f-4262-9595-46aaf66de54b'
TOL = 12.0; STILL_SHARE = 0.002; K = 2   # a pixel is still when it did not change over the K frames before and after
def one(args):
    i, upper, count = args
    from aitu_backend.video import store
    lo, hi = max(0, i - K), min(count - 1, i + K)
    frames = [store.load_frame(U, j) for j in range(lo, hi + 1)]
    f = frames[i - lo]
    still = np.ones(f.shape[:2], bool); roll_moves = True
    for a, b in zip(frames, frames[1:]):
        changed = np.abs(a - b).max(axis=2) >= TOL
        still &= ~changed
        if changed[:upper].mean() < STILL_SHARE:
            roll_moves = False
    return f.astype(np.uint8), still, roll_moves
if __name__ == '__main__':
    from aitu_backend.video import store, stitch, notes as notes_module, geometry
    from aitu_backend.video.detector import DetectorSettings
    import extent_core, local_valleys
    cal = store.load_calibration(U); meas = store.load_measurement(U); count = store.frame_count(U)
    upper = int(round(cal.upper_line))
    picks = np.linspace(0, count - 1, PICKS).round().astype(int)
    t0 = time.time()
    with ProcessPoolExecutor(8) as pool:
        results = list(pool.map(one, [(int(i), upper, count) for i in picks]))
    kept = [(f, s) for f, s, moves in results if moves]
    stack = np.stack([f for f, s in kept]); mask = np.stack([s for f, s in kept])
    plate = np.zeros((720, 1280, 3), np.float32); plain = np.median(stack, axis=0).astype(np.float32)
    for y0 in range(0, 720, 60):
        block = stack[:, y0:y0+60].astype(np.float32)
        block[~mask[:, y0:y0+60]] = np.nan
        with np.errstate(all='ignore'):
            med = np.nanmedian(block, axis=0)
        plate[y0:y0+60] = np.where(np.isnan(med), plain[y0:y0+60], med)
    holes = ~mask.any(axis=0)
    print(f'{which}: still-median plate from {len(kept)} of {PICKS} spread frames ({PICKS-len(kept)} still-roll frames left out) in {time.time()-t0:.1f} s; pixels with no still value {holes[:upper].sum()} ({100*holes[:upper].mean():.3f}%); still frames per roll pixel p10/50: {np.percentile(mask[:, :upper].sum(axis=0), [10, 50])}')
    np.save(S + f'/plate_stillmedian_{which}.npy', plate)
    p20 = store.load_plate(U)
    d = np.abs(plate[:upper] - p20[:upper]).max(axis=2)
    bad = []
    for k in geometry.keys(cal):
        a, b = int(round(k.left)) + 2, int(round(k.right)) - 1
        if b > a and (d[:, a:b] > 12).mean() > 0.05: bad.append((k.midi, round(float((d[:, a:b] > 12).mean()), 2)))
    print('   lanes where it differs from the shipped p20 plate on more than 5% of pixels:', bad)
    store.load_plate = lambda uuid: plate
    if which == 'photo':
        cal.roll_top = 0; cal.guard_band = 56; store.load_calibration = lambda uuid: cal
        meas.scroll_speed.px_per_frame = 20.22; meas.scroll_speed.px_per_second = 202.2; store.load_measurement = lambda uuid: meas
        strikes = json.load(open(S + '/strikes.json'))
    else:
        strikes = [tuple(x) for x in json.load(open(S + '/strikes_first.json'))]
    duration = store.load_metadata(U).duration_seconds
    roll, geom = stitch.build(U)
    sk = {}
    for m, t in strikes: sk.setdefault(m, []).append(t)
    def report(label, notes):
        by = {}
        for n in notes: by.setdefault(n.midi, []).append(n)
        found = sum(1 for m, t in strikes if any(abs(t - n.start) <= 0.15 for n in by.get(m, [])))
        ns = [n for n in notes if not any(abs(n.start - s) <= 0.15 for s in sk.get(n.midi, []))]
        near = sum(1 for n in ns if any(0 < abs(n.start - o.start) <= 0.25 for o in by[n.midi]))
        print(f'   {label:34s}: notes {len(notes)}  found {found} of {len(strikes)} ({100*found/len(strikes):.1f}%)  not shown {len(ns)} ({100*len(ns)/len(notes):.1f}%), within 250 ms of another note {near}, isolated {len(ns)-near}')
    notes, _ = notes_module.notes_from_roll(roll, cal, geom, duration)
    report('shipped rules', notes)
    extent_core.install(); local_valleys.install(14)
    notes, _ = notes_module.notes_from_roll(roll, cal, geom, duration, settings=DetectorSettings(split_prominence=0.30))
    report('proposed rules', notes)
    json.dump({'notes': [n.model_dump(by_alias=True) for n in notes]}, open(S + f'/notes_stillmedian_{which}.json', 'w'))
