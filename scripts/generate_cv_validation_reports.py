#!/usr/bin/env python3
"""Generate CV v0.1 evaluation and calibration plan markdown reports."""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.calibrate_scores import evaluate_calibration
from ml.dataset_utils import METRICS_PATH, MODEL_PATH, audit_dataset_full, iter_bucket_images
from ml.inference_classifier import run_cv_inference

REPORTS_DIR = ROOT / "ml" / "reports"
EVAL_REPORT = REPORTS_DIR / "prooforigin_cv_v0_1_evaluation.md"
CALIBRATION_PLAN = REPORTS_DIR / "calibration_plan_v0_1.md"


def _detector_availability():
    return {
        "prooforigin_cv_classifier": MODEL_PATH.exists(),
        "openai_vision": bool(os.getenv("OPENAI_API_KEY", "").strip()),
        "sightengine": bool(
            os.getenv("SIGHTENGINE_USER", "").strip()
            and os.getenv("SIGHTENGINE_SECRET", "").strip()
        ),
        "huggingface": bool(os.getenv("PROOFORIGIN_HF_MODEL", "").strip()),
        "local_heuristics": True,
    }


def _run_full_evaluation(threshold=50.0):
    samples = []
    for bucket, paths in iter_bucket_images(split="train").items():
        if bucket == "uncertain":
            continue
        for path in paths:
            true = "ai" if bucket == "ai_generated" else "real"
            samples.append((path, bucket, true))

    records = []
    y_true = []
    y_pred = []
    by_bucket = defaultdict(lambda: {"fp": 0, "fn": 0, "n": 0, "probs": []})

    for path, bucket, true in samples:
        result = run_cv_inference(path)
        prob = result.get("ai_probability")
        if prob is None:
            continue
        pred = "ai" if float(prob) >= threshold else "real"
        y_true.append(true)
        y_pred.append(pred)
        by_bucket[bucket]["n"] += 1
        by_bucket[bucket]["probs"].append(float(prob))
        if true == "real" and pred == "ai":
            by_bucket[bucket]["fp"] += 1
        elif true == "ai" and pred == "real":
            by_bucket[bucket]["fn"] += 1
        records.append(
            {
                "file_path": str(path),
                "true_label": bucket,
                "prooforigin_ai_probability": float(prob),
                "human_verified_label": bucket,
            }
        )

    tp = sum(1 for t, p in zip(y_true, y_pred) if t == "ai" and p == "ai")
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == "real" and p == "ai")
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == "ai" and p == "real")
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == "real" and p == "real")
    n = len(y_true)

    acc = (tp + tn) / n if n else 0.0
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * recall / (prec + recall) if (prec + recall) else 0.0

    rc = by_bucket["real_camera"]
    ag = by_bucket["ai_generated"]
    calibration = evaluate_calibration(records, threshold=threshold)

    return {
        "evaluated_images": n,
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "confusion_matrix": {"real": {"real": tn, "ai": fp}, "ai": {"real": fn, "ai": tp}},
        "false_positive_rate_real_camera": round(rc["fp"] / rc["n"], 4) if rc["n"] else None,
        "false_negative_rate_ai_generated": round(ag["fn"] / ag["n"], 4) if ag["n"] else None,
        "per_bucket_at_50": {
            bucket: {
                "count": stats["n"],
                "false_positive_rate": round(stats["fp"] / stats["n"], 4)
                if stats["n"] and bucket != "ai_generated"
                else None,
                "false_negative_rate": round(stats["fn"] / stats["n"], 4)
                if stats["n"] and bucket == "ai_generated"
                else None,
                "avg_ai_probability": round(sum(stats["probs"]) / len(stats["probs"]), 2)
                if stats["probs"]
                else None,
            }
            for bucket, stats in by_bucket.items()
        },
        "calibration_evaluation": calibration,
        "false_positives": fp,
        "false_negatives": fn,
    }


def _blocked_evaluation_md():
    return "\n".join(
        [
            "# ProofOrigin CV v0.1 Evaluation",
            "",
            f"Generated: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Status: blocked",
            "",
            "Model validation is **blocked** because CV v0.1 has not been trained yet.",
            "",
            f"- Expected model: `{MODEL_PATH}`",
            f"- Expected metrics: `{METRICS_PATH}`",
            "",
            "Complete Part A vault work and dataset audit. Train with:",
            "",
            "```bash",
            "pip install -r requirements-dev.txt",
            "python -m ml.train_classifier",
            "python -m ml.evaluate_classifier",
            "```",
            "",
        ]
    )


def _blocked_calibration_md():
    return "\n".join(
        [
            "# Calibration Plan — CV v0.1",
            "",
            f"Generated: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Status: blocked",
            "",
            "Calibration planning requires a trained model and evaluation metrics.",
            "Run training first, then regenerate this report.",
            "",
        ]
    )


def generate_reports():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    model_exists = MODEL_PATH.exists()
    metrics_exists = METRICS_PATH.exists()

    if not model_exists or not metrics_exists:
        EVAL_REPORT.write_text(_blocked_evaluation_md(), encoding="utf-8")
        CALIBRATION_PLAN.write_text(_blocked_calibration_md(), encoding="utf-8")
        return {
            "status": "blocked",
            "reason": "blocked by missing model/data",
            "model_exists": model_exists,
            "metrics_exists": metrics_exists,
        }

    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    eval_live = _run_full_evaluation()
    full_eval = metrics.get("full_dataset_evaluation") or eval_live
    threshold_rec = full_eval.get("threshold_recommendations") or {}
    calibration = eval_live.get("calibration_evaluation") or {}
    ece = (calibration.get("calibration_error") or {}).get("ece")
    dataset_audit = audit_dataset_full(split="all")
    detectors = _detector_availability()

    eval_lines = [
        "# ProofOrigin CV v0.1 Evaluation",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Model",
        "",
        f"- Version: `{metrics.get('model_version', 'cv_v0.1')}`",
        f"- Weights: `{MODEL_PATH}`",
        f"- Trained at: {metrics.get('trained_at', 'n/a')}",
        "",
        "## Overall metrics (threshold 50)",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Accuracy | {full_eval.get('accuracy', eval_live['accuracy'])} |",
        f"| Precision | {full_eval.get('precision', eval_live['precision'])} |",
        f"| Recall | {full_eval.get('recall', eval_live['recall'])} |",
        f"| F1 | {full_eval.get('f1', eval_live['f1'])} |",
        f"| ECE | {ece} |",
        f"| FPR real_camera | {full_eval.get('false_positive_rate_real_camera', eval_live['false_positive_rate_real_camera'])} |",
        f"| FNR ai_generated | {full_eval.get('false_negative_rate_ai_generated', eval_live['false_negative_rate_ai_generated'])} |",
        "",
        "## Confusion matrix",
        "",
        "```json",
        json.dumps(full_eval.get("confusion_matrix", eval_live["confusion_matrix"]), indent=2),
        "```",
        "",
        "## Per-bucket evaluation",
        "",
        "```json",
        json.dumps(full_eval.get("per_bucket_at_50", eval_live["per_bucket_at_50"]), indent=2),
        "```",
        "",
        "## Threshold recommendations",
        "",
        f"- **likely_human:** {threshold_rec.get('likely_human', 'n/a')}",
        f"- **inconclusive:** {threshold_rec.get('inconclusive', 'n/a')}",
        f"- **likely_synthetic:** {threshold_rec.get('likely_synthetic', 'n/a')}",
        "",
        "## Detector comparison (configured)",
        "",
        "```json",
        json.dumps(detectors, indent=2),
        "```",
        "",
        "External detectors are compared when API keys are set; production `/analyze` blends CV at 55% when weights are present.",
        "",
        "## Dataset imbalance",
        "",
        "```json",
        json.dumps(dataset_audit.get("class_imbalance", {}), indent=2),
        "```",
        "",
        "## False positives / negatives",
        "",
        f"- False positives (real flagged as AI): {eval_live.get('false_positives', 'n/a')}",
        f"- False negatives (AI flagged as real): {eval_live.get('false_negatives', 'n/a')}",
        "",
        "## Human photo over-flagging",
        "",
        f"Real-camera FPR: {full_eval.get('false_positive_rate_real_camera')}. "
        "Target for production: ≤5% on `real_camera` before widening `likely_human` band.",
        "",
    ]
    EVAL_REPORT.write_text("\n".join(eval_lines), encoding="utf-8")

    weaknesses = []
    if (full_eval.get("false_positive_rate_real_camera") or 0) > 0.05:
        weaknesses.append("real_camera FPR exceeds 5% target at default threshold")
    if ece and ece > 0.05:
        weaknesses.append(f"ECE {ece} suggests miscalibration in mid-confidence bins")
    imbalance = dataset_audit.get("class_imbalance", {})
    if imbalance.get("ratio_real_to_ai") and imbalance["ratio_real_to_ai"] > 1.5:
        weaknesses.append("Dataset skewed toward real-origin buckets; monitor AI recall")

    cal_lines = [
        "# Calibration Plan — CV v0.1",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Recommended tiers",
        "",
        f"- **likely_human:** {threshold_rec.get('likely_human', 'ai_probability < 35')}",
        f"- **inconclusive:** {threshold_rec.get('inconclusive', '35–65')}",
        f"- **likely_synthetic:** {threshold_rec.get('likely_synthetic', 'ai_probability > 65')}",
        "",
        "## Calibration weaknesses",
        "",
    ]
    if weaknesses:
        cal_lines.extend(f"- {w}" for w in weaknesses)
    else:
        cal_lines.append("- No critical weaknesses flagged at current thresholds.")
    cal_lines.extend(
        [
            "",
            "## Priority edge cases",
            "",
            "- Rainbow, sky, and smooth-gradient photos (add to `ml/edge_cases/real_phone/`)",
            "- HEIC exports and heavy compression",
            "- Screenshots of social feeds",
            "- Lightly edited authentic portraits",
            "",
            "## Actions",
            "",
            "1. Populate `ml/edge_cases/` and run `python scripts/evaluate_edge_cases.py`",
            "2. Human-verify rows in `ml/calibration/calibration_manifest.jsonl`",
            "3. Re-run `python -m ml.calibrate_scores` after manifest updates",
            "4. Expand `uncertain` bucket before tightening `likely_synthetic`",
            "",
            "## Detector blend",
            "",
            "Keep `/analyze` contract unchanged. CV weight stays 55% when model loads; "
            "external engines optional for disagreement logging only.",
            "",
        ]
    )
    CALIBRATION_PLAN.write_text("\n".join(cal_lines), encoding="utf-8")

    return {
        "status": "complete",
        "evaluation_report": str(EVAL_REPORT),
        "calibration_plan": str(CALIBRATION_PLAN),
        "model_exists": True,
        "metrics_exists": True,
    }


def main():
    result = generate_reports()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
