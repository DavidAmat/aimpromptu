"""Run several cases with one model, N at a time: python run_many.py <model> <N> [case ids...] (none: every case)."""
import json, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, '/home/app/04-3-phase-5')
from harness import ROOT, run
model, n = sys.argv[1], int(sys.argv[2])
cases = [c for c in json.loads((ROOT / "cases.json").read_text()) if c["kind"] != "cache"]
if sys.argv[3:]:
    cases = [c for c in cases if c["id"] in sys.argv[3:]]
def one(c):
    try:
        run(c, model)
    except Exception as e:  # noqa: BLE001
        print(f"FAILED {c['id']}|{model}: {type(e).__name__}: {e}", flush=True)
with ThreadPoolExecutor(n) as ex:
    list(ex.map(one, cases))
print("ALL DONE", model, flush=True)
