"""Print the notes of bars a..b of a kern file, per staff: offset in the bar, duration, pitches."""
import sys, music21 as m
K = '/home/david/Documents/projects/music/poc-aitu-research/data/raw/kern/humdrum-chopin-first-editions/kern/'
f, a, b = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
s = m.converter.parse(K + f)
names = ['R', 'L'] if len(s.parts) == 2 else [str(i) for i in range(len(s.parts))]
for bar in range(a, b + 1):
    print(f'== bar {bar}')
    for pi, part in enumerate(s.parts):
        ms = part.measure(bar)
        if ms is None: continue
        ev = []
        for n in ms.recurse().notes:
            off = n.getOffsetInHierarchy(ms)
            p = ' '.join(x.nameWithOctave for x in (n.pitches))
            g = 'g' if n.duration.isGrace else ''
            ev.append((float(off), f'{float(off):.2f}:{p}/{n.duration.quarterLength:.2f}{g}'))
        ev.sort()
        print(f'  {names[pi]}:', '  '.join(e[1] for e in ev))
