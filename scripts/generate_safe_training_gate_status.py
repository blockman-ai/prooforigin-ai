#!/usr/bin/env python3
"""Write safe training gate status report without training or promoting models."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.safe_train_eval import CANDIDATE_MODEL_PATH
from scripts.audit_correction_set import audit_correction_set
from scripts.audit_private_dataset_captures import audit_private_dataset_captures

REPORT_PATH = ROOT / "ml" / "reports" / "safe_training_gate_status.md"


def generate_gate_status_report():
    audit = audit_private_dataset_captures()
    correction = audit["correction_progress"]
    gate = audit["retraining_gate"]
    captures = audit.get("captures") or {}

    candidate_status = "present" if CANDIDATE_MODEL_PATH.exists() else "none"
    promotion = (
        "manual_confirmation_required"
        if CANDIDATE_MODEL_PATH.exists()
        else "no_candidate"
    )

    lines = [
        "# Safe Training Gate Status",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        f"**Training gate:** {'OPEN' if gate.get('allowed') else 'CLOSED'}",
        "",
        "## Captures (remote)",
        "",
        f"- Status: {captures.get('status', 'n/a')}",
        f"- Total captures: {captures.get('total_captures', 'n/a')}",
        f"- Approved: {captures.get('approved_count', 'n/a')}",
        f"- Pending review: {captures.get('pending_review_count', 'n/a')}",
        f"- Rejected: {captures.get('rejected_count', 'n/a')}",
        f"- Duplicate records: {captures.get('duplicate_count', 'n/a')}",
        f"- Missing consent: {captures.get('missing_consent_count', 'n/a')}",
        "",
        "## Correction target progress",
        "",
    ]

    for bucket, data in correction.get("buckets", {}).items():
        lines.append(
            f"- `{bucket}`: {data['count']}/{data['target']} "
            f"({'met' if data['meets_target'] else 'need ' + str(data['remaining_to_target'])})"
        )

    expansion = audit.get("general_expansion") or {}
    lines.extend(
        [
            "",
            "## General expansion (not in v0.2 gate)",
            "",
            f"- Total images: {expansion.get('totals', {}).get('images', 0)}",
            f"- Buckets with data: {expansion.get('totals', {}).get('buckets_with_images', 0)}"
            f"/{expansion.get('totals', {}).get('buckets_total', 0)}",
            "",
        ]
    )
    for bucket, data in (expansion.get("buckets") or {}).items():
        if data.get("count"):
            lines.append(f"- `{bucket}`: {data['count']}")

    lines.extend(
        [
            "",
            "## Candidate model",
            "",
            f"- Candidate artifact: `{candidate_status}`",
            f"- Promotion recommendation: {promotion}",
            "",
            "Production model is never replaced automatically.",
            "",
        ]
    )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"report_path": str(REPORT_PATH), "training_gate_open": gate.get("allowed")}


def main():
    result = generate_gate_status_report()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
