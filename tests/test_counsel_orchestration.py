"""End-to-end orchestration tests with mocked OpenRouter calls."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.counsel import run_full_counsel
from backend.errors import AllModelsFailedError, OpenRouterError


@pytest.mark.asyncio
async def test_full_deliberation_happy_path(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    async def fake_query_model(model, messages, timeout=None):
        prompt = messages[0]["content"]
        # Stage 3 prompt embeds Stage 2 text (which contains "FINAL RANKING:"),
        # so check the Lead Counsel marker first.
        if "Lead Counsel" in prompt:
            return "# LEAD COUNSEL STRATEGY MEMORANDUM\n\nFinal synthesis..."
        if "FINAL RANKING:" in prompt:
            return (
                "Each response was thoughtful.\n"
                "FINAL RANKING:\n"
                "1. Response A\n"
                "2. Response B\n"
                "3. Response C\n"
                "4. Response D\n"
            )
        return "Stage 1 analysis content"

    with patch("backend.openrouter.query_model", side_effect=fake_query_model), \
         patch("backend.counsel.query_model", side_effect=fake_query_model):
        result = await run_full_counsel("What is our strategy?")

    assert set(result["stage1"].keys()) == {
        "plaintiff_strategist",
        "defense_analyst",
        "procedural_specialist",
        "evidence_counsel",
    }
    for role_data in result["stage1"].values():
        assert role_data["error"] is None
        assert role_data["content"]

    assert len(result["stage2"]["assessments"]) == 4
    assert len(result["stage2"]["label_mapping"]) == 4
    assert len(result["stage2"]["aggregate_rankings"]) == 4

    assert "LEAD COUNSEL STRATEGY MEMORANDUM" in result["stage3"]["content"]
    assert result["stage3"]["error"] is None


@pytest.mark.asyncio
async def test_partial_stage1_failure_still_completes(monkeypatch):
    """If 2 of 4 Stage 1 models fail, deliberation finishes with the 2 that worked."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    fail_models = {"x-ai/grok-4.20", "openai/gpt-5.4"}

    async def fake_query_model(model, messages, timeout=None):
        if model in fail_models:
            raise OpenRouterError(model, 429, "rate limited")
        prompt = messages[0]["content"]
        if "Lead Counsel" in prompt:
            return "Final memo with 2 inputs."
        if "FINAL RANKING:" in prompt:
            return (
                "Both look strong.\n"
                "FINAL RANKING:\n1. Response A\n2. Response B\n"
            )
        return "stage1 success"

    with patch("backend.openrouter.query_model", side_effect=fake_query_model), \
         patch("backend.counsel.query_model", side_effect=fake_query_model):
        result = await run_full_counsel("Question?")

    successes = [r for r in result["stage1"].values() if r["content"]]
    failures = [r for r in result["stage1"].values() if r["error"]]
    assert len(successes) == 2
    assert len(failures) == 2

    assert len(result["stage2"]["label_mapping"]) == 2
    assert result["stage3"]["content"] == "Final memo with 2 inputs."


@pytest.mark.asyncio
async def test_all_stage1_failure_raises(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    async def always_fail(model, messages, timeout=None):
        raise OpenRouterError(model, 500, "boom")

    with patch("backend.openrouter.query_model", side_effect=always_fail), \
         patch("backend.counsel.query_model", side_effect=always_fail):
        with pytest.raises(AllModelsFailedError):
            await run_full_counsel("Question?")


# Codex-driven additions


@pytest.mark.asyncio
async def test_lead_counsel_failure_preserves_partial_work(monkeypatch):
    """If synthesis fails, stage1+stage2 work is preserved with stage3.error set."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    async def fake_query_model(model, messages, timeout=None):
        prompt = messages[0]["content"]
        if "Lead Counsel" in prompt:
            raise OpenRouterError(model, 503, "service down")
        if "FINAL RANKING:" in prompt:
            return (
                "Done.\n"
                "FINAL RANKING:\n1. Response A\n2. Response B\n"
                "3. Response C\n4. Response D"
            )
        return "stage1 work"

    with patch("backend.openrouter.query_model", side_effect=fake_query_model), \
         patch("backend.counsel.query_model", side_effect=fake_query_model):
        result = await run_full_counsel("Q?")

    # Stage 1 + Stage 2 work preserved
    assert all(r["content"] for r in result["stage1"].values())
    assert len(result["stage2"]["assessments"]) == 4
    assert len(result["stage2"]["aggregate_rankings"]) == 4

    # Stage 3 has an error marker but no content
    assert result["stage3"]["content"] is None
    assert result["stage3"]["error"] is not None


@pytest.mark.asyncio
async def test_stage2_unparseable_ballot_yields_empty_aggregates(monkeypatch):
    """Stage 2 prose with no FINAL RANKING → empty aggregates but stage3 still runs."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    async def fake_query_model(model, messages, timeout=None):
        prompt = messages[0]["content"]
        if "FINAL RANKING:" in prompt:
            return "I refuse to rank these in a structured way."
        if "Lead Counsel" in prompt:
            return "Synthesis even without rankings."
        return "stage1 content"

    with patch("backend.openrouter.query_model", side_effect=fake_query_model), \
         patch("backend.counsel.query_model", side_effect=fake_query_model):
        result = await run_full_counsel("Q?")

    assert all(r["content"] for r in result["stage1"].values())
    for assessment in result["stage2"]["assessments"].values():
        assert assessment["ranking"] == []
    assert result["stage2"]["aggregate_rankings"] == []
    assert result["stage3"]["content"] == "Synthesis even without rankings."


@pytest.mark.asyncio
async def test_self_votes_excluded_from_aggregate(monkeypatch):
    """Each evaluator ranks Response A first; aggregate must drop self-votes."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    async def fake_query_model(model, messages, timeout=None):
        prompt = messages[0]["content"]
        if "FINAL RANKING:" in prompt:
            # All evaluators produce the SAME ranking (A first).
            return (
                "Self-favoring eval.\n"
                "FINAL RANKING:\n1. Response A\n2. Response B\n"
                "3. Response C\n4. Response D"
            )
        if "Lead Counsel" in prompt:
            return "Synthesized."
        return "content"

    with patch("backend.openrouter.query_model", side_effect=fake_query_model), \
         patch("backend.counsel.query_model", side_effect=fake_query_model):
        result = await run_full_counsel("Q?")

    # With 4 personas and everyone voting A=1, B=2, C=3, D=4:
    # - A's self-vote (from the A-persona) is dropped → A has 3 positions
    # - B's self-vote (from the B-persona) is dropped → B has 3 positions
    # - Same for C and D → each has 3 positions.
    aggregates = result["stage2"]["aggregate_rankings"]
    assert len(aggregates) == 4
    assert all(len(a["positions"]) == 3 for a in aggregates), (
        f"Expected 3 votes per persona after self-vote exclusion, got: "
        f"{[(a['role'], len(a['positions'])) for a in aggregates]}"
    )
