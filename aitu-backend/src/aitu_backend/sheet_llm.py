"""Claude for the LLM step of the new sheet (implementation 03, Phase 4): the ``complete`` function of the core.

The core (:mod:`aitu_backend.sheet.llm.frames`) imports no SDK; it calls ``complete(system, messages) -> text``.
:class:`ClaudeComplete` is that function with the official ``anthropic`` SDK and the API key of ``.env``
(``ANTHROPIC_API_KEY``, from the Claude Console organization linked to the Max 5x credits, plan section 3.8):

* the model is Sonnet 5.5 (``claude-sonnet-5-5``, the user's choice of 2026-10-22), with adaptive thinking and an
  explicit effort (``high``, the model's default);
* the system prompt (the frozen instructions, the same for every request of every song) is cached
  (``cache_control``): the first request of a song writes it, the others read it at a tenth of the price;
* each request is streamed, so a long answer never meets the HTTP time limit; the SDK retries a lost connection, a
  rate limit (429) and a server error (5xx) ``max_retries`` times with a growing wait;
* a refusal (``stop_reason == "refusal"``) raises :class:`~aitu_backend.sheet.llm.frames.SkipWindow`: that window
  keeps the algorithm. The server-side fallback (``fallbacks: "default"``) first gives a declined request to another
  model when the category allows it;
* an assistant turn sent back after a rejected answer carries the full content of that reply (its thinking blocks
  unchanged), as the API asks;
* every request is recorded (:class:`Call`: tokens, seconds, US dollars), for the cost per song.

Any other error (no key, no credits left, no network after the retries) is raised; the chain then keeps the
algorithm for the rest of the song and says why in its result.

:class:`OpenAIComplete` (implementation 04-3, Phase 5) is the same function with OpenAI's models (GPT-6 Luna,
GPT-6.1 Terra, GPT-6.1 Sol), through the Responses API and ``OPENAI_API_KEY``, for the comparison of models on the
level runs. The app does not use it yet. Its caching is explicit: a breakpoint after the system prompt (the same in
every request of a run, read at a tenth of the price or less) and one after each user message (so a reply after a
rejected answer reads the whole conversation before it); every request of one client sends the same
``prompt_cache_key``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

from aitu_backend.sheet.llm.frames import SkipWindow

__all__ = ["MODEL", "Call", "ClaudeComplete", "OpenAIComplete", "openai_price", "price"]

MODEL = "claude-sonnet-5-5"
EFFORT = "high"
MAX_TOKENS = 64000
TIMEOUT_S = 600.0
MAX_RETRIES = 4
FALLBACK_BETA = "server-side-fallback-2026-07-01"

#: US dollars per million tokens: input, output, cache write (5 minutes), cache read (2026-10, platform prices)
PRICES = {
    "claude-sonnet-5-5": (2.0, 10.0, 2.5, 0.20),
    "claude-sonnet-5": (2.0, 10.0, 2.5, 0.20),
    "claude-opus-5-5": (4.0, 20.0, 5.0, 0.20),
}


def price(
    model: str, input_tokens: int, output_tokens: int, cache_write: int, cache_read: int
) -> float:
    p_in, p_out, p_write, p_read = PRICES.get(model, PRICES[MODEL])
    return (
        input_tokens * p_in + output_tokens * p_out + cache_write * p_write + cache_read * p_read
    ) / 1e6


@dataclass
class Call:
    model: str
    input_tokens: int  # not cached
    cache_write_tokens: int
    cache_read_tokens: int
    output_tokens: int  # thinking included
    seconds: float
    stop_reason: str
    request_id: str | None
    usd: float
    reasoning_tokens: int = 0  # part of output_tokens (OpenAI reports it; Claude does not)


class ClaudeComplete:
    """``complete(system, messages) -> text`` with Claude. ``client`` replaces the SDK client (tests)."""

    def __init__(
        self,
        *,
        model: str = MODEL,
        effort: str = EFFORT,
        max_tokens: int = MAX_TOKENS,
        timeout: float = TIMEOUT_S,
        max_retries: int = MAX_RETRIES,
        fallbacks: bool = True,
        client: Any = None,
        on_call: Callable[[Call, list[dict], str], None] | None = None,
    ) -> None:
        if client is None:
            import anthropic

            client = anthropic.Anthropic(timeout=timeout, max_retries=max_retries)
        self.client = client
        self.model = model
        self.effort = effort
        self.max_tokens = max_tokens
        self.fallbacks = fallbacks
        self.on_call = on_call
        self.calls: list[Call] = []
        self._content: dict[str, Any] = {}  # reply text -> the reply's content blocks

    @property
    def usd(self) -> float:
        return sum(c.usd for c in self.calls)

    def __call__(self, system: str, messages: list[dict]) -> str:
        sent = [
            {
                "role": m["role"],
                "content": (
                    self._content.get(m["content"], m["content"])
                    if m["role"] == "assistant"
                    else m["content"]
                ),
            }
            for m in messages
        ]
        params: dict[str, Any] = dict(
            model=self.model,
            max_tokens=self.max_tokens,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=sent,
            thinking={"type": "adaptive"},
            output_config={"effort": self.effort},
        )
        begin = time.perf_counter()
        if self.fallbacks:
            with self.client.beta.messages.stream(
                **params, betas=[FALLBACK_BETA], fallbacks="default"
            ) as stream:
                message = stream.get_final_message()
        else:
            with self.client.messages.stream(**params) as stream:
                message = stream.get_final_message()
        usage = message.usage
        call = Call(
            model=message.model,
            input_tokens=usage.input_tokens or 0,
            cache_write_tokens=usage.cache_creation_input_tokens or 0,
            cache_read_tokens=usage.cache_read_input_tokens or 0,
            output_tokens=usage.output_tokens or 0,
            seconds=round(time.perf_counter() - begin, 2),
            stop_reason=str(message.stop_reason),
            request_id=getattr(message, "_request_id", None),
            usd=0.0,
        )
        call.usd = price(
            call.model,
            call.input_tokens,
            call.output_tokens,
            call.cache_write_tokens,
            call.cache_read_tokens,
        )
        self.calls.append(call)
        text = "".join(b.text for b in message.content if b.type == "text")
        if self.on_call:
            self.on_call(call, messages, text)
        if message.stop_reason == "refusal":
            details = getattr(message, "stop_details", None)
            raise SkipWindow(f"refusal ({getattr(details, 'category', None)})")
        self._content[text] = message.content
        return text


OPENAI_EFFORT = "max"
OPENAI_MAX_TOKENS = 128000

#: US dollars per million tokens: input, output, cache write (30 minutes), cache read (2026-10-30, OpenAI's pricing
#: page, Standard tier, prompts up to 272K tokens)
OPENAI_PRICES = {
    "gpt-6-luna": (0.10, 0.50, 0.125, 0.01),
    "gpt-6.1-terra": (1.0, 5.0, 1.25, 0.05),
    "gpt-6.1-sol": (2.0, 10.0, 2.5, 0.10),
}


def openai_price(model: str, input_tokens: int, output_tokens: int, cache_write: int, cache_read: int) -> float:
    """``input_tokens``: the tokens neither read from nor written to the cache."""
    base = next((m for m in OPENAI_PRICES if model == m or model.startswith(m + "-")), None)
    if base is None:
        raise KeyError(f"no price for {model}")
    p_in, p_out, p_write, p_read = OPENAI_PRICES[base]
    return (input_tokens * p_in + output_tokens * p_out + cache_write * p_write + cache_read * p_read) / 1e6


def _openai_key() -> str | None:
    """``OPENAI_API_KEY`` of the environment, else of the repository's ``.env`` (the container started before the
    key was added)."""
    import os
    from pathlib import Path

    if os.environ.get("OPENAI_API_KEY"):
        return os.environ["OPENAI_API_KEY"]
    for env in (Path("/work/aimpromptu/.env"), Path(__file__).resolve().parents[3] / ".env"):
        if env.is_file():
            for line in env.read_text().splitlines():
                if line.startswith("OPENAI_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


class OpenAIComplete:
    """``complete(system, messages) -> text`` with an OpenAI model. ``cache_key``: the ``prompt_cache_key`` of every
    request (one per run, for example the song and the level). ``client`` replaces the SDK client (tests)."""

    def __init__(
        self,
        *,
        model: str,
        effort: str = OPENAI_EFFORT,
        cache_key: str | None = None,
        max_tokens: int = OPENAI_MAX_TOKENS,
        timeout: float = 1800.0,
        max_retries: int = MAX_RETRIES,
        client: Any = None,
        on_call: Callable[[Call, list[dict], str], None] | None = None,
    ) -> None:
        if client is None:
            import openai

            client = openai.OpenAI(api_key=_openai_key(), timeout=timeout, max_retries=max_retries)
        self.client = client
        self.model = model
        self.effort = effort
        self.cache_key = cache_key
        self.max_tokens = max_tokens
        self.on_call = on_call
        self.calls: list[Call] = []

    @property
    def usd(self) -> float:
        return sum(c.usd for c in self.calls)

    def request(self, system: str, messages: list[dict]) -> dict[str, Any]:
        """The body of the request: the system prompt first (a developer message, because the top-level
        ``instructions`` cannot hold a breakpoint), then the messages. A breakpoint after the system prompt and after
        each of the last three user messages (at most four per request): the API finds a cached prefix only at a
        breakpoint of the request, so a reply after a rejected answer reads the turns before it only when their
        breakpoints stay (measured on 2026-10-30)."""
        mark = {"mode": "explicit"}
        users = [i for i, m in enumerate(messages) if m["role"] != "assistant"][-3:]
        sent: list[dict[str, Any]] = [
            {
                "role": "developer",
                "content": [{"type": "input_text", "text": system, "prompt_cache_breakpoint": mark}],
            }
        ]
        for i, m in enumerate(messages):
            if m["role"] == "assistant":
                sent.append({"role": "assistant", "content": m["content"]})
                continue
            part: dict[str, Any] = {"type": "input_text", "text": m["content"]}
            if i in users:
                part["prompt_cache_breakpoint"] = mark
            sent.append({"role": "user", "content": [part]})
        params: dict[str, Any] = {
            "model": self.model,
            "input": sent,
            "reasoning": {"effort": self.effort},
            "max_output_tokens": self.max_tokens,
            "prompt_cache_options": {"mode": "explicit"},
            "store": False,
        }
        if self.cache_key:
            params["prompt_cache_key"] = self.cache_key
        return params

    def __call__(self, system: str, messages: list[dict]) -> str:
        params = self.request(system, messages)
        begin = time.perf_counter()
        with self.client.responses.stream(**params) as stream:
            response = stream.get_final_response()
        usage = response.usage
        details = usage.input_tokens_details
        read = details.cached_tokens or 0
        written = getattr(details, "cache_write_tokens", 0) or 0
        refused = any(
            getattr(c, "type", None) == "refusal"
            for item in response.output
            if getattr(item, "type", None) == "message"
            for c in item.content
        )
        incomplete = getattr(response, "incomplete_details", None)
        call = Call(
            model=response.model,
            input_tokens=max(0, (usage.input_tokens or 0) - read - written),
            cache_write_tokens=written,
            cache_read_tokens=read,
            output_tokens=usage.output_tokens or 0,
            seconds=round(time.perf_counter() - begin, 2),
            stop_reason="refusal" if refused else (f"incomplete:{incomplete.reason}" if incomplete else str(response.status)),
            request_id=getattr(response, "_request_id", None) or response.id,
            usd=0.0,
            reasoning_tokens=usage.output_tokens_details.reasoning_tokens or 0,
        )
        call.usd = openai_price(
            call.model, call.input_tokens, call.output_tokens, call.cache_write_tokens, call.cache_read_tokens
        )
        self.calls.append(call)
        text = response.output_text or ""
        if self.on_call:
            self.on_call(call, messages, text)
        if refused:
            raise SkipWindow("refusal")
        return text
