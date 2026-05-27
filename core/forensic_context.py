def analyze_forensic_context(report, external_engines=None, metadata=None):
    engines = external_engines or {}
    metadata = metadata or {}

    prooforigin_score = report.get("summary", {}).get("ai_score", 0)
    openai_score = engines.get("openai_vision", {}).get("score")
    sightengine_score = engines.get("sightengine", {}).get("score")

    visual_text = " ".join(
        report.get("visual_findings", [])
        + report.get("ai_findings", [])
        + report.get("lighting_findings", [])
    ).lower()

    openai_findings = " ".join(
        engines.get("openai_vision", {}).get("findings", [])
    ).lower()

    openai_summary = str(
        engines.get("openai_vision", {}).get("reasoning_summary", "")
    ).lower()

    combined_text = " ".join([visual_text, openai_findings, openai_summary])

    screenshot_indicators = [
        "screenshot",
        "screen",
        "ui",
        "browser",
        "mobile",
        "text overlay",
        "webpage",
        "interface",
        "re-encoded",
        "compressed",
    ]

    synthetic_indicators = [
        "synthetic",
        "ai-generated",
        "diffusion",
        "unnatural",
        "stylized",
        "composite",
        "neon",
        "smooth texture",
        "generated",
        "rendered",
        "artificial",
    ]

    screenshot_hits = sum(
        1 for word in screenshot_indicators if word in combined_text
    )

    synthetic_hits = sum(
        1 for word in synthetic_indicators if word in combined_text
    )

    missing_exif = not metadata or len(metadata.keys()) == 0

    media_object_type = "Unknown"
    final_media_authenticity = "Unknown"
    explanation = "The image returned mixed forensic signals."

    embedded_ai_likelihood = max(
        prooforigin_score or 0,
        openai_score or 0,
        sightengine_score or 0,
    )

    if screenshot_hits >= 2:
        media_object_type = "Screenshot / Re-encoded Media"
        final_media_authenticity = "Human-created container or screenshot"

        if synthetic_hits >= 2 or embedded_ai_likelihood >= 60:
            embedded_ai_likelihood = max(embedded_ai_likelihood, 75)
            explanation = (
                "The uploaded file appears to be a screenshot or re-encoded media object. "
                "The overall file may be human-created, but it appears to contain embedded "
                "synthetic or AI-generated content inside the screenshot."
            )
        else:
            explanation = (
                "The uploaded file appears to be a screenshot or re-encoded media object. "
                "Screenshotting, compression, UI rendering, and re-encoding can weaken original "
                "AI-generation signals and reduce detector certainty."
            )

    elif synthetic_hits >= 2 or embedded_ai_likelihood >= 65:
        media_object_type = "Likely Synthetic Image"
        embedded_ai_likelihood = max(embedded_ai_likelihood, 75)
        final_media_authenticity = "Likely AI-generated or AI-assisted"
        explanation = (
            "The image contains visual characteristics commonly associated with AI generation, "
            "including synthetic texture, unnatural composition, stylized rendering, or diffusion-like traits."
        )

    elif missing_exif:
        media_object_type = "Low-Provenance Image"
        final_media_authenticity = "Insufficient provenance"
        explanation = (
            "The image lacks strong original capture metadata. This does not prove AI generation, "
            "but it lowers provenance confidence and should be interpreted cautiously."
        )

    return {
        "media_object_type": media_object_type,
        "embedded_ai_likelihood": round(embedded_ai_likelihood or 0),
        "final_media_authenticity": final_media_authenticity,
        "screenshot_or_reencoding_likely": screenshot_hits >= 2,
        "synthetic_content_likely": synthetic_hits >= 2
        or embedded_ai_likelihood >= 65,
        "transformation_layers": {
            "screenshot_indicators": screenshot_hits,
            "synthetic_indicators": synthetic_hits,
            "missing_exif": missing_exif,
        },
        "forensic_context_explanation": explanation,
    }
