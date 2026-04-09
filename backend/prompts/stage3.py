"""Stage 3: Lead Counsel synthesis prompt."""

from __future__ import annotations

from typing import Any

from ._shared import render_matter_header


_STAGE3_TEMPLATE = """\
{matter_header}You are the Lead Counsel for this matter. Multiple senior legal
strategists have independently analyzed the legal question and peer-reviewed
each other's work. Your role is to synthesize their collective wisdom into a
definitive strategy memorandum grounded in the governing law specified above
(if a MATTER CONTEXT block is present).

══════════════════════════════════════════════════════════
LEGAL QUESTION UNDER REVIEW:
{question}
══════════════════════════════════════════════════════════

DELIBERATION RECORD:

STAGE 1 — Independent Counsel Analyses:
{stage1_block}

STAGE 2 — Peer Evaluations:
{stage2_block}

STAGE 2 — AGGREGATE PEER RANKING (lower position = ranked higher by peers,
self-votes excluded):
{aggregate_block}

══════════════════════════════════════════════════════════

As Lead Counsel, prepare a FINAL STRATEGY MEMORANDUM using this structure:

# LEAD COUNSEL STRATEGY MEMORANDUM

## I. EXECUTIVE SUMMARY
3-4 sentences synthesizing the core issue, recommended approach, and key risks.

## II. CONSENSUS LEGAL ANALYSIS
### A. Governing Legal Framework
### B. Strength Assessment (integrating the team's strongest arguments)
### C. Vulnerabilities & Challenges (integrating the team's risk findings)

## III. STRATEGIC RECOMMENDATION (PRIMARY)
### Recommended Course of Action
### Implementation Plan

## IV. ALTERNATIVE STRATEGIES CONSIDERED

## V. RISK MATRIX & MITIGATION
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|

## VI. AREAS REQUIRING RESOLUTION
Disagreements among counsel, factual gaps, decisions needing client input.
Use the AGGREGATE PEER RANKING above to weight conflicting recommendations.

## VII. PRIORITIZED ACTION PLAN
**IMMEDIATE (0-7 days):**
**SHORT-TERM (7-30 days):**
**ONGOING/STRATEGIC:**

## VIII. CONCLUSION
One paragraph bottom-line.

---

IMPORTANT: This is the FINAL work product. Synthesize — do not just summarize.
Where counsel disagreed, give greater weight to the analyses that ranked
higher in the AGGREGATE PEER RANKING, but make a definitive call based on the
weight of legal authority and strategic considerations. Apply the governing
law specified in the MATTER CONTEXT, not generic federal common law."""


def build_stage3_prompt(
    question: str,
    stage1_results: dict[str, dict[str, Any]],
    stage2_results: dict[str, dict[str, Any]],
    aggregate_rankings: list[dict[str, Any]],
    matter_context: dict[str, str] | None = None,
) -> str:
    """Build the Lead Counsel synthesis prompt."""
    stage1_block = "\n\n".join(
        f"### {info['display_name']}\n{info['content']}"
        for info in stage1_results.values()
        if info.get("content")
    )
    stage2_block = "\n\n".join(
        f"### {info['display_name']} (evaluator)\n{info['evaluation']}"
        for info in stage2_results.values()
        if info.get("evaluation")
    )
    if aggregate_rankings:
        aggregate_block = "\n".join(
            f"{i + 1}. {r['display_name']} — avg position {r['avg_position']}"
            for i, r in enumerate(aggregate_rankings)
        )
    else:
        aggregate_block = (
            "(no aggregate ranking — Stage 2 produced no parseable ballots)"
        )

    return _STAGE3_TEMPLATE.format(
        matter_header=render_matter_header(matter_context),
        question=question,
        stage1_block=stage1_block,
        stage2_block=stage2_block,
        aggregate_block=aggregate_block,
    )
