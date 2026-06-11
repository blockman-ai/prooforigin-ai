#!/usr/bin/env python3
"""Scan private dataset folders, compute SHA-256 hashes, and write manifest records.

Does not upload, expose, or serve raw images. Output stays local (gitignored).
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.dataset_utils import (
    DATASET_BUCKETS,
    MANIFEST_JSONL,
    bucket_dir,
    file_sha256,
    is_image_file,
    list_valid_images,
    validate_readable_image,
)

MANIFEST_FIELDS = [
    "file_path",
    "sha256",
    "label",
    "split",
    "source",
    "license",
    "consent_status",
    "provenance",
    "generator_or_camera_source",
    "created_at",
    "notes",
    "original_filename",
]


def _default_provenance(label, split):
    return f"vault_scan/{split}/{label}"


def _build_entry(
    path,
    *,
    label,
    split,
    source,
    license_note,
    consent_status,
    provenance,
    generator_or_camera_source,
    notes,
):
    return {
        "file_path": str(path.resolve()),
        "sha256": file_sha256(path),
        "label": label,
        "split": split,
        "source": source,
        "license": license_note,
        "consent_status": consent_status,
        "provenance": provenance or _default_provenance(label, split),
        "generator_or_camera_source": generator_or_camera_source,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "notes": notes,
        "original_filename": path.name,
    }


def _scan_split(split, *, source, license_note, consent_status, provenance, notes):
    entries = []
    skipped = []

    for bucket in DATASET_BUCKETS:
        directory = bucket_dir(bucket, split=split)
        for path in list_valid_images(directory):
            ok, reason = validate_readable_image(path)
            if not ok:
                skipped.append({"path": str(path), "reason": reason})
                continue
            entries.append(
                _build_entry(
                    path,
                    label=bucket,
                    split=split,
                    source=source,
                    license_note=license_note,
                    consent_status=consent_status,
                    provenance=provenance,
                    generator_or_camera_source="",
                    notes=notes,
                )
            )
    return entries, skipped


def _load_existing_manifest(path):
    if not path.exists():
        return []
    records = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def _merge_entries(existing, scanned):
    """Keep manual metadata for paths that still exist; replace sha256 if changed."""
    by_path = {row["file_path"]: row for row in existing}
    merged = []
    seen_paths = set()

    for entry in scanned:
        path = entry["file_path"]
        seen_paths.add(path)
        prior = by_path.get(path)
        if prior:
            entry["source"] = prior.get("source") or entry["source"]
            entry["license"] = prior.get("license") or entry["license"]
            entry["consent_status"] = prior.get("consent_status") or entry["consent_status"]
            entry["provenance"] = prior.get("provenance") or entry["provenance"]
            entry["generator_or_camera_source"] = (
                prior.get("generator_or_camera_source") or entry["generator_or_camera_source"]
            )
            entry["notes"] = prior.get("notes") or entry["notes"]
            entry["created_at"] = prior.get("created_at") or entry["created_at"]
        merged.append(entry)

    return merged


def hash_dataset(
    *,
    split="all",
    source="vault_scan",
    license_note="user-owned",
    consent_status="unknown",
    provenance="",
    notes="",
    update=False,
    dry_run=False,
):
    splits = ["train", "validation"] if split == "all" else [split]
    all_entries = []
    all_skipped = []

    for current_split in splits:
        entries, skipped = _scan_split(
            current_split,
            source=source,
            license_note=license_note,
            consent_status=consent_status,
            provenance=provenance,
            notes=notes,
        )
        all_entries.extend(entries)
        all_skipped.extend(skipped)

    if update:
        existing = _load_existing_manifest(MANIFEST_JSONL)
        all_entries = _merge_entries(existing, all_entries)

    summary = {
        "manifest_path": str(MANIFEST_JSONL),
        "records_written": len(all_entries),
        "skipped_unreadable": len(all_skipped),
        "splits": splits,
        "dry_run": dry_run,
        "update_mode": update,
    }

    if dry_run:
        summary["sample_records"] = all_entries[:3]
        print(json.dumps(summary, indent=2))
        return summary

    MANIFEST_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_JSONL, "w", encoding="utf-8") as handle:
        for entry in all_entries:
            handle.write(json.dumps(entry, ensure_ascii=True) + "\n")

    print(json.dumps(summary, indent=2))
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Hash private dataset images and write local manifest (no upload)"
    )
    parser.add_argument(
        "--split",
        choices=["all", "train", "validation"],
        default="all",
    )
    parser.add_argument("--source", default="vault_scan")
    parser.add_argument("--license", default="user-owned")
    parser.add_argument(
        "--consent-status",
        choices=["granted", "pending", "not_applicable", "unknown"],
        default="unknown",
    )
    parser.add_argument("--provenance", default="")
    parser.add_argument("--notes", default="")
    parser.add_argument(
        "--update",
        action="store_true",
        help="Merge with existing manifest, preserving manual metadata fields",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    hash_dataset(
        split=args.split,
        source=args.source,
        license_note=args.license,
        consent_status=args.consent_status,
        provenance=args.provenance,
        notes=args.notes,
        update=args.update,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
