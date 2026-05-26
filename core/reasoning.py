from core.constitution import PROOFORIGIN_CONSTITUTION
from core.evidence import EvidenceWeightingSystem
from core.signals import ForensicSignalAnalyzer
from core.origin import OriginIntelligence
from core.consensus import ConsensusIntelligenceEngine


class ProofOriginReasoner:

    def __init__(self):
        self.constitution = PROOFORIGIN_CONSTITUTION
        self.evidence_system = EvidenceWeightingSystem()
        self.signal_analyzer = ForensicSignalAnalyzer()
        self.origin_intelligence = OriginIntelligence()
        self.consensus_engine = ConsensusIntelligenceEngine()

    def classify_confidence(self, score):
        if score >= 90:
            return "Very High"
        elif score >= 75:
            return "High"
        elif score >= 55:
            return "Moderate"
        elif score >= 35:
            return "Low"
        return "Very Low"

    def determine_label(self, ai_score):
        if ai_score >= 85:
            return "Likely AI Generated"
        elif ai_score >= 65:
            return "Possibly AI Generated"
        elif ai_score >= 45:
            return "Inconclusive"
        elif ai_score >= 20:
            return "Likely Human-Made"
        return "Human-Made"

    def moral_safety_check(self, analysis):
        warnings = []

        if analysis["confidence"] == "Low":
            warnings.append("Low confidence result. Avoid making public accusations.")

        if analysis["label"] == "Inconclusive":
            warnings.append("Evidence is mixed and requires additional verification.")

        if analysis["ai_score"] >= 65:
            warnings.append("AI indicators detected, but this is not definitive proof.")

        return warnings

    def generate_reasoning(self, ai_score, evidence):
        confidence = self.classify_confidence(ai_score)
        label = self.determine_label(ai_score)

        analysis = {
            "label": label,
            "ai_score": ai_score,
            "confidence": confidence,
            "evidence": evidence,
        }

        warnings = self.moral_safety_check(analysis)

        return {
            "analysis": analysis,
            "warnings": warnings,
            "constitution_law": self.constitution["foundational_law"],
            "highest_duty": self.constitution["highest_duty"],
        }

    def analyze_signals(self, signals):
        ai_score = self.evidence_system.calculate_ai_score(signals)
        evidence = self.evidence_system.explain_evidence(signals)

        return self.generate_reasoning(ai_score, evidence)

    def build_consensus(self, reasoning_result):
        ai_score = reasoning_result["analysis"]["ai_score"]
        origin_label = reasoning_result.get("origin", {}).get("label", "")

        origin_score = 50

        if origin_label == "Synthetic / AI-Generated":
            origin_score = 90
        elif origin_label == "Edited or Manipulated":
            origin_score = 70
        elif origin_label == "Screenshot":
            origin_score = 55
        elif origin_label == "Camera Capture":
            origin_score = 15

        engine_scores = {
            "forensic_score": ai_score,
            "origin_score": origin_score,
            "metadata_score": ai_score * 0.6,
            "manipulation_score": ai_score * 0.5,
            "human_authenticity_score": 100 - ai_score,
        }

        return self.consensus_engine.build_consensus_result(engine_scores)

    def analyze_input_data(self, input_data):
        signals = self.signal_analyzer.build_signals(input_data)
        reasoning_result = self.analyze_signals(signals)

        origin_label = self.origin_intelligence.classify_origin(input_data, signals)

        origin_confidence = self.origin_intelligence.estimate_origin_confidence(
            origin_label,
            signals
        )

        origin_explanation = self.origin_intelligence.explain_origin(origin_label)

        reasoning_result["origin"] = {
            "label": origin_label,
            "confidence": origin_confidence,
            "explanation": origin_explanation,
        }

        reasoning_result["consensus"] = self.build_consensus(reasoning_result)

        return reasoning_result
