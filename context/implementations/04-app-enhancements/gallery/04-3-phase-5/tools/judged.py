"""Add the agent's judgments of a case to judgments.json: python judged.py '<json>'"""
import json, sys
from pathlib import Path
f = Path(__file__).parent / "judgments.json"
j = json.loads(f.read_text()) if f.exists() else {}
new = json.loads(sys.argv[1])
for cid, v in new.items():
    if cid.startswith("_"):
        j[cid] = v
        continue
    j.setdefault(cid, {}).setdefault("scores", {}).update(
        {k: dict(zip(["melody", "level", "pattern", "playable", "musical", "overall", "reasons"], s)) for k, s in v.get("scores", {}).items()})
    if "note" in v:
        j[cid]["note"] = v["note"]
f.write_text(json.dumps(j, indent=1))
print({k: {l: (s["overall"] if isinstance(s["overall"], int) else "BAD") for l, s in v.get("scores", {}).items()} for k, v in j.items() if not k.startswith("_")})
