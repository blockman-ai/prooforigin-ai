from PIL import Image
import numpy as np


class VisionForensicsEngine:

    def analyze_image(self, image_path):
        findings = {
            "visual_findings": [],
            "lighting_findings": [],
            "ai_findings": [],
        }

        try:
            image = Image.open(image_path).convert("RGB")

            img_array = np.array(image)

            findings["visual_findings"] += (
                self.detect_resolution_anomalies(img_array)
            )

            findings["ai_findings"] += (
                self.detect_synthetic_patterns(img_array)
            )

            findings["lighting_findings"] += (
                self.detect_lighting_consistency(img_array)
            )

        except Exception as e:
            findings["visual_findings"].append(
                f"Vision engine error: {str(e)}"
            )

        return findings

    def detect_resolution_anomalies(self, img_array):
        findings = []

        height, width, _ = img_array.shape

        if width < 512 or height < 512:
            findings.append("low_resolution_source")

        if width == height:
            findings.append("perfect_square_generation")

        return findings

    def detect_synthetic_patterns(self, img_array):
        findings = []

        variance = np.var(img_array)

        if variance < 800:
            findings.append("overly_smooth_pixel_distribution")

        if variance > 12000:
            findings.append("abnormal_noise_distribution")

        return findings

    def detect_lighting_consistency(self, img_array):
        findings = []

        brightness = np.mean(img_array)

        if brightness > 220:
            findings.append("extreme_brightness_uniformity")

        if brightness < 25:
            findings.append("extreme_darkness_uniformity")

        return findings
