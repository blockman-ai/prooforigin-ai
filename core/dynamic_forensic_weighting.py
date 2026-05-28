def clamp(value, minimum=0, maximum=100):
    return max(minimum, min(maximum, value))


def calculate_dynamic_forensic_weight(
    report,
    external_engines=None,
    metadata=None,
):
    engines = external_engines or {}
    metadata = metadata or {}

    prooforigin_score = report.get("summary", {}).get("ai_score", 0) or 0
    openai_score = engines.get("openai_vision", {}).get("score") or 0
    sightengine_score = engines.get("sightengine", {}).get("score") or 0

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

    combined_text = " ".join(
        [visual_text, openai_findings, openai_summary]
    )

    human_score = 0
    synthetic_score = 0
    screenshot_score = 0
    provenance_score = 0

    human_terms = {
        "natural": 10,
        "real": 10,
        "camera": 12,
        "photograph": 12,
        "human-taken": 15,
        "consistent lighting": 12,
        "realistic texture": 12,
        "natural noise": 14,
        "sensor noise": 14,
        "low-light": 8,
        "sharp edges": 8,
        "printed text": 10,
        "authentic": 12,
        "no ai": 10,
        "lacks artificial": 12,
        "no signs": 8,
    }

    synthetic_terms = {
        "synthetic": 16,
        "ai-generated": 20,
        "generated": 14,
        "diffusion": 22,
        "unnatural": 14,
        "stylized": 12,
        "rendered": 14,
        "artificial": 12,
        "hallucinated": 20,
        "over-smoothed": 16,
        "smooth texture": 14,
        "malformed": 18,
        "impossible": 22,
        "composite": 14,
        "neon": 8,
    }

    screenshot_terms = {
        "screenshot": 16,
        "screen": 10,
        "browser": 10,
        "mobile": 8,
        "webpage": 12,
        "interface": 12,
        "ui": 10,
        "text overlay": 10,
        "re-encoded": 12,
        "compressed": 8,
    }

    for term, weight in human_terms.items():
        if term in combined_text:
            human_score += weight

    for term, weight in synthetic_terms.items():
        if term in combined_text:
            synthetic_score += weight

    for term, weight in screenshot_terms.items():
        if term in combined_text:
            screenshot_score += weight

    missing_exif = not metadata or len(metadata.keys()) == 0

    if not missing_exif:
        provenance_score += 15
        human_score += 8
    else:
        provenance_score -= 10

    engine_average = (
        prooforigin_score + openai_score + sightengine_score
    ) / 3

    engine_max = max(
        prooforigin_score,
        openai_score,
        sightengine_score,
    )

    if engine_average < 25:
        human_score += 20

    if engine_max >= 65:
        synthetic_score += 25

    if engine_max >= 85:
        synthetic_score += 40

    total = human_score + synthetic_score + max(screenshot_score, 0)

    if total <= 0:
        embedded_ai_likelihood = engine_average
    else:
        embedded_ai_likelihood = (
            synthetic_score / total
        ) * 100

    # Blend forensic signal with engine agreement
    embedded_ai_likelihood = (
        embedded_ai_likelihood * 0.55
    ) + (engine_average * 0.45)

    embedded_ai_likelihood = clamp(round(embedded_ai_likelihood, 2))

    screenshot_indicators = sum(
        1 for term in screenshot_terms if term in combined_text
    )

    synthetic_indicators = sum(
        1 for term in synthetic_terms if term in combined_text
    )

    human_indicators = sum(
        1 for term in human_terms if term in combined_text
    )

    return {
        "embedded_ai_likelihood": embedded_ai_likelihood,
        "human_score": round(human_score, 2),
        "synthetic_score": round(synthetic_score, 2),
        "screenshot_score": round(screenshot_score, 2),
        "provenance_score": round(provenance_score, 2),
        "engine_average": round(engine_average, 2),
        "engine_max": round(engine_max, 2),
        "missing_exif": missing_exif,
        "screenshot_indicators": screenshot_indicators,
        "synthetic_indicators": synthetic_indicators,
        "human_indicators": human_indicators,
    }
