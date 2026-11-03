"""The model of the LLM in one place (implementation 04-6, Part B): the setting ``AITU_LLM_MODEL``, the one table of
the models (``llm_models``), the choices the dialog reads from ``GET /sheet/{uuid}/llm/costs``, and a model the table
does not hold. The AI is a stand-in: no request leaves the machine."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from aitu_backend import config, llm_models
from aitu_backend.part_sheet import job
import test_part_sheet
from test_part_sheet import sheet

client = test_part_sheet.client
part = test_part_sheet.part
#: The real check (the ``client`` fixture replaces it with a stand-in that says yes).
AVAILABLE = job.available


# ------------------------------------------------------------------ the setting and the table


def test_the_setting_names_the_model_and_has_a_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AITU_LLM_MODEL", raising=False)
    assert config.llm_model() == config.DEFAULT_LLM_MODEL == llm_models.default()
    monkeypatch.setenv("AITU_LLM_MODEL", "  ")
    assert config.llm_model() == config.DEFAULT_LLM_MODEL
    monkeypatch.setenv("AITU_LLM_MODEL", "gpt-6.1-sol")
    assert llm_models.default() == "gpt-6.1-sol" and llm_models.resolve(None) == "gpt-6.1-sol"


def test_the_choices_put_the_setting_first(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AITU_LLM_MODEL", "claude-sonnet-5-5")
    values = [c["value"] for c in llm_models.choices()]
    assert values[0] == "claude-sonnet-5-5" and len(values) == len(set(values))
    assert set(values) == {n for n, m in llm_models.TABLE.items() if m.choice}
    # A model kept for its price only is not offered, and cannot be asked for.
    assert "claude-opus-5-5" not in values
    with pytest.raises(ValueError):
        llm_models.resolve("claude-opus-5-5")


def test_a_model_the_table_does_not_hold_works_from_the_setting(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("AITU_LLM_MODEL", "gpt-7-nova")
    assert llm_models.choices()[0] == {"value": "gpt-7-nova", "label": "gpt-7-nova"}
    assert llm_models.resolve("gpt-7-nova") == "gpt-7-nova"
    assert (llm_models.provider("gpt-7-nova"), llm_models.effort("gpt-7-nova")) == ("openai", "medium")
    assert llm_models.provider("claude-fable-9") == "anthropic"
    # No price: the estimate is the measured model's, and a request costs 0 with a warning (no crash).
    assert llm_models.prices("gpt-7-nova") is None and llm_models.ratio("gpt-7-nova") == (1.0, 1.0)
    with caplog.at_level("WARNING", logger="aitu_backend.llm_models"):
        assert llm_models.cost("gpt-7-nova", 1000, 1000, 0, 0) == 0.0
    assert "gpt-7-nova" in caplog.text
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    complete = job._complete("p", "stretch")
    assert type(complete).__name__ == "OpenAIComplete" and (complete.model, complete.effort) == ("gpt-7-nova", "medium")


def test_the_ratio_is_measured_else_from_the_prices() -> None:
    assert llm_models.ratio(llm_models.MEASURED_WITH) == (1.0, 1.0)
    assert llm_models.ratio("claude-sonnet-5-5") == (6.6, 2.5)  # measured in 04-3, Phase 5
    # Never measured: the price of a typical request against the measured model; the time 1.
    usd, time = llm_models.ratio("claude-opus-5-5")
    assert time == 1.0 and usd > llm_models.ratio("claude-sonnet-5")[0] > 1.0
    assert llm_models.ratio("gpt-6-luna")[0] < 0.2


def test_a_dated_name_finds_its_price_and_the_longest_name_wins() -> None:
    assert llm_models.prices("gpt-6.1-terra-2026-10-01") == llm_models.TABLE["gpt-6.1-terra"].prices
    assert llm_models.prices("claude-sonnet-5-5-20261001") == llm_models.TABLE["claude-sonnet-5-5"].prices
    assert llm_models.prices("claude-sonnet-5-20260901") == llm_models.TABLE["claude-sonnet-5"].prices
    assert llm_models.prices("gpt-6.1") is None


# ------------------------------------------------------------------ the routes


def test_the_costs_give_the_choices_and_the_setting(
    client: TestClient, part: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    sheet(client, part)
    costs = client.get(f"/sheet/{part}/llm/costs").json()
    assert costs["model"] == config.llm_model() == costs["models"][0]["value"]
    assert all(set(c) == {"value", "label"} for c in costs["models"])
    assert "level-both" in costs  # the estimates are still there
    monkeypatch.setenv("AITU_LLM_MODEL", "gpt-7-nova")
    costs = client.get(f"/sheet/{part}/llm/costs").json()
    assert costs["model"] == "gpt-7-nova" and costs["models"][0] == {"value": "gpt-7-nova", "label": "gpt-7-nova"}


def test_the_routes_take_the_setting_model_and_refuse_an_unknown_one(
    client: TestClient, part: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    sheet(client, part)
    monkeypatch.setenv("AITU_LLM_MODEL", "gpt-7-nova")
    plan = client.get(f"/sheet/{part}/llm/batches", params={"run": "all", "model": "gpt-7-nova"})
    assert plan.status_code == 200 and plan.json()["model"] == "gpt-7-nova"
    assert client.get(f"/sheet/{part}/llm/batches", params={"run": "all"}).json()["model"] == "gpt-7-nova"
    calls: list[dict] = []

    def started(uuid: str, **kwargs: object):
        calls.append(kwargs)
        return type("J", (), {"id": "j", "status": "queued"})()

    monkeypatch.setattr(job, "start", started)
    monkeypatch.setattr(job, "available", lambda model=None: True)
    assert client.post(f"/sheet/{part}/llm", json={"model": "gpt-7-nova"}).status_code == 202
    assert calls[-1]["model"] == "gpt-7-nova"
    assert client.post(f"/sheet/{part}/llm", json={"model": "claude-opus-5-5"}).status_code == 422


def test_a_claude_model_without_its_key_is_not_set_up(
    client: TestClient, part: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    sheet(client, part)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(job, "available", AVAILABLE)
    assert job.available("claude-sonnet-5-5") is False
    reply = client.post(f"/sheet/{part}/llm", json={"model": "claude-sonnet-5-5"})
    assert reply.status_code == 409 and reply.json()["detail"] == "This AI is not set up on this machine."
