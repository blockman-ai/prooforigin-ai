"""ProofOrigin CV v0.2 correction dataset buckets and targets."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CORRECTION_ROOT = REPO_ROOT / "ml" / "correction_sets" / "v0_2"
CORRECTION_MANIFEST = CORRECTION_ROOT / "manifest.jsonl"

CORRECTION_BUCKETS = (
    "real_pet_photos",
    "phone_screen_photos",
    "indoor_soft_light",
    "screenshots",
    "ai_controls",
)

CORRECTION_TARGETS = {
    "real_pet_photos": 50,
    "phone_screen_photos": 25,
    "indoor_soft_light": 25,
    "screenshots": 25,
    "ai_controls": 25,
}

# Minimum recommended before retraining (same as targets for v0.2).
CORRECTION_MINIMUMS = dict(CORRECTION_TARGETS)

BUCKET_LABELS = {
    "real_pet_photos": "real_camera",
    "phone_screen_photos": "real_camera",
    "indoor_soft_light": "real_camera",
    "screenshots": "real_camera",
    "ai_controls": "ai_generated",
}


def bucket_dir(bucket):
    if bucket not in CORRECTION_BUCKETS:
        raise ValueError(f"Unknown correction bucket: {bucket}")
    return CORRECTION_ROOT / bucket


def total_target():
    return sum(CORRECTION_TARGETS.values())
