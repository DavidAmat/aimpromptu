"""The OpenAI client of the level runs (implementation 04-3, Phase 5), with a stand-in for the API (no request)."""

from __future__ import annotations

from types import SimpleNamespace as NS

import pytest

from aitu_backend.sheet.llm.frames import SkipWindow
from aitu_backend.sheet_llm import OpenAIComplete, openai_price


def response(text: str, *, model="gpt-6-luna", inp=10_000, read=0, written=0, out=3_000, reasoning=2_500,
             refusal=False, incomplete=None):
    content = [NS(type="refusal", refusal="no")] if refusal else [NS(type="output_text", text=text)]
    return NS(
        id="resp_1",
        model=model,
        status="incomplete" if incomplete else "completed",
        incomplete_details=NS(reason=incomplete) if incomplete else None,
        output=[NS(type="reasoning"), NS(type="message", content=content)],
        output_text="" if refusal else text,
        usage=NS(
            input_tokens=inp,
            input_tokens_details=NS(cached_tokens=read, cache_write_tokens=written),
            output_tokens=out,
            output_tokens_details=NS(reasoning_tokens=reasoning),
        ),
    )


class FakeStream:
    def __init__(self, r):
        self.r = r

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get_final_response(self):
        return self.r


def fake_client(replies, sent):
    def stream(**params):
        sent.append(params)
        return FakeStream(replies.pop(0))

    return NS(responses=NS(stream=stream))


def test_openai_complete_caches_the_system_prompt_and_the_conversation_and_records_the_cost() -> None:
    sent: list[dict] = []
    replies = [
        response("first", inp=10_000, written=9_000),
        response("second", inp=14_000, read=9_000, written=4_500),
    ]
    gpt = OpenAIComplete(model="gpt-6-luna", cache_key="song|easy", client=fake_client(replies, sent))
    assert gpt("SYSTEM", [{"role": "user", "content": "batch"}]) == "first"
    p = sent[0]
    assert p["model"] == "gpt-6-luna" and p["reasoning"] == {"effort": "max"}
    assert p["prompt_cache_options"] == {"mode": "explicit"} and p["prompt_cache_key"] == "song|easy"
    assert p["store"] is False
    # the system prompt is the first part, as a developer message with a breakpoint after it
    dev = p["input"][0]
    assert dev["role"] == "developer" and dev["content"][0]["text"] == "SYSTEM"
    assert dev["content"][0]["prompt_cache_breakpoint"] == {"mode": "explicit"}
    assert p["input"][1]["content"][0]["prompt_cache_breakpoint"] == {"mode": "explicit"}

    # a reply after a rejected answer: the same prefix, a breakpoint on every user message
    msgs = [
        {"role": "user", "content": "batch"},
        {"role": "assistant", "content": "first"},
        {"role": "user", "content": "feedback"},
    ]
    assert gpt("SYSTEM", msgs) == "second"
    q = sent[1]["input"]
    assert q[0] == dev and q[1]["content"][0]["text"] == "batch"
    assert q[1]["content"][0]["prompt_cache_breakpoint"] == {"mode": "explicit"}
    assert q[2] == {"role": "assistant", "content": "first"}
    assert q[3]["content"][0]["prompt_cache_breakpoint"] == {"mode": "explicit"}

    a, b = gpt.calls
    assert (a.input_tokens, a.cache_write_tokens, a.cache_read_tokens) == (1_000, 9_000, 0)
    assert (b.input_tokens, b.cache_write_tokens, b.cache_read_tokens) == (500, 4_500, 9_000)
    assert a.reasoning_tokens == 2_500 and a.stop_reason == "completed"
    assert a.usd == pytest.approx((1_000 * 0.10 + 9_000 * 0.125 + 3_000 * 0.50) / 1e6)
    assert b.usd == pytest.approx((500 * 0.10 + 4_500 * 0.125 + 9_000 * 0.01 + 3_000 * 0.50) / 1e6)
    assert gpt.usd == pytest.approx(a.usd + b.usd)


def test_openai_complete_skips_a_refusal_and_returns_an_incomplete_answer() -> None:
    sent: list[dict] = []
    gpt = OpenAIComplete(
        model="gpt-6.1-sol",
        client=fake_client([response("", model="gpt-6.1-sol", refusal=True),
                            response("half", model="gpt-6.1-sol", incomplete="max_output_tokens")], sent),
    )
    with pytest.raises(SkipWindow):
        gpt("S", [{"role": "user", "content": "x"}])
    assert "prompt_cache_key" not in sent[0]
    assert gpt("S", [{"role": "user", "content": "x"}]) == "half"
    assert [c.stop_reason for c in gpt.calls] == ["refusal", "incomplete:max_output_tokens"]


def test_openai_prices_follow_the_model_and_its_dated_names() -> None:
    assert openai_price("gpt-6.1-terra", 1_000_000, 0, 0, 0) == pytest.approx(1.0)
    assert openai_price("gpt-6.1-terra-2026-10-01", 0, 1_000_000, 0, 1_000_000) == pytest.approx(5.05)
    with pytest.raises(KeyError):
        openai_price("gpt-4o", 1, 1, 0, 0)


def test_openai_complete_sets_at_most_four_breakpoints() -> None:
    gpt = OpenAIComplete(model="gpt-6-luna", client=NS())
    msgs = []
    for k in range(5):
        msgs += [{"role": "user", "content": f"u{k}"}, {"role": "assistant", "content": f"a{k}"}]
    body = gpt.request("S", msgs[:-1])
    marked = [p["content"][0]["text"] for p in body["input"]
              if isinstance(p["content"], list) and "prompt_cache_breakpoint" in p["content"][0]]
    assert marked == ["S", "u2", "u3", "u4"]
