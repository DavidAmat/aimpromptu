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
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

from aitu_backend.sheet.llm.frames import SkipWindow

__all__ = ["Call", "ClaudeComplete", "MODEL", "price"]

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
