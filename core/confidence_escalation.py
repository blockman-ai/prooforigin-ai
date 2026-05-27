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
            "Esc
