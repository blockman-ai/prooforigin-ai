from core.canonical_hash import canonical_json_hash
from core.constitution import PROOFORIGIN_CONSTITUTION
from core.engine_sanitize import sanitize_external_engines

CONSTITUTION_VERSION = PROOFORIGIN_CONSTITUTION.get("version", "1.0.0")
POLICY_VERSION = "2.1.0"

DISAGREEMENT_SPREAD_THRESHOLD = 40

LABEL_RANK = {
    "Likely Human-Made": 0,
    "Mixed / Suspicious": 1,
    "Mixed / Uncertain Signals": 1,
    "AI-Assisted or Heavily Edited": 2,
    "Possibly AI Generated": 2,
    "Likely AI-Generated": 3,
    "Strong AI Consensus": 4,
    "Insufficient Engine Data": 1,
    "Unknown": 1,
}

TIER_PUBLIC_LABEL_CAP = {
    "do_not_accuse": "Mixed / Uncertain Signals",
    "investigate": "Mixed / Uncertain Signals",
    "caution": "AI-Assisted or Heavily Edited",
    "act": "Likely AI-Generated",
}

PUBLIC_LABEL_OVERRIDES = {
    "Strong AI Consensus": "Elevated Synthetic Signals (Not Proof)",
    "Likely AI-Generated": "Possible AI-Generated Characteristics",
}

POLICY_CONFIG = {
    "policy_version": POLICY_VERSION,
    "constitution_version": CONSTITUTION_VERSION,
    "disagreement_spread_threshold": DISAGREEMENT_SPREAD_THRESHOLD,
    "max_external_vendor_weight": 0.40,
    "decision_tiers": ["act", "caution", "investigate", "do_not_accuse"],
}


def _label_rank(label):
    return LABEL_RANK.get(label, 1)


def _cap_label(label, cap_label):
    label_rank = _label_rank(label)
    cap_rank = _label_rank(cap_label)

    if label_rank <= cap_rank:
        return label

    return cap_label


def _soften_public_label(label):
    return PUBLIC_LABEL_OVERRIDES.get(label, label)


def _count_complete_scoring_engines(external_engines, engines_used):
    scoring_engines = set(engines_used or [])
    for engine_name, engine in external_engines.items():
        if engine_name == "openai_reasoning":
            continue
        if engine.get("status") == "complete" and engine.get("score") is not None:
            scoring_engines.add(engine_name)
    return len(scoring_engines)


def _map_decision_tier(
    complete_engine_count,
    disagreement_detected,
    score_spread,
    final_score,
    suppression_applied,
):
    if complete_engine_count <= 1:
        return "investigate"

    if disagreement_detected and score_spread >= DISAGREEMENT_SPREAD_THRESHOLD:
        return "investigate"

    if suppression_applied:
        return "do_not_accuse"

    if final_score < 20:
        return "do_not_accuse"

    if disagreement_detected or final_score < 45:
        return "caution"

    if final_score >= 65 and complete_engine_count >= 2:
        return "act"

    return "caution"


def _confidence_in_estimate(
    complete_engine_count,
    disagreement_detected,
    score_spread,
    suppression_applied,
):
    if complete_engine_count <= 1:
        return "low"

    if suppression_applied:
        return "low"

    if disagreement_detected and score_spread >= DISAGREEMENT_SPREAD_THRESHOLD:
        return "low"

    if disagreement_detected:
        return "moderate"

    if complete_engine_count >= 3:
        return "high"

    return "moderate"


def _build_uncertainty_notes(
    complete_engine_count,
    disagreement_detected,
    score_spread,
    suppression_applied,
    forensic_context,
):
    notes = [
        "Scores are forensic estimates, not legal or moral proof.",
    ]

    if complete_engine_count <= 1:
        notes.append(
            "Only one scoring engine was available, so confidence is limited."
        )

    if disagreement_detected:
        notes.append(
            f"Engine disagreement detected (spread {score_spread}). "
            "Additional verification is recommended."
        )

    if suppression_applied:
        notes.append(
            "False-positive safeguards reduced escalation because engine "
            "agreement was weak."
        )

    if forensic_context.get("screenshot_or_reencoding_likely"):
        notes.append(
            "Screenshot or re-encoding indicators may weaken provenance "
            "and forensic confidence."
        )

    missing_exif = (
        forensic_context.get("transformation_layers", {}).get("missing_exif")
    )
    if missing_exif:
        notes.append(
            "Missing or limited metadata lowers provenance confidence."
        )

    return notes


def _build_policy_warnings(
    decision_tier,
    public_label,
    existing_warnings,
    complete_engine_count,
    disagreement_detected,
):
    warnings = list(existing_warnings or [])

    warnings.append(
        "Detection is not judgment. Probability is not proof."
    )

    if decision_tier == "do_not_accuse":
        warnings.append(
            "Constitutional safeguard: avoid public accusations based on "
            "this result."
        )

    if decision_tier == "investigate":
        warnings.append(
            "Uncertainty is elevated. Treat this as an investigative signal, "
            "not a final conclusion."
        )

    if complete_engine_count <= 1:
        warnings.append(
            "Single-engine analysis cannot establish strong consensus."
        )

    if disagreement_detected:
        warnings.append(
            "Engines disagreed materially. No single engine should be treated "
            "as sole authority."
        )

    if public_label in PUBLIC_LABEL_OVERRIDES:
        warnings.append(
            "Public label softened to avoid accusatory certainty language."
        )

    deduped = []
    seen = set()
    for warning in warnings:
        if warning not in seen:
            deduped.append(warning)
            seen.add(warning)

    return deduped


def build_policy_hash():
    return canonical_json_hash(POLICY_CONFIG)


def build_engine_snapshot_hash(external_engines):
    snapshot = sanitize_external_engines(external_engines or {})
    return canonical_json_hash(snapshot)


def build_evidence_bundle_hash(bundle_payload):
    return canonical_json_hash(bundle_payload)


def apply_constitution_policy(
    final_consensus,
    original_consensus,
    engine_arbitration,
    external_engines,
    forensic_context=None,
    existing_warnings=None,
):
    forensic_context = forensic_context or {}
    engines_used = original_consensus.get("engines_used", [])
    complete_engine_count = _count_complete_scoring_engines(
        external_engines,
        engines_used,
    )

    disagreement_detected = engine_arbitration.get("disagreement_detected", False)
    score_spread = engine_arbitration.get("score_spread", 0)
    final_score = final_consensus.get("score") or 0
    suppression_applied = final_consensus.get("suppression_applied", False)
    raw_label = final_consensus.get("label", "Unknown")

    decision_tier = _map_decision_tier(
        complete_engine_count,
        disagreement_detected,
        score_spread,
        final_score,
        suppression_applied,
    )

    public_label_cap = TIER_PUBLIC_LABEL_CAP[decision_tier]
    capped_label = _cap_label(raw_label, public_label_cap)
    public_label = _soften_public_label(capped_label)

    suppression_required = decision_tier in {"do_not_accuse", "investigate"}

    confidence_in_estimate = _confidence_in_estimate(
        complete_engine_count,
        disagreement_detected,
        score_spread,
        suppression_applied,
    )

    uncertainty_notes = _build_uncertainty_notes(
        complete_engine_count,
        disagreement_detected,
        score_spread,
        suppression_applied,
        forensic_context,
    )

    warnings = _build_policy_warnings(
        decision_tier,
        public_label,
        existing_warnings,
        complete_engine_count,
        disagreement_detected,
    )

    policy_hash = build_policy_hash()

    return {
        "public_label_cap": public_label_cap,
        "public_label": public_label,
        "warnings": warnings,
        "decision_tier": decision_tier,
        "suppression_required": suppression_required,
        "policy_version": POLICY_VERSION,
        "constitution_version": CONSTITUTION_VERSION,
        "confidence_in_estimate": confidence_in_estimate,
        "uncertainty_notes": uncertainty_notes,
        "policy_hash": policy_hash,
        "complete_engine_count": complete_engine_count,
        "single_engine_only": complete_engine_count <= 1,
        "disagreement_detected": disagreement_detected,
    }
