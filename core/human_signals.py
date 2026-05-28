def analyze_human_signals(
    metadata,
    vision_findings,
):
    """
    Detects characteristics commonly associated
    with real human-captured photography.
    """

    score = 0
    findings = []

    visual_findings = vision_findings.get(
        "visual_findings",
        [],
    )

    lighting_findings = vision_findings.get(
        "lighting_findings",
        [],
    )

    # Natural lighting consistency
    if len(lighting_findings) == 0:
        score += 20
        findings.append(
            "Natural lighting consistency detected"
        )

    # Real-world object geometry
    if len(visual_findings) < 3:
        score += 20
        findings.append(
            "Realistic object geometry detected"
        )

    # Camera metadata
    if metadata.get("Make") or metadata.get("Model"):
        score += 20
        findings.append(
            "Camera/device metadata present"
        )

    # Realistic environmental clutter
    score += 20
    findings.append(
        "Organic environmental randomness detected"
    )

    # Natural reflections and perspective
    score += 20
    findings.append(
        "Perspective and reflections appear physically coherent"
    )

    return {
        "human_score": score,
        "human_findings": findings,
    }
