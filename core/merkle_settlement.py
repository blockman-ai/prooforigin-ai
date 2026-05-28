import json
import os
import hashlib
import uuid
from datetime import datetime, timezone

PENDING_PATH = "data/anchors/anchor_pending.jsonl"
BATCH_DIR = "data/anchors/batches"


def sha256_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def ensure_dirs():
    os.makedirs("data/anchors", exist_ok=True)
    os.makedirs(BATCH_DIR, exist_ok=True)


def merkle_parent(left, right):
    return sha256_text(left + right)


def build_merkle_root(hashes):
    if not hashes:
        return None

    level = hashes[:]

    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])

        next_level = []

        for i in range(0, len(level), 2):
            next_level.append(merkle_parent(level[i], level[i + 1]))

        level = next_level

    return level[0]


def read_pending_records():
    ensure_dirs()

    if not os.path.exists(PENDING_PATH):
        return []

    records = []

    with open(PENDING_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            try:
                records.append(json.loads(line))
            except Exception:
                continue

    return records


def create_merkle_batch():
    ensure_dirs()

    records = read_pending_records()

    pending = [
        record for record in records
        if record.get("status") == "pending_batch"
    ]

    if not pending:
        return {
            "success": False,
            "message": "No pending anchor records found.",
            "count": 0,
        }

    report_hashes = [
        record.get("report_hash")
        for record in pending
        if record.get("report_hash")
    ]

    merkle_root = build_merkle_root(report_hashes)

    batch_id = str(uuid.uuid4())

    batch = {
        "success": True,
        "batch_id": batch_id,
        "anchor_type": "prooforigin_merkle_batch",
        "network": "bitcoin_lite_pending",
        "status": "merkle_root_created",
        "record_count": len(pending),
        "merkle_root": merkle_root,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "bitcoin_anchor_status": "not_broadcast",
        "bitcoin_txid": None,
        "records": pending,
    }

    batch_path = f"{BATCH_DIR}/{batch_id}.json"

    with open(batch_path, "w", encoding="utf-8") as f:
        json.dump(batch, f, indent=2)

    remaining = [
        record for record in records
        if record.get("status") != "pending_batch"
    ]

    with open(PENDING_PATH, "w", encoding="utf-8") as f:
        for record in remaining:
            f.write(json.dumps(record) + "\n")

    return batch
