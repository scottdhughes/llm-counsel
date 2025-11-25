"""
LLM-COUNSEL Configuration

Defines the legal counsel team and model assignments.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# OpenRouter API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Legal Counsel Team - PREMIUM: Latest and most capable models only
# Each model provides legal strategy analysis from different perspectives
COUNSEL_MODELS = [
    "anthropic/claude-3.5-sonnet",         # Latest Claude Sonnet - Superior legal reasoning
    "anthropic/claude-3-opus",             # Claude Opus - Most capable, comprehensive analysis
    "openai/gpt-4-turbo",                  # GPT-4 Turbo - Advanced reasoning
    "google/gemini-pro-1.5",               # Gemini Pro 1.5 - Long context, strategic insights
]

# Lead Counsel - synthesizes final legal strategy (use Claude Opus - most capable)
LEAD_COUNSEL_MODEL = "anthropic/claude-3-opus"

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Server configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8001"))

# Data directory for conversation storage
DATA_DIR = os.getenv("DATA_DIR", "data/conversations")
