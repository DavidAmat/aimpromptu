"""Phase 5: the drawings, the blind sheets for the judge (the agent), and the HTML report.

python report.py draw     -> svg/ (the passage now and every answer, drawn by the app's engine) and judge/<case>.html
python report.py page     -> the report, gallery/04-3-phase-5/index.html (reads judgments.json when it exists)
"""
from __future__ import annotations

import html
import json
import random
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, "/home/app/04-3-phase-5")
from harness import MODELS, ROOT, SONGS, song  # noqa: E402
from aitu_backend.sheet.engrave import frames as engine  # noqa: E402
from aitu_backend.sheet.llm import levels as L  # noqa: E402
from aitu_backend.sheet.levels.hands import measure  # noqa: E402
from aitu_backend.sheet.sheet import f1  # noqa: E402

RUNS = ROOT / "runs"
GALLERY = Path("/work/aimpromptu/context/implementations/04-app-enhancements/gallery/04-3-phase-5")
MAIN = ["sonnet", "luna-medium", "terra-medium", "sol-medium"]
EXTRA = ["luna", "terra", "sol"]  # max effort, on the riff at medium only
NAMES = {"sonnet": "Sonnet 5.5 (high)", "luna-medium": "GPT-6 Luna (medium)", "terra-medium": "GPT-6.1 Terra (medium)",
         "sol-medium": "GPT-6.1 Sol (medium)", "luna": "GPT-6 Luna (max)", "terra": "GPT-6.1 Terra (max)",
         "sol": "GPT-6.1 Sol (max)"}
SONG_S = 195.0          # 99 Red Balloons, 3:15
SONG_BATCHES = 13
SONNET_SONG = (2.25, 2.70, 25, 30)  # measured: USD, minutes (Phase 4)


def cases() -> list[dict]:
    return [c for c in json.loads((ROOT / "cases.json").read_text()) if c["kind"] != "cache"]


def result(case: str, model: str) -> dict | None:
    f = RUNS / case / model / "result.json"
    return json.loads(f.read_text()) if f.exists() else None


def passage(c: dict):
    s, g = song(c["song"])
    a, b = c["span"]
    return s, g, replace(s, notes=[n for n in s.notes if a <= n.frame < b])


def answer_sheet(c: dict, res: dict):
    """The passage as the model left it: its accepted answers drawn by the app; a failed batch keeps the notes now."""
    s, g, now = passage(c)
    notes, failed = [], []
    for b in res["batches"]:
        if b.get("answer") and b["status"] == "ok":
            notes += f1.read(b["answer"]).notes
        else:
            failed.append((b["start"], b["end"]))
    sheet = replace(s, notes=notes)
    drawn = L.drawn(sheet, s.quarter_ms, key=s.key or 0) if notes else replace(s, notes=[])
    kept = [n for n in now.notes if any(a <= n.frame < e for a, e in failed)]
    return replace(drawn, notes=sorted(drawn.notes + kept, key=lambda n: (n.frame, n.staff, n.midi))), failed


def svg_of(sheet) -> str:
    return engine.render_frames(sheet, engine.Options(width=130), note_ids=False).svg


def measures(c: dict, sheet) -> dict:
    s, g, _ = passage(c)
    a, b = c["span"]
    return {st: measure(sheet, st, a, b, g).row() for st in (1, 2)}


def draw() -> None:
    (GALLERY / "svg").mkdir(parents=True, exist_ok=True)
    (ROOT / "judge").mkdir(exist_ok=True)
    data = {}
    for c in cases():
        cid = c["id"]
        _, _, now = passage(c)
        (GALLERY / "svg" / f"{cid}.now.svg").write_text(svg_of(now))
        entry = {"now": measures(c, now), "answers": {}}
        for m in MAIN + EXTRA:
            res = result(cid, m)
            if not res:
                continue
            sheet, failed = answer_sheet(c, res)
            (GALLERY / "svg" / f"{cid}.{m}.svg").write_text(svg_of(sheet))
            entry["answers"][m] = {"measures": measures(c, sheet), "failed": failed}
        data[cid] = entry
        # the blind sheet: letters in a shuffled order, no model names
        models = [m for m in MAIN if m in entry["answers"]]
        rng = random.Random("judge|" + cid)
        rng.shuffle(models)
        letters = {m: "ABCD"[i] for i, m in enumerate(models)}
        entry["letters"] = letters
        blocks = [f"<h2>Now (f{c['span'][0]}-f{c['span'][1]})</h2>" + (GALLERY / "svg" / f"{cid}.now.svg").read_text()]
        for m in models:
            res = result(cid, m)
            st = ", ".join(f"{b['status']} ({b['replies']} replies)" for b in res["batches"])
            blocks.append(f"<h2>Answer {letters[m]}: {st}</h2>" + (GALLERY / "svg" / f"{cid}.{m}.svg").read_text())
        (ROOT / "judge" / f"{cid}.html").write_text(
            "<!DOCTYPE html><html><body style='margin:8px;background:#fff;font:16px sans-serif'>"
            + "".join(f"<div style='margin-bottom:6px'>{b}</div>" for b in blocks) + "</body></html>")
    (ROOT / "drawn.json").write_text(json.dumps(data, indent=1))
    print("drawn", len(data), "cases")


if __name__ == "__main__" and sys.argv[1] == "draw":
    draw()


# ---------------------------------------------------------------- the page

def esc(x) -> str:
    return html.escape(str(x))


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def fmt(x, nd=2, pre="", post=""):
    return "-" if x is None else f"{pre}{x:.{nd}f}{post}"


def prompts(c: dict) -> dict:
    """The prompt files of a case: the system prompt (the same for every model) and Sonnet's first batch prompt."""
    (GALLERY / "prompts").mkdir(exist_ok=True)
    cid = c["id"]
    res = result(cid, "sonnet") or result(cid, "terra-medium")
    refs = res["refs"]
    (GALLERY / "prompts" / f"{cid}.system.md").write_text(L.system_prompt(c["level"], [L.catalog()[r] for r in refs]))
    calls = json.loads((RUNS / cid / res["model"] / "calls.json").read_text())
    n_plan = res.get("plan_replies") or 1
    (GALLERY / "prompts" / f"{cid}.plan.md").write_text(calls[0]["prompt"])
    if len(calls) > n_plan:
        (GALLERY / "prompts" / f"{cid}.batch.md").write_text(calls[n_plan]["prompt"])
    return {"refs": refs}


def model_rows(judg: dict, drawn: dict) -> dict:
    rows = {}
    for m in MAIN + EXTRA:
        d = {"cases": 0, "usd": [], "sec": [], "passage_s": 0.0, "batch_usd": 0.0, "batch_sec": 0.0, "plan_usd": [],
             "plan_sec": [], "ok": [], "replies": [], "scores": {}, "out": []}
        for c in cases():
            res = result(c["id"], m)
            if not res:
                continue
            d["cases"] += 1
            d["usd"].append(res["usd"])
            d["sec"].append(res["seconds"])
            d["plan_usd"].append(res["plan_usd"])
            d["plan_sec"].append(res["plan_seconds"])
            d["passage_s"] += (c["span"][1] - c["span"][0]) * 0.04
            for b in res["batches"]:
                d["batch_usd"] += b["usd"]
                d["batch_sec"] += b["seconds"]
                d["ok"].append(b["status"] == "ok")
                d["replies"].append(b["replies"])
                d["out"] += [x["output_tokens"] for x in b["calls"]]
            letter = drawn.get(c["id"], {}).get("letters", {}).get(m)
            sc = judg.get(c["id"], {}).get("scores", {}).get(letter) if letter else None
            if sc:
                d["scores"][c["id"]] = sc
        if d["cases"]:
            d["song_usd"] = mean(d["plan_usd"]) + d["batch_usd"] / d["passage_s"] * SONG_S
            d["song_min"] = (mean(d["plan_sec"]) + d["batch_sec"] / d["passage_s"] * SONG_S) / 60
            rows[m] = d
    return rows


CSS = """
:root { --ink:#1d1d1f; --soft:#6e6e73; --line:#d2d2d7; --acc:#0b57d0; }
body { margin:0; font:15px/1.5 system-ui, sans-serif; color:var(--ink); background:#fff; }
main { padding:20px 28px 60px; max-width:1500px; }
h1 { font-size:24px; margin:0 0 6px; } h2 { font-size:20px; margin:32px 0 6px; } h3 { font-size:16px; margin:22px 0 4px; }
p { max-width:980px; } .soft { color:var(--soft); }
.tabs { display:flex; gap:6px; margin:18px 0 8px; border-bottom:1px solid var(--line); }
.tabs button { font:inherit; padding:8px 16px; border:1px solid var(--line); border-bottom:none; background:#f5f5f7; border-radius:8px 8px 0 0; cursor:pointer; }
.tabs button.on { background:#fff; font-weight:600; position:relative; top:1px; }
.pills { display:flex; flex-wrap:wrap; gap:6px; margin:12px 0; }
.pills button { font:inherit; font-size:13px; padding:4px 12px; border:1px solid var(--line); border-radius:16px; background:#fff; cursor:pointer; }
.pills button.on { background:var(--ink); color:#fff; border-color:var(--ink); }
table { border-collapse:collapse; font-size:14px; margin:8px 0 14px; }
th, td { border:1px solid var(--line); padding:5px 9px; text-align:right; vertical-align:top; }
th { background:#f5f5f7; } td.l, th.l { text-align:left; }
tr.base td { background:#fafaf0; }
.card { border:1px solid var(--line); border-radius:8px; padding:10px 14px; margin:10px 0 18px; }
.card h3 { margin:0 0 4px; } .meta { font-size:13px; color:var(--soft); }
.svg { overflow-x:auto; background:#fff; } .svg img { display:block; max-width:none; height:auto; }
.ask { background:#f5f5f7; border-radius:8px; padding:10px 14px; max-width:980px; }
.score { font-weight:600; } .bad { color:#b3261e; } details { font-size:13px; } pre { white-space:pre-wrap; font-size:12px; }
.panel { display:none; } .panel.on { display:block; }
"""

JS = """
function tab(id){document.querySelectorAll('.tabs button').forEach(b=>b.classList.toggle('on',b.dataset.t===id));
 document.querySelectorAll('.tab').forEach(t=>t.style.display=t.id===id?'block':'none');}
function pick(id){document.querySelectorAll('.pills button').forEach(b=>b.classList.toggle('on',b.dataset.c===id));
 document.querySelectorAll('.panel').forEach(p=>p.classList.toggle('on',p.id===id)); location.hash=id;}
window.onload=()=>{tab('cmp'); const h=location.hash.slice(1); if(h&&document.getElementById(h)){tab('ex');pick(h);} else pick(document.querySelector('.panel').id);};
"""

LEVEL_WORDS = {"easy": "Easy", "medium": "Medium", "hard": "Hard"}


def ask_text(c: dict, refs: list[str]) -> str:
    lv = c["level"]
    if isinstance(lv, dict):
        level = f"Right hand {lv['right']}, left hand {lv['left']}"
    else:
        level = f"{LEVEL_WORDS[lv]} for both hands"
    pats = (f"Patterns selected in the catalog: {', '.join(c['patterns'])}" if c.get("patterns")
            else f"No pattern selected, so the level's patterns are used: {', '.join(refs)}")
    return (f"<div class='ask'><b>Enhance with AI</b>: a stretch, frames {c['span'][0]} to {c['span'][1]} "
            f"({(c['span'][1]-c['span'][0])*0.04:.0f} s), both hands. <b>A level</b>: {esc(level)}. {esc(pats)}. No words."
            f"<br><span class='soft'>The full prompts: <a href='prompts/{c['id']}.system.md'>the instructions (system prompt)</a>"
            f" · <a href='prompts/{c['id']}.plan.md'>the plan request</a> · <a href='prompts/{c['id']}.batch.md'>the first batch"
            f" (Sonnet's; each model's batch carries its own plan)</a></span></div>")


def mrow(ms: dict) -> str:
    r, l = ms.get("1", ms.get(1, {})), ms.get("2", ms.get(2, {}))
    return (f"L: moves per negra {l.get('moves_q', 0):.2f}, widest chord {l.get('chord_max', 0)} notes, span {l.get('span', 0)}, "
            f"range in two negras {l.get('reach', 0)}, {l.get('notes_s', 0):.1f} notes/s · R: moves per negra "
            f"{r.get('moves_q', 0):.2f}, widest chord {r.get('chord_max', 0)} notes, {r.get('notes_s', 0):.1f} notes/s")


def page() -> None:
    judg = json.loads((ROOT / "judgments.json").read_text()) if (ROOT / "judgments.json").exists() else {}
    drawn = json.loads((ROOT / "drawn.json").read_text())
    rows = model_rows(judg, drawn)
    keys = ["melody", "level", "pattern", "playable", "musical", "overall"]
    out = [f"<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'><title>04-3 Phase 5: AI models for the levels</title>"
           f"<style>{CSS}</style><script>{JS}</script></head><body><main>",
           "<h1>The level runs with other AI models: Sonnet 5.5 against OpenAI's GPT-6 Luna, GPT-6.1 Terra and GPT-6.1 Sol</h1>",
           f"<p class='soft'>Implementation 04-3, Phase 5, 2026-10-30. Every run is in memory (no sheet of the app changed). "
           f"{len(cases())} cases: 4 passages × (easy, medium, hard right with medium left, one forced pattern). The judge is "
           f"the agent of the phase (Opus 5.5), who read every answer drawn by the app without the model's name.</p>",
           "<div class='tabs'><button data-t='cmp' onclick=\"tab('cmp')\">Cost, quality and time</button>"
           "<button data-t='ex' onclick=\"tab('ex')\">The examples</button></div>"]
    # ---- comparison tab
    out.append("<section class='tab' id='cmp'>")
    if judg.get("_verdict"):
        out.append(f"<h2>The verdict</h2>{judg['_verdict']}")
    out.append("<h2>The summary, one row per model</h2><p class='soft'>Quality: my overall score from 0 to 10 (mean over the cases; "
               "an answer the app's check refused counts as what the user gets, the sheet as it was). Cost and time per passage: "
               "mean of the cases (the plan request and the batches, with all replies). Per song: 99 Red Balloons (3:15, 13 "
               "batches one after the other), from each model's cost and time per second of music; Sonnet's measured whole song "
               f"(Phase 4) is ${SONNET_SONG[0]:.2f} to ${SONNET_SONG[1]:.2f} and {SONNET_SONG[2]} to {SONNET_SONG[3]} minutes.</p>")
    out.append("<table><tr><th class='l'>Model (effort)</th><th>Quality</th><th>Level cases</th><th>Forced pattern</th>"
               "<th>Batches accepted</th><th>Replies per batch</th><th>Cost per passage</th><th>Time per passage</th>"
               "<th>Cost per song</th><th>Time per song</th><th>Failed batches per song</th><th>Output tokens per request</th></tr>")
    for m in MAIN:
        d = rows.get(m)
        if not d:
            continue
        sc = d["scores"]
        lv = mean([v["overall"] for k, v in sc.items() if not k.split(".")[1].startswith("forced")])
        fo = mean([v["overall"] for k, v in sc.items() if k.split(".")[1].startswith("forced")])
        ok = mean([1.0 if x else 0.0 for x in d["ok"]])
        out.append(f"<tr class='{'base' if m == 'sonnet' else ''}'><td class='l'>{esc(NAMES[m])}</td>"
                   f"<td class='score'>{fmt(mean([v['overall'] for v in sc.values()]), 1)}</td><td>{fmt(lv, 1)}</td><td>{fmt(fo, 1)}</td>"
                   f"<td>{ok:.0%} ({sum(d['ok'])} of {len(d['ok'])})</td><td>{fmt(mean(d['replies']), 2)}</td>"
                   f"<td>${mean(d['usd']):.3f}</td><td>{mean(d['sec'])/60:.1f} min</td><td>${d['song_usd']:.2f}</td>"
                   f"<td>{d['song_min']:.0f} min</td><td>{(1-ok)*SONG_BATCHES:.1f}</td><td>{mean(d['out']):,.0f}</td></tr>")
    out.append("</table>")
    out.append("<h3>The scores by criterion (mean of the cases)</h3><table><tr><th class='l'>Model</th>"
               + "".join(f"<th>{k}</th>" for k in keys) + "</tr>")
    for m in MAIN:
        d = rows.get(m)
        if d:
            out.append(f"<tr><td class='l'>{esc(NAMES[m])}</td>" + "".join(
                f"<td>{fmt(mean([v[k] for v in d['scores'].values()]), 1)}</td>" for k in keys) + "</tr>")
    out.append("</table>")
    out.append("<h3>Medium against max effort (the riff of 99 Red Balloons at medium, the only case run at max)</h3><table>"
               "<tr><th class='l'>Model</th><th>Effort</th><th>Cost</th><th>Time</th><th>Replies</th><th>Output tokens per request</th></tr>")
    for base in ["luna", "terra", "sol"]:
        for m in [f"{base}-medium", base]:
            res = result("99rb-riff.medium", m)
            if res:
                outs = [x["output_tokens"] for b in res["batches"] for x in b["calls"]]
                out.append(f"<tr><td class='l'>{esc(NAMES[m].split(' (')[0])}</td><td>{'max' if m == base else 'medium'}</td>"
                           f"<td>${res['usd']:.3f}</td><td>{res['seconds']/60:.1f} min</td><td>{res['batches'][0]['replies']}</td>"
                           f"<td>{mean(outs):,.0f}</td></tr>")
    out.append("</table>")
    out.append("<h3>The prices (US dollars per million tokens, 2026-10-30)</h3><table><tr><th class='l'>Model</th><th>Input</th>"
               "<th>Cache read</th><th>Cache write</th><th>Output</th></tr>"
               "<tr><td class='l'>Sonnet 5.5</td><td>2.00</td><td>0.20</td><td>2.50</td><td>10.00</td></tr>"
               "<tr><td class='l'>GPT-6 Luna</td><td>0.10</td><td>0.01</td><td>0.125</td><td>0.50</td></tr>"
               "<tr><td class='l'>GPT-6.1 Terra</td><td>1.00</td><td>0.05</td><td>1.25</td><td>5.00</td></tr>"
               "<tr><td class='l'>GPT-6.1 Sol</td><td>2.00</td><td>0.10</td><td>2.50</td><td>10.00</td></tr></table>"
               "<p class='soft'>Sources: OpenAI's pricing and model pages and its prompt caching guide; Anthropic's prices. The "
               "reasoning (thinking) tokens are billed as output.</p></section>")
    # ---- examples tab
    out.append("<section class='tab' id='ex'><p class='soft'>Each case: what the user asks in Enhance with AI, the passage now, "
               "then each model's version, drawn by the app's engine. A batch the app's check refused keeps the notes now (marked). "
               "Scores and reasons are mine.</p><div class='pills'>")
    for c in cases():
        out.append(f"<button data-c='{c['id']}' onclick=\"pick('{c['id']}')\">{esc(c['id'])}</button>")
    out.append("</div>")
    for c in cases():
        cid = c["id"]
        info = prompts(c)
        dj = drawn[cid]
        out.append(f"<div class='panel' id='{cid}'><h2>{esc(SONGS[c['song']][1])}, f{c['span'][0]}-f{c['span'][1]}: {esc(cid.split('.', 1)[1])}</h2>")
        out.append(ask_text(c, info["refs"]))
        if judg.get(cid, {}).get("note"):
            out.append(f"<p>{judg[cid]['note']}</p>")
        out.append(f"<div class='card'><h3>The passage now</h3><div class='meta'>{mrow(dj['now'])}</div>"
                   f"<div class='svg'><img loading='lazy' src='svg/{cid}.now.svg'></div></div>")
        for m in MAIN + (EXTRA if cid == "99rb-riff.medium" else []):
            res = result(cid, m)
            if not res:
                continue
            a = dj["answers"].get(m)
            if a is None:
                continue
            letter = dj["letters"].get(m)
            sc = judg.get(cid, {}).get("scores", {}).get(letter) if letter else None
            st = "; ".join(f"f{b['start']}-f{b['end']}: " + ("<span class='bad'>refused after 3 replies, keeps the notes now</span>"
                           if b["status"] != "ok" else f"accepted at reply {b['replies']}") for b in res["batches"])
            decl = "\n".join(l for b in res["batches"] for l in (b.get("declared") or []))
            plan = "\n".join(res["plan"])
            scores = (f"<div><span class='score'>Score {sc['overall']}/10</span> <span class='soft'>(melody {sc['melody']}, level "
                      f"{sc['level']}, pattern {sc['pattern']}, playable {sc['playable']}, musical {sc['musical']})</span><br>"
                      f"{esc(sc['reasons'])}</div>") if sc else ""
            out.append(f"<div class='card'><h3>{esc(NAMES[m])}</h3><div class='meta'>{st} · ${res['usd']:.3f} · "
                       f"{res['seconds']/60:.1f} min · {res['calls']} requests</div>{scores}<div class='meta'>{mrow(a['measures'])}</div>"
                       f"<div class='svg'><img loading='lazy' src='svg/{cid}.{m}.svg'></div>"
                       f"<details><summary>The plan and the declared lines</summary><pre>{esc(plan)}\n\n{esc(decl)}</pre></details></div>")
        out.append("</div>")
    out.append("</section></main></body></html>")
    (GALLERY / "index.html").write_text("".join(out))
    print("page written", GALLERY / "index.html")


if __name__ == "__main__" and sys.argv[1] == "page":
    page()
