"""JSON-based storage for legal matters."""

import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from .config import DATA_DIR


def ensure_data_dir():
    """Ensure the data directory exists."""
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)


def get_matter_path(matter_id: str) -> str:
    """Get the file path for a matter."""
    return os.path.join(DATA_DIR, f"{matter_id}.json")


def create_matter(
    matter_name: str = "New Matter",
    practice_area: str = "civil",
    jurisdiction: str = "federal"
) -> Dict[str, Any]:
    """
    Create a new legal matter.

    Args:
        matter_name: Name of the matter
        practice_area: Practice area (e.g., "employment", "civil")
        jurisdiction: Jurisdiction (e.g., "federal", "state-ca")

    Returns:
        New matter dict
    """
    ensure_data_dir()

    matter_id = f"matter_{uuid.uuid4().hex[:12]}"

    matter = {
        "id": matter_id,
        "created_at": datetime.utcnow().isoformat(),
        "matter_name": matter_name,
        "practice_area": practice_area,
        "jurisdiction": jurisdiction,
        "messages": []
    }

    # Save to file
    path = get_matter_path(matter_id)
    with open(path, 'w') as f:
        json.dump(matter, f, indent=2)

    return matter


def get_matter(matter_id: str) -> Optional[Dict[str, Any]]:
    """
    Load a matter from storage.

    Args:
        matter_id: Unique identifier for the matter

    Returns:
        Matter dict or None if not found
    """
    path = get_matter_path(matter_id)

    if not os.path.exists(path):
        return None

    with open(path, 'r') as f:
        return json.load(f)


def save_matter(matter: Dict[str, Any]):
    """
    Save a matter to storage.

    Args:
        matter: Matter dict to save
    """
    ensure_data_dir()

    path = get_matter_path(matter['id'])
    with open(path, 'w') as f:
        json.dump(matter, f, indent=2)


def list_matters() -> List[Dict[str, Any]]:
    """
    List all matters (metadata only).

    Returns:
        List of matter metadata dicts
    """
    ensure_data_dir()

    matters = []
    for filename in os.listdir(DATA_DIR):
        if filename.endswith('.json'):
            path = os.path.join(DATA_DIR, filename)
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    # Return metadata only
                    matters.append({
                        "id": data["id"],
                        "created_at": data["created_at"],
                        "matter_name": data.get("matter_name", "New Matter"),
                        "practice_area": data.get("practice_area", "civil"),
                        "jurisdiction": data.get("jurisdiction", "federal"),
                        "message_count": len(data.get("messages", []))
                    })
            except (json.JSONDecodeError, KeyError):
                # Skip corrupted files
                continue

    # Sort by creation time, newest first
    matters.sort(key=lambda x: x["created_at"], reverse=True)

    return matters


def delete_matter(matter_id: str) -> bool:
    """
    Delete a matter.

    Args:
        matter_id: Matter identifier

    Returns:
        True if deleted, False if not found
    """
    path = get_matter_path(matter_id)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False


def add_user_message(matter_id: str, content: str, context: str = None):
    """
    Add a user message to a matter.

    Args:
        matter_id: Matter identifier
        content: User message content (legal question)
        context: Additional case context (optional)
    """
    matter = get_matter(matter_id)
    if matter is None:
        raise ValueError(f"Matter {matter_id} not found")

    message = {
        "role": "user",
        "content": content
    }
    if context:
        message["context"] = context

    matter["messages"].append(message)

    save_matter(matter)


def add_assistant_message(
    matter_id: str,
    stage1: List[Dict[str, Any]],
    stage2: List[Dict[str, Any]],
    stage3: Dict[str, Any]
):
    """
    Add an assistant message with all 3 stages to a matter.

    Args:
        matter_id: Matter identifier
        stage1: List of individual model responses
        stage2: List of model rankings
        stage3: Final synthesized legal strategy
    """
    matter = get_matter(matter_id)
    if matter is None:
        raise ValueError(f"Matter {matter_id} not found")

    matter["messages"].append({
        "role": "assistant",
        "stage1": stage1,
        "stage2": stage2,
        "stage3": stage3
    })

    save_matter(matter)
