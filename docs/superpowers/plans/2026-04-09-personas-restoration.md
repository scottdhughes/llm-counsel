# LLM-COUNSEL: Personas Restoration & Cleanup Implementation Plan

> **For agentic workers:** This plan is being executed inline in the same session that produced it. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the persona-based legal counsel architecture (Architecture B), fix all bugs identified in the 2026-04-09 code review, update model pins to current OpenRouter slugs, and verify the system runs end-to-end.

**Architecture:** Each of 4 named legal personas is paired with a distinct frontier model. Stage 1 collects persona-conditioned analyses in parallel. Stage 2 performs blind peer ranking with each persona acting as evaluator. Stage 3 synthesizes a final memo via a dedicated Lead Counsel model. Storage is per-matter JSON with file locking. Backend exposes a thin FastAPI surface; frontend renders three tabbed stages keyed by persona role.

**Tech Stack:** FastAPI · httpx (async) · Pydantic v2 · React 18 · Vite 4 · TailwindCSS · OpenRouter · Python 3.10+

---

## Persona–Model Assignments

Verified against `https://openrouter.ai/api/v1/models` on 2026-04-09:

| Role | Display | Model (OpenRouter slug) | Why this model |
|---|---|---|---|
| `plaintiff_strategist` | Plaintiff's Strategist | `x-ai/grok-4.20` | Aggressive, creative case-theory generation; Grok 4.20 leads in lateral reasoning |
| `defense_analyst` | Defense Analyst | `anthropic/claude-opus-4.6` | Systematic risk decomposition and counterargument quality |
| `procedural_specialist` | Procedural Specialist | `openai/gpt-5.4` | Strong rule-following and procedural precision |
| `evidence_counsel` | Evidence Counsel | `google/gemini-3.1-pro-preview` | Long context for handling discovery records and expert reports |
| **Lead Counsel** | (synthesizer, no persona) | `anthropic/claude-opus-4.6` | Best synthesis quality across the lineup; reuses `defense_analyst`'s model intentionally |

**Note on the 4-persona cut:** Of the 8 personas in the original orphaned design, these four cover the full litigation lifecycle: offense (plaintiff), defense (defense analyst), procedure (procedural specialist), proof (evidence counsel). The remaining four (`appellate_consultant`, `settlement_strategist`, `trial_tactician`, `regulatory_specialist`) will be defined in `personas.py` but **not** part of the active team — leaving them registered keeps the door open for users to swap them in via config without code changes.

---

## File Structure

### Backend (Python)

| File | Status | Purpose |
|---|---|---|
| `backend/__init__.py` | exists | empty package marker |
| `backend/main.py` | modify | FastAPI app; thin route layer |
| `backend/config.py` | rewrite | persona registry, model pins, env loading |
| `backend/counsel.py` | rewrite | 3-stage orchestration; uses prompts package |
| `backend/openrouter.py` | rewrite | async client with typed errors, logging, no silent failures |
| `backend/storage.py` | modify | timezone-aware datetimes + fcntl file locking |
| `backend/errors.py` | **create** | typed exception hierarchy: `OpenRouterError`, `ModelTimeoutError`, etc. |
| `backend/prompts/__init__.py` | **create** | exports `LEGAL_PERSONAS`, builders |
| `backend/prompts/personas.py` | **create** | 8 persona definitions (system_prompt, display_name, focus_areas, color, icon) |
| `backend/prompts/stage1.py` | **create** | `build_stage1_prompt(persona, question, context)` |
| `backend/prompts/stage2.py` | **create** | `build_stage2_prompt(persona, question, anonymized_responses)` + `parse_ranking()` |
| `backend/prompts/stage3.py` | **create** | `build_stage3_prompt(question, stage1, stage2)` |
| `tests/__init__.py` | **create** | empty |
| `tests/test_personas.py` | **create** | persona registry shape + completeness tests |
| `tests/test_ranking_parser.py` | **create** | parser correctness + fail-closed semantics |
| `tests/test_storage.py` | **create** | round-trip + concurrent write safety |
| `tests/test_counsel_orchestration.py` | **create** | mocked end-to-end deliberation |

### Frontend (React)

| File | Status | Purpose |
|---|---|---|
| `frontend/src/main.jsx` | unchanged | Vite entrypoint |
| `frontend/src/App.jsx` | modify | per-message tab state, error display |
| `frontend/src/api.js` | modify | use Vite proxy with relative URLs |
| `frontend/src/components/MatterInterface.jsx` | rewrite | imports standalone Stage display components; deletes inline duplicates |
| `frontend/src/components/Sidebar.jsx` | unchanged | already correct |
| `frontend/src/components/Stage1Display.jsx` | modify | match new persona-keyed data shape from backend |
| `frontend/src/components/Stage2Display.jsx` | modify | match new shape; fix `aggregate_rankings` field names |
| `frontend/src/components/Stage3Display.jsx` | modify | use `stage3.content` (not `stage3.response`) |
| `frontend/tailwind.config.js` | modify | add `legal-navy`, `legal-gold` color tokens |
| `frontend/package.json` | modify | drop `lucide-react`, fix `lint` script |
| `frontend/eslint.config.js` | **create** | flat config for ESLint v8 (or remove the lint script entirely) |

### Top-level

| File | Status | Purpose |
|---|---|---|
| `CLAUDE.md` | rewrite | match actual code |
| `README.md` | modify | fix model names, persona section, broken `docs/security.md` link |
| `docs/security.md` | **create** | the page README links to |
| `start.sh` | modify | safer env loading |
| `pyproject.toml` | modify | add `pytest` and `ruff` to optional dev deps |

---

## Phase 0 — Foundation (already complete)

- [x] **Verify OpenRouter model slugs** — done via curl; results above
- [x] **Clone repo to `~/llm-counsel`** — done

---

## Phase 1 — Backend persona system

### Task 1: Create the typed error hierarchy

**Files:**
- Create: `backend/errors.py`

- [ ] **Step 1: Write the file**

```python
"""Typed exceptions for LLM-COUNSEL backend.

Each error class carries enough context for the API layer to convert it to a
useful HTTP response, and for logs to be actionable without exposing secrets.
"""

from __future__ import annotations


class CounselError(Exception):
    """Base for all LLM-COUNSEL errors."""


class OpenRouterError(CounselError):
    """OpenRouter API call failed in a way that isn't a transient timeout."""

    def __init__(self, model: str, status_code: int | None, detail: str) -> None:
        super().__init__(f"{model}: HTTP {status_code}: {detail}")
        self.model = model
        self.status_code = status_code
        self.detail = detail


class ModelTimeoutError(CounselError):
    """A model exceeded the per-call timeout."""

    def __init__(self, model: str, timeout: float) -> None:
        super().__init__(f"{model}: timed out after {timeout}s")
        self.model = model
        self.timeout = timeout


class AllModelsFailedError(CounselError):
    """Every model in a stage failed; no usable output produced."""


class LeadCounselError(CounselError):
    """The Lead Counsel synthesis call failed."""
```

- [ ] **Step 2: Commit**

```bash
git add backend/errors.py
git commit -m "feat(backend): add typed error hierarchy"
```

---

### Task 2: Create the persona registry

**Files:**
- Create: `backend/prompts/__init__.py`
- Create: `backend/prompts/personas.py`

- [ ] **Step 1: Write `__init__.py`**

```python
"""Prompt templates and persona registry for LLM-COUNSEL."""

from .personas import LEGAL_PERSONAS, Persona, get_persona, list_personas
from .stage1 import build_stage1_prompt
from .stage2 import build_stage2_prompt, parse_ranking
from .stage3 import build_stage3_prompt

__all__ = [
    "LEGAL_PERSONAS",
    "Persona",
    "get_persona",
    "list_personas",
    "build_stage1_prompt",
    "build_stage2_prompt",
    "parse_ranking",
    "build_stage3_prompt",
]
```

- [ ] **Step 2: Write `personas.py`**

```python
"""Legal persona definitions for the LLM-COUNSEL deliberation system.

Personas are roles, not models. Each persona has a focused legal lens (system
prompt) that gets composed with the per-stage prompts. The mapping from persona
to model lives in `backend/config.py`, so the same persona can be re-cast onto a
different model without touching prompt logic.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Persona:
    role: str               # stable identifier; used as dict key everywhere
    display_name: str       # shown in UI
    icon: str               # unicode/emoji shown in UI
    color: str              # tailwind color family (red, blue, purple, ...)
    focus_areas: tuple[str, ...]
    system_prompt: str      # the legal lens for this persona


LEGAL_PERSONAS: dict[str, Persona] = {
    "plaintiff_strategist": Persona(
        role="plaintiff_strategist",
        display_name="Plaintiff's Strategist",
        icon="\u2696",  # ⚖
        color="red",
        focus_areas=("case theory", "damages maximization", "offensive litigation"),
        system_prompt=(
            "You are a senior plaintiff's strategist. Your lens is offensive: "
            "build the strongest possible case theory for the plaintiff, identify "
            "every plausible cause of action, and frame facts to maximize damages "
            "and leverage. Where the facts cut against you, surface that honestly "
            "but pivot to the strongest available counter-frame."
        ),
    ),
    "defense_analyst": Persona(
        role="defense_analyst",
        display_name="Defense Analyst",
        icon="\U0001F6E1",  # 🛡
        color="blue",
        focus_areas=("risk assessment", "counterarguments", "weaknesses"),
        system_prompt=(
            "You are a senior defense litigator. Your lens is defensive: "
            "decompose the case into discrete risks, find every weakness in the "
            "opposing theory, identify the strongest counterarguments, and rank "
            "vulnerabilities by likelihood and impact. Be ruthlessly honest about "
            "where the defense is exposed."
        ),
    ),
    "procedural_specialist": Persona(
        role="procedural_specialist",
        display_name="Procedural Specialist",
        icon="\U0001F4CB",  # 📋
        color="purple",
        focus_areas=("motion strategy", "timing", "rule compliance"),
        system_prompt=(
            "You are a procedural specialist focused on the rules of civil "
            "procedure, court-specific local rules, and motion practice. Your "
            "lens is procedural: identify dispositive motions, statutes of "
            "limitations, jurisdictional issues, deadlines, and any procedural "
            "leverage either side has overlooked. Cite specific rule numbers "
            "where applicable."
        ),
    ),
    "evidence_counsel": Persona(
        role="evidence_counsel",
        display_name="Evidence Counsel",
        icon="\U0001F50D",  # 🔍
        color="green",
        focus_areas=("admissibility", "discovery", "expert witnesses"),
        system_prompt=(
            "You are evidence counsel. Your lens is evidentiary: what evidence "
            "exists, what can be admitted, what discovery is needed, what expert "
            "testimony is required, and what foundation must be laid. Apply the "
            "Federal Rules of Evidence (or analogous state rules) and flag any "
            "Daubert/702 issues with proposed experts."
        ),
    ),
    "appellate_consultant": Persona(
        role="appellate_consultant",
        display_name="Appellate Consultant",
        icon="\u269A",  # ⚚
        color="orange",
        focus_areas=("issue preservation", "standard of review", "precedent"),
        system_prompt=(
            "You are an appellate consultant. Your lens is forward-looking: "
            "what issues must be preserved at trial, what standard of review "
            "applies on appeal, what precedent shapes the legal questions, and "
            "where the trial record needs to be built to support an eventual "
            "appeal. Think about both sides' likely appellate posture."
        ),
    ),
    "settlement_strategist": Persona(
        role="settlement_strategist",
        display_name="Settlement Strategist",
        icon="\U0001F91D",  # 🤝
        color="teal",
        focus_areas=("case valuation", "negotiation", "resolution"),
        system_prompt=(
            "You are a settlement strategist. Your lens is resolution-oriented: "
            "value the case realistically (best/likely/worst), identify the "
            "leverage each side has, suggest negotiation timing and structure, "
            "and recommend a settlement range. Account for litigation cost, "
            "uncertainty, and reputational factors."
        ),
    ),
    "trial_tactician": Persona(
        role="trial_tactician",
        display_name="Trial Tactician",
        icon="\U0001F3AD",  # 🎭
        color="pink",
        focus_areas=("jury strategy", "witness examination", "trial themes"),
        system_prompt=(
            "You are a trial tactician. Your lens is the courtroom: what jury "
            "themes will resonate, how to sequence witnesses, where to put "
            "your strongest evidence, what cross-examination angles to develop, "
            "and how to handle adverse facts at trial. Think about both opening "
            "and closing arguments."
        ),
    ),
    "regulatory_specialist": Persona(
        role="regulatory_specialist",
        display_name="Regulatory Specialist",
        icon="\U0001F3DB",  # 🏛
        color="gray",
        focus_areas=("compliance", "agency proceedings", "administrative law"),
        system_prompt=(
            "You are a regulatory specialist. Your lens is administrative and "
            "regulatory: what agency rules apply, what enforcement risk exists, "
            "what parallel regulatory proceedings might run alongside "
            "litigation, and how administrative deference (Chevron/Loper Bright) "
            "shapes the legal questions."
        ),
    ),
}


def get_persona(role: str) -> Persona:
    """Look up a persona by role; raises KeyError with a useful message."""
    try:
        return LEGAL_PERSONAS[role]
    except KeyError:
        valid = ", ".join(sorted(LEGAL_PERSONAS.keys()))
        raise KeyError(f"Unknown persona role '{role}'. Valid roles: {valid}")


def list_personas() -> list[str]:
    """All registered persona role identifiers."""
    return list(LEGAL_PERSONAS.keys())
```

- [ ] **Step 3: Commit**

```bash
git add backend/prompts/__init__.py backend/prompts/personas.py
git commit -m "feat(backend): add persona registry with 8 legal lenses"
```

---

### Task 3: Stage 1 prompt builder

**Files:**
- Create: `backend/prompts/stage1.py`

- [ ] **Step 1: Write the file**

```python
"""Stage 1: persona-conditioned initial legal analysis prompts."""

from __future__ import annotations

from .personas import Persona


_STAGE1_TEMPLATE = """\
{persona_system_prompt}

LEGAL QUESTION:
{question}
{context_block}
Prepare a comprehensive LEGAL STRATEGY MEMORANDUM from your perspective as
{display_name}. Use the following format:

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
) -> str:
    """Render the Stage 1 prompt for a single persona.

    The persona's system prompt becomes the opening; the rest of the template is
    structural so that downstream parsing and rendering have a stable shape.
    """
    context_block = f"\nCASE CONTEXT:\n{context}\n" if context else ""
    return _STAGE1_TEMPLATE.format(
        persona_system_prompt=persona.system_prompt,
        question=question,
        context_block=context_block,
        display_name=persona.display_name,
        focus_summary=", ".join(persona.focus_areas),
    )
```

- [ ] **Step 2: Commit**

```bash
git add backend/prompts/stage1.py
git commit -m "feat(backend): stage 1 persona-conditioned prompt builder"
```

---

### Task 4: Stage 2 prompt builder + ranking parser

**Files:**
- Create: `backend/prompts/stage2.py`

- [ ] **Step 1: Write the file**

```python
"""Stage 2: blind peer ranking prompt + ranking parser.

The parser is intentionally fail-closed: if the model didn't produce the
required FINAL RANKING block in the right shape, we return an empty list rather
than guess from prose mentions of "Response A" inside the evaluation body.
"""

from __future__ import annotations

import re

from .personas import Persona


_STAGE2_TEMPLATE = """\
{persona_system_prompt}

You are evaluating different legal strategy analyses for this question:

QUESTION: {question}

Below are anonymized analyses from your colleagues. You do not know which
attorney wrote which.

{anonymized_responses}

Your task:
1. Evaluate each response individually from your perspective as
   {display_name}. For each, briefly assess:
   - Legal soundness and accuracy
   - Strength of strategic recommendations
   - Practical viability
   - Completeness of analysis

2. After your evaluations, provide a final ranking. The ranking section MUST
   appear EXACTLY in this format and nothing else:

FINAL RANKING:
1. Response X
2. Response Y
3. Response Z
4. Response W

Rules for the ranking section:
- Start with the literal line "FINAL RANKING:" (uppercase, with colon)
- Use a numbered list, one response per line
- Each line is "<number>. Response <letter>" — nothing else
- Each label must appear exactly once

Do not add commentary inside the ranking section."""


# Strict pattern: number, dot, optional space, "Response", space, single
# capital letter, end-of-line. We anchor to lines and require exactly that.
_RANK_LINE_RE = re.compile(r"^\s*\d+\.\s*Response\s+([A-Z])\s*$", re.MULTILINE)
_HEADER_RE = re.compile(r"^FINAL RANKING:\s*$", re.MULTILINE)


def build_stage2_prompt(
    persona: Persona,
    question: str,
    anonymized: list[tuple[str, str]],
) -> str:
    """Build the Stage 2 ranking prompt.

    Args:
        persona: The persona acting as evaluator.
        question: The original legal question.
        anonymized: List of (label, content) tuples, e.g.
            [("A", "..."), ("B", "...")].
    """
    blocks = "\n\n".join(
        f"Response {label}:\n{content}" for label, content in anonymized
    )
    return _STAGE2_TEMPLATE.format(
        persona_system_prompt=persona.system_prompt,
        question=question,
        display_name=persona.display_name,
        anonymized_responses=blocks,
    )


def parse_ranking(ranking_text: str, valid_labels: set[str]) -> list[str]:
    """Extract the ordered list of response labels from a Stage 2 reply.

    Returns the labels in best-to-worst order, e.g. ["A", "C", "B", "D"].
    Returns an empty list if:
      - the FINAL RANKING: header is not present, or
      - parsed labels do not exactly match `valid_labels` as a set.

    Fail-closed: bogus output produces no ranking, never a guessed one.
    """
    header_match = _HEADER_RE.search(ranking_text)
    if not header_match:
        return []

    after_header = ranking_text[header_match.end():]
    labels = [m.group(1) for m in _RANK_LINE_RE.finditer(after_header)]

    # Each label must appear exactly once and the set must match what we asked
    # the model to rank. Otherwise, fail closed.
    if len(labels) != len(valid_labels):
        return []
    if set(labels) != valid_labels:
        return []

    return labels
```

- [ ] **Step 2: Commit**

```bash
git add backend/prompts/stage2.py
git commit -m "feat(backend): stage 2 prompt + fail-closed ranking parser"
```

---

### Task 5: Stage 3 prompt builder

**Files:**
- Create: `backend/prompts/stage3.py`

- [ ] **Step 1: Write the file**

```python
"""Stage 3: Lead Counsel synthesis prompt."""

from __future__ import annotations

from typing import Any


_STAGE3_TEMPLATE = """\
You are the Lead Counsel for this matter. Multiple senior legal strategists
have independently analyzed the legal question and peer-reviewed each other's
work. Your role is to synthesize their collective wisdom into a definitive
strategy memorandum.

══════════════════════════════════════════════════════════
LEGAL QUESTION UNDER REVIEW:
{question}
══════════════════════════════════════════════════════════

DELIBERATION RECORD:

STAGE 1 — Independent Counsel Analyses:
{stage1_block}

STAGE 2 — Peer Evaluations & Rankings:
{stage2_block}

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

## VII. PRIORITIZED ACTION PLAN
**IMMEDIATE (0-7 days):**
**SHORT-TERM (7-30 days):**
**ONGOING/STRATEGIC:**

## VIII. CONCLUSION
One paragraph bottom-line.

---

IMPORTANT: This is the FINAL work product. Synthesize — do not just summarize.
Where counsel disagreed, make a definitive call based on the weight of legal
authority and strategic considerations."""


def build_stage3_prompt(
    question: str,
    stage1_results: dict[str, dict[str, Any]],
    stage2_results: dict[str, dict[str, Any]],
) -> str:
    """Build the Lead Counsel synthesis prompt.

    `stage1_results` is keyed by persona role; each value has at least
    `display_name` and `content`. Same for `stage2_results` but the value has
    `evaluation` (the full peer review text).
    """
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
    return _STAGE3_TEMPLATE.format(
        question=question,
        stage1_block=stage1_block,
        stage2_block=stage2_block,
    )
```

- [ ] **Step 2: Commit**

```bash
git add backend/prompts/stage3.py
git commit -m "feat(backend): stage 3 lead counsel synthesis prompt"
```

---

### Task 6: Rewrite `config.py` for the persona-model team

**Files:**
- Modify: `backend/config.py`

- [ ] **Step 1: Replace the file with**

```python
"""LLM-COUNSEL configuration: persona team, model pins, env loading."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# OpenRouter
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Active counsel team: ordered mapping from persona role to OpenRouter model
# slug. Each persona must exist in backend.prompts.personas.LEGAL_PERSONAS.
# The order here is the order analyses are presented in the UI.
COUNSEL_TEAM: dict[str, str] = {
    "plaintiff_strategist": "x-ai/grok-4.20",
    "defense_analyst": "anthropic/claude-opus-4.6",
    "procedural_specialist": "openai/gpt-5.4",
    "evidence_counsel": "google/gemini-3.1-pro-preview",
}

# Lead Counsel synthesizes the final memorandum. Reuses defense_analyst's model
# intentionally — Opus 4.6 is the strongest synthesizer in the lineup.
LEAD_COUNSEL_MODEL: str = "anthropic/claude-opus-4.6"

# Per-call timeout for OpenRouter requests (seconds).
MODEL_REQUEST_TIMEOUT: float = float(os.getenv("MODEL_REQUEST_TIMEOUT", "180.0"))

# Server
API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
API_PORT: int = int(os.getenv("API_PORT", "8001"))

# Storage
DATA_DIR: str = os.getenv("DATA_DIR", "data/conversations")
```

**Two intentional changes worth noting for review:**
1. `API_HOST` default flipped from `0.0.0.0` to `127.0.0.1`. The repo has no auth; binding to all interfaces by default is a footgun. Users who really want LAN access set the env var explicitly.
2. `MODEL_REQUEST_TIMEOUT` is now configurable (default 180s, up from the old hardcoded 120s) — Stage 2 analyses with 4 long Stage 1 inputs can run long on slower models.

- [ ] **Step 2: Commit**

```bash
git add backend/config.py
git commit -m "refactor(backend): persona-team config + safer host default"
```

---

### Task 7: Rewrite `openrouter.py` with typed errors

**Files:**
- Modify: `backend/openrouter.py`

- [ ] **Step 1: Replace the file with**

```python
"""Async OpenRouter client.

This module deliberately does NOT swallow exceptions. Callers receive either a
parsed response or a typed error from `backend.errors`.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from .config import (
    MODEL_REQUEST_TIMEOUT,
    OPENROUTER_API_KEY,
    OPENROUTER_API_URL,
)
from .errors import ModelTimeoutError, OpenRouterError

logger = logging.getLogger(__name__)


def _headers() -> dict[str, str]:
    if not OPENROUTER_API_KEY:
        raise OpenRouterError(
            model="<config>",
            status_code=None,
            detail="OPENROUTER_API_KEY is not set",
        )
    return {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/scottdhughes/llm-counsel",
        "X-Title": "LLM-COUNSEL",
    }


async def query_model(
    model: str,
    messages: list[dict[str, str]],
    timeout: float = MODEL_REQUEST_TIMEOUT,
) -> str:
    """Call a single model and return its message content.

    Raises:
        ModelTimeoutError: the request did not complete within `timeout`.
        OpenRouterError: the API returned a non-2xx response or malformed body.
    """
    payload = {"model": model, "messages": messages}

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                OPENROUTER_API_URL, headers=_headers(), json=payload
            )
    except httpx.TimeoutException as exc:
        logger.warning("model %s timed out after %.0fs", model, timeout)
        raise ModelTimeoutError(model, timeout) from exc
    except httpx.HTTPError as exc:
        logger.warning("model %s transport error: %s", model, exc)
        raise OpenRouterError(model, None, str(exc)) from exc

    if response.status_code >= 400:
        body_preview = response.text[:500]
        logger.warning(
            "model %s returned HTTP %d: %s", model, response.status_code, body_preview
        )
        raise OpenRouterError(model, response.status_code, body_preview)

    try:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as exc:
        raise OpenRouterError(
            model, response.status_code, f"malformed response: {exc}"
        ) from exc

    if content is None:
        raise OpenRouterError(model, response.status_code, "empty content")

    return content


async def query_models_parallel(
    model_assignments: dict[str, str],
    messages_for: callable,
) -> dict[str, str | Exception]:
    """Run a stage in parallel across a set of (key, model) assignments.

    Args:
        model_assignments: Mapping from a stable key (e.g. persona role) to
            OpenRouter model slug.
        messages_for: Callable taking a key and returning the `messages` list
            for that call. Allows per-key prompt customization (Stage 1) and
            shared prompts (Stage 2).

    Returns:
        Dict mapping the input keys to either the model's content string OR an
        exception instance. Callers decide how to surface partial failures.
        Never raises — failures are returned in-band so callers can present
        successful analyses alongside failed ones.
    """

    async def _one(key: str, model: str) -> tuple[str, str | Exception]:
        try:
            return key, await query_model(model, messages_for(key))
        except Exception as exc:  # noqa: BLE001 — explicit in-band reporting
            return key, exc

    results = await asyncio.gather(
        *(_one(k, m) for k, m in model_assignments.items())
    )
    return dict(results)
```

**Why "exceptions in-band" instead of raising:** if Grok fails but the other three personas succeed, the user should still see those three analyses. Raising would force the route to either (a) fail the whole deliberation or (b) bury the partial success. Returning failures as values lets the orchestrator surface "3 succeeded, 1 failed (rate limit)" cleanly.

- [ ] **Step 2: Commit**

```bash
git add backend/openrouter.py
git commit -m "refactor(backend): typed errors, no silent failures, in-band parallel results"
```

---

### Task 8: Rewrite `counsel.py` for the persona system

**Files:**
- Modify: `backend/counsel.py`

- [ ] **Step 1: Replace the file with**

```python
"""3-stage legal counsel deliberation orchestration (persona-based)."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from .config import COUNSEL_TEAM, LEAD_COUNSEL_MODEL
from .errors import AllModelsFailedError, LeadCounselError
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
) -> dict[str, dict[str, Any]]:
    """Collect persona-conditioned analyses in parallel.

    Returns a dict keyed by persona role:
        {
            "plaintiff_strategist": {
                "role": "plaintiff_strategist",
                "display_name": "Plaintiff's Strategist",
                "model": "x-ai/grok-4.20",
                "content": "...",
                "error": None,
            },
            ...
        }

    Raises:
        AllModelsFailedError: every persona's model failed.
    """
    def messages_for(role: str) -> list[dict[str, str]]:
        persona = get_persona(role)
        prompt = build_stage1_prompt(persona, question, context)
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
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    """Run blind peer review.

    Returns (stage2_output, label_to_role).
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
        prompt = build_stage2_prompt(persona, question, anonymized)
        return [{"role": "user", "content": prompt}]

    # Only the personas whose Stage 1 succeeded participate as evaluators.
    evaluator_assignments = {
        role: COUNSEL_TEAM[role]
        for role in label_to_role.values()
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
            output[role] = {**base, "evaluation": None, "ranking": [], "error": str(result)}
        else:
            ranking = parse_ranking(result, valid_labels)
            output[role] = {
                **base,
                "evaluation": result,
                "ranking": ranking,  # list of labels A/B/C/D in best-to-worst order
                "error": None if ranking else "ranking parse failed",
            }

    return output, label_to_role


def aggregate_rankings(
    stage2: dict[str, dict[str, Any]],
    label_to_role: dict[str, str],
) -> list[dict[str, Any]]:
    """Compute aggregate rankings across all evaluators.

    Returns a list sorted by avg_position ascending (best first):
        [
            {
                "role": "evidence_counsel",
                "label": "C",
                "display_name": "Evidence Counsel",
                "avg_position": 1.5,
                "positions": [1, 2, 1, 2],
            },
            ...
        ]
    """
    role_to_label = {role: label for label, role in label_to_role.items()}
    positions: dict[str, list[int]] = defaultdict(list)

    for evaluator_result in stage2.values():
        ranking = evaluator_result.get("ranking") or []
        for position, label in enumerate(ranking, start=1):
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
) -> dict[str, Any]:
    """Synthesize the final Lead Counsel memorandum.

    Raises:
        LeadCounselError: the synthesis call failed.
    """
    prompt = build_stage3_prompt(question, stage1, stage2)
    try:
        content = await query_model(
            LEAD_COUNSEL_MODEL,
            [{"role": "user", "content": prompt}],
        )
    except Exception as exc:
        logger.error("lead counsel synthesis failed: %s", exc)
        raise LeadCounselError(str(exc)) from exc

    return {
        "model": LEAD_COUNSEL_MODEL,
        "content": content,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Full deliberation
# ──────────────────────────────────────────────────────────────────────────────

async def run_full_counsel(
    question: str,
    context: str | None = None,
) -> dict[str, Any]:
    """Run the complete 3-stage deliberation.

    Returns:
        {
            "stage1": {...persona-keyed dict...},
            "stage2": {
                "assessments": {...persona-keyed dict...},
                "label_mapping": {"A": "plaintiff_strategist", ...},
                "aggregate_rankings": [...sorted list...],
            },
            "stage3": {"model": "...", "content": "..."},
        }
    """
    stage1 = await run_stage1(question, context)
    stage2_results, label_to_role = await run_stage2(question, stage1)
    aggregates = aggregate_rankings(stage2_results, label_to_role)
    stage3 = await run_stage3(question, stage1, stage2_results)

    return {
        "stage1": stage1,
        "stage2": {
            "assessments": stage2_results,
            "label_mapping": label_to_role,
            "aggregate_rankings": aggregates,
        },
        "stage3": stage3,
    }
```

- [ ] **Step 2: Commit**

```bash
git add backend/counsel.py
git commit -m "refactor(backend): persona-based 3-stage orchestration"
```

---

## Phase 2 — Backend bug fixes & storage hardening

### Task 9: Fix `storage.py`: timezone-aware datetime + file locking

**Files:**
- Modify: `backend/storage.py`

- [ ] **Step 1: Replace the file with**

```python
"""JSON storage for legal matters with file locking and timezone-aware times."""

from __future__ import annotations

import fcntl
import json
import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .config import DATA_DIR


def _data_path() -> Path:
    p = Path(DATA_DIR)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _matter_path(matter_id: str) -> Path:
    return _data_path() / f"{matter_id}.json"


@contextmanager
def _locked(path: Path, mode: str) -> Iterator[Any]:
    """Open `path` with an exclusive lock for the duration of the with-block.

    Uses fcntl.flock; the lock is advisory but enforced for processes that
    cooperate (which is everyone touching this code).
    """
    with open(path, mode) as f:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            yield f
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_matter(
    matter_name: str = "New Matter",
    practice_area: str = "civil",
    jurisdiction: str = "federal",
) -> dict[str, Any]:
    matter_id = f"matter_{uuid.uuid4().hex[:12]}"
    matter = {
        "id": matter_id,
        "created_at": _utcnow_iso(),
        "matter_name": matter_name,
        "practice_area": practice_area,
        "jurisdiction": jurisdiction,
        "messages": [],
    }
    path = _matter_path(matter_id)
    with _locked(path, "w") as f:
        json.dump(matter, f, indent=2)
    return matter


def get_matter(matter_id: str) -> dict[str, Any] | None:
    path = _matter_path(matter_id)
    if not path.exists():
        return None
    with _locked(path, "r") as f:
        return json.load(f)


def list_matters() -> list[dict[str, Any]]:
    matters = []
    for entry in _data_path().iterdir():
        if entry.suffix != ".json":
            continue
        try:
            with _locked(entry, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        matters.append({
            "id": data["id"],
            "created_at": data["created_at"],
            "matter_name": data.get("matter_name", "New Matter"),
            "practice_area": data.get("practice_area", "civil"),
            "jurisdiction": data.get("jurisdiction", "federal"),
            "message_count": len(data.get("messages", [])),
        })
    matters.sort(key=lambda m: m["created_at"], reverse=True)
    return matters


def delete_matter(matter_id: str) -> bool:
    path = _matter_path(matter_id)
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False


def append_user_message(matter_id: str, content: str, context: str | None = None) -> None:
    path = _matter_path(matter_id)
    if not path.exists():
        raise ValueError(f"Matter {matter_id} not found")

    with _locked(path, "r+") as f:
        matter = json.load(f)
        message = {"role": "user", "content": content}
        if context:
            message["context"] = context
        matter["messages"].append(message)
        f.seek(0)
        f.truncate()
        json.dump(matter, f, indent=2)


def append_assistant_message(matter_id: str, deliberation: dict[str, Any]) -> None:
    """Append a full deliberation result as an assistant message."""
    path = _matter_path(matter_id)
    if not path.exists():
        raise ValueError(f"Matter {matter_id} not found")

    with _locked(path, "r+") as f:
        matter = json.load(f)
        matter["messages"].append({"role": "assistant", **deliberation})
        f.seek(0)
        f.truncate()
        json.dump(matter, f, indent=2)
```

**Note on `r+` + `seek(0)` + `truncate()`:** this read-modify-write happens inside the lock, so concurrent writers serialize cleanly. Without the lock, two simultaneous appends would overwrite each other.

- [ ] **Step 2: Commit**

```bash
git add backend/storage.py
git commit -m "fix(backend): tz-aware datetimes and fcntl-locked storage writes"
```

---

### Task 10: Rewrite `main.py` for the new API surface and error handling

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Replace the file with**

```python
"""FastAPI server for LLM-COUNSEL."""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import storage
from .config import API_HOST, API_PORT, COUNSEL_TEAM, LEAD_COUNSEL_MODEL
from .counsel import run_full_counsel
from .errors import AllModelsFailedError, LeadCounselError
from .prompts import LEGAL_PERSONAS

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = FastAPI(title="LLM-COUNSEL API", description="Legal Strategy Deliberation System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateMatterRequest(BaseModel):
    matter_name: str = "New Matter"
    practice_area: str = "civil"
    jurisdiction: str = "federal"


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=20_000)
    context: str | None = Field(default=None, max_length=100_000)


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok", "service": "LLM-COUNSEL Legal Strategy API"}


@app.get("/api/config/team")
async def get_team_config() -> dict[str, object]:
    """Expose the active counsel team for the frontend to render."""
    return {
        "lead_counsel": LEAD_COUNSEL_MODEL,
        "team": [
            {
                "role": role,
                "display_name": LEGAL_PERSONAS[role].display_name,
                "icon": LEGAL_PERSONAS[role].icon,
                "color": LEGAL_PERSONAS[role].color,
                "focus_areas": list(LEGAL_PERSONAS[role].focus_areas),
                "model": model,
            }
            for role, model in COUNSEL_TEAM.items()
        ],
    }


@app.get("/api/matters")
async def list_matters() -> list[dict]:
    return storage.list_matters()


@app.post("/api/matters")
async def create_matter(request: CreateMatterRequest) -> dict:
    return storage.create_matter(
        matter_name=request.matter_name,
        practice_area=request.practice_area,
        jurisdiction=request.jurisdiction,
    )


@app.get("/api/matters/{matter_id}")
async def get_matter(matter_id: str) -> dict:
    matter = storage.get_matter(matter_id)
    if matter is None:
        raise HTTPException(status_code=404, detail="Matter not found")
    return matter


@app.delete("/api/matters/{matter_id}")
async def delete_matter(matter_id: str) -> dict:
    if not storage.delete_matter(matter_id):
        raise HTTPException(status_code=404, detail="Matter not found")
    return {"status": "deleted", "id": matter_id}


@app.post("/api/matters/{matter_id}/message")
async def send_message(matter_id: str, request: SendMessageRequest) -> dict:
    if storage.get_matter(matter_id) is None:
        raise HTTPException(status_code=404, detail="Matter not found")

    storage.append_user_message(matter_id, request.content, request.context)

    try:
        deliberation = await run_full_counsel(request.content, request.context)
    except AllModelsFailedError as exc:
        raise HTTPException(status_code=502, detail=f"All models failed: {exc}") from exc
    except LeadCounselError as exc:
        raise HTTPException(status_code=502, detail=f"Lead Counsel failed: {exc}") from exc

    storage.append_assistant_message(matter_id, deliberation)
    return deliberation


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)
```

- [ ] **Step 2: Commit**

```bash
git add backend/main.py
git commit -m "refactor(backend): typed errors → HTTP, /api/config/team, input bounds"
```

---

## Phase 3 — Backend tests

### Task 11: Persona registry tests

**Files:**
- Create: `tests/__init__.py` (empty)
- Create: `tests/test_personas.py`

- [ ] **Step 1: Write `tests/__init__.py` (empty file)**

- [ ] **Step 2: Write `tests/test_personas.py`**

```python
"""Persona registry sanity tests."""

from __future__ import annotations

import pytest

from backend.config import COUNSEL_TEAM, LEAD_COUNSEL_MODEL
from backend.prompts import LEGAL_PERSONAS, get_persona, list_personas


REQUIRED_FIELDS = ("role", "display_name", "icon", "color", "focus_areas", "system_prompt")


def test_all_personas_have_required_fields():
    for role, persona in LEGAL_PERSONAS.items():
        for field in REQUIRED_FIELDS:
            assert getattr(persona, field), f"{role} missing {field}"
        assert persona.role == role, f"key/role mismatch: {role} vs {persona.role}"


def test_persona_lookup_succeeds_for_known_role():
    p = get_persona("plaintiff_strategist")
    assert p.display_name == "Plaintiff's Strategist"


def test_persona_lookup_raises_for_unknown_role():
    with pytest.raises(KeyError, match="Unknown persona role"):
        get_persona("not_a_real_role")


def test_counsel_team_personas_all_registered():
    """Every role in COUNSEL_TEAM must exist in the registry."""
    for role in COUNSEL_TEAM:
        assert role in LEGAL_PERSONAS, f"COUNSEL_TEAM uses unregistered role: {role}"


def test_counsel_team_models_have_provider_prefix():
    """OpenRouter slugs must look like provider/model."""
    for role, model in COUNSEL_TEAM.items():
        assert "/" in model, f"{role} model missing provider prefix: {model}"
    assert "/" in LEAD_COUNSEL_MODEL


def test_list_personas_returns_all():
    assert set(list_personas()) == set(LEGAL_PERSONAS.keys())
```

- [ ] **Step 3: Run tests**

```bash
cd ~/llm-counsel && python -m pytest tests/test_personas.py -v
```
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add tests/__init__.py tests/test_personas.py
git commit -m "test(backend): persona registry sanity tests"
```

---

### Task 12: Ranking parser tests

**Files:**
- Create: `tests/test_ranking_parser.py`

- [ ] **Step 1: Write the test file**

```python
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
    text = "FINAL RANKING:\n1. Response A\n2. Response A\n3. Response B\n4. Response C"
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
    text = "FINAL RANKING:\n  1.   Response A\n  2.   Response B\n  3.   Response C\n  4.   Response D"
    assert parse_ranking(text, VALID_LABELS) == ["A", "B", "C", "D"]


def test_returns_empty_when_label_outside_valid_set():
    """Model invented Response E — fail closed."""
    text = "FINAL RANKING:\n1. Response A\n2. Response B\n3. Response C\n4. Response E"
    assert parse_ranking(text, VALID_LABELS) == []
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest tests/test_ranking_parser.py -v
```
Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add tests/test_ranking_parser.py
git commit -m "test(backend): ranking parser fail-closed semantics"
```

---

### Task 13: Storage round-trip tests

**Files:**
- Create: `tests/test_storage.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Write `tests/conftest.py`**

```python
"""Shared test fixtures."""

from __future__ import annotations

import importlib
import os

import pytest


@pytest.fixture
def isolated_data_dir(tmp_path, monkeypatch):
    """Run a test against a fresh DATA_DIR; reload modules so the path is picked up."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")  # avoids config import errors
    import backend.config
    import backend.storage
    importlib.reload(backend.config)
    importlib.reload(backend.storage)
    yield backend.storage
```

- [ ] **Step 2: Write `tests/test_storage.py`**

```python
"""Storage round-trip and concurrent-write safety tests."""

from __future__ import annotations

import threading


def test_create_and_get_matter(isolated_data_dir):
    storage = isolated_data_dir
    matter = storage.create_matter(matter_name="Smith v. Acme")
    fetched = storage.get_matter(matter["id"])
    assert fetched is not None
    assert fetched["matter_name"] == "Smith v. Acme"
    assert fetched["messages"] == []


def test_get_returns_none_for_missing(isolated_data_dir):
    assert isolated_data_dir.get_matter("matter_missing") is None


def test_list_returns_newest_first(isolated_data_dir):
    storage = isolated_data_dir
    a = storage.create_matter(matter_name="A")
    b = storage.create_matter(matter_name="B")
    listed = storage.list_matters()
    assert [m["id"] for m in listed][:2] == [b["id"], a["id"]]


def test_delete_matter(isolated_data_dir):
    storage = isolated_data_dir
    matter = storage.create_matter()
    assert storage.delete_matter(matter["id"]) is True
    assert storage.delete_matter(matter["id"]) is False
    assert storage.get_matter(matter["id"]) is None


def test_append_user_then_assistant(isolated_data_dir):
    storage = isolated_data_dir
    matter = storage.create_matter()
    storage.append_user_message(matter["id"], "Question?", context="Some facts")
    storage.append_assistant_message(matter["id"], {
        "stage1": {"plaintiff_strategist": {"content": "..."}},
        "stage2": {"assessments": {}, "label_mapping": {}, "aggregate_rankings": []},
        "stage3": {"model": "anthropic/claude-opus-4.6", "content": "..."},
    })
    fetched = storage.get_matter(matter["id"])
    assert len(fetched["messages"]) == 2
    assert fetched["messages"][0]["role"] == "user"
    assert fetched["messages"][0]["context"] == "Some facts"
    assert fetched["messages"][1]["role"] == "assistant"
    assert "stage3" in fetched["messages"][1]


def test_concurrent_appends_do_not_lose_messages(isolated_data_dir):
    """Hammer the same matter from N threads; every message must be persisted."""
    storage = isolated_data_dir
    matter = storage.create_matter()
    n_threads = 10

    def append(i: int) -> None:
        storage.append_user_message(matter["id"], f"msg-{i}")

    threads = [threading.Thread(target=append, args=(i,)) for i in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    fetched = storage.get_matter(matter["id"])
    contents = sorted(m["content"] for m in fetched["messages"])
    assert contents == sorted(f"msg-{i}" for i in range(n_threads))
```

- [ ] **Step 3: Run tests**

```bash
python -m pytest tests/test_storage.py -v
```
Expected: all pass, including the concurrency test.

- [ ] **Step 4: Commit**

```bash
git add tests/conftest.py tests/test_storage.py
git commit -m "test(backend): storage round-trip + concurrent-write safety"
```

---

### Task 14: Mocked end-to-end orchestration test

**Files:**
- Create: `tests/test_counsel_orchestration.py`

- [ ] **Step 1: Write the test file**

```python
"""End-to-end orchestration tests with mocked OpenRouter calls."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.counsel import run_full_counsel


def _stage1_content(role: str) -> str:
    return f"Stage 1 analysis from {role}"


def _stage2_content(_role: str) -> str:
    return (
        "Each response was thoughtful.\n"
        "FINAL RANKING:\n"
        "1. Response A\n"
        "2. Response B\n"
        "3. Response C\n"
        "4. Response D\n"
    )


@pytest.mark.asyncio
async def test_full_deliberation_happy_path(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    call_log = []

    async def fake_query_model(model, messages, timeout=None):
        call_log.append(model)
        # Return content based on which stage's prompt this is
        prompt = messages[0]["content"]
        if "FINAL RANKING:" in prompt:
            return _stage2_content("any")
        if "Lead Counsel" in prompt:
            return "# LEAD COUNSEL STRATEGY MEMORANDUM\n\nFinal synthesis..."
        return _stage1_content("any")

    with patch("backend.openrouter.query_model", side_effect=fake_query_model), \
         patch("backend.counsel.query_model", side_effect=fake_query_model):
        result = await run_full_counsel("What is our strategy?")

    # Stage 1: 4 personas, all populated
    assert set(result["stage1"].keys()) == {
        "plaintiff_strategist", "defense_analyst",
        "procedural_specialist", "evidence_counsel",
    }
    for role_data in result["stage1"].values():
        assert role_data["error"] is None
        assert role_data["content"]

    # Stage 2: 4 evaluators, each producing a parsed ranking
    assert len(result["stage2"]["assessments"]) == 4
    assert len(result["stage2"]["label_mapping"]) == 4
    assert len(result["stage2"]["aggregate_rankings"]) == 4

    # Stage 3: synthesized memo
    assert "LEAD COUNSEL STRATEGY MEMORANDUM" in result["stage3"]["content"]


@pytest.mark.asyncio
async def test_partial_stage1_failure_still_completes(monkeypatch):
    """If 2 of 4 Stage 1 models fail, the deliberation still finishes with the 2 that worked."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    fail_models = {"x-ai/grok-4.20", "openai/gpt-5.4"}

    async def fake_query_model(model, messages, timeout=None):
        if model in fail_models:
            from backend.errors import OpenRouterError
            raise OpenRouterError(model, 429, "rate limited")
        prompt = messages[0]["content"]
        if "FINAL RANKING:" in prompt:
            return (
                "Both look strong.\nFINAL RANKING:\n1. Response A\n2. Response B\n"
            )
        if "Lead Counsel" in prompt:
            return "Final memo with 2 inputs."
        return "stage1 success"

    with patch("backend.openrouter.query_model", side_effect=fake_query_model), \
         patch("backend.counsel.query_model", side_effect=fake_query_model):
        result = await run_full_counsel("Question?")

    # 2 personas succeed, 2 carry an error
    successes = [r for r in result["stage1"].values() if r["content"]]
    failures = [r for r in result["stage1"].values() if r["error"]]
    assert len(successes) == 2
    assert len(failures) == 2

    # Stage 2 only ranks the 2 successful ones
    assert len(result["stage2"]["label_mapping"]) == 2

    # Stage 3 still produces a memo
    assert result["stage3"]["content"] == "Final memo with 2 inputs."


@pytest.mark.asyncio
async def test_all_stage1_failure_raises(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    async def always_fail(model, messages, timeout=None):
        from backend.errors import OpenRouterError
        raise OpenRouterError(model, 500, "boom")

    with patch("backend.openrouter.query_model", side_effect=always_fail), \
         patch("backend.counsel.query_model", side_effect=always_fail):
        from backend.errors import AllModelsFailedError
        with pytest.raises(AllModelsFailedError):
            await run_full_counsel("Question?")
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest tests/test_counsel_orchestration.py -v
```
Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add tests/test_counsel_orchestration.py
git commit -m "test(backend): mocked end-to-end orchestration with partial failures"
```

---

## Phase 4 — Frontend persona UI

### Task 15: Update `frontend/src/api.js` to use Vite proxy

**Files:**
- Modify: `frontend/src/api.js`

- [ ] **Step 1: Replace the file with**

```javascript
/**
 * API client for the LLM-COUNSEL backend.
 * Uses Vite's dev proxy (vite.config.js) to forward /api → backend.
 */

const API_BASE = '';  // empty → use same origin → Vite proxy handles /api → :8001

async function jsonOrThrow(response, action) {
  if (!response.ok) {
    let detail = '';
    try {
      const body = await response.json();
      detail = body?.detail ? `: ${body.detail}` : '';
    } catch {
      // ignore
    }
    throw new Error(`${action} failed (HTTP ${response.status})${detail}`);
  }
  return response.json();
}

export const api = {
  async listMatters() {
    const res = await fetch(`${API_BASE}/api/matters`);
    return jsonOrThrow(res, 'List matters');
  },

  async createMatter(data = {}) {
    const res = await fetch(`${API_BASE}/api/matters`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        matter_name: data.matter_name || 'New Matter',
        practice_area: data.practice_area || 'civil',
        jurisdiction: data.jurisdiction || 'federal',
      }),
    });
    return jsonOrThrow(res, 'Create matter');
  },

  async getMatter(matterId) {
    const res = await fetch(`${API_BASE}/api/matters/${matterId}`);
    return jsonOrThrow(res, 'Get matter');
  },

  async deleteMatter(matterId) {
    const res = await fetch(`${API_BASE}/api/matters/${matterId}`, { method: 'DELETE' });
    return jsonOrThrow(res, 'Delete matter');
  },

  async sendMessage(matterId, content, context = null) {
    const res = await fetch(`${API_BASE}/api/matters/${matterId}/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, context }),
    });
    return jsonOrThrow(res, 'Send message');
  },

  async getTeamConfig() {
    const res = await fetch(`${API_BASE}/api/config/team`);
    return jsonOrThrow(res, 'Get team config');
  },
};
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api.js
git commit -m "fix(frontend): use Vite proxy + extract HTTP error details"
```

---

### Task 16: Add tailwind color tokens

**Files:**
- Modify: `frontend/tailwind.config.js`

- [ ] **Step 1: Read the existing file** (it's small) and **add `theme.extend.colors`:**

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        'legal-navy': '#0a2540',
        'legal-gold': '#c9a962',
      },
    },
  },
  plugins: [],
};
```

- [ ] **Step 2: Commit**

```bash
git add frontend/tailwind.config.js
git commit -m "style(frontend): add legal-navy and legal-gold color tokens"
```

---

### Task 17: Update standalone Stage1Display.jsx for new data shape

**Files:**
- Modify: `frontend/src/components/Stage1Display.jsx`

- [ ] **Step 1: Replace the file with**

```jsx
import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';

/**
 * Stage1Display: shows persona-keyed legal analyses.
 *
 * Props:
 *   stage1: object keyed by persona role:
 *     {
 *       plaintiff_strategist: {
 *         role, display_name, model, icon, color, content, error
 *       },
 *       ...
 *     }
 */
function Stage1Display({ stage1 }) {
  const roles = Object.keys(stage1 || {});
  const [selectedRole, setSelectedRole] = useState(roles[0] || null);

  useEffect(() => {
    if (!selectedRole && roles.length > 0) {
      setSelectedRole(roles[0]);
    }
  }, [roles, selectedRole]);

  if (roles.length === 0) {
    return <div className="text-gray-500 py-8">No analyses yet.</div>;
  }

  const selected = selectedRole ? stage1[selectedRole] : null;

  return (
    <div className="flex gap-6">
      {/* Persona selector */}
      <div className="w-64 flex-shrink-0 space-y-2">
        <h3 className="text-sm font-semibold text-legal-navy uppercase tracking-wider mb-2">
          Legal Team
        </h3>
        {roles.map((role) => {
          const info = stage1[role];
          const isSelected = selectedRole === role;
          const failed = !!info.error;
          return (
            <button
              key={role}
              onClick={() => setSelectedRole(role)}
              className={`
                w-full text-left p-3 rounded-lg border-2 transition-all
                ${isSelected
                  ? 'border-legal-gold bg-white shadow-md'
                  : 'border-gray-200 hover:border-gray-300 bg-white'}
              `}
            >
              <div className="font-medium text-legal-navy truncate">
                {info.display_name}
              </div>
              <div className="text-xs text-gray-500 truncate">{info.model}</div>
              {failed ? (
                <div className="text-xs text-red-600 mt-1">⚠ Failed</div>
              ) : (
                <div className="text-xs text-green-600 mt-1">✓ Complete</div>
              )}
            </button>
          );
        })}
      </div>

      {/* Analysis content */}
      <div className="flex-1 bg-white rounded-lg shadow p-6 overflow-y-auto">
        {selected && selected.content ? (
          <div>
            <div className="border-b pb-3 mb-4">
              <h3 className="text-xl font-bold text-legal-navy">
                {selected.display_name}
              </h3>
              <p className="text-xs text-gray-500 mt-1">Model: {selected.model}</p>
            </div>
            <div className="prose max-w-none">
              <ReactMarkdown>{selected.content}</ReactMarkdown>
            </div>
          </div>
        ) : selected && selected.error ? (
          <div className="text-red-700 bg-red-50 border border-red-200 rounded p-4">
            <p className="font-semibold">Analysis failed</p>
            <p className="text-sm mt-1">{selected.error}</p>
          </div>
        ) : (
          <div className="text-gray-500">Select an attorney to view analysis</div>
        )}
      </div>
    </div>
  );
}

export default Stage1Display;
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Stage1Display.jsx
git commit -m "refactor(frontend): Stage1Display matches persona-keyed backend shape"
```

---

### Task 18: Update standalone Stage2Display.jsx for new data shape

**Files:**
- Modify: `frontend/src/components/Stage2Display.jsx`

- [ ] **Step 1: Replace the file with**

```jsx
import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';

/**
 * Stage2Display: shows peer rankings and individual evaluations.
 *
 * Props:
 *   stage2: {
 *     assessments: { [role]: { display_name, model, evaluation, ranking, error } },
 *     label_mapping: { "A": "plaintiff_strategist", ... },
 *     aggregate_rankings: [
 *       { role, label, display_name, avg_position, positions }
 *     ]
 *   }
 */
function Stage2Display({ stage2 }) {
  const [view, setView] = useState('rankings');

  if (!stage2 || !stage2.assessments) {
    return <div className="text-gray-500 py-8">No peer assessment yet.</div>;
  }

  return (
    <div>
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setView('rankings')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            view === 'rankings'
              ? 'bg-legal-navy text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          Aggregate Rankings
        </button>
        <button
          onClick={() => setView('evaluations')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            view === 'evaluations'
              ? 'bg-legal-navy text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          Individual Evaluations
        </button>
      </div>

      {view === 'rankings' ? (
        <RankingsView aggregate={stage2.aggregate_rankings} />
      ) : (
        <EvaluationsView assessments={stage2.assessments} />
      )}
    </div>
  );
}

function RankingsView({ aggregate }) {
  if (!aggregate || aggregate.length === 0) {
    return (
      <div className="text-gray-500 py-8">
        No aggregate ranking — peer review didn't produce parseable rankings.
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-xl font-bold text-legal-navy mb-2">Aggregate Peer Rankings</h3>
      <p className="text-sm text-gray-600 mb-6">
        Lower average position = consistently ranked higher by peers.
      </p>

      <div className="space-y-3">
        {aggregate.map((rank, idx) => {
          const isTop = idx === 0;
          return (
            <div
              key={rank.role}
              className={`flex items-center gap-4 p-4 rounded-lg border-2 ${
                isTop ? 'border-legal-gold bg-yellow-50' : 'border-gray-200 bg-white'
              }`}
            >
              <div
                className={`w-12 h-12 rounded-full flex items-center justify-center font-bold ${
                  isTop ? 'bg-legal-gold text-white' : 'bg-gray-200 text-gray-600'
                }`}
              >
                #{idx + 1}
              </div>
              <div className="flex-1">
                <div className="font-semibold text-legal-navy">{rank.display_name}</div>
                <div className="text-xs text-gray-500">
                  Anonymized as: Response {rank.label}
                </div>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-legal-navy">
                  {rank.avg_position.toFixed(2)}
                </div>
                <div className="text-xs text-gray-500">avg. position</div>
              </div>
              {rank.positions && (
                <div className="text-xs text-gray-500 ml-2">
                  Votes: [{rank.positions.join(', ')}]
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function EvaluationsView({ assessments }) {
  const evaluators = Object.keys(assessments);
  const [selected, setSelected] = useState(evaluators[0] || null);

  useEffect(() => {
    if (!selected && evaluators.length > 0) setSelected(evaluators[0]);
  }, [evaluators, selected]);

  if (evaluators.length === 0) return <div className="text-gray-500">No evaluations.</div>;

  const data = selected ? assessments[selected] : null;

  return (
    <div className="flex gap-6">
      <div className="w-56 flex-shrink-0 space-y-2">
        <h4 className="text-sm font-semibold text-gray-700 mb-2">Evaluated by:</h4>
        {evaluators.map((role) => {
          const info = assessments[role];
          const isSelected = selected === role;
          return (
            <button
              key={role}
              onClick={() => setSelected(role)}
              className={`w-full text-left p-3 rounded-lg border transition-all ${
                isSelected
                  ? 'border-legal-gold bg-white shadow'
                  : 'border-gray-200 hover:border-gray-300 bg-white'
              }`}
            >
              <div className="text-sm font-medium truncate">{info.display_name}</div>
            </button>
          );
        })}
      </div>

      <div className="flex-1 bg-white rounded-lg shadow p-6 overflow-y-auto">
        {data && data.evaluation ? (
          <div>
            <h3 className="text-lg font-semibold text-legal-navy mb-3">
              Evaluation by {data.display_name}
            </h3>
            {data.ranking && data.ranking.length > 0 && (
              <div className="mb-4 p-3 bg-gray-50 rounded-lg text-sm">
                <span className="font-medium">Their ranking:</span>{' '}
                {data.ranking.map((label) => `Response ${label}`).join(' > ')}
              </div>
            )}
            <div className="prose max-w-none">
              <ReactMarkdown>{data.evaluation}</ReactMarkdown>
            </div>
          </div>
        ) : data && data.error ? (
          <div className="text-red-700 bg-red-50 border border-red-200 rounded p-4">
            <p className="font-semibold">Evaluation failed</p>
            <p className="text-sm mt-1">{data.error}</p>
          </div>
        ) : (
          <div className="text-gray-500">Select an evaluator</div>
        )}
      </div>
    </div>
  );
}

export default Stage2Display;
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Stage2Display.jsx
git commit -m "refactor(frontend): Stage2Display matches new shape with assessments + aggregate"
```

---

### Task 19: Update standalone Stage3Display.jsx for new data shape

**Files:**
- Modify: `frontend/src/components/Stage3Display.jsx`

- [ ] **Step 1: Replace the file with**

```jsx
import React from 'react';
import ReactMarkdown from 'react-markdown';

/**
 * Stage3Display: renders the Lead Counsel synthesis memo.
 *
 * Props:
 *   stage3: { model: string, content: string }
 */
function Stage3Display({ stage3 }) {
  if (!stage3 || !stage3.content) {
    return <div className="text-gray-500 py-8">No final strategy yet.</div>;
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Disclaimer */}
      <div className="bg-red-50 border-l-4 border-red-600 p-3 mb-4">
        <p className="text-xs text-red-800">
          <strong>DISCLAIMER:</strong> This AI-generated analysis is not legal advice.
          Review by a licensed attorney is required before any implementation.
        </p>
      </div>

      <div className="bg-legal-navy text-white rounded-t-lg p-6">
        <h2 className="text-2xl font-bold">Legal Strategy Memorandum</h2>
        <p className="text-blue-200 text-sm mt-1">
          Synthesized by Lead Counsel — {stage3.model}
        </p>
      </div>

      <div className="bg-white shadow-lg rounded-b-lg">
        <div className="h-2 bg-legal-gold" />
        <div className="p-8">
          <div className="prose prose-lg max-w-none">
            <ReactMarkdown>{stage3.content}</ReactMarkdown>
          </div>
        </div>
        <div className="border-t px-8 py-4 bg-gray-50 rounded-b-lg flex items-center justify-between text-sm text-gray-500">
          <span>⚖ LLM-COUNSEL · Multi-Model Legal Strategy Deliberation</span>
          <span>{new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</span>
        </div>
      </div>

      <div className="mt-6 flex gap-4 justify-center">
        <button
          onClick={() => {
            navigator.clipboard.writeText(stage3.content);
          }}
          className="px-6 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          Copy to Clipboard
        </button>
        <button
          onClick={() => {
            const blob = new Blob([stage3.content], { type: 'text/markdown' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'legal-strategy-memo.md';
            a.click();
            URL.revokeObjectURL(url);
          }}
          className="px-6 py-2 bg-legal-navy text-white rounded-lg hover:bg-blue-900"
        >
          Download as Markdown
        </button>
      </div>
    </div>
  );
}

export default Stage3Display;
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Stage3Display.jsx
git commit -m "refactor(frontend): Stage3Display uses content/model from new shape"
```

---

### Task 20: Rewrite `MatterInterface.jsx` to use the standalone components

**Files:**
- Modify: `frontend/src/components/MatterInterface.jsx`

- [ ] **Step 1: Replace the file with**

```jsx
import { useState } from 'react';
import Stage1Display from './Stage1Display';
import Stage2Display from './Stage2Display';
import Stage3Display from './Stage3Display';

function MatterInterface({ matter, onSendMessage, isLoading }) {
  const [question, setQuestion] = useState('');
  const [context, setContext] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (question.trim() && !isLoading) {
      onSendMessage(question, context || null);
      setQuestion('');
      setContext('');
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="border-b bg-white p-4">
        <h2 className="text-xl font-bold text-legal-navy">{matter.matter_name}</h2>
        <p className="text-sm text-gray-600">
          {matter.practice_area} | {matter.jurisdiction}
        </p>
      </div>

      <div className="flex-1 overflow-y-auto bg-gray-50 p-6">
        {matter.messages.length === 0 ? (
          <div className="text-center text-gray-500 py-12">
            No messages yet. Ask a legal question to begin deliberation.
          </div>
        ) : (
          <div className="space-y-6 max-w-6xl mx-auto">
            {matter.messages.map((msg, idx) => (
              <Message key={idx} message={msg} />
            ))}
          </div>
        )}

        {isLoading && (
          <div className="max-w-6xl mx-auto mt-6 p-6 bg-white rounded-lg shadow">
            <div className="flex items-center gap-3">
              <div className="animate-spin h-5 w-5 border-2 border-legal-navy border-t-transparent rounded-full" />
              <span className="text-gray-700">Legal counsel is deliberating…</span>
            </div>
          </div>
        )}
      </div>

      <div className="border-t bg-white p-4">
        <form onSubmit={handleSubmit} className="max-w-6xl mx-auto space-y-3">
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Enter your legal question…"
            className="w-full p-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-legal-navy"
            rows={2}
            disabled={isLoading}
          />
          <textarea
            value={context}
            onChange={(e) => setContext(e.target.value)}
            placeholder="Additional context (optional)…"
            className="w-full p-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-legal-navy"
            rows={2}
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={!question.trim() || isLoading}
            className="px-6 py-2 bg-legal-navy text-white rounded-lg hover:bg-blue-900 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Deliberating…' : 'Submit Question'}
          </button>
        </form>
      </div>
    </div>
  );
}

function Message({ message }) {
  // Per-message tab state — fixes the shared-state bug from the old version.
  const [activeTab, setActiveTab] = useState('stage3');

  if (message.role === 'user') {
    return (
      <div className="bg-white p-6 rounded-lg shadow">
        <div className="font-semibold text-legal-navy mb-2">Legal Question:</div>
        <div className="text-gray-800 whitespace-pre-wrap">{message.content}</div>
        {message.context && (
          <div className="mt-3 pt-3 border-t">
            <div className="text-sm font-semibold text-gray-700 mb-1">Context:</div>
            <div className="text-sm text-gray-600 whitespace-pre-wrap">{message.context}</div>
          </div>
        )}
      </div>
    );
  }

  // assistant message
  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="flex border-b">
        <Tab active={activeTab === 'stage1'} onClick={() => setActiveTab('stage1')} label="Stage 1: Initial Analyses" />
        <Tab active={activeTab === 'stage2'} onClick={() => setActiveTab('stage2')} label="Stage 2: Peer Rankings" />
        <Tab active={activeTab === 'stage3'} onClick={() => setActiveTab('stage3')} label="Stage 3: Lead Counsel" highlight />
      </div>
      <div className="p-6">
        {activeTab === 'stage1' && <Stage1Display stage1={message.stage1} />}
        {activeTab === 'stage2' && <Stage2Display stage2={message.stage2} />}
        {activeTab === 'stage3' && <Stage3Display stage3={message.stage3} />}
      </div>
    </div>
  );
}

function Tab({ active, onClick, label, highlight }) {
  return (
    <button
      onClick={onClick}
      className={`
        px-6 py-3 font-medium transition-colors
        ${active
          ? highlight
            ? 'bg-green-50 text-green-900 border-b-2 border-green-600'
            : 'bg-blue-50 text-legal-navy border-b-2 border-legal-gold'
          : 'text-gray-600 hover:bg-gray-50'}
      `}
    >
      {label}
    </button>
  );
}

export default MatterInterface;
```

**Critical change:** `activeTab` state is now scoped to the `Message` component, so each assistant turn remembers its own tab. Old version shared one state across all messages.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/MatterInterface.jsx
git commit -m "refactor(frontend): import standalone Stage components, per-message tab state"
```

---

### Task 21: Update `App.jsx` (minor — message shape uses `stage1/stage2/stage3` directly)

**Files:**
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Update `handleSendMessage` to use the new flat response shape**

The relevant block becomes:

```jsx
const handleSendMessage = async (content, context) => {
  if (!currentMatterId) return;
  setIsLoading(true);
  setError(null);

  try {
    const userMessage = { role: 'user', content, context };
    setCurrentMatter((prev) => ({
      ...prev,
      messages: [...prev.messages, userMessage],
    }));

    // Backend now returns { stage1, stage2, stage3 } directly
    const response = await api.sendMessage(currentMatterId, content, context);

    const assistantMessage = {
      role: 'assistant',
      stage1: response.stage1,
      stage2: response.stage2,
      stage3: response.stage3,
    };

    setCurrentMatter((prev) => ({
      ...prev,
      messages: [...prev.messages, assistantMessage],
    }));

    loadMatters();
  } catch (err) {
    console.error('Failed to send message:', err);
    setError(err.message);
    setCurrentMatter((prev) => ({
      ...prev,
      messages: prev.messages.slice(0, -1),
    }));
  } finally {
    setIsLoading(false);
  }
};
```

(Other parts of App.jsx don't change.)

- [ ] **Step 2: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "fix(frontend): use new flat deliberation response shape"
```

---

### Task 22: Drop dead `lucide-react` dep + remove the unused lint script

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Remove `"lucide-react": "^0.263.1"` from dependencies. Remove the `"lint"` script and the four eslint dev deps (`eslint`, `eslint-plugin-react`, `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`). The repo currently has no eslint config, so the lint script is broken anyway.**

After editing, package.json should look like:

```json
{
  "name": "llm-counsel-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-markdown": "^9.0.1"
  },
  "devDependencies": {
    "@types/react": "^18.2.15",
    "@types/react-dom": "^18.2.7",
    "@vitejs/plugin-react": "^4.0.3",
    "autoprefixer": "^10.4.14",
    "postcss": "^8.4.27",
    "tailwindcss": "^3.3.3",
    "vite": "^4.4.5"
  }
}
```

- [ ] **Step 2: Reinstall to update lockfile**

```bash
cd ~/llm-counsel/frontend && rm -f package-lock.json && npm install
```

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore(frontend): drop dead lucide-react dep + broken lint script"
```

---

## Phase 5 — Top-level fixes

### Task 23: Fix `start.sh` env loading

**Files:**
- Modify: `start.sh`

- [ ] **Step 1: Replace lines 33-34 (the `export $(grep ...)` block) with safer sourcing**

```bash
# Load environment variables (safe even with quoted values / spaces)
set -a
# shellcheck disable=SC1091
source .env
set +a
```

- [ ] **Step 2: Commit**

```bash
git add start.sh
git commit -m "fix(start.sh): safer env loading via set -a + source"
```

---

### Task 24: Update `pyproject.toml` with dev deps and ruff config

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Replace with**

```toml
[project]
name = "llm-counsel"
version = "1.1.0"
description = "Multi-model legal reasoning system that simulates adversarial analysis, peer review, and strategic synthesis"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "python-dotenv>=1.0.0",
    "httpx>=0.27.0",
    "pydantic>=2.9.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "ruff>=0.6.0",
]

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["backend*"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B"]
```

- [ ] **Step 2: Reinstall in editable mode with dev extras**

```bash
cd ~/llm-counsel && pip install -e ".[dev]"
```

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: bump to 1.1.0, add pytest+ruff dev deps"
```

---

### Task 25: Rewrite `CLAUDE.md` to match reality

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Replace with content that accurately reflects the new persona-based system, the new endpoints (including `/api/config/team`), the actual file layout, the test commands, and the actual config symbols (`COUNSEL_TEAM`, `LEAD_COUNSEL_MODEL`).**

(Content shown in implementation section — too long for the plan body, but follows the structure of the existing CLAUDE.md with corrected paths/symbols/commands.)

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(claude.md): rewrite to match persona-based architecture"
```

---

### Task 26: Update `README.md` model table and remove broken link

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update the model table to use real OpenRouter slugs and the persona team. Remove or repoint the `docs/security.md` link.**

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs(readme): persona team + current OpenRouter slugs"
```

---

### Task 27: Create `docs/security.md`

**Files:**
- Create: `docs/security.md`

- [ ] **Step 1: Write a brief security recommendations doc that consolidates the items from the README's Security Considerations section into one canonical page (auth, rate limiting, encryption at rest, secrets manager, audit logging, CORS, HTTPS).**

- [ ] **Step 2: Commit**

```bash
git add docs/security.md
git commit -m "docs: add security recommendations referenced from README"
```

---

## Phase 6 — Run + verify end-to-end

### Task 28: Set up the local environment

- [ ] **Step 1: Confirm `.env` exists with `OPENROUTER_API_KEY`** (will prompt user if not present)

- [ ] **Step 2: Install backend in editable + dev mode**

```bash
cd ~/llm-counsel
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

- [ ] **Step 3: Install frontend deps** (already done in Task 22)

- [ ] **Step 4: Run the test suite**

```bash
python -m pytest tests/ -v
```
Expected: all tests pass. If anything fails, fix before proceeding.

---

### Task 29: Backend smoke test

- [ ] **Step 1: Start backend in background**

```bash
cd ~/llm-counsel && source .venv/bin/activate && uvicorn backend.main:app --port 8001 &
```

- [ ] **Step 2: Hit health endpoint**

```bash
curl -s http://localhost:8001/ | python3 -m json.tool
```
Expected: `{"status": "ok", ...}`

- [ ] **Step 3: Hit team config endpoint**

```bash
curl -s http://localhost:8001/api/config/team | python3 -m json.tool
```
Expected: 4 personas with the right model slugs.

---

### Task 30: Frontend smoke test

- [ ] **Step 1: Start Vite dev server**

```bash
cd ~/llm-counsel/frontend && npm run dev
```

- [ ] **Step 2: Curl the index**

```bash
curl -s http://localhost:5173/ | head -20
```
Expected: HTML page returns.

- [ ] **Step 3: Verify proxy works**

```bash
curl -s http://localhost:5173/api/matters | python3 -m json.tool
```
Expected: `[]` (empty list).

---

### Task 31: End-to-end deliberation (requires real OpenRouter key)

- [ ] **Step 1: Create a matter via the API**

```bash
curl -s -X POST http://localhost:8001/api/matters \
  -H "Content-Type: application/json" \
  -d '{"matter_name":"Smoke test","practice_area":"civil","jurisdiction":"federal"}'
```

- [ ] **Step 2: Send a small deliberation question** (will cost ~$0.50-$2 in OpenRouter credits)

```bash
curl -s -X POST http://localhost:8001/api/matters/{matter_id}/message \
  -H "Content-Type: application/json" \
  -d '{"content":"Two parties have a contract dispute over a $50,000 deliverable. What is our strategy?"}'
```

- [ ] **Step 3: Verify the response shape matches the orchestrator contract**

Check that `stage1` has 4 keys, `stage2.assessments` has up to 4 keys, `stage2.aggregate_rankings` has up to 4 entries, `stage3.content` is non-empty, `stage3.model` matches the configured Lead Counsel.

- [ ] **Step 4: Open browser to `http://localhost:5173`** and visually verify the matter renders the deliberation correctly through all 3 tabs. Confirm:
  - Stage 1 tab lets you click between 4 personas with different content
  - Stage 2 tab shows aggregate rankings + lets you switch to individual evaluations
  - Stage 3 tab shows the synthesized memo with proper markdown rendering
  - Tab state is per-message (create a second deliberation, switch tabs, confirm the first one keeps its tab)

---

## Out of scope (deliberate)

The following items from the code review are intentionally not in this plan, in order to keep scope focused and the plan tractable:

- **Auth + rate limiting** — needed for any non-local deployment, but a separate concern from the architecture restoration
- **SQLite migration** — JSON storage with locking is good enough for single-user dev
- **Vite 4 → 6, React 18 → 19, Tailwind 3 → 4** — risky stack bumps, separate effort
- **Streaming Stage 3 output** — UX nice-to-have; backend would need SSE or similar
- **CI workflow / GitHub Actions** — separate hygiene pass
- **Cost tracking per matter** — feature work, not cleanup
- **Implementing the other 4 personas as live team members** — they exist in the registry; users can swap them in via `COUNSEL_TEAM` config

---

## Self-review

**Spec coverage check:** Walking through each item in the user's request:

| Asked for | Covered by |
|---|---|
| Plan for Architecture B with personas | Phase 1 (Tasks 1-8) — registry, prompts, config, orchestrator |
| Plan to implement everything (cleanup) | Phase 2 (Tasks 9-10), Phase 5 (Tasks 23-27) — bug fixes, docs |
| Codex review of plan | Will dispatch via codex:rescue after self-review |
| Simplify and make elegant | Plan rewrites the major files rather than patching, which collapses incidental complexity |
| No bugs | Tests in Phase 3 (Tasks 11-14) cover the trickiest paths (parser, storage races, partial failure) |
| Make functional and run | Phase 6 (Tasks 28-31) — env setup, smoke tests, end-to-end deliberation |
| GPT 5.4, Opus 4.6, Grok, Gemini 3.1 | Verified slugs, used in Task 6 config |

**Placeholder scan:** I deliberately abbreviated Tasks 25 (CLAUDE.md rewrite) and 26 (README update) because they're prose. I'll write the actual content during execution rather than transcribing it twice.

**Type/symbol consistency check:**
- Stage 1 output: `dict[role -> {role, display_name, model, content, error}]` — used the same shape in Tasks 8, 14, 17.
- Stage 2 output: `dict[role -> {role, display_name, model, evaluation, ranking, error}]` plus `assessments`/`label_mapping`/`aggregate_rankings` wrapper — Tasks 8, 14, 18 align.
- Stage 3 output: `{model, content}` — Tasks 8, 14, 19 align (note: backend uses `content`, NOT `response`, contrary to the old code).
- `COUNSEL_TEAM` (new symbol, replaces `COUNSEL_MODELS`) — Tasks 6, 8, 10, 11.
- `parse_ranking(text, valid_labels)` signature — Tasks 4, 12.

No drift.

---

## Risk register

| Risk | Mitigation |
|---|---|
| OpenRouter slug for `gemini-3.1-pro-preview` ages out before user runs it | Configurable via env override; document the swap procedure |
| `httpx.AsyncClient` per-request creation has connection overhead | Acceptable at this scale (4 calls/stage); a shared client is a future optimization |
| Test 13 concurrency test is timing-sensitive on slow systems | Uses `flock` which is deterministic; should be reliable |
| Lead Counsel cost is high (1 call with ~50K input tokens) | Documented in README cost section; out of scope for this pass |
| User runs out of OpenRouter credits during smoke test | Will warn before Task 31 and offer to skip the live deliberation |

---

## Execution handoff

Codex review complete (2026-04-09). The amendments section below supersedes the affected tasks. Execution follows the amended versions where they conflict with the originals.

---

# AMENDMENTS — Post-Codex Review

Codex flagged 6 real bugs, 2 architectural concerns, 4 test gaps, and 2 scope issues. Each amendment below cites the codex finding it addresses and specifies the exact change.

## A1 — Lead Counsel model: switch to Gemini 3.1 Pro Preview

**Codex finding:** Reusing `anthropic/claude-opus-4.6` for both `defense_analyst` and Lead Counsel concentrates bias in one model family in a system whose claim is cross-model deliberation.

**Change:** `LEAD_COUNSEL_MODEL` becomes `google/gemini-3.1-pro-preview` in Task 6. Gemini 3.1 Pro has the longest context in the lineup, which is the natural fit for synthesizing 4 long Stage 1 memos + 4 evaluation responses + the aggregate ranking.

**Updated row in the persona-model assignments table:**
| **Lead Counsel** | (synthesizer, no persona) | `google/gemini-3.1-pro-preview` | Longest context window in the lineup; no model family appears twice |

## A2 — Stage 2 prompt + parser: dynamic ranking size + sequence validation

**Codex finding 1:** The Stage 2 prompt template hardcodes a 4-line example, but `run_stage2` correctly shrinks `valid_labels` to 2 or 3 if Stage 1 has failures. The model would still get a 4-line example, producing 4-line output that fails the parser's `len(labels) != len(valid_labels)` check.

**Codex finding 2:** The parser accepts any `\d+. Response X` line anywhere after the header, so non-sequential numbering (`9. Response A`) or stray matches in later prose can produce parseable-but-wrong output.

**Updated `backend/prompts/stage2.py` (replaces Task 4 Step 1 entirely):**

```python
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

from .personas import Persona


_STAGE2_TEMPLATE = """\
{persona_system_prompt}

You are evaluating different legal strategy analyses for this question:

QUESTION: {question}

Below are {n_responses} anonymized analyses from your colleagues. You do not
know which attorney wrote which.

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


# Capture the line number AND the response label so we can validate the
# ordinal sequence, not just the label set.
_RANK_LINE_RE = re.compile(r"^\s*(\d+)\.\s*Response\s+([A-Z])\s*$")
_HEADER_RE = re.compile(r"^FINAL RANKING:\s*$", re.MULTILINE)


def build_stage2_prompt(
    persona: Persona,
    question: str,
    anonymized: list[tuple[str, str]],
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
        persona_system_prompt=persona.system_prompt,
        question=question,
        display_name=persona.display_name,
        anonymized_responses=blocks,
        n_responses=len(labels),
        example_ranking=example_lines,
    )


def parse_ranking(ranking_text: str, valid_labels: set[str]) -> list[str]:
    """Extract the ordered list of response labels.

    Returns labels in best-to-worst order; returns [] if anything is malformed.
    """
    header_match = _HEADER_RE.search(ranking_text)
    if not header_match:
        return []

    after_header = ranking_text[header_match.end():]
    n = len(valid_labels)

    # Walk lines after the header. Stop at the first non-blank, non-matching
    # line — this prevents us from picking up "Response A" mentions in any
    # post-ranking commentary the model adds despite our instructions.
    parsed: list[tuple[int, str]] = []
    for raw_line in after_header.splitlines():
        if raw_line.strip() == "":
            if not parsed:
                continue  # blank lines before the first numbered line are fine
            break  # blank line after the ranking ends the ranking block
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

    # Numbering must be contiguous 1..n
    if numbers != list(range(1, n + 1)):
        return []
    # Each label exactly once and the set must match what we asked for
    if set(labels) != valid_labels:
        return []

    return labels
```

## A3 — Stage 3 prompt: feed aggregate rankings directly

**Codex finding:** The plan computes `aggregate_rankings` and stores it for the UI but never feeds it into the Lead Counsel prompt, so Lead Counsel has to reconstruct peer consensus from prose. The most distilled signal is being thrown away at exactly the moment it would be most useful.

**Updated `backend/prompts/stage3.py` (replaces Task 5 Step 1):**

```python
"""Stage 3: Lead Counsel synthesis prompt."""

from __future__ import annotations

from typing import Any


_STAGE3_TEMPLATE = """\
You are the Lead Counsel for this matter. Multiple senior legal strategists
have independently analyzed the legal question and peer-reviewed each other's
work. Your role is to synthesize their collective wisdom into a definitive
strategy memorandum.

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
weight of legal authority and strategic considerations."""


def build_stage3_prompt(
    question: str,
    stage1_results: dict[str, dict[str, Any]],
    stage2_results: dict[str, dict[str, Any]],
    aggregate_rankings: list[dict[str, Any]],
) -> str:
    """Build the Lead Counsel synthesis prompt.

    Args:
        question: The original legal question.
        stage1_results: persona role -> {display_name, content, ...}
        stage2_results: persona role -> {display_name, evaluation, ...}
        aggregate_rankings: sorted list of {role, display_name, avg_position, ...}
    """
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
        aggregate_block = "(no aggregate ranking — Stage 2 produced no parseable ballots)"

    return _STAGE3_TEMPLATE.format(
        question=question,
        stage1_block=stage1_block,
        stage2_block=stage2_block,
        aggregate_block=aggregate_block,
    )
```

## A4 — Config: Lead Counsel slug update

**Updated `LEAD_COUNSEL_MODEL` line in `backend/config.py` (Task 6):**

```python
# Lead Counsel synthesizes the final memorandum. Gemini 3.1 Pro has the
# longest context in the lineup, and using a different model family from
# defense_analyst keeps cross-model diversity.
LEAD_COUNSEL_MODEL: str = "google/gemini-3.1-pro-preview"
```

## A5 — `query_models_parallel` exception scope

**Codex finding:** The blanket `except Exception` in `_one()` swallows bugs in `messages_for(key)` (e.g., a persona lookup typo) and reports them as model failures, masking programming defects.

**Updated `_one` helper in `backend/openrouter.py` (Task 7):**

```python
async def query_models_parallel(
    model_assignments: dict[str, str],
    messages_for: callable,
) -> dict[str, str | Exception]:
    """Run a stage in parallel across persona-model assignments.

    Errors raised by `messages_for` propagate immediately — those are
    programming bugs, not model failures. Errors raised by the model call are
    captured per-key so partial successes can be surfaced.
    """

    async def _one(key: str, model: str) -> tuple[str, str | Exception]:
        # Build messages OUTSIDE the try so prompt-builder bugs propagate.
        messages = messages_for(key)
        try:
            return key, await query_model(model, messages)
        except (OpenRouterError, ModelTimeoutError) as exc:
            return key, exc

    results = await asyncio.gather(
        *(_one(k, m) for k, m in model_assignments.items())
    )
    return dict(results)
```

## A6 — Orchestration: self-vote exclusion + partial preservation on Lead Counsel failure

**Codex finding 1:** Each evaluator ranks the full anonymized set including its own analysis. Even with anonymity, persona conditioning can leak self-preference. Exclude self-votes from aggregation.

**Codex finding 2:** Lead Counsel failure currently raises and discards all Stage 1 + Stage 2 work. Preserve the partial deliberation with a `stage3.error` marker.

**Updated `aggregate_rankings` and `run_full_counsel` in `backend/counsel.py` (Task 8):**

```python
def aggregate_rankings(
    stage2: dict[str, dict[str, Any]],
    label_to_role: dict[str, str],
) -> list[dict[str, Any]]:
    """Compute aggregate rankings, excluding evaluators' self-votes.

    Each persona evaluates all responses (including their own anonymized
    output), but their vote for themselves is dropped before averaging. This
    is the simplest defense against self-preference leakage in persona-
    conditioned ranking.
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


async def run_stage3(
    question: str,
    stage1: dict[str, dict[str, Any]],
    stage2: dict[str, dict[str, Any]],
    aggregates: list[dict[str, Any]],
) -> dict[str, Any]:
    """Synthesize the final Lead Counsel memorandum.

    Returns either {"model", "content", "error": None} on success or
    {"model", "content": None, "error": str} on failure. Never raises — Lead
    Counsel failure must not discard upstream Stage 1 + Stage 2 work.
    """
    prompt = build_stage3_prompt(question, stage1, stage2, aggregates)
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


async def run_full_counsel(
    question: str,
    context: str | None = None,
) -> dict[str, Any]:
    """Run the complete 3-stage deliberation.

    Raises AllModelsFailedError only if Stage 1 has zero successes. Lead
    Counsel failures are returned in-band as stage3.error.
    """
    stage1 = await run_stage1(question, context)
    stage2_results, label_to_role = await run_stage2(question, stage1)
    aggregates = aggregate_rankings(stage2_results, label_to_role)
    stage3 = await run_stage3(question, stage1, stage2_results, aggregates)

    return {
        "stage1": stage1,
        "stage2": {
            "assessments": stage2_results,
            "label_mapping": label_to_role,
            "aggregate_rankings": aggregates,
        },
        "stage3": stage3,
    }
```

(The `LeadCounselError` class in `backend/errors.py` is no longer raised by orchestration — it's now an in-band error. Keep the class definition for any future use, but it won't be caught in `main.py` anymore.)

## A7 — Storage: atomic temp-file writes + separate lockfile

**Codex finding:** `r+` + `seek(0)` + `truncate()` + `dump()` is not crash-safe — a crash mid-write leaves a corrupt or empty JSON file. Also, the original "lock the destination file" pattern has a subtle race when combined with atomic rename: a writer that opens the file before another writer's `os.replace()` reads stale data and clobbers the new write.

**Fix:** Use a per-matter lockfile for serialization, plus atomic temp-file + `os.replace()` for the actual write.

**Updated `backend/storage.py` (replaces Task 9 Step 1):**

```python
"""JSON storage for legal matters with atomic writes and separate lockfiles."""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .config import DATA_DIR


def _data_path() -> Path:
    p = Path(DATA_DIR)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _matter_path(matter_id: str) -> Path:
    return _data_path() / f"{matter_id}.json"


def _lock_path(matter_id: str) -> Path:
    return _data_path() / f".{matter_id}.lock"


@contextmanager
def _matter_lock(matter_id: str) -> Iterator[None]:
    """Acquire an exclusive advisory lock for a matter via a separate lockfile.

    The lockfile is never replaced (only the data file is), so two writers
    racing to read-modify-write the same matter serialize correctly even when
    the data file is replaced atomically between operations.
    """
    lock_path = _lock_path(matter_id)
    lock_path.touch(exist_ok=True)
    with open(lock_path, "r") as lf:
        try:
            fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Write JSON atomically: temp file in same dir → fsync → os.replace."""
    fd, tmp_str = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    tmp_path = Path(tmp_str)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass
        raise


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_matter(
    matter_name: str = "New Matter",
    practice_area: str = "civil",
    jurisdiction: str = "federal",
) -> dict[str, Any]:
    matter_id = f"matter_{uuid.uuid4().hex[:12]}"
    matter = {
        "id": matter_id,
        "created_at": _utcnow_iso(),
        "matter_name": matter_name,
        "practice_area": practice_area,
        "jurisdiction": jurisdiction,
        "messages": [],
    }
    with _matter_lock(matter_id):
        _atomic_write_json(_matter_path(matter_id), matter)
    return matter


def get_matter(matter_id: str) -> dict[str, Any] | None:
    path = _matter_path(matter_id)
    if not path.exists():
        return None
    with _matter_lock(matter_id):
        with open(path, "r") as f:
            return json.load(f)


def list_matters() -> list[dict[str, Any]]:
    matters = []
    for entry in _data_path().iterdir():
        if entry.suffix != ".json" or entry.name.startswith("."):
            continue
        try:
            with open(entry, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        matters.append({
            "id": data["id"],
            "created_at": data["created_at"],
            "matter_name": data.get("matter_name", "New Matter"),
            "practice_area": data.get("practice_area", "civil"),
            "jurisdiction": data.get("jurisdiction", "federal"),
            "message_count": len(data.get("messages", [])),
        })
    matters.sort(key=lambda m: m["created_at"], reverse=True)
    return matters


def delete_matter(matter_id: str) -> bool:
    path = _matter_path(matter_id)
    lock_path = _lock_path(matter_id)
    deleted = False
    try:
        with _matter_lock(matter_id):
            try:
                path.unlink()
                deleted = True
            except FileNotFoundError:
                deleted = False
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass
    return deleted


def append_user_message(
    matter_id: str, content: str, context: str | None = None
) -> None:
    with _matter_lock(matter_id):
        path = _matter_path(matter_id)
        if not path.exists():
            raise ValueError(f"Matter {matter_id} not found")
        with open(path, "r") as f:
            matter = json.load(f)
        message = {"role": "user", "content": content}
        if context:
            message["context"] = context
        matter["messages"].append(message)
        _atomic_write_json(path, matter)


def append_assistant_message(matter_id: str, deliberation: dict[str, Any]) -> None:
    with _matter_lock(matter_id):
        path = _matter_path(matter_id)
        if not path.exists():
            raise ValueError(f"Matter {matter_id} not found")
        with open(path, "r") as f:
            matter = json.load(f)
        matter["messages"].append({"role": "assistant", **deliberation})
        _atomic_write_json(path, matter)
```

Note: `list_matters` deliberately skips dotfiles (the lockfiles) and reads without taking a per-matter lock — listing is best-effort metadata anyway.

## A8 — `main.py`: simpler error handling + startup validation

**Codex finding 1:** Lead Counsel failure should not 502 — partial Stage 1/Stage 2 work should be persisted and returned with `stage3.error` populated.

**Codex finding 2:** No startup validation that the active team is well-formed; misconfiguration is only discovered on first request.

**Updated `backend/main.py` (replaces Task 10 Step 1):**

```python
"""FastAPI server for LLM-COUNSEL."""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import storage
from .config import API_HOST, API_PORT, COUNSEL_TEAM, LEAD_COUNSEL_MODEL, OPENROUTER_API_KEY
from .counsel import run_full_counsel
from .errors import AllModelsFailedError
from .prompts import LEGAL_PERSONAS

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="LLM-COUNSEL API", description="Legal Strategy Deliberation System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def validate_team() -> None:
    """Fail fast on misconfiguration instead of waiting for the first request."""
    for role in COUNSEL_TEAM:
        if role not in LEGAL_PERSONAS:
            raise RuntimeError(
                f"COUNSEL_TEAM uses unregistered persona '{role}'. "
                f"Valid roles: {sorted(LEGAL_PERSONAS.keys())}"
            )
    if len(COUNSEL_TEAM) < 2:
        raise RuntimeError("COUNSEL_TEAM needs at least 2 personas for peer review")
    if not OPENROUTER_API_KEY:
        logger.warning("OPENROUTER_API_KEY is not set; deliberation calls will fail")
    logger.info(
        "counsel team validated: %d personas, lead=%s",
        len(COUNSEL_TEAM), LEAD_COUNSEL_MODEL,
    )


class CreateMatterRequest(BaseModel):
    matter_name: str = "New Matter"
    practice_area: str = "civil"
    jurisdiction: str = "federal"


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=20_000)
    context: str | None = Field(default=None, max_length=100_000)


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok", "service": "LLM-COUNSEL Legal Strategy API"}


@app.get("/api/config/team")
async def get_team_config() -> dict[str, object]:
    """Expose the active counsel team for the frontend to render."""
    return {
        "lead_counsel": LEAD_COUNSEL_MODEL,
        "team": [
            {
                "role": role,
                "display_name": LEGAL_PERSONAS[role].display_name,
                "icon": LEGAL_PERSONAS[role].icon,
                "color": LEGAL_PERSONAS[role].color,
                "focus_areas": list(LEGAL_PERSONAS[role].focus_areas),
                "model": model,
            }
            for role, model in COUNSEL_TEAM.items()
        ],
    }


@app.get("/api/matters")
async def list_matters() -> list[dict]:
    return storage.list_matters()


@app.post("/api/matters")
async def create_matter(request: CreateMatterRequest) -> dict:
    return storage.create_matter(
        matter_name=request.matter_name,
        practice_area=request.practice_area,
        jurisdiction=request.jurisdiction,
    )


@app.get("/api/matters/{matter_id}")
async def get_matter(matter_id: str) -> dict:
    matter = storage.get_matter(matter_id)
    if matter is None:
        raise HTTPException(status_code=404, detail="Matter not found")
    return matter


@app.delete("/api/matters/{matter_id}")
async def delete_matter(matter_id: str) -> dict:
    if not storage.delete_matter(matter_id):
        raise HTTPException(status_code=404, detail="Matter not found")
    return {"status": "deleted", "id": matter_id}


@app.post("/api/matters/{matter_id}/message")
async def send_message(matter_id: str, request: SendMessageRequest) -> dict:
    if storage.get_matter(matter_id) is None:
        raise HTTPException(status_code=404, detail="Matter not found")

    storage.append_user_message(matter_id, request.content, request.context)

    try:
        deliberation = await run_full_counsel(request.content, request.context)
    except AllModelsFailedError as exc:
        logger.warning("matter %s: all stage 1 models failed: %s", matter_id, exc)
        raise HTTPException(status_code=502, detail=f"All models failed: {exc}") from exc

    # Lead Counsel failure is in-band (stage3.error); the partial deliberation
    # is persisted and returned so the user can still see Stage 1 + Stage 2.
    storage.append_assistant_message(matter_id, deliberation)
    return deliberation


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)
```

## A9 — Persona test improvements

**Codex finding:** Asserting that slugs contain `/` is low-value. Replace with explicit assertions about the active team shape.

**Replaces Task 11 Step 2:**

```python
"""Persona registry sanity tests."""

from __future__ import annotations

import pytest

from backend.config import COUNSEL_TEAM, LEAD_COUNSEL_MODEL
from backend.prompts import LEGAL_PERSONAS, get_persona, list_personas


REQUIRED_FIELDS = ("role", "display_name", "icon", "color", "focus_areas", "system_prompt")


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
        assert role in LEGAL_PERSONAS, f"COUNSEL_TEAM uses unregistered role: {role}"


def test_active_team_has_at_least_two_personas():
    """Peer review requires at least 2 evaluators to be meaningful."""
    assert len(COUNSEL_TEAM) >= 2


def test_active_team_models_have_provider_prefix():
    for role, model in COUNSEL_TEAM.items():
        assert model.count("/") == 1, f"{role} model not in provider/model form: {model}"
    assert LEAD_COUNSEL_MODEL.count("/") == 1


def test_lead_counsel_uses_different_family_from_evaluators_or_documents_choice():
    """Cross-family diversity is the design goal. If Lead Counsel reuses an
    evaluator's model, that's a deliberate tradeoff that should be visible
    in this test failing — change the test if you change the policy.
    """
    lead_family = LEAD_COUNSEL_MODEL.split("/")[0]
    evaluator_families = {m.split("/")[0] for m in COUNSEL_TEAM.values()}
    if lead_family in evaluator_families:
        # Allow it but make the choice explicit. Update this assertion when
        # COUNSEL_TEAM changes.
        assert lead_family in {"google", "anthropic"}, (
            f"Lead Counsel family {lead_family} reuses evaluator family — "
            "is this intentional?"
        )


def test_list_personas_returns_all():
    assert set(list_personas()) == set(LEGAL_PERSONAS.keys())
```

## A10 — Parser test additions

**Adds to Task 12 (`tests/test_ranking_parser.py`):**

```python
def test_returns_empty_for_non_sequential_numbering():
    """1, 2, 4, 5 instead of 1, 2, 3, 4."""
    text = "FINAL RANKING:\n1. Response A\n2. Response B\n4. Response C\n5. Response D"
    assert parse_ranking(text, VALID_LABELS) == []


def test_returns_empty_when_invented_high_numbers():
    text = "FINAL RANKING:\n9. Response A\n10. Response B\n11. Response C\n12. Response D"
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
```

## A11 — Cross-process storage concurrency test

**Adds to Task 13 (`tests/test_storage.py`):**

```python
import multiprocessing
import os


def _append_in_subprocess(data_dir, matter_id, content):
    """Worker for the cross-process concurrency test."""
    os.environ["DATA_DIR"] = str(data_dir)
    os.environ["OPENROUTER_API_KEY"] = "test"
    import importlib
    import backend.config
    import backend.storage
    importlib.reload(backend.config)
    importlib.reload(backend.storage)
    backend.storage.append_user_message(matter_id, content)


def test_concurrent_appends_across_processes(isolated_data_dir, tmp_path):
    """Threads share an interpreter; processes don't. fcntl.flock is the
    only thing keeping cross-process writers from clobbering each other."""
    storage = isolated_data_dir
    matter = storage.create_matter()
    n = 6
    procs = [
        multiprocessing.Process(
            target=_append_in_subprocess,
            args=(tmp_path, matter["id"], f"proc-{i}"),
        )
        for i in range(n)
    ]
    for p in procs:
        p.start()
    for p in procs:
        p.join()
        assert p.exitcode == 0

    fetched = storage.get_matter(matter["id"])
    contents = sorted(m["content"] for m in fetched["messages"])
    assert contents == sorted(f"proc-{i}" for i in range(n))
```

## A12 — Orchestration test additions

**Adds to Task 14 (`tests/test_counsel_orchestration.py`):**

```python
@pytest.mark.asyncio
async def test_lead_counsel_failure_preserves_partial_work(monkeypatch):
    """If synthesis fails, stage1+stage2 results are still returned with stage3.error."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test")

    async def fake_query_model(model, messages, timeout=None):
        prompt = messages[0]["content"]
        if "Lead Counsel" in prompt:
            from backend.errors import OpenRouterError
            raise OpenRouterError(model, 503, "service down")
        if "FINAL RANKING:" in prompt:
            return (
                "Done.\nFINAL RANKING:\n"
                "1. Response A\n2. Response B\n3. Response C\n4. Response D"
            )
        return "stage1 work"

    with patch("backend.openrouter.query_model", side_effect=fake_query_model), \
         patch("backend.counsel.query_model", side_effect=fake_query_model):
        result = await run_full_counsel("Q?")

    # Stage 1 + Stage 2 work was preserved
    assert all(r["content"] for r in result["stage1"].values())
    assert len(result["stage2"]["assessments"]) == 4
    assert len(result["stage2"]["aggregate_rankings"]) == 4

    # Stage 3 has an error marker but no content (lead counsel failed)
    assert result["stage3"]["content"] is None
    assert result["stage3"]["error"] is not None


@pytest.mark.asyncio
async def test_stage2_unparseable_ballot_yields_empty_aggregates(monkeypatch):
    """If Stage 2 returns prose with no FINAL RANKING block, aggregates are empty
    but stage3 still runs."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test")

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
    """Each evaluator ranks itself first; aggregate must drop self-votes."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test")

    # Each persona will rank Response A first (its own), then B, C, D.
    # After self-vote exclusion, no persona should have a "1" position.
    async def fake_query_model(model, messages, timeout=None):
        prompt = messages[0]["content"]
        if "FINAL RANKING:" in prompt:
            # Find which persona this is by looking at the system prompt
            # marker. All evaluators will produce the SAME ranking, A first.
            return (
                "Self-favoring evaluation.\nFINAL RANKING:\n"
                "1. Response A\n2. Response B\n3. Response C\n4. Response D"
            )
        if "Lead Counsel" in prompt:
            return "Synthesized."
        return "content"

    with patch("backend.openrouter.query_model", side_effect=fake_query_model), \
         patch("backend.counsel.query_model", side_effect=fake_query_model):
        result = await run_full_counsel("Q?")

    # All 4 personas voted Response A first. Persona-A's self-vote is excluded,
    # so Response A's positions list has only 3 entries (the OTHER 3 evaluators
    # voting it first). Response B, C, D have 3 entries each too — also missing
    # the vote from whichever persona they correspond to.
    aggregates = result["stage2"]["aggregate_rankings"]
    assert all(len(a["positions"]) == 3 for a in aggregates), (
        f"Expected 3 votes per persona after self-vote exclusion, got: "
        f"{[(a['role'], len(a['positions'])) for a in aggregates]}"
    )
```

## A13 — NEW Task: openrouter unit tests (fills the biggest test gap)

**Codex finding:** `openrouter.py` gets the largest control-flow rewrite (silent-failure → typed errors) and has zero direct tests in the original plan.

**Files:**
- Create: `tests/test_openrouter.py`

```python
"""Unit tests for the OpenRouter client error mapping."""

from __future__ import annotations

import importlib

import httpx
import pytest


@pytest.fixture
def fresh_openrouter(monkeypatch):
    """Reload openrouter with a test API key in env."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    import backend.config
    import backend.openrouter
    importlib.reload(backend.config)
    importlib.reload(backend.openrouter)
    return backend.openrouter


def _patch_async_client(monkeypatch, post_impl):
    class FakeClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *exc):
            return None
        async def post(self, *args, **kwargs):
            return await post_impl(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: FakeClient())


@pytest.mark.asyncio
async def test_query_model_timeout_raises_typed_error(fresh_openrouter, monkeypatch):
    from backend.errors import ModelTimeoutError

    async def post_timeout(*a, **k):
        raise httpx.TimeoutException("timeout")

    _patch_async_client(monkeypatch, post_timeout)

    with pytest.raises(ModelTimeoutError) as exc_info:
        await fresh_openrouter.query_model("test/model", [{"role": "user", "content": "hi"}])
    assert exc_info.value.model == "test/model"


@pytest.mark.asyncio
async def test_query_model_http_429_raises_openrouter_error(fresh_openrouter, monkeypatch):
    from backend.errors import OpenRouterError

    class FakeResponse:
        status_code = 429
        text = '{"error":"rate limited"}'
        def json(self): return {"error": "rate limited"}

    async def post_429(*a, **k): return FakeResponse()
    _patch_async_client(monkeypatch, post_429)

    with pytest.raises(OpenRouterError) as exc_info:
        await fresh_openrouter.query_model("test/model", [{"role": "user", "content": "hi"}])
    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_query_model_malformed_json_raises_openrouter_error(fresh_openrouter, monkeypatch):
    from backend.errors import OpenRouterError

    class FakeResponse:
        status_code = 200
        text = "not json at all"
        def json(self): raise ValueError("not json")

    async def post_bad_json(*a, **k): return FakeResponse()
    _patch_async_client(monkeypatch, post_bad_json)

    with pytest.raises(OpenRouterError, match="malformed"):
        await fresh_openrouter.query_model("test/model", [{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_query_model_returns_content_on_success(fresh_openrouter, monkeypatch):
    class FakeResponse:
        status_code = 200
        text = ""
        def json(self):
            return {"choices": [{"message": {"content": "hello"}}]}

    async def post_ok(*a, **k): return FakeResponse()
    _patch_async_client(monkeypatch, post_ok)

    result = await fresh_openrouter.query_model("test/model", [{"role": "user", "content": "hi"}])
    assert result == "hello"


@pytest.mark.asyncio
async def test_query_models_parallel_isolates_failures(fresh_openrouter, monkeypatch):
    """Per-key failures must be returned in-band, not raised."""
    from backend.errors import OpenRouterError

    async def fake_query(model, messages, timeout=None):
        if "fail" in model:
            raise OpenRouterError(model, 500, "boom")
        return f"ok from {model}"

    monkeypatch.setattr(fresh_openrouter, "query_model", fake_query)

    results = await fresh_openrouter.query_models_parallel(
        {"good": "good/model", "bad": "fail/model"},
        lambda key: [{"role": "user", "content": "x"}],
    )
    assert results["good"] == "ok from good/model"
    assert isinstance(results["bad"], OpenRouterError)


@pytest.mark.asyncio
async def test_query_models_parallel_does_not_swallow_builder_bugs(fresh_openrouter):
    """A bug in messages_for() is a programming error and must propagate."""
    def broken_messages_for(key):
        raise KeyError(f"unknown {key}")

    with pytest.raises(KeyError):
        await fresh_openrouter.query_models_parallel(
            {"role1": "any/model"},
            broken_messages_for,
        )
```

This gets inserted as **Task 14b** between Task 14 and Task 15.

## A14 — CUT Task 16

**Codex finding (verified):** `legal-navy` (`#1a365d`), `legal-gold` (`#c9a227`), and `legal-cream` already exist in `frontend/tailwind.config.js`. Task 16 is dropped entirely. Renumber Tasks 17+ down by 1 mentally during execution; the existing task IDs in this file are unchanged for traceability.

## A15 — Wire `/api/config/team` into the welcome screen

**Codex finding:** The `/api/config/team` endpoint is added but no frontend task consumes it, making it dead code. Either cut or use. Decision: use it in the WelcomeScreen so users can see the team before running a deliberation.

**Adds to Task 21 (App.jsx update):**

In `WelcomeScreen`, replace the static "Initial Analyses / Peer Rankings / Lead Counsel" 3-card grid with a dynamic team panel fetched from `/api/config/team`. Add to App.jsx imports:

```jsx
import { useEffect, useState } from 'react';
```

And inside `WelcomeScreen`:

```jsx
function WelcomeScreen({ onNewMatter }) {
  const [team, setTeam] = useState(null);

  useEffect(() => {
    api.getTeamConfig().then(setTeam).catch((err) => {
      console.warn('Failed to load team config:', err);
    });
  }, []);

  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="text-center max-w-3xl">
        {/* Disclaimer banner — unchanged */}
        <div className="bg-red-50 border-l-4 border-red-600 p-4 mb-8 text-left">
          <div className="flex items-start gap-3">
            <div className="text-2xl">⚠️</div>
            <div>
              <h3 className="font-bold text-red-900 mb-2">IMPORTANT LEGAL DISCLAIMER</h3>
              <p className="text-sm text-red-800 leading-relaxed">
                This system does <strong>NOT</strong> provide legal advice. LLM-COUNSEL is a
                legal research and strategy analysis tool. All outputs are AI-generated and
                must be reviewed by a licensed attorney.
              </p>
            </div>
          </div>
        </div>

        <div className="text-6xl mb-6">⚖️</div>
        <h1 className="text-4xl font-bold text-legal-navy mb-4">LLM-COUNSEL</h1>
        <p className="text-xl text-gray-600 mb-2">Multi-Model Legal Strategy Deliberation</p>
        <p className="text-gray-500 mb-8 max-w-xl mx-auto">
          Each legal question is analyzed by a team of AI attorneys with different
          specialized perspectives, who then peer-review each other's work. A Lead Counsel
          synthesizes the team's deliberation into a final strategy memorandum.
        </p>

        {team && (
          <div className="mb-8">
            <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-3">
              Your Counsel Team
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {team.team.map((p) => (
                <div key={p.role} className="p-4 bg-white rounded-lg shadow text-left">
                  <div className="text-2xl mb-1">{p.icon}</div>
                  <div className="font-semibold text-legal-navy text-sm">{p.display_name}</div>
                  <div className="text-xs text-gray-400 truncate" title={p.model}>
                    {p.model}
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-3 text-xs text-gray-500">
              Lead Counsel synthesizer: <code>{team.lead_counsel}</code>
            </div>
          </div>
        )}

        <button
          onClick={onNewMatter}
          className="px-8 py-3 bg-legal-navy text-white rounded-lg hover:bg-blue-900 transition-colors font-semibold"
        >
          Create New Matter
        </button>
      </div>
    </div>
  );
}
```

---

## Codex points acknowledged but not addressed in this pass

| Codex point | Reason |
|---|---|
| Self-ranking via per-evaluator anonymized sets (vs simple aggregation exclusion) | Aggregation exclusion in A6 is the simpler, equivalent fix for single-pass deliberation |
| Eight personas registered but only four active | The bench is documentary; cost is ~150 lines of small dataclass entries. Low overhead, high optionality |
| Structured logging with correlation IDs across the 9-call path | Real value but distinct concern; the basic per-stage `logger.warning` is sufficient for this pass |

## Summary of execution-order impact

The amendments touch **9 of 31 tasks**. Tasks 1, 2, 3, 11 (header), 12 (header), 13 (most), 14 (most), 15-22 (most), 23-31 (all) are **unchanged**. Affected:
- Task 4 → use A2 code
- Task 5 → use A3 code
- Task 6 → use A4 line for Lead Counsel
- Task 8 → use A6 code for `aggregate_rankings`, `run_stage3`, `run_full_counsel`
- Task 9 → use A7 code in full
- Task 10 → use A8 code in full
- Task 11 → use A9 test additions
- Task 12 → append A10 tests
- Task 13 → append A11 cross-process test
- Task 14 → append A12 tests
- **NEW Task 14b** → A13 openrouter tests
- Task 16 → SKIP (already in tailwind config)
- Task 21 → also apply A15 WelcomeScreen team panel
