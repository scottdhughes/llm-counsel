"""Tests for the Stage 2 ranking parser. Fail-closed semantics matter here."""

from __future__ import annotations

from backend.prompts.stage2 import parse_ranking


VALID_LABELS = {"A", "B", "C", "D"}


def test_parses_clean_ranking():
    text = """\
Response A is solid but lacks depth on procedural strategy.
Response B is comprehensive on risks.
Response C has practical recommendations.
Response D has the strongest authorities.

FINAL RANKING:
1. Response D
2. Response B
3. Response A
4. Response C
"""
    assert parse_ranking(text, VALID_LABELS) == ["D", "B", "A", "C"]


def test_returns_empty_when_header_missing():
    text = "1. Response A\n2. Response B\n3. Response C\n4. Response D"
    assert parse_ranking(text, VALID_LABELS) == []


def test_returns_empty_when_label_set_mismatched():
    """Model only ranked 3 of the 4 — fail closed, don't guess."""
    text = "FINAL RANKING:\n1. Response A\n2. Response B\n3. Response C"
    assert parse_ranking(text, VALID_LABELS) == []


def test_returns_empty_when_label_duplicated():
    text = (
        "FINAL RANKING:\n1. Response A\n2. Response A\n"
        "3. Response B\n4. Response C"
    )
    assert parse_ranking(text, VALID_LABELS) == []


def test_ignores_response_mentions_in_evaluation_body():
    """The body talks about Response A many times; only the FINAL RANKING block matters."""
    text = """\
Response A is the best because Response A is well-cited.
Response A also handles Response D's argument well.

FINAL RANKING:
1. Response B
2. Response C
3. Response A
4. Response D
"""
    assert parse_ranking(text, VALID_LABELS) == ["B", "C", "A", "D"]


def test_handles_extra_whitespace_in_ranking_lines():
    text = (
        "FINAL RANKING:\n"
        "  1.   Response A\n"
        "  2.   Response B\n"
        "  3.   Response C\n"
        "  4.   Response D"
    )
    assert parse_ranking(text, VALID_LABELS) == ["A", "B", "C", "D"]


def test_returns_empty_when_label_outside_valid_set():
    """Model invented Response E — fail closed."""
    text = (
        "FINAL RANKING:\n1. Response A\n2. Response B\n"
        "3. Response C\n4. Response E"
    )
    assert parse_ranking(text, VALID_LABELS) == []


# Codex-driven additions: non-sequential numbering + shrunken sets


def test_returns_empty_for_non_sequential_numbering():
    """1, 2, 4, 5 instead of 1, 2, 3, 4."""
    text = (
        "FINAL RANKING:\n1. Response A\n2. Response B\n"
        "4. Response C\n5. Response D"
    )
    assert parse_ranking(text, VALID_LABELS) == []


def test_returns_empty_when_invented_high_numbers():
    text = (
        "FINAL RANKING:\n9. Response A\n10. Response B\n"
        "11. Response C\n12. Response D"
    )
    assert parse_ranking(text, VALID_LABELS) == []


def test_parses_three_response_set_when_one_persona_failed():
    """When Stage 1 has 3 successes, parser must accept a 3-line ranking."""
    text = "FINAL RANKING:\n1. Response A\n2. Response B\n3. Response C"
    assert parse_ranking(text, {"A", "B", "C"}) == ["A", "B", "C"]


def test_parses_two_response_set():
    text = "FINAL RANKING:\n1. Response A\n2. Response B"
    assert parse_ranking(text, {"A", "B"}) == ["A", "B"]


def test_returns_empty_when_post_ranking_commentary_breaks_block():
    """A blank line followed by prose ends the ranking block."""
    text = (
        "FINAL RANKING:\n"
        "1. Response A\n"
        "2. Response B\n"
        "\n"
        "Note: I was unable to evaluate Response C and Response D fairly."
    )
    # Only 2 lines parsed but valid_labels requires 4 → fail closed
    assert parse_ranking(text, VALID_LABELS) == []
