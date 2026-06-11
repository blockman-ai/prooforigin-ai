#!/usr/bin/env python3
"""Audit CV v0.2 correction dataset buckets and readiness for retraining."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.correction_utils import (
    CORRECTION_BUCKETS,
    CORRECTION_MINIMUMS,
    CORRECTION_ROOT,
    CORRECTION_TARGETS,
    bucket_dir,
    total_target,
)
from ml.dataset_utils import (
    file_sha256,
    image_metadata,
    list_valid_images,
    validate_readable_image,
)


def audit_correction_set():
    CORRECTION_ROOT.mkdir(parents=True, exist_ok=True)

    report = {
        "correction_root": str(CORRECTION_ROOT),
        "buckets": {},
        "totals": {},
        "duplicates": [],
        "unreadable_files": [],
        "retraining": {},
    }

    sha_index = {}
    total_images = 0
    total_unreadable = 0

    for bucket in CORRECTION_BUCKETS:
        directory = bucket_dir(bucket)
        directory.mkdir(parents=True, exist_ok=True)
        paths = [
            p
            for p in list_valid_images(directory)
            if p.name not in {".gitkeep", "manifest.jsonl"}
        ]

        bucket_report = {
            "count": 0,
            "target": CORRECTION_TARGETS[bucket],
            "minimum_recommended": CORRECTION_MINIMUMS[bucket],
            "remaining_to_target": CORRECTION_TARGETS[bucket],
            "meets_target": False,
            "formats": {},
            "dimensions": [],
            "file_sizes_bytes": [],
            "sha256": [],
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
            size = path.stat().st_size

            bucket_report["count"] += 1
            total_images += 1
            fmt = (meta.get("format") or "unknown").lower()
            bucket_report["formats"][fmt] = bucket_report["formats"].get(fmt, 0) + 1
            if meta.get("width") and meta.get("height"):
                bucket_report["dimensions"].append(
                    {
                        "filename": path.name,
                        "width": meta["width"],
                        "height": meta["height"],
                    }
                )
            bucket_report["file_sizes_bytes"].append(
                {"filename": path.name, "bytes": size}
            )
            bucket_report["sha256"].append({"filename": path.name, "sha256": digest})

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

        remaining = max(0, CORRECTION_TARGETS[bucket] - bucket_report["count"])
        bucket_report["remaining_to_target"] = remaining
        bucket_report["meets_target"] = bucket_report["count"] >= CORRECTION_TARGETS[bucket]
        report["buckets"][bucket] = bucket_report

    all_met = all(report["buckets"][b]["meets_target"] for b in CORRECTION_BUCKETS)
    total_remaining = sum(report["buckets"][b]["remaining_to_target"] for b in CORRECTION_BUCKETS)

    report["totals"] = {
        "images": total_images,
        "target": total_target(),
        "remaining_to_target": total_remaining,
        "unreadable": total_unreadable,
        "duplicate_pairs": len(report["duplicates"]),
        "buckets_meeting_target": sum(
            1 for b in CORRECTION_BUCKETS if report["buckets"][b]["meets_target"]
        ),
        "buckets_total": len(CORRECTION_BUCKETS),
    }
    report["retraining"] = {
        "allowed": all_met and total_unreadable == 0,
        "reason": (
            "All correction buckets meet v0.2 targets"
            if all_met
            else f"{total_remaining} images still needed across buckets"
        ),
        "minimums": CORRECTION_MINIMUMS,
    }

    return report


def main():
    parser = argparse.ArgumentParser(description="Audit CV v0.2 correction dataset")
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Omit per-file sha256 and dimensions from stdout JSON",
    )
    args = parser.parse_args()

    report = audit_correction_set()
    if args.compact:
        compact = json.loads(json.dumps(report))
        for bucket in compact.get("buckets", {}).values():
            bucket.pop("sha256", None)
            bucket.pop("dimensions", None)
            bucket.pop("file_sizes_bytes", None)
        print(json.dumps(compact, indent=2))
    else:
        print(json.dumps(report, indent=2))

    if not report["retraining"]["allowed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
