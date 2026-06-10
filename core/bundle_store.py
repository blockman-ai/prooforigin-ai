import json
import os

from core.evidence_schema import build_evidence_bundle_payload
from core.policy_engine import build_evidence_bundle_hash

BUNDLE_VERSION = 1
BUNDLE_FILENAME = f"v{BUNDLE_VERSION}.bundle.json"
FEEDBACK_EVENTS_FILENAME = "feedback_events.jsonl"

IMMUTABLE_BUNDLE_FIELDS = (
    "report_id",
    "created_at",
    "published_at",
    "report_version",
    "protocol_name",
    "protocol_version",
    "protocol_invariant",
    "protocol_claim_boundary",
    "integrity",
    "evidence_bundle_hash",
    "policy_hash",
    "engine_snapshot_hash",
    "decision_tier",
    "constitution_version",
    "policy_version",
    "confidence_in_estimate",
    "uncertainty_notes",
    "report",
    "policy",
    "prooforigin",
    "consensus",
    "signals",
    "metadata",
    "provenance",
    "adversarial",
    "trace",
    "engine_outputs",
)


class BundleAlreadyExistsError(Exception):
    pass


def get_bundle_dir(evidence_path, file_id):
    return os.path.join(evidence_path, file_id)


def get_bundle_path(evidence_path, file_id, version=BUNDLE_VERSION):
    bundle_dir = get_bundle_dir(evidence_path, file_id)
    return os.path.join(bundle_dir, f"v{version}.bundle.json")


def get_legacy_path(evidence_path, file_id):
    return os.path.join(evidence_path, f"{file_id}.json")


def get_feedback_events_path(evidence_path, file_id):
    return os.path.join(get_bundle_dir(evidence_path, file_id), FEEDBACK_EVENTS_FILENAME)


def extract_immutable_bundle(evidence_record):
    bundle = {key: evidence_record[key] for key in IMMUTABLE_BUNDLE_FIELDS if key in evidence_record}
    bundle.setdefault("report_version", BUNDLE_VERSION)
    bundle.setdefault("published_at", evidence_record.get("created_at"))
    return bundle


def bundle_exists(evidence_path, file_id):
    if os.path.exists(get_bundle_path(evidence_path, file_id)):
        return True
    return os.path.exists(get_legacy_path(evidence_path, file_id))


def write_bundle_once(evidence_path, file_id, evidence_record):
    bundle_path = get_bundle_path(evidence_path, file_id)
    legacy_path = get_legacy_path(evidence_path, file_id)

    if os.path.exists(bundle_path) or os.path.exists(legacy_path):
        raise BundleAlreadyExistsError(
            f"Evidence bundle for {file_id} already exists and is immutable."
        )

    bundle_dir = get_bundle_dir(evidence_path, file_id)
    os.makedirs(bundle_dir, exist_ok=True)

    bundle = extract_immutable_bundle(evidence_record)

    with open(bundle_path, "x", encoding="utf-8") as handle:
        json.dump(bundle, handle, indent=2)

    return bundle_path


def load_evidence_bundle(evidence_path, file_id):
    bundle_path = get_bundle_path(evidence_path, file_id)
    legacy_path = get_legacy_path(evidence_path, file_id)

    if os.path.exists(bundle_path):
        with open(bundle_path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    if os.path.exists(legacy_path):
        with open(legacy_path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    return None


def append_feedback_event(evidence_path, file_id, event):
    bundle_dir = get_bundle_dir(evidence_path, file_id)
    os.makedirs(bundle_dir, exist_ok=True)

    events_path = get_feedback_events_path(evidence_path, file_id)
    with open(events_path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(event) + "\n")


def load_feedback_events(evidence_path, file_id):
    events_path = get_feedback_events_path(evidence_path, file_id)
    events = []

    if not os.path.exists(events_path):
        return events

    with open(events_path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return events


def _report_for_hash(evidence):
    report = dict(evidence.get("report") or {})
    consensus = evidence.get("consensus") or {}

    if evidence.get("decision_tier") and not report.get("decision_tier"):
        report["decision_tier"] = evidence["decision_tier"]

    if consensus.get("weighted") and not report.get("weighted_consensus"):
        report["weighted_consensus"] = consensus["weighted"]

    return report


def recompute_bundle_hash(evidence):
    policy = evidence.get("policy") or {}
    report = _report_for_hash(evidence)

    payload = build_evidence_bundle_payload(
        file_id=evidence.get("report_id"),
        timestamp=evidence.get("created_at"),
        integrity=evidence.get("integrity") or {},
        report=report,
        policy=policy,
        engine_snapshot_hash=evidence.get("engine_snapshot_hash"),
        policy_hash=evidence.get("policy_hash"),
    )
    return build_evidence_bundle_hash(payload)


def verify_bundle_integrity(evidence):
    stored_hash = evidence.get("evidence_bundle_hash")
    recomputed_hash = recompute_bundle_hash(evidence)
    hash_match = bool(stored_hash) and stored_hash == recomputed_hash

    return {
        "bundle_verified": hash_match,
        "bundle_hash": stored_hash,
        "recomputed_hash": recomputed_hash,
        "hash_match": hash_match,
        "report_version": evidence.get("report_version", BUNDLE_VERSION),
    }
