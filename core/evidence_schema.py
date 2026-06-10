from core.engine_sanitize import sanitize_external_engines


def build_integrity_from_report(report, file_hash=None, file_name=None, file_type=None, file_size=None):
    report_integrity = report.get("integrity")

    if report_integrity:
        return dict(report_integrity)

    legacy_hash = file_hash or report.get("file_hash")

    return {
        "original_sha256": legacy_hash,
        "analysis_sha256": report.get("analysis_sha256"),
        "file_name": file_name,
        "original_file_type": file_type,
        "original_file_size": file_size,
        "hash_algorithm": "SHA-256",
        "verification_status": "hash_recorded" if legacy_hash else "hash_missing",
        "tamper_evidence": "available" if legacy_hash else "unavailable",
    }


def build_evidence_record(
    file_id,
    timestamp,
    report,
    external_engines=None,
    user_feedback=None,
    file_hash=None,
    file_name=None,
    file_type=None,
    file_size=None,
):
    engines = sanitize_external_engines(external_engines or {})
    integrity = build_integrity_from_report(
        report,
        file_hash=file_hash,
        file_name=file_name,
        file_type=file_type,
        file_size=file_size,
    )

    prooforigin_score = report.get("summary", {}).get("ai_score")
    sightengine_score = engines.get("sightengine", {}).get("score")
    openai_vision_score = engines.get("openai_vision", {}).get("score")
    weighted_consensus = report.get("weighted_consensus", {})

    feedback = user_feedback or {
        "human_votes": 0,
        "ai_votes": 0,
        "edited_votes": 0,
        "disputed_votes": 0,
        "correct_votes": 0,
        "wrong_votes": 0,
    }

    stored_report = {
        "summary": report.get("summary"),
        "origin_analysis": report.get("origin_analysis"),
        "consensus_analysis": report.get("consensus_analysis"),
        "adversarial_analysis": report.get("adversarial_analysis"),
        "provenance_analysis": report.get("provenance_analysis"),
        "trace_analysis": report.get("trace_analysis"),
        "evidence": report.get("evidence", []),
        "warnings": report.get("warnings", []),
        "weighted_consensus": weighted_consensus,
        "original_consensus": report.get("original_consensus"),
        "forensic_context": report.get("forensic_context"),
        "engine_arbitration": report.get("engine_arbitration"),
        "human_summary": report.get("human_summary"),
        "contradiction_resolution": report.get("contradiction_resolution"),
        "camera_authenticity": report.get("camera_authenticity"),
        "camera_provenance": report.get("camera_provenance"),
        "integrity": integrity,
        "bitcoin_lite_anchor": report.get("bitcoin_lite_anchor"),
        "file_id": file_id,
        "training_status": report.get("training_status"),
    }

    training_data = {
        "prooforigin_score": prooforigin_score,
        "sightengine_score": sightengine_score,
        "openai_vision_score": openai_vision_score,
        "weighted_consensus": weighted_consensus,
        "visual_findings": report.get("visual_findings", []),
        "lighting_findings": report.get("lighting_findings", []),
        "ai_findings": report.get("ai_findings", []),
        "metadata": report.get("metadata_analysis", {}),
        "provenance": report.get("provenance_analysis", {}),
        "adversarial": report.get("adversarial_analysis", {}),
        "trace": report.get("trace_analysis", {}),
        "human_feedback": feedback,
        "training_timestamp": timestamp,
    }

    return {
        "report_id": file_id,
        "created_at": timestamp,
        "integrity": integrity,
        "report": stored_report,
        "prooforigin": {
            "score": prooforigin_score,
            "classification": report.get("summary", {}).get("label"),
        },
        "consensus": {
            "score": weighted_consensus.get("score")
            or report.get("consensus_analysis", {}).get("consensus_score"),
            "label": weighted_consensus.get("label")
            or report.get("consensus_analysis", {}).get("consensus_label"),
            "weighted": weighted_consensus,
        },
        "signals": report.get("signals", []),
        "metadata": report.get("metadata_analysis", {}),
        "provenance": report.get("provenance_analysis", {}),
        "adversarial": report.get("adversarial_analysis", {}),
        "trace": report.get("trace_analysis", {}),
        "engine_outputs": engines,
        "feedback": feedback,
        "training_data": training_data,
        "training_status": "pending_review",
    }
