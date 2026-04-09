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

# Lead Counsel synthesizes the final memorandum. Gemini 3.1 Pro has the
# longest context in the lineup, and using a different model family from
# defense_analyst (which uses Opus 4.6) keeps cross-model diversity.
LEAD_COUNSEL_MODEL: str = "google/gemini-3.1-pro-preview"

# Per-call timeout for OpenRouter requests (seconds).
MODEL_REQUEST_TIMEOUT: float = float(os.getenv("MODEL_REQUEST_TIMEOUT", "180.0"))

# Server. 127.0.0.1 by default because this repo has no auth and no rate
# limiting; binding to 0.0.0.0 is opt-in via env var.
API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
API_PORT: int = int(os.getenv("API_PORT", "8001"))

# Storage
DATA_DIR: str = os.getenv("DATA_DIR", "data/conversations")
