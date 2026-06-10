import os

from core.bundle_store import load_evidence_bundle, verify_bundle_integrity
from core.protocol import (
    PROTOCOL_DOES_NOT_CLAIM,
    PROTOCOL_VERSION,
    VERIFIED_SCOPE_BUNDLE_AND_FILE_HASH,
    VERIFIED_SCOPE_NONE,
    VERIFIED_SCOPE_PARTIAL,
)

EVIDENCE_PATH = "data/evidence"


def _extract_integrity(evidence):
    report = evidence.get("report", {})
    integrity = report.get("integrity") or evidence.get("integrity", {})

    original_sha256 = integrity.get("original_sha256") or integrity.get("sha256")
    analysis_sha256 = integrity.get("analysis_sha256")

    return integrity, original_sha256, analysis_sha256


def _extract_bitcoin_lite_anchor(evidence):
    report = evidence.get("report", {})
    return report.get("bitcoin_lite_anchor") or evidence.get("bitcoin_lite_anchor", {})


def _resolve_claim_boundary(evidence):
    return evidence.get("protocol_claim_boundary", PROTOCOL_DOES_NOT_CLAIM)


def _resolve_protocol_version(evidence):
    return evidence.get("protocol_version", PROTOCOL_VERSION)


def _resolve_verified_scope(hash_presence_verified, hash_match, legacy_only):
    if hash_presence_verified and hash_match:
        return VERIFIED_SCOPE_BUNDLE_AND_FILE_HASH

    if legacy_only or hash_presence_verified or hash_match:
        return VERIFIED_SCOPE_PARTIAL

    return VERIFIED_SCOPE_NONE


def verify_proof_record(file_id: str, evidence_path=EVIDENCE_PATH):
    evidence = load_evidence_bundle(evidence_path, file_id)

    if evidence is None:
        return {
            "verified": False,
            "file_id": file_id,
            "error": "Evidence record not found",
            "verified_scope": VERIFIED_SCOPE_NONE,
            "claim_boundary": PROTOCOL_DOES_NOT_CLAIM,
            "protocol_version": PROTOCOL_VERSION,
            "truth_verified": False,
        }

    integrity, original_sha256, analysis_sha256 = _extract_integrity(evidence)
    bitcoin_lite_anchor = _extract_bitcoin_lite_anchor(evidence)
    bundle_check = verify_bundle_integrity(evidence)

    merkle_root = bitcoin_lite_anchor.get("merkle_root")
    anchor_status = bitcoin_lite_anchor.get("status", "queued")

    hash_presence_verified = bool(original_sha256 and analysis_sha256)
    legacy_only = bool(original_sha256 and not analysis_sha256)
    hash_match = bundle_check["hash_match"]
    verified = hash_presence_verified and hash_match
    verified_scope = _resolve_verified_scope(hash_presence_verified, hash_match, legacy_only)
    claim_boundary = _resolve_claim_boundary(evidence)
    protocol_version = _resolve_protocol_version(evidence)

    if verified:
        message = (
            "Evidence bundle integrity and stored file hashes verified. "
            "This confirms record state at publication time — not absolute truth."
        )
    elif hash_presence_verified and not hash_match:
        message = (
            "Stored file hashes present but evidence bundle integrity check failed. "
            "Record may have been tampered with."
        )
    elif legacy_only:
        message = (
            "Legacy evidence record found with original hash only; "
            "analysis hash missing. Bundle integrity not fully confirmed."
        )
    else:
        message = "Proof record exists but is missing required hashes."

    return {
        "verified": verified,
        "truth_verified": False,
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
        "bundle_verified": bundle_check["bundle_verified"],
        "bundle_hash": bundle_check["bundle_hash"],
        "hash_match": hash_match,
        "report_version": bundle_check["report_version"],
        "verified_scope": verified_scope,
        "claim_boundary": claim_boundary,
        "protocol_version": protocol_version,
        "message": message,
    }


def verify_uploaded_file_hash(file_id, uploaded_sha256, evidence_path=EVIDENCE_PATH):
    evidence = load_evidence_bundle(evidence_path, file_id)

    if evidence is None:
        return {
            "success": False,
            "file_id": file_id,
            "error": "Evidence record not found",
            "truth_verified": False,
            "claim_boundary": PROTOCOL_DOES_NOT_CLAIM,
        }

    integrity, original_sha256, _analysis_sha256 = _extract_integrity(evidence)
    hash_match = bool(original_sha256) and uploaded_sha256 == original_sha256

    return {
        "success": True,
        "file_id": file_id,
        "original_sha256": original_sha256,
        "uploaded_sha256": uploaded_sha256,
        "hash_match": hash_match,
        "file_name": integrity.get("file_name"),
        "verification_status": integrity.get("verification_status"),
        "truth_verified": False,
        "claim_boundary": _resolve_claim_boundary(evidence),
        "protocol_version": _resolve_protocol_version(evidence),
        "message": (
            "Uploaded file hash matches stored record."
            if hash_match
            else "Uploaded file hash does not match stored record."
        ),
    }
