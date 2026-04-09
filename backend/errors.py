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
    """The Lead Counsel synthesis call failed.

    Note: in the current orchestration, Lead Counsel failures are returned
    in-band as `stage3.error` rather than raised, so this class is defined
    for future use but not actively thrown by `run_full_counsel`.
    """
