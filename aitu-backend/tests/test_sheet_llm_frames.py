"""The LLM step of the new sheet (implementation 03, Phase 4): windows, the checker, the chain, the assembly by the
rules, the frozen prompt, and the Claude ``complete`` with a stand-in SDK client (no request leaves the machine).
"""

from __future__ import annotations

import re
from collections import Counter
from types import SimpleNamespace

import numpy as np

from aitu_backend.pmn import HAND_LEFT, HAND_RIGHT, Notes
from aitu_backend.sheet.llm import frames as llm
from aitu_backend.sheet.proposal.frames import propose_frames
from aitu_backend.sheet.sheet import f1, frames
from aitu_backend.sheet.sheet.data import Sheet
from aitu_backend.sheet_llm import ClaudeComplete

R, L = HAND_RIGHT, HAND_LEFT
Q = 500.0


def song(seconds: float = 60.0) -> Notes:
    """A left hand in eighths (bass, fifth, octave, fifth) under a right hand that holds a chord, then runs up and
    down in eighths; a pause of 1 s every 8 s."""
    rows = []
    t = 0.0
    bar = 0
    while t < seconds * 1000:
        root = [45, 41, 48, 43][bar % 4]
        for i, step in enumerate([0, 7, 12, 7, 0, 7, 12, 7]):
            rows.append((root + step, t + i * 250, 240, L))
        if bar % 2 == 0:
            rows += [(64, t, 1900, R), (69, t, 1900, R)]
        else:
            for i, m in enumerate([69, 71, 72, 74, 76, 74, 72, 71]):
                rows.append((m, t + i * 250, 240, R))
        t += 2000 + (1000 if bar % 4 == 3 else 0)
        bar += 1
    midi, on, length, hand = (list(x) for x in zip(*rows))
    return Notes.build(key=np.array(midi) - 21, on_ms=on, len_ms=length, hand=hand)


def oracle(notes: Notes, quarter_ms: float = Q, log: list | None = None):
    """A ``complete`` that answers each window with the algorithm's own decisions (hands, beams, clefs)."""
    algo = propose_frames(notes, quarter_ms=quarter_ms).sheet

    def complete(system: str, messages: list[dict]) -> str:
        if log is not None:
            log.append(messages)
        text = messages[0]["content"]
        if "reference figure of song" in text:
            return f"```\nquarterMs={quarter_ms:g}\n# why: the test\n```"
        a, b = (int(x) for x in re.search(r"frames f(\d+)-f(\d+)", text).groups())
        part = llm._algorithm_part(a, b + 1, algo)
        s = Sheet(
            notes=list(part.notes.values()),
            clefs=part.clefs,
            key=part.key,
            clef_changes=part.clef_changes,
            key_changes=part.key_changes,
            quarter_ms=quarter_ms,
        )
        return "Here it is:\n```\n" + f1.write(s.sort(), mode="frames") + "```\n"

    return complete


def unhanded(c: Counter) -> Counter:
    out: Counter = Counter()
    for (_, midi, cell), k in c.items():
        out[(midi, cell)] += k
    return out


# ------------------------------------------------------------------ windows and the reference figure


def test_windows_cover_the_song_end_at_pauses_and_stay_within_their_limits() -> None:
    notes = song(90)
    sheet = propose_frames(notes, quarter_ms=Q).sheet
    wins = llm.windows_of(sheet)
    cols = sorted({n.frame for n in sheet.notes})
    assert wins[0][0] == cols[0] and wins[-1][1] == cols[-1] + 1
    assert all(a[1] == b[0] for a, b in zip(wins, wins[1:]))  # contiguous, nothing decided twice
    for a, b in wins[:-1]:
        inside = [c for c in cols if a <= c < b]
        assert (inside[-1] - a) * 40 <= llm.WINDOW_MS[1]
        assert sum(1 for n in sheet.notes if a <= n.frame < b) <= llm.MAX_ONSETS
        # no beam group goes across the end
        assert not any(
            n.beam is not None and any(m.beam == n.beam and m.frame >= b for m in sheet.notes)
            for n in sheet.notes
            if a <= n.frame < b
        )


def test_the_gap_peaks_and_the_reference_reply() -> None:
    sheet = frames.from_notes(song())
    peaks, count = llm.gap_peaks(sheet)
    # the measured onsets, not the 40 ms columns (which would split 250 ms into 240 and 280 ms)
    assert abs(peaks[0][0] - 250) <= 1 and peaks[0][1] > 0.8 and count > 100
    prompt = llm.reference_prompt(sheet, sheet, "s1")
    assert (
        "about 250 ms" in prompt and "?: " in prompt and ":8" not in prompt
    )  # no hands, no figures
    assert llm.read_reference("```\nquarterMs=480\n# why: x\n```") == 480
    assert llm.read_reference("quarterMs=20") is None and llm.read_reference("no number") is None


# ------------------------------------------------------------------ the checker


def test_the_checker_lists_each_kind_of_problem() -> None:
    target = f1.read(
        "F1 frames frameMs=40 quarterMs=500\nkey=0 clefs: R=treble L=bass\n"
        + "\n".join(f"f{6 * i} ?: C4:8" if i % 2 else f"f{6 * i} ?: E4:8" for i in range(10))
    )

    def answer(lines: list[str], head: str = "key=0 clefs: R=treble L=bass") -> str:
        return (
            "```\nF1 frames frameMs=40 quarterMs=500\n" + head + "\n" + "\n".join(lines) + "\n```"
        )

    good = [f"f{6 * i} R: {'C4' if i % 2 else 'E4'}:8 b{1 + i // 5}" for i in range(10)]
    assert llm.check_answer(answer(good), target)[0] == []

    def errs(lines: list[str]) -> str:
        return " | ".join(llm.check_answer(answer(lines), target)[0])

    assert "missing" in errs(good[:-1])
    assert "not in the target" in errs(good[:-1] + ["f54 R: D4:8"])
    assert "without a hand" in errs(good[:-1] + ["f54 ?: C4:8"])
    nine = [f"f{6 * i} R: {'C4' if i % 2 else 'E4'}:8 b1" for i in range(9)] + ["f54 R: C4:8"]
    assert "a beam group of 9 notes" in errs(nine)
    assert "a beam group of one note" in errs(
        good[:4] + ["f24 R: E4:8 b2"] + [x.replace("b2", "") for x in good[5:]]
    )
    skip = [x.replace(" b1", "") if x.startswith("f12 ") else x for x in good]
    assert "skips the R note at f12" in errs(skip)
    assert "8va in the bass clef" in errs(
        [x.replace("R:", "L:") + (" 8va" if x.startswith("f0 ") else "") for x in good]
    )
    assert "'orn' with no ornament" in errs(good[:-1] + ["f54 R: C4:8 orn"])
    assert "parse error" in errs(good[:-1] + ["f54 R: H4:8"])
    assert llm.check_answer("I cannot.", target)[0][0].startswith("the answer must be F1 frames")


# ------------------------------------------------------------------ the chain


def test_the_chain_writes_a_valid_sheet_that_keeps_every_onset() -> None:
    notes = song()
    log: list = []
    result = llm.write_frames(notes, oracle(notes, log=log), sid="s1")
    assert result.reference["source"] == "llm" and result.quarter_ms == Q
    assert result.summary["ok"] == result.summary["windows"] == len(result.windows) > 2
    assert result.summary["requests"] == len(log) == len(result.windows) + 1
    assert result.info["problems"] == [] and frames.check(f1.read(result.text)) == []
    got, lost = frames.cells_of(f1.read(result.text), notes)
    assert lost == 0 and got == frames.matrix_cells(notes)
    # window 2 on: the decided context is the end of the previous answer, with its hands
    assert (
        "Decided context" in log[2][0]["content"] and "Decided context" not in log[1][0]["content"]
    )
    assert "?: " in log[1][0]["content"].split("## Target")[1]  # the target has no hands


def test_a_rejected_reply_gets_the_feedback_and_a_second_try() -> None:
    notes = song(20)
    good = oracle(notes)
    sent: list = []

    def complete(system: str, messages: list[dict]) -> str:
        sent.append(messages)
        if len(sent) == 2:  # the first window's first reply loses a note
            return "\n".join(good(system, messages).splitlines()[:-3]) + "\n```"
        return good(system, messages)

    result = llm.write_frames(notes, complete)
    first = result.windows[0]
    assert first.status == "ok" and first.replies == 2 and "missing" in first.errors[0][0]
    assert [m["role"] for m in sent[2]] == ["user", "assistant", "user"]
    assert sent[2][2]["content"].startswith("The checker did not accept your answer:\n- ")


def test_a_refused_window_keeps_the_algorithm_and_an_error_stops_the_requests() -> None:
    notes = song(90)
    good = oracle(notes)
    calls = Counter()

    def refuse_second(system: str, messages: list[dict]) -> str:
        calls["n"] += 1
        if calls["n"] == 3:
            raise llm.SkipWindow("refusal")
        return good(system, messages)

    result = llm.write_frames(notes, refuse_second)
    assert [w.status for w in result.windows[:3]] == ["ok", "failed", "ok"]
    assert result.parts[1].source == "algorithm" and result.info["problems"] == []

    def no_credits(system: str, messages: list[dict]) -> str:
        calls["m"] += 1
        if calls["m"] == 3:
            raise RuntimeError("credit balance too low")
        return good(system, messages)

    result = llm.write_frames(notes, no_credits)
    statuses = [w.status for w in result.windows]
    assert statuses[:2] == ["ok", "error"] and set(statuses[2:]) == {"skipped"} and calls["m"] == 3
    assert "credit balance" in result.windows[1].note and result.info["problems"] == []
    got, lost = frames.cells_of(f1.read(result.text), notes)
    assert lost == 0 and got == frames.matrix_cells(notes)


def test_hands_moved_by_the_llm_are_kept_and_the_figures_follow_them() -> None:
    notes = song(20)
    good = oracle(notes)

    def all_right(system: str, messages: list[dict]) -> str:
        reply = good(system, messages)
        if "reference figure" in messages[0]["content"]:
            return reply
        return re.sub(r"\bb\d+", "", reply.replace("L:", "R:"))

    result = llm.write_frames(notes, all_right, guards=False)
    assert {n.staff for n in result.sheet.notes} == {1}
    assert result.info["problems"] == []
    got, lost = frames.cells_of(f1.read(result.text), notes)
    assert lost == 0 and unhanded(got) == unhanded(frames.matrix_cells(notes))
    # with both hands in one, every figure is capped by the next onset of either: no figure longer than a corchea
    assert min(n.figure for n in result.sheet.notes if not n.grace) >= 8


def test_beam_groups_are_cut_where_the_rule_figures_break_them() -> None:
    sheet = f1.read(
        "F1 frames frameMs=40 quarterMs=500\nkey=0 clefs: R=treble L=bass\n"
        "f0 R: C5:8 b1\nf6 R: D5:8 b1\nf12 R: E5:4 b1\nf24 R: F5:8 b1\nf30 R: G5:8 b1\n"
        "f36 R: A5:16 b2\nf39 R: B5:16 b2\nf42 R: C6:8 b2\nf48 R: D6:8 b2\nf54 R: E6:8 b2\nf60 R: F6:16 b2\n"
        "f66 R: G5:8 b3\nf72 R: F5:8 b3\n"
    )
    why = llm.trim_beams(sheet)
    groups = Counter((n.beam, n.frame) for n in sheet.notes if n.beam is not None)
    sizes = sorted(Counter(b for b, _ in groups).values())
    # b1 is cut by the negra into two pairs; b2 holds two figures: the two sixteenths, then the eighths and the
    # closing sixteenth (one odd note at an edge); b3 is kept
    assert sizes == [2, 2, 2, 2, 4] and why["groups cut"] == 2 and why["groups kept"] == 1
    assert next(n for n in sheet.notes if n.frame == 12).beam is None


def test_the_beam_floor_counts_only_notes_that_can_be_joined() -> None:
    lines = "\n".join(f"f{6 * i} R: C5:8" for i in range(30))
    sheet = f1.read(f"F1 frames frameMs=40 quarterMs=500\nkey=0 clefs: R=treble L=bass\n{lines}\n")
    for n in sheet.notes:
        n.on_ms = n.frame * 40.0
    assert "pairs of consecutive eighths" in llm.beam_floor(sheet)[0]
    for n in sheet.notes:  # the same eighths, a negra apart: nothing to join
        n.on_ms = n.frame * 80.0
    assert llm.beam_floor(sheet) == []


# ------------------------------------------------------------------ the frozen prompt


def test_the_prompt_examples_pass_the_checker() -> None:
    text = llm.instructions()
    assert (
        text.startswith("# Task") and "clef.L1 Priority for the left hand" in text
    )  # version 4 clef rules
    assert "At most 8 notes in a group" in text and llm.PROMPT_VERSION == "5"
    blocks = re.findall(r"Input \(target\):\n```\n(.*?)```\n\nAnswer:\n```\n(.*?)```", text, re.S)
    assert len(blocks) == 4
    for given, answer in blocks:
        errs, sheet = llm.check_answer("```\n" + answer + "```", f1.read(given))
        assert errs == [], errs
        assert all(n.staff in (1, 2) for n in sheet.notes)
    assert "{errors}" in (llm.PROMPT_DIR / "feedback.md").read_text()


# ------------------------------------------------------------------ Claude, with a stand-in SDK client


class FakeStream:
    def __init__(self, message):
        self.message = message

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self):
        return self.message


def message(text: str, stop: str = "end_turn") -> SimpleNamespace:
    return SimpleNamespace(
        model="claude-sonnet-5-5",
        content=[
            SimpleNamespace(type="thinking", thinking=""),
            SimpleNamespace(type="text", text=text),
        ],
        usage=SimpleNamespace(
            input_tokens=1000,
            output_tokens=2000,
            cache_creation_input_tokens=6000,
            cache_read_input_tokens=0,
        ),
        stop_reason=stop,
        stop_details=SimpleNamespace(category="general_harms") if stop == "refusal" else None,
    )


def test_claude_complete_sends_the_cached_instructions_and_records_the_cost() -> None:
    sent: list[dict] = []
    replies = [message("first"), message("second"), message("", "refusal")]

    def stream(**params):
        sent.append(params)
        return FakeStream(replies[len(sent) - 1])

    client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(stream=stream)))
    claude = ClaudeComplete(client=client)
    assert claude("SYSTEM", [{"role": "user", "content": "window"}]) == "first"
    p = sent[0]
    assert p["model"] == "claude-sonnet-5-5" and p["thinking"] == {"type": "adaptive"}
    assert p["output_config"] == {"effort": "high"} and p["fallbacks"] == "default"
    assert p["system"] == [
        {"type": "text", "text": "SYSTEM", "cache_control": {"type": "ephemeral"}}
    ]
    # 1000 x $2 + 2000 x $10 + 6000 x $2.50 per million tokens
    assert abs(claude.calls[0].usd - 0.037) < 1e-9 and claude.calls[0].cache_write_tokens == 6000
    # the rejected reply goes back with its whole content (the thinking block unchanged)
    claude(
        "SYSTEM",
        [
            {"role": "user", "content": "window"},
            {"role": "assistant", "content": "first"},
            {"role": "user", "content": "feedback"},
        ],
    )
    assert sent[1]["messages"][1]["content"] is replies[0].content
    try:
        claude("SYSTEM", [{"role": "user", "content": "window"}])
    except llm.SkipWindow as exc:
        assert "general_harms" in str(exc)
    else:
        raise AssertionError("a refusal must skip the window")


def test_a_written_group_keeps_a_sixteenth_beamed_to_its_eighth() -> None:
    # a short-long pair is one group (one odd note opens it); two figures apart is never one group
    assert llm.one_figure([0, 1], [16, 8]) == [[0, 1]]
    assert llm.one_figure([0, 1, 2, 3], [16, 8, 16, 8]) == [[0, 1], [2, 3]]
    assert llm.one_figure([0, 1], [32, 8]) == [[0], [1]]
    assert llm.one_figure([0, 1, 2, 3, 4], [8, 8, 16, 8, 8]) == [
        [0, 1, 2],
        [3, 4],
    ]  # never inside a group


def test_the_checker_keeps_notes_within_four_ledger_lines_of_their_staff() -> None:
    target = f1.read(
        "F1 frames frameMs=40 quarterMs=500\nkey=0 clefs: R=treble L=bass\nf0 ?: B4:4\nf12 ?: B6:4\n"
    )

    def errs(head: str, a: str, b: str) -> str:
        reply = f"```\nF1 frames frameMs=40 quarterMs=500\n{head}\nf0 {a}\nf12 {b}\n```"
        return " | ".join(llm.check_answer(reply, target)[0])

    head = "key=0 clefs: R=treble L=bass"
    assert "B4 is four or more ledger lines above the bass staff" in errs(
        head, "L: B4:4", "R: B6:4 8va"
    )
    assert "B6 is four or more ledger lines above the treble staff" in errs(
        head, "R: B4:4", "R: B6:4"
    )
    assert errs(head, "L: clef=treble B4:4", "R: B6:4 8va") == ""
    assert errs(head, "L: A4:4".replace("A4", "B4"), "R: B6:4 8va").count("clef.L3") == 1


def test_short_8va_lines_of_one_passage_become_one() -> None:
    sheet = f1.read(
        "F1 frames frameMs=40 quarterMs=500\nkey=0 clefs: R=treble L=bass\n"
        "f0 R: G6:8 8va\nf6 R: E6:8\nf12 R: A6:8 8va\nf18 R: C5:8\nf24 R: G6:8 8va\n"  # joined: C5 and up
        "f30 R: B4:8\nf36 R: G6:8 8va\n"  # B4 between: not joined
        "f200 R: A6:8 8va\n"  # more than 2 s later: not joined
    )
    assert llm.join_ottavas(sheet) == 2
    under = [n.frame for n in sheet.notes if n.ottava]
    assert under == [0, 6, 12, 18, 24, 36, 200]
