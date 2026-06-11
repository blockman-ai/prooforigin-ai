#!/usr/bin/env python3
"""Process Supabase dataset_training_jobs queue (import, audit, train candidate — no auto-promote)."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.training_jobs import (
    fetch_requested_jobs,
    load_jobs_config,
    map_pipeline_status_to_job_status,
    mark_job_finished,
    mark_job_running,
)
from scripts.safe_auto_train import run_safe_auto_train


def process_training_jobs(*, dry_run=False, epochs=8, force_train=False, limit=None):
    config = load_jobs_config()
    summary = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "configured": config.get("configured"),
        "jobs_processed": 0,
        "results": [],
    }

    if not config.get("configured"):
        summary["status"] = "blocked"
        summary["error"] = config.get("missing_env")
        return summary

    jobs, error = fetch_requested_jobs(config)
    if error:
        summary["status"] = "failed"
        summary["error"] = error
        return summary

    if limit is not None:
        jobs = jobs[:limit]

    for job in jobs:
        job_id = job.get("id")
        if not job_id:
            continue

        _, run_error = mark_job_running(config, job_id)
        if run_error:
            summary["results"].append({"job_id": job_id, "error": run_error})
            continue

        pipeline = run_safe_auto_train(
            dry_run=dry_run,
            epochs=epochs,
            force_train=force_train,
            quiet_import=True,
        )
        job_status = map_pipeline_status_to_job_status(pipeline.get("status"))
        _, finish_error = mark_job_finished(
            config,
            job_id,
            status=job_status,
            result_report_path=pipeline.get("result_report_path"),
            candidate_model_path=pipeline.get("candidate_model_path"),
            error=pipeline.get("error"),
        )

        summary["jobs_processed"] += 1
        summary["results"].append(
            {
                "job_id": job_id,
                "requested_by": job.get("requested_by"),
                "pipeline_status": pipeline.get("status"),
                "job_status": job_status,
                "result_report_path": pipeline.get("result_report_path"),
                "candidate_model_path": pipeline.get("candidate_model_path"),
                "error": pipeline.get("error") or finish_error,
            }
        )

    summary["finished_at"] = datetime.now(timezone.utc).isoformat()
    summary["status"] = "complete"
    return summary


def main():
    parser = argparse.ArgumentParser(description="Run Supabase dataset training jobs")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--force-train", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    result = process_training_jobs(
        dry_run=args.dry_run,
        epochs=args.epochs,
        force_train=args.force_train,
        limit=args.limit,
    )
    print(json.dumps(result, indent=2, default=str))
    if result.get("status") in {"blocked", "failed"}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
