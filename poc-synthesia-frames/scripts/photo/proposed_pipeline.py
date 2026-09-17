"""The proposed rules together, on one video: the long-still plate with still-roll frames left out,
the extent against the core, the local plateau at 0.30, the travel voted by the rectangles."""
import sys, json, time
sys.path.insert(0, sys.argv[1])
import numpy as np
from concurrent.futures import ProcessPoolExecutor
S = sys.argv[1]; which = sys.argv[2]
U = 'b99bc3ae-30a5-4aa0-9b3b-8f11eea5fba7' if which == 'photo' else 'ddd8bce8-3e3f-4262-9595-46aaf66de54b'
TOL = 12.0; STILL_SHARE = 0.002
def block(args):
    lo, hi, L, upper = args
    from aitu_backend.video import store
    prev = run = ssum = scount = None; still_frames = []
    for i in range(lo, hi):
        f = store.load_frame(U, i)
        if prev is None:
            run = np.zeros(f.shape[:2], np.int32); ssum = np.zeros(f.shape, np.float64); scount = np.zeros(f.shape[:2], np.int32)
        else:
            changed = np.abs(f - prev).max(axis=2) >= TOL
            if changed[:upper].mean() < STILL_SHARE:
                still_frames.append(i)
                run[:] = 0            # a still-roll frame is not a picture of the roll's background: the run restarts after it
            else:
                run = np.where(~changed, run + 1, 0); long = run >= L
                ssum[long] += f[long]; scount[long] += 1
        prev = f
    return ssum, scount, still_frames
if __name__ == '__main__':
    from aitu_backend.video import store, stitch, notes as notes_module
    from aitu_backend.video.detector import DetectorSettings
    import extent_core, local_valleys
    cal = store.load_calibration(U); meas = store.load_measurement(U); count = store.frame_count(U)
    upper = int(round(cal.upper_line))
    travel = 20.22 if which == 'photo' else meas.scroll_speed.px_per_frame
    L = int(np.ceil(upper / travel)) + 1
    t0 = time.time()
    edges = np.linspace(0, count, 9).round().astype(int)
    with ProcessPoolExecutor(8) as pool:
        parts = list(pool.map(block, [(int(a), int(b), L, upper) for a, b in zip(edges, edges[1:])]))
    ssum = sum(p[0] for p in parts); scount = sum(p[1] for p in parts); still = sorted(sum((p[2] for p in parts), []))
    plate = (ssum / np.maximum(scount, 1)[..., None]).astype(np.float32)
    holes = scount == 0
    old = store.load_plate(U)
    plate[holes] = old[holes]
    print(f'{which}: plate in {time.time()-t0:.1f} s; L {L} frames; still-roll frames left out {len(still)}; holes filled from the shipped plate {holes[:upper].sum()} of {holes[:upper].size} roll pixels ({100*holes[:upper].mean():.2f}%)')
    np.save(S + f'/plate_proposed_{which}.npy', plate)
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
        print(f'   {label:34s}: notes {len(notes)}  found {found} of {len(strikes)} ({100*found/len(strikes):.1f}%)  not shown {len(ns)} ({100*len(ns)/len(notes):.1f}%), of which within 250 ms of another note on the key {near}, isolated {len(ns)-near}')
        return notes
    notes, _ = notes_module.notes_from_roll(roll, cal, geom, duration)
    report('shipped rules, proposed plate', notes)
    extent_core.install(); local_valleys.install(14)
    notes, _ = notes_module.notes_from_roll(roll, cal, geom, duration, settings=DetectorSettings(split_prominence=0.30))
    report('proposed rules, proposed plate', notes)
    json.dump({'notes': [n.model_dump(by_alias=True) for n in notes]}, open(S + f'/notes_proposed_{which}.json', 'w'))
