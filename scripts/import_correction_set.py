#!/usr/bin/env python3
"""Import images into CV v0.2 correction buckets (local only, never committed)."""

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.correction_utils import (
    BUCKET_LABELS,
    CORRECTION_BUCKETS,
    CORRECTION_MANIFEST,
    CORRECTION_ROOT,
    bucket_dir,
)
from ml.dataset_utils import (
    file_sha256,
    image_metadata,
    is_image_file,
    validate_readable_image,
)


def _ensure_folders():
    CORRECTION_ROOT.mkdir(parents=True, exist_ok=True)
    for bucket in CORRECTION_BUCKETS:
        target = bucket_dir(bucket)
        target.mkdir(parents=True, exist_ok=True)
        gitkeep = target / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()


def _unique_destination(directory, filename):
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


def _load_manifest_index():
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


def _append_manifest(entry):
    CORRECTION_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with open(CORRECTION_MANIFEST, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=True) + "\n")


def import_correction_set(
    source_dir,
    bucket,
    *,
    source_tag="correction_import",
    consent_status="owner_provided",
    notes="",
    move=False,
    dry_run=False,
):
    if bucket not in CORRECTION_BUCKETS:
        raise SystemExit(
            f"bucket must be one of: {', '.join(CORRECTION_BUCKETS)}"
        )

    _ensure_folders()
    source_dir = Path(source_dir)
    if not source_dir.is_dir():
        raise SystemExit(f"Source directory not found: {source_dir}")

    target_dir = bucket_dir(bucket)
    label = BUCKET_LABELS[bucket]
    manifest_index = _load_manifest_index()
    imported = []
    skipped = []
    duplicates = []

    for path in sorted(source_dir.rglob("*")):
        if not path.is_file() or not is_image_file(path):
            continue

        ok, reason = validate_readable_image(path)
        if not ok:
            skipped.append({"source": str(path), "reason": reason})
            continue

        digest = file_sha256(path)
        if digest in manifest_index:
            duplicates.append(
                {
                    "source": str(path),
                    "existing_bucket": manifest_index[digest].get("bucket"),
                    "sha256": digest,
                }
            )
            continue

        destination = _unique_destination(target_dir, path.name)
        if dry_run:
            print(f"would import {path} -> {destination} [{bucket}]")
            continue

        if move:
            shutil.move(str(path), str(destination))
        else:
            shutil.copy2(path, destination)

        meta = image_metadata(destination)
        entry = {
            "file_path": str(destination.resolve()),
            "bucket": bucket,
            "label": label,
            "source": source_tag,
            "consent_status": consent_status,
            "sha256": digest,
            "width": meta.get("width"),
            "height": meta.get("height"),
            "format": meta.get("format"),
            "original_filename": path.name,
            "notes": notes,
            "imported_at": datetime.now(timezone.utc).isoformat(),
        }
        _append_manifest(entry)
        manifest_index[digest] = entry
        imported.append(entry)

    summary = {
        "status": "complete",
        "bucket": bucket,
        "source_dir": str(source_dir.resolve()),
        "target_dir": str(target_dir),
        "imported": len(imported),
        "skipped_unreadable": len(skipped),
        "duplicates_skipped": len(duplicates),
        "dry_run": dry_run,
        "move": move,
    }
    if skipped:
        summary["skipped"] = skipped
    if duplicates:
        summary["duplicates"] = duplicates
    print(json.dumps(summary, indent=2))
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Import images into CV v0.2 correction buckets"
    )
    parser.add_argument("--source-dir", required=True)
    parser.add_argument(
        "--bucket",
        required=True,
        choices=CORRECTION_BUCKETS,
        help="Correction bucket to populate",
    )
    parser.add_argument("--source-tag", default="correction_import")
    parser.add_argument("--consent-status", default="owner_provided")
    parser.add_argument("--notes", default="")
    parser.add_argument("--move", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    import_correction_set(
        args.source_dir,
        args.bucket,
        source_tag=args.source_tag,
        consent_status=args.consent_status,
        notes=args.notes,
        move=args.move,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
