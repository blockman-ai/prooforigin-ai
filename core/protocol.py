PROTOCOL_NAME = "Proof-of-Origin"

PROTOCOL_VERSION = "0.1.0"

PROTOCOL_INVARIANT = (
    "ProofOrigin proves the existence, state, lineage, and evaluation context "
    "of a digital claim at a specific point in time — not absolute truth."
)

PROTOCOL_DOES_NOT_CLAIM = (
    "ProofOrigin does not prove absolute truth, legal guilt, moral certainty, "
    "or that a file is definitively AI-generated or human-made."
)

VERIFICATION_NOTICE = (
    "This is an evidence evaluation record at a point in time. "
    "It documents forensic signals and policy context; it does not prove absolute truth."
)

REQUIRED_BUNDLE_HASH_FIELDS = (
    "report_id",
    "created_at",
    "integrity",
    "summary",
    "weighted_consensus",
    "decision_tier",
    "policy_summary",
    "engine_snapshot_hash",
    "policy_hash",
)

REQUIRED_VERIFICATION_STEPS = (
    "load_immutable_bundle",
    "recompute_evidence_bundle_hash",
    "compare_stored_and_recomputed_hash",
    "confirm_file_hash_fields_present",
    "optional_uploaded_file_hash_match",
    "report_verification_scope_without_truth_claim",
)

ANCHOR_LEAF_FIELD = "evidence_bundle_hash"

VERIFIED_SCOPE_BUNDLE_AND_FILE_HASH = "bundle_and_file_hash"
VERIFIED_SCOPE_UPLOAD_FILE_HASH = "upload_file_hash"
VERIFIED_SCOPE_PARTIAL = "partial"
VERIFIED_SCOPE_NONE = "none"
