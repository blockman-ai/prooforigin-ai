"""Map mixed external signals into cautious ProofOrigin decisions."""

DISAGREEMENT_SPREAD_THRESHOLD = 25.0


def _clamp(value, low=0.0, high=100.0):
    return max(low, min(high, round(float(value), 2)))


def assess_detector_disagreement(detector_bundle):
    detectors = detector_bundle.get("detectors") or []
    scores = [
        d.get("ai_probability")
        for d in detectors
        if d.get("available") and d.get("ai_probability") is not None
    ]
    if len(scores) < 2:
        return {
            "disagreement": False,
            "spread": 0.0,
            "decision_hint": None,
            "public_label_hint": None,
            "evaluation_mode_hint": None,
        }

    spread = max(scores) - min(scores)
    disagreement = spread >= DISAGREEMENT_SPREAD_THRESHOLD
    if not disagreement:
        return {
            "disagreement": False,
            "spread": round(spread, 2),
            "decision_hint": None,
            "public_label_hint": None,
            "evaluation_mode_hint": None,
        }

    avg = sum(scores) / len(scores)
    if 35 <= avg <= 65:
        public_label = "mixed"
        decision = "needs_more_evidence"
        mode = "calibration_uncertain"
    elif avg >= 65:
        public_label = "caution"
        decision = "caution"
        mode = "calibration_caution"
    else:
        public_label = "likely_human_made"
        decision = "caution"
        mode = "calibration_caution"

    return {
        "disagreement": True,
        "spread": round(spread, 2),
        "decision_hint": decision,
        "public_label_hint": public_label,
        "evaluation_mode_hint": mode,
        "average_ai_probability": round(avg, 2),
    }


def apply_calibration_to_scores(
    *,
    ai_probability,
    manipulation_risk,
    confidence,
    public_label,
    evaluation_mode,
    detector_bundle=None,
):
    bundle = detector_bundle or {}
    disagreement = assess_detector_disagreement(bundle)

    updated = {
        "ai_probability": ai_probability,
        "manipulation_risk": manipulation_risk,
        "confidence": confidence,
        "public_label": public_label,
        "evaluation_mode": evaluation_mode,
        "calibration_notes": [],
    }

    if not disagreement.get("disagreement"):
        return updated

    updated["calibration_notes"].append(
        f"External detectors disagreed (spread={disagreement['spread']}). "
        "ProofOrigin avoids a hard fake/real claim."
    )
    updated["public_label"] = disagreement["public_label_hint"] or public_label
    updated["evaluation_mode"] = disagreement["evaluation_mode_hint"] or evaluation_mode
    updated["confidence"] = "low"
    updated["manipulation_risk"] = _clamp(float(manipulation_risk) + 5.0)

    if disagreement.get("average_ai_probability") is not None:
        blended = (float(ai_probability) * 0.6) + (
            float(disagreement["average_ai_probability"]) * 0.4
        )
        updated["ai_probability"] = _clamp(blended)

    return updated
