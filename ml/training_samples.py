"""Collect merged training samples from bootstrap dataset and correction sets."""

from pathlib import Path

from ml.correction_utils import BUCKET_LABELS, CORRECTION_BUCKETS, bucket_dir
from ml.dataset_utils import collect_binary_training_samples, list_valid_images, validate_readable_image

REAL_CORRECTION_BUCKETS = frozenset(
    {
        "real_pet_photos",
        "phone_screen_photos",
        "indoor_soft_light",
        "screenshots",
    }
)
AI_CORRECTION_BUCKETS = frozenset({"ai_controls"})


def _correction_weight(bucket):
    return 2 if bucket in REAL_CORRECTION_BUCKETS else 1


def collect_correction_samples():
    samples = []
    counts = {bucket: 0 for bucket in CORRECTION_BUCKETS}

    for bucket in CORRECTION_BUCKETS:
        label = 1 if bucket in AI_CORRECTION_BUCKETS else 0
        directory = bucket_dir(bucket)
        weight = _correction_weight(bucket)
        for path in list_valid_images(directory):
            if path.name in {".gitkeep", "manifest.jsonl"}:
                continue
            ok, _ = validate_readable_image(path)
            if not ok:
                continue
            for _ in range(weight):
                samples.append((path, label, bucket))
            counts[bucket] += 1

    return samples, counts


def collect_merged_training_samples(*, min_per_class=2, split="train", include_correction=True):
    bootstrap_samples, _, real_count, ai_count = collect_binary_training_samples(
        min_per_class=min_per_class,
        split=split,
    )
    merged = [(path, label) for path, label, _bucket in bootstrap_samples]
    correction_counts = {bucket: 0 for bucket in CORRECTION_BUCKETS}

    if include_correction:
        correction_samples, correction_counts = collect_correction_samples()
        merged.extend((path, label) for path, label, _bucket in correction_samples)

    real_total = sum(1 for _, label in merged if label == 0)
    ai_total = sum(1 for _, label in merged if label == 1)

    return {
        "samples": merged,
        "bootstrap_real": real_count,
        "bootstrap_ai": ai_count,
        "correction_counts": correction_counts,
        "real_total": real_total,
        "ai_total": ai_total,
    }
