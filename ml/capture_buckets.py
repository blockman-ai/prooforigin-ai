"""Dataset capture bucket registry: CV v0.2 correction gate + general expansion."""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# CV v0.2 retraining gate — unchanged; only these five buckets gate safe auto-train.
V02_CORRECTION_BUCKETS = (
    "real_pet_photos",
    "phone_screen_photos",
    "indoor_soft_light",
    "screenshots",
    "ai_controls",
)

# General expansion capture buckets — stored locally, excluded from v0.2 retraining until mapped.
GENERAL_EXPANSION_BUCKETS = (
    "real_people_photos",
    "real_document_photos",
    "real_food_photos",
    "real_vehicle_photos",
    "real_nature_sky",
    "real_low_light",
    "real_reflections_glass",
    "photo_of_photo",
    "social_media_screenshots",
    "edited_real",
    "ai_generated_people",
    "ai_generated_objects",
    "ai_generated_art",
    "ai_generated_screenshot_like",
    "uncertain_mixed",
)

CAPTURE_BUCKETS = V02_CORRECTION_BUCKETS + GENERAL_EXPANSION_BUCKETS

V02_CORRECTION_ROOT = REPO_ROOT / "ml" / "correction_sets" / "v0_2"
V02_CORRECTION_MANIFEST = V02_CORRECTION_ROOT / "manifest.jsonl"

GENERAL_EXPANSION_ROOT = REPO_ROOT / "ml" / "correction_sets" / "general_expansion"
GENERAL_EXPANSION_MANIFEST = GENERAL_EXPANSION_ROOT / "manifest.jsonl"

# Alternate layout (documented; not used by default import routing).
PRIVATE_EXPANSION_ROOT = REPO_ROOT / "ml" / "datasets" / "private_expansion"

CAPTURE_BUCKET_LABELS = {
    "real_pet_photos": "real_camera",
    "phone_screen_photos": "real_camera",
    "indoor_soft_light": "real_camera",
    "screenshots": "real_camera",
    "ai_controls": "ai_generated",
    "real_people_photos": "real_camera",
    "real_document_photos": "real_camera",
    "real_food_photos": "real_camera",
    "real_vehicle_photos": "real_camera",
    "real_nature_sky": "real_camera",
    "real_low_light": "real_camera",
    "real_reflections_glass": "real_camera",
    "photo_of_photo": "real_camera",
    "social_media_screenshots": "real_camera",
    "edited_real": "edited_real",
    "ai_generated_people": "ai_generated",
    "ai_generated_objects": "ai_generated",
    "ai_generated_art": "ai_generated",
    "ai_generated_screenshot_like": "ai_generated",
    "uncertain_mixed": "uncertain",
}


def is_valid_capture_bucket(value):
    return str(value or "").strip() in CAPTURE_BUCKETS


def is_v02_correction_bucket(value):
    return str(value or "").strip() in V02_CORRECTION_BUCKETS


def is_general_expansion_bucket(value):
    return str(value or "").strip() in GENERAL_EXPANSION_BUCKETS


def is_retraining_bucket(value):
    """Buckets that count toward the CV v0.2 safe auto-train gate."""
    return is_v02_correction_bucket(value)


def normalize_capture_bucket(value):
    bucket = str(value or "").strip()
    if not is_valid_capture_bucket(bucket):
        raise ValueError(
            f"Invalid capture bucket '{bucket}'. "
            f"Expected one of: {', '.join(CAPTURE_BUCKETS)}"
        )
    return bucket


def capture_bucket_label(bucket):
    bucket = normalize_capture_bucket(bucket)
    return CAPTURE_BUCKET_LABELS[bucket]


def capture_bucket_root(bucket):
    bucket = normalize_capture_bucket(bucket)
    if is_v02_correction_bucket(bucket):
        return V02_CORRECTION_ROOT
    return GENERAL_EXPANSION_ROOT


def capture_bucket_dir(bucket):
    bucket = normalize_capture_bucket(bucket)
    return capture_bucket_root(bucket) / bucket


def capture_bucket_manifest(bucket):
    bucket = normalize_capture_bucket(bucket)
    if is_v02_correction_bucket(bucket):
        return V02_CORRECTION_MANIFEST
    return GENERAL_EXPANSION_MANIFEST


def _load_manifest_file(path):
    index = {}
    if not path.exists():
        return index
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            index[row["sha256"]] = row
    return index


def load_combined_capture_manifest_index():
    """SHA index across v0.2 and general expansion manifests (import dedup)."""
    combined = _load_manifest_file(V02_CORRECTION_MANIFEST)
    combined.update(_load_manifest_file(GENERAL_EXPANSION_MANIFEST))
    return combined


def append_capture_manifest_entry(entry, bucket):
    manifest = capture_bucket_manifest(bucket)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=True) + "\n")


def unique_capture_destination(bucket, filename):
    directory = capture_bucket_dir(bucket)
    directory.mkdir(parents=True, exist_ok=True)
    candidate = directory / filename
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    index = 1
    while True:
        alt = directory / f"{stem}_{index}{suffix}"
        if not alt.exists():
            return alt
        index += 1
