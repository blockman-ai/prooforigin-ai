import os
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".heic", ".heif"}

DATASET_REQUIRED_MESSAGE = (
    "Dataset required: add real images to ml/datasets/real and "
    "AI images to ml/datasets/ai"
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASETS_DIR = REPO_ROOT / "ml" / "datasets"
REAL_DIR = DATASETS_DIR / "real"
AI_DIR = DATASETS_DIR / "ai"
MODELS_DIR = REPO_ROOT / "ml" / "models"
MODEL_PATH = MODELS_DIR / "prooforigin_cv_classifier.pt"
METRICS_PATH = MODELS_DIR / "metrics.json"


def is_image_file(path):
    return Path(path).suffix.lower() in IMAGE_EXTENSIONS


def list_valid_images(directory):
    directory = Path(directory)
    if not directory.is_dir():
        return []

    valid = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        if not is_image_file(path):
            continue
        valid.append(path)
    return valid


def validate_readable_image(path):
    try:
        from PIL import Image

        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            image.convert("RGB")
        return True, None
    except Exception as exc:
        return False, str(exc)


def audit_dataset_counts():
    real_images = list_valid_images(REAL_DIR)
    ai_images = list_valid_images(AI_DIR)
    return {
        "real_dir": str(REAL_DIR),
        "ai_dir": str(AI_DIR),
        "real_count": len(real_images),
        "ai_count": len(ai_images),
        "real_images": real_images,
        "ai_images": ai_images,
    }


def ensure_dataset_ready(min_per_class=2):
    counts = audit_dataset_counts()
    if counts["real_count"] < min_per_class or counts["ai_count"] < min_per_class:
        raise SystemExit(DATASET_REQUIRED_MESSAGE)
    return counts
