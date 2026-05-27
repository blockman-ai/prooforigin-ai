def apply_confidence_escalation(
    weighted_consensus,
    forensic_context,
    engine_outputs,
):
    """
    Escalates consensus confidence when
    forensic indicators strongly suggest
    synthetic or AI-generated media.
    """

    score = weighted_consensus.get("score", 0)
    label = weighted_consensus.get("label", "Unknown")

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

    media_authenticity = forensic_context.get(
        "final_media_authenticity",
        "",
    ).lower()

    openai_label = (
        engine_outputs.get("openai_vision", {})
        .get("label", "")
        .lower()
    )

    escalation_triggered = False
    escalation_reasons = []

    # Strong synthetic forensic indicators
    if synthetic_indicators >= 4:
        score = max(score, 65)
        escalation_triggered = True
        escalation_reasons.append(
            "High synthetic indicator count"
        )

    # AI-authenticity context override
    if "ai-generated" in media_authenticity:
        score = max(score, 70)
        escalation_triggered = True
        escalation_reasons.append(
            "Forensic context identified likely AI generation"
        )

    # OpenAI Vision override
    if "ai" in openai_label:
        score = max(score, 75)
        escalation_triggered = True
        escalation_reasons.append(
            "OpenAI Vision classified media as AI-generated"
        )

    # Screenshot + synthetic combo
    if (
        screenshot_indicators >= 2
        and synthetic_indicators >= 2
    ):
        score = max(score, 68)
        escalation_triggered = True
        escalation_reasons.append(
            "Screenshot/re-encoding with synthetic indicators"
        )

    # Final label recalculation
    if score >= 85:
        label = "Strong AI Consensus"
    elif score >= 65:
        label = "Likely AI-Generated"
    elif score >= 45:
        label = "AI-Assisted or Heavily Edited"

    return {
        "score": round(score, 2),
        "label": label,
        "escalation_triggered": escalation_triggered,
        "escalation_reasons": escalation_reasons,
    }
