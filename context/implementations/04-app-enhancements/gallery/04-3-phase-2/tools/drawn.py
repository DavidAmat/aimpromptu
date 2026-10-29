"""Implementation 04-3, Phase 2, task 2.5: left-hand patterns drawn by the app's engine (from the brief and the
user's review of the first gallery, 2026-10-29).

Every drawing has the same right-hand melody in Fa major and the same harmony (Fa for two bars, Do, then Sib and Do
for half a bar each), so that only the left hand changes from one pattern to the next. A pattern is a template of
four beats; a harmony of two beats takes its first half. Run inside the backend container (it reads no database):

    docker exec -i aimpromptu-backend-1 python - < drawn.py

Writes ``drawn-left-<id>.f1`` and ``.svg`` to /home/app/04-3-phase-2/ and prints, per pattern, the widest chord and
the widest range of a half bar (semitones), for the report.
"""

from pathlib import Path

from aitu_backend.sheet.engrave.frames import render_frames
from aitu_backend.sheet.sheet import f1

OUT = Path("/home/app/04-3-phase-2")
OUT.mkdir(parents=True, exist_ok=True)
Q = 12  # frames of one negra (quarterMs=480, frameMs=40)
HEAD = "F1 frames frameMs=40 quarterMs=480\nkey=1b clefs: R=treble L=bass\n"

MELODY = [  # (beat, pitch, figure, beam)
    (0, "A4", 4, None), (1, "C5", 4, None), (2, "F5", 4, None), (3, "E5", 8, 1), (3.5, "D5", 8, 1),
    (4, "C5", 2, None), (6, "A4", 4, None), (7, "Bb4", 4, None),
    (8, "C5", 4, None), (9, "D5", 4, None), (10, "E5", 4, None), (11, "D5", 8, 2), (11.5, "C5", 8, 2),
    (12, "Bb4", 4, None), (13, "A4", 4, None), (14, "G4", 4, None), (15, "C5", 4, None),
]
HARMONY = [(0, 4, "F"), (4, 4, "F"), (8, 4, "C"), (12, 2, "Bb"), (14, 2, "C")]

# The left-hand notes of each chord, in one hand position near Fa3 (t: the triad; four: the triad and the octava
# of its lowest note; low: a bass note near the chord; deep: the bass an octave lower, as the approved
# low-note-then-chord drawing has it; six: the chord with its sixth; open: root, fifth, octava, tenth).
CHORDS = {
    "F": dict(low="F2", deep="F2", low5="C3", oct=("F2", "F3"), t=("F3", "A3", "C4"), inv=("A3", "C4", "F4"),
              four=("F3", "A3", "C4", "F4"), six=("F3", "A3", "C4", "D4"), open=("F2", "C3", "F3", "A3"),
              top="C4", fifth=("F3", "C4"), sixth=("F3", "D4"), dy=("A3", "C4"), up2=("C4", "F4"), bass="F3",
              th=(("A3", "C4"), ("Bb3", "D4"))),
    "C": dict(low="C3", deep="C2", low5="G2", oct=("C2", "C3"), t=("E3", "G3", "C4"), inv=("G3", "C4", "E4"),
              four=("E3", "G3", "C4", "E4"), six=("C3", "E3", "G3", "A3"), open=("C2", "G2", "C3", "E3"),
              top="G3", fifth=("C3", "G3"), sixth=("C3", "A3"), dy=("G3", "C4"), up2=("C4", "E4"), bass="C3",
              th=(("E3", "G3"), ("F3", "A3"))),
    "Bb": dict(low="Bb2", deep="Bb1", low5="F2", oct=("Bb1", "Bb2"), t=("F3", "Bb3", "D4"), inv=("Bb3", "D4", "F4"),
               four=("F3", "Bb3", "D4", "F4"), six=("Bb2", "D3", "F3", "G3"), open=("Bb1", "F2", "Bb2", "D3"),
               top="F3", fifth=("Bb2", "F3"), sixth=("Bb2", "G3"), dy=("Bb3", "D4"), up2=("D4", "F4"), bass="Bb2",
               th=(("D3", "F3"), ("D3", "G3"))),
}


def k(key, i=None):
    """A note (or chord) of the chord: ``k('t', 0)`` the lowest note of the triad, ``k('t')`` the whole triad."""
    return (key, i)


def run(keys, start, step, beam_every):
    """Notes one after the other from ``start``, each ``step`` beats long, a beam every ``beam_every`` notes."""
    return [(start + j * step, key, step, f"r{start}-{j // beam_every}") for j, key in enumerate(keys)]


T0, T1, T2 = k("t", 0), k("t", 1), k("t", 2)
F0, F1, F2, F3 = (k("four", i) for i in range(4))
S0, S1, S2, S3 = (k("six", i) for i in range(4))
O0, O1, O2, O3 = (k("open", i) for i in range(4))
LOW, LOW5, OCT, TRI, INV, FOUR = k("low"), k("low5"), k("oct"), k("t"), k("inv"), k("four")
FIFTH, SIXTH, DY, UP2, BASS, TOP = k("fifth"), k("sixth"), k("dy"), k("up2"), k("bass"), k("top")
D0, D1 = k("dy", 0), k("dy", 1)
R0, R1 = k("rock", 0), k("rock", 1)  # the first third of th: within reach of the held bass

# id: template (beat, notes, length in beats, beam label or None). A held note never starts at the same beat as
# the notes moving above it: the engine would draw both as one chord with the shorter figure.
TEMPLATES = {
    # ---- the first three (the brief)
    "held-triad": [(0, TRI, 4, None)],
    "low-note-then-chord": [(0, k("deep"), 1, None), (1, TRI, 3, None)],
    "triads-in-steps": "steps",
    # ---- easy: one hand position, a triad or two notes
    "low-note-then-two-notes-rocking": [(0, LOW, 1, None)] + run([D0, D1, D0, D1, D0, D1], 1, 0.5, 6),
    "alberti": run([T0, T2, T1, T2], 0, 0.5, 4) + run([T0, T2, T1, T2], 2, 0.5, 4),
    "triad-up-and-down": run([T0, T1, T2, T1], 0, 0.5, 4) + run([T0, T1, T2, T1], 2, 0.5, 4),
    "triad-up-and-hold": run([T0, T1], 0, 0.5, 2) + [(1, T2, 1, None)] + run([T0, T1], 2, 0.5, 2) + [(3, T2, 1, None)],
    "triad-down-and-hold": run([T2, T1], 0, 0.5, 2) + [(1, T0, 1, None)] + run([T2, T1], 2, 0.5, 2) + [(3, T0, 1, None)],
    "chord-then-two-notes-above": [(0, TRI, 1, None), (1, UP2, 1, None), (2, TRI, 1, None), (3, UP2, 1, None)],
    "held-two-note-chord": [(0, FIFTH, 2, None), (2, FIFTH, 2, None)],
    "low-note-then-two-note-chords": [(0, LOW, 1, None), (1, DY, 1, None), (2, DY, 1, None), (3, DY, 1, None)],
    "two-note-chord-then-arpeggio": [(0, FIFTH, 1, None)] + run([T0, T1, T2, T1, T0, T1], 1, 0.5, 6),
    "fifth-to-sixth-rocking": [(0, FIFTH, 1, None), (1, SIXTH, 1, None), (2, FIFTH, 1, None), (3, SIXTH, 1, None)],
    # ---- medium: a new rhythm or a new chord note
    "octave-then-arpeggio": [(0, OCT, 1, None)] + run([T0, T1, T2, T1, T0, T1], 1, 0.5, 6),
    "low-note-then-off-beat-chords": [(0, LOW, 1, None), (1.5, TRI, 0.5, None), (2.5, TRI, 0.5, None),
                                      (3.5, TRI, 0.5, None)],
    "added-sixth-up-and-down": run([S0, S1, S2, S3], 0, 0.5, 4) + run([S2, S1, S0, S1], 2, 0.5, 4),
    "held-bass-under-rocking-notes": [(0, BASS, 4, None)] + run([R0, R1, R0, R1, R0, R1, R0], 0.5, 0.5, 7),
    "triad-in-semicorcheas": sum((run([T0, T1, T2, T1], b, 0.25, 4) for b in range(4)), []),
    "octave-then-two-beamed-chords": [(0, OCT, 1, None)] + run([TRI, TRI], 1, 0.5, 2) + [(2, OCT, 1, None)]
    + run([TRI, TRI], 3, 0.5, 2),
    "alternating-bass-and-chord": [(0, LOW, 1, None), (1, TRI, 1, None), (2, LOW5, 1, None), (3, TRI, 1, None)],
    "arpeggio-three-three-two": run([T0, T1, T2], 0, 0.5, 3) + run([T0, T1, T2], 1.5, 0.5, 3) + run([T0, T1], 3, 0.5, 2),
    "octave-rocking": run([k("oct", 0), k("oct", 1)] * 2, 0, 0.5, 4) + run([k("oct", 0), k("oct", 1)] * 2, 2, 0.5, 4),
    "chord-then-arpeggio-down": [(0, TRI, 1, None)] + run([k("up2", 1), T2, T1, T0, T1, T2], 1, 0.5, 6),
    # ---- hard: the chord gets a fourth note (its octava), or the hand moves more
    "four-note-arpeggio-up-and-down": run([F0, F1, F2, F3], 0, 0.5, 4) + run([F2, F1, F0, F1], 2, 0.5, 4),
    "low-note-then-four-note-chords": [(0, LOW, 1, None), (1, FOUR, 1, None), (2, FOUR, 1, None), (3, FOUR, 1, None)],
    "open-arpeggio-up-and-down": run([O0, O1, O2, O3], 0, 0.5, 4) + run([TOP, O3, O2, O1], 2, 0.5, 4),
    "alberti-over-an-octave": run([F0, F3, F2, F3], 0, 0.5, 4) + run([F1, F3, F2, F3], 2, 0.5, 4),
    "four-note-wave-in-semicorcheas": [(0, LOW, 1, None)] + run([F0, F1, F2, F3], 1, 0.25, 4)
    + run([F2, F1, F0, F1], 2, 0.25, 4) + run([F2, F3, F2, F1], 3, 0.25, 4),
    "low-note-then-chord-moving-up": [(0, OCT, 1, None)] + run([TRI, INV], 1, 0.5, 2) + [(2, OCT, 1, None)]
    + run([TRI, INV], 3, 0.5, 2),
    "octave-then-four-note-chords": [(0, OCT, 1, None)] + run([FOUR] * 6, 1, 0.5, 2),
    "held-bass-under-moving-thirds": [(0, BASS, 4, None)] + run([k("th", 0), k("th", 1)] * 3 + [k("th", 0)], 0.5, 0.5, 7),
    "off-beat-four-note-chords": [(0, OCT, 1, None), (1.5, FOUR, 0.5, None), (2.5, FOUR, 0.5, None),
                                  (3.5, FOUR, 0.5, None)],
    "arpeggio-up-then-chord": run([F0, F1, F2, F3], 0, 0.5, 4) + [(2, FOUR, 2, None)],
}

FIGURE = {4: 1, 3: 2, 2: 2, 1: 4, 0.5: 8, 0.25: 16}
STEPS = {  # the triads of triads-in-steps, one every two beats
    0: ("F3", "A3", "C4"), 2: ("G3", "Bb3", "D4"), 4: ("A3", "C4", "E4"), 6: ("G3", "Bb3", "D4"),
    8: ("F3", "A3", "C4"), 10: ("G3", "Bb3", "D4"), 12: ("F3", "A3", "C4"), 14: ("E3", "G3", "C4")}


def notes_of(chord, ref):
    key, i = ref
    if key == "rock":
        return (CHORDS[chord]["th"][0][i],)
    v = CHORDS[chord][key]
    if key == "th":
        return v[i]
    if i is not None:
        return (v[i],)
    return (v,) if isinstance(v, str) else v


def left(tpl):
    """The left-hand events of the whole passage: (beat, notes, figure, beam number or None)."""
    if tpl == "steps":
        return [(b, n, 2, None) for b, n in STEPS.items()]
    out, beams = [], {}
    for si, (start, length, chord) in enumerate(HARMONY):
        for beat, ref, dur, beam in tpl:
            if beat >= length:
                continue
            dur = min(dur, length - beat)
            label = None
            if beam is not None:
                label = beams.setdefault((si, beam), 10 + len(beams))
            out.append((start + beat, notes_of(chord, ref), FIGURE[dur], label))
    return out


def text(events, right=None):
    """The F1 frames text: the left-hand ``events`` under the melody, or under ``right`` (beat, notes, figure, beam,
    tag) for the right-hand patterns."""
    lines = {}
    if right is None:
        right = [(beat, (p,), fig, beam, "") for beat, p, fig, beam in MELODY]
    for beat, notes, fig, beam, tag in right:
        lines.setdefault(round(beat * Q), {}).setdefault("R", []).append(
            f"{','.join(notes)}:{fig}" + (f" {tag}" if tag else "") + (f" b{beam}" if beam else ""))
    for beat, notes, fig, beam in events:
        lines.setdefault(round(beat * Q), {}).setdefault("L", []).append(
            f"{','.join(notes)}:{fig}" + (f" b{beam}" if beam else ""))
    out = []
    for f in sorted(lines):
        row = lines[f]
        part = []
        if "L" in row:
            part.append("L: " + "  ".join(row["L"]))
        if "R" in row:
            part.append("R: " + "  ".join(row["R"]))
        out.append(f"f{f:<5} " + "  ".join(part))
    return HEAD + "\n".join(out) + "\n"


def spans(t):
    """(widest chord, widest range of a half bar) of the left hand, in semitones."""
    sheet = f1.read(t)
    lh = [n for n in sheet.notes if n.staff == 2]
    chord = max(max(m.midi for m in lh if m.frame == n.frame) - min(m.midi for m in lh if m.frame == n.frame)
                for n in lh)
    wide = 0
    for h in range(0, 16 * Q, 2 * Q):
        ns = sorted((n for n in lh if h <= n.frame < h + 2 * Q), key=lambda n: (n.frame, n.midi))
        if ns:
            wide = max(wide, max(n.midi for n in ns) - min(n.midi for n in ns))
    return chord, wide


# ---------------------------------------------------------------- right hand (review 3, 2026-10-29)
# The right-hand patterns that the study of Chopin's works did not give, drawn over the held triad of the left hand
# and the same harmony, so that only the right hand changes. Notes in Fa major; chromatic notes take sharps.

SCALE = {5: "F", 7: "G", 9: "A", 10: "Bb", 0: "C", 2: "D", 4: "E"}
CHROMA = {6: "F#", 8: "G#", 11: "B", 1: "C#", 3: "D#"}
PCS = sorted(SCALE)


def midi(name):
    step = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}[name[0]]
    acc = name[1:-1]
    return 12 * (int(name[-1]) + 1) + step + (1 if acc == "#" else -1 if acc == "b" else 0)


def name(m):
    pc = m % 12
    return f"{SCALE.get(pc) or CHROMA[pc]}{m // 12 - 1}"


def step(m, k):
    """``m`` moved ``k`` steps of the scale of Fa major (``m`` in the scale)."""
    octave, i = divmod(PCS.index(m % 12) + k, 7)
    return 12 * (m // 12 + octave) + PCS[i]


RCH = {  # the right hand's chords near the melody: the triad, with the octava, the triad one position higher
    "F": dict(t=("F4", "A4", "C5"), four=("F4", "A4", "C5", "F5")),
    "C": dict(t=("E4", "G4", "C5"), four=("E4", "G4", "C5", "E5")),
    "Bb": dict(t=("F4", "Bb4", "D5"), four=("F4", "Bb4", "D5", "F5")),
}


def over_harmony(tpl):
    """A template of four beats over each harmony, as the left-hand patterns: (beat, f(chord) -> notes, len, beam)."""
    out, beams = [], {}
    for si, (start, length, chord) in enumerate(HARMONY):
        for beat, notes, dur, beam in tpl:
            if beat >= length:
                continue
            dur = min(dur, length - beat)
            label = beams.setdefault((si, beam), 30 + len(beams)) if beam is not None else None
            out.append((start + beat, tuple(notes(chord)), FIGURE[dur], label, ""))
    return out


def rrun(fns, start, step_, every):
    return [(start + j * step_, f, step_, f"r{start}-{j // every}") for j, f in enumerate(fns)]


def t(i):
    return lambda ch: (RCH[ch]["t"][i],)


def octave_up(i):
    return lambda ch: (name(midi(RCH[ch]["t"][i]) + 12),)


TRI_R, FOUR_R = (lambda ch: RCH[ch]["t"]), (lambda ch: RCH[ch]["four"])
DY_LO = lambda ch: RCH[ch]["t"][:2]  # noqa: E731
DY_HI = lambda ch: RCH[ch]["t"][1:]  # noqa: E731


def melody(transform, *, only=None):
    """The melody, each note changed by ``transform(midi, figure) -> [(beat offset, notes, figure, tag)]``."""
    out, beam = [], 50
    for beat, p, fig, b in MELODY:
        if only and fig not in only:
            out.append((beat, (p,), fig, b, ""))
            continue
        for off, notes, f, tag in transform(midi(p), fig):
            out.append((beat + off, notes, f, (beam if f >= 8 and len(transform(midi(p), fig)) > 1 else b), tag))
        beam += 1
    return out


RIGHT = {
    # ---- easy: the hand stays in one position, also with chords
    "five-finger-melody": [(b, (p,), f, None, "") for b, p, f in [
        (0, "F4", 4), (1, "A4", 4), (2, "G4", 4), (3, "Bb4", 4), (4, "A4", 2), (6, "G4", 4), (7, "F4", 4),
        (8, "E4", 4), (9, "G4", 4), (10, "C5", 2), (12, "Bb4", 4), (13, "A4", 4), (14, "G4", 4), (15, "E4", 4)]],
    "chords-on-each-beat": over_harmony([(0, TRI_R, 1, None), (1, TRI_R, 1, None), (2, TRI_R, 1, None),
                                         (3, TRI_R, 1, None)]),
    "repeated-chord-in-corcheas": over_harmony(rrun([TRI_R] * 8, 0, 0.5, 4)),
    "two-note-chords-in-one-position": over_harmony([(0, DY_LO, 1, None), (1, DY_HI, 1, None), (2, DY_LO, 1, None),
                                            (3, DY_HI, 1, None)]),
    "broken-triad-in-one-position": over_harmony(rrun([t(0), t(2), t(1), t(2)] * 2, 0, 0.5, 4)),
    # ---- medium: a pattern that repeats, small chords, a few accidentals
    "melody-in-thirds": melody(lambda m, f: [(0, (name(step(m, -2)), name(m)), f, "")]),
    "melody-landing-on-a-chord": "landing",  # below
    "broken-chord-up-and-down-in-semicorcheas": over_harmony(
        rrun([t(0), t(1), t(2), octave_up(0), t(2), t(1), t(0), t(1)] * 2, 0, 0.25, 4)),
    "turn-around-the-melody": melody(lambda m, f: [(0, (name(m),), 16, ""), (0.25, (name(step(m, 1)),), 16, ""),
                                                   (0.5, (name(m),), 16, ""), (0.75, (name(step(m, -1)),), 16, "")]
                                     + ([(1, (name(m),), 4, "")] if f == 2 else []), only={4, 2}),
    "chromatic-neighbour": melody(lambda m, f: [(0, (name(m - 1),), 8, ""), (0.5, (name(m),), 8, "")], only={4}),
    # ---- hard: chords moving in a run, fast notes, accidentals, ornaments
    "chords-climbing-in-corcheas": over_harmony(rrun(
        [(lambda k: lambda ch: tuple(name(step(midi(x), k)) for x in RCH[ch]["t"]))(k) for k in (0, 1, 2, 3, 2, 1, 0, 1)],
        0, 0.5, 4)),
    "sixths-in-semicorcheas": over_harmony(rrun(
        [(lambda k: lambda ch: (name(step(midi(RCH[ch]["t"][0]), -k)), name(step(midi(RCH[ch]["t"][0]), 5 - k))))(k)
         for k in (0, 1, 2, 3, 2, 1, 0, 1)] * 2, 0, 0.25, 4)),
    "melody-in-octaves": melody(lambda m, f: [(0, (name(m - 12), name(m)), f, "")]),
    "chromatic-run": [],  # below, from _chromatic()
    "trill-on-long-notes": melody(lambda m, f: [(0, (name(m),), f, "tr")], only={2}),
    # ---- super hard: octavas and full chords that move fast, chromatic double notes
    "octaves-in-semicorcheas": over_harmony(rrun(
        [(lambda k: lambda ch: (name(step(midi(RCH[ch]["t"][2]), k) - 12), name(step(midi(RCH[ch]["t"][2]), k))))(k)
         for k in (0, 1, 2, 3, 4, 3, 2, 1)] * 2, 0, 0.25, 4)),
    "chords-jumping-an-octave": over_harmony(rrun(
        [FOUR_R, lambda ch: tuple(name(midi(x) + 12) for x in RCH[ch]["four"])] * 4, 0, 0.5, 2)),
    "chromatic-thirds": [],  # below, from _chromatic(thirds=True)
}


def _chromatic(thirds=False):
    """A chromatic run of semicorcheas, eight semitones up from the top of each chord and back (thirds: with a
    major third under each note)."""
    out, n = [], 70
    for start, length, chord in HARMONY:
        top = midi(RCH[chord]["t"][2])
        line = [top + k for k in range(8)] + [top + 8 - k for k in range(8)]
        for j, m in enumerate(line[: int(length * 4)]):
            notes = (name(m - 4), name(m)) if thirds else (name(m),)
            out.append((start + j * 0.25, notes, 16, n + j // 4, ""))
        n += 8
    return out


def _landing(at=(4, 10, 15)):
    """The melody in single notes; at the end of each phrase, the two notes of the harmony below it make a chord."""
    harmony_at = {b: ch for start, length, ch in HARMONY for b in range(start, start + length)}
    out = []
    for beat, p, fig, b in MELODY:
        notes = (p,)
        if beat in at:
            m = midi(p)
            tones = sorted({midi(x) % 12 for x in RCH[harmony_at[int(beat)]]["t"]})
            below = [k for k in range(m - 1, m - 12, -1) if k % 12 in tones][:2]
            notes = tuple(name(k) for k in sorted(below)) + (p,)
        out.append((beat, notes, fig, b, ""))
    return out


RIGHT["melody-landing-on-a-chord"] = _landing()
RIGHT["chromatic-run"] = _chromatic()
RIGHT["chromatic-thirds"] = _chromatic(thirds=True)
HELD = left(TEMPLATES["held-triad"])

for name_, right in RIGHT.items():
    tx = text(HELD, right)
    (OUT / f"drawn-right-{name_}.f1").write_text(tx)
    r = render_frames(tx, px_per_space=10.0, note_ids=False)
    (OUT / f"drawn-right-{name_}.svg").write_text(r.svg)
    print(f"right {name_:40} lines={r.lines}")

for name, tpl in TEMPLATES.items():
    t = text(left(tpl))
    (OUT / f"drawn-left-{name}.f1").write_text(t)
    r = render_frames(t, px_per_space=10.0, note_ids=False)
    (OUT / f"drawn-left-{name}.svg").write_text(r.svg)
    c, w = spans(t)
    print(f"{name:36} lines={r.lines} chord={c} range={w}")
