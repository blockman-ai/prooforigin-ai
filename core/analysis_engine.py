import os

from core.confidence_scoring import build_weighted_analysis_scores
from core.external_engines import run_openai_vision_analysis, run_sightengine_analysis
from core.forensic_signals import build_forensic_signal_summary
from core.ml_features import extract_ml_features

try:
    from ml.inference_classifier import run_cv_inference
except Exception:
    run_cv_inference = None


ENGINE_TIMEOUT_SECONDS = int(os.getenv("PROOFORIGIN_ENGINE_TIMEOUT_SECONDS", "60"))


def _safe_external_score(engine_result):
    if not isinstance(engine_result, dict):
        return None
    if engine_result.get("status") != "complete":
        return None
    score = engine_result.get("score")
    return score if score is not None else None


def _collect_model_sources(
    external_engines,
    *,
    heuristic_used=True,
    trained_model_used=False,
):
    sources = []
    if trained_model_used:
        sources.append("prooforigin_cv_classifier")
    if heuristic_used:
        sources.append("local_heuristics")

    for name, engine in (external_engines or {}).items():
        status = (engine or {}).get("status")
        if status == "complete":
            sources.append(name)
        elif status == "unconfigured":
            continue
        elif status in {"failed", "error"}:
            sources.append(f"{name}_unavailable")

    return sources


def run_modular_analysis(
    *,
    image_path,
    metadata,
    extracted_signals,
    vision_findings,
    reasoner_result,
    run_external=True,
):
    ml_features = extract_ml_features(image_path, metadata=metadata)
    signal_summary = build_forensic_signal_summary(
        metadata=metadata,
        extracted_signals=extracted_signals,
        vision_findings=vision_findings,
        ml_features=ml_features,
    )

    external_engines = {}
    if run_external:
        try:
            external_engines["sightengine"] = run_sightengine_analysis(image_path)
        except Exception as exc:
            external_engines["sightengine"] = {
                "status": "failed",
                "score": None,
                "label": f"Sightengine unavailable: {exc}",
            }

        try:
            external_engines["openai_vision"] = run_openai_vision_analysis(image_path)
        except Exception as exc:
            external_engines["openai_vision"] = {
                "status": "failed",
                "score": None,
                "label": f"OpenAI Vision unavailable: {exc}",
            }

    external_scores = [
        _safe_external_score(external_engines.get("sightengine")),
        _safe_external_score(external_engines.get("openai_vision")),
    ]

    cv_result = {"status": "unavailable"}
    if run_cv_inference is not None:
        try:
            cv_result = run_cv_inference(image_path)
        except Exception as exc:
            cv_result = {
                "status": "failed",
                "source": "prooforigin_cv_classifier",
                "reason": str(exc),
            }

    trained_model_used = cv_result.get("status") == "complete"
    if trained_model_used and cv_result.get("ai_probability") is not None:
        external_scores.append(cv_result["ai_probability"])

    reasoner_score = (reasoner_result or {}).get("summary", {}).get("ai_score", 0)
    weighted = build_weighted_analysis_scores(
        reasoner_score=reasoner_score,
        signal_hits=signal_summary["signal_hits"],
        ml_features=ml_features,
        external_scores=external_scores,
    )

    if trained_model_used and cv_result.get("ai_probability") is not None:
        blended = (weighted["ai_probability"] * 0.45) + (cv_result["ai_probability"] * 0.55)
        weighted["ai_probability"] = round(blended, 2)

    warnings = list((reasoner_result or {}).get("warnings") or [])
    if weighted["confidence"] == "low":
        warnings.append("Protocol-scoped evaluation only; confidence is limited.")

    model_sources_used = _collect_model_sources(
        external_engines,
        heuristic_used=True,
        trained_model_used=trained_model_used,
    )

    has_external = any(
        _safe_external_score(v) is not None for v in external_engines.values()
    )
    if trained_model_used:
        evaluation_mode = "trained_model"
        if has_external:
            evaluation_mode = "trained_model_with_external"
    elif has_external:
        evaluation_mode = "multi_signal_with_external"
    else:
        evaluation_mode = "local_heuristic_fallback"

    forensic_notes = list(signal_summary["forensic_notes"])
    if trained_model_used:
        forensic_notes.append(
            "Trained CV classifier contributed a protocol-scoped estimate (not absolute truth)."
        )
    elif cv_result.get("status") == "unavailable":
        forensic_notes.append(
            "Trained CV classifier unavailable; using heuristic and optional external engines."
        )

    return {
        "ai_probability": weighted["ai_probability"],
        "manipulation_risk": weighted["manipulation_risk"],
        "confidence": weighted["confidence"],
        "signal_summary": signal_summary,
        "forensic_notes": forensic_notes,
        "ml_features": ml_features,
        "model_sources_used": model_sources_used,
        "warnings": warnings,
        "external_engines": external_engines,
        "cv_classifier": cv_result,
        "evaluation_mode": evaluation_mode,
    }
