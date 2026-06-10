PUBLIC_REPORT_FIELDS = (
    "file_id",
    "report_version",
    "published_at",
    "public_label",
    "decision_tier",
    "warnings",
    "evidence_bundle_hash",
    "constitution_version",
    "protocol_name",
    "protocol_version",
    "claim_boundary",
    "verification_notice",
)


def build_public_report(evidence):
    if not evidence:
        return None

    from core.protocol import (
        PROTOCOL_DOES_NOT_CLAIM,
        PROTOCOL_NAME,
        PROTOCOL_VERSION,
        VERIFICATION_NOTICE,
    )

    policy = evidence.get("policy") or {}
    report = evidence.get("report") or {}

    warnings = policy.get("warnings")
    if warnings is None:
        warnings = report.get("warnings", [])

    return {
        "file_id": evidence.get("report_id"),
        "report_version": evidence.get("report_version", 1),
        "published_at": evidence.get("published_at") or evidence.get("created_at"),
        "public_label": policy.get("public_label"),
        "decision_tier": evidence.get("decision_tier"),
        "warnings": warnings or [],
        "evidence_bundle_hash": evidence.get("evidence_bundle_hash"),
        "constitution_version": evidence.get("constitution_version"),
        "protocol_name": evidence.get("protocol_name", PROTOCOL_NAME),
        "protocol_version": evidence.get("protocol_version", PROTOCOL_VERSION),
        "claim_boundary": evidence.get("protocol_claim_boundary", PROTOCOL_DOES_NOT_CLAIM),
        "verification_notice": VERIFICATION_NOTICE,
    }
