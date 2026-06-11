#!/usr/bin/env python3
"""Import human-approved private dataset captures from Supabase into correction buckets.

Downloads images locally only. Never uploads files or exposes images through API routes.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.correction_utils import (
    BUCKET_LABELS,
    append_manifest_entry,
    bucket_dir,
    load_manifest_index,
    unique_destination,
)
from ml.dataset_utils import file_sha256, image_metadata, validate_readable_image
from ml.private_capture_utils import (
    capture_consent_ok,
    download_capture_object,
    fetch_captures,
    load_capture_config,
    normalize_correction_bucket,
)


def import_private_captures(*, dry_run=False, limit=None):
    config = load_capture_config()
    if not config["configured"]:
        summary = {
            "status": "blocked",
            "reason": "blocked by missing Supabase configuration",
            "missing_env": config["missing_env"],
        }
        print(json.dumps(summary, indent=2))
        return summary

    records, error = fetch_captures(config, approved_only=True)
    if error:
        summary = {"status": "blocked", "reason": "supabase_query_failed", **error}
        print(json.dumps(summary, indent=2))
        return summary

    manifest_index = load_manifest_index()
    imported = []
    skipped = []
    duplicates = []

    eligible = [
        r
        for r in records
        if capture_consent_ok(r) and r.get("storage_path")
    ]

    if limit is not None:
        eligible = eligible[:limit]

    for record in eligible:
        capture_id = record.get("id")
        try:
            bucket = normalize_correction_bucket(record.get("correction_bucket"))
        except ValueError as exc:
            skipped.append({"id": capture_id, "reason": str(exc)})
            continue

        storage_path = str(record.get("storage_path")).strip()
        filename = Path(storage_path).name or f"capture_{capture_id}.jpg"
        target_dir = bucket_dir(bucket)
        destination = unique_destination(target_dir, filename)

        if dry_run:
            imported.append(
                {
                    "id": capture_id,
                    "bucket": bucket,
                    "would_download": storage_path,
                    "destination": str(destination),
                }
            )
            continue

        try:
            download_capture_object(config, storage_path, destination)
        except Exception as exc:
            skipped.append({"id": capture_id, "reason": f"download_failed: {exc}"})
            continue

        ok, reason = validate_readable_image(destination)
        if not ok:
            destination.unlink(missing_ok=True)
            skipped.append({"id": capture_id, "reason": f"unreadable: {reason}"})
            continue

        digest = file_sha256(destination)
        if digest in manifest_index:
            duplicates.append(
                {
                    "id": capture_id,
                    "sha256": digest,
                    "existing_bucket": manifest_index[digest].get("bucket"),
                }
            )
            destination.unlink(missing_ok=True)
            continue

        meta = image_metadata(destination)
        entry = {
            "file_path": str(destination.resolve()),
            "bucket": bucket,
            "label": BUCKET_LABELS[bucket],
            "human_verified_label": record.get("human_verified_label")
            or BUCKET_LABELS[bucket],
            "source": record.get("source") or "website_capture",
            "consent_status": record.get("consent_status") or "granted",
            "sha256": digest,
            "width": meta.get("width"),
            "height": meta.get("height"),
            "format": meta.get("format"),
            "original_filename": filename,
            "capture_id": capture_id,
            "storage_path": storage_path,
            "suggested_label": record.get("suggested_label"),
            "reviewer_notes": record.get("reviewer_notes"),
            "notes": record.get("notes") or "private dataset capture import",
            "imported_at": datetime.now(timezone.utc).isoformat(),
        }
        append_manifest_entry(entry)
        manifest_index[digest] = entry
        imported.append(entry)

    summary = {
        "status": "complete",
        "approved_queried": len(records),
        "eligible_with_consent": len(eligible),
        "imported": len(imported),
        "duplicates_skipped": len(duplicates),
        "skipped": len(skipped),
        "dry_run": dry_run,
        "storage_bucket": config["storage_bucket"],
        "correction_root": str(ROOT / "ml" / "correction_sets" / "v0_2"),
    }
    if skipped:
        summary["skipped_details"] = skipped
    if duplicates:
        summary["duplicate_details"] = duplicates

    print(json.dumps(summary, indent=2))
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Import approved private dataset captures from Supabase"
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    import_private_captures(dry_run=args.dry_run, limit=args.limit)


if __name__ == "__main__":
    main()
