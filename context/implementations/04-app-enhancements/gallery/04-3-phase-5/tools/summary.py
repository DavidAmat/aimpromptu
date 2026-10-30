import json, sys
sys.path.insert(0, '/home/app/04-3-phase-5')
from report import model_rows, mean, MAIN, EXTRA, NAMES, ROOT
judg = json.loads((ROOT / "judgments.json").read_text()); drawn = json.loads((ROOT / "drawn.json").read_text())
rows = model_rows(judg, drawn)
for m in MAIN + EXTRA:
    d = rows.get(m)
    if not d: continue
    ok = mean([1.0 if x else 0.0 for x in d["ok"]])
    print(f"{m:13} cases {d['cases']:2} ok {ok:.0%} ({sum(d['ok'])}/{len(d['ok'])}) replies {mean(d['replies']):.2f} usd/passage {mean(d['usd']):.3f} min/passage {mean(d['sec'])/60:.1f} usd/song {d['song_usd']:.2f} min/song {d['song_min']:.0f} out/req {mean(d['out']):.0f} total ${sum(d['usd']):.2f}")
