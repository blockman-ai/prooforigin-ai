"""ProofOrigin CV v0.2 correction dataset buckets and targets."""

import json
from pathlib import Path

from ml.capture_buckets import (
    CAPTURE_BUCKET_LABELS,
    V02_CORRECTION_BUCKETS,
    V02_CORRECTION_MANIFEST,
    V02_CORRECTION_ROOT,
    capture_bucket_dir as _capture_bucket_dir,
    is_v02_correction_bucket,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CORRECTION_ROOT = V02_CORRECTION_ROOT
CORRECTION_MANIFEST = V02_CORRECTION_MANIFEST

CORRECTION_BUCKETS = V02_CORRECTION_BUCKETS

CORRECTION_TARGETS = {
    "real_pet_photos": 50,
    "phone_screen_photos": 25,
    "indoor_soft_light": 25,
    "screenshots": 25,
    "ai_controls": 25,
}

# Minimum recommended before retraining (same as targets for v0.2).
CORRECTION_MINIMUMS = dict(CORRECTION_TARGETS)

BUCKET_LABELS = {bucket: CAPTURE_BUCKET_LABELS[bucket] for bucket in CORRECTION_BUCKETS}


def bucket_dir(bucket):
    if not is_v02_correction_bucket(bucket):
        raise ValueError(f"Unknown v0.2 correction bucket: {bucket}")
    return _capture_bucket_dir(bucket)


def total_target():
    return sum(CORRECTION_TARGETS.values())


def load_manifest_index():
    index = {}
    if not CORRECTION_MANIFEST.exists():
        return index
    with open(CORRECTION_MANIFEST, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            index[row["sha256"]] = row
    return index


def append_manifest_entry(entry):
    CORRECTION_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with open(CORRECTION_MANIFEST, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=True) + "\n")


def unique_destination(directory, filename):
    directory = Path(directory)
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
