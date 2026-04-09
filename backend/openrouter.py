"""Async OpenRouter client.

This module deliberately does NOT swallow exceptions. Callers receive either a
parsed response (a content string) or a typed error from `backend.errors`.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Callable

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
        OpenRouterError: the API returned a non-2xx response, a transport
            error, or a malformed body.
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
            "model %s returned HTTP %d: %s",
            model,
            response.status_code,
            body_preview,
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
    messages_for: Callable[[str], list[dict[str, str]]],
) -> dict[str, str | Exception]:
    """Run a stage in parallel across a set of (key, model) assignments.

    Errors raised by `messages_for` propagate immediately — those are
    programming bugs, not model failures. Errors raised by the model call
    (OpenRouterError, ModelTimeoutError) are captured per-key so partial
    successes can be surfaced to the caller.

    Args:
        model_assignments: Mapping from a stable key (e.g. persona role) to
            OpenRouter model slug.
        messages_for: Callable taking a key and returning the `messages` list
            for that call. Allows per-key prompt customization.

    Returns:
        Dict mapping the input keys to either the model's content string OR
        an exception instance. Callers decide how to surface partial failures.
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
