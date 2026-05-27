def apply_confidence_escalation(
    weighted_consensus,
    forensic_context,
    engine_outputs,
):
    score = weighted_consensus.get("score", 0) or 0
    label = weighted_consensus.get("label", "Unknown")

    prooforigin_score = engine_outputs.get("prooforigin", {}).get("score") or 0
    sightengine_score = engine_outputs.get("sightengine", {}).get("score") or 0
    openai_score = engine_outputs.get("openai_vision", {}).get("score") or 0

    synthetic_indicators = (
        forensic_context.get("transformation_layers", {})
        .get("synthetic_indicators", 0)
    )

    screenshot_indicators = (
        forensic_context.get("transformation_layers", {})
        .get("screenshot_indicators", 0)
    )

    media_authenticity = (
        forensic_context.get("final_media_authenticity", "") or ""
    ).lower()

    escalation_triggered = False
    escalation_reasons = []
    suppression_applied = False
    suppression_reasons = []

    engine_support_count = 0

    if prooforigin_score >= 45:
        engine_support_count += 1

    if sightengine_score >= 45:
        engine_support_count += 1

    if openai_score >= 45:
        engine_support_count += 1

    # FALSE POSITIVE SAFEGUARD:
    # If all engines are low and synthetic indicators are weak/moderate,
    # do NOT escalate just because forensic context says synthetic.
    if (
        prooforigin_score < 35
        and sightengine_score < 35
        and openai_score < 35
        and synthetic_indicators < 4
    ):
        suppression_applied = True
        suppression_reasons.append(
            "Escalation suppressed because all engine scores were low and synthetic indicators were not strong enough."
        )

        return {
            "score": round(score, 2),
            "label": label,
            "escalation_triggered": False,
            "escalation_reasons": [],
            "suppression_applied": suppression_applied,
            "suppression_reasons": suppression_reasons,
        }

    # Strong synthetic evidence alone can escalate,
    # but only if indicator count is high.
    if synthetic_indicators >= 5 and engine_support_count >= 1:
        escalation_triggered = True
        escalation_reasons.append(
            "Very high synthetic indicator count"
        )

    elif synthetic_indicators >= 4 and engine_support_count >= 1:
        score = max(score, 65)
        escalation_triggered = True
        escalation_reasons.append(
            "Strong synthetic indicators supported by at least one engine"
        )

    # Forensic context override now requires engine support
    if "ai-generated" in media_authenticity and engine_support_count >= 1:
        score = max(score, 70)
        escalation_triggered = True
        escalation_reasons.append(
            "Forensic context identified likely AI generation with engine support"
        )

    # Strong OpenAI score override
    if openai_score >= 65:
        score = max(score, 75)
        escalation_triggered = True
        escalation_reasons.append(
            "OpenAI Vision strongly indicated AI-generated media"
        )

    # Screenshot + synthetic combo
    if (
        screenshot_indicators >= 2
        and synthetic_indicators >= 3
        and engine_support_count >= 1
    ):
        score = max(score, 68)
        escalation_triggered = True
        escalation_reasons.append(
            "Screenshot/re-encoding indicators combined with synthetic evidence"
        )

    if score >= 85:
        label = "Strong AI Consensus"
    elif score >= 65:
        label = "Likely AI-Generated"
    elif score >= 45:
        label = "AI-Assisted or Heavily Edited"
    elif score >= 20:
        label = "Mixed / Suspicious"
    else:
        label = "Likely Human-Made"

    return {
        "score": round(score, 2),
        "label": label,
        "escalation_triggered": escalation_triggered,
        "escalation_reasons": escalation_reasons,
        "suppression_applied": suppression_applied,
        "suppression_reasons": suppression_reasons,
    }
