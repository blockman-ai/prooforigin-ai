#!/usr/bin/env python3
"""Organize raw images into ProofOrigin ML dataset buckets with manifest entries."""

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.dataset_utils import (
    DATASET_BUCKETS,
    append_manifest_entry,
    bucket_dir,
    build_manifest_entry,
    is_image_file,
    validate_readable_image,
)

LABEL_ALIASES = {
    "real": "real_camera",
    "ai": "ai_generated",
    "camera": "real_camera",
    "phone": "real_camera",
    "edited": "edited_real",
    "screenshot": "screenshots",
}


def _normalize_label(label):
    normalized = LABEL_ALIASES.get(label, label)
    if normalized not in DATASET_BUCKETS:
        raise SystemExit(
            f"label must be one of: {', '.join(DATASET_BUCKETS)} "
            f"(aliases: {', '.join(LABEL_ALIASES)})"
        )
    return normalized


def _unique_destination(target_dir, filename):
    target_dir.mkdir(parents=True, exist_ok=True)
    candidate = target_dir / filename
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix.lower() or ".jpg"
    index = 1
    while True:
        alt = target_dir / f"{stem}_{index}{suffix}"
        if not alt.exists():
            return alt
        index += 1


def _normalize_extension(path):
    suffix = path.suffix.lower()
    if suffix in {".jpeg", ".jpg", ".png", ".webp", ".gif", ".bmp"}:
        return suffix
    return ".jpg"


def prepare_dataset(
    source_dir,
    label,
    *,
    split="train",
    source="local_import",
    license_note="user-owned",
    generator_or_camera_source="",
    notes="",
    move=False,
    dry_run=False,
):
    label = _normalize_label(label)
    source_dir = Path(source_dir)
    if not source_dir.is_dir():
        raise SystemExit(f"Source directory not found: {source_dir}")

    target_dir = bucket_dir(label, split=split)
    copied = 0
    skipped = 0
    manifest_entries = []

    for path in sorted(source_dir.rglob("*")):
        if not path.is_file() or not is_image_file(path):
            continue

        ok, reason = validate_readable_image(path)
        if not ok:
            skipped += 1
            print(f"skip unreadable: {path} ({reason})")
            continue

        normalized_name = f"{path.stem}{_normalize_extension(path)}"
        destination = _unique_destination(target_dir, normalized_name)

        if dry_run:
            print(f"would copy {path} -> {destination}")
        elif move:
            shutil.move(str(path), str(destination))
        else:
            shutil.copy2(path, destination)

        entry = build_manifest_entry(
            destination=destination,
            label=label,
            source=source,
            license_note=license_note,
            generator_or_camera_source=generator_or_camera_source,
            notes=notes,
            original_filename=path.name,
        )
        if not dry_run:
            append_manifest_entry(entry)
        manifest_entries.append(entry)
        copied += 1

    summary = {
        "label": label,
        "split": split,
        "source_dir": str(source_dir),
        "target_dir": str(target_dir),
        "copied": copied,
        "skipped_unreadable": skipped,
        "mode": "move" if move else "copy",
        "dry_run": dry_run,
        "manifest_entries": len(manifest_entries),
    }
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Prepare ProofOrigin ML dataset folders")
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument(
        "--split",
        choices=["train", "validation"],
        default="train",
    )
    parser.add_argument("--source", default="local_import")
    parser.add_argument("--license", default="user-owned")
    parser.add_argument("--generator-or-camera-source", default="")
    parser.add_argument("--notes", default="")
    parser.add_argument("--move", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    prepare_dataset(
        source_dir=args.source_dir,
        label=args.label,
        split=args.split,
        source=args.source,
        license_note=args.license,
        generator_or_camera_source=args.generator_or_camera_source,
        notes=args.notes,
        move=args.move,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
