from PIL import Image
import numpy as np


def extract_ml_features(image_path, metadata=None):
    metadata = metadata or {}
    features = {
        "width": metadata.get("width"),
        "height": metadata.get("height"),
        "aspect_ratio": None,
        "megapixels": None,
        "exif_field_count": len((metadata.get("exif") or {})),
        "has_exif": bool(metadata.get("exif")),
        "format": metadata.get("format"),
        "pixel_variance": None,
        "edge_density": None,
        "color_channel_balance": None,
        "low_resolution": False,
        "square_aspect": False,
    }

    try:
        width = int(metadata.get("width") or 0)
        height = int(metadata.get("height") or 0)

        if width > 0 and height > 0:
            features["aspect_ratio"] = round(width / height, 4)
            features["megapixels"] = round((width * height) / 1_000_000, 3)
            features["low_resolution"] = width < 512 or height < 512
            features["square_aspect"] = width == height

        image = Image.open(image_path).convert("RGB")
        arr = np.array(image, dtype=np.float32)

        features["pixel_variance"] = round(float(np.var(arr)), 2)

        gray = np.mean(arr, axis=2)
        gx = np.abs(np.diff(gray, axis=1)).mean()
        gy = np.abs(np.diff(gray, axis=0)).mean()
        features["edge_density"] = round(float((gx + gy) / 2.0), 4)

        channel_means = arr.reshape(-1, 3).mean(axis=0)
        spread = float(channel_means.max() - channel_means.min())
        features["color_channel_balance"] = round(spread, 4)
    except Exception as exc:
        features["extraction_error"] = str(exc)

    return features
