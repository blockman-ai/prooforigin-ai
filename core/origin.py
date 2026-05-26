class OriginIntelligence:

    def classify_origin(self, input_data, signals):

        metadata = input_data.get("metadata") or {}
        exif = input_data.get("exif") or {}
        image_info = input_data.get("image_info") or {}

        if self.is_screenshot(metadata, image_info):
            return "Screenshot"

        if self.is_camera_capture(exif):
            return "Camera Capture"

        if signals.get("ai_pattern") in ["strong", "moderate"]:
            return "Synthetic / AI-Generated"

        if signals.get("visual_artifacts") in ["strong", "moderate"]:
            return "Edited or Manipulated"

        return "Unknown / Requires Review"

    def is_screenshot(self, metadata, image_info):
        software = str(metadata.get("software", "")).lower()
        filename = str(image_info.get("filename", "")).lower()

        screenshot_terms = [
            "screenshot",
            "screen shot",
            "screen_capture",
            "screen capture",
        ]

        if any(term in filename for term in screenshot_terms):
            return True

        if "screenshot" in software:
            return True

        if image_info.get("has_screen_dimensions"):
            return True

        return False

    def is_camera_capture(self, exif):
        if not exif:
            return False

        has_camera = exif.get("camera_make") or exif.get("camera_model")
        has_capture_date = exif.get("date_original")

        if has_camera and has_capture_date:
            return True

        return False

    def estimate_origin_confidence(self, origin_label, signals):

        if origin_label == "Camera Capture":
            if signals.get("exif") == "weak" and signals.get("ai_pattern") == "none":
                return "High"
            return "Moderate"

        if origin_label == "Synthetic / AI-Generated":
            if signals.get("ai_pattern") == "strong":
                return "High"
            return "Moderate"

        if origin_label == "Screenshot":
            return "Moderate"

        if origin_label == "Edited or Manipulated":
            return "Moderate"

        return "Low"

    def explain_origin(self, origin_label):

        explanations = {
            "Camera Capture":
                "The file contains indicators consistent with a real camera capture.",
            "Screenshot":
                "The file contains indicators consistent with a screen capture or reposted digital image.",
            "Synthetic / AI-Generated":
                "The file contains indicators consistent with synthetic or AI-generated media.",
            "Edited or Manipulated":
                "The file contains indicators suggesting editing, alteration, or manipulation.",
            "Unknown / Requires Review":
                "The available evidence is not strong enough to determine origin.",
        }

        return explanations.get(origin_label, "Origin could not be determined.")
