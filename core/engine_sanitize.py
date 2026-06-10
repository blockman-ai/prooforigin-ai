PUBLIC_ENGINE_FIELDS = frozenset(
    {
        "status",
        "score",
        "label",
        "confidence",
        "findings",
        "reasoning_summary",
        "details",
        "ai_findings",
        "synthetic_hits",
        "engines_used",
        "escalation_triggered",
        "suppression_applied",
    }
)


def sanitize_engine_output(engine_result):
    if not isinstance(engine_result, dict):
        return engine_result

    return {
        key: value
        for key, value in engine_result.items()
        if key in PUBLIC_ENGINE_FIELDS
    }


def sanitize_external_engines(external_engines):
    if not isinstance(external_engines, dict):
        return external_engines

    return {
        engine_name: sanitize_engine_output(engine_result)
        for engine_name, engine_result in external_engines.items()
    }
