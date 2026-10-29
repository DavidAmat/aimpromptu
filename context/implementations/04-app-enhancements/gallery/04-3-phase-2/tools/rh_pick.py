"""Implementation 04-3, Phase 2 (review 3): random right-hand candidates per level and kind, from rh_study.py's measures.

The kinds follow the user's rules (2026-10-29): a static right hand is easy, also with chords; medium is fast or with
small chords, but with a shape that repeats; hard is chords that move in one run, or fast notes with no pattern,
accidentals or ornaments; super hard is fast chords or octavas that move, very fast and wide notes, or jumps. Two
windows per kind, each from a different work, drawn at random (fixed seed). The agent then looks at every candidate
drawn by the app and keeps, names and levels the patterns (the measures only find candidates).

    python rh_pick.py RH.jsonl          # writes rh_candidates.json and rh_run.py next to this file
    docker exec -i aimpromptu-backend-1 python - < rh_run.py
"""

from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

from transcribe import QUARTER_MS, RUN, passage

HERE = Path(__file__).resolve().parent

KINDS = {  # level, kind: rule on the measures of a two-bar window
    ("easy", "slow-single"): lambda r: r["fastest"] >= 1 and r["chord_share"] == 0 and r["moves"] <= 1 and r["onsets"] >= 4,
    ("easy", "corcheas-single"): lambda r: r["fastest"] == 0.5 and r["chord_share"] < 0.2 and r["moves"] <= 1 and r["onsets"] >= 8,
    ("easy", "held-chords"): lambda r: r["fastest"] >= 1 and r["chord_share"] >= 0.7 and r["chord_mean"] >= 2.5 and r["moves"] <= 1,
    ("easy", "two-note-chords"): lambda r: r["fastest"] >= 0.5 and r["chord_share"] >= 0.7 and r["chord_mean"] <= 2.2 and r["moves"] <= 1,
    ("easy", "repeated-chord"): lambda r: r["chord_share"] >= 0.7 and r["pattern"] >= 0.8 and r["moves"] == 0 and r["density"] >= 2,
    ("easy", "fast-in-position"): lambda r: r["fastest"] <= 0.25 and r["moves"] <= 1 and r["span"] <= 12 and r["pattern"] >= 0.6,
    ("medium", "fast-repeating-shape"): lambda r: r["fastest"] <= 0.25 and r["pattern"] >= 0.6 and 2 <= r["moves"] <= 6 and r["chord_share"] < 0.3,
    ("medium", "small-chords-moving"): lambda r: r["fastest"] >= 0.5 and r["chord_share"] >= 0.6 and 2 <= r["chord_mean"] <= 3 and 2 <= r["moves"] <= 4,
    ("medium", "melody-with-accidentals"): lambda r: r["fastest"] >= 0.5 and 0.15 <= r["altered"] <= 0.3 and r["moves"] <= 3 and r["chord_share"] < 0.3,
    ("medium", "thirds-sixths-corcheas"): lambda r: r["fastest"] == 0.5 and r["chord_share"] >= 0.8 and r["chord_mean"] <= 2.2 and r["pattern"] >= 0.5,
    ("medium", "melody-with-ornament"): lambda r: (r["ornaments"] + r["graces"]) >= 1 and r["fastest"] >= 0.5 and r["moves"] <= 3,
    ("hard", "chord-run"): lambda r: r["chord_run"] >= 4 and r["chord_mean"] >= 2.5,
    ("hard", "fast-no-pattern"): lambda r: r["fastest"] <= 0.25 and r["pattern"] < 0.25 and r["moves"] >= 5 and r["chord_share"] < 0.3,
    ("hard", "fast-chromatic"): lambda r: r["fastest"] <= 0.25 and r["altered"] >= 0.3 and r["chord_share"] < 0.3,
    ("hard", "fast-ornamented"): lambda r: r["fastest"] <= 0.25 and (r["ornaments"] >= 2 or r["graces"] >= 3),
    ("hard", "fast-double-notes"): lambda r: r["fastest"] <= 0.25 and r["chord_share"] >= 0.7 and r["chord_mean"] <= 2.3 and r["moves"] >= 3,
    ("super hard", "fast-chords-moving"): lambda r: r["fastest"] <= 0.25 and r["chord_share"] >= 0.7 and r["chord_mean"] >= 2.5 and r["moves"] >= 6,
    ("super hard", "very-fast-wide"): lambda r: r["fastest"] <= 0.167 and r["span"] >= 24 and r["moves"] >= 8,
    ("super hard", "jumps"): lambda r: r["jumps"] >= 3,
    ("super hard", "doubles-fast"): lambda r: r["doubles"] >= 2 and r["fastest"] <= 0.25,
}

COLLECTION = {
    "Étude": ["010", "025"], "Prelude": ["028", "045"], "Nocturne": ["009", "015", "027", "032", "037", "048", "055", "062", "072"],
    "Waltz": ["018", "034", "042", "064", "069", "070"], "Ballade": ["023", "038", "047", "052"],
    "Scherzo": ["020", "031", "039", "054"], "Polonaise": ["022", "026", "040", "044", "053", "061", "071"],
    "Impromptu": ["029", "036", "051", "066"], "Sonata": ["004", "035", "058"], "Barcarolle": ["060"],
    "Berceuse": ["057"], "Fantaisie": ["049"], "Concerto": ["011", "021"], "Rondo": ["001", "005", "016"],
    "Variations": ["002", "012"], "Fantasy on Polish airs": ["013"], "Krakowiak": ["014"], "Bolero": ["019"],
    "Tarantelle": ["043"], "Allegro de concert": ["046"],
    "Mazurka": ["006", "007", "017", "024", "030", "033", "041", "050", "056", "059", "063", "067", "068"],
}
BALLADE = {"023": 1, "038": 2, "047": 3, "052": 4}
SCHERZO = {"020": 1, "031": 2, "039": 3, "054": 4}


POSTHUMOUS = {"VGN": "Variations on a German air (posthumous)", "MEG": "Contredanse (posthumous)",
              "Pol": "Polonaise (posthumous)", "Wal": "Waltz in E minor (posthumous)"}


def piece(file: str) -> str:
    opus = file[:3]
    if not opus.isdigit():
        return POSTHUMOUS.get(opus, file.split("-")[0])
    num = re.search(r"-(\d{3})(?:-|\.krn)", file)
    sub = re.match(r"^\d+_(\d+)", file)
    n = int(num.group(1)) if num else (int(sub.group(1)) if sub else None)
    name = next((c for c, ops in COLLECTION.items() if opus in ops), "Op.")
    if opus in BALLADE:
        return f"Ballade No. {BALLADE[opus]}, Op. {int(opus)}"
    if opus in SCHERZO:
        return f"Scherzo No. {SCHERZO[opus]}, Op. {int(opus)}"
    if name == "Sonata" and n:
        return f"Sonata Op. {int(opus)}, movement {n}"
    if name == "Concerto" and n:
        return f"Concerto Op. {int(opus)}, movement {n} (piano)"
    return f"{name} Op. {int(opus)}" + (f" No. {n}" if n else "")


def main() -> None:
    rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
    rows = [r for r in rows if "error" not in r]
    rng = random.Random(4)
    used: set[str] = set()  # one candidate per opus, so that the candidates spread over the works
    picks = []
    for (level, kind), rule in KINDS.items():
        cands = [r for r in rows if rule(r)]
        rng.shuffle(cands)
        got = 0
        for r in cands:
            if r["file"][:3] in used:
                continue
            used.add(r["file"][:3])
            picks.append({"level": level, "kind": kind, "count": len(cands), "piece": piece(r["file"]), **r})
            got += 1
            if got == 2:
                break
    (HERE / "rh_candidates.json").write_text(json.dumps(picks, indent=1, ensure_ascii=False) + "\n")
    data = {}
    for i, p in enumerate(picks):
        name = f"rh-{i:02d}-{p['kind']}"
        data[name] = passage(p["file"], p["bars"])
    run = RUN.replace("__DATA__", repr(json.dumps(data))).replace("__Q__", repr(QUARTER_MS))
    (HERE / "rh_run.py").write_text(run.replace("/home/app/04-3-phase-2/transcribed", "/home/app/04-3-phase-2/rh"))
    for p in picks:
        print(f"{p['level']:10} {p['kind']:24} {p['count']:5}  {p['piece']:40} {p['bars']}")


if __name__ == "__main__":
    main()
