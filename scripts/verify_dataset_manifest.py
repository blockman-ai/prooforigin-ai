#!/usr/bin/env python3
"""Verify dataset manifest integrity against schema and on-disk files."""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.dataset_utils import (
    DATASET_BUCKETS,
    MANIFEST_JSONL,
    file_sha256,
    validate_readable_image,
)

SCHEMA_PATH = ROOT / "ml" / "dataset_manifest.schema.json"
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
VALID_SPLITS = frozenset({"train", "validation"})
VALID_CONSENT = frozenset({"granted", "pending", "not_applicable", "unknown"})
WEAK_LICENSE = frozenset({"", "unknown", "tbd", "pending"})


def _load_schema():
    if not SCHEMA_PATH.exists():
        return {"required": []}
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _load_manifest(path):
    if not path.exists():
        return None, [{"error": "manifest_not_found", "path": str(path)}]

    records = []
    errors = []
    with open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                errors.append({"line": line_no, "error": f"invalid_json: {exc}"})
    return records, errors


def _is_missing(value):
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def verify_manifest(manifest_path=None, *, check_files=True):
    manifest_path = Path(manifest_path or MANIFEST_JSONL)
    schema = _load_schema()
    required_fields = schema.get("required", [])

    records, parse_errors = _load_manifest(manifest_path)
    if records is None:
        return {
            "status": "blocked",
            "manifest_path": str(manifest_path),
            "errors": parse_errors,
            "record_count": 0,
        }

    report = {
        "status": "ok",
        "manifest_path": str(manifest_path),
        "record_count": len(records),
        "required_fields": required_fields,
        "missing_required_fields": [],
        "missing_consent_or_license": [],
        "missing_files": [],
        "hash_mismatches": [],
        "duplicates": [],
        "unreadable_files": [],
        "invalid_labels": [],
        "invalid_splits": [],
        "invalid_sha256": [],
        "parse_errors": parse_errors,
    }

    sha_index = {}

    for index, record in enumerate(records):
        row_id = index + 1

        for field in required_fields:
            if _is_missing(record.get(field)):
                report["missing_required_fields"].append(
                    {"row": row_id, "field": field, "file_path": record.get("file_path")}
                )

        label = record.get("label")
        if label and label not in DATASET_BUCKETS:
            report["invalid_labels"].append({"row": row_id, "label": label})

        split = record.get("split")
        if split and split not in VALID_SPLITS:
            report["invalid_splits"].append({"row": row_id, "split": split})

        digest = record.get("sha256", "")
        if digest and not SHA256_RE.match(str(digest)):
            report["invalid_sha256"].append({"row": row_id, "sha256": digest})

        license_val = str(record.get("license", "")).strip().lower()
        consent_val = str(record.get("consent_status", "")).strip().lower()
        if license_val in WEAK_LICENSE or consent_val in {"", "unknown"}:
            report["missing_consent_or_license"].append(
                {
                    "row": row_id,
                    "file_path": record.get("file_path"),
                    "license": record.get("license"),
                    "consent_status": record.get("consent_status"),
                }
            )

        digest = record.get("sha256")
        file_path = record.get("file_path")
        if digest and file_path:
            if digest in sha_index:
                report["duplicates"].append(
                    {
                        "sha256": digest,
                        "first_row": sha_index[digest],
                        "duplicate_row": row_id,
                        "duplicate_path": file_path,
                    }
                )
            else:
                sha_index[digest] = row_id

        if not check_files or not file_path:
            continue

        path = Path(file_path)
        if not path.is_file():
            report["missing_files"].append({"row": row_id, "file_path": file_path})
            continue

        ok, reason = validate_readable_image(path)
        if not ok:
            report["unreadable_files"].append(
                {"row": row_id, "file_path": file_path, "reason": reason}
            )
            continue

        if digest:
            try:
                actual = file_sha256(path)
                if actual != digest:
                    report["hash_mismatches"].append(
                        {
                            "row": row_id,
                            "file_path": file_path,
                            "expected": digest,
                            "actual": actual,
                        }
                    )
            except OSError as exc:
                report["unreadable_files"].append(
                    {"row": row_id, "file_path": file_path, "reason": str(exc)}
                )

    issue_count = sum(
        len(report[key])
        for key in (
            "missing_required_fields",
            "missing_consent_or_license",
            "missing_files",
            "hash_mismatches",
            "duplicates",
            "unreadable_files",
            "invalid_labels",
            "invalid_splits",
            "invalid_sha256",
            "parse_errors",
        )
    )
    if issue_count:
        report["status"] = "issues_found"
    if not records:
        report["status"] = "empty_manifest"

    report["issue_count"] = issue_count
    report["verified_ok"] = issue_count == 0 and report["record_count"] > 0
    return report


def main():
    parser = argparse.ArgumentParser(description="Verify ProofOrigin dataset manifest")
    parser.add_argument(
        "--manifest",
        default=str(MANIFEST_JSONL),
        help="Path to manifest.jsonl",
    )
    parser.add_argument(
        "--skip-file-checks",
        action="store_true",
        help="Validate schema fields only; do not read image files",
    )
    args = parser.parse_args()

    report = verify_manifest(args.manifest, check_files=not args.skip_file_checks)
    print(json.dumps(report, indent=2))
    if report["status"] in {"blocked", "issues_found"}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
