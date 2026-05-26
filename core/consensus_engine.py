def calculate_weighted_consensus(engines):
    weights = {
        "prooforigin": 0.15,
        "sightengine": 0.10,
        "openai_vision": 0.75,
    }

    total_score = 0
    total_weight = 0
    engines_used = []

    for engine_name, weight in weights.items():
        engine = engines.get(engine_name, {})
        score = engine.get("score")

        if engine.get("status") == "complete" and score is not None:
            total_score += float(score) * weight
            total_weight += weight
            engines_used.append(engine_name)

    if total_weight == 0:
        return {
            "score": None,
            "label": "Insufficient Engine Data",
            "status": "pending",
            "engines_used": [],
        }

    final_score = round(total_score / total_weight, 2)

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
    }
