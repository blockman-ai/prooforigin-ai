import json
import os
from datetime import datetime


class DatasetLogger:
    def __init__(
        self,
        log_path="data/realtime_analysis_log.jsonl",
        evidence_path="data/evidence",
    ):
        self.log_path = log_path
        self.evidence_path = evidence_path

        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        os.makedirs(self.evidence_path, exist_ok=True)

    def log_analysis(self, file_id, report, external_engines=None, user_feedback=None):
        timestamp = datetime.utcnow().isoformat()

        evidence_record = {
            "report_id": file_id,
            "created_at": timestamp,
            "prooforigin": {
                "score": report.get("summary", {}).get("ai_score"),
                "classification": report.get("summary", {}).get("label"),
            },
            "consensus": {
                "score": report.get("consensus_analysis", {}).get("consensus_score"),
                "label": report.get("consensus_analysis", {}).get("consensus_label"),
            },
            "signals": report.get("signals", []),
            "metadata": report.get("metadata_analysis", {}),
            "provenance": report.get("provenance_analysis", {}),
            "adversarial": report.get("adversarial_analysis", {}),
            "trace": report.get("trace_analysis", {}),
            "engine_outputs": external_engines or {},
            "feedback": user_feedback or {
                "human_votes": 0,
                "ai_votes": 0,
                "edited_votes": 0,
                "disputed_votes": 0,
            },
            "training_status": "pending_review",
        }

        evidence_file = os.path.join(self.evidence_path, f"{file_id}.json")

        with open(evidence_file, "w", encoding="utf-8") as f:
            json.dump(evidence_record, f, indent=2)

        entry = {
            "file_id": file_id,
            "timestamp": timestamp,
            "prooforigin_report": report,
            "evidence_file": evidence_file,
            "external_engines": external_engines or {},
            "user_feedback": user_feedback,
            "training_status": "pending_review",
        }

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        print(f"[ProofOrigin] Evidence file created: {evidence_file}")

        return entry
