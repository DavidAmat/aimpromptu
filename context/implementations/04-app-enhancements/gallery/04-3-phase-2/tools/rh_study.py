"""Implementation 04-3, Phase 2 (review 3): measures of the right hand in every two-bar window of Chopin's works.

The user asked (2026-10-29) for more right-hand patterns from more works, with the levels judged by hand motion:
a static right hand is easy, also with chords; medium is fast or with chords but with a pattern that repeats; hard is
chords moving up and down in one run, or fast notes with no pattern and many accidentals or ornaments. This script
measures, for each window of two bars of the right hand (the staff with the higher notes):

- ``fastest``: the shortest time between two onsets (negras: 1, corcheas: 0.5, semicorcheas: 0.25, fusas: 0.125);
  ``density``: onsets per negra;
- ``chord_max``, ``chord_mean``: notes per onset; ``chord_share``: share of onsets with two notes or more;
- ``moves``, ``shift``, ``jumps``: an open hand of one octave over the notes, which moves only when a note is out of
  reach (as the research's hand tracker): how many moves, the semitones moved, the moves larger than a fifth;
  ``span``: the range of the window; ``stretch``: chords wider than an octave;
- ``pattern``: the share of beats whose shape (rhythm, intervals from the first note, chord sizes) repeats the beat
  before or the one before it, transposed or not;
- ``chord_run``: the longest run of chords (two notes or more) that move in one direction, onset after onset;
- ``altered``: the share of notes whose sign differs from the armadura (sharps, naturals, flats); ``doubles``:
  double sharps and double flats; ``ornaments``: trills, mordents, turns; ``graces``: decoration notes.

    python rh_study.py OUT.jsonl     # research venv (music21); about a minute on 32 cores
"""

from __future__ import annotations

import json
import re
import sys
from multiprocessing import Pool
from pathlib import Path

import music21 as m21

KERN = Path("/home/david/Documents/projects/music/poc-aitu-research/data/raw/kern/humdrum-chopin-first-editions/kern")
SKIP = ("003", "008", "065", "074", "GDC")  # with cello or violin, or songs


def files() -> list[Path]:
    """One edition per piece: the first file of each opus and piece number."""
    seen, out = set(), []
    for f in sorted(KERN.glob("*.krn")):
        if f.name.startswith(SKIP):
            continue
        head = next((l for l in f.open(errors="ignore") if l.startswith("**")), "")
        if [t.strip() for t in head.split("\t")].count("**kern") != 2:  # two piano staves only
            continue
        opus = re.match(r"^([0-9A-Za-z]+)", f.name).group(1)
        num = re.search(r"-(\d{3})(?:-|\.krn)", f.name)
        sub = re.match(r"^\d+_(\d+)", f.name)
        key = (opus, num.group(1) if num else (sub.group(1) if sub else ""))
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


def tracker(onsets):
    """Moves of an open hand of one octave (12 semitones) over the onsets [(lo, hi)]."""
    if not onsets:
        return 0, 0, 0, 0
    p = onsets[0][0]
    moves = shift = jumps = stretch = 0
    for lo, hi in onsets:
        if hi - lo > 12:
            stretch += 1
        if lo >= p and hi <= p + 12:
            continue
        # the hand moves only as far as it must: down to the low note, or up until the high note is in reach
        new = lo if (lo < p or hi - lo > 12) else hi - 12
        moves += 1
        shift += abs(new - p)
        jumps += abs(new - p) > 7
        p = new
    return moves, shift, jumps, stretch


def armadura_alter(sharps: int) -> dict[str, int]:
    ks = m21.key.KeySignature(sharps)
    return {p.step: int(p.alter) for p in ks.alteredPitches}


def study(path: Path) -> list[dict]:
    try:
        score = m21.converter.parse(path).stripTies()
    except Exception as exc:  # noqa: BLE001 - a file music21 cannot read is reported and left out
        return [{"file": path.name, "error": str(exc)[:200]}]
    parts = [p for p in score.parts if any(True for _ in p.recurse().notes)]
    if len(parts) < 2:
        return []
    mean = [sum(n.pitches[-1].midi for n in p.recurse().notes) / max(1, len(list(p.recurse().notes))) for p in parts]
    rh = parts[max(range(len(parts)), key=lambda i: mean[i])]
    title = ""
    for line in path.open(errors="ignore"):
        if line.startswith("!!!OTL"):
            title = line.split(":", 1)[1].strip()
            break
    measures = [m for m in rh.getElementsByClass("Measure")]
    keys = [(float(k.getOffsetInHierarchy(rh)), k.sharps) for k in rh.recurse().getElementsByClass("KeySignature")]
    meters = [(float(t.getOffsetInHierarchy(rh)), t.numerator, t.denominator)
              for t in rh.recurse().getElementsByClass("TimeSignature")]
    out = []
    for i in range(0, len(measures) - 1):
        a, b = measures[i], measures[i + 1]
        if a.number is None or a.number < 1:
            continue
        start = float(a.getOffsetInHierarchy(rh))
        end = float(b.getOffsetInHierarchy(rh)) + float(b.duration.quarterLength)
        # the armadura in force; a "*kcancel" reads as a second armadura with no signs at the same place
        at = max((o for o, _ in keys if o <= start + 1e-6), default=None)
        here = [sh for o, sh in keys if o == at]
        k = next((sh for sh in here if sh), here[-1] if here else 0)
        num, den = next(((n_, d_) for o, n_, d_ in reversed(meters) if o <= start + 1e-6), (4, 4))
        beat = 1.5 if den == 8 and num % 3 == 0 else 4.0 / den
        alter = armadura_alter(k)
        on: dict[float, list] = {}
        graces = ornaments = altered = doubles = total = 0
        for m in (a, b):
            for n in m.recurse().notes:
                off = float(n.getOffsetInHierarchy(rh))
                for p in n.pitches:
                    total += 1
                    acc = int(p.alter)
                    if acc != alter.get(p.step, 0):
                        altered += 1
                    if abs(acc) == 2:
                        doubles += 1
                if n.duration.isGrace:
                    graces += 1
                    continue
                if any(isinstance(e, (m21.expressions.Trill, m21.expressions.GeneralMordent, m21.expressions.Turn))
                       for e in n.expressions):
                    ornaments += 1
                on.setdefault(round(off, 4), []).extend(p.midi for p in n.pitches)
        times = sorted(on)
        if len(times) < 2:
            continue
        chords = [sorted(set(on[t])) for t in times]
        sizes = [len(c) for c in chords]
        iois = [round(t2 - t1, 4) for t1, t2 in zip(times, times[1:])]
        moves, shift, jumps, stretch = tracker([(c[0], c[-1]) for c in chords])
        # pattern: beats whose shape repeats one of the two beats before
        shapes = {}
        for t, c in zip(times, chords):
            bi = int((t - start) // beat)
            shapes.setdefault(bi, []).append((round((t - start) - bi * beat, 3), c[-1], len(c)))
        sh = []
        for bi in sorted(shapes):
            ev = shapes[bi]
            if len(ev) < 2:
                continue
            top0 = ev[0][1]
            sh.append(tuple((o, top - top0, s) for o, top, s in ev))
        rep = sum(1 for j in range(1, len(sh)) if sh[j] == sh[j - 1] or (j > 1 and sh[j] == sh[j - 2]))
        pattern = rep / (len(sh) - 1) if len(sh) > 1 else 0.0
        # the longest run of chords moving in one direction
        run = best = 0
        prev_dir = 0
        for c1, c2 in zip(chords, chords[1:]):
            d = (c2[-1] > c1[-1]) - (c2[-1] < c1[-1])
            if len(c1) >= 2 and len(c2) >= 2 and d != 0 and (d == prev_dir or run == 0):
                run = run + 1 if d == prev_dir else 2
                prev_dir = d
            else:
                run, prev_dir = 0, 0
            best = max(best, run)
        lo = min(c[0] for c in chords)
        hi = max(c[-1] for c in chords)
        out.append({
            "file": path.name, "title": title, "bars": f"{a.number}-{b.number}", "key": k, "meter": f"{num}/{den}",
            "quarters": round(end - start, 3), "onsets": len(times), "fastest": min(iois),
            "density": round(len(times) / max(end - start, 1e-6), 3), "chord_max": max(sizes),
            "chord_mean": round(sum(sizes) / len(sizes), 2), "chord_share": round(sum(s >= 2 for s in sizes) / len(sizes), 2),
            "moves": moves, "shift": shift, "jumps": jumps, "stretch": stretch, "span": hi - lo, "low": lo, "high": hi,
            "pattern": round(pattern, 2), "chord_run": best, "altered": round(altered / max(total, 1), 2),
            "doubles": doubles, "ornaments": ornaments, "graces": graces,
        })
    return out


def main() -> None:
    fs = files()
    with Pool(30) as pool:
        rows = [r for rs in pool.imap_unordered(study, fs, chunksize=1) for r in rs]
    Path(sys.argv[1]).write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    print(len(fs), "pieces,", sum("error" not in r for r in rows), "windows,", sum("error" in r for r in rows), "errors")


if __name__ == "__main__":
    main()
