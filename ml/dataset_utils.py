import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".heic", ".heif"}

DATASET_BUCKETS = (
    "real_camera",
    "ai_generated",
    "edited_real",
    "screenshots",
    "uncertain",
)

BINARY_REAL_BUCKETS = frozenset({"real_camera", "edited_real", "screenshots"})
BINARY_AI_BUCKETS = frozenset({"ai_generated"})
TRAINING_SKIP_BUCKETS = frozenset({"uncertain"})

DATASET_REQUIRED_MESSAGE = (
    "Dataset required: add labeled images under ml/datasets/<bucket>/ "
    f"for buckets: {', '.join(DATASET_BUCKETS)}"
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASETS_DIR = REPO_ROOT / "ml" / "datasets"
VALIDATION_DIR = DATASETS_DIR / "validation"
MODELS_DIR = REPO_ROOT / "ml" / "models"
CALIBRATION_DIR = REPO_ROOT / "ml" / "calibration"
MODEL_PATH = MODELS_DIR / "prooforigin_cv_classifier.pt"
METRICS_PATH = MODELS_DIR / "metrics.json"
MANIFEST_JSONL = DATASETS_DIR / "manifest.jsonl"
MANIFEST_CSV = DATASETS_DIR / "manifest.csv"

# Legacy paths (still scanned for backward compatibility)
LEGACY_REAL_DIR = DATASETS_DIR / "real"
LEGACY_AI_DIR = DATASETS_DIR / "ai"


def bucket_dir(bucket, split="train"):
    if split == "validation":
        return VALIDATION_DIR / bucket
    return DATASETS_DIR / bucket


def is_image_file(path):
    return Path(path).suffix.lower() in IMAGE_EXTENSIONS


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_metadata(path):
    from PIL import Image

    metadata = {
        "format": None,
        "width": None,
        "height": None,
        "has_exif": False,
        "exif_field_count": 0,
    }
    try:
        with Image.open(path) as image:
            metadata["format"] = image.format
            metadata["width"] = image.width
            metadata["height"] = image.height
            exif = image.getexif() or {}
            metadata["exif_field_count"] = len(exif)
            metadata["has_exif"] = bool(exif)
    except Exception as exc:
        metadata["error"] = str(exc)
    return metadata


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


def iter_bucket_images(split="train"):
    images_by_bucket = {}
    for bucket in DATASET_BUCKETS:
        paths = list_valid_images(bucket_dir(bucket, split=split))
        images_by_bucket[bucket] = paths

    # Legacy fallback
    if LEGACY_REAL_DIR.is_dir():
        legacy_real = list_valid_images(LEGACY_REAL_DIR)
        if legacy_real:
            images_by_bucket.setdefault("real_camera", [])
            images_by_bucket["real_camera"].extend(legacy_real)
    if LEGACY_AI_DIR.is_dir():
        legacy_ai = list_valid_images(LEGACY_AI_DIR)
        if legacy_ai:
            images_by_bucket.setdefault("ai_generated", [])
            images_by_bucket["ai_generated"].extend(legacy_ai)

    return images_by_bucket


def audit_dataset_full(split="all"):
    splits = ["train", "validation"] if split == "all" else [split if split != "train" else "train"]
    if split == "validation":
        splits = ["validation"]
    elif split == "train":
        splits = ["train"]

    report = {"buckets": {}, "totals": {}, "duplicates": [], "class_imbalance": {}}
    sha_index = {}
    total_images = 0
    unreadable = []

    for current_split in splits:
        images_by_bucket = iter_bucket_images(split=current_split)
        for bucket, paths in images_by_bucket.items():
            bucket_key = f"{current_split}/{bucket}" if split == "all" else bucket
            bucket_report = {
                "count": 0,
                "formats": {},
                "with_exif": 0,
                "without_exif": 0,
                "sizes": [],
                "unreadable": [],
            }

            for path in paths:
                ok, reason = validate_readable_image(path)
                if not ok:
                    unreadable.append({"path": str(path), "bucket": bucket, "reason": reason})
                    bucket_report["unreadable"].append({"path": str(path), "reason": reason})
                    continue

                meta = image_metadata(path)
                bucket_report["count"] += 1
                total_images += 1
                fmt = (meta.get("format") or "unknown").lower()
                bucket_report["formats"][fmt] = bucket_report["formats"].get(fmt, 0) + 1
                if meta.get("has_exif"):
                    bucket_report["with_exif"] += 1
                else:
                    bucket_report["without_exif"] += 1
                if meta.get("width") and meta.get("height"):
                    bucket_report["sizes"].append(
                        {"width": meta["width"], "height": meta["height"]}
                    )

                digest = file_sha256(path)
                if digest in sha_index:
                    report["duplicates"].append(
                        {
                            "sha256": digest,
                            "first": sha_index[digest],
                            "duplicate": str(path),
                        }
                    )
                else:
                    sha_index[digest] = str(path)

            report["buckets"][bucket_key] = bucket_report

    real_count = sum(
        report["buckets"].get(k, {}).get("count", 0)
        for k in report["buckets"]
        if "real_camera" in k or "edited_real" in k or "screenshots" in k
    )
    ai_count = sum(
        report["buckets"].get(k, {}).get("count", 0)
        for k in report["buckets"]
        if "ai_generated" in k
    )
    report["totals"] = {
        "images": total_images,
        "unreadable": len(unreadable),
        "duplicate_pairs": len(report["duplicates"]),
        "real_origin_buckets": real_count,
        "ai_generated_buckets": ai_count,
    }
    report["class_imbalance"] = {
        "real_origin": real_count,
        "ai_generated": ai_count,
        "ratio_real_to_ai": round(real_count / ai_count, 3) if ai_count else None,
    }
    report["ready_for_binary_training"] = real_count >= 2 and ai_count >= 2
    report["ready_for_calibration"] = total_images >= 5
    report["unreadable_files"] = unreadable
    return report


def append_manifest_entry(
    entry,
    *,
    manifest_jsonl=MANIFEST_JSONL,
    manifest_csv=MANIFEST_CSV,
):
    manifest_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_jsonl, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=True) + "\n")

    headers = [
        "file_path",
        "label",
        "source",
        "license",
        "generator_or_camera_source",
        "created_at",
        "notes",
        "sha256",
        "original_filename",
    ]
    write_header = not manifest_csv.exists()
    import csv

    with open(manifest_csv, "a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        if write_header:
            writer.writeheader()
        writer.writerow({key: entry.get(key, "") for key in headers})


def build_manifest_entry(
    *,
    destination,
    label,
    source,
    license_note="user-owned",
    generator_or_camera_source="",
    notes="",
    original_filename="",
):
    return {
        "file_path": str(destination),
        "label": label,
        "source": source,
        "license": license_note,
        "generator_or_camera_source": generator_or_camera_source,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "notes": notes,
        "sha256": file_sha256(destination),
        "original_filename": original_filename or Path(destination).name,
    }


def collect_binary_training_samples(min_per_class=2, split="train"):
    images_by_bucket = iter_bucket_images(split=split)
    samples = []
    counts = {bucket: 0 for bucket in DATASET_BUCKETS}

    for bucket, paths in images_by_bucket.items():
        if bucket in TRAINING_SKIP_BUCKETS:
            continue
        label = 1 if bucket in BINARY_AI_BUCKETS else 0
        for path in paths:
            ok, _ = validate_readable_image(path)
            if not ok:
                continue
            samples.append((path, label, bucket))
            counts[bucket] += 1

    real_count = sum(counts[b] for b in BINARY_REAL_BUCKETS)
    ai_count = counts.get("ai_generated", 0)
    if real_count < min_per_class or ai_count < min_per_class:
        raise SystemExit(DATASET_REQUIRED_MESSAGE)

    return samples, counts, real_count, ai_count


def ensure_dataset_ready(min_per_class=2, split="train"):
    samples, counts, real_count, ai_count = collect_binary_training_samples(
        min_per_class=min_per_class,
        split=split,
    )
    return {
        "samples": samples,
        "counts": counts,
        "real_count": real_count,
        "ai_count": ai_count,
    }
