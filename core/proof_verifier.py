import json
import os


def _extract_integrity(evidence):
    report = evidence.get("report", {})
    integrity = report.get("integrity") or evidence.get("integrity", {})

    original_sha256 = integrity.get("original_sha256") or integrity.get("sha256")
    analysis_sha256 = integrity.get("analysis_sha256")

    return integrity, original_sha256, analysis_sha256


def _extract_bitcoin_lite_anchor(evidence):
    report = evidence.get("report", {})
    return report.get("bitcoin_lite_anchor") or evidence.get("bitcoin_lite_anchor", {})


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

    integrity, original_sha256, analysis_sha256 = _extract_integrity(evidence)
    bitcoin_lite_anchor = _extract_bitcoin_lite_anchor(evidence)

    merkle_root = bitcoin_lite_anchor.get("merkle_root")
    anchor_status = bitcoin_lite_anchor.get("status", "queued")

    verified = bool(original_sha256 and analysis_sha256)
    legacy_only = bool(original_sha256 and not analysis_sha256)

    if verified:
        message = "Proof record verified from stored evidence."
    elif legacy_only:
        message = (
            "Legacy evidence record found with original hash only; "
            "analysis hash missing."
        )
    else:
        message = "Proof record exists but is missing required hashes."

    return {
        "verified": verified,
        "legacy_partial": legacy_only,
        "file_id": file_id,
        "original_sha256": original_sha256,
        "analysis_sha256": analysis_sha256,
        "file_name": integrity.get("file_name"),
        "file_type": integrity.get("original_file_type") or integrity.get("file_type"),
        "verification_status": integrity.get("verification_status"),
        "tamper_evidence": integrity.get("tamper_evidence"),
        "bitcoin_lite_anchor": bitcoin_lite_anchor,
        "merkle_root": merkle_root,
        "anchor_status": anchor_status,
        "message": message,
    }
