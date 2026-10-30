"""The blind view of a case for the judge: PNG of the sheet, and the measures and declared lines by letter only."""
import json, subprocess, sys
from pathlib import Path
root = Path(__file__).parent
drawn = json.loads((root / "drawn.json").read_text())
for cid in sys.argv[1:]:
    d = drawn[cid]
    page = (root / "judge" / f"{cid}.html").read_text()
    head, body = page.split("<body", 1)
    tag, rest = body.split(">", 1)
    blocks = rest.replace("</body></html>", "").split("<div style='margin-bottom:6px'>")[1:]
    groups = [blocks[:3], blocks[3:]] if len(blocks) > 3 else [blocks]
    pngs = []
    for k, g in enumerate(groups, 1):
        part = root / "judge" / f"{cid}.{k}.html"
        part.write_text(head + "<body" + tag + ">" + "".join("<div style='margin-bottom:6px'>" + b for b in g) + "</body></html>")
        png = root / "judge" / "png" / f"{cid}.{k}.png"
        subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                        "--force-device-scale-factor=1.5", f"--window-size=1400,{len(g) * 1100 + 60}", f"--screenshot={png}",
                        f"file://{part}"], capture_output=True)
        subprocess.run(["docker", "exec", "aimpromptu-backend-1", "python", "/home/app/04-3-phase-5/crop.py",
                        f"/home/app/04-3-phase-5/judge/png/{cid}.{k}.png"])
        pngs.append(str(png))
    png = " ".join(pngs)
    print(f"== {cid}  ({png})")
    def row(ms):
        r, l = ms["1"], ms["2"]
        return (f"L moves/negra {l['moves_q']:.2f} chord {l['chord_max']} span {l['span']} reach {l['reach']} "
                f"notes/s {l['notes_s']:.1f} | R moves/negra {r['moves_q']:.2f} chord {r['chord_max']} notes/s {r['notes_s']:.1f}")
    print("  now:", row(d["now"]))
    for m, letter in sorted(d["letters"].items(), key=lambda x: x[1]):
        res = json.loads((root / "runs" / cid / m / "result.json").read_text())
        print(f"  {letter}:", row(d["answers"][m]["measures"]), "|", [(b["status"], b["replies"]) for b in res["batches"]])
        for b in res["batches"]:
            for line in b.get("declared") or []:
                print("      ", line[:150])
