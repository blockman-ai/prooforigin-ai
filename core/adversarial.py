class AdversarialDetectionEngine:

    def analyze_adversarial_risk(self, input_data):

        findings = []

        risk_score = 0

        metadata = input_data.get("metadata", {})
        exif = input_data.get("exif", {})
        image_info = input_data.get("image_info", {})

        visual_findings = input_data.get("visual_findings", [])
        ai_findings = input_data.get("ai_findings", [])

        # Missing EXIF
        if not exif:
            findings.append("missing_exif_data")
            risk_score += 15

        # Screenshot indicators
        if image_info.get("has_screen_dimensions"):
            findings.append("possible_screenshot_recompression")
            risk_score += 20

        # Strong AI findings
        if len(ai_findings) >= 3:
            findings.append("stacked_ai_generation_indicators")
            risk_score += 30

        # Heavy visual inconsistencies
        if len(visual_findings) >= 3:
            findings.append("possible_artifact_obfuscation")
            risk_score += 20

        # AI software metadata
        software = str(metadata.get("software", "")).lower()

        suspicious_tools = [
            "stable diffusion",
            "midjourney",
            "comfyui",
            "dall-e",
            "firefly",
        ]

        for tool in suspicious_tools:
            if tool in software:
                findings.append(f"detected_ai_tool:{tool}")
                risk_score += 25

        return {
            "risk_score": min(risk_score, 100),
            "risk_level": self.classify_risk(risk_score),
            "findings": findings,
        }

    def classify_risk(self, score):

        if score >= 75:
            return "High"

        if score >= 45:
            return "Moderate"

        if score >= 20:
            return "Low"

        return "Minimal"
