"""Shared test fixtures."""

from __future__ import annotations

import importlib

import pytest


@pytest.fixture
def isolated_data_dir(tmp_path, monkeypatch):
    """Run a test against a fresh DATA_DIR; reload modules so the path is picked up."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    import backend.config
    import backend.storage
    importlib.reload(backend.config)
    importlib.reload(backend.storage)
    yield backend.storage
