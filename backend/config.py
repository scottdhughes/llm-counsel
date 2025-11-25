"""
LLM-COUNSEL Configuration

Defines the legal counsel team and model assignments.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# OpenRouter API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Legal Counsel Team - NEXT-GEN: Latest and most capable models only
# Each model provides legal strategy analysis from different perspectives
COUNSEL_MODELS = [
    "openai/gpt-5.1",                      # GPT-5.1 - Next-generation reasoning
    "google/gemini-3-pro-preview",         # Gemini 3 Pro Preview - Advanced multimodal
    "anthropic/claude-sonnet-4.5",         # Claude Sonnet 4.5 - Enhanced legal reasoning
    "x-ai/grok-4",                         # Grok-4 - Latest from xAI
]

# Lead Counsel - synthesizes final legal strategy
LEAD_COUNSEL_MODEL = "google/gemini-3-pro-preview"

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Server configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8001"))

# Data directory for conversation storage
DATA_DIR = os.getenv("DATA_DIR", "data/conversations")
