"""Optional external detector adapters for signal comparison and calibration."""

import os
from pathlib import Path

from core.external_engines import run_openai_vision_analysis, run_sightengine_analysis


def _normalize_score(value):
    if value is None:
        return None
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if score <= 1.0:
        score *= 100.0
    return max(0.0, min(100.0, score))


def run_sightengine_detector(image_path):
    result = run_sightengine_analysis(image_path)
    status = result.get("status")
    score = _normalize_score(result.get("score"))
    return {
        "detector": "sightengine",
        "status": status,
        "ai_probability": score,
        "label": result.get("label"),
        "available": status not in {"unconfigured", "failed"},
    }


def run_openai_vision_detector(image_path):
    result = run_openai_vision_analysis(image_path)
    status = result.get("status")
    score = _normalize_score(result.get("score"))
    return {
        "detector": "openai_vision",
        "status": status,
        "ai_probability": score,
        "label": result.get("label"),
        "available": status not in {"unconfigured", "failed"},
    }


def run_huggingface_detector(image_path):
    model_id = os.getenv("PROOFORIGIN_HF_MODEL", "").strip()
    if not model_id:
        return {
            "detector": "huggingface",
            "status": "unconfigured",
            "ai_probability": None,
            "label": "PROOFORIGIN_HF_MODEL not set",
            "available": False,
        }

    try:
        from transformers import pipeline
    except ImportError:
        return {
            "detector": "huggingface",
            "status": "unavailable",
            "ai_probability": None,
            "label": "transformers not installed",
            "available": False,
        }

    try:
        classifier = pipeline("image-classification", model=model_id)
        outputs = classifier(str(image_path))
        if not outputs:
            raise ValueError("empty classifier output")

        top = outputs[0]
        label = str(top.get("label", "")).lower()
        confidence = float(top.get("score", 0.0))
        ai_like = any(token in label for token in ("ai", "fake", "generated", "synthetic"))
        score = confidence * 100.0 if ai_like else (1.0 - confidence) * 100.0
        return {
            "detector": "huggingface",
            "status": "ok",
            "ai_probability": round(score, 2),
            "label": top.get("label"),
            "available": True,
        }
    except Exception as exc:
        return {
            "detector": "huggingface",
            "status": "failed",
            "ai_probability": None,
            "label": str(exc),
            "available": False,
        }


def run_local_classifier_detector(image_path):
    try:
        from ml.inference_classifier import run_cv_inference
    except ImportError:
        return {
            "detector": "prooforigin_cv_classifier",
            "status": "unavailable",
            "ai_probability": None,
            "label": "inference module unavailable",
            "available": False,
        }

    result = run_cv_inference(image_path)
    if not result.get("available"):
        return {
            "detector": "prooforigin_cv_classifier",
            "status": result.get("status", "unavailable"),
            "ai_probability": None,
            "label": result.get("reason", "model unavailable"),
            "available": False,
        }

    return {
        "detector": "prooforigin_cv_classifier",
        "status": "ok",
        "ai_probability": _normalize_score(result.get("ai_probability")),
        "label": result.get("label"),
        "available": True,
    }


def build_detector_bundle_from_results(*, external_engines=None, cv_result=None):
    detectors = []
    external_engines = external_engines or {}
    cv_result = cv_result or {}

    if cv_result.get("status") == "complete" and cv_result.get("ai_probability") is not None:
        detectors.append(
            {
                "detector": "prooforigin_cv_classifier",
                "status": "ok",
                "ai_probability": _normalize_score(cv_result.get("ai_probability")),
                "label": cv_result.get("label"),
                "available": True,
            }
        )

    for name, result in external_engines.items():
        if not isinstance(result, dict):
            continue
        status = result.get("status")
        score = _normalize_score(result.get("score"))
        detectors.append(
            {
                "detector": name,
                "status": status,
                "ai_probability": score,
                "label": result.get("label"),
                "available": status == "complete" and score is not None,
            }
        )

    return summarize_detector_bundle(detectors)


def summarize_detector_bundle(detectors):
    available = [d for d in detectors if d.get("available")]
    scores = [d["ai_probability"] for d in available if d.get("ai_probability") is not None]

    return {
        "detectors": detectors,
        "available_count": len(available),
        "score_spread": round(max(scores) - min(scores), 2) if len(scores) >= 2 else 0.0,
        "average_ai_probability": round(sum(scores) / len(scores), 2) if scores else None,
    }


def collect_detector_signals(image_path):
    image_path = Path(image_path)
    detectors = [
        run_local_classifier_detector(image_path),
        run_sightengine_detector(image_path),
        run_openai_vision_detector(image_path),
        run_huggingface_detector(image_path),
    ]
    return summarize_detector_bundle(detectors)
