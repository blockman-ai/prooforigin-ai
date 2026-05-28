from core.dynamic_forensic_weighting import (
    calculate_dynamic_forensic_weight,
)


def analyze_forensic_context(report, external_engines=None, metadata=None):
    engines = external_engines or {}
    metadata = metadata or {}

    dynamic = calculate_dynamic_forensic_weight(
        report=report,
        external_engines=engines,
        metadata=metadata,
    )

    embedded_ai_likelihood = dynamic.get(
        "embedded_ai_likelihood",
        0,
    )

    screenshot_hits = dynamic.get("screenshot_indicators", 0)
    synthetic_hits = dynamic.get("synthetic_indicators", 0)
    human_hits = dynamic.get("human_indicators", 0)
    missing_exif = dynamic.get("missing_exif", False)

    human_score = dynamic.get("human_score", 0)
    synthetic_score = dynamic.get("synthetic_score", 0)
    screenshot_score = dynamic.get("screenshot_score", 0)

    media_object_type = "Unknown"
    final_media_authenticity = "Unknown"

    if screenshot_hits >= 2 or screenshot_score >= 20:
        media_object_type = "Screenshot / Re-encoded Media"

        if embedded_ai_likelihood >= 55:
            final_media_authenticity = (
                "Screenshot or re-encoded media with possible embedded synthetic content"
            )
            explanation = (
                "The file appears to be a screenshot or re-encoded media object. "
                "Some embedded synthetic indicators were detected, but screenshoting "
                "and compression can distort forensic signals."
            )
        else:
            final_media_authenticity = (
                "Human-created screenshot or re-encoded media"
            )
            explanation = (
                "The file appears to be a screenshot or re-encoded media object. "
                "However, the calibrated forensic weighting does not strongly support "
                "AI generation."
            )

    elif embedded_ai_likelihood >= 65 and synthetic_score > human_score:
        media_object_type = "Likely Synthetic Image"
        final_media_authenticity = "Likely AI-generated or AI-assisted"
        explanation = (
            "The weighted forensic model detected stronger synthetic-media indicators "
            "than human-capture indicators. This suggests possible AI generation, "
            "AI assistance, or heavy digital manipulation."
        )

    elif embedded_ai_likelihood >= 35:
        media_object_type = "Mixed / Uncertain Media"
        final_media_authenticity = "Mixed forensic signals"
        explanation = (
            "The image contains some suspicious or synthetic-like traits, but the "
            "weighted evidence is not strong enough to classify it as AI-generated. "
            "This may occur with compression, glossy surfaces, screenshots, low light, "
            "collectibles, or edited real photographs."
        )

    elif missing_exif and human_hits <= 1:
        media_object_type = "Low-Provenance Image"
        final_media_authenticity = "Insufficient provenance"
        explanation = (
            "The image lacks strong original capture metadata. This does not prove AI "
            "generation, but it lowers provenance confidence and should be interpreted "
            "cautiously."
        )

    else:
        media_object_type = "Likely Natural Photograph"
        final_media_authenticity = "Likely human-made or naturally captured"
        explanation = (
            "The weighted forensic model found stronger human-capture indicators than "
            "synthetic indicators, including natural image structure, realistic texture, "
            "lighting consistency, or low AI engine agreement."
        )

    synthetic_content_likely = (
        embedded_ai_likelihood >= 65
        and synthetic_score > human_score
    )

    return {
        "media_object_type": media_object_type,
        "embedded_ai_likelihood": round(embedded_ai_likelihood or 0),
        "final_media_authenticity": final_media_authenticity,
        "screenshot_or_reencoding_likely": screenshot_hits >= 2,
        "synthetic_content_likely": synthetic_content_likely,
        "dynamic_forensic_weighting": dynamic,
        "transformation_layers": {
            "screenshot_indicators": screenshot_hits,
            "synthetic_indicators": synthetic_hits,
            "human_indicators": human_hits,
            "missing_exif": missing_exif,
        },
        "forensic_context_explanation": explanation,
    }
