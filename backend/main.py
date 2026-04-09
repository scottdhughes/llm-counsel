"""FastAPI server for LLM-COUNSEL."""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import storage
from .config import (
    API_HOST,
    API_PORT,
    COUNSEL_TEAM,
    LEAD_COUNSEL_MODEL,
    OPENROUTER_API_KEY,
)
from .counsel import run_full_counsel
from .errors import AllModelsFailedError
from .prompts import LEGAL_PERSONAS

logging.basicConfig(
    level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="LLM-COUNSEL API",
    description="Multi-model legal strategy deliberation system",
    version="1.1.0",
)

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
        raise RuntimeError(
            "COUNSEL_TEAM needs at least 2 personas for peer review"
        )
    if not OPENROUTER_API_KEY:
        logger.warning(
            "OPENROUTER_API_KEY is not set; deliberation calls will fail"
        )
    logger.info(
        "counsel team validated: %d personas, lead=%s",
        len(COUNSEL_TEAM),
        LEAD_COUNSEL_MODEL,
    )


class CreateMatterRequest(BaseModel):
    matter_name: str = "New Matter"
    practice_area: str = "civil"
    jurisdiction: str = "federal"


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=20_000)
    context: str | None = Field(default=None, max_length=100_000)


class UpdateMatterRequest(BaseModel):
    """Partial update for matter metadata. All fields optional."""

    matter_name: str | None = Field(default=None, max_length=200)
    practice_area: str | None = Field(default=None, max_length=64)
    jurisdiction: str | None = Field(default=None, max_length=64)


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


@app.patch("/api/matters/{matter_id}")
async def update_matter(
    matter_id: str, request: UpdateMatterRequest
) -> dict:
    """Update matter metadata (name, practice area, jurisdiction)."""
    updated = storage.update_matter_metadata(
        matter_id,
        matter_name=request.matter_name,
        practice_area=request.practice_area,
        jurisdiction=request.jurisdiction,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Matter not found")
    return updated


@app.delete("/api/matters/{matter_id}")
async def delete_matter(matter_id: str) -> dict:
    if not storage.delete_matter(matter_id):
        raise HTTPException(status_code=404, detail="Matter not found")
    return {"status": "deleted", "id": matter_id}


def _matter_context_from(matter: dict) -> dict[str, str]:
    """Extract the fields that flow into every stage's prompt."""
    return {
        "matter_name": matter.get("matter_name", ""),
        "practice_area": matter.get("practice_area", ""),
        "jurisdiction": matter.get("jurisdiction", ""),
    }


@app.post("/api/matters/{matter_id}/message")
async def send_message(matter_id: str, request: SendMessageRequest) -> dict:
    matter = storage.get_matter(matter_id)
    if matter is None:
        raise HTTPException(status_code=404, detail="Matter not found")

    storage.append_user_message(matter_id, request.content, request.context)

    try:
        deliberation = await run_full_counsel(
            question=request.content,
            context=request.context,
            matter_context=_matter_context_from(matter),
        )
    except AllModelsFailedError as exc:
        logger.warning(
            "matter %s: all stage 1 models failed: %s", matter_id, exc
        )
        raise HTTPException(
            status_code=502, detail=f"All models failed: {exc}"
        ) from exc

    # Lead Counsel failure is in-band (stage3.error); the partial deliberation
    # is persisted and returned so the user can still see Stage 1 + Stage 2.
    storage.append_assistant_message(matter_id, deliberation)
    return deliberation


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=API_HOST, port=API_PORT)
