def generate_human_summary(
    weighted_consensus,
    forensic_context,
    engine_arbitration,
):
    score = weighted_consensus.get("score", 0)
    label = weighted_consensus.get("label", "Unknown")

    media_type = forensic_context.get(
        "media_object_type",
        "Unknown",
    )

    explanation = forensic_context.get(
        "forensic_context_explanation",
        "",
    )

    arbitration = engine_arbitration.get(
        "explanation",
        "",
    )

    summary = (
        f"{label}. "
        f"The analyzed media appears to be: {media_type}. "
        f"Overall AI likelihood estimated at approximately {score}%. "
        f"{explanation} "
        f"{arbitration}"
    )

    return {
        "summary": summary,
        "classification": label,
        "score": score,
    }
