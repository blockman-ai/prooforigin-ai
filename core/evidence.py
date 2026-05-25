class EvidenceWeightingSystem:

    def __init__(self):
        self.weights = {
            "metadata": 15,
            "exif": 15,
            "compression": 15,
            "visual_artifacts": 20,
            "lighting_geometry": 15,
            "ai_pattern": 20,
        }

    def score_signal(self, value):
        """
        Converts signal strength into weighted score.
        Expected values:
        - none
        - weak
        - moderate
        - strong
        """

        mapping = {
            "none": 0,
            "weak": 0.25,
            "moderate": 0.6,
            "strong": 1.0,
        }

        return mapping.get(value, 0)

    def calculate_ai_score(self, signals):
        """
        signals example:
        {
            "metadata": "weak",
            "exif": "moderate",
            "compression": "strong",
            "visual_artifacts": "moderate",
            "lighting_geometry": "weak",
            "ai_pattern": "strong"
        }
        """

        total_score = 0

        for signal_name, strength in signals.items():
            weight = self.weights.get(signal_name, 0)
            signal_score = self.score_signal(strength)
            total_score += weight * signal_score

        return round(total_score, 2)

    def explain_evidence(self, signals):
        explanations = []

        for signal_name, strength in signals.items():
            explanations.append({
                "signal": signal_name,
                "strength": strength,
                "meaning": self.describe_signal(signal_name, strength)
            })

        return explanations

    def describe_signal(self, signal_name, strength):

        descriptions = {
            "metadata": "Metadata consistency and origin clues.",
            "exif": "Camera/device information and capture details.",
            "compression": "Compression patterns that may reveal editing or generation.",
            "visual_artifacts": "Visible image flaws, unnatural textures, or synthetic details.",
            "lighting_geometry": "Light direction, shadows, reflections, and scene consistency.",
            "ai_pattern": "Known AI-generation indicators or synthetic fingerprints.",
        }

        return f"{descriptions.get(signal_name, 'Unknown signal')} Strength detected: {strength}."
