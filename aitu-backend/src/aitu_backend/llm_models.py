"""The models of the LLM, in one table (implementation 04-6, Part B): the one source of truth for which model a run
uses and what it costs.

* The model of every run the user starts without choosing one is the setting ``AITU_LLM_MODEL``
  (:func:`aitu_backend.config.llm_model`).
* :data:`TABLE` holds, for each model the backend knows: the name the dialog shows, its provider (``openai`` or
  ``anthropic``), the effort the app asks for, its prices, whether the dialog's **Model** selector offers it, and the
  cost and the time of a request compared with :data:`MEASURED_WITH`, when they were measured. A model with
  ``choice`` off is there for its price only (a model a fallback answers with, a model of an old comparison).
* The page reads the choices from ``GET /sheet/{uuid}/llm/costs`` (:func:`choices`); a run asks :func:`resolve`,
  :func:`provider`, :func:`effort`; the cost of a request asks :func:`prices`; the estimates ask :func:`ratio`.

A model in the setting that the table does not hold still works: it is the first choice, named by its name, asked
with ``medium`` effort, its provider guessed from its name (``claude-...``: Anthropic), its cost counted as 0 (a
warning in the backend log) and its estimate the one of :data:`MEASURED_WITH`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from aitu_backend import config

__all__ = [
    "MEASURED_WITH",
    "TABLE",
    "Model",
    "choices",
    "default",
    "effort",
    "prices",
    "provider",
    "ratio",
    "resolve",
]

log = logging.getLogger(__name__)

#: The model the estimates of ``part_sheet.job`` (``USD_*``, ``SECONDS_*``) were measured with, at medium effort
#: (implementation 04-3, Phase 5, 2026-10-30): a dated measure, so its name stays here.
MEASURED_WITH = "gpt-6.1-terra"

#: Tokens of a typical request of a level run with :data:`MEASURED_WITH` (04-3 Phase 5: about 6,500 read from the
#: cache, 3,000 written to it, 1,850 output, a few plain): the cost ratio of a model never measured is the price of
#: this request with it, against :data:`MEASURED_WITH`.
TYPICAL_REQUEST = (10, 1850, 3000, 6500)  # input, output, cache write, cache read


@dataclass(frozen=True)
class Model:
    label: str
    provider: str  # "openai" or "anthropic"
    effort: str
    #: US dollars per million tokens: input, output, cache write, cache read. None: no price known.
    prices: tuple[float, float, float, float] | None
    #: Offered by the dialog's **Model** selector.
    choice: bool = False
    #: The cost and the time of a request compared with :data:`MEASURED_WITH`, measured per passage of a level run
    #: (04-3 Phase 5). None: never measured.
    measured: tuple[float, float] | None = None


#: Prices: OpenAI's pricing page, Standard tier, prompts up to 272K tokens, cache write of 30 minutes (2026-10-30);
#: Anthropic's platform prices, cache write of 5 minutes (2026-10). Measured per passage (04-3 Phase 5): Terra $0.041
#: and 1.0 min, Sol $0.072 and 1.0 min, Sonnet 5.5 at high effort $0.269 and 2.5 min. The choices are the user's
#: (2026-10-30), in the order the dialog lists them after the setting's model.
TABLE: dict[str, Model] = {
    "gpt-6.1-terra": Model("GPT-6.1 Terra", "openai", "medium", (1.0, 5.0, 1.25, 0.05), True, (1.0, 1.0)),
    "gpt-6.1-sol": Model("GPT-6.1 Sol", "openai", "medium", (2.0, 10.0, 2.5, 0.10), True, (1.8, 1.0)),
    "claude-sonnet-5-5": Model("Sonnet 5.5", "anthropic", "high", (2.0, 10.0, 2.5, 0.20), True, (6.6, 2.5)),
    "gpt-6-luna": Model("GPT-6 Luna", "openai", "medium", (0.10, 0.50, 0.125, 0.01)),
    "claude-sonnet-5": Model("Sonnet 5", "anthropic", "high", (2.0, 10.0, 2.5, 0.20)),
    "claude-opus-5-5": Model("Opus 5.5", "anthropic", "high", (4.0, 20.0, 5.0, 0.20)),
}


def default() -> str:
    """The model of a run when the user chooses none: the setting ``AITU_LLM_MODEL``."""
    return config.llm_model()


def _guess(name: str) -> Model:
    """A model the table does not hold (only the setting's can be asked): what the backend assumes of it."""
    return Model(name, "anthropic" if name.startswith("claude") else "openai", "medium", None, True)


def _entry(name: str) -> Model:
    return TABLE.get(name) or _guess(name)


def choices() -> list[dict[str, str]]:
    """The models of the dialog's **Model** selector, the setting's first (added when the table does not offer
    it): ``value`` (the name a run is asked with) and ``label``."""
    first = default()
    names = [first] + [n for n, m in TABLE.items() if m.choice and n != first]
    return [{"value": n, "label": _entry(n).label} for n in names]


def resolve(name: str | None) -> str:
    """The model of a run: the one chosen, or the setting's. A name the selector does not offer is refused
    (``ValueError``)."""
    if name is None:
        return default()
    if name not in {c["value"] for c in choices()}:
        raise ValueError(f"No AI model {name!r}.")
    return name


def provider(name: str) -> str:
    """``openai`` or ``anthropic``: which SDK and which key a run with ``name`` uses."""
    return _entry(name).provider


def effort(name: str) -> str:
    """The effort the app asks ``name`` for."""
    return _entry(name).effort


def _base(name: str) -> str | None:
    """The table's name of a model the API answered with: the same, or the longest one it starts with followed by
    ``-`` (a dated name such as ``gpt-6.1-terra-2026-10-01``)."""
    if name in TABLE:
        return name
    found = [n for n in TABLE if name.startswith(n + "-")]
    return max(found, key=len) if found else None


def prices(name: str) -> tuple[float, float, float, float] | None:
    """US dollars per million tokens of ``name`` (input, output, cache write, cache read), or None when unknown."""
    base = _base(name)
    return TABLE[base].prices if base is not None else None


def cost(name: str, input_tokens: int, output_tokens: int, cache_write: int, cache_read: int) -> float:
    """US dollars of one request. A model with no price costs 0, with a warning in the backend log, so a model new
    to the table never stops a run."""
    p = prices(name)
    if p is None:
        log.warning("No price for the model %r: its requests count as $0.", name)
        return 0.0
    p_in, p_out, p_write, p_read = p
    return (input_tokens * p_in + output_tokens * p_out + cache_write * p_write + cache_read * p_read) / 1e6


def ratio(name: str) -> tuple[float, float]:
    """The cost and the time of a run with ``name`` compared with :data:`MEASURED_WITH`, for the estimates: the
    measured ones; else the cost from the prices (a typical request) and the time 1; with no price, 1 and 1."""
    entry = TABLE.get(name)
    if entry is not None and entry.measured is not None:
        return entry.measured
    mine, theirs = prices(name), prices(MEASURED_WITH)
    if mine is None or theirs is None:
        return 1.0, 1.0
    priced = [sum(t * p for t, p in zip(TYPICAL_REQUEST, prices_)) for prices_ in (mine, theirs)]
    return round(priced[0] / priced[1], 2), 1.0
