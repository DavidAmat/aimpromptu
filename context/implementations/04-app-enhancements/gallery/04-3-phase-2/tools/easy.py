"""Implementation 04-3, Phase 2, task 2.5: the easy left-hand patterns of the brief, drawn by the app's engine.

Run inside the backend container (it reads no database): docker exec -i aimpromptu-backend-1 python - < easy.py
Writes F1 frames texts and SVGs to /home/app/04-3-phase-2/.
"""
from pathlib import Path
from aitu_backend.sheet.engrave.frames import render_frames

OUT = Path('/home/app/04-3-phase-2'); OUT.mkdir(parents=True, exist_ok=True)
Q = 12  # frames of one negra (quarterMs=480, frameMs=40)
HEAD = 'F1 frames frameMs=40 quarterMs=480\nkey=1b clefs: R=treble L=bass\n'

# The right hand is the same simple melody in F major for the three patterns: negras and a few corcheas.
MELODY = [  # (beat, pitch, figure, beam)
    (0, 'A4', 4, None), (1, 'C5', 4, None), (2, 'F5', 4, None), (3, 'E5', 8, 1), (3.5, 'D5', 8, 1),
    (4, 'C5', 2, None), (6, 'A4', 4, None), (7, 'Bb4', 4, None),
    (8, 'C5', 4, None), (9, 'D5', 4, None), (10, 'E5', 4, None), (11, 'D5', 8, 2), (11.5, 'C5', 8, 2),
    (12, 'Bb4', 4, None), (13, 'A4', 4, None), (14, 'G4', 4, None), (15, 'E4', 4, None),
]

def text(left):
    lines = {}
    for beat, p, fig, beam in MELODY:
        lines.setdefault(round(beat * Q), {}).setdefault('R', []).append(f"{p}:{fig}" + (f" b{beam}" if beam else ''))
    for beat, notes, fig in left:
        lines.setdefault(round(beat * Q), {}).setdefault('L', []).append(f"{','.join(notes)}:{fig}")
    out = []
    for f in sorted(lines):
        row = lines[f]
        part = []
        if 'L' in row: part.append('L: ' + '  '.join(row['L']))
        if 'R' in row: part.append('R: ' + '  '.join(row['R']))
        out.append(f"f{f:<5} " + '  '.join(part))
    return HEAD + '\n'.join(out) + '\n'

F, Bb, C, Dm = ('F3', 'A3', 'C4'), ('F3', 'Bb3', 'D4'), ('E3', 'G3', 'C4'), ('F3', 'A3', 'D4')
PATTERNS = {
    # 1. A held triad: the chord of the harmony, held while the melody moves; it changes only with the harmony.
    'drawn-left-held-triad': [(0, F, 1), (4, F, 1), (8, C, 1), (12, Bb, 2), (14, C, 2)],
    # 2. A low note, then the chord (Fa2, then Fa3-La3-Do4): one note and one chord, the same shape each time.
    'drawn-left-low-note-then-chord': [
        (0, ('F2',), 4), (1, F, 2), (4, ('F2',), 4), (5, F, 2), (8, ('C2',), 4), (9, C, 2),
        (12, ('Bb1',), 4), (13, Bb, 4), (14, ('C2',), 4), (15, C, 4)],
    # 3. Triads that move in steps with the melody: the same three-finger shape slides one step up, then down.
    'drawn-left-triads-in-steps': [
        (0, ('F3', 'A3', 'C4'), 2), (2, ('G3', 'Bb3', 'D4'), 2), (4, ('A3', 'C4', 'E4'), 2), (6, ('G3', 'Bb3', 'D4'), 2),
        (8, ('F3', 'A3', 'C4'), 2), (10, ('G3', 'Bb3', 'D4'), 2), (12, ('F3', 'A3', 'C4'), 2), (14, ('E3', 'G3', 'C4'), 2)],
}
for name, left in PATTERNS.items():
    t = text(left)
    (OUT / f'{name}.f1').write_text(t)
    r = render_frames(t, px_per_space=10.0, note_ids=False)
    (OUT / f'{name}.svg').write_text(r.svg)
    print(name, r.lines, 'lines', round(r.width, 1), 'x', round(r.height, 1))
