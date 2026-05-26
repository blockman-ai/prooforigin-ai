from core.reasoning import ProofOriginReasoner


reasoner = ProofOriginReasoner()

sample_input = {
    "metadata": {
        "software": "Stable Diffusion",
    },
    "exif": {},
    "image_info": {
        "filename": "ai_test_image.png",
        "compression_quality": 70,
        "has_screen_dimensions": False,
    },
    "visual_findings": [
        "unnatural skin texture",
        "warped fingers",
        "inconsistent background details",
    ],
    "lighting_findings": [
        "shadow direction mismatch",
        "reflection inconsistency",
    ],
    "ai_findings": [
        "diffusion texture pattern",
        "synthetic facial symmetry",
        "repeated background artifacts",
        "unnatural object edges",
        "AI-like detail hallucination",
    ],
}

result = reasoner.analyze_input_data(sample_input)

print(result)
