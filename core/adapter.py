class ExtractorAdapter:

    def build_input_data(self, metadata, extracted_signals):
        exif = metadata.get("exif", {})

        image_info = {
            "filename": metadata.get("filename", ""),
            "compression_quality": metadata.get("compression_quality"),
            "has_screen_dimensions": self.has_screen_dimensions(metadata),
        }

        ai_findings = []
        visual_findings = []
        lighting_findings = []

        for signal in extracted_signals:
            signal_type = signal.get("type", "")

            if signal_type in ["ai_generation_software"]:
                ai_findings.append(signal.get("details", signal_type))

            if signal_type in ["missing_exif"]:
                visual_findings.append(signal.get("details", signal_type))

        return {
            "metadata": metadata,
            "exif": exif,
            "image_info": image_info,
            "visual_findings": visual_findings,
            "lighting_findings": lighting_findings,
            "ai_findings": ai_findings,
        }

    def has_screen_dimensions(self, metadata):
        width = metadata.get("width")
        height = metadata.get("height")

        common_screen_ratios = [
            (1920, 1080),
            (1080, 1920),
            (1170, 2532),
            (1284, 2778),
            (1440, 2960),
            (1080, 2400),
        ]

        return (width, height) in common_screen_ratios
