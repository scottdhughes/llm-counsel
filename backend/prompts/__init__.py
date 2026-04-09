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
