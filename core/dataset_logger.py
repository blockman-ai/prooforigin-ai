import json
import os
from datetime import datetime

from core.evidence_schema import build_evidence_record
from core.engine_sanitize import sanitize_external_engines
from core.bundle_store import BundleAlreadyExistsError, write_bundle_once


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
        timestamp=None,
    ):
        timestamp = timestamp or datetime.utcnow().isoformat()
        engines = sanitize_external_engines(external_engines or {})

        prooforigin_score = report.get("summary", {}).get("ai_score")
        sightengine_score = engines.get("sightengine", {}).get("score")
        openai_vision_score = engines.get("openai_vision", {}).get("score")
        weighted_consensus = report.get("weighted_consensus", {})

        evidence_record = build_evidence_record(
            file_id=file_id,
            timestamp=timestamp,
            report=report,
            external_engines=engines,
            user_feedback=user_feedback,
            file_hash=file_hash,
            file_name=file_name,
            file_type=file_type,
            file_size=file_size,
            policy=report.get("policy"),
        )

        integrity = evidence_record["integrity"]
        training_data = evidence_record["training_data"]

        try:
            evidence_file = write_bundle_once(
                self.evidence_path,
                file_id,
                evidence_record,
            )
        except BundleAlreadyExistsError as exc:
            raise ValueError(str(exc)) from exc

        training_file = os.path.join(self.training_path, f"{file_id}.json")

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
            "evidence_bundle_hash": evidence_record.get("evidence_bundle_hash"),
            "policy_hash": evidence_record.get("policy_hash"),
            "engine_snapshot_hash": evidence_record.get("engine_snapshot_hash"),
            "decision_tier": evidence_record.get("decision_tier"),
            "constitution_version": evidence_record.get("constitution_version"),
            "policy_version": evidence_record.get("policy_version"),
            "report_version": evidence_record.get("report_version"),
            "published_at": evidence_record.get("published_at"),
        }

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        print(f"[ProofOrigin] Evidence bundle sealed: {evidence_file}")
        print(f"[ProofOrigin] Training file created: {training_file}")

        if disagreement_record:
            print(f"[ProofOrigin] Disagreement case logged: {file_id}")

        return entry
