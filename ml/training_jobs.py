"""Supabase dataset_training_jobs queue helpers (backend only)."""

import os
from datetime import datetime, timezone

import requests

JOBS_TABLE = "dataset_training_jobs"
ENV_SUPABASE_URL = "SUPABASE_URL"
ENV_SERVICE_ROLE_KEY = "SUPABASE_SERVICE_ROLE_KEY"

JOB_STATUS_REQUESTED = "requested"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_BLOCKED_GATE_CLOSED = "blocked_gate_closed"
JOB_STATUS_FAILED = "failed"
JOB_STATUS_PASSED_CANDIDATE = "passed_candidate"
JOB_STATUS_REJECTED_CANDIDATE = "rejected_candidate"
JOB_STATUS_PROMOTION_READY = "promotion_ready"

TERMINAL_JOB_STATUSES = frozenset(
    {
        JOB_STATUS_BLOCKED_GATE_CLOSED,
        JOB_STATUS_FAILED,
        JOB_STATUS_PASSED_CANDIDATE,
        JOB_STATUS_REJECTED_CANDIDATE,
        JOB_STATUS_PROMOTION_READY,
    }
)


def load_jobs_config():
    url = os.getenv(ENV_SUPABASE_URL, "").strip().rstrip("/")
    service_role_key = os.getenv(ENV_SERVICE_ROLE_KEY, "").strip()
    missing = []
    if not url:
        missing.append(ENV_SUPABASE_URL)
    if not service_role_key:
        missing.append(ENV_SERVICE_ROLE_KEY)
    if missing:
        return {"configured": False, "missing_env": missing}
    return {
        "configured": True,
        "missing_env": [],
        "url": url,
        "service_role_key": service_role_key,
    }


def _rest_headers(config):
    key = config["service_role_key"]
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def fetch_requested_jobs(config):
    if not config.get("configured"):
        return [], {"error": "supabase_not_configured", "missing_env": config.get("missing_env")}

    url = f"{config['url']}/rest/v1/{JOBS_TABLE}"
    response = requests.get(
        url,
        headers=_rest_headers(config),
        params={
            "select": "*",
            "status": f"eq.{JOB_STATUS_REQUESTED}",
            "order": "requested_at.asc",
        },
        timeout=60,
    )
    if response.status_code >= 400:
        return [], {
            "error": "supabase_query_failed",
            "status_code": response.status_code,
            "message": response.text[:500],
        }
    rows = response.json()
    if not isinstance(rows, list):
        return [], {"error": "unexpected_response", "message": "Expected list from Supabase REST"}
    return rows, None


def update_job(config, job_id, patch):
    url = f"{config['url']}/rest/v1/{JOBS_TABLE}"
    response = requests.patch(
        url,
        headers=_rest_headers(config),
        params={"id": f"eq.{job_id}"},
        json=patch,
        timeout=60,
    )
    if response.status_code >= 400:
        return None, {
            "error": "supabase_update_failed",
            "status_code": response.status_code,
            "message": response.text[:500],
        }
    rows = response.json()
    if isinstance(rows, list) and rows:
        return rows[0], None
    return {"id": job_id, **patch}, None


def mark_job_running(config, job_id):
    now = datetime.now(timezone.utc).isoformat()
    return update_job(
        config,
        job_id,
        {"status": JOB_STATUS_RUNNING, "started_at": now, "error": None},
    )


def mark_job_finished(config, job_id, *, status, result_report_path=None, candidate_model_path=None, error=None):
    now = datetime.now(timezone.utc).isoformat()
    patch = {
        "status": status,
        "finished_at": now,
        "result_report_path": result_report_path,
        "candidate_model_path": candidate_model_path,
        "error": error,
    }
    return update_job(config, job_id, patch)


def map_pipeline_status_to_job_status(pipeline_status):
    mapping = {
        "gate_closed": JOB_STATUS_BLOCKED_GATE_CLOSED,
        "failed": JOB_STATUS_FAILED,
        "promotion_ready": JOB_STATUS_PROMOTION_READY,
        "rejected_candidate": JOB_STATUS_REJECTED_CANDIDATE,
        "passed_candidate": JOB_STATUS_PASSED_CANDIDATE,
        "dry_run": JOB_STATUS_PASSED_CANDIDATE,
    }
    return mapping.get(pipeline_status, JOB_STATUS_FAILED)
