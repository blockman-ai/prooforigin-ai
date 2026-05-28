import json
import os
import hashlib
from datetime import datetime, timezone

PENDING_PATH = "data/anchors/anchor_pending.jsonl"


def sha256_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def ensure_anchor_folder():
    os.makedirs("data/anchors", exist_ok=True)


def build_report_hash(report):
    clean_report = json.dumps(report, sort_keys=True, default=str)
    return sha256_text(clean_report)


def queue_lite_anchor(file_id, integrity, verdict, report):
    ensure_anchor_folder()

    report_hash = build_report_hash(report)

    anchor_record = {
        "anchor_type": "prooforigin_lite",
        "file_id": file_id,
        "report_hash": report_hash,
        "original_sha256": integrity.get("original_sha256"),
        "analysis_sha256": integrity.get("analysis_sha256"),
        "verdict": verdict,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending_batch",
        "network": "bitcoin_lite_pending",
    }

    with open(PENDING_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(anchor_record) + "\n")

    return anchor_record
