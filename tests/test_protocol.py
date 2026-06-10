import json
import os
import tempfile
import unittest

from core.bitcoin_lite_anchor import extract_anchor_leaf, queue_lite_anchor
from core.bundle_store import get_bundle_path, write_bundle_once
from core.engine_sanitize import sanitize_external_engines
from core.evidence_schema import build_evidence_record
from core.merkle_settlement import build_merkle_root
from core.policy_engine import apply_constitution_policy
from core.proof_verifier import verify_proof_record
from core.public_report import PUBLIC_REPORT_FIELDS, build_public_report
from core.protocol import (
    ANCHOR_LEAF_FIELD,
    PROTOCOL_DOES_NOT_CLAIM,
    PROTOCOL_INVARIANT,
    PROTOCOL_NAME,
    PROTOCOL_VERSION,
    REQUIRED_BUNDLE_HASH_FIELDS,
    REQUIRED_VERIFICATION_STEPS,
    VERIFIED_SCOPE_BUNDLE_AND_FILE_HASH,
    VERIFICATION_NOTICE,
)
from core.consensus_engine import calculate_weighted_consensus


def _sample_report():
    engines = {
        "prooforigin": {"status": "complete", "score": 12, "label": "Likely Human-Made"},
        "sightengine": {"status": "unconfigured", "score": None},
        "openai_vision": {"status": "unconfigured", "score": None},
    }
    consensus = calculate_weighted_consensus(engines)
    policy = apply_constitution_policy(
        final_consensus=consensus,
        original_consensus=consensus,
        engine_arbitration={"disagreement_detected": False, "score_spread": 0},
        external_engines=engines,
    )

    return {
        "summary": {"label": "Likely Human-Made", "ai_score": 12},
        "integrity": {
            "original_sha256": "abc123original",
            "analysis_sha256": "def456analysis",
            "file_name": "sample.jpg",
            "original_file_type": "image/jpeg",
            "verification_status": "hash_recorded",
            "tamper_evidence": "available",
        },
        "weighted_consensus": consensus,
        "decision_tier": policy["decision_tier"],
        "confidence_in_estimate": policy["confidence_in_estimate"],
        "uncertainty_notes": policy["uncertainty_notes"],
        "warnings": policy["warnings"],
        "policy": policy,
    }


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.evidence_path = os.path.join(self.tmpdir.name, "data", "evidence")
        self.anchor_path = os.path.join(self.tmpdir.name, "data", "anchors")
        os.makedirs(self.evidence_path, exist_ok=True)
        os.makedirs(self.anchor_path, exist_ok=True)

    def tearDown(self):
        self.tmpdir.cleanup()

    def _build_evidence(self, file_id="protocol-test-id"):
        report = _sample_report()
        engines = sanitize_external_engines(
            {
                "prooforigin": {"status": "complete", "score": 12, "label": "Likely Human-Made"},
            }
        )
        return build_evidence_record(
            file_id=file_id,
            timestamp="2026-01-01T00:00:00",
            report=report,
            external_engines=engines,
            policy=report["policy"],
        )

    def test_protocol_constants_are_stable(self):
        self.assertEqual(PROTOCOL_NAME, "Proof-of-Origin")
        self.assertEqual(PROTOCOL_VERSION, "0.1.0")
        self.assertIn("not absolute truth", PROTOCOL_INVARIANT.lower())
        self.assertIn("does not prove absolute truth", PROTOCOL_DOES_NOT_CLAIM.lower())
        self.assertEqual(ANCHOR_LEAF_FIELD, "evidence_bundle_hash")
        self.assertIn("report_id", REQUIRED_BUNDLE_HASH_FIELDS)
        self.assertIn("recompute_evidence_bundle_hash", REQUIRED_VERIFICATION_STEPS)

    def test_bundle_includes_protocol_metadata(self):
        evidence = self._build_evidence()
        write_bundle_once(self.evidence_path, "protocol-test-id", evidence)

        bundle_path = get_bundle_path(self.evidence_path, "protocol-test-id")
        with open(bundle_path, "r", encoding="utf-8") as handle:
            stored = json.load(handle)

        self.assertEqual(stored["protocol_name"], PROTOCOL_NAME)
        self.assertEqual(stored["protocol_version"], PROTOCOL_VERSION)
        self.assertEqual(stored["protocol_invariant"], PROTOCOL_INVARIANT)
        self.assertEqual(stored["protocol_claim_boundary"], PROTOCOL_DOES_NOT_CLAIM)

    def test_public_report_includes_claim_boundary(self):
        evidence = self._build_evidence(file_id="public-protocol-id")
        write_bundle_once(self.evidence_path, "public-protocol-id", evidence)

        report = build_public_report(evidence)

        for field in PUBLIC_REPORT_FIELDS:
            self.assertIn(field, report)

        self.assertEqual(report["protocol_name"], PROTOCOL_NAME)
        self.assertEqual(report["protocol_version"], PROTOCOL_VERSION)
        self.assertEqual(report["claim_boundary"], PROTOCOL_DOES_NOT_CLAIM)
        self.assertEqual(report["verification_notice"], VERIFICATION_NOTICE)
        self.assertIn("does not prove absolute truth", report["verification_notice"].lower())

    def test_verify_proof_returns_verified_scope(self):
        evidence = self._build_evidence(file_id="verify-scope-id")
        write_bundle_once(self.evidence_path, "verify-scope-id", evidence)

        original_cwd = os.getcwd()
        os.chdir(self.tmpdir.name)
        try:
            result = verify_proof_record("verify-scope-id", evidence_path="data/evidence")
        finally:
            os.chdir(original_cwd)

        self.assertTrue(result["verified"])
        self.assertFalse(result["truth_verified"])
        self.assertEqual(result["verified_scope"], VERIFIED_SCOPE_BUNDLE_AND_FILE_HASH)
        self.assertEqual(result["claim_boundary"], PROTOCOL_DOES_NOT_CLAIM)
        self.assertEqual(result["protocol_version"], PROTOCOL_VERSION)
        self.assertIn("not absolute truth", result["message"].lower())

    def test_merkle_anchor_uses_evidence_bundle_hash(self):
        evidence = self._build_evidence(file_id="anchor-leaf-id")
        bundle_hash = evidence["evidence_bundle_hash"]

        pending_file = os.path.join(self.anchor_path, "anchor_pending.jsonl")

        import core.bitcoin_lite_anchor as anchor_module
        import core.merkle_settlement as merkle_module

        original_anchor_path = anchor_module.PENDING_PATH
        original_merkle_path = merkle_module.PENDING_PATH

        anchor_module.PENDING_PATH = pending_file
        merkle_module.PENDING_PATH = pending_file

        try:
            record = queue_lite_anchor(
                file_id="anchor-leaf-id",
                integrity=evidence["integrity"],
                verdict="Likely Human-Made",
                evidence_bundle_hash=bundle_hash,
            )

            self.assertEqual(record[ANCHOR_LEAF_FIELD], bundle_hash)
            self.assertEqual(record["anchor_leaf_field"], ANCHOR_LEAF_FIELD)
            self.assertNotIn("report_hash", record)

            leaf = extract_anchor_leaf(record)
            self.assertEqual(leaf, bundle_hash)

            root = build_merkle_root([leaf])
            self.assertEqual(len(root), 64)
        finally:
            anchor_module.PENDING_PATH = original_anchor_path
            merkle_module.PENDING_PATH = original_merkle_path

    def test_legacy_anchor_record_falls_back_to_report_hash(self):
        legacy_record = {
            "file_id": "legacy-id",
            "report_hash": "a" * 64,
        }
        self.assertEqual(extract_anchor_leaf(legacy_record), "a" * 64)


if __name__ == "__main__":
    unittest.main()
