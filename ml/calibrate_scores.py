#!/usr/bin/env python3
"""Evaluate ProofOrigin scores against human-verified calibration labels."""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from ml.calibration_utils import CALIBRATION_MANIFEST, load_calibration_records

AI_LABELS = frozenset({"ai_generated", "ai", "synthetic", "likely_ai"})
REAL_LABELS = frozenset(
    {"real_camera", "real", "human_made", "likely_human_made", "edited_real", "screenshots"}
)
UNCERTAIN_LABELS = frozenset({"uncertain", "mixed", "needs_more_evidence", "caution"})


def _normalize_label(label):
    if label is None:
        return "uncertain"
    normalized = str(label).strip().lower().replace(" ", "_")
    if normalized in AI_LABELS:
        return "ai"
    if normalized in REAL_LABELS:
        return "real"
    if normalized in UNCERTAIN_LABELS:
        return "uncertain"
    return normalized


def _predicted_label(ai_probability, threshold=50.0):
    if ai_probability is None:
        return "uncertain"
    return "ai" if float(ai_probability) >= threshold else "real"


def _safe_div(numerator, denominator):
    return numerator / denominator if denominator else 0.0


def _classification_metrics(y_true, y_pred, positive_label="ai"):
    labels = sorted(set(y_true) | set(y_pred))
    matrix = {true: Counter() for true in labels}
    for true, pred in zip(y_true, y_pred):
        matrix[true][pred] += 1

    tp = sum(1 for t, p in zip(y_true, y_pred) if t == positive_label and p == positive_label)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t != positive_label and p == positive_label)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == positive_label and p != positive_label)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t != positive_label and p != positive_label)

    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * precision * recall, precision + recall)
    accuracy = _safe_div(tp + tn, len(y_true))

    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "confusion_matrix": {k: dict(v) for k, v in matrix.items()},
        "counts": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
    }


def _expected_calibration_error(records, bins=10):
    bucket = defaultdict(lambda: {"count": 0, "sum_prob": 0.0, "sum_outcome": 0.0})
    for record in records:
        prob = record.get("prooforigin_ai_probability")
        if prob is None:
            continue
        true = _normalize_label(record.get("human_verified_label") or record.get("true_label"))
        if true not in {"ai", "real"}:
            continue
        outcome = 1.0 if true == "ai" else 0.0
        prob_norm = max(0.0, min(1.0, float(prob) / 100.0))
        index = min(bins - 1, int(prob_norm * bins))
        bucket[index]["count"] += 1
        bucket[index]["sum_prob"] += prob_norm
        bucket[index]["sum_outcome"] += outcome

    ece = 0.0
    total = sum(v["count"] for v in bucket.values())
    if total == 0:
        return {"ece": None, "bins": []}

    bin_rows = []
    for index in range(bins):
        row = bucket[index]
        if row["count"] == 0:
            continue
        avg_conf = row["sum_prob"] / row["count"]
        avg_outcome = row["sum_outcome"] / row["count"]
        weight = row["count"] / total
        ece += weight * abs(avg_conf - avg_outcome)
        bin_rows.append(
            {
                "bin": index,
                "count": row["count"],
                "avg_confidence": round(avg_conf, 4),
                "avg_outcome": round(avg_outcome, 4),
            }
        )

    return {"ece": round(ece, 4), "bins": bin_rows}


def _human_made_photo_protection(records, threshold=50.0):
    """False positive rate on real human-made photos (real_camera bucket)."""
    real_camera = []
    all_real = []

    for record in records:
        true = _normalize_label(record.get("human_verified_label") or record.get("true_label"))
        raw_true = str(record.get("true_label", "")).strip().lower()
        prob = record.get("prooforigin_ai_probability")
        predicted = _predicted_label(prob, threshold=threshold)

        if true == "real":
            all_real.append(predicted == "ai")
        if raw_true == "real_camera":
            real_camera.append(predicted == "ai")

    return {
        "threshold": threshold,
        "real_camera_false_positive_rate": round(
            _safe_div(sum(real_camera), len(real_camera)), 4
        )
        if real_camera
        else None,
        "real_camera_samples": len(real_camera),
        "all_real_false_positive_rate": round(
            _safe_div(sum(all_real), len(all_real)), 4
        )
        if all_real
        else None,
        "all_real_samples": len(all_real),
        "goal": "Keep false positive rate low on authentic phone/camera photos",
    }


def evaluate_calibration(records, threshold=50.0):
    if not records:
        return {
            "error": "No calibration records found. Add entries to ml/calibration/calibration_manifest.jsonl",
            "record_count": 0,
        }

    y_true = []
    y_pred = []
    ai_records = []

    for record in records:
        true = _normalize_label(record.get("human_verified_label") or record.get("true_label"))
        if true not in {"ai", "real"}:
            continue
        pred = _predicted_label(record.get("prooforigin_ai_probability"), threshold=threshold)
        y_true.append(true)
        y_pred.append(pred)
        if true == "ai":
            ai_records.append(pred == "real")

    metrics = _classification_metrics(y_true, y_pred, positive_label="ai")
    metrics["calibration_error"] = _expected_calibration_error(records)
    metrics["human_made_photo_protection"] = _human_made_photo_protection(
        records, threshold=threshold
    )
    metrics["false_negative_rate_on_ai"] = round(
        _safe_div(sum(ai_records), len(ai_records)), 4
    ) if ai_records else None
    metrics["ai_samples_evaluated"] = len(ai_records)
    metrics["record_count"] = len(records)
    metrics["evaluated_binary_records"] = len(y_true)
    metrics["threshold"] = threshold
    return metrics


def main():
    parser = argparse.ArgumentParser(description="Evaluate ProofOrigin calibration manifest")
    parser.add_argument(
        "--manifest",
        default=str(CALIBRATION_MANIFEST),
        help="Path to calibration_manifest.jsonl",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=50.0,
        help="AI probability threshold for binary prediction",
    )
    args = parser.parse_args()

    records = load_calibration_records(args.manifest)
    report = evaluate_calibration(records, threshold=args.threshold)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
