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
        await fresh_openrouter.query_model(
            "test/model", [{"role": "user", "content": "hi"}]
        )
    assert exc_info.value.model == "test/model"


@pytest.mark.asyncio
async def test_query_model_http_429_raises_openrouter_error(
    fresh_openrouter, monkeypatch
):
    from backend.errors import OpenRouterError

    class FakeResponse:
        status_code = 429
        text = '{"error":"rate limited"}'

        def json(self):
            return {"error": "rate limited"}

    async def post_429(*a, **k):
        return FakeResponse()

    _patch_async_client(monkeypatch, post_429)

    with pytest.raises(OpenRouterError) as exc_info:
        await fresh_openrouter.query_model(
            "test/model", [{"role": "user", "content": "hi"}]
        )
    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_query_model_malformed_json_raises_openrouter_error(
    fresh_openrouter, monkeypatch
):
    from backend.errors import OpenRouterError

    class FakeResponse:
        status_code = 200
        text = "not json at all"

        def json(self):
            raise ValueError("not json")

    async def post_bad_json(*a, **k):
        return FakeResponse()

    _patch_async_client(monkeypatch, post_bad_json)

    with pytest.raises(OpenRouterError, match="malformed"):
        await fresh_openrouter.query_model(
            "test/model", [{"role": "user", "content": "hi"}]
        )


@pytest.mark.asyncio
async def test_query_model_returns_content_on_success(
    fresh_openrouter, monkeypatch
):
    class FakeResponse:
        status_code = 200
        text = ""

        def json(self):
            return {"choices": [{"message": {"content": "hello"}}]}

    async def post_ok(*a, **k):
        return FakeResponse()

    _patch_async_client(monkeypatch, post_ok)

    result = await fresh_openrouter.query_model(
        "test/model", [{"role": "user", "content": "hi"}]
    )
    assert result == "hello"


@pytest.mark.asyncio
async def test_query_models_parallel_isolates_failures(
    fresh_openrouter, monkeypatch
):
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
async def test_query_models_parallel_does_not_swallow_builder_bugs(
    fresh_openrouter,
):
    """A bug in messages_for() is a programming error and must propagate."""

    def broken_messages_for(key):
        raise KeyError(f"unknown {key}")

    with pytest.raises(KeyError):
        await fresh_openrouter.query_models_parallel(
            {"role1": "any/model"},
            broken_messages_for,
        )
