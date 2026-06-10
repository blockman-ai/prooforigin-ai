from core.engine_sanitize import sanitize_external_engines

RESPONSE_SCHEMA_VERSION = "1.0"

LEGACY_DUPLICATE_KEYS_NOTE = (
    "camelCase and snake_case fields are duplicated for backward compatibility; "
    "prefer snake_case in new clients. Duplicate keys will be removed in a future version."
)


def build_analyze_response(
    result,
    file_id,
    metadata,
    original_metadata,
    converted_metadata,
    integrity,
    final_consensus,
    original_consensus,
    forensic_context,
    engine_arbitration,
    human_summary,
    contradiction_resolution,
    camera_authenticity,
    camera_provenance,
    bitcoin_lite_anchor,
    external_engines,
):
    sanitized_engines = sanitize_external_engines(external_engines)

    response = {
        **result,
        "file_id": file_id,
        "percent": final_consensus.get("score")
        if final_consensus.get("score") is not None
        else result.get("summary", {}).get("ai_score", 0),
        "metadata": metadata,
        "originalMetadata": original_metadata,
        "convertedMetadata": converted_metadata,
        "integrity": integrity,
        "proofOriginScore": result.get("consensus_analysis", {}).get("consensus_score"),
        "weightedConsensus": final_consensus,
        "weighted_consensus": final_consensus,
        "originalConsensus": original_consensus,
        "original_consensus": original_consensus,
        "confidenceEscalation": final_consensus,
        "confidence_escalation": final_consensus,
        "forensicContext": forensic_context,
        "forensic_context": forensic_context,
        "engineArbitration": engine_arbitration,
        "engine_arbitration": engine_arbitration,
        "humanSummary": human_summary,
        "human_summary": human_summary,
        "contradictionResolution": contradiction_resolution,
        "contradiction_resolution": contradiction_resolution,
        "cameraAuthenticity": camera_authenticity,
        "camera_authenticity": camera_authenticity,
        "cameraProvenance": camera_provenance,
        "camera_provenance": camera_provenance,
        "bitcoinLiteAnchor": bitcoin_lite_anchor,
        "bitcoin_lite_anchor": bitcoin_lite_anchor,
        "verdict": final_consensus.get("label")
        or result.get("summary", {}).get("label"),
        "engine_outputs": sanitized_engines,
        "response_meta": {
            "schema_version": RESPONSE_SCHEMA_VERSION,
            "legacy_duplicate_keys": LEGACY_DUPLICATE_KEYS_NOTE,
        },
    }

    return response
