class ForensicSignalAnalyzer:

    def analyze_metadata(self, metadata):
        if not metadata:
            return "moderate"

        if metadata.get("software"):
            software = str(metadata.get("software")).lower()

            ai_tools = [
                "midjourney",
                "stable diffusion",
                "dall-e",
                "firefly",
                "leonardo",
                "comfyui",
            ]

            if any(tool in software for tool in ai_tools):
                return "strong"

        if metadata.get("camera_make") or metadata.get("camera_model"):
            return "weak"

        return "moderate"

    def analyze_exif(self, exif):
        if not exif:
            return "moderate"

        if exif.get("date_original") and (
            exif.get("camera_make") or exif.get("camera_model")
        ):
            return "weak"

        return "moderate"

    def analyze_compression(self, image_info):
        if not image_info:
            return "none"

        quality = image_info.get("compression_quality")

        if quality is None:
            return "weak"

        if quality < 55:
            return "strong"

        if quality < 75:
            return "moderate"

        return "weak"

    def analyze_visual_artifacts(self, visual_findings):
        if not visual_findings:
            return "none"

        artifact_count = len(visual_findings)

        if artifact_count >= 5:
            return "strong"

        if artifact_count >= 3:
            return "moderate"

        if artifact_count >= 1:
            return "weak"

        return "none"

    def analyze_lighting_geometry(self, lighting_findings):
        if not lighting_findings:
            return "none"

        inconsistency_count = len(lighting_findings)

        if inconsistency_count >= 4:
            return "strong"

        if inconsistency_count >= 2:
            return "moderate"

        if inconsistency_count == 1:
            return "weak"

        return "none"

    def analyze_ai_pattern(self, ai_findings):
        if not ai_findings:
            return "none"

        pattern_count = len(ai_findings)

        if pattern_count >= 5:
            return "strong"

        if pattern_count >= 3:
            return "moderate"

        if pattern_count >= 1:
            return "weak"

        return "none"

    def build_signals(self, input_data):
        return {
            "metadata": self.analyze_metadata(input_data.get("metadata")),
            "exif": self.analyze_exif(input_data.get("exif")),
            "compression": self.analyze_compression(input_data.get("image_info")),
            "visual_artifacts": self.analyze_visual_artifacts(
                input_data.get("visual_findings")
            ),
            "lighting_geometry": self.analyze_lighting_geometry(
                input_data.get("lighting_findings")
            ),
            "ai_pattern": self.analyze_ai_pattern(input_data.get("ai_findings")),
        }
