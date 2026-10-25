"""The texts of the LLM step (product core since phase 15): the frozen instructions, the window prompt, the feedback.

* ``prompt/instructions.md``: the system prompt, the same for every window (the measured phase 7 prompt with the
  user's left-hand clef rules of phase 14 and the API answer section; few-shot examples included as text). The
  research package builds it from the rulebook and the dataset (``aitu_research.llm.prompts.product_instructions``);
  a test asserts that this file equals it.
* :func:`window_prompt`: the user message of one window (target, look-ahead, decided context).
* ``prompt/feedback.md``: the user message after a rejected answer (one line per problem).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from aitu_backend.sheet.llm.windows import last_bars_text, range_lines
from aitu_backend.sheet.sheet import f1
from aitu_backend.sheet.sheet.data import Sheet

__all__ = ["PROMPT_DIR", "PROMPT_VERSION", "feedback", "instructions", "window_prompt"]

PROMPT_DIR = Path(__file__).with_name("prompt")
PROMPT_VERSION = "2026-10-23"  # phase 14 clef rules, version 4 (see prompt/VERSION)


@lru_cache(maxsize=1)
def instructions() -> str:
    return (PROMPT_DIR / "instructions.md").read_text(encoding="utf-8")


def feedback(errors: list[str]) -> str:
    template = (PROMPT_DIR / "feedback.md").read_text(encoding="utf-8")
    return template.format(errors="\n".join(f"- {e}" for e in errors)).rstrip("\n")


def window_prompt(
    *,
    sid: str,
    index: int,
    target: Sheet,
    lookahead: Sheet,
    context: str | None,
    first_bar: int,
    bar_frame: int | None,
    answer_to: str = "in your reply",
) -> str:
    """The prompt of window ``index`` (0 = first) of a song. ``context`` = the kept bars of the previous accepted
    answer (F1 bars); ``bar_frame`` = the frame near which bar ``first_bar`` starts (from the previous answer).
    ``answer_to`` ends the sentence that says where to write (the research harness: a file)."""
    lo, hi = min(n.frame for n in target.notes), max(n.frame for n in target.notes)
    out = [f"# Window {index + 1} of song {sid} (frames f{lo}–f{hi})"]
    if context:
        try:
            rl = "\n".join(range_lines(f1.read(context)))
        except f1.F1Error:
            rl = ""
        out.append(
            "## Decided context (the last bars kept from your previous window)\n\n```\n"
            + last_bars_text(context).strip()
            + "\n```\n"
            + (f"\n```\n{rl}\n```" if rl else "")
        )
    out.append(
        "## Target (write all of these notes)\n\n```\n"
        + f1.write(target, mode="frames").strip()
        + "\n```"
    )
    if lookahead.notes:
        out.append(
            "## Look-ahead (do not write these)\n\n```\n"
            + f1.write(lookahead, mode="frames").strip()
            + "\n```"
        )
    if not context:
        start = "Start with bar 1 (bar 0 if the first bar is a pickup)."
    else:
        near = (
            f" (its downbeat is near frame f{bar_frame} by the tempo of the context)"
            if bar_frame
            else ""
        )
        start = (
            f"The context ends with bar {first_bar - 1}. The target starts with bar {first_bar}{near}: write "
            f"`bar {first_bar}` first and keep the meter and the beat of the context unless the music clearly "
            "changes."
        )
    out.append(
        f"## Answer\n\nWrite the target in F1 bars with frame anchors {answer_to}. {start} The first bar "
        "line of your answer always carries `meter=` and `key=`."
    )
    return "\n\n".join(out) + "\n"
