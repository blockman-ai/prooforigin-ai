import hashlib
import json
import os
import tempfile
import unittest

from core.bundle_store import (
    BUNDLE_FILENAME,
    BundleAlreadyExistsError,
    append_feedback_event,
    get_bundle_path,
    load_evidence_bundle,
    verify_bundle_integrity,
    write_bundle_once,
)
from core.dataset_logger import DatasetLogger
from core.engine_sanitize import sanitize_external_engines
from core.evidence_schema import build_evidence_record
from core.policy_engine import apply_constitution_policy
from core.proof_verifier import verify_proof_record, verify_uploaded_file_hash
from core.public_report import PUBLIC_REPORT_FIELDS, build_public_report
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


class ImmutabilityHardeningTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.evidence_path = os.path.join(self.tmpdir.name, "data", "evidence")
        self.training_path = os.path.join(self.tmpdir.name, "data", "training")
        self.log_path = os.path.join(self.tmpdir.name, "data", "realtime_analysis_log.jsonl")
        os.makedirs(self.evidence_path, exist_ok=True)
        os.makedirs(self.training_path, exist_ok=True)

    def tearDown(self):
        self.tmpdir.cleanup()

    def _build_evidence(self, file_id="immutable-test-id"):
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

    def test_bundle_immutable_refuses_overwrite(self):
        evidence = self._build_evidence()
        write_bundle_once(self.evidence_path, "immutable-test-id", evidence)

        bundle_path = get_bundle_path(self.evidence_path, "immutable-test-id")
        self.assertTrue(os.path.exists(bundle_path))
        self.assertTrue(bundle_path.endswith(BUNDLE_FILENAME))

        with open(bundle_path, "r", encoding="utf-8") as handle:
            stored = json.load(handle)

        self.assertEqual(stored["report_version"], 1)
        self.assertEqual(stored["published_at"], "2026-01-01T00:00:00")
        self.assertNotIn("feedback", stored)
        self.assertNotIn("training_data", stored)

        with self.assertRaises(BundleAlreadyExistsError):
            write_bundle_once(self.evidence_path, "immutable-test-id", evidence)

    def test_feedback_append_only_does_not_mutate_bundle(self):
        evidence = self._build_evidence()
        file_id = "feedback-test-id"
        write_bundle_once(self.evidence_path, file_id, evidence)

        bundle_path = get_bundle_path(self.evidence_path, file_id)
        with open(bundle_path, "rb") as handle:
            original_bytes = handle.read()

        event = {
            "file_id": file_id,
            "timestamp": "2026-01-02T00:00:00",
            "user_label": "correct",
            "status": "received",
        }
        append_feedback_event(self.evidence_path, file_id, event)
        append_feedback_event(self.evidence_path, file_id, {
            **event,
            "user_label": "wrong",
            "timestamp": "2026-01-03T00:00:00",
        })

        with open(bundle_path, "rb") as handle:
            after_bytes = handle.read()

        self.assertEqual(original_bytes, after_bytes)

        loaded = load_evidence_bundle(self.evidence_path, file_id)
        self.assertNotIn("feedback", loaded)

    def test_verify_bundle_hash(self):
        evidence = self._build_evidence(file_id="verify-bundle-id")
        write_bundle_once(self.evidence_path, "verify-bundle-id", evidence)

        original_cwd = os.getcwd()
        os.chdir(self.tmpdir.name)
        try:
            result = verify_proof_record("verify-bundle-id", evidence_path="data/evidence")
        finally:
            os.chdir(original_cwd)

        self.assertTrue(result["hash_match"])
        self.assertTrue(result["bundle_verified"])
        self.assertEqual(result["report_version"], 1)
        self.assertTrue(result["verified"])
        self.assertEqual(len(result["bundle_hash"]), 64)

    def test_verify_uploaded_file_hash(self):
        matching_hash = hashlib.sha256(b"original-file-bytes").hexdigest()
        mismatch_hash = hashlib.sha256(b"tampered-file-bytes").hexdigest()

        report = _sample_report()
        report["integrity"]["original_sha256"] = matching_hash
        engines = sanitize_external_engines(
            {
                "prooforigin": {"status": "complete", "score": 12, "label": "Likely Human-Made"},
            }
        )
        evidence = build_evidence_record(
            file_id="upload-verify-id",
            timestamp="2026-01-01T00:00:00",
            report=report,
            external_engines=engines,
            policy=report["policy"],
        )
        write_bundle_once(self.evidence_path, "upload-verify-id", evidence)

        match_result = verify_uploaded_file_hash(
            "upload-verify-id",
            matching_hash,
            evidence_path=self.evidence_path,
        )
        mismatch_result = verify_uploaded_file_hash(
            "upload-verify-id",
            mismatch_hash,
            evidence_path=self.evidence_path,
        )

        self.assertTrue(match_result["hash_match"])
        self.assertFalse(mismatch_result["hash_match"])

    def test_public_report_schema(self):
        evidence = self._build_evidence(file_id="public-report-id")
        write_bundle_once(self.evidence_path, "public-report-id", evidence)

        loaded = load_evidence_bundle(self.evidence_path, "public-report-id")
        report = build_public_report(loaded)

        for field in PUBLIC_REPORT_FIELDS:
            self.assertIn(field, report)

        self.assertNotIn("engine_outputs", report)
        self.assertNotIn("metadata", report)
        self.assertNotIn("raw", json.dumps(report))
        self.assertEqual(report["report_version"], 1)
        self.assertTrue(report["evidence_bundle_hash"])
        self.assertEqual(report["constitution_version"], loaded["constitution_version"])

    def test_dataset_logger_writes_versioned_bundle(self):
        logger = DatasetLogger(
            log_path=self.log_path,
            evidence_path=self.evidence_path,
            training_path=self.training_path,
            disagreement_path=os.path.join(self.tmpdir.name, "data", "disagreements"),
        )

        report = _sample_report()
        engines = sanitize_external_engines(
            {
                "prooforigin": {"status": "complete", "score": 12, "label": "Likely Human-Made"},
            }
        )

        entry = logger.log_analysis(
            file_id="logger-bundle-id",
            report=report,
            external_engines=engines,
            file_hash="abc123original",
        )

        bundle_path = get_bundle_path(self.evidence_path, "logger-bundle-id")
        self.assertTrue(os.path.exists(bundle_path))
        self.assertEqual(entry["report_version"], 1)
        self.assertTrue(entry["published_at"])

        with self.assertRaises(ValueError):
            logger.log_analysis(
                file_id="logger-bundle-id",
                report=report,
                external_engines=engines,
                file_hash="abc123original",
            )

    def test_bundle_hash_stable_after_feedback(self):
        evidence = self._build_evidence(file_id="stable-hash-id")
        write_bundle_once(self.evidence_path, "stable-hash-id", evidence)

        before = verify_bundle_integrity(
            load_evidence_bundle(self.evidence_path, "stable-hash-id")
        )

        append_feedback_event(
            self.evidence_path,
            "stable-hash-id",
            {"file_id": "stable-hash-id", "user_label": "ai", "timestamp": "2026-01-02T00:00:00"},
        )

        after = verify_bundle_integrity(
            load_evidence_bundle(self.evidence_path, "stable-hash-id")
        )

        self.assertEqual(before["bundle_hash"], after["bundle_hash"])
        self.assertTrue(after["hash_match"])


if __name__ == "__main__":
    unittest.main()
