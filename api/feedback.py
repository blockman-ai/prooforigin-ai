from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel
import json
import os
from datetime import datetime

from core.bundle_store import append_feedback_event, load_evidence_bundle


router = APIRouter()

EVIDENCE_PATH = "data/evidence"


class FeedbackPayload(BaseModel):
    file_id: str
    user_label: str
    user_confidence: Optional[str] = None
    notes: Optional[str] = None


VALID_LABELS = {
    "correct",
    "wrong",
    "ai",
    "human",
    "edited",
    "disputed",
}


def empty_stats():
    return {
        "total_feedback": 0,
        "correct_votes": 0,
        "wrong_votes": 0,
        "ai_votes": 0,
        "human_votes": 0,
        "edited_votes": 0,
        "disputed_votes": 0,
        "unique_files": 0,
    }


@router.post("/feedback")
def submit_feedback(payload: FeedbackPayload):
    os.makedirs("data", exist_ok=True)

    label = payload.user_label.lower().strip()

    if label not in VALID_LABELS:
        return {
            "success": False,
            "error": "Invalid feedback label",
            "allowed_labels": list(VALID_LABELS),
        }

    timestamp = datetime.utcnow().isoformat()

    entry = {
        "file_id": payload.file_id,
        "timestamp": timestamp,
        "user_label": label,
        "user_confidence": payload.user_confidence,
        "notes": payload.notes,
        "status": "received",
    }

    with open("data/user_feedback_log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    bundle = load_evidence_bundle(EVIDENCE_PATH, payload.file_id)
    if bundle:
        append_feedback_event(EVIDENCE_PATH, payload.file_id, entry)

    print(f"[ProofOrigin] Feedback received for {payload.file_id}: {label}")

    return {
        "success": True,
        "status": "feedback_received",
        "file_id": payload.file_id,
        "label": label,
        "bundle_mutated": False,
    }


@router.get("/feedback/stats")
def feedback_stats():
    log_path = "data/user_feedback_log.jsonl"

    stats = empty_stats()
    files = set()

    if not os.path.exists(log_path):
        return {
            "success": True,
            "stats": stats,
            "message": "No feedback recorded yet.",
        }

    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            label = entry.get("user_label")
            file_id = entry.get("file_id")

            if file_id:
                files.add(file_id)

            stats["total_feedback"] += 1

            if label == "correct":
                stats["correct_votes"] += 1
            elif label == "wrong":
                stats["wrong_votes"] += 1
            elif label == "ai":
                stats["ai_votes"] += 1
            elif label == "human":
                stats["human_votes"] += 1
            elif label == "edited":
                stats["edited_votes"] += 1
            elif label == "disputed":
                stats["disputed_votes"] += 1

    stats["unique_files"] = len(files)

    return {
        "success": True,
        "stats": stats,
    }
