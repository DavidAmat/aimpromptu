"""The Enhance with AI dialog of implementation 04, Phase 4: the gallery of the tests with the AI.

* ``--song TITLE BEFORE AFTER`` (one or more): **Simplify** on a song. ``BEFORE`` is the part as it was (a version of
  My library, only read), ``AFTER`` a temporary copy of it that the AI simplified. The changes are grouped into
  passages (changes less than ``JOIN_S`` apart are one passage); each passage is drawn as the page draws it, before
  above after, with a band over it, the change lines of the run's record (where and why, the AI's words) and the
  changes read from the data.
* ``--stretch JSON PART START END STAFF``: **a stretch of one hand**, from the reply an in-memory test saved (the
  ``stretch`` list of the JSON: its last reply): the reply spliced into the sheet of ``PART`` with the other hand
  fixed, and laid on the notes without the notes it left out, drawn under the sheet as it is.

Nothing is written but the page. In the backend container::

    docker exec -i aimpromptu-backend-1 python scripts/simplify_gallery.py \\
        --out ../context/implementations/04-app-enhancements/gallery/phase-4 \\
        --song "7 Years" 1a16a836-... <copy> --song "Moonlight Shadow" c0edc9b0-... <copy>
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

import numpy as np

from aitu_backend.part_sheet import build, store
from aitu_backend.sheet.engrave import frames as engine
from aitu_backend.sheet.llm import frames as llm_frames
from aitu_backend.sheet.sheet import f1
from aitu_backend.sheet.sheet import frames as frames_mod
from aitu_backend.matrix.keys import LOWEST_MIDI
from aitu_backend.sheet.sheet.data import FRAME_MS
from aitu_backend.sheet.sheet.frames import drawn_columns
from aitu_backend.transcription import pipeline

from simplicity_gallery import _drawn, _figure, banded, changes, clock

#: Changes closer than this, in seconds, are drawn as one passage.
JOIN_S = 6.0
#: The music drawn around a passage, before and after it, in seconds.
AROUND_S = 2.0
#: Passages drawn per song, at most (the rest are listed).
MOST = 12


def passages(frames: list[int]) -> list[tuple[int, int]]:
    """The frames of the changes, grouped: ``(first, last)`` of each group."""
    out: list[list[int]] = []
    for f in sorted(set(frames)):
        if out and (f - out[-1][-1]) * FRAME_MS / 1000 < JOIN_S:
            out[-1].append(f)
        else:
            out.append([f])
    return [(g[0], g[-1]) for g in out]


def song_section(
    no: int, title: str, before_part: str, after_part: str, notes: dict[int, str]
) -> tuple[str, str, list[str]]:
    before, after = _drawn(before_part), _drawn(after_part)
    record = store.load(after_part).record
    run = record.simplified[-1]
    hand, added, left, usd = run[0], run[1], run[2], run[3]
    lines = run[5] if len(run) > 5 else []
    problems = [p for p in frames_mod.check(after) if p not in set(frames_mod.check(before))]
    every = changes(before, after, 0, 10**6)
    changed = [
        int(t.split(" ")[0][1:]) for t in every if " added," in t or " left out," in t
    ]
    groups = passages(changed)
    opts = engine.Options(width=110)
    pad = int(AROUND_S * 1000 / FRAME_MS)
    items = []
    for k, (a, b) in enumerate(groups[:MOST], start=1):
        why = [line for line in lines if a <= int(line.split(" ")[1][1:]) <= b]
        listed = changes(before, after, a, b + 1)
        said = "".join(
            f'<p class="note">{html.escape(text)}</p>' for f, text in notes.items() if a <= f <= b
        )
        items.append(
            f'<section id="s{no}-{k}"><h3>{html.escape(title)}, passage {k}: {clock(a)}</h3>{said}'
            + _figure(
                "Before (the My library version)",
                banded(engine.render_frames(before, opts, segment=(max(0, a - pad), b + pad)), a, b + 1),
            )
            + _figure(
                f"After: Simplify the {hand} hand (a test copy)",
                banded(engine.render_frames(after, opts, segment=(max(0, a - pad), b + pad)), a, b + 1),
            )
            + (
                "<details open><summary>The AI's changes and why</summary><ul>"
                + "".join(f"<li>{html.escape(line[2:])}</li>" for line in why)
                + "</ul></details>"
                if why
                else ""
            )
            + "<details open><summary>What changed (from the data)</summary><ul>"
            + "".join(f"<li>{html.escape(t)}</li>" for t in listed)
            + "</ul></details></section>"
        )
    rest = groups[MOST:]
    more = (
        f"<p>{len(rest)} more passages, not drawn: "
        + ", ".join(clock(a) for a, _ in rest)
        + ".</p>"
        if rest
        else ""
    )
    head = (
        f'<h2 id="s{no}">{html.escape(title)}: Simplify the {hand} hand</h2>'
        f"<p>{added} notes added and {left} left out, in {len(groups)} passages; "
        f"{sum(' moved to ' in t for t in every)} hands moved; {len(problems)} new problems by the sheet's rules. "
        f"Cost of the run: ${usd:.2f}.</p>"
        + (
            ""
            if lines
            else "<p>This run was made before the app kept the AI's reason for each change: only what "
            "changed is listed.</p>"
        )
    )
    index = f'<li><a href="#s{no}">{html.escape(title)}</a> ({len(groups)} passages)</li>'
    return index, head + "".join(items) + more, problems


def stretch_section(path: Path, part: str, start: int, end: int, staff: int) -> str:
    saved = json.loads(path.read_text(encoding="utf-8"))["stretch"]
    reply = saved[-1]["reply"]
    current = _drawn(part)
    errs, answer = llm_frames.check_answer(
        reply, current, drop=True, free=(start, end), hand=staff
    )
    spliced = llm_frames.splice(current, answer, start, end, keep=3 - staff)
    kept = {(n.frame, n.midi) for n in spliced.notes}
    notes = pipeline.starting_hands(part)
    # The notes the answer left out, taken off the notes (the app marks them removed in notes.pmn), found by their
    # drawn column and key as ``part_sheet.edits`` finds them.
    _, onset = drawn_columns(notes.on_ms)
    column = np.floor(np.round(onset / FRAME_MS, 9) + 0.5).astype(np.int64)
    place = [(int(c), int(k) + LOWEST_MIDI) for c, k in zip(column, notes.key)]
    gone = {p for p in place if start <= p[0] < end and p not in kept}
    keep = np.array([p not in gone for p in place])
    after = build.reapply(spliced, notes.take(np.flatnonzero(keep)))
    opts = engine.Options(width=110)
    hand = "left" if staff == 2 else "right"
    words = "Make the octaves single notes."
    return (
        f'<h2 id="stretch">A stretch of the {hand} hand</h2>'
        f"<p>7 Years, {clock(start)} to {clock(end)}, the {hand} hand only, with the words "
        f"<q>{html.escape(words)}</q> (an in-memory test: nothing was written). The other hand stays exactly as it "
        f"is. {len(gone)} notes left out. Drawn with the figures of the rule; the app also keeps the figures the AI "
        "wrote, so a figure or two may differ on the page.</p>"
        + _figure("Before", banded(engine.render_frames(current, opts, segment=(start - 50, end + 50)), start, end))
        + _figure("After", banded(engine.render_frames(after, opts, segment=(start - 50, end + 50)), start, end))
        + ("<p>The check: " + html.escape("; ".join(errs)) + "</p>" if errs else "")
    )


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Simplify: Phase 4 gallery</title>
<style>
:root { color-scheme: only light; --ink: #1d1d1f; --soft: #5f6368; --line: #e3e3e6; }
body { margin: 0; background: #fff; color: var(--ink); font: 15px/1.5 system-ui, sans-serif; }
main { max-width: 1440px; margin: 0 auto; padding: 24px 16px 80px; }
h1 { font-size: 24px; margin: 0 0 8px; } h2 { font-size: 19px; margin: 40px 0 4px; }
h3 { font-size: 16px; margin: 28px 0 2px; }
figure { margin: 8px 0 12px; } figcaption { font-size: 13px; color: var(--soft); margin-bottom: 4px; }
.svg { overflow-x: auto; border: 1px solid var(--line); border-radius: 6px; padding: 8px; background: #fff; }
.svg svg { display: block; max-width: none; } details { font-size: 13px; color: var(--soft); }
details ul { margin: 4px 0; }
.note { background: #fff4cc; border-radius: 6px; padding: 8px 12px; max-width: 980px; }
</style></head><body><main>
<h1>Enhance with AI: Simplify, and a stretch of one hand</h1>
<p>Implementation 04, Phase 4. <b>Simplify</b> goes over the whole song, batch after batch, with the rules of
simplicity only (uniform patterns, no quick jumps); the hands do not move. Each batch sees every change made before
it, so a passage that repeats gets the same change. Each passage shows the sheet before (the My library version) and
after (a test copy, deleted after); the band marks the notes that changed. Under it, the AI's own words for each
change.</p>
<ol>{{INDEX}}</ol>
{{SECTIONS}}
</main></body></html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--song", nargs=3, action="append", default=[], metavar=("TITLE", "BEFORE", "AFTER"))
    parser.add_argument("--stretch", nargs=5, metavar=("JSON", "PART", "START", "END", "STAFF"))
    parser.add_argument(
        "--note", nargs=3, action="append", default=[], metavar=("TITLE", "FRAME", "TEXT"),
        help="a sentence shown over the passage of that song that holds the frame",
    )
    args = parser.parse_args()
    index, sections = [], []
    if args.stretch:
        path, part, start, end, staff = args.stretch
        sections.append(stretch_section(Path(path), part, int(start), int(end), int(staff)))
        index.append('<li><a href="#stretch">A stretch of one hand</a></li>')
    for no, (title, before, after) in enumerate(args.song, start=1):
        notes = {int(f): text for t, f, text in args.note if t == title}
        line, body, problems = song_section(no, title, before, after, notes)
        index.append(line)
        sections.append(body)
        for problem in problems:
            print(f"{title}: rule broken: {problem}")
    page = PAGE.replace("{{INDEX}}", "".join(index)).replace("{{SECTIONS}}", "".join(sections))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "index.html").write_text(page, encoding="utf-8")
    print(f"-> {args.out / 'index.html'}")


if __name__ == "__main__":
    main()
