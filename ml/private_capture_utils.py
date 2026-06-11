"""Supabase private dataset capture helpers (local import only, no API exposure)."""

import os
from urllib.parse import quote

import requests

from ml.correction_utils import CORRECTION_BUCKETS

CAPTURES_TABLE = "private_dataset_captures"
ENV_SUPABASE_URL = "SUPABASE_URL"
ENV_SERVICE_ROLE_KEY = "SUPABASE_SERVICE_ROLE_KEY"
ENV_DATASET_BUCKET = "PRIVATE_DATASET_BUCKET"
DEFAULT_DATASET_BUCKET = "po-private-dataset"

VALID_CONSENT = frozenset({"granted", "owner_provided"})
BLOCKED_REVIEW_STATUSES = frozenset(
    {"duplicate", "reject", "rejected", "low_quality", "wrong_bucket"}
)


def capture_bucket(record):
    return record.get("correction_bucket") or record.get("selected_bucket")


def import_eligible(record):
    if not record.get("approved_for_training"):
        return False
    if record.get("rejected"):
        return False
    if record.get("keep_for_regression_only"):
        return False
    status = str(record.get("review_status") or "").strip().lower()
    if status in BLOCKED_REVIEW_STATUSES:
        return False
    if not capture_consent_ok(record):
        return False
    if not capture_bucket(record):
        return False
    return True


def load_capture_config():
    url = os.getenv(ENV_SUPABASE_URL, "").strip().rstrip("/")
    service_role_key = os.getenv(ENV_SERVICE_ROLE_KEY, "").strip()
    storage_bucket = os.getenv(ENV_DATASET_BUCKET, DEFAULT_DATASET_BUCKET).strip()

    missing = []
    if not url:
        missing.append(ENV_SUPABASE_URL)
    if not service_role_key:
        missing.append(ENV_SERVICE_ROLE_KEY)

    if missing:
        return {
            "configured": False,
            "missing_env": missing,
            "url": url or None,
            "service_role_key": None,
            "storage_bucket": storage_bucket,
        }

    return {
        "configured": True,
        "missing_env": [],
        "url": url,
        "service_role_key": service_role_key,
        "storage_bucket": storage_bucket,
    }


def _rest_headers(config):
    key = config["service_role_key"]
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def fetch_captures(config, *, approved_only=False):
    if not config.get("configured"):
        return [], {"error": "supabase_not_configured", "missing_env": config.get("missing_env")}

    url = f"{config['url']}/rest/v1/{CAPTURES_TABLE}"
    params = {"select": "*", "order": "created_at.asc"}
    if approved_only:
        params["approved_for_training"] = "eq.true"

    response = requests.get(
        url,
        headers=_rest_headers(config),
        params=params,
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


def download_capture_object(config, storage_path, destination):
    bucket = config["storage_bucket"]
    encoded_path = "/".join(quote(part, safe="") for part in storage_path.split("/"))
    url = f"{config['url']}/storage/v1/object/{bucket}/{encoded_path}"

    response = requests.get(
        url,
        headers={
            "apikey": config["service_role_key"],
            "Authorization": f"Bearer {config['service_role_key']}",
        },
        timeout=120,
    )
    if response.status_code >= 400:
        raise RuntimeError(
            f"Storage download failed ({response.status_code}): {response.text[:300]}"
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(response.content)
    return destination


def normalize_correction_bucket(value):
    bucket = str(value or "").strip()
    if bucket not in CORRECTION_BUCKETS:
        raise ValueError(
            f"Invalid correction_bucket '{bucket}'. "
            f"Expected one of: {', '.join(CORRECTION_BUCKETS)}"
        )
    return bucket


def capture_consent_ok(record):
    status = str(record.get("consent_status") or "").strip().lower()
    if status in VALID_CONSENT:
        return True
    if record.get("consent_granted") is True:
        return True
    return False


def capture_review_state(record):
    approved = bool(record.get("approved_for_training"))
    consent_ok = capture_consent_ok(record)
    if not consent_ok:
        return "missing_consent"
    if approved:
        return "approved"
    return "pending_review"


def audit_capture_records(records):
    sha_index = {}
    duplicate_hashes = []
    by_bucket = {bucket: 0 for bucket in CORRECTION_BUCKETS}
    by_state = {
        "approved": 0,
        "pending_review": 0,
        "missing_consent": 0,
        "rejected": 0,
        "duplicate": 0,
    }

    for record in records:
        status = str(record.get("review_status") or "").strip().lower()
        if record.get("rejected") or status in {"reject", "rejected", "low_quality"}:
            by_state["rejected"] += 1
        elif status == "duplicate" or record.get("is_duplicate"):
            by_state["duplicate"] += 1
        elif capture_review_state(record) == "approved":
            by_state["approved"] += 1
        elif capture_review_state(record) == "missing_consent":
            by_state["missing_consent"] += 1
        else:
            by_state["pending_review"] += 1

        bucket = capture_bucket(record)
        if bucket in CORRECTION_BUCKETS:
            by_bucket[bucket] += 1

        digest = record.get("sha256")
        if digest:
            if digest in sha_index:
                duplicate_hashes.append(
                    {
                        "sha256": digest,
                        "first_id": sha_index[digest],
                        "duplicate_id": record.get("id"),
                    }
                )
            else:
                sha_index[digest] = record.get("id")

    return {
        "total_captures": len(records),
        "approved_count": by_state["approved"],
        "pending_review_count": by_state["pending_review"],
        "missing_consent_count": by_state["missing_consent"],
        "rejected_count": by_state["rejected"],
        "duplicate_count": by_state["duplicate"],
        "duplicate_hashes": duplicate_hashes,
        "count_per_bucket": by_bucket,
    }
