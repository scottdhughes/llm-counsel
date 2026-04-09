"""Shared helpers used by multiple stage prompts.

The matter header lets every stage see the jurisdiction and practice area that
the user chose when creating the matter. Without it, the personas have to
infer which body of law applies from the free-text context — which usually
works but is a load-bearing inference that should be explicit.
"""

from __future__ import annotations


# Human-readable labels keyed by taxonomy code. The codes are what's stored
# in the matter JSON; the labels are what the models see in prompts.
_JURISDICTION_LABELS: dict[str, str] = {
    "federal": "Federal (United States)",
    "state-ca": "California (state)",
    "state-ny": "New York (state)",
    "state-tx": "Texas (state)",
    "state-fl": "Florida (state)",
    "state-il": "Illinois (state)",
    "state-de": "Delaware (state)",
    "state-wa": "Washington (state)",
    "state-ma": "Massachusetts (state)",
}

_PRACTICE_AREA_LABELS: dict[str, str] = {
    "civil": "Civil litigation",
    "commercial": "Commercial litigation",
    "employment": "Employment law",
    "intellectual_property": "Intellectual property",
    "personal_injury": "Personal injury",
    "criminal": "Criminal law",
    "family": "Family law",
    "regulatory": "Regulatory / administrative",
}


def _humanize(mapping: dict[str, str], code: str) -> str:
    """Return a human label; fall back to the code with separators fixed."""
    if code in mapping:
        return mapping[code]
    return code.replace("_", " ").replace("-", " ").title()


def render_matter_header(matter_context: dict[str, str] | None) -> str:
    """Render an optional matter context header for prompts.

    Returns "" if `matter_context` is None or empty, so callers that don't
    pass matter metadata get the same prompt shape as before this was added.
    """
    if not matter_context:
        return ""

    name = matter_context.get("matter_name")
    practice = matter_context.get("practice_area")
    jurisdiction = matter_context.get("jurisdiction")

    # Only emit the header if there's at least one meaningful field.
    if not (name or practice or jurisdiction):
        return ""

    lines = ["══════════════════════════════════════════════════════════"]
    lines.append("MATTER CONTEXT")
    if name:
        lines.append(f"  Name:          {name}")
    if practice:
        lines.append(
            f"  Practice area: {_humanize(_PRACTICE_AREA_LABELS, practice)}"
        )
    if jurisdiction:
        label = _humanize(_JURISDICTION_LABELS, jurisdiction)
        lines.append(f"  Jurisdiction:  {label}")
        lines.append(f"  Governing law: {label}")
    lines.append("══════════════════════════════════════════════════════════")
    return "\n".join(lines) + "\n\n"
