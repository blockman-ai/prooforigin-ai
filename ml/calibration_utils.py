import json
from pathlib import Path

from ml.dataset_utils import CALIBRATION_DIR, REPO_ROOT

CALIBRATION_MANIFEST = CALIBRATION_DIR / "calibration_manifest.jsonl"

CALIBRATION_FIELDS = (
    "file_path",
    "true_label",
    "prooforigin_ai_probability",
    "manipulation_risk",
    "confidence",
    "decision_tier",
    "model_sources_used",
    "human_verified_label",
    "reviewer_notes",
    "public_label",
    "evaluation_mode",
    "recorded_at",
)


def append_calibration_record(record, manifest_path=CALIBRATION_MANIFEST):
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {field: record.get(field) for field in CALIBRATION_FIELDS}
    with open(manifest_path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
    return payload


def load_calibration_records(manifest_path=CALIBRATION_MANIFEST):
    manifest_path = Path(manifest_path)
    if not manifest_path.exists():
        return []

    records = []
    with open(manifest_path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def build_calibration_record_from_analyze(
    *,
    file_path,
    true_label,
    analyze_response,
    human_verified_label=None,
    reviewer_notes="",
):
    from datetime import datetime, timezone

    return {
        "file_path": str(file_path),
        "true_label": true_label,
        "prooforigin_ai_probability": analyze_response.get("ai_probability"),
        "manipulation_risk": analyze_response.get("manipulation_risk"),
        "confidence": analyze_response.get("confidence"),
        "decision_tier": analyze_response.get("decision_tier"),
        "model_sources_used": analyze_response.get("model_sources_used"),
        "human_verified_label": human_verified_label or true_label,
        "reviewer_notes": reviewer_notes,
        "public_label": analyze_response.get("public_label"),
        "evaluation_mode": analyze_response.get("evaluation_mode"),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
