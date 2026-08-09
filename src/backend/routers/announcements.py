"""
Announcements endpoints for the High School Management System API
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
from datetime import date
from pydantic import BaseModel

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


class AnnouncementCreate(BaseModel):
    message: str
    expires_on: date
    starts_on: Optional[date] = None


class AnnouncementUpdate(BaseModel):
    message: Optional[str] = None
    expires_on: Optional[date] = None
    starts_on: Optional[date] = None


def _require_teacher(username: Optional[str]):
    if not username:
        raise HTTPException(status_code=401, detail="Authentication required")
    if not teachers_collection.find_one({"_id": username}):
        raise HTTPException(status_code=401, detail="Invalid credentials")


def _serialize(doc) -> Dict[str, Any]:
    doc["id"] = str(doc.pop("_id"))
    return doc


@router.get("", response_model=List[Dict[str, Any]])
def get_active_announcements():
    """Return announcements that are currently active (within date range)."""
    today = date.today().isoformat()
    query = {
        "expires_on": {"$gte": today},
        "$or": [
            {"starts_on": None},
            {"starts_on": {"$lte": today}},
        ],
    }
    return [_serialize(doc) for doc in announcements_collection.find(query)]


@router.get("/all", response_model=List[Dict[str, Any]])
def get_all_announcements(teacher_username: Optional[str] = None):
    """Return all announcements (active and expired). Requires authentication."""
    _require_teacher(teacher_username)
    return [_serialize(doc) for doc in announcements_collection.find()]


@router.post("", response_model=Dict[str, Any])
def create_announcement(body: AnnouncementCreate, teacher_username: Optional[str] = None):
    """Create a new announcement. Requires authentication."""
    _require_teacher(teacher_username)
    doc = {
        "message": body.message,
        "expires_on": body.expires_on.isoformat(),
        "starts_on": body.starts_on.isoformat() if body.starts_on else None,
    }
    result = announcements_collection.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _serialize(doc)


@router.put("/{announcement_id}", response_model=Dict[str, Any])
def update_announcement(announcement_id: str, body: AnnouncementUpdate, teacher_username: Optional[str] = None):
    """Update an existing announcement. Requires authentication."""
    _require_teacher(teacher_username)
    from bson import ObjectId
    try:
        oid = ObjectId(announcement_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")

    updates = {}
    if body.message is not None:
        updates["message"] = body.message
    if body.expires_on is not None:
        updates["expires_on"] = body.expires_on.isoformat()
    if body.starts_on is not None:
        updates["starts_on"] = body.starts_on.isoformat()
    elif body.starts_on == "" or (body.model_fields_set and "starts_on" in body.model_fields_set and body.starts_on is None):
        updates["starts_on"] = None

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = announcements_collection.find_one_and_update(
        {"_id": oid},
        {"$set": updates},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return _serialize(result)


@router.delete("/{announcement_id}")
def delete_announcement(announcement_id: str, teacher_username: Optional[str] = None):
    """Delete an announcement. Requires authentication."""
    _require_teacher(teacher_username)
    from bson import ObjectId
    try:
        oid = ObjectId(announcement_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")

    result = announcements_collection.delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return {"message": "Announcement deleted"}
