from core.constitution import PROOFORIGIN_CONSTITUTION


class ProofOriginReasoner:

    def __init__(self):
        self.constitution = PROOFORIGIN_CONSTITUTION

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
