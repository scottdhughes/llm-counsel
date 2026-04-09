"""JSON storage for legal matters with atomic writes and separate lockfiles.

Design:
  - Per-matter lockfile (`.{matter_id}.lock`) serializes RMW operations.
  - Data file writes go temp-file → fsync → `os.replace()` for crash safety.
  - The lockfile is never replaced, so two writers racing on the same matter
    serialize correctly even when the data file is replaced atomically
    between operations.
"""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .config import DATA_DIR


def _data_path() -> Path:
    p = Path(DATA_DIR)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _matter_path(matter_id: str) -> Path:
    return _data_path() / f"{matter_id}.json"


def _lock_path(matter_id: str) -> Path:
    return _data_path() / f".{matter_id}.lock"


@contextmanager
def _matter_lock(matter_id: str) -> Iterator[None]:
    """Acquire an exclusive advisory lock for a matter via a sentinel lockfile."""
    lock_path = _lock_path(matter_id)
    lock_path.touch(exist_ok=True)
    with open(lock_path, "r") as lf:
        try:
            fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Write JSON atomically: temp file in same dir → fsync → os.replace."""
    fd, tmp_str = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    tmp_path = Path(tmp_str)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass
        raise


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_matter(
    matter_name: str = "New Matter",
    practice_area: str = "civil",
    jurisdiction: str = "federal",
) -> dict[str, Any]:
    """Create a new legal matter and persist it."""
    matter_id = f"matter_{uuid.uuid4().hex[:12]}"
    matter = {
        "id": matter_id,
        "created_at": _utcnow_iso(),
        "matter_name": matter_name,
        "practice_area": practice_area,
        "jurisdiction": jurisdiction,
        "messages": [],
    }
    with _matter_lock(matter_id):
        _atomic_write_json(_matter_path(matter_id), matter)
    return matter


def get_matter(matter_id: str) -> dict[str, Any] | None:
    """Load a matter from storage, or None if it doesn't exist."""
    path = _matter_path(matter_id)
    if not path.exists():
        return None
    with _matter_lock(matter_id):
        with open(path, "r") as f:
            return json.load(f)


def list_matters() -> list[dict[str, Any]]:
    """List all matters (metadata only). Skips lockfiles and corrupt files."""
    matters = []
    for entry in _data_path().iterdir():
        if entry.suffix != ".json" or entry.name.startswith("."):
            continue
        try:
            with open(entry, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        matters.append({
            "id": data["id"],
            "created_at": data["created_at"],
            "matter_name": data.get("matter_name", "New Matter"),
            "practice_area": data.get("practice_area", "civil"),
            "jurisdiction": data.get("jurisdiction", "federal"),
            "message_count": len(data.get("messages", [])),
        })
    matters.sort(key=lambda m: m["created_at"], reverse=True)
    return matters


def delete_matter(matter_id: str) -> bool:
    """Delete a matter and its lockfile."""
    path = _matter_path(matter_id)
    lock_path = _lock_path(matter_id)
    deleted = False
    try:
        with _matter_lock(matter_id):
            try:
                path.unlink()
                deleted = True
            except FileNotFoundError:
                deleted = False
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass
    return deleted


def append_user_message(
    matter_id: str, content: str, context: str | None = None
) -> None:
    """Append a user message to a matter. RMW inside the lock."""
    with _matter_lock(matter_id):
        path = _matter_path(matter_id)
        if not path.exists():
            raise ValueError(f"Matter {matter_id} not found")
        with open(path, "r") as f:
            matter = json.load(f)
        message = {"role": "user", "content": content}
        if context:
            message["context"] = context
        matter["messages"].append(message)
        _atomic_write_json(path, matter)


def append_assistant_message(
    matter_id: str, deliberation: dict[str, Any]
) -> None:
    """Append a full deliberation result as an assistant message."""
    with _matter_lock(matter_id):
        path = _matter_path(matter_id)
        if not path.exists():
            raise ValueError(f"Matter {matter_id} not found")
        with open(path, "r") as f:
            matter = json.load(f)
        matter["messages"].append({"role": "assistant", **deliberation})
        _atomic_write_json(path, matter)


# Fields that can be updated via `update_matter_metadata`. Anything else in the
# update dict is silently ignored — this is the allowlist, not a generic patch.
_UPDATABLE_FIELDS: frozenset[str] = frozenset(
    {"matter_name", "practice_area", "jurisdiction"}
)


def update_matter_metadata(
    matter_id: str, **updates: str | None
) -> dict[str, Any] | None:
    """Update a matter's metadata fields (name, practice area, jurisdiction).

    Only fields in `_UPDATABLE_FIELDS` are touched. Values that are None are
    ignored (not written as None), so clients can send only the fields they
    want to change. Messages are never modified.

    Returns the updated matter dict, or None if the matter doesn't exist.
    """
    applied = {
        k: v
        for k, v in updates.items()
        if k in _UPDATABLE_FIELDS and v is not None
    }

    with _matter_lock(matter_id):
        path = _matter_path(matter_id)
        if not path.exists():
            return None
        with open(path, "r") as f:
            matter = json.load(f)
        if applied:
            matter.update(applied)
            _atomic_write_json(path, matter)
        return matter
