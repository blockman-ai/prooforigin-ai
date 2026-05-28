import json
import os


def verify_proof_record(file_id: str):
    evidence_path = f"data/evidence/{file_id}.json"

    if not os.path.exists(evidence_path):
        return {
            "verified": False,
            "file_id": file_id,
            "error": "Evidence record not found",
        }

    with open(evidence_path, "r", encoding="utf-8") as f:
        evidence = json.load(f)

    report = evidence.get("report", {})
    integrity = report.get("integrity", {})
    bitcoin_lite_anchor = report.get("bitcoin_lite_anchor", {})

    original_sha256 = integrity.get("original_sha256")
    analysis_sha256 = integrity.get("analysis_sha256")
    merkle_root = bitcoin_lite_anchor.get("merkle_root")
    anchor_status = bitcoin_lite_anchor.get("status", "queued")

    verified = bool(original_sha256 and analysis_sha256)

    return {
        "verified": verified,
        "file_id": file_id,
        "original_sha256": original_sha256,
        "analysis_sha256": analysis_sha256,
        "file_name": integrity.get("file_name"),
        "file_type": integrity.get("original_file_type"),
        "verification_status": integrity.get("verification_status"),
        "tamper_evidence": integrity.get("tamper_evidence"),
        "bitcoin_lite_anchor": bitcoin_lite_anchor,
        "merkle_root": merkle_root,
        "anchor_status": anchor_status,
        "message": (
            "Proof record verified from stored evidence."
            if verified
            else "Proof record exists but is missing required hashes."
        ),
    }
