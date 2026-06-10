import os
import tempfile
import unittest

from api.response_utils import RESPONSE_SCHEMA_VERSION, build_analyze_response
from core.bundle_store import write_bundle_once
from core.engine_sanitize import sanitize_external_engines
from core.evidence_schema import build_evidence_record
from core.policy_engine import apply_constitution_policy
from core.proof_verifier import verify_proof_record, verify_uploaded_file_hash
from core.public_report import PUBLIC_REPORT_FIELDS, build_public_report
from core.website_contract import REQUIRED_WEBSITE_FIELDS, build_website_contract_from_analyze
from core.protocol import (
    PROTOCOL_NAME,
    PROTOCOL_VERSION,
    VERIFICATION_NOTICE,
    VERIFIED_SCOPE_BUNDLE_AND_FILE_HASH,
    VERIFIED_SCOPE_UPLOAD_FILE_HASH,
)
from core.consensus_engine import calculate_weighted_consensus


def _sample_analyze_result():
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
    integrity = {
        "original_sha256": "abc123",
        "analysis_sha256": "def456",
    }
    result = {
        "summary": {"label": "Likely Human-Made", "ai_score": 12},
        "integrity": integrity,
        "weighted_consensus": consensus,
        "decision_tier": policy["decision_tier"],
        "policy": policy,
        "constitution_version": policy["constitution_version"],
        "confidence_in_estimate": policy["confidence_in_estimate"],
        "uncertainty_notes": policy["uncertainty_notes"],
        "warnings": policy["warnings"],
        "evidence_bundle_hash": "a" * 64,
        "policy_hash": "b" * 64,
        "engine_snapshot_hash": "c" * 64,
    }
    return result, integrity, consensus, engines


class WebsiteContractTests(unittest.TestCase):
    def test_analyze_response_includes_website_fields(self):
        result, integrity, consensus, engines = _sample_analyze_result()

        response = build_analyze_response(
            result=result,
            file_id="website-test-id",
            metadata={},
            original_metadata={},
            converted_metadata={},
            integrity=integrity,
            final_consensus=consensus,
            original_consensus=consensus,
            forensic_context={},
            engine_arbitration={},
            human_summary={},
            contradiction_resolution={},
            camera_authenticity={},
            camera_provenance={},
            bitcoin_lite_anchor={},
            external_engines=engines,
        )

        for field in REQUIRED_WEBSITE_FIELDS:
            self.assertIn(field, response)

        self.assertFalse(response["truth_verified"])
        self.assertEqual(response["verified_scope"], VERIFIED_SCOPE_BUNDLE_AND_FILE_HASH)
        self.assertEqual(response["protocol_name"], PROTOCOL_NAME)
        self.assertEqual(response["protocol_version"], PROTOCOL_VERSION)
        self.assertEqual(response["verification_notice"], VERIFICATION_NOTICE)
        self.assertIn("contract", response)
        self.assertEqual(response["response_meta"]["schema_version"], RESPONSE_SCHEMA_VERSION)
        self.assertNotIn("raw", str(response["engine_outputs"]))

    def test_website_contract_from_analyze(self):
        result, integrity, _, _ = _sample_analyze_result()
        contract = build_website_contract_from_analyze(result, integrity=integrity)

        self.assertFalse(contract["truth_verified"])
        self.assertEqual(contract["verified_scope"], VERIFIED_SCOPE_BUNDLE_AND_FILE_HASH)

    def test_public_report_remains_slim(self):
        report, integrity, _, engines = _sample_analyze_result()
        evidence = build_evidence_record(
            file_id="public-slim-id",
            timestamp="2026-01-01T00:00:00",
            report=report,
            external_engines=sanitize_external_engines(engines),
            policy=report["policy"],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            evidence_path = os.path.join(tmpdir, "data", "evidence")
            os.makedirs(evidence_path)
            write_bundle_once(evidence_path, "public-slim-id", evidence)
            public = build_public_report(evidence)

        for field in PUBLIC_REPORT_FIELDS:
            self.assertIn(field, public)

        self.assertNotIn("engine_outputs", public)
        self.assertNotIn("raw", str(public))

    def test_verify_proof_scope_safe_language(self):
        report, integrity, _, engines = _sample_analyze_result()
        evidence = build_evidence_record(
            file_id="verify-safe-id",
            timestamp="2026-01-01T00:00:00",
            report=report,
            external_engines=sanitize_external_engines(engines),
            policy=report["policy"],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            evidence_path = os.path.join(tmpdir, "data", "evidence")
            os.makedirs(evidence_path)
            write_bundle_once(evidence_path, "verify-safe-id", evidence)

            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                result = verify_proof_record("verify-safe-id", evidence_path="data/evidence")
            finally:
                os.chdir(original_cwd)

        self.assertFalse(result["truth_verified"])
        self.assertIn("verified_scope", result)
        self.assertIn("protocol_version", result)
        self.assertIn("claim_boundary", result)
        self.assertNotIn("truth verified", result["message"].lower())

    def test_verify_upload_includes_verified_scope(self):
        report, _, _, engines = _sample_analyze_result()
        evidence = build_evidence_record(
            file_id="upload-scope-id",
            timestamp="2026-01-01T00:00:00",
            report=report,
            external_engines=sanitize_external_engines(engines),
            policy=report["policy"],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            evidence_path = os.path.join(tmpdir, "data", "evidence")
            os.makedirs(evidence_path)
            write_bundle_once(evidence_path, "upload-scope-id", evidence)

            result = verify_uploaded_file_hash(
                "upload-scope-id",
                report["integrity"]["original_sha256"],
                evidence_path=evidence_path,
            )

        self.assertFalse(result["truth_verified"])
        self.assertEqual(result["verified_scope"], VERIFIED_SCOPE_UPLOAD_FILE_HASH)
        self.assertNotIn("truth verified", result["message"].lower())


if __name__ == "__main__":
    unittest.main()
