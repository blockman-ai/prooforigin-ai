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

    suppression_applied = confidence_escalation.get("suppression_applied", False)
    escalation_triggered = confidence_escalation.get("escalation_triggered", False)

    media_type = forensic_context.get("media_object_type", "Unknown")
    synthetic_likely = forensic_context.get("synthetic_content_likely", False)

    arbitration_explanation = engine_arbitration.get(
        "explanation",
        "Engine arbitration completed.",
    )

    if suppression_applied:
        summary = (
            f"{final_label}. The final calibrated AI probability is approximately "
            f"{round(final_score, 2)}%. Although forensic-context analysis detected "
            f"synthetic-like traits, the baseline engine scores did not strongly support "
            f"AI generation. Escalation safeguards were applied, so the image is treated "
            f"as more consistent with human-made or naturally captured media."
        )

    elif escalation_triggered:
        reasons = ", ".join(
            confidence_escalation.get("escalation_reasons", [])
        ) or "strong forensic indicators"

        summary = (
            f"{final_label}. The final calibrated AI probability is approximately "
            f"{round(final_score, 2)}%. Confidence was escalated because {reasons}. "
            f"The media appears to contain indicators consistent with synthetic or "
            f"AI-assisted generation."
        )

    elif final_score < 20:
        summary = (
            f"{final_label}. The final calibrated AI probability is approximately "
            f"{round(final_score, 2)}%. The image shows stronger human-made or natural "
            f"capture characteristics than AI-generation indicators. Any synthetic-like "
            f"traits were not strong enough to change the final verdict."
        )

    elif final_score < 45:
        summary = (
            f"{final_label}. The final calibrated AI probability is approximately "
            f"{round(final_score, 2)}%. The image contains some mixed or suspicious "
            f"signals, but the evidence does not strongly support AI generation."
        )

    else:
        summary = (
            f"{final_label}. The final calibrated AI probability is approximately "
            f"{round(final_score, 2)}%. The system detected enough forensic or engine "
            f"signals to classify the media as potentially AI-generated, AI-assisted, "
            f"or heavily edited."
        )

    return {
        "summary": summary,
        "final_score": round(final_score, 2),
        "final_label": final_label,
        "media_object_type": media_type,
        "synthetic_content_likely": synthetic_likely,
        "arbitration_note": arbitration_explanation,
        "suppression_applied": suppression_applied,
        "escalation_triggered": escalation_triggered,
    }
