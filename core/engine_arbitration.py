def analyze_engine_disagreement(external_engines):
    prooforigin_score = (
        external_engines.get("prooforigin", {}).get("score") or 0
    )

    sightengine_score = (
        external_engines.get("sightengine", {}).get("score") or 0
    )

    openai_score = (
        external_engines.get("openai_vision", {}).get("score") or 0
    )

    scores = [
        prooforigin_score,
        sightengine_score,
        openai_score,
    ]

    spread = max(scores) - min(scores)

    disagreement_detected = spread >= 40

    explanation = (
        "All engines produced relatively aligned results."
    )

    confidence = "High"

    if disagreement_detected:
        confidence = "Moderate"

        if openai_score > prooforigin_score:
            explanation = (
                "Advanced visual reasoning engines detected stronger "
                "synthetic characteristics than traditional forensic "
                "detectors. This may indicate stylized AI-generated "
                "content, transformed media, or screenshot layering."
            )

        elif prooforigin_score > openai_score:
            explanation = (
                "ProofOrigin forensic analysis detected synthetic "
                "patterns not strongly identified by external "
                "visual reasoning systems."
            )

        else:
            explanation = (
                "Cross-engine disagreement detected. The media may "
                "contain mixed authenticity indicators."
            )

    return {
        "disagreement_detected": disagreement_detected,
        "score_spread": spread,
        "confidence": confidence,
        "explanation": explanation,
    }
