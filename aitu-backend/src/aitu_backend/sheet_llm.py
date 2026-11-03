"""The clients of the LLM: the ``complete(system, messages) -> text`` function of the core, one per provider.

The core (:mod:`aitu_backend.sheet.llm.frames`) imports no SDK; it calls ``complete(system, messages) -> text``. The
model and its effort come from the caller (``part_sheet.job``, from :mod:`aitu_backend.llm_models`, the one table of
the models); the prices of every request too (:func:`price`).

:class:`ClaudeComplete` (implementation 03, Phase 4) uses the official ``anthropic`` SDK and ``ANTHROPIC_API_KEY``:

* adaptive thinking and an explicit effort;
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

:class:`OpenAIComplete` (implementation 04-3, Phase 5) is the same function with OpenAI's models, through the
Responses API and ``OPENAI_API_KEY``. Its caching is explicit: a breakpoint after the system prompt (the same in
every request of a run, read at a tenth of the price or less) and one after each user message (so a reply after a
rejected answer reads the whole conversation before it); every request of one client sends the same
``prompt_cache_key``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

from aitu_backend import llm_models
from aitu_backend.sheet.llm.frames import SkipWindow

__all__ = ["Call", "ClaudeComplete", "NoCredits", "OpenAIComplete", "price"]

MAX_TOKENS = 64000
TIMEOUT_S = 600.0
MAX_RETRIES = 4
FALLBACK_BETA = "server-side-fallback-2026-07-01"


def price(
    model: str, input_tokens: int, output_tokens: int, cache_write: int, cache_read: int
) -> float:
    """US dollars of one request (``input_tokens``: the tokens neither read from nor written to the cache), from the
    table of the models. A model with no price: 0, with a warning in the backend log."""
    return llm_models.cost(model, input_tokens, output_tokens, cache_write, cache_read)


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
    """``complete(system, messages) -> text`` with an Anthropic model. ``effort``: by default the table's.
    ``client`` replaces the SDK client (tests)."""

    def __init__(
        self,
        *,
        model: str,
        effort: str | None = None,
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
        self.effort = effort or llm_models.effort(model)
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


class NoCredits(RuntimeError):
    """The OpenAI account has no credits left (``insufficient_quota``): the run stops, and the page asks the user to
    add credits to the OpenAI account (the user, 2026-10-30)."""


def _no_credits(exc: Exception) -> bool:
    code = getattr(exc, "code", None)
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        code = code or body.get("code") or (body.get("error") or {}).get("code")
    return code == "insufficient_quota" or "insufficient_quota" in str(exc)


OPENAI_MAX_TOKENS = 128000


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
    """``complete(system, messages) -> text`` with an OpenAI model. ``effort``: by default the table's.
    ``cache_key``: the ``prompt_cache_key`` of every request (one per run, for example the song and the level).
    ``client`` replaces the SDK client (tests)."""

    def __init__(
        self,
        *,
        model: str,
        effort: str | None = None,
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
        self.effort = effort or llm_models.effort(model)
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
        try:
            with self.client.responses.stream(**params) as stream:
                response = stream.get_final_response()
        except Exception as exc:
            if _no_credits(exc):
                raise NoCredits("The OpenAI account has no credits left.") from exc
            raise
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
        call.usd = price(
            call.model, call.input_tokens, call.output_tokens, call.cache_write_tokens, call.cache_read_tokens
        )
        self.calls.append(call)
        text = response.output_text or ""
        if self.on_call:
            self.on_call(call, messages, text)
        if refused:
            raise SkipWindow("refusal")
        return text
