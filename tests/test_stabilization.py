import json
import os
import tempfile
import unittest

from core.evidence_schema import build_evidence_record
from core.engine_sanitize import sanitize_external_engines
from core.proof_verifier import verify_proof_record


class StabilizationTests(unittest.TestCase):
    def test_sanitize_external_engines_removes_raw(self):
        engines = {
            "sightengine": {
                "status": "complete",
                "score": 42,
                "label": "Test",
                "raw": {"secret": "vendor_payload"},
            },
            "openai_vision": {
                "status": "complete",
                "score": 55,
                "label": "Test",
                "raw": {"ai_score": 55},
                "findings": ["test"],
            },
        }

        sanitized = sanitize_external_engines(engines)

        self.assertNotIn("raw", sanitized["sightengine"])
        self.assertNotIn("raw", sanitized["openai_vision"])
        self.assertEqual(sanitized["sightengine"]["score"], 42)
        self.assertEqual(sanitized["openai_vision"]["findings"], ["test"])

    def test_evidence_record_matches_verifier_schema(self):
        report = {
            "summary": {"label": "Likely Human-Made", "ai_score": 12},
            "integrity": {
                "original_sha256": "abc123",
                "analysis_sha256": "def456",
                "file_name": "sample.jpg",
                "original_file_type": "image/jpeg",
                "verification_status": "hash_recorded",
                "tamper_evidence": "available",
            },
            "bitcoin_lite_anchor": {
                "status": "pending_batch",
                "merkle_root": None,
            },
            "weighted_consensus": {"score": 12, "label": "Likely Human-Made"},
        }

        engines = sanitize_external_engines(
            {
                "sightengine": {
                    "status": "unconfigured",
                    "score": None,
                    "label": "Sightengine API not configured",
                    "raw": {"hidden": True},
                }
            }
        )

        evidence = build_evidence_record(
            file_id="test-file-id",
            timestamp="2026-01-01T00:00:00",
            report=report,
            external_engines=engines,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            evidence_dir = os.path.join(tmpdir, "data", "evidence")
            os.makedirs(evidence_dir)
            file_id = "test-file-id"

            from core.bundle_store import write_bundle_once

            write_bundle_once(evidence_dir, file_id, evidence)

            original_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                result = verify_proof_record("test-file-id")
            finally:
                os.chdir(original_cwd)

        self.assertTrue(result["hash_match"])
        self.assertTrue(result["verified"])
        self.assertEqual(result["original_sha256"], "abc123")
        self.assertEqual(result["analysis_sha256"], "def456")
        self.assertNotIn("raw", evidence["engine_outputs"]["sightengine"])


if __name__ == "__main__":
    unittest.main()
