def _clamp(value, low=0.0, high=100.0):
    return max(low, min(high, round(float(value), 2)))


def score_manipulation_risk(signal_hits, ml_features=None):
    ml_features = ml_features or {}
    risk = 15.0

    weights = {
        "missing_exif": 12,
        "ai_generation_software": 35,
        "overly_smooth_texture": 18,
        "high_noise_texture": 10,
        "low_resolution_source": 8,
        "square_aspect_ratio": 6,
        "overly_smooth_pixel_distribution": 16,
        "abnormal_noise_distribution": 10,
        "perfect_square_generation": 6,
        "lighting_inconsistency_detected": 14,
    }

    for hit in signal_hits:
        risk += weights.get(hit, 4)

    if not ml_features.get("has_exif"):
        risk += 8

    return _clamp(risk)


def score_ai_probability(
    *,
    base_score,
    signal_hits,
    manipulation_risk,
    external_scores=None,
):
    external_scores = external_scores or []
    score = float(base_score or 0)

    synthetic_hits = {
        "ai_generation_software",
        "overly_smooth_texture",
        "overly_smooth_pixel_distribution",
        "abnormal_noise_distribution",
    }
    synthetic_count = sum(1 for hit in signal_hits if hit in synthetic_hits)
    score += synthetic_count * 4
    score += manipulation_risk * 0.15

    usable_external = [s for s in external_scores if s is not None]
    if usable_external:
        external_avg = sum(usable_external) / len(usable_external)
        score = (score * 0.55) + (external_avg * 0.45)

    return _clamp(score)


def classify_confidence_label(ai_probability, complete_engine_count=1):
    if complete_engine_count <= 1:
        return "low"

    if ai_probability >= 75:
        return "moderate"
    if ai_probability >= 45:
        return "moderate"
    if ai_probability >= 25:
        return "low"
    return "low"


def build_weighted_analysis_scores(
    *,
    reasoner_score,
    signal_hits,
    ml_features,
    external_scores=None,
):
    manipulation_risk = score_manipulation_risk(signal_hits, ml_features=ml_features)
    ai_probability = score_ai_probability(
        base_score=reasoner_score,
        signal_hits=signal_hits,
        manipulation_risk=manipulation_risk,
        external_scores=external_scores,
    )
    confidence = classify_confidence_label(
        ai_probability,
        complete_engine_count=max(1, len([s for s in (external_scores or []) if s is not None]) + 1),
    )

    return {
        "ai_probability": ai_probability,
        "manipulation_risk": manipulation_risk,
        "confidence": confidence,
    }
