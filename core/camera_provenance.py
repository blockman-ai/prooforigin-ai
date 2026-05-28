def classify_camera_provenance(report, metadata=None):
    metadata = metadata or {}

    visual_text = " ".join(
        report.get("visual_findings", [])
        + report.get("lighting_findings", [])
        + report.get("ai_findings", [])
    ).lower()

    scores = {
        "Smartphone Camera": 0,
        "DSLR / Mirrorless Camera": 0,
        "Webcam / Low-Quality Camera": 0,
        "Security / CCTV Camera": 0,
        "Screenshot / Re-encoded Media": 0,
        "Scanned / Printed Object": 0,
        "AI / Synthetic Render": 0,
        "Unknown Capture Source": 10,
    }

    if metadata:
        scores["Smartphone Camera"] += 15
        scores["DSLR / Mirrorless Camera"] += 10

    smartphone_terms = ["smartphone", "phone", "mobile", "hdr", "portrait"]
    dslr_terms = ["bokeh", "lens", "depth of field", "sharp focus"]
    webcam_terms = ["webcam", "low resolution", "compression", "soft focus"]
    cctv_terms = ["security", "cctv", "surveillance", "timestamp"]
    screenshot_terms = ["screenshot", "screen", "browser", "ui", "webpage"]
    printed_terms = ["printed text", "trading card", "card", "physical", "paper"]
    synthetic_terms = ["diffusion", "synthetic", "ai-generated", "rendered"]

    for term in smartphone_terms:
        if term in visual_text:
            scores["Smartphone Camera"] += 12

    for term in dslr_terms:
        if term in visual_text:
            scores["DSLR / Mirrorless Camera"] += 12

    for term in webcam_terms:
        if term in visual_text:
            scores["Webcam / Low-Quality Camera"] += 12

    for term in cctv_terms:
        if term in visual_text:
            scores["Security / CCTV Camera"] += 15

    for term in screenshot_terms:
        if term in visual_text:
            scores["Screenshot / Re-encoded Media"] += 18

    for term in printed_terms:
        if term in visual_text:
            scores["Scanned / Printed Object"] += 15

    for term in synthetic_terms:
        if term in visual_text:
            scores["AI / Synthetic Render"] += 18

    best_source = max(scores, key=scores.get)
    best_score = max(0, min(100, scores[best_source]))

    alternatives = sorted(
        scores.items(),
        key=lambda item: item[1],
        reverse=True,
    )[1:4]

    return {
        "most_likely_source": best_source,
        "source_confidence": round(best_score),
        "source_scores": scores,
        "alternative_sources": [
            {"source": source, "score": round(score)}
            for source, score in alternatives
        ],
    }
