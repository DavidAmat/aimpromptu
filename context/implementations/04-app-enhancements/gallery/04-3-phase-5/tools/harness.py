"""Phase 5 (implementation 04-3): one case of the comparison run by one model, in memory, through write_level.

A case: a song (part id), a passage (span), a level (or one per hand), the patterns selected (none: the level's
defaults, as the app), the words. Results in /home/app/04-3-phase-5/runs/<case>/<model>/: calls.json (every request:
the last message, the reply, the Call) and result.json (plan, batches, answers drawn by the app, measures, cost, time).
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

from aitu_backend.part_sheet import build
from aitu_backend.sheet.sheet import f1
from aitu_backend.sheet.levels.grid import song_grid
from aitu_backend.sheet.levels.hands import measure
from aitu_backend.sheet.llm import levels as L
from aitu_backend.sheet_llm import ClaudeComplete, OpenAIComplete

ROOT = Path("/home/app/04-3-phase-5")

MODELS = {
    "sonnet": ("Sonnet 5.5", lambda key, on_call: ClaudeComplete(on_call=on_call)),
    "luna": ("GPT-6 Luna", lambda key, on_call: OpenAIComplete(model="gpt-6-luna", cache_key=key, on_call=on_call)),
    "terra": ("GPT-6.1 Terra", lambda key, on_call: OpenAIComplete(model="gpt-6.1-terra", cache_key=key, on_call=on_call)),
    "sol": ("GPT-6.1 Sol", lambda key, on_call: OpenAIComplete(model="gpt-6.1-sol", cache_key=key, on_call=on_call)),
}
# the user, 2026-10-30: measure a lower effort too
for _m, (_name, _id) in {"luna": ("GPT-6 Luna", "gpt-6-luna"), "terra": ("GPT-6.1 Terra", "gpt-6.1-terra"),
                         "sol": ("GPT-6.1 Sol", "gpt-6.1-sol")}.items():
    for _e in ("medium", "high"):
        MODELS[f"{_m}-{_e}"] = (f"{_name} ({_e})", lambda key, on_call, _id=_id, _e=_e: OpenAIComplete(
            model=_id, effort=_e, cache_key=key, on_call=on_call))

SONGS = {
    "99rb": ("c0e39afe-3122-47fb-aada-54952b014783", "99 Red Balloons"),
    "7years": ("477086a0-b8ac-492f-aeca-2a56805868af", "7 Years"),
    "halleluyah": ("f198e0d5-ceb5-478f-9396-a14aa9ec5e7c", "Halleluyah (Pinchivi)"),
}

_sheets: dict = {}


def song(key: str):
    if key not in _sheets:
        s = f1.read(build.current(SONGS[key][0]).text)
        _sheets[key] = (s, song_grid(s))
    return _sheets[key]


def run(case: dict, model: str, out_root: Path = ROOT / "runs", force: bool = False) -> dict:
    out = out_root / case["id"] / model
    if (out / "result.json").exists() and not force:
        return json.loads((out / "result.json").read_text())
    out.mkdir(parents=True, exist_ok=True)
    s, g = song(case["song"])
    staffs = tuple(case.get("staffs", (1, 2)))
    refs = L.run_refs(case["level"], staffs, list(case.get("patterns", [])), case.get("words", ""))
    log: list[dict] = []

    def on_call(call, messages, text):
        log.append({"call": asdict(call), "turn": len(messages), "prompt": messages[-1]["content"], "reply": text})
        (out / "calls.json").write_text(json.dumps(log, indent=1))
        print(f"  [{case['id']}|{model}] call {len(log)}: in {call.input_tokens} cw {call.cache_write_tokens} "
              f"cr {call.cache_read_tokens} out {call.output_tokens} (r {call.reasoning_tokens}) {call.seconds}s "
              f"${call.usd:.4f} {call.stop_reason}", flush=True)

    complete = MODELS[model][1](f"{case['id']}|{model}", on_call)
    marks: list[int] = []
    t0 = time.time()
    span = tuple(case["span"])
    lr = L.write_level(s, complete, g, level=case["level"], staffs=staffs, patterns=[L.catalog()[r] for r in refs],
                       sid=SONGS[case["song"]][1], words=case.get("words", ""), span=span,
                       on_plan=lambda wl: marks.append(len(log)), on_batch=lambda wl, b: marks.append(len(log)))
    seconds = time.time() - t0
    calls = [c["call"] for c in log]
    plan_calls = calls[: marks[0]] if marks else calls
    batches = []
    for k, (wl, b) in enumerate(lr.batches):
        lo = marks[k] if k < len(marks) else len(calls)
        hi = marks[k + 1] if k + 1 < len(marks) else len(calls)
        mine = calls[lo:hi]
        entry = {"start": wl.start, "end": wl.end, "status": wl.status, "replies": wl.replies, "errors": wl.errors,
                 "note": getattr(wl, "note", None), "usd": sum(c["usd"] for c in mine),
                 "seconds": sum(c["seconds"] for c in mine), "calls": mine,
                 "declared": b.declared.lines(), "measures": {str(st): m.row() for st, m in b.measures.items()},
                 "melody": b.melody, "melody_dropped": b.melody_dropped, "new_notes": b.new_notes}
        if b.sheet is not None:
            entry["answer"] = f1.write(b.sheet, mode="frames")
            entry["drawn"] = f1.write(L.drawn(b.sheet, s.quarter_ms, key=s.key or 0), mode="frames")
        batches.append(entry)
    # the last answer of a failed batch, so the judge sees what the model wrote
    for e in batches:
        if "answer" not in e:
            replies = [c["reply"] for c in log if c["prompt"] and str(e["start"]) in c["prompt"][:4000]]
            e["last_reply"] = replies[-1] if replies else None
    res = {
        "case": case, "model": model, "model_name": MODELS[model][0], "refs": refs,
        "plan": [sec.line() for sec in lr.plan], "plan_status": lr.plan_log.status, "plan_replies": lr.plan_log.replies,
        "plan_errors": lr.plan_log.errors, "plan_note": getattr(lr.plan_log, "note", None),
        "plan_usd": sum(c["usd"] for c in plan_calls), "plan_seconds": sum(c["seconds"] for c in plan_calls),
        "batches": batches, "usd": complete.usd, "seconds": round(seconds, 1), "calls": len(calls),
        "tokens": {k: sum(c[k] for c in calls) for k in
                   ("input_tokens", "cache_write_tokens", "cache_read_tokens", "output_tokens", "reasoning_tokens")},
    }
    (out / "result.json").write_text(json.dumps(res, indent=1))
    print(f"[{case['id']}|{model}] plan {lr.plan_log.status} batches "
          f"{[(e['status'], e['replies']) for e in batches]} ${complete.usd:.3f} {seconds:.0f}s", flush=True)
    return res


def original(case: dict) -> dict:
    """The passage now: its F1 frames text and the measures of each hand."""
    s, g = song(case["song"])
    a, b = case["span"]
    from dataclasses import replace
    part = replace(s, notes=[n for n in s.notes if a <= n.frame < b])
    return {"text": f1.write(part, mode="frames"),
            "measures": {str(st): measure(s, st, a, b, g).row() for st in (1, 2)}}


if __name__ == "__main__":
    cases = {c["id"]: c for c in json.loads((ROOT / "cases.json").read_text())}
    run(cases[sys.argv[1]], sys.argv[2], force="--force" in sys.argv)
