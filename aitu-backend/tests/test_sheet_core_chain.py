"""The product core ``aitu_backend.sheet`` on its own: import boundary, frozen files, the chain's conversation and
fallback. Copied from the research core (implementation 03, Phase 1) with the backend names."""

from __future__ import annotations

import ast
import re
import sys
from collections import Counter
from pathlib import Path

import aitu_backend.sheet
from aitu_backend.sheet.llm import prompts
from aitu_backend.sheet.llm.chain import write_song
from aitu_backend.sheet.sheet import f1
from tests.test_sheet_core_golden import GOLD, notes_of_frames

CORE = Path(aitu_backend.sheet.__file__).resolve().parent
ALLOWED = set(sys.stdlib_module_names) | {"numpy", "__future__"}
# the backend modules the core uses instead of the research's copies (``sheet/pmn.py``)
BACKEND = {
    "aitu_backend.pmn.notes",
    "aitu_backend.pmn.columns",
    "aitu_backend.pmn.dense",
    "aitu_backend.matrix.keys",
}


def _allowed(name: str) -> bool:
    return (
        name.split(".")[0] in ALLOWED or name in BACKEND or name.startswith("aitu_backend.sheet.")
    )


def test_imports_stay_inside_the_core():
    bad = []
    for p in CORE.rglob("*.py"):
        for node in ast.walk(ast.parse(p.read_text())):
            names = (
                [a.name for a in node.names]
                if isinstance(node, ast.Import)
                else (
                    [node.module or ""]
                    if isinstance(node, ast.ImportFrom) and not node.level
                    else []
                )
            )
            bad += [f"{p.name}: {n}" for n in names if not _allowed(n)]
    assert not bad


def test_frozen_files():
    for name in ("instructions.md", "feedback.md", "VERSION"):
        assert (prompts.PROMPT_DIR / name).exists()
    assert prompts.instructions().startswith("# Task")
    assert (
        "clef.L1 Priority for the left hand" in prompts.instructions()
    )  # the phase 14 clef rules, version 4
    assert (prompts.PROMPT_DIR / "VERSION").read_text().split()[0] == prompts.PROMPT_VERSION
    for asset in (
        "engrave/leipzig.json",
        "engrave/spacing_model.json",
        "proposal/beat_weights.json",
        "proposal/meter_weights.json",
        "proposal/spelling_tables.json",
    ):
        assert (CORE / asset).exists(), asset


def test_feedback_lists_one_problem_per_line():
    text = prompts.feedback(
        ["2 onsets of the input are missing: f412 E4", "bar 9: a position beyond the end"]
    )
    assert (
        "\n- 2 onsets of the input are missing: f412 E4\n- bar 9: a position beyond the end\n"
        in text
    )
    assert text.startswith("The checker did not accept your answer:")


def _song():
    d = GOLD / "chain" / "43faf78e"
    frames = f1.read((d / "frames.f1").read_text())
    replies = {
        int(p.stem.split("-")[1]): p.read_text() for p in (d / "answers").glob("window-*.md")
    }
    return notes_of_frames(frames), frames, replies


def test_a_rejected_reply_gets_the_feedback_and_a_second_try():
    notes, frames, replies = _song()
    calls = []

    def complete(system: str, messages: list[dict]) -> str:
        calls.append([m["role"] for m in messages])
        k = int(re.match(r"# Window (\d+)", messages[0]["content"]).group(1))
        if len(messages) == 1 and k == 1:
            return "I think this is 3/4."  # not F1: rejected
        return "```\n" + replies[k] + "```"  # the product's reply shape: one fenced block

    res = write_song(notes, complete, key=frames.key, max_windows=2)
    assert calls[:2] == [["user"], ["user", "assistant", "user"]]
    assert [w.status for w in res.windows] == ["ok", "ok"] and res.windows[0].replies == 2
    assert res.summary == {"windows": 2, "ok": 2, "ok_first_check": 1, "failed": 0, "requests": 3}


def test_a_window_that_fails_every_check_keeps_the_algorithm_and_every_onset():
    notes, frames, _ = _song()
    res = write_song(notes, lambda system, messages: "no answer", key=frames.key, max_windows=3)
    assert [w.status for w in res.windows] == ["failed"] * 3 and all(
        w.replies == 3 for w in res.windows
    )
    last = res.windows[-1].end
    want = Counter((n.frame, n.midi) for n in frames.notes if n.frame < last)
    assert Counter((n.frame, n.midi) for n in res.sheet.notes) == want
