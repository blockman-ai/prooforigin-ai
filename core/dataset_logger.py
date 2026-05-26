import json
import os
from datetime import datetime


class DatasetLogger:

    def __init__(self, log_path="data/realtime_analysis_log.jsonl"):
        self.log_path = log_path
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def log_analysis(self, file_id, report, external_engines=None, user_feedback=None):
        entry = {
            "file_id": file_id,
            "timestamp": datetime.utcnow().isoformat(),
            "prooforigin_report": report,
            "external_engines": external_engines or {},
            "user_feedback": user_feedback,
            "training_status": "pending_review",
        }

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        return entry
