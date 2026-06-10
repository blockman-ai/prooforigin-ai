from core.evidence_schema import build_protocol_metadata
from core.protocol import (
    PROTOCOL_DOES_NOT_CLAIM,
    PROTOCOL_NAME,
    PROTOCOL_VERSION,
    VERIFICATION_NOTICE,
    VERIFIED_SCOPE_BUNDLE_AND_FILE_HASH,
    VERIFIED_SCOPE_NONE,
    VERIFIED_SCOPE_UPLOAD_FILE_HASH,
)


REQUIRED_WEBSITE_FIELDS = (
    "public_label",
    "decision_tier",
    "verification_notice",
    "claim_boundary",
    "protocol_name",
    "protocol_version",
    "evidence_bundle_hash",
    "verified_scope",
    "truth_verified",
)


def _resolve_verified_scope_for_publish(evidence_bundle_hash, integrity=None):
    if not evidence_bundle_hash:
        return VERIFIED_SCOPE_NONE

    integrity = integrity or {}
    has_file_hashes = bool(
        integrity.get("original_sha256") and integrity.get("analysis_sha256")
    )
    if has_file_hashes:
        return VERIFIED_SCOPE_BUNDLE_AND_FILE_HASH

    return VERIFIED_SCOPE_NONE


def build_website_contract_fields(
    *,
    policy=None,
    decision_tier=None,
    evidence_bundle_hash=None,
    protocol_name=None,
    protocol_version=None,
    protocol_claim_boundary=None,
    verified_scope=None,
    truth_verified=False,
):
    policy = policy or {}
    protocol = build_protocol_metadata()

    return {
        "public_label": policy.get("public_label"),
        "decision_tier": decision_tier or policy.get("decision_tier"),
        "verification_notice": VERIFICATION_NOTICE,
        "claim_boundary": protocol_claim_boundary or PROTOCOL_DOES_NOT_CLAIM,
        "protocol_name": protocol_name or protocol.get("protocol_name", PROTOCOL_NAME),
        "protocol_version": protocol_version or protocol.get("protocol_version", PROTOCOL_VERSION),
        "evidence_bundle_hash": evidence_bundle_hash,
        "verified_scope": verified_scope,
        "truth_verified": truth_verified,
    }


def build_website_contract_from_analyze(result, integrity=None):
    policy = result.get("policy") or {}
    protocol = build_protocol_metadata()

    return build_website_contract_fields(
        policy=policy,
        decision_tier=result.get("decision_tier"),
        evidence_bundle_hash=result.get("evidence_bundle_hash"),
        protocol_name=result.get("protocol_name") or protocol["protocol_name"],
        protocol_version=result.get("protocol_version") or protocol["protocol_version"],
        protocol_claim_boundary=result.get("protocol_claim_boundary")
        or protocol["protocol_claim_boundary"],
        verified_scope=_resolve_verified_scope_for_publish(
            result.get("evidence_bundle_hash"),
            integrity=integrity or result.get("integrity"),
        ),
        truth_verified=False,
    )


def build_website_contract_from_evidence(evidence, verified_scope=None):
    policy = evidence.get("policy") or {}
    protocol = build_protocol_metadata()

    if verified_scope is None:
        integrity = evidence.get("integrity") or {}
        verified_scope = _resolve_verified_scope_for_publish(
            evidence.get("evidence_bundle_hash"),
            integrity=integrity,
        )

    return build_website_contract_fields(
        policy=policy,
        decision_tier=evidence.get("decision_tier"),
        evidence_bundle_hash=evidence.get("evidence_bundle_hash"),
        protocol_name=evidence.get("protocol_name") or protocol["protocol_name"],
        protocol_version=evidence.get("protocol_version") or protocol["protocol_version"],
        protocol_claim_boundary=evidence.get("protocol_claim_boundary")
        or protocol["protocol_claim_boundary"],
        verified_scope=verified_scope,
        truth_verified=False,
    )


def with_camel_case_contract(contract):
    return {
        **contract,
        "publicLabel": contract.get("public_label"),
        "decisionTier": contract.get("decision_tier"),
        "verificationNotice": contract.get("verification_notice"),
        "claimBoundary": contract.get("claim_boundary"),
        "protocolName": contract.get("protocol_name"),
        "protocolVersion": contract.get("protocol_version"),
        "evidenceBundleHash": contract.get("evidence_bundle_hash"),
        "verifiedScope": contract.get("verified_scope"),
        "truthVerified": contract.get("truth_verified"),
    }
