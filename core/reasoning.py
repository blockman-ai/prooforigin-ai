from core.constitution import PROOFORIGIN_CONSTITUTION
from core.evidence import EvidenceWeightingSystem
from core.signals import ForensicSignalAnalyzer
from core.origin import OriginIntelligence
class ProofOriginReasoner:

    def __init__(self):
    self.constitution = PROOFORIGIN_CONSTITUTION
    self.evidence_system = EvidenceWeightingSystem()
    self.signal_analyzer = ForensicSignalAnalyzer()
    
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
            warnings.append(
                "Low confidence result. Avoid making public accusations."
            )

        if analysis["label"] == "Inconclusive":
            warnings.append(
                "Evidence is mixed and requires additional verification."
            )

        if analysis["ai_score"] >= 65:
            warnings.append(
                "AI indicators detected, but this is not definitive proof."
            )

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

        result = {
            "analysis": analysis,
            "warnings": warnings,
            "constitution_law":
                self.constitution["foundational_law"],
            "highest_duty":
                self.constitution["highest_duty"],
        }

        return result

def analyze_signals(self, signals):

    ai_score = self.evidence_system.calculate_ai_score(signals)

    evidence = self.evidence_system.explain_evidence(signals)

    return self.generate_reasoning(ai_score, evidence)
    
def analyze_input_data(self, input_data):

    signals = self.signal_analyzer.build_signals(input_data)

    return self.analyze_signals(signals)
