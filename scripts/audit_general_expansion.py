#!/usr/bin/env python3
"""Audit general expansion capture buckets (no v0.2 retraining gate)."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.capture_buckets import GENERAL_EXPANSION_BUCKETS, GENERAL_EXPANSION_ROOT, capture_bucket_dir
from ml.dataset_utils import file_sha256, image_metadata, list_valid_images, validate_readable_image


def audit_general_expansion():
    GENERAL_EXPANSION_ROOT.mkdir(parents=True, exist_ok=True)

    report = {
        "expansion_root": str(GENERAL_EXPANSION_ROOT),
        "buckets": {},
        "totals": {},
        "duplicates": [],
        "unreadable_files": [],
        "retraining": {
            "included_in_v02_gate": False,
            "note": "General expansion buckets are stored for future mapping; they do not gate CV v0.2 retraining.",
        },
    }

    sha_index = {}
    total_images = 0
    total_unreadable = 0

    for bucket in GENERAL_EXPANSION_BUCKETS:
        directory = capture_bucket_dir(bucket)
        directory.mkdir(parents=True, exist_ok=True)
        paths = [
            p
            for p in list_valid_images(directory)
            if p.name not in {".gitkeep", "manifest.jsonl"}
        ]

        bucket_report = {
            "count": 0,
            "formats": {},
            "unreadable": [],
        }

        for path in paths:
            ok, reason = validate_readable_image(path)
            if not ok:
                total_unreadable += 1
                bucket_report["unreadable"].append({"path": str(path), "reason": reason})
                report["unreadable_files"].append(
                    {"bucket": bucket, "path": str(path), "reason": reason}
                )
                continue

            meta = image_metadata(path)
            digest = file_sha256(path)
            bucket_report["count"] += 1
            total_images += 1
            fmt = (meta.get("format") or "unknown").lower()
            bucket_report["formats"][fmt] = bucket_report["formats"].get(fmt, 0) + 1

            if digest in sha_index:
                report["duplicates"].append(
                    {
                        "sha256": digest,
                        "first": sha_index[digest],
                        "duplicate": str(path),
                        "bucket": bucket,
                    }
                )
            else:
                sha_index[digest] = str(path)

        report["buckets"][bucket] = bucket_report

    report["totals"] = {
        "images": total_images,
        "buckets_with_images": sum(1 for b in GENERAL_EXPANSION_BUCKETS if report["buckets"][b]["count"]),
        "buckets_total": len(GENERAL_EXPANSION_BUCKETS),
        "unreadable": total_unreadable,
        "duplicate_pairs": len(report["duplicates"]),
    }

    return report


def main():
    parser = argparse.ArgumentParser(description="Audit general expansion capture buckets")
    args = parser.parse_args()
    report = audit_general_expansion()
    print(json.dumps(report, indent=2))
    if report["totals"]["unreadable"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
