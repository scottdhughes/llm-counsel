"""FastAPI backend for LLM-COUNSEL Legal Strategy System."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any

from . import storage
from .counsel import run_full_counsel

app = FastAPI(title="LLM-COUNSEL API", description="Legal Strategy Deliberation System")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateMatterRequest(BaseModel):
    """Request to create a new matter."""
    matter_name: str = "New Matter"
    practice_area: str = "civil"
    jurisdiction: str = "federal"


class SendMessageRequest(BaseModel):
    """Request to send a legal question."""
    content: str
    context: str = None


class MatterMetadata(BaseModel):
    """Matter metadata for list view."""
    id: str
    created_at: str
    matter_name: str
    practice_area: str
    jurisdiction: str
    message_count: int


class Matter(BaseModel):
    """Full matter with all messages."""
    id: str
    created_at: str
    matter_name: str
    practice_area: str
    jurisdiction: str
    messages: List[Dict[str, Any]]


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "LLM-COUNSEL Legal Strategy API"}


@app.get("/api/matters", response_model=List[MatterMetadata])
async def list_matters():
    """List all matters (metadata only)."""
    return storage.list_matters()


@app.post("/api/matters", response_model=Matter)
async def create_matter(request: CreateMatterRequest):
    """Create a new matter."""
    matter = storage.create_matter(
        matter_name=request.matter_name,
        practice_area=request.practice_area,
        jurisdiction=request.jurisdiction
    )
    return matter


@app.get("/api/matters/{matter_id}", response_model=Matter)
async def get_matter(matter_id: str):
    """Get a specific matter with all its messages."""
    matter = storage.get_matter(matter_id)
    if matter is None:
        raise HTTPException(status_code=404, detail="Matter not found")
    return matter


@app.delete("/api/matters/{matter_id}")
async def delete_matter(matter_id: str):
    """Delete a matter."""
    deleted = storage.delete_matter(matter_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Matter not found")
    return {"status": "deleted", "id": matter_id}


@app.post("/api/matters/{matter_id}/message")
async def send_message(matter_id: str, request: SendMessageRequest):
    """
    Submit a legal question and run the 3-stage counsel deliberation.
    Returns the complete response with all stages.
    """
    # Check if matter exists
    matter = storage.get_matter(matter_id)
    if matter is None:
        raise HTTPException(status_code=404, detail="Matter not found")

    # Add user message
    storage.add_user_message(matter_id, request.content, request.context)

    # Run the 3-stage legal counsel process
    stage1_results, stage2_results, stage3_result, metadata = await run_full_counsel(
        legal_question=request.content,
        context=request.context
    )

    # Add assistant message with all stages
    storage.add_assistant_message(
        matter_id,
        stage1_results,
        stage2_results,
        stage3_result
    )

    # Return the complete response with metadata
    return {
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": metadata
    }


if __name__ == "__main__":
    import uvicorn
    from .config import API_HOST, API_PORT
    uvicorn.run(app, host=API_HOST, port=API_PORT)
