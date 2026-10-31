"""One level run on a page (implementation 04-5): the request, the plan, the rules, and each batch drawn before and
after the run, with the AI's explanation and the check's refusals, from the run's log (``part_sheet.runs``).

"Before" is the sheet of now with the hand of the batch put back as the batch's target (the notes the AI read);
"after" is the sheet of now. Nothing is written but the page. In the backend container::

    docker exec aimpromptu-backend-1 python scripts/level_run_page.py --part <uuid> --run <id> \\
        --out ../context/implementations/04-app-enhancements/gallery/04-5/<name>.html [--title "..."]
"""

from __future__ import annotations

import argparse
import html
from dataclasses import replace
from pathlib import Path

from aitu_backend.part_sheet import build, runs
from aitu_backend.sheet.engrave import frames as engine
from aitu_backend.sheet.sheet import f1

from simplicity_gallery import banded

STAFF = {"right": (1,), "left": (2,), "both": (1, 2)}

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{ color-scheme: only light; --ink: #1d1d1f; --soft: #5f6368; --line: #e3e3e6; }}
body {{ margin: 0; background: #fff; color: var(--ink); font: 15px/1.5 system-ui, sans-serif; }}
main {{ max-width: 1440px; margin: 0 auto; padding: 24px 16px 80px; }}
h1 {{ font-size: 24px; margin: 0 0 8px; }} h2 {{ font-size: 18px; margin: 32px 0 6px; }}
.soft {{ color: var(--soft); font-size: 13px; }} pre {{ background: #f6f6f8; padding: 8px; white-space: pre-wrap; }}
figure {{ margin: 8px 0 12px; }} figcaption {{ font-size: 13px; color: var(--soft); margin-bottom: 4px; }}
.svg svg {{ width: 100%; height: auto; }} .explain {{ background: #eef6ff; padding: 6px 10px; border-radius: 6px; }}
.refused {{ color: #a50e0e; font-size: 13px; }}
</style></head><body><main>
{body}
</main></body></html>
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="A level run")
    args = ap.parse_args()
    run = runs.load(args.part, args.run)
    if run is None:
        raise SystemExit("no such run")
    now = f1.read(build.current(args.part).text)
    req = run["request"]
    staffs = STAFF[req["hand"]]
    opts = engine.Options(width=110)
    out = [f"<h1>{html.escape(args.title)}</h1>"]
    out.append(
        '<p class="soft">'
        + html.escape(
            f"level {req['level']}, {req['hand']} hand, patterns {', '.join(req['patterns'])}; Strict "
            f"{', '.join(req['strict']) or 'none'}; model {req['model']}; state {run['state']}; "
            f"${run['usd']:.3f}, {run['requests']} requests"
        )
        + "</p>"
    )
    if req["words"]:
        out.append(f"<p><b>The user's words:</b> {html.escape(req['words'])}</p>")
    plan = run.get("plan")
    if plan and plan["messages"]:
        out.append("<h2>The plan</h2><pre>" + html.escape(plan["messages"][-1]["content"]) + "</pre>")
    if run["rules"]:
        out.append(
            "<h2>The rules</h2><ul>"
            + "".join(
                f"<li>{html.escape((r['ref'] + ' ') if r['ref'] else '')}({html.escape(r['source'])}): "
                f"{html.escape(r['text'])}</li>"
                for r in run["rules"]
            )
            + "</ul>"
        )
    for b in run["batches"]:
        a, e = b["start"], b["end"]
        out.append(f"<h2>Batch {b['k'] + 1}: f{a}-f{e} ({b['status']})</h2>")
        for x in b["explain"]:
            out.append(f'<p class="explain">{html.escape(x)}</p>')
        for x in b["rules"]:
            out.append(f"<p><b>Rule added:</b> {html.escape(x)}</p>")
        for k, errs in enumerate(b["errors"], start=1):
            out.append(f'<p class="refused">Refused reply {k}: {html.escape(" | ".join(errs))}</p>')
        if b["target"]:
            target = f1.read(b["target"])
            kept = [n for n in now.notes if not (n.staff in staffs and a <= n.frame < e)]
            before = replace(now, notes=kept + [n for n in target.notes if n.staff in staffs]).sort()
            for cap, sheet in (("Before the run", before), ("After the run (the sheet now)", now)):
                svg = banded(engine.render_frames(sheet, opts, segment=(a, e)), a, e)
                out.append(f'<figure><figcaption>{cap}</figcaption><div class="svg">{svg}</div></figure>')
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(PAGE.format(title=html.escape(args.title), body="\n".join(out)), encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
