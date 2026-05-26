from fastapi import APIRouter
from pydantic import BaseModel
import json
import os
from datetime import datetime


router = APIRouter()


class FeedbackPayload(BaseModel):
    file_id: str
    user_label: str
    user_confidence: str | None = None
    notes: str | None = None


@router.post("/feedback")
def submit_feedback(payload: FeedbackPayload):
    os.makedirs("data", exist_ok=True)

    entry = {
        "file_id": payload.file_id,
        "timestamp": datetime.utcnow().isoformat(),
        "user_label": payload.user_label,
        "user_confidence": payload.user_confidence,
        "notes": payload.notes,
        "status": "received",
    }

    with open("data/user_feedback_log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    return {
        "status": "feedback_received",
        "file_id": payload.file_id,
    }
