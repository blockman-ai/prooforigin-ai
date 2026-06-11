#!/usr/bin/env python3
"""Audit private dataset captures in Supabase and local correction progress."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from ml.private_capture_utils import audit_capture_records, fetch_captures, load_capture_config
from audit_correction_set import audit_correction_set
from audit_general_expansion import audit_general_expansion


def audit_private_dataset_captures():
    config = load_capture_config()
    report = {
        "supabase": {"configured": config["configured"]},
        "captures": {},
        "correction_progress": {},
        "retraining_gate": {},
    }

    if not config["configured"]:
        report["supabase"]["missing_env"] = config["missing_env"]
        report["captures"] = {
            "status": "blocked",
            "reason": "Supabase env vars not configured; remote capture audit skipped",
        }
    else:
        records, error = fetch_captures(config, approved_only=False)
        if error:
            report["captures"] = {"status": "blocked", **error}
        else:
            capture_audit = audit_capture_records(records)
            report["captures"] = {
                "status": "ok",
                **capture_audit,
            }
            report["supabase"]["storage_bucket"] = config["storage_bucket"]
            report["supabase"]["table"] = "private_dataset_captures"

    correction = audit_correction_set()
    expansion = audit_general_expansion()
    report["correction_progress"] = {
        "buckets": {
            bucket: {
                "count": data["count"],
                "target": data["target"],
                "remaining_to_target": data["remaining_to_target"],
                "meets_target": data["meets_target"],
            }
            for bucket, data in correction["buckets"].items()
        },
        "totals": correction["totals"],
    }
    report["general_expansion"] = {
        "buckets": {
            bucket: {"count": data["count"]}
            for bucket, data in expansion["buckets"].items()
        },
        "totals": expansion["totals"],
        "retraining": expansion["retraining"],
    }
    report["retraining_gate"] = correction["retraining"]

    return report


def main():
    report = audit_private_dataset_captures()
    print(json.dumps(report, indent=2))

    if not report["retraining_gate"].get("allowed"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
