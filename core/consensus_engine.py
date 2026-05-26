def calculate_weighted_consensus(engines):
    weights = {
        "prooforigin": 0.55,
        "sightengine": 0.45,
    }

    total_score = 0
    total_weight = 0

    for engine_name, weight in weights.items():
        engine = engines.get(engine_name, {})
        score = engine.get("score")

        if engine.get("status") == "complete" and score is not None:
            total_score += float(score) * weight
            total_weight += weight

    if total_weight == 0:
        return {
            "score": None,
            "label": "Insufficient Engine Data",
            "status": "pending",
        }

    final_score = round(total_score / total_weight, 2)

    if final_score >= 75:
        label = "Likely AI Generated"
    elif final_score >= 40:
        label = "Mixed / Suspicious"
    else:
        label = "Likely Human-Made"

    return {
        "score": final_score,
        "label": label,
        "status": "complete",
        "engines_used": list(weights.keys()),
    }
