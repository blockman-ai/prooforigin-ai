EXTERNAL_VENDOR_ENGINES = frozenset({"sightengine", "openai_vision"})
MAX_EXTERNAL_VENDOR_WEIGHT = 0.40

BASE_WEIGHTS = {
    "prooforigin": 0.35,
    "sightengine": 0.25,
    "openai_vision": 0.40,
}


def _cap_and_normalize_weights(active_weights):
    capped = {}

    for engine_name, weight in active_weights.items():
        if engine_name in EXTERNAL_VENDOR_ENGINES:
            capped[engine_name] = min(weight, MAX_EXTERNAL_VENDOR_WEIGHT)
        else:
            capped[engine_name] = weight

    total = sum(capped.values())
    if total == 0:
        return {}

    return {
        engine_name: round(weight / total, 4)
        for engine_name, weight in capped.items()
    }


def calculate_weighted_consensus(engines):
    active_weights = {}

    for engine_name, weight in BASE_WEIGHTS.items():
        engine = engines.get(engine_name, {})
        score = engine.get("score")

        if engine.get("status") == "complete" and score is not None:
            active_weights[engine_name] = weight

    effective_weights = _cap_and_normalize_weights(active_weights)

    if not effective_weights:
        return {
            "score": None,
            "label": "Insufficient Engine Data",
            "status": "pending",
            "engines_used": [],
            "effective_weights": {},
            "complete_engine_count": 0,
            "single_engine_only": True,
        }

    total_score = 0.0

    for engine_name, weight in effective_weights.items():
        score = engines.get(engine_name, {}).get("score")
        total_score += float(score) * weight

    final_score = round(total_score, 2)
    engines_used = list(effective_weights.keys())

    prooforigin_engine = engines.get("prooforigin", {})

    ai_findings = (
        prooforigin_engine.get("ai_findings", [])
        or prooforigin_engine.get("findings", [])
        or []
    )

    synthetic_keywords = [
        "synthetic",
        "diffusion",
        "ai-generated",
        "stylized",
        "unnatural",
        "composite",
        "generated",
        "artificial",
        "rendered",
        "cgi",
    ]

    synthetic_hits = 0

    for finding in ai_findings:
        text = str(finding).lower()

        if any(keyword in text for keyword in synthetic_keywords):
            synthetic_hits += 1

    if synthetic_hits >= 2 and final_score < 50:
        final_score += 35

    final_score = min(final_score, 100)

    if final_score >= 85:
        label = "Strong AI Consensus"
    elif final_score >= 65:
        label = "Likely AI-Generated"
    elif final_score >= 45:
        label = "AI-Assisted or Heavily Edited"
    elif final_score >= 20:
        label = "Mixed / Suspicious"
    else:
        label = "Likely Human-Made"

    return {
        "score": final_score,
        "label": label,
        "status": "complete",
        "engines_used": engines_used,
        "synthetic_hits": synthetic_hits,
        "effective_weights": effective_weights,
        "complete_engine_count": len(engines_used),
        "single_engine_only": len(engines_used) <= 1,
    }
