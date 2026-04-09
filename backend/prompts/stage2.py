"""Stage 2: blind peer ranking prompt + ranking parser.

The parser is strict and fail-closed:
  - the FINAL RANKING: header must be present
  - exactly N response lines must follow, contiguous
  - line numbers must be 1..N in order
  - the label set must match the expected `valid_labels` exactly

If any condition fails, parse_ranking returns []. Bogus output never produces
a guessed ranking.
"""

from __future__ import annotations

import re

from ._shared import render_matter_header
from .personas import Persona


_STAGE2_TEMPLATE = """\
{matter_header}{persona_system_prompt}

You are evaluating different legal strategy analyses for this question:

QUESTION: {question}

Below are {n_responses} anonymized analyses from your colleagues. You do not
know which attorney wrote which. Evaluate them against the governing law
specified in the MATTER CONTEXT above (if present).

{anonymized_responses}

Your task:
1. Evaluate each of the {n_responses} responses individually from your
   perspective as {display_name}. For each, briefly assess:
   - Legal soundness and accuracy
   - Strength of strategic recommendations
   - Practical viability
   - Completeness of analysis

2. After your evaluations, provide a final ranking of all {n_responses}
   responses. The ranking section MUST appear EXACTLY in this format and
   nothing else:

FINAL RANKING:
{example_ranking}

Rules for the ranking section:
- Start with the literal line "FINAL RANKING:" (uppercase, with colon)
- Use exactly {n_responses} numbered lines, in order from 1 to {n_responses}
- Each line: "<number>. Response <letter>" — nothing else
- Each label must appear exactly once
- Do not add commentary inside the ranking section."""


# Capture line number AND label so we can validate the ordinal sequence.
_RANK_LINE_RE = re.compile(r"^\s*(\d+)\.\s*Response\s+([A-Z])\s*$")
_HEADER_RE = re.compile(r"^FINAL RANKING:\s*$", re.MULTILINE)


def build_stage2_prompt(
    persona: Persona,
    question: str,
    anonymized: list[tuple[str, str]],
    matter_context: dict[str, str] | None = None,
) -> str:
    """Build the Stage 2 ranking prompt with the right number of slots."""
    labels = [label for label, _ in anonymized]
    blocks = "\n\n".join(
        f"Response {label}:\n{content}" for label, content in anonymized
    )
    example_lines = "\n".join(
        f"{i + 1}. Response {labels[i]}" for i in range(len(labels))
    )
    return _STAGE2_TEMPLATE.format(
        matter_header=render_matter_header(matter_context),
        persona_system_prompt=persona.system_prompt,
        question=question,
        display_name=persona.display_name,
        anonymized_responses=blocks,
        n_responses=len(labels),
        example_ranking=example_lines,
    )


def parse_ranking(ranking_text: str, valid_labels: set[str]) -> list[str]:
    """Extract the ordered list of response labels.

    Returns labels in best-to-worst order, e.g. ["B", "A", "C", "D"].
    Returns an empty list if:
      - the FINAL RANKING: header is not present
      - fewer than len(valid_labels) numbered lines follow the header
      - the numbering is not a contiguous 1..N sequence
      - the label set doesn't exactly match `valid_labels`
    """
    header_match = _HEADER_RE.search(ranking_text)
    if not header_match:
        return []

    after_header = ranking_text[header_match.end():]
    n = len(valid_labels)

    # Walk lines after the header. Stop at the first non-blank, non-matching
    # line — prevents picking up "Response A" mentions in post-ranking prose.
    parsed: list[tuple[int, str]] = []
    for raw_line in after_header.splitlines():
        if raw_line.strip() == "":
            if not parsed:
                continue  # blank lines before the first numbered line are fine
            break  # blank line after ranking ends the block
        match = _RANK_LINE_RE.match(raw_line)
        if not match:
            break
        parsed.append((int(match.group(1)), match.group(2)))
        if len(parsed) == n:
            break

    if len(parsed) != n:
        return []

    numbers = [p[0] for p in parsed]
    labels = [p[1] for p in parsed]

    if numbers != list(range(1, n + 1)):
        return []
    if set(labels) != valid_labels:
        return []

    return labels
