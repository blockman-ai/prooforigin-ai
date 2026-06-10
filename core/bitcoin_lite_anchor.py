import json
import os
from datetime import datetime, timezone

from core.protocol import ANCHOR_LEAF_FIELD

PENDING_PATH = "data/anchors/anchor_pending.jsonl"


def ensure_anchor_folder():
    os.makedirs("data/anchors", exist_ok=True)


def queue_lite_anchor(file_id, integrity, verdict, evidence_bundle_hash, report=None):
    ensure_anchor_folder()

    if not evidence_bundle_hash:
        raise ValueError("evidence_bundle_hash is required for anchor queueing.")

    anchor_record = {
        "anchor_type": "prooforigin_lite",
        "file_id": file_id,
        ANCHOR_LEAF_FIELD: evidence_bundle_hash,
        "original_sha256": integrity.get("original_sha256"),
        "analysis_sha256": integrity.get("analysis_sha256"),
        "verdict": verdict,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending_batch",
        "network": "bitcoin_lite_pending",
        "anchor_leaf_field": ANCHOR_LEAF_FIELD,
    }

    with open(PENDING_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(anchor_record) + "\n")

    return anchor_record


def extract_anchor_leaf(record):
    leaf = record.get(ANCHOR_LEAF_FIELD)
    if leaf:
        return leaf
    return record.get("report_hash")
