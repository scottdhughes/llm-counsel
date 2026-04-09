"""3-stage legal counsel deliberation orchestration (persona-based)."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from .config import COUNSEL_TEAM, LEAD_COUNSEL_MODEL
from .errors import AllModelsFailedError
from .openrouter import query_model, query_models_parallel
from .prompts import (
    build_stage1_prompt,
    build_stage2_prompt,
    build_stage3_prompt,
    get_persona,
    parse_ranking,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Stage 1
# ──────────────────────────────────────────────────────────────────────────────

async def run_stage1(
    question: str,
    context: str | None,
    matter_context: dict[str, str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Collect persona-conditioned analyses in parallel.

    Returns a dict keyed by persona role. Each value has:
        role, display_name, model, content (str | None), error (str | None)

    Raises:
        AllModelsFailedError: every persona's model failed.
    """
    def messages_for(role: str) -> list[dict[str, str]]:
        persona = get_persona(role)
        prompt = build_stage1_prompt(persona, question, context, matter_context=matter_context)
        return [{"role": "user", "content": prompt}]

    results = await query_models_parallel(COUNSEL_TEAM, messages_for)

    output: dict[str, dict[str, Any]] = {}
    for role, result in results.items():
        persona = get_persona(role)
        if isinstance(result, Exception):
            logger.warning("stage1 %s failed: %s", role, result)
            output[role] = {
                "role": role,
                "display_name": persona.display_name,
                "model": COUNSEL_TEAM[role],
                "content": None,
                "error": str(result),
            }
        else:
            output[role] = {
                "role": role,
                "display_name": persona.display_name,
                "model": COUNSEL_TEAM[role],
                "content": result,
                "error": None,
            }

    if not any(r["content"] for r in output.values()):
        raise AllModelsFailedError("Every Stage 1 model failed")

    return output


# ──────────────────────────────────────────────────────────────────────────────
# Stage 2
# ──────────────────────────────────────────────────────────────────────────────

def _label_assignments(stage1: dict[str, dict[str, Any]]) -> dict[str, str]:
    """Assign anonymous labels (A, B, C, ...) to successful Stage 1 personas.

    Only successful analyses are labeled — a persona whose Stage 1 call failed
    doesn't get a label and isn't ranked.
    """
    successful = [
        role for role, info in stage1.items() if info["content"] is not None
    ]
    return {chr(65 + i): role for i, role in enumerate(successful)}


async def run_stage2(
    question: str,
    stage1: dict[str, dict[str, Any]],
    matter_context: dict[str, str] | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    """Run blind peer review.

    Returns (stage2_output, label_to_role). stage2_output is keyed by
    persona role (only those whose Stage 1 succeeded). label_to_role maps
    "A"/"B"/... to persona roles.
    """
    label_to_role = _label_assignments(stage1)
    valid_labels = set(label_to_role.keys())

    if len(valid_labels) < 2:
        # Not enough successful analyses for meaningful peer review.
        return {}, label_to_role

    anonymized = [
        (label, stage1[role]["content"])
        for label, role in label_to_role.items()
    ]

    def messages_for(role: str) -> list[dict[str, str]]:
        persona = get_persona(role)
        prompt = build_stage2_prompt(
            persona, question, anonymized, matter_context=matter_context
        )
        return [{"role": "user", "content": prompt}]

    # Only personas whose Stage 1 succeeded participate as evaluators.
    evaluator_assignments = {
        role: COUNSEL_TEAM[role] for role in label_to_role.values()
    }
    results = await query_models_parallel(evaluator_assignments, messages_for)

    output: dict[str, dict[str, Any]] = {}
    for role, result in results.items():
        persona = get_persona(role)
        base = {
            "role": role,
            "display_name": persona.display_name,
            "model": COUNSEL_TEAM[role],
        }
        if isinstance(result, Exception):
            logger.warning("stage2 %s failed: %s", role, result)
            output[role] = {
                **base,
                "evaluation": None,
                "ranking": [],
                "error": str(result),
            }
        else:
            ranking = parse_ranking(result, valid_labels)
            output[role] = {
                **base,
                "evaluation": result,
                "ranking": ranking,  # labels in best-to-worst order
                "error": None if ranking else "ranking parse failed",
            }

    return output, label_to_role


def aggregate_rankings(
    stage2: dict[str, dict[str, Any]],
    label_to_role: dict[str, str],
) -> list[dict[str, Any]]:
    """Compute aggregate rankings, excluding evaluators' self-votes.

    Each persona evaluates all responses (including their own anonymized
    output), but their vote for themselves is dropped before averaging. This
    is the simplest defense against self-preference leakage in persona-
    conditioned ranking.

    Returns a list sorted by avg_position ascending (best first).
    """
    role_to_label = {role: label for label, role in label_to_role.items()}
    positions: dict[str, list[int]] = defaultdict(list)

    for evaluator_role, evaluator_result in stage2.items():
        ranking = evaluator_result.get("ranking") or []
        evaluator_label = role_to_label.get(evaluator_role)
        for position, label in enumerate(ranking, start=1):
            if label == evaluator_label:
                continue  # drop self-votes
            if label in label_to_role:
                role = label_to_role[label]
                positions[role].append(position)

    aggregate = []
    for role, pos_list in positions.items():
        if not pos_list:
            continue
        persona = get_persona(role)
        aggregate.append({
            "role": role,
            "label": role_to_label[role],
            "display_name": persona.display_name,
            "avg_position": round(sum(pos_list) / len(pos_list), 2),
            "positions": pos_list,
        })

    aggregate.sort(key=lambda x: x["avg_position"])
    return aggregate


# ──────────────────────────────────────────────────────────────────────────────
# Stage 3
# ──────────────────────────────────────────────────────────────────────────────

async def run_stage3(
    question: str,
    stage1: dict[str, dict[str, Any]],
    stage2: dict[str, dict[str, Any]],
    aggregates: list[dict[str, Any]],
    matter_context: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Synthesize the final Lead Counsel memorandum.

    Returns either {model, content, error: None} on success or
    {model, content: None, error: str} on failure. Never raises — Lead
    Counsel failure must not discard upstream Stage 1 + Stage 2 work.
    """
    prompt = build_stage3_prompt(
        question, stage1, stage2, aggregates, matter_context=matter_context
    )
    try:
        content = await query_model(
            LEAD_COUNSEL_MODEL,
            [{"role": "user", "content": prompt}],
        )
    except Exception as exc:
        logger.error("lead counsel synthesis failed: %s", exc)
        return {
            "model": LEAD_COUNSEL_MODEL,
            "content": None,
            "error": str(exc),
        }

    return {
        "model": LEAD_COUNSEL_MODEL,
        "content": content,
        "error": None,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Full deliberation
# ──────────────────────────────────────────────────────────────────────────────

async def run_full_counsel(
    question: str,
    context: str | None = None,
    matter_context: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run the complete 3-stage deliberation.

    `matter_context` carries stable matter metadata (jurisdiction, practice
    area, name) that gets rendered into every stage's prompt. This keeps the
    governing-law choice explicit rather than letting each model re-infer it
    from the free-text case context.

    Raises AllModelsFailedError only if Stage 1 has zero successes. Lead
    Counsel failures are returned in-band as `stage3.error` so partial work
    is never discarded.
    """
    stage1 = await run_stage1(question, context, matter_context)
    stage2_results, label_to_role = await run_stage2(
        question, stage1, matter_context
    )
    aggregates = aggregate_rankings(stage2_results, label_to_role)
    stage3 = await run_stage3(
        question, stage1, stage2_results, aggregates, matter_context
    )

    return {
        "stage1": stage1,
        "stage2": {
            "assessments": stage2_results,
            "label_mapping": label_to_role,
            "aggregate_rankings": aggregates,
        },
        "stage3": stage3,
    }
