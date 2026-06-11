#!/usr/bin/env python3
"""Import human-approved private dataset captures from Supabase into local bucket folders.

v0.2 correction buckets -> ml/correction_sets/v0_2/{bucket}/
General expansion buckets -> ml/correction_sets/general_expansion/{bucket}/

Downloads images locally only. Never uploads files or exposes images through API routes.
General expansion buckets are excluded from CV v0.2 retraining until explicitly mapped.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.capture_buckets import (
    GENERAL_EXPANSION_ROOT,
    V02_CORRECTION_ROOT,
    append_capture_manifest_entry,
    capture_bucket_label,
    is_general_expansion_bucket,
    is_v02_correction_bucket,
    load_combined_capture_manifest_index,
    normalize_capture_bucket,
    unique_capture_destination,
)
from ml.dataset_utils import file_sha256, image_metadata, validate_readable_image
from ml.private_capture_utils import (
    capture_bucket,
    download_capture_object,
    fetch_captures,
    import_eligible,
    load_capture_config,
)


def import_private_captures(*, dry_run=False, limit=None, quiet=False):
    config = load_capture_config()
    if not config["configured"]:
        summary = {
            "status": "blocked",
            "reason": "blocked by missing Supabase configuration",
            "missing_env": config["missing_env"],
        }
        if not quiet:
            print(json.dumps(summary, indent=2))
        return summary

    records, error = fetch_captures(config, approved_only=True)
    if error:
        summary = {"status": "blocked", "reason": "supabase_query_failed", **error}
        if not quiet:
            print(json.dumps(summary, indent=2))
        return summary

    manifest_index = load_combined_capture_manifest_index()
    imported = []
    skipped = []
    duplicates = []
    imported_v02 = 0
    imported_expansion = 0

    eligible = [r for r in records if import_eligible(r) and r.get("storage_path")]

    if limit is not None:
        eligible = eligible[:limit]

    for record in eligible:
        capture_id = record.get("id")
        digest_known = record.get("sha256")
        if digest_known and digest_known in manifest_index:
            duplicates.append(
                {
                    "id": capture_id,
                    "sha256": digest_known,
                    "existing_bucket": manifest_index[digest_known].get("bucket"),
                    "skipped_before_download": True,
                }
            )
            continue

        try:
            bucket = normalize_capture_bucket(capture_bucket(record))
        except ValueError as exc:
            skipped.append({"id": capture_id, "reason": str(exc)})
            continue

        storage_path = str(record.get("storage_path")).strip()
        filename = Path(storage_path).name or f"capture_{capture_id}.jpg"
        destination = unique_capture_destination(bucket, filename)

        if dry_run:
            imported.append(
                {
                    "id": capture_id,
                    "bucket": bucket,
                    "storage_tier": "v0_2" if is_v02_correction_bucket(bucket) else "general_expansion",
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
            "label": capture_bucket_label(bucket),
            "human_verified_label": record.get("human_verified_label")
            or capture_bucket_label(bucket),
            "source": record.get("source") or "website_capture",
            "consent_status": record.get("consent_status") or "granted",
            "sha256": digest,
            "width": meta.get("width"),
            "height": meta.get("height"),
            "format": meta.get("format"),
            "original_filename": filename,
            "capture_id": capture_id,
            "storage_path": storage_path,
            "storage_tier": "v0_2" if is_v02_correction_bucket(bucket) else "general_expansion",
            "suggested_label": record.get("suggested_label"),
            "reviewer_notes": record.get("reviewer_notes"),
            "notes": record.get("notes") or "private dataset capture import",
            "imported_at": datetime.now(timezone.utc).isoformat(),
        }
        append_capture_manifest_entry(entry, bucket)
        manifest_index[digest] = entry
        imported.append(entry)
        if is_v02_correction_bucket(bucket):
            imported_v02 += 1
        elif is_general_expansion_bucket(bucket):
            imported_expansion += 1

    summary = {
        "status": "complete",
        "approved_queried": len(records),
        "eligible_with_consent": len(eligible),
        "imported": len(imported),
        "imported_v02": imported_v02 if not dry_run else sum(
            1 for row in imported if row.get("storage_tier") == "v0_2"
        ),
        "imported_general_expansion": imported_expansion if not dry_run else sum(
            1 for row in imported if row.get("storage_tier") == "general_expansion"
        ),
        "duplicates_skipped": len(duplicates),
        "skipped": len(skipped),
        "dry_run": dry_run,
        "storage_bucket": config["storage_bucket"],
        "v02_correction_root": str(V02_CORRECTION_ROOT),
        "general_expansion_root": str(GENERAL_EXPANSION_ROOT),
    }
    if skipped:
        summary["skipped_details"] = skipped
    if duplicates:
        summary["duplicate_details"] = duplicates

    if not quiet:
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
