def build_forensic_signal_summary(
    *,
    metadata=None,
    extracted_signals=None,
    vision_findings=None,
    ml_features=None,
):
    metadata = metadata or {}
    extracted_signals = extracted_signals or []
    vision_findings = vision_findings or {}
    ml_features = ml_features or {}

    notes = []
    signal_hits = []

    exif = metadata.get("exif") or {}
    if not exif:
        signal_hits.append("missing_exif")
        notes.append("EXIF metadata is missing or stripped.")

    for signal in extracted_signals:
        signal_type = signal.get("type")
        if signal_type:
            signal_hits.append(signal_type)
        details = signal.get("details")
        strength = signal.get("strength")
        if details:
            notes.append(f"{details} (strength {strength})")

    for category in ("visual_findings", "lighting_findings", "ai_findings"):
        for finding in vision_findings.get(category, []):
            signal_hits.append(finding)
            notes.append(f"{category.replace('_', ' ')}: {finding}")

    if ml_features.get("low_resolution"):
        signal_hits.append("low_resolution_source")
        notes.append("Source resolution is below common camera-capture thresholds.")

    if ml_features.get("square_aspect"):
        signal_hits.append("square_aspect_ratio")

    if ml_features.get("pixel_variance") is not None:
        variance = float(ml_features["pixel_variance"])
        if variance < 800:
            signal_hits.append("overly_smooth_texture")
            notes.append("Pixel variance suggests unusually smooth texture.")
        elif variance > 12000:
            signal_hits.append("high_noise_texture")
            notes.append("Pixel variance suggests heavy noise or recompression.")

    unique_hits = sorted(set(signal_hits))

    return {
        "signal_hits": unique_hits,
        "signal_count": len(unique_hits),
        "forensic_notes": notes[:12],
    }
