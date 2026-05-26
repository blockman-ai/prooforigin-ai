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

        # -----------------------------------
        # Software metadata analysis
        # -----------------------------------

        software = str(metadata.get("software", "")).lower()

        if "photoshop" in software:
            trace["editing_lineage"].append(
                "Adobe Photoshop detected"
            )

        if "lightroom" in software:
            trace["editing_lineage"].append(
                "Adobe Lightroom detected"
            )

        if "stable diffusion" in software:
            trace["editing_lineage"].append(
                "Stable Diffusion metadata detected"
            )

        if "midjourney" in software:
            trace["editing_lineage"].append(
                "Midjourney metadata detected"
            )

        if "dall" in software or "openai" in software:
            trace["editing_lineage"].append(
                "OpenAI image generation metadata detected"
            )

        if "canva" in software:
            trace["editing_lineage"].append(
                "Canva editing metadata detected"
            )

        # -----------------------------------
        # Compression analysis
        # -----------------------------------

        compression = image_info.get("compression_quality")

        if compression is not None and compression < 85:
            trace["recompression_detected"] = True
            trace["editing_lineage"].append(
                "Image appears recompressed"
            )

        # -----------------------------------
        # Screenshot detection
        # -----------------------------------

        if image_info.get("has_screen_dimensions"):
            trace["screenshot_generation"] = "Likely Screenshot"

        # -----------------------------------
        # Platform fingerprint estimation
        # -----------------------------------

        width = image_info.get("width")
        height = image_info.get("height")

        if width and height:

            if width == 1080 and height == 1920:
                trace["likely_platform"] = "TikTok / Instagram Story"

            elif width == 1170 and height == 2532:
                trace["likely_platform"] = "iPhone Screenshot"

            elif width == 1284 and height == 2778:
                trace["likely_platform"] = "iPhone Pro Max Screenshot"

            elif width == 1440 and height == 3040:
                trace["likely_platform"] = "Android Screenshot"

            elif width == 1920 and height == 1080:
                trace["likely_platform"] = "Desktop / YouTube"

        # -----------------------------------
        # Final fallback logic
        # -----------------------------------

        if not trace["editing_lineage"]:
            trace["editing_lineage"].append(
                "No major editing lineage detected"
            )

        return trace
