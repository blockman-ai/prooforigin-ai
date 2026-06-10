import unittest

from core.consensus_engine import calculate_weighted_consensus, MAX_EXTERNAL_VENDOR_WEIGHT
from core.evidence_schema import build_evidence_record
from core.policy_engine import (
    apply_constitution_policy,
    build_evidence_bundle_hash,
    POLICY_VERSION,
)
from core.engine_sanitize import sanitize_external_engines


class PolicyHardeningTests(unittest.TestCase):
    def test_external_vendor_weight_cap(self):
        engines = {
            "prooforigin": {"status": "complete", "score": 10},
            "sightengine": {"status": "complete", "score": 20},
            "openai_vision": {"status": "complete", "score": 90},
        }

        consensus = calculate_weighted_consensus(engines)
        effective_weights = consensus["effective_weights"]

        self.assertLessEqual(
            effective_weights.get("openai_vision", 0),
            MAX_EXTERNAL_VENDOR_WEIGHT,
        )
        self.assertLessEqual(
            effective_weights.get("sightengine", 0),
            MAX_EXTERNAL_VENDOR_WEIGHT,
        )

    def test_single_engine_forces_investigate_tier(self):
        engines = {
            "prooforigin": {"status": "complete", "score": 85, "label": "Likely AI Generated"},
            "sightengine": {"status": "unconfigured", "score": None},
            "openai_vision": {"status": "unconfigured", "score": None},
        }

        consensus = calculate_weighted_consensus(engines)
        policy = apply_constitution_policy(
            final_consensus=consensus,
            original_consensus=consensus,
            engine_arbitration={
                "disagreement_detected": False,
                "score_spread": 0,
            },
            external_engines=engines,
        )

        self.assertTrue(consensus["single_engine_only"])
        self.assertEqual(policy["decision_tier"], "investigate")

    def test_high_disagreement_triggers_investigate_or_caution(self):
        engines = {
            "prooforigin": {"status": "complete", "score": 15},
            "sightengine": {"status": "complete", "score": 20},
            "openai_vision": {"status": "complete", "score": 80},
        }

        consensus = calculate_weighted_consensus(engines)
        arbitration = {
            "disagreement_detected": True,
            "score_spread": 65,
        }

        policy = apply_constitution_policy(
            final_consensus=consensus,
            original_consensus=consensus,
            engine_arbitration=arbitration,
            external_engines=engines,
        )

        self.assertIn(policy["decision_tier"], {"investigate", "caution"})
        self.assertTrue(policy["suppression_required"])

    def test_evidence_bundle_hash_is_stable(self):
        payload = {
            "report_id": "abc",
            "summary": {"ai_score": 12, "label": "Likely Human-Made"},
            "policy_hash": "policy123",
        }

        first_hash = build_evidence_bundle_hash(payload)
        second_hash = build_evidence_bundle_hash(payload)

        self.assertEqual(first_hash, second_hash)
        self.assertEqual(len(first_hash), 64)

    def test_policy_fields_in_evidence_record(self):
        report = {
            "summary": {"label": "Likely Human-Made", "ai_score": 12},
            "integrity": {
                "original_sha256": "abc123",
                "analysis_sha256": "def456",
            },
            "weighted_consensus": {"score": 12, "label": "Likely Human-Made"},
            "decision_tier": "caution",
            "confidence_in_estimate": "moderate",
            "uncertainty_notes": ["Scores are forensic estimates, not legal or moral proof."],
            "policy": {
                "decision_tier": "caution",
                "public_label": "Mixed / Uncertain Signals",
                "policy_version": POLICY_VERSION,
                "constitution_version": "1.0.0",
                "policy_hash": "placeholder",
            },
        }

        engines = sanitize_external_engines(
            {
                "prooforigin": {"status": "complete", "score": 12, "label": "Likely Human-Made"},
            }
        )

        evidence = build_evidence_record(
            file_id="policy-test-id",
            timestamp="2026-01-01T00:00:00",
            report=report,
            external_engines=engines,
            policy=report["policy"],
        )

        self.assertTrue(evidence["evidence_bundle_hash"])
        self.assertTrue(evidence["policy_hash"])
        self.assertTrue(evidence["engine_snapshot_hash"])
        self.assertEqual(evidence["decision_tier"], "caution")
        self.assertEqual(evidence["constitution_version"], "1.0.0")
        self.assertEqual(evidence["policy_version"], POLICY_VERSION)
        self.assertIn("policy", evidence)


if __name__ == "__main__":
    unittest.main()
