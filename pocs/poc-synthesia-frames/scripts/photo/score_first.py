"""Score readings of the first video against its keyboard, for any plate file."""
import sys, time
import numpy as np
from concurrent.futures import ProcessPoolExecutor
from aitu_backend.video import store, geometry, notes as notes_module
U = 'ddd8bce8-3e3f-4262-9595-46aaf66de54b'
def lit_chunk(args):
    idx, patches = args
    plate = np.load(f'data/audio/{U}/video/plate.npy')
    return [[float(np.median(np.abs(store.load_frame(U, i)[r0:r1, a:b] - plate[r0:r1, a:b]).max(axis=2))) for a, b, r0, r1 in patches] for i in idx]
if __name__ == '__main__':
    S = sys.argv[1]; plates = sys.argv[2:]
    cal = store.load_calibration(U); count = store.frame_count(U); upper = int(round(cal.upper_line))
    keys = geometry.keys(cal); depth = int(cal.black_depth)
    try:
        strikes = [tuple(x) for x in __import__('json').load(open(S + '/strikes_first.json'))]
    except FileNotFoundError:
        patches = []
        for k in keys:
            a, b = int(round(k.left)) + 2, int(round(k.right)) - 1
            r0, r1 = (upper + depth + 4, upper + depth + 16) if k.kind == 'white' else (upper + 10, upper + 40)
            patches.append((max(0, a), max(a + 1, b), r0, r1))
        idx = [list(range(a, min(a + 48, count))) for a in range(0, count, 48)]
        rows = []
        with ProcessPoolExecutor(8) as pool:
            for part in pool.map(lit_chunk, [(i, patches) for i in idx]):
                rows.extend(part)
        lit = np.array(rows) > 40
        always = [k.midi for j, k in enumerate(keys) if lit[:, j].mean() > 0.95]
        strikes = []
        for j, k in enumerate(keys):
            if k.midi in always: continue
            on = np.where(lit[1:, j] & ~lit[:-1, j])[0] + 1
            strikes.extend((k.midi, i * 0.1) for i in on)
        print('keys always lit:', always, 'strikes:', len(strikes))
        __import__('json').dump(strikes, open(S + '/strikes_first.json', 'w'))
    sk = {}
    for m, t in strikes: sk.setdefault(m, []).append(t)
    def score(notes, lo, hi, tol=0.15):
        by = {}
        for n in notes: by.setdefault(n.midi, []).append(n.start)
        st = [(m, t) for m, t in strikes if lo <= t < hi]
        found = sum(1 for m, t in st if any(abs(t - s) <= tol for s in by.get(m, [])))
        ns = [n for n in notes if lo <= n.start < hi]
        not_shown = sum(1 for n in ns if not any(abs(n.start - s) <= tol for s in sk.get(n.midi, [])))
        return len(st), found, len(ns), not_shown
    notes_module.store.save_notes = lambda uuid, answer: None
    for path in plates:
        plate = np.load(path) if path != 'p20' else np.load(f'data/audio/{U}/video/plate.npy')
        store.load_plate = lambda uuid, p=plate: p
        t1 = time.time()
        answer = notes_module.read_notes(U, compare_connected=False)
        a = score(answer.notes, 40, 100); b = score(answer.notes, 0, 1e9)
        print(f'{path.split("/")[-1]:24s}: {len(answer.notes)} notes in {time.time()-t1:.0f} s; 40-100 s: strikes {a[0]} found {a[1]} ({100*a[1]/a[0]:.0f}%) notes {a[2]} not shown {a[3]} ({100*a[3]/a[2]:.0f}%); whole: strikes {b[0]} found {b[1]} ({100*b[1]/b[0]:.0f}%) notes {b[2]} not shown {b[3]} ({100*b[3]/b[2]:.0f}%)')
