def analyze_camera_authenticity(report, metadata=None):
    metadata = metadata or {}

    visual_text = " ".join(
        report.get("visual_findings", [])
        + report.get("lighting_findings", [])
        + report.get("ai_findings", [])
    ).lower()

    score = 0
    findings = []

    camera_terms = {
        "natural lighting": 15,
        "consistent lighting": 12,
        "realistic texture": 12,
        "natural noise": 15,
        "sensor noise": 15,
        "sharp focus": 10,
        "depth": 8,
        "motion blur": 8,
        "camera": 10,
        "photograph": 12,
        "real": 10,
        "printed text": 8,
        "physical": 10,
    }

    negative_terms = {
        "diffusion": -18,
        "synthetic": -15,
        "hallucinated": -20,
        "unnatural lighting": -16,
        "over-smoothed": -14,
        "malformed": -18,
        "rendered": -14,
        "ai-generated": -20,
    }

    for term, weight in camera_terms.items():
        if term in visual_text:
            score += weight
            findings.append(f"Camera-authenticity indicator detected: {term}")

    for term, weight in negative_terms.items():
        if term in visual_text:
            score += weight
            findings.append(f"Camera-authenticity concern detected: {term}")

    if metadata and len(metadata.keys()) > 0:
        score += 15
        findings.append("Metadata available, supporting capture provenance")
    else:
        score -= 10
        findings.append("Metadata limited or missing")

    score = max(0, min(100, score))

    if score >= 70:
        label = "Strong Camera Capture Signal"
    elif score >= 45:
        label = "Moderate Camera Capture Signal"
    elif score >= 25:
        label = "Weak Camera Capture Signal"
    else:
        label = "Low Camera Capture Confidence"

    return {
        "camera_authenticity_score": round(score),
        "camera_authenticity_label": label,
        "camera_findings": findings,
    }
