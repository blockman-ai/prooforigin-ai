def generate_human_summary(
    weighted_consensus,
    forensic_context,
    engine_arbitration,
    confidence_escalation=None,
):
    confidence_escalation = confidence_escalation or {}

    final_score = (
        confidence_escalation.get("score")
        if confidence_escalation.get("score") is not None
        else weighted_consensus.get("score", 0)
    )

    final_label = (
        confidence_escalation.get("label")
        or weighted_consensus.get("label")
        or "Unknown"
    )

    suppression_applied = confidence_escalation.get(
        "suppression_applied",
        False,
    )

    escalation_triggered = confidence_escalation.get(
        "escalation_triggered",
        False,
    )

    escalation_reasons = confidence_escalation.get(
        "escalation_reasons",
        [],
    )

    arbitration_explanation = engine_arbitration.get(
        "explanation",
        "Engine arbitration completed.",
    )

    # -----------------------------
    # SUPPRESSED FALSE POSITIVE
    # -----------------------------
    if suppression_applied:

        summary = (
            f"{final_label}. "
            f"The final calibrated AI probability is approximately "
            f"{round(final_score, 2)}%. "

            f"Although some synthetic-like visual traits were detected, "
            f"the overall engine agreement remained weak and did not "
            f"strongly support AI generation. "

            f"The final result is therefore considered more consistent "
            f"with naturally captured or human-made media."
        )

    # -----------------------------
    # ESCALATED AI CONFIDENCE
    # -----------------------------
    elif escalation_triggered:

        reasons = ", ".join(escalation_reasons)

        if not reasons:
            reasons = "strong forensic indicators"

        summary = (
            f"{final_label}. "
            f"The final calibrated AI probability is approximately "
            f"{round(final_score, 2)}%. "

            f"Confidence escalation was triggered due to "
            f"{reasons}. "

            f"The combined forensic and engine evidence suggests "
            f"the media may contain AI-generated, AI-assisted, "
            f"or synthetic characteristics."
        )

    # -----------------------------
    # LOW AI PROBABILITY
    # -----------------------------
    elif final_score < 20:

        summary = (
            f"{final_label}. "
            f"The final calibrated AI probability is approximately "
            f"{round(final_score, 2)}%. "

            f"The image displays stronger natural-photography "
            f"characteristics than synthetic-media indicators, "
            f"including realistic lighting, geometry, textures, "
            f"and scene consistency."
        )

    # -----------------------------
    # MIXED / SUSPICIOUS
    # -----------------------------
    elif final_score < 45:

        summary = (
            f"{final_label}. "
            f"The final calibrated AI probability is approximately "
            f"{round(final_score, 2)}%. "

            f"The analysis detected mixed or uncertain signals. "
            f"Some visual patterns may resemble synthetic-media "
            f"characteristics, but the evidence is not currently "
            f"strong enough to confidently classify the media as AI-generated."
        )

    # -----------------------------
    # HIGH AI PROBABILITY
    # -----------------------------
    else:

        summary = (
            f"{final_label}. "
            f"The final calibrated AI probability is approximately "
            f"{round(final_score, 2)}%. "

            f"The system detected a combination of forensic indicators "
            f"and engine agreement commonly associated with AI-generated, "
            f"AI-assisted, or heavily manipulated media."
        )

    return {
        "summary": summary,
        "final_score": round(final_score, 2),
        "final_label": final_label,
        "suppression_applied": suppression_applied,
        "escalation_triggered": escalation_triggered,
        "arbitration_note": arbitration_explanation,
    }
