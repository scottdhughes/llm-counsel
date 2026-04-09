"""Stage 1: persona-conditioned initial legal analysis prompts."""

from __future__ import annotations

from ._shared import render_matter_header
from .personas import Persona


_STAGE1_TEMPLATE = """\
{matter_header}{persona_system_prompt}

LEGAL QUESTION:
{question}
{context_block}
Prepare a comprehensive LEGAL STRATEGY MEMORANDUM from your perspective as
{display_name}. Apply the governing law specified in the MATTER CONTEXT above
(if present). Use the following format:

## I. EXECUTIVE SUMMARY
Brief 2-3 sentence overview from your perspective.

## II. LEGAL FRAMEWORK & APPLICABLE LAW
- Relevant statutes, regulations, and case law
- Key legal principles and standards
- Jurisdictional considerations

## III. LEGAL ANALYSIS (your perspective)
A. Key issues, viewed through your lens ({focus_summary})
B. Strengths of position
C. Weaknesses & challenges

## IV. STRATEGIC RECOMMENDATIONS
A. Primary strategy
B. Alternative approaches
C. Tactical considerations specific to your area of focus

## V. RISK ASSESSMENT & MITIGATION
- Risks identified through your lens, with mitigation

## VI. ACTION ITEMS & NEXT STEPS
Priority-ordered list of immediate (7d), short-term (30d), and long-term actions.

Be specific, cite relevant authority where applicable, and stay in your
persona's lens. Other counsel will cover other angles."""


def build_stage1_prompt(
    persona: Persona,
    question: str,
    context: str | None = None,
    matter_context: dict[str, str] | None = None,
) -> str:
    """Render the Stage 1 prompt for a single persona."""
    context_block = f"\nCASE CONTEXT:\n{context}\n" if context else ""
    return _STAGE1_TEMPLATE.format(
        matter_header=render_matter_header(matter_context),
        persona_system_prompt=persona.system_prompt,
        question=question,
        context_block=context_block,
        display_name=persona.display_name,
        focus_summary=", ".join(persona.focus_areas),
    )
