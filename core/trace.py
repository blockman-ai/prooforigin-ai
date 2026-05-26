class TraceIntelligenceEngine:

    def analyze_trace(self, input_data):

        metadata = input_data.get("metadata", {})
        image_info = input_data.get("image_info", {})

        trace = {
            "likely_platform": "Unknown",
            "recompression_detected": False,
            "screenshot_generation": "Unknown",
            "editing_lineage": [],
        }

        software = str(metadata.get("software", "")).lower()

        if "photoshop" in software:
            trace["editing_lineage"].append(
                "Adobe Photoshop detected"
            )

        if "stable diffusion" in software:
            trace["editing_lineage"].append(
                "Stable Diffusion metadata detected"
            )

        compression = image_info.get("compression_quality", 100)

        if compression < 85:
            trace["recompression_detected"] = True

        if image_info.get("has_screen_dimensions"):
            trace["screenshot_generation"] = "Likely Screenshot"

        return trace
