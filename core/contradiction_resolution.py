def resolve_forensic_contradictions(
    weighted_consensus,
    forensic_context,
    engine_arbitration,
    confidence_escalation,
):
    final_score = confidence_escalation.get("score", 0)
    final_label = confidence_escalation.get(
        "label",
        "Unknown",
    )

    suppression_applied = confidence_escalation.get(
        "suppression_applied",
        False,
    )

    escalation_triggered = confidence_escalation.get(
        "escalation_triggered",
        False,
    )

    synthetic_indicators = (
        forensic_context.get(
            "transformation_layers",
            {},
        ).get("synthetic_indicators", 0)
    )

    screenshot_indicators = (
        forensic_context.get(
            "transformation_layers",
            {},
        ).get("screenshot_indicators", 0)
    )

    explanation = ""

    if suppression_applied:
        explanation = (
            "Although some forensic layers detected synthetic-like "
            "visual patterns, the overall engine agreement remained "
            "too weak to confidently classify the media as AI-generated. "
            "Suppression safeguards reduced the probability escalation "
            "to avoid a likely false positive."
        )

    elif escalation_triggered:
        explanation = (
            "Multiple forensic and engine-analysis layers aligned "
            "toward synthetic-media characteristics. Confidence escalation "
            "logic therefore increased the final AI probability estimate."
        )

    elif (
        synthetic_indicators >= 3
        and final_score < 20
    ):
        explanation = (
            "Some synthetic-like traits were detected, but the final "
            "consensus remained strongly weighted toward human-made "
            "media due to low engine agreement and stronger natural-image characteristics."
        )

    elif screenshot_indicators >= 2:
        explanation = (
            "The media appears to contain screenshot or re-encoding "
            "characteristics, which can weaken provenance confidence "
            "and complicate authenticity analysis."
        )

    else:
        explanation = (
            "No major contradiction was detected between forensic "
            "analysis layers and final calibrated consensus."
        )

    return {
        "final_score": final_score,
        "final_label": final_label,
        "contradiction_resolution": explanation,
        "suppression_applied": suppression_applied,
        "escalation_triggered": escalation_triggered,
    }
