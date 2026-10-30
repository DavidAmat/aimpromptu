"""Implementation 04-3, Phase 2, task 2.6: cut the snapshots of the gallery from the user's Chopin PDFs.

Each snapshot is some bars of one system (or of two systems, side by side, the second with the clef and key of its
line in front), both staves, the other hand in light grey. The PDFs stay outside the repo
(/home/david/Documents/projects/music/chopin); x positions are pixels of the page rendered at 200 dpi and
straightened by layout.py. Run with the research venv (PIL, numpy):

    python crop.py OUT_DIR [name ...]
"""
import sys, os, numpy as np
from PIL import Image
import layout
C = '/home/david/Documents/projects/music/chopin/'
OUT = sys.argv[1]
# the cut name -> the file name of images/chopin_passages/ (numbered per piece and hand)
RENAME = {'ballade1-right-2': 'ballade1-right-1', 'ballade1-right-3': 'ballade1-right-2',
          'ballade4-left-4': 'ballade4-left-3', 'ballade4-left-5': 'ballade4-left-4', 'ballade4-left-6': 'ballade4-left-5',
          'ballade4-right-3': 'ballade4-right-1', 'ballade4-right-5': 'ballade4-right-2',
          'waltz-64-2-right-2': 'waltz-64-2-right-1', 'ballade1b-right-3': 'ballade1-right-3',
          'ballade1c-right-4': 'ballade1-right-4', 'ballade1d-right-5': 'ballade1-right-5',
          **{f'ballade4p44-right-{n}': f'ballade4-right-{n}' for n in range(3, 9)},
          'ballade4p41-left-6': 'ballade4-left-6', 'ballade4p41-left-7': 'ballade4-left-7'}
# id: (pdf, page, [(system, x0, x1, head)], hands); head = x where the clef and key end (prepended when x0 is mid-system)
SPEC = {
    'ballade1-{h}-1': ('ballades', 10, [(1, 96, 948, 0)], 'L'),
    'ballade1-{h}-2': ('ballades', 10, [(1, 948, 1555, 205), (2, 98, 730, 0)], 'LR'),
    'ballade1-{h}-3': ('ballades', 12, [(0, 532, 1561, 192)], 'LR'),
    'ballade4-{h}-1': ('ballades', 41, [(3, 98, 1309, 0)], 'L'),
    'ballade4-{h}-2': ('ballades', 43, [(0, 564, 1562, 250)], 'L'),
    'ballade4-{h}-3': ('ballades', 43, [(3, 570, 1563, 250)], 'R'),
    'ballade4-{h}-4': ('ballades', 52, [(3, 96, 1560, 0)], 'L'),
    'ballade4-{h}-5': ('ballades', 50, [(0, 99, 1566, 0)], 'LR'),
    'ballade4-{h}-6': ('ballades', 54, [(1, 98, 1560, 0)], 'L'),
    'waltz-69-2-{h}-1': ('waltzes', 79, [(0, 165, 1020, 0)], 'LR'),
    'waltz-69-1-{h}-1': ('waltzes', 71, [(0, 215, 1350, 0)], 'L'),
    'waltz-64-2-{h}-1': ('waltzes', 59, [(0, 182, 1410, 0)], 'L'),
    'waltz-64-2-{h}-2': ('waltzes', 59, [(0, 182, 812, 0)], 'R'),
    'waltz-64-3-{h}-1': ('waltzes', 65, [(0, 185, 1290, 0)], 'L'),
    'waltz-42-{h}-1': ('waltzes', 45, [(1, 88, 1053, 0)], 'R'),
    'waltz-70-3-{h}-1': ('waltzes', 99, [(2, 815, 1615, 290)], 'R'),
    'prelude-4-{h}-1': ('preludes', 13, [(0, 180, 1255, 0)], 'LR'),
    'prelude-7-{h}-1': ('preludes', 16, [(0, 190, 1250, 0)], 'LR'),
    'prelude-13-{h}-1': ('preludes', 26, [(0, 190, 1260, 0)], 'L'),
    'prelude-15-{h}-1': ('preludes', 29, [(0, 190, 1260, 0)], 'L'),
    'prelude-20-{h}-1': ('preludes', 45, [(0, 99, 979, 0)], 'L'),
    'prelude-21-{h}-1': ('preludes', 45, [(2, 198, 1258, 0)], 'L'),
    'nocturne-9-2-{h}-1': ('nocturnes', 10, [(0, 360, 1990, 0)], 'L'),
    'ballade1b-{h}-3': ('ballades', 20, [(3, 100, 1346, 0)], 'R'),  # review 4: bars 255-256, the scale up
    'ballade1c-{h}-4': ('ballades', 13, [(3, 658, 1556, 185)], 'R'),  # review 5: bars 130-131, irregular jumps up
    'ballade1d-{h}-5': ('ballades', 14, [(4, 98, 1558, 0)], 'R'),  # review 5: bars 150-152, broken octave frames
    # review 6: Ballade No. 4, page 44, one bar of each of the five lines (two voices in the right hand)
    'ballade4p44-{h}-3': ('ballades', 44, [(0, 1024, 1560, 225)], 'R'),  # bar 58
    'ballade4p44-{h}-4': ('ballades', 44, [(1, 650, 1110, 225)], 'R'),  # bar 60
    'ballade4p44-{h}-5': ('ballades', 44, [(2, 876, 1560, 225)], 'R'),  # bar 63
    'ballade4p44-{h}-6': ('ballades', 44, [(3, 97, 842, 0)], 'R'),  # bar 64
    'ballade4p44-{h}-7': ('ballades', 44, [(3, 842, 1559, 225)], 'R'),  # bar 65
    'ballade4p44-{h}-8': ('ballades', 44, [(4, 96, 878, 0)], 'R'),  # bar 66
    # review of Phase 3 (2026-10-30): Ballade No. 4, page 41, the second line, the left hand
    'ballade4p41-{h}-6': ('ballades', 41, [(1, 98, 651, 0)], 'L'),  # bar 3
    'ballade4p41-{h}-7': ('ballades', 41, [(1, 651, 1105, 225)], 'L'),  # bar 4
}
FADE = 0.75
only = sys.argv[2:]
for key, (pdf, p, segs, hands) in SPEC.items():
    im = layout.page(C + pdf + '.pdf', p); a = np.array(im); sy = layout.systems(a)
    for h in hands:
        name = key.format(h={'L': 'left', 'R': 'right'}[h])
        if only and name not in only: continue
        parts = []
        for si, x0, x1, head in segs:
            s = sy[si]; g = s['gap']
            top = s['top'] - 4.5 * g; bot = s['bottom'] + 4.5 * g
            if si > 0: top = max(top, (sy[si - 1]['bottom'] + s['top']) / 2)
            if si + 1 < len(sy): bot = min(bot, (s['bottom'] + sy[si + 1]['top']) / 2)
            top, bot, mid = int(top), int(bot), int(s['mid'] - top)
            pieces = []
            if head:
                left = layout.barlines(a, s)[0] if layout.barlines(a, s) and layout.barlines(a, s)[0] < 150 else 90
                hp = im.crop((left - 4, top, head, bot)); arr = np.array(hp)
                arr[int(s['s1'][1] - top) + 3:int(s['s2'][0] - top) - 3, 9:] = 255
                pieces.append(Image.fromarray(arr))
            pieces.append(im.crop((x0 - 4, top, x1 + 4, bot)))
            for piece in pieces:
                arr = np.array(piece).astype(float)
                sl = slice(0, mid) if h == 'L' else slice(mid, None)
                arr[sl] = 255 - (255 - arr[sl]) * (1 - FADE)
                parts.append(Image.fromarray(arr.astype('uint8')))
            parts.append(None)
        parts = parts[:-1]
        W = sum(14 if q is None else q.width for q in parts); H = max(q.height for q in parts if q is not None)
        out = Image.new('L', (W, H), 255); x = 0
        for q in parts:
            if q is None: x += 14; continue
            out.paste(q, (x, (H - q.height) // 2)); x += q.width
        out.save(os.path.join(OUT, RENAME.get(name, name) + '.png'), optimize=True)
        print(name, out.size)
