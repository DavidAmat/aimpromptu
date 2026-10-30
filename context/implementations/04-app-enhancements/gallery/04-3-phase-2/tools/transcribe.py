"""Implementation 04-3, Phase 2 (review 2): every Chopin example of the gallery in the app's notation.

The user asked (2026-10-29) that each passage shown as a snapshot also be written in the app's notation and drawn as
the app draws a song. This script reads the bars of each example (``kern``, ``kernBars`` in patterns.json) from the
kern files of the first editions, and writes the notes as the app stores them: onset and length in milliseconds
(one negra = ``QUARTER_MS``), pitch and hand. The app's own path then makes the sheet, inside the backend container:
``propose_frames`` (figures, decoration notes, beams, clefs and 8va, with the armadura of the edition), ``f1.write``
(the F1 frames text) and ``render_frames`` (the drawing).

    python transcribe.py            # research venv (music21); writes transcribe_run.py next to this file
    docker exec -i aimpromptu-backend-1 python - < transcribe_run.py

Decoration notes of the edition (grace notes in kern) become short notes just before their main note, so that the
app's rule finds them again. Ties are joined. Tuplets are kept as times (the app draws no tuplets).
"""

from __future__ import annotations

import json
from pathlib import Path

import music21 as m21

HERE = Path(__file__).resolve().parent
KERN = Path("/home/david/Documents/projects/music/poc-aitu-research/data/raw/kern/humdrum-chopin-first-editions/kern")
QUARTER_MS = 600.0
GRACE_Q = 0.1  # a decoration note: a tenth of a negra (60 ms) before its main note, 50 ms long
GRACE_LEN_Q = 0.083
#: The armadura is the edition's, except where the passage is in another key than the piece and the edition writes
#: it with accidentals: there the app's own choice reads better (its rule gives black keys flats under flats).
KEY = {"ballade1-left-3": 3, "ballade1-right-2": 3}  # Ballade No. 1, 106-108: on Mi, towards La


def passage(kern: str, bars: str) -> dict:
    a, b = (int(x) for x in bars.split("-"))
    score = m21.converter.parse(KERN / kern).stripTies()
    parts = [p for p in score.parts if any(True for _ in p.recurse().notes)]
    mean = [sum(n.pitches[0].midi for n in p.recurse().notes) / len(list(p.recurse().notes)) for p in parts]
    left = min(range(len(parts)), key=lambda i: mean[i])
    # the bars, from the part that has them (a few files number the bars of one staff only)
    ref = next(p for p in [parts[left]] + parts if p.measure(a) is not None and p.measure(b) is not None)
    first = ref.measure(a)
    start = first.getOffsetInHierarchy(ref)
    last = ref.measure(b)
    end = last.getOffsetInHierarchy(ref) + last.duration.quarterLength
    # the armadura in force at the start; a "*kcancel" line reads as a second armadura with nothing at the same
    # place (Waltz Op. 69 No. 2), so at one place the armadura with signs wins
    ks = [(float(k.getOffsetInHierarchy(ref)), k.sharps)
          for k in ref.recurse().getElementsByClass("KeySignature")
          if k.getOffsetInHierarchy(ref) <= start]
    at = max((o for o, _ in ks), default=None)
    here = [sh for o, sh in ks if o == at]
    key = next((sh for sh in here if sh), here[-1] if here else 0)
    notes, graces = [], []
    for i, part in enumerate(parts):
        hand = 2 if i == left else 1
        for n in part.recurse().notes:
            off = float(n.getOffsetInHierarchy(part))
            if not (start <= off < end):
                continue
            for p in n.pitches:
                if n.duration.isGrace:
                    graces.append((off - start, p.midi, hand, n))
                else:
                    notes.append({"q": off - start, "len": float(n.duration.quarterLength), "midi": p.midi,
                                  "hand": hand})
    # the decoration notes before each main note: placed one after the other, ending just before it
    by_main: dict[tuple[float, int], list] = {}
    for q, midi, hand, n in graces:
        by_main.setdefault((q, hand), []).append((id(n), midi))
    for (q, hand), items in by_main.items():
        order = list(dict.fromkeys(i for i, _ in items))
        for i, midi in items:
            k = len(order) - order.index(i)
            notes.append({"q": q - k * GRACE_Q, "len": GRACE_LEN_Q, "midi": midi, "hand": hand, "grace": True})
    lo = min(n["q"] for n in notes)
    shift = -lo if lo < 0 else 0.0
    for n in notes:
        n["q"] += shift
    return {"key": key, "notes": sorted(notes, key=lambda n: (n["q"], n["midi"]))}


IR_EXAMPLES = {"ballade1-right-3", "ballade1-right-4", "ballade1-right-5",  # bars music21 does not read (reviews 4, 5)
               *(f"ballade4-right-{n}" for n in range(3, 9))}  # review 6: two voices in one hand, Ballade No. 4, page 44


def _ballade4_bar65(notes: list[dict]) -> list[dict]:
    """Ballade No. 4, bar 65, as the user's edition prints it. Both kern editions write the left hand's rising notes
    (Do4, Mib4, Solb4, Fa4, second half) on the upper staff, and put an octava Solb4-Solb5 on the fourth corchea where
    the edition has Mib4 over a held La4 natural (arpeggiated)."""
    out = [n for n in notes if not (n["hand"] == 1 and n["q"] == 1.5 and n["midi"] in (66, 78))]
    out.append({"q": 1.5, "len": 0.5, "midi": 63, "hand": 1})
    for n in out:
        if n["hand"] == 1 and n["q"] >= 2.0 and n["midi"] < 67:
            n["hand"] = 2
    return out


FIX = {"ballade4-right-7": _ballade4_bar65}
IR = Path("/home/david/Documents/projects/music/poc-aitu-research/data/derived/ir/nifc")


def passage_ir(kern: str, bars: str) -> dict:
    """The same as ``passage``, read from the research's model of the kern (verovio, ``aitu_research.ir``). music21
    stops reading one staff of 36 works at a voice split (Ballade No. 1 after bar 179); this model has every bar.
    ``bars`` are the printed bar numbers."""
    import sys  # noqa: PLC0415
    sys.path.insert(0, "/home/david/Documents/projects/music/poc-aitu-research/src")
    from aitu_research.ir.model import Piece  # noqa: PLC0415

    piece = Piece.load(IR / f"nifc-{kern[:-4]}.json.gz")
    a, b = bars.split("-")
    ms = {m.label: m for m in piece.measures}
    first, last = ms[a], ms[b]
    start, end = first.onset, last.onset + last.dur
    notes, graces = [], {}
    for e in piece.events:
        if e.kind != "note" or not e.visible or not (start <= e.onset < end):
            continue
        q = float(e.onset - start)
        if e.grace:
            graces.setdefault((q, e.staff), []).append(e.midi)
        elif e.tie in (None, "i"):
            dur = float(e.dur)
            if e.tie == "i":  # join the tied notes that follow
                t, nxt = e.onset + e.dur, True
                while nxt:
                    nxt = next((x for x in piece.events if x.kind == "note" and x.onset == t and x.midi == e.midi
                                and x.staff == e.staff and x.tie in ("m", "t")), None)
                    if nxt:
                        dur += float(nxt.dur)
                        t += nxt.dur
                        nxt = nxt.tie == "m"
            notes.append({"q": q, "len": dur, "midi": e.midi, "hand": e.staff})
    for (q, staff), ms_ in graces.items():
        for k, m in enumerate(reversed(ms_)):
            notes.append({"q": q - (k + 1) * GRACE_Q, "len": GRACE_LEN_Q, "midi": m, "hand": staff, "grace": True})
    # a note that both voices of one hand share is printed once and played once: keep the longer
    keep: dict[tuple, dict] = {}
    for n in notes:
        k = (n["q"], n["midi"], n["hand"], n.get("grace", False))
        if k not in keep or n["len"] > keep[k]["len"]:
            keep[k] = n
    notes = list(keep.values())
    lo = min(n["q"] for n in notes)
    for n in notes:
        n["q"] -= min(lo, 0.0)
    return {"key": first.key, "notes": sorted(notes, key=lambda n: (n["q"], n["midi"]))}


RUN = '''"""Generated by transcribe.py: draws every Chopin example in the app's notation (run in the backend container)."""
import json
from pathlib import Path
import numpy as np
from aitu_backend.pmn.notes import Notes, HAND_LEFT, HAND_RIGHT
from aitu_backend.sheet.proposal.frames import propose_frames
from aitu_backend.sheet.sheet import f1
from aitu_backend.sheet.engrave.frames import render_frames

OUT = Path("/home/app/04-3-phase-2/transcribed")
OUT.mkdir(parents=True, exist_ok=True)
DATA = json.loads(__DATA__)
Q = __Q__
for name, p in DATA.items():
    ns = p["notes"]
    notes = Notes(
        id=np.arange(1, len(ns) + 1),
        key=[n["midi"] - 21 for n in ns],
        on_ms=[1000.0 + n["q"] * Q for n in ns],
        len_ms=[max(n["len"] * Q, 30.0) for n in ns],
        hand=[HAND_LEFT if n["hand"] == 2 else HAND_RIGHT for n in ns],
    )
    sheet = propose_frames(notes, key=p["key"], quarter_ms=Q).sheet
    text = f1.write(sheet, mode="frames")
    (OUT / f"{name}.f1").write_text(text)
    r = render_frames(text, px_per_space=10.0, note_ids=False)
    (OUT / f"{name}.svg").write_text(r.svg)
    graces = sum(1 for n in sheet.notes if n.grace)
    print(f"{name:24} notes={len(ns):3} key={p['key']:+d} lines={r.lines} graces={graces}")
'''


def main() -> None:
    pats = json.loads((HERE.parent / "patterns.json").read_text())["patterns"]
    data = {}
    for p in pats:
        for e in p["examples"]:
            if e.get("kern") and (e["image"] or "").endswith(".png"):
                name = e["image"][:-4]
                read = passage_ir if name in IR_EXAMPLES else passage
                data[name] = read(e["kern"], e["kernBars"])
                if name in FIX:
                    data[name]["notes"] = sorted(FIX[name](data[name]["notes"]), key=lambda n: (n["q"], n["midi"]))
                data[name]["key"] = KEY.get(name, data[name]["key"])
    (HERE / "transcribe_run.py").write_text(
        RUN.replace("__DATA__", repr(json.dumps(data))).replace("__Q__", repr(QUARTER_MS)))
    print(len(data), "passages:", ", ".join(f"{k} ({len(v['notes'])})" for k, v in data.items()))


if __name__ == "__main__":
    main()
