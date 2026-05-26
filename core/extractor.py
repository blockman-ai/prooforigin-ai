from PIL import Image
from PIL.ExifTags import TAGS


class ImageSignalExtractor:

    def extract_metadata(self, image_path):
        metadata = {}

        try:
            image = Image.open(image_path)

            metadata["format"] = image.format
            metadata["mode"] = image.mode
            metadata["width"] = image.width
            metadata["height"] = image.height

            exif_data = image.getexif()

            exif = {}

            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                exif[tag] = str(value)

            metadata["exif"] = exif

        except Exception as e:
            metadata["error"] = str(e)

        return metadata

    def detect_basic_signals(self, metadata):
        signals = []

        exif = metadata.get("exif", {})

        software = str(exif.get("Software", "")).lower()

        suspicious_software = [
            "midjourney",
            "stable diffusion",
            "dall-e",
            "photoshop ai",
            "firefly",
            "comfyui",
        ]

        for tool in suspicious_software:
            if tool in software:
                signals.append({
                    "type": "ai_generation_software",
                    "strength": 90,
                    "details": tool,
                })

        if len(exif) == 0:
            signals.append({
                "type": "missing_exif",
                "strength": 40,
                "details": "No EXIF metadata present",
            })

        return signals
