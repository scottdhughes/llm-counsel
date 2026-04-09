"""Tests that matter metadata (jurisdiction, practice area) actually flows
into the stage prompts, not just the UI label.
"""

from __future__ import annotations

from backend.prompts import (
    build_stage1_prompt,
    build_stage2_prompt,
    build_stage3_prompt,
    get_persona,
)


MATTER_CA = {
    "matter_name": "Smith v. Acme",
    "practice_area": "civil",
    "jurisdiction": "state-ca",
}


# The rendered header starts with a distinctive box-drawing rule. The stage
# templates also contain the literal phrase "MATTER CONTEXT" in their
# instructional text ("Apply the governing law specified in the MATTER CONTEXT
# above"), so we detect the *rendered* header by its box rule and label rows
# rather than by the phrase alone.
HEADER_MARKER = "══════════════════════════════════════════════════════════"


def test_stage1_prompt_includes_matter_header_when_provided():
    persona = get_persona("defense_analyst")
    prompt = build_stage1_prompt(
        persona,
        "What's our exposure?",
        context=None,
        matter_context=MATTER_CA,
    )
    assert HEADER_MARKER in prompt
    assert "Name:          Smith v. Acme" in prompt
    assert "California (state)" in prompt
    assert "Civil litigation" in prompt
    assert "Governing law:" in prompt


def test_stage1_prompt_omits_matter_header_when_none():
    persona = get_persona("defense_analyst")
    prompt_without = build_stage1_prompt(
        persona, "What's our exposure?", context=None
    )
    prompt_with_empty = build_stage1_prompt(
        persona, "What's our exposure?", context=None, matter_context={}
    )
    # The rendered box rule is absent when no matter_context is passed
    assert HEADER_MARKER not in prompt_without
    assert HEADER_MARKER not in prompt_with_empty
    assert "Name:" not in prompt_without
    assert "Governing law:" not in prompt_without


def test_stage2_prompt_includes_matter_header_when_provided():
    persona = get_persona("procedural_specialist")
    prompt = build_stage2_prompt(
        persona,
        "What's the right motion?",
        anonymized=[("A", "analysis one"), ("B", "analysis two")],
        matter_context=MATTER_CA,
    )
    assert HEADER_MARKER in prompt
    assert "California (state)" in prompt
    # The dynamic 2-slot example is still rendered correctly
    assert "1. Response A" in prompt
    assert "2. Response B" in prompt


def test_stage3_prompt_includes_matter_header_when_provided():
    prompt = build_stage3_prompt(
        question="Q?",
        stage1_results={
            "defense_analyst": {"display_name": "Defense Analyst", "content": "s1"}
        },
        stage2_results={
            "defense_analyst": {"display_name": "Defense Analyst", "evaluation": "s2"}
        },
        aggregate_rankings=[
            {"display_name": "Defense Analyst", "avg_position": 1.0}
        ],
        matter_context=MATTER_CA,
    )
    assert HEADER_MARKER in prompt
    assert "California (state)" in prompt
    assert "Governing law:" in prompt


def test_unknown_jurisdiction_code_still_humanized():
    """A code we don't have a label for should still render, not crash."""
    persona = get_persona("defense_analyst")
    prompt = build_stage1_prompt(
        persona,
        "Q?",
        matter_context={"jurisdiction": "state-vt"},
    )
    assert HEADER_MARKER in prompt
    assert "State Vt" in prompt  # humanized fallback


def test_matter_context_with_only_jurisdiction():
    """Partial matter context: just jurisdiction, no name or practice area."""
    persona = get_persona("defense_analyst")
    prompt = build_stage1_prompt(
        persona,
        "Q?",
        matter_context={"jurisdiction": "state-ca"},
    )
    assert HEADER_MARKER in prompt
    assert "California (state)" in prompt
    assert "Name:" not in prompt
    assert "Practice area:" not in prompt
