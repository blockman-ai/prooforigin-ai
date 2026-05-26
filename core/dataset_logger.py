import json
import os
from datetime import datetime


class DatasetLogger:
    def __init__(
        self,
        log_path="data/realtime_analysis_log.jsonl",
        evidence_path="data/evidence",
        training_path="data/training",
        disagreement_path="data/disagreements",
    ):
        self.log_path = log_path
        self.evidence_path = evidence_path
        self.training_path = training_path
        self.disagreement_path = disagreement_path

        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        os.makedirs(self.evidence_path, exist_ok=True)
        os.makedirs(self.training_path, exist_ok=True)
        os.makedirs(self.disagreement_path, exist_ok=True)

    def log_analysis(
        self,
        file_id,
        report,
        external_engines=None,
        user_feedback=None,
        file_hash=None,
        file_name=None,
        file_type=None,
        file_size=None,
    ):
        timestamp = datetime.utcnow().isoformat()
        engines = external_engines or {}

        prooforigin_score = report.get("summary", {}).get("ai_score")
        sightengine_score = engines.get("sightengine", {}).get("score")
        openai_vision_score = engines.get("openai_vision", {}).get("score")
        weighted_consensus = report.get("weighted_consensus", {})

        integrity = {
            "sha256": file_hash,
            "file_name": file_name,
            "file_type": file_type,
            "file_size": file_size,
            "hash_algorithm": "SHA-256",
            "verification_status": "hash_recorded" if file_hash else "hash_missing",
            "tamper_evidence": "available" if file_hash else "unavailable",
        }

        feedback = user_feedback or {
            "human_votes": 0,
            "ai_votes": 0,
            "edited_votes": 0,
            "disputed_votes": 0,
            "correct_votes": 0,
            "wrong_votes": 0,
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

        evidence_record = {
            "report_id": file_id,
            "created_at": timestamp,
            "integrity": integrity,
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

        evidence_file = os.path.join(self.evidence_path, f"{file_id}.json")
        training_file = os.path.join(self.training_path, f"{file_id}.json")

        with open(evidence_file, "w", encoding="utf-8") as f:
            json.dump(evidence_record, f, indent=2)

        with open(training_file, "w", encoding="utf-8") as f:
            json.dump(training_data, f, indent=2)

        disagreement_record = None

        if prooforigin_score is not None and openai_vision_score is not None:
            score_gap = abs(float(openai_vision_score) - float(prooforigin_score))

            if score_gap >= 40:
                disagreement_record = {
                    "file_id": file_id,
                    "timestamp": timestamp,
                    "score_gap": score_gap,
                    "prooforigin_score": prooforigin_score,
                    "sightengine_score": sightengine_score,
                    "openai_vision_score": openai_vision_score,
                    "weighted_consensus": weighted_consensus,
                    "integrity": integrity,
                    "engine_outputs": engines,
                    "reason": "Large disagreement between ProofOrigin and OpenAI Vision",
                }

                disagreement_file = os.path.join(
                    self.disagreement_path,
                    f"{file_id}.json",
                )

                with open(disagreement_file, "w", encoding="utf-8") as f:
                    json.dump(disagreement_record, f, indent=2)

        entry = {
            "file_id": file_id,
            "timestamp": timestamp,
            "file_hash": file_hash,
            "file_name": file_name,
            "file_type": file_type,
            "file_size": file_size,
            "prooforigin_score": prooforigin_score,
            "sightengine_score": sightengine_score,
            "openai_vision_score": openai_vision_score,
            "weighted_consensus": weighted_consensus,
            "prooforigin_report": report,
            "evidence_file": evidence_file,
            "training_file": training_file,
            "disagreement_detected": disagreement_record is not None,
            "external_engines": engines,
            "user_feedback": user_feedback,
            "training_status": "pending_review",
        }

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        print(f"[ProofOrigin] Evidence file created: {evidence_file}")
        print(f"[ProofOrigin] Training file created: {training_file}")

        if disagreement_record:
            print(f"[ProofOrigin] Disagreement case logged: {file_id}")

        return entry
