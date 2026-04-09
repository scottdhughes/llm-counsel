"""Persona registry sanity tests."""

from __future__ import annotations

import pytest

from backend.config import COUNSEL_TEAM, LEAD_COUNSEL_MODEL
from backend.prompts import LEGAL_PERSONAS, get_persona, list_personas


REQUIRED_FIELDS = (
    "role",
    "display_name",
    "icon",
    "color",
    "focus_areas",
    "system_prompt",
)


def test_all_personas_have_required_fields():
    for role, persona in LEGAL_PERSONAS.items():
        for field in REQUIRED_FIELDS:
            assert getattr(persona, field), f"{role} missing {field}"
        assert persona.role == role


def test_persona_lookup_succeeds_for_known_role():
    p = get_persona("plaintiff_strategist")
    assert p.display_name == "Plaintiff's Strategist"


def test_persona_lookup_raises_for_unknown_role():
    with pytest.raises(KeyError, match="Unknown persona role"):
        get_persona("not_a_real_role")


def test_active_team_uses_registered_personas():
    """Every role in COUNSEL_TEAM must exist in the registry."""
    for role in COUNSEL_TEAM:
        assert role in LEGAL_PERSONAS, (
            f"COUNSEL_TEAM uses unregistered role: {role}"
        )


def test_active_team_has_at_least_two_personas():
    """Peer review requires at least 2 evaluators to be meaningful."""
    assert len(COUNSEL_TEAM) >= 2


def test_active_team_models_have_provider_prefix():
    for role, model in COUNSEL_TEAM.items():
        assert model.count("/") == 1, (
            f"{role} model not in provider/model form: {model}"
        )
    assert LEAD_COUNSEL_MODEL.count("/") == 1


def test_lead_counsel_family_choice_is_documented():
    """Cross-family diversity is the design goal. If Lead Counsel reuses an
    evaluator's model family, that's a deliberate tradeoff that should be
    explicit in this test — update it when COUNSEL_TEAM changes.
    """
    lead_family = LEAD_COUNSEL_MODEL.split("/")[0]
    evaluator_families = {m.split("/")[0] for m in COUNSEL_TEAM.values()}
    if lead_family in evaluator_families:
        # Explicit allowlist: update when COUNSEL_TEAM changes.
        assert lead_family in {"google", "anthropic"}, (
            f"Lead Counsel family {lead_family} reuses evaluator family — "
            "is this intentional?"
        )


def test_list_personas_returns_all():
    assert set(list_personas()) == set(LEGAL_PERSONAS.keys())
