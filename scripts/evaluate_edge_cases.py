#!/usr/bin/env python3
"""Evaluate ProofOrigin CV v0.1 on local edge-case image folders (never committed)."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.dataset_utils import METRICS_PATH, MODEL_PATH, list_valid_images

EDGE_CASES_DIR = ROOT / "ml" / "edge_cases"
REPORTS_DIR = ROOT / "ml" / "reports"
IMPORT_MANIFEST = EDGE_CASES_DIR / "real_phone" / "_import_manifest.json"

EDGE_BUCKETS = {
    "real_phone": {"expected": "real", "fpr_bucket": True},
    "screenshots": {"expected": "real", "fpr_bucket": False},
    "edited_real": {"expected": "real", "fpr_bucket": False},
    "ai_generated": {"expected": "ai", "fnr_bucket": True},
}

REAL_PHONE_ALERT_THRESHOLD = 20.0
DISAGREEMENT_SPREAD_THRESHOLD = 15.0
RAINBOW_NOTE = (
    "Rainbow / sky / gradient images are high-priority calibration samples."
)

SCENE_SECTIONS = {
    "rainbow": "Rainbow Analysis",
    "windshield": "Windshield Analysis",
    "pet_photo": "Pet Photo Analysis",
    "photo_of_photo": "Photo-of-Photo Analysis",
    "trading_card": "Trading Card Analysis",
}


def _predicted_label(ai_probability, threshold=50.0):
    if ai_probability is None:
        return "uncertain"
    return "ai" if float(ai_probability) >= threshold else "real"


def _safe_div(numerator, denominator):
    return numerator / denominator if denominator else 0.0


def _load_import_manifest():
    if not IMPORT_MANIFEST.exists():
        return {}
    payload = json.loads(IMPORT_MANIFEST.read_text(encoding="utf-8"))
    return {row["filename"]: row for row in payload.get("records", [])}


def _load_threshold_recommendations():
    if not METRICS_PATH.exists():
        return {}
    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    full = metrics.get("full_dataset_evaluation") or {}
    return full.get("threshold_recommendations") or {}


def _run_detectors(image_path):
    try:
        from core.external_detectors import collect_detector_signals

        return collect_detector_signals(image_path)
    except Exception as exc:
        return {"detectors": [], "available_count": 0, "score_spread": 0.0, "error": str(exc)}


def _detector_disagreement(detector_bundle):
    spread = detector_bundle.get("score_spread") or 0.0
    available = [
        d
        for d in detector_bundle.get("detectors", [])
        if d.get("available") and d.get("ai_probability") is not None
    ]
    scores = {d["detector"]: d["ai_probability"] for d in available}
    return {
        "spread": spread,
        "disagreement": spread >= DISAGREEMENT_SPREAD_THRESHOLD,
        "detector_scores": scores,
        "available_count": detector_bundle.get("available_count", 0),
    }


def _calibration_warnings(ai_probability, predicted, expected="real"):
    warnings = []
    if ai_probability is None:
        warnings.append("Inference unavailable")
        return warnings

    prob = float(ai_probability)
    if expected == "real" and prob > REAL_PHONE_ALERT_THRESHOLD:
        warnings.append(f"ai_probability {prob}% exceeds {REAL_PHONE_ALERT_THRESHOLD}% alert threshold")
    if expected == "real" and predicted == "ai":
        warnings.append("False positive: real image classified as AI at threshold 50")
    if 20 <= prob <= 80:
        warnings.append("Score falls in inconclusive band (20–80)")
    if prob > 50 and expected == "real":
        warnings.append("Real photo scored above default 50% AI threshold")
    return warnings


def _analyze_image(path, bucket, meta, *, threshold=50.0, import_meta=None):
    from ml.inference_classifier import run_cv_inference

    result = run_cv_inference(path)
    prob = result.get("ai_probability")
    pred = _predicted_label(prob, threshold=threshold)
    expected = meta["expected"]
    detector_bundle = _run_detectors(path)
    disagreement = _detector_disagreement(detector_bundle)
    warnings = _calibration_warnings(prob, pred, expected=expected)

    filename = path.name
    categories = (import_meta or {}).get("scene_categories", [])

    return {
        "bucket": bucket,
        "filename": filename,
        "file_path": str(path),
        "expected": expected,
        "label": (import_meta or {}).get("label", "real_camera"),
        "human_verified_label": (import_meta or {}).get("human_verified_label", "real_camera"),
        "source": (import_meta or {}).get("source", "user_phone"),
        "scene_categories": categories,
        "ai_probability": prob,
        "predicted_class": pred,
        "confidence": result.get("confidence"),
        "status": result.get("status"),
        "detector_disagreement": disagreement,
        "calibration_warnings": warnings,
        "flagged_high_ai": prob is not None and float(prob) > REAL_PHONE_ALERT_THRESHOLD,
    }


def _scan_edge_cases():
    results = {}
    for bucket, meta in EDGE_BUCKETS.items():
        folder = EDGE_CASES_DIR / bucket
        folder.mkdir(parents=True, exist_ok=True)
        paths = [
            p
            for p in list_valid_images(folder)
            if p.name not in {".gitkeep", "_import_manifest.json"}
        ]
        results[bucket] = {"folder": str(folder), "paths": paths, "meta": meta}
    return results


def _section_stats(predictions, category):
    rows = [p for p in predictions if category in p.get("scene_categories", [])]
    probs = [float(p["ai_probability"]) for p in rows if p.get("ai_probability") is not None]
    fps = sum(1 for p in rows if p.get("predicted_class") == "ai" and p.get("expected") == "real")
    return {
        "count": len(rows),
        "false_positives": fps,
        "false_positive_rate": round(_safe_div(fps, len(rows)), 4) if rows else None,
        "average_ai_probability": round(sum(probs) / len(probs), 2) if probs else None,
        "highest_ai_probability": max(probs) if probs else None,
        "lowest_ai_probability": min(probs) if probs else None,
        "flagged_count": sum(1 for p in rows if p.get("flagged_high_ai")),
        "images": [
            {
                "filename": p["filename"],
                "ai_probability": p.get("ai_probability"),
                "predicted_class": p.get("predicted_class"),
                "calibration_warnings": p.get("calibration_warnings"),
            }
            for p in rows
        ],
    }


def _real_phone_aggregate(predictions):
    rows = [p for p in predictions if p.get("bucket") == "real_phone" and p.get("ai_probability") is not None]
    if not rows:
        return {}

    probs = [float(p["ai_probability"]) for p in rows]
    fps = sum(1 for p in rows if p.get("predicted_class") == "ai")
    highest = max(rows, key=lambda p: float(p["ai_probability"]))
    lowest = min(rows, key=lambda p: float(p["ai_probability"]))

    return {
        "count": len(rows),
        "false_positives": fps,
        "false_positive_rate": round(_safe_div(fps, len(rows)), 4),
        "average_ai_probability": round(sum(probs) / len(probs), 2),
        "highest_scoring": {
            "filename": highest["filename"],
            "ai_probability": highest["ai_probability"],
        },
        "lowest_scoring": {
            "filename": lowest["filename"],
            "ai_probability": lowest["ai_probability"],
        },
        "flagged_above_20": [p["filename"] for p in rows if p.get("flagged_high_ai")],
    }


def _deployment_recommendation(aggregate, flagged_count):
    fpr = aggregate.get("false_positive_rate")
    avg = aggregate.get("average_ai_probability")
    if not aggregate:
        return {
            "safe_for_deployment": False,
            "summary": "No edge-case samples evaluated.",
        }

    issues = []
    if fpr and fpr > 0.05:
        issues.append(f"FPR {fpr:.1%} exceeds 5% target on real phone photos")
    if flagged_count:
        issues.append(f"{flagged_count} images exceed {REAL_PHONE_ALERT_THRESHOLD}% AI probability")
    if avg and avg > 10:
        issues.append(f"Average AI probability ({avg}%) is elevated for verified real photos")

    safe = not issues and fpr is not None and fpr <= 0.05
    return {
        "safe_for_deployment": safe,
        "summary": "Proceed with caution" if issues else "Acceptable for staged rollout",
        "issues": issues,
    }


def _calibration_recommendations(aggregate, threshold_rec):
    recs = []
    fpr = aggregate.get("false_positive_rate")
    flagged = aggregate.get("flagged_above_20") or []

    if flagged:
        recs.append(
            f"Review flagged images ({', '.join(flagged)}) before production; "
            "rainbow/holographic/trading-card scenes may need category-specific thresholds."
        )
    if fpr and fpr > 0:
        recs.append(
            "Consider raising likely_human upper bound or adding scene-aware down-weighting "
            "for rainbow, windshield glare, and photo-of-photo captures."
        )
    else:
        recs.append("No false positives at threshold 50 on this phone-photo set.")

    likely_human = threshold_rec.get("likely_human", "ai_probability < 20")
    recs.append(f"Current tier recommendation: likely_human = {likely_human}")
    if aggregate.get("average_ai_probability", 0) <= 5:
        recs.append("Threshold 20 alert band appears appropriate for this sample set.")
    recs.append(
        "Collect additional: night/low-light phone photos, HEIC exports, social screenshots, "
        "and more rainbow/sky gradients from different devices."
    )
    return recs


def evaluate_edge_cases(*, threshold=50.0):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    if not MODEL_PATH.exists():
        blocked = {
            "status": "blocked",
            "reason": "blocked by missing model/data",
            "model_path": str(MODEL_PATH),
            "model_exists": False,
            "rainbow_calibration_note": RAINBOW_NOTE,
        }
        _write_reports(blocked, predictions=[])
        print(json.dumps(blocked, indent=2))
        return blocked

    import_lookup = _load_import_manifest()
    threshold_rec = _load_threshold_recommendations()
    scanned = _scan_edge_cases()
    predictions = []
    bucket_stats = {}

    for bucket, payload in scanned.items():
        meta = payload["meta"]
        expected = meta["expected"]
        stats = {
            "count": 0,
            "false_positives": 0,
            "false_negatives": 0,
            "high_ai_probability_real_phone": [],
        }

        for path in payload["paths"]:
            row = _analyze_image(
                path,
                bucket,
                meta,
                threshold=threshold,
                import_meta=import_lookup.get(path.name),
            )
            predictions.append(row)

            prob = row.get("ai_probability")
            pred = row.get("predicted_class")
            if prob is None or row.get("status") != "complete":
                continue

            stats["count"] += 1
            if expected == "real" and pred == "ai":
                stats["false_positives"] += 1
            if expected == "ai" and pred == "real":
                stats["false_negatives"] += 1
            if bucket == "real_phone" and row.get("flagged_high_ai"):
                stats["high_ai_probability_real_phone"].append(
                    {"filename": row["filename"], "ai_probability": float(prob)}
                )

        stats["false_positive_rate"] = (
            round(_safe_div(stats["false_positives"], stats["count"]), 4)
            if meta.get("fpr_bucket") or expected == "real"
            else None
        )
        stats["false_negative_rate"] = (
            round(_safe_div(stats["false_negatives"], stats["count"]), 4)
            if meta.get("fnr_bucket") or expected == "ai"
            else None
        )
        bucket_stats[bucket] = stats

    real_phone_agg = _real_phone_aggregate(predictions)
    scene_analysis = {
        key: _section_stats(predictions, key) for key in SCENE_SECTIONS
    }
    deployment = _deployment_recommendation(
        real_phone_agg,
        len(real_phone_agg.get("flagged_above_20", [])),
    )
    calibration_recs = _calibration_recommendations(real_phone_agg, threshold_rec)

    real_phone = bucket_stats.get("real_phone", {})
    ai_bucket = bucket_stats.get("ai_generated", {})
    empty_folders = [b for b, p in scanned.items() if not p["paths"]]

    report = {
        "status": "complete" if predictions else "empty",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_path": str(MODEL_PATH),
        "threshold": threshold,
        "real_phone_alert_threshold": REAL_PHONE_ALERT_THRESHOLD,
        "rainbow_calibration_note": RAINBOW_NOTE,
        "bucket_stats": bucket_stats,
        "real_phone_aggregate": real_phone_agg,
        "scene_analysis": scene_analysis,
        "false_positive_rate_real_phone": real_phone_agg.get("false_positive_rate"),
        "average_ai_probability_real_phone": real_phone_agg.get("average_ai_probability"),
        "highest_scoring_real_image": real_phone_agg.get("highest_scoring"),
        "lowest_scoring_real_image": real_phone_agg.get("lowest_scoring"),
        "false_negative_rate_ai_generated": ai_bucket.get("false_negative_rate"),
        "real_phone_high_ai_flags": real_phone.get("high_ai_probability_real_phone", []),
        "deployment_recommendation": deployment,
        "calibration_recommendations": calibration_recs,
        "threshold_recommendations": threshold_rec,
        "empty_folders": empty_folders,
        "total_images": len(predictions),
        "add_images_instructions": _add_images_instructions(empty_folders),
    }

    _write_reports(report, predictions)
    print(json.dumps(report, indent=2))
    return report


def _add_images_instructions(empty_folders):
    if not empty_folders:
        return None
    lines = [
        "Copy local-only test images into:",
        "  ml/edge_cases/real_phone/     — authentic phone/camera photos",
        "  ml/edge_cases/screenshots/    — UI captures and screen photos",
        "  ml/edge_cases/edited_real/    — lightly edited authentic images",
        "  ml/edge_cases/ai_generated/   — known synthetic images",
        "",
        "Priority: add rainbow, sky, and smooth-gradient photos to real_phone/",
        "Re-run: python scripts/import_edge_cases.py && python scripts/evaluate_edge_cases.py",
    ]
    return "\n".join(lines)


def _write_reports(summary, predictions):
    json_path = REPORTS_DIR / "cv_v01_edge_case_report.json"
    md_path = REPORTS_DIR / "cv_v01_edge_case_report.md"

    payload = {"summary": summary, "predictions": predictions}
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# ProofOrigin CV v0.1 Edge-Case Report",
        "",
        f"Generated: {summary.get('generated_at', 'n/a')}",
        "",
        f"**Status:** {summary.get('status')}",
        "",
        f"> {RAINBOW_NOTE}",
        "",
    ]

    if summary.get("status") == "blocked":
        lines.extend(["## Blocked", "", summary.get("reason", "Model not available"), ""])
    elif summary.get("status") == "empty":
        lines.extend(
            ["## No edge-case images found", "", summary.get("add_images_instructions", ""), ""]
        )
    else:
        agg = summary.get("real_phone_aggregate") or {}
        lines.extend(
            [
                "## Summary",
                "",
                f"- Total images evaluated: {summary.get('total_images', 0)}",
                f"- False positive rate (real_phone): {summary.get('false_positive_rate_real_phone')}",
                f"- Average AI probability (real_phone): {summary.get('average_ai_probability_real_phone')}",
                f"- Highest scoring real image: {json.dumps(summary.get('highest_scoring_real_image'))}",
                f"- Lowest scoring real image: {json.dumps(summary.get('lowest_scoring_real_image'))}",
                f"- Flagged (ai_probability > {REAL_PHONE_ALERT_THRESHOLD}): "
                f"{len(summary.get('real_phone_high_ai_flags', []))}",
                "",
                "## Per-image results",
                "",
                "| Filename | AI prob | Predicted | Confidence | Disagreement | Warnings |",
                "|----------|---------|-----------|------------|--------------|----------|",
            ]
        )
        for row in predictions:
            spread = row.get("detector_disagreement", {}).get("spread", 0)
            disagree = "yes" if row.get("detector_disagreement", {}).get("disagreement") else "no"
            warnings = "; ".join(row.get("calibration_warnings") or []) or "—"
            flag = " ⚠" if row.get("flagged_high_ai") else ""
            lines.append(
                f"| {row['filename']}{flag} | {row.get('ai_probability')} | "
                f"{row.get('predicted_class')} | {row.get('confidence')} | "
                f"spread={spread} ({disagree}) | {warnings} |"
            )
        lines.append("")

        for key, title in SCENE_SECTIONS.items():
            section = (summary.get("scene_analysis") or {}).get(key) or {}
            if not section.get("count"):
                continue
            lines.extend(
                [
                    f"## {title}",
                    "",
                    f"- Images: {section.get('count')}",
                    f"- False positive rate: {section.get('false_positive_rate')}",
                    f"- Average AI probability: {section.get('average_ai_probability')}",
                    f"- Highest AI probability: {section.get('highest_ai_probability')}",
                    f"- Lowest AI probability: {section.get('lowest_ai_probability')}",
                    f"- Flagged (>20): {section.get('flagged_count')}",
                    "",
                ]
            )
            for img in section.get("images", []):
                lines.append(
                    f"- **{img['filename']}** — ai_prob={img.get('ai_probability')}, "
                    f"pred={img.get('predicted_class')}"
                )
            lines.append("")

        deploy = summary.get("deployment_recommendation") or {}
        lines.extend(
            [
                "## Deployment assessment",
                "",
                f"- Safe for deployment: **{deploy.get('safe_for_deployment')}**",
                f"- Summary: {deploy.get('summary')}",
                "",
            ]
        )
        for issue in deploy.get("issues") or []:
            lines.append(f"- Issue: {issue}")
        lines.append("")

        lines.extend(["## Calibration recommendations", ""])
        for rec in summary.get("calibration_recommendations") or []:
            lines.append(f"- {rec}")
        lines.append("")

        lines.extend(
            [
                "## Additional photos to collect",
                "",
                "- More rainbow/sky/gradient scenes (different lighting, partial arcs)",
                "- Night-mode and HEIC phone exports",
                "- Windshield shots with heavy glare and rain streaks",
                "- Pet photos with motion blur",
                "- Photo-of-photo with glossy print glare",
                "- Known AI-generated controls in `ml/edge_cases/ai_generated/`",
                "",
            ]
        )

    if summary.get("empty_folders"):
        lines.extend(
            [
                "## Empty folders",
                "",
                ", ".join(summary["empty_folders"]),
                "",
                summary.get("add_images_instructions", ""),
                "",
            ]
        )

    md_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Evaluate CV classifier on edge-case folders")
    parser.add_argument("--threshold", type=float, default=50.0)
    args = parser.parse_args()
    evaluate_edge_cases(threshold=args.threshold)


if __name__ == "__main__":
    main()
