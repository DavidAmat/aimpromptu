"""Write the new sheet of parts with the LLM step (``aitu_backend.sheet.llm.frames``) and measure it.

Implementation 03, Phase 4. For each part: the starting hands (``pipeline.starting_hands``), the reference request
and the windows with Claude (``aitu_backend.sheet_llm.ClaudeComplete``), the sheet assembled by the rules, checked
(``frames.check``, the round trip with the matrix), and compared with the research's recorded Sonnet sheet of the
same song (same hand, same beam decisions). Every request is logged (prompt, reply, tokens, seconds, US dollars)
in ``<database>/lab/sheet-llm/<run>/`` with the F1 text of each part and ``summary.json``.

    python scripts/llm_sheet.py --test-key                       # three small requests: usage and time
    python scripts/llm_sheet.py 1a16a836 --windows 2             # the reference and two windows of one part
    python scripts/llm_sheet.py --viewer [--run NAME]            # the 10 viewer songs, whole
    python scripts/llm_sheet.py --viewer --replay                # offline: the recorded Sonnet answers each window
    python scripts/llm_sheet.py 1a16a836 --dry                   # print the first prompts, no request

Run on the host with ``.env`` loaded (the key and the database folder): ``set -a; . ../.env; set +a``.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from collections import Counter
from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path
from typing import Any

from aitu_backend.sheet.llm import frames as llm
from aitu_backend.sheet.llm.song import frames_per_quarter
from aitu_backend.sheet.sheet import f1, frames
from aitu_backend.sheet.sheet.data import Sheet
from aitu_backend.storage import bundle, paths
from aitu_backend.transcription.pipeline import starting_hands

VIEWER = "1a16a836 f4c4de9a 43faf78e 2ed0f379 3c8d4cfa 4cb9cb38 b80e6f5a c0edc9b0 92255337 68e277fe".split()
RESEARCH = Path(
    os.environ.get("AITU_RESEARCH_DIR", "/home/david/Documents/projects/music/poc-aitu-research")
)


def recorded(pid: str) -> Sheet | None:
    """The research's Sonnet sheet of a song (phase 13 runs, F1 bars with frame anchors on the matrix cells)."""
    p = RESEARCH / "experiments/E07-pop-songs/runs" / f"sonnet-{pid[:8]}" / "song.f1"
    return f1.read(p.read_text()) if p.exists() else None


def matched(ours: Sheet, rec: Sheet) -> list[tuple[Any, Any]]:
    """Pairs (our note, recorded note): same key, the recorded cell at our drawn column or the next one."""
    pool: dict[tuple[int, int], list] = {}
    for n in rec.notes:
        if n.frame is not None:
            pool.setdefault((n.frame, n.midi), []).append(n)
    out = []
    for n in sorted(ours.notes, key=lambda n: (n.frame, n.midi)):
        for f in (n.frame, n.frame + 1):
            if pool.get((f, n.midi)):
                out.append((n, pool[(f, n.midi)].pop(0)))
                break
    return out


def compare(ours: Sheet, rec: Sheet) -> dict:
    """Same hand as the recorded sheet, and the same beam decision between consecutive short notes of a hand (both
    sheets with the same hands for both notes; graces left out)."""
    pairs = matched(ours, rec)
    same_hand = sum(a.staff == b.staff for a, b in pairs)
    of = {id(a): b for a, b in pairs}
    agree = total = 0
    joins = {"both": 0, "ours": 0, "recorded": 0}
    for staff in (1, 2):
        cols: dict[int, list] = {}
        for n in ours.notes:
            if n.staff == staff and not n.grace and not n.covered:
                cols.setdefault(n.frame, []).append(n)
        seq = [max(ns, key=lambda n: n.midi) for _, ns in sorted(cols.items())]
        for a, b in zip(seq, seq[1:]):
            ra, rb = of.get(id(a)), of.get(id(b))
            if (
                ra is None
                or rb is None
                or ra.staff != staff
                or rb.staff != staff
                or ra.grace
                or rb.grace
            ):
                continue
            if (a.figure or 0) < 8 or (b.figure or 0) < 8:
                continue
            ours_joined = a.beam is not None and a.beam == b.beam
            rec_joined = ra.beam is not None and ra.beam == rb.beam
            total += 1
            agree += ours_joined == rec_joined
            if ours_joined and rec_joined:
                joins["both"] += 1
            elif ours_joined:
                joins["ours"] += 1
            elif rec_joined:
                joins["recorded"] += 1
    return {
        "matched": len(pairs),
        "sameHand": round(same_hand / max(1, len(pairs)), 4),
        "beamPairs": total,
        "sameBeamDecision": round(agree / max(1, total), 4),
        "joins": joins,
    }


class Replay:
    """An offline ``complete``: the recorded Sonnet sheet answers (its hands and beam groups on the target notes;
    clefs and 8va as the header gives them). The reference request gets its frames per quarter."""

    def __init__(self, rec: Sheet) -> None:
        self.rec = rec
        self.calls: list = []
        self.usd = 0.0

    def __call__(self, system: str, messages: list[dict]) -> str:
        text = messages[0]["content"]
        if "reference figure of song" in text:
            q = (frames_per_quarter(self.rec) or 12.5) * 40
            return f"```\nquarterMs={q:.0f}\n# why: the recorded run\n```"
        block = text.split("## Target")[1].split("```")[1]
        target = f1.read(block.strip())
        pool: dict[tuple[int, int], list] = {}
        for n in self.rec.notes:
            pool.setdefault((n.frame, n.midi), []).append(n)
        out = []
        for n in target.notes:
            r = next(
                (pool[(f, n.midi)].pop(0) for f in (n.frame, n.frame + 1) if pool.get((f, n.midi))),
                None,
            )
            staff = r.staff if r is not None else (1 if n.midi >= 60 else 2)
            out.append(replace(n, staff=staff, beam=r.beam if r is not None else None))
        cols = Counter()
        for k in {(n.staff, n.beam, n.frame) for n in out if n.beam is not None}:
            cols[k[:2]] += 1
        out = [
            replace(n, beam=None) if n.beam is not None and cols[(n.staff, n.beam)] < 2 else n
            for n in out
        ]
        ans = Sheet(
            notes=out, clefs=dict(target.clefs), key=target.key, quarter_ms=target.quarter_ms
        )
        return "```\n" + f1.write(ans.sort(), mode="frames") + "```"


class Logged:
    """An offline ``complete``: the replies logged by an earlier run, in order, with their recorded cost. The chain
    is deterministic, so the same notes give the same prompts; from the first prompt that differs from the logged
    one (the code changed what is sent, or the checker rejects a logged reply), the requests go to ``live``, or
    the replay stops when there is none."""

    def __init__(self, folder: Path, live: Any = None, on_call: Any = None) -> None:
        self.logs = [json.loads(p.read_text()) for p in sorted(folder.glob("request-*.json"))]
        self.live = live
        self.on_call = (
            on_call  # the replayed requests are logged again, so the new run can be replayed
        )
        self.diverged = False
        self.replayed = 0
        self.calls: list = []

    @property
    def usd(self) -> float:
        return sum(c.usd for c in self.calls)

    def __call__(self, system: str, messages: list[dict]) -> str:
        k = len(self.calls)
        if not self.diverged and k < len(self.logs) and self.logs[k]["messages"] == messages:
            from aitu_backend.sheet_llm import Call

            self.calls.append(Call(**self.logs[k]["call"]))
            self.replayed += 1
            if self.on_call:
                self.on_call(self.calls[-1], messages, self.logs[k]["reply"])
            return self.logs[k]["reply"]
        if self.live is None:
            raise RuntimeError(f"request {k + 1}: the prompt differs from the logged one")
        self.diverged = True
        reply = self.live(system, messages)
        self.calls.append(self.live.calls[-1])
        return reply


def resolve(prefixes: list[str]) -> list[str]:
    parts = bundle.list_parts(layers=["private"])
    out = []
    for p in prefixes:
        found = [x for x in parts if x.startswith(p)]
        if not found:
            raise SystemExit(f"no part {p}")
        out.append(found[0])
    return out


def test_key(out: Path) -> None:
    """Task 4.1: three requests (a tiny one, then the reference request of 7 Years twice: the second reads the
    cached instructions)."""
    from aitu_backend.sheet_llm import ClaudeComplete

    claude = ClaudeComplete()
    rows = []
    begin = time.perf_counter()
    msg = claude.client.messages.create(
        model=claude.model,
        max_tokens=64,
        messages=[{"role": "user", "content": "Reply with the single word OK."}],
    )
    rows.append(
        {
            "request": "tiny",
            "reply": "".join(b.text for b in msg.content if b.type == "text"),
            "usage": msg.usage.to_dict(),
            "seconds": round(time.perf_counter() - begin, 2),
        }
    )
    pid = resolve(["1a16a836"])[0]
    plain = frames.from_notes(starting_hands(pid))
    first = min(n.frame for n in plain.notes)
    start = Sheet(notes=llm._part(plain, first, first + 400))
    prompt = llm.reference_prompt(plain, start, pid[:8])
    for name in ("reference (cache write)", "reference (cache read)"):
        reply = claude(llm.instructions(), [{"role": "user", "content": prompt}])
        rows.append({"request": name, "reply": reply, **asdict(claude.calls[-1])})
    out.mkdir(parents=True, exist_ok=True)
    (out / "test-key.json").write_text(json.dumps(rows, indent=2, default=str))
    print(json.dumps(rows, indent=2, default=str))


def run(pid: str, args: argparse.Namespace, out: Path) -> dict:
    notes = starting_hands(pid)
    rec = recorded(pid)
    log_dir = out / pid[:8]
    log_dir.mkdir(parents=True, exist_ok=True)
    counter = Counter()

    def on_call(call, messages, text) -> None:
        counter["n"] += 1
        (log_dir / f"request-{counter['n']:02d}.json").write_text(
            json.dumps({"call": asdict(call), "messages": messages, "reply": text}, indent=1)
        )

    if args.from_run:
        live = None
        if args.then_live:
            from aitu_backend.sheet_llm import ClaudeComplete

            live = ClaudeComplete(model=args.model, effort=args.effort, on_call=on_call)
        complete: Any = Logged(
            paths.lab_dir() / "sheet-llm" / args.from_run / pid[:8], live, on_call
        )
    elif args.replay:
        if rec is None:
            raise SystemExit(f"{pid[:8]}: no recorded run")
        complete = Replay(rec)
    else:
        from aitu_backend.sheet_llm import ClaudeComplete

        complete = ClaudeComplete(model=args.model, effort=args.effort, on_call=on_call)

    def on_window(w: llm.WindowLog) -> None:
        last = complete.calls[-1] if complete.calls else None
        print(
            f"  {pid[:8]} window {w.k + 1:2d}  f{w.start}-f{w.end}  {w.status:7s} replies {w.replies}  "
            + (f"{last.seconds:5.1f} s  ${complete.usd:.3f}" if last else "")
            + (f"  {w.errors[-1][:2]}" if w.errors else "")
            + (f"  {w.note}" if w.note else ""),
            flush=True,
        )

    begin = time.perf_counter()
    song = llm.write_frames(
        notes, complete, sid=pid[:8], max_windows=args.windows, on_window=on_window
    )
    seconds = round(time.perf_counter() - begin, 1)
    (out / f"{pid[:8]}.f1").write_text(song.text)
    (out / f"{pid[:8]}-algorithm.f1").write_text(f1.write(song.algo.sheet, mode="frames"))
    got, lost = frames.cells_of(f1.read(song.text), notes)
    unhanded = Counter()
    for (_, midi, cell), k in got.items():
        unhanded[(midi, cell)] += k
    want = Counter()
    for (_, midi, cell), k in frames.matrix_cells(notes).items():
        want[(midi, cell)] += k
    hands_changed = 0
    algo_staff = {(n.frame, n.midi): n.staff for n in song.algo.sheet.notes}
    for n in song.sheet.notes:
        hands_changed += algo_staff.get((n.frame, n.midi), n.staff) != n.staff
    calls = complete.calls
    row = {
        "part": pid,
        "notes": len(song.sheet.notes),
        "seconds": seconds,
        **song.summary,
        "quarterMs": song.quarter_ms,
        "reference": {k: v for k, v in song.reference.items() if k != "reply"},
        "recordedQuarterMs": round((frames_per_quarter(rec) or 0) * 40, 1) if rec else None,
        "windowsLog": [asdict(w) for w in song.windows],
        "info": {k: v for k, v in song.info.items() if k != "problems"},
        "problems": song.info["problems"][:10],
        "roundTrip": unhanded == want and lost == 0,  # every onset cell, whatever its hand
        "handsChangedFromStart": hands_changed,
        "inputTokens": sum(c.input_tokens for c in calls),
        "cacheWriteTokens": sum(c.cache_write_tokens for c in calls),
        "cacheReadTokens": sum(c.cache_read_tokens for c in calls),
        "outputTokens": sum(c.output_tokens for c in calls),
        "requestSeconds": round(sum(c.seconds for c in calls), 1),
        "usd": round(complete.usd, 4),
    }
    if rec is not None:
        row["vsRecorded"] = compare(song.sheet, rec)
        row["algorithmVsRecorded"] = compare(song.algo.sheet, rec)
    print(
        f"{pid[:8]}  windows {row['ok']}/{row['windows']} ok ({row['ok_first_check']} first)  failed "
        f"{row['failed']}  skipped {row['skipped']}  quarter {song.quarter_ms:.0f} ({song.reference.get('source')})"
        f"  ${row['usd']:.3f}  {seconds} s  problems {len(song.info['problems'])}  round trip {row['roundTrip']}"
        + (
            f"  same hand {row['vsRecorded']['sameHand']:.3f} (algorithm "
            f"{row['algorithmVsRecorded']['sameHand']:.3f})"
            if rec is not None
            else ""
        ),
        flush=True,
    )
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("parts", nargs="*", help="part ids or their first characters")
    parser.add_argument("--viewer", action="store_true", help="the 10 viewer songs")
    parser.add_argument(
        "--windows", type=int, help="at most this many windows per part (the rest: algorithm)"
    )
    parser.add_argument("--model", default="claude-sonnet-5-5")
    parser.add_argument("--effort", default="high")
    parser.add_argument(
        "--replay", action="store_true", help="the recorded Sonnet sheets answer (no API)"
    )
    parser.add_argument("--from-run", help="replay the logged replies of this run (no API)")
    parser.add_argument(
        "--then-live",
        action="store_true",
        help="with --from-run: ask Claude from the first prompt that differs",
    )
    parser.add_argument(
        "--dry", action="store_true", help="print the reference and first window prompts"
    )
    parser.add_argument("--test-key", action="store_true", help="three test requests (task 4.1)")
    parser.add_argument("--run", help="name of the run folder (default: the time)")
    args = parser.parse_args()

    name = args.run or datetime.now().strftime("%Y%m%d-%H%M%S") + ("-replay" if args.replay else "")
    out = paths.lab_dir() / "sheet-llm" / name
    if args.test_key:
        test_key(out)
        return
    pids = resolve(args.parts + (VIEWER if args.viewer else []))
    if args.dry:
        for pid in pids:
            prompts: list[str] = []

            def keep(system: str, messages: list[dict]) -> str:
                prompts.append(messages[-1]["content"])
                return "```\nquarterMs=500\n```" if len(prompts) == 1 else ""

            llm.write_frames(starting_hands(pid), keep, sid=pid[:8], max_windows=1, max_checks=1)
            for p in prompts:
                print(p, "\n" + "=" * 100)
        return
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for pid in pids:
        rows.append(run(pid, args, out))
        (out / "summary.json").write_text(json.dumps(rows, indent=2, default=str))
    total = sum(r["usd"] for r in rows)
    print(f"{len(rows)} parts, ${total:.3f}, logs in {out}")


if __name__ == "__main__":
    main()
