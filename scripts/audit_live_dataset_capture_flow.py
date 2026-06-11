#!/usr/bin/env python3
"""End-to-end audit of live dataset capture upload, duplicate skip, and approve flow."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CAPTURE_TABLE = "private_dataset_captures"
DEFAULT_BUCKET = "real_pet_photos"
DEFAULT_BASE_URL = "http://localhost:3000"


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _require_env(*names: str) -> dict[str, str]:
    missing = [name for name in names if not os.getenv(name, "").strip()]
    if missing:
        raise SystemExit(
            "Missing required environment variables: "
            + ", ".join(missing)
            + "\nSet them in the shell or pass --dotenv path/to/.env.local"
        )
    return {name: os.getenv(name, "").strip() for name in names}


def _minimal_png(seed: bytes) -> bytes:
    width = height = 32
    pixel = bytes([seed[i % len(seed)] for i in range(3)])
    raw = b"".join(b"\x00" + pixel * width for _ in range(height))
    compressed = zlib.compress(raw, 9)

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", compressed)
        + chunk(b"IEND", b"")
    )


def _admin_token(supabase_url: str, anon_key: str, email: str, password: str) -> str:
    res = requests.post(
        f"{supabase_url.rstrip('/')}/auth/v1/token?grant_type=password",
        headers={"apikey": anon_key, "Content-Type": "application/json"},
        json={"email": email, "password": password},
        timeout=60,
    )
    if res.status_code >= 400:
        raise SystemExit(f"Admin login failed ({res.status_code}): {res.text[:500]}")
    token = res.json().get("access_token")
    if not token:
        raise SystemExit("Admin login succeeded but no access_token returned.")
    return token


def _upload(base_url: str, token: str, image_bytes: bytes, filename: str) -> dict:
    res = requests.post(
        f"{base_url.rstrip('/')}/api/dataset-capture/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (filename, image_bytes, "image/png")},
        data={
            "selected_bucket": DEFAULT_BUCKET,
            "consent": "true",
            "notes": "phase4h live capture audit",
        },
        timeout=120,
    )
    try:
        body = res.json()
    except Exception:
        body = {"raw": res.text[:500]}
    return {"status": res.status_code, "body": body}


def _approve(base_url: str, token: str, capture_id: str) -> dict:
    res = requests.post(
        f"{base_url.rstrip('/')}/api/dataset-capture/review",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "id": capture_id,
            "action": "approve",
            "correction_bucket": DEFAULT_BUCKET,
            "reviewer_notes": "phase4h live capture audit approve",
        },
        timeout=60,
    )
    try:
        body = res.json()
    except Exception:
        body = {"raw": res.text[:500]}
    return {"status": res.status_code, "body": body}


def _fetch_row(supabase_url: str, service_key: str, capture_id: str) -> dict | None:
    res = requests.get(
        f"{supabase_url.rstrip('/')}/rest/v1/{CAPTURE_TABLE}",
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
        },
        params={
            "id": f"eq.{capture_id}",
            "select": "id,sha256,approved_for_training,ready_for_import,rejected,review_status,is_duplicate,duplicate_of_id,created_at,reviewed_at",
        },
        timeout=60,
    )
    if res.status_code >= 400:
        raise SystemExit(f"Capture lookup failed ({res.status_code}): {res.text[:500]}")
    rows = res.json()
    return rows[0] if rows else None


def _model_snapshot() -> dict:
    prod = ROOT / "ml" / "models" / "prooforigin_cv_classifier.pt"
    cand = ROOT / "ml" / "models" / "prooforigin_cv_classifier_candidate.pt"
    candidates_dir = ROOT / "ml" / "models" / "candidates"
    snap = {}
    for label, path in [("production", prod), ("candidate", cand)]:
        if path.is_file():
            stat = path.stat()
            snap[label] = {
                "path": str(path),
                "mtime_iso": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "size_bytes": stat.st_size,
            }
        else:
            snap[label] = {"path": str(path), "exists": False}
    snap["candidate_runs"] = len(list(candidates_dir.glob("*"))) if candidates_dir.is_dir() else 0
    return snap


def run_audit(*, base_url: str, dotenv: Path | None) -> dict:
    if dotenv:
        _load_dotenv(dotenv)

    env = _require_env(
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY",
        "NEXT_PUBLIC_SUPABASE_URL",
        "NEXT_PUBLIC_SUPABASE_ANON_KEY",
        "DATASET_CAPTURE_ADMIN_EMAIL",
        "DATASET_CAPTURE_ADMIN_PASSWORD",
    )

    supabase_url = env["NEXT_PUBLIC_SUPABASE_URL"]
    if "YOUR_" in supabase_url:
        raise SystemExit("NEXT_PUBLIC_SUPABASE_URL is still a placeholder.")

    report: dict = {
        "started_at": datetime.now(tz=timezone.utc).isoformat(),
        "base_url": base_url,
        "steps": {},
        "errors": [],
        "model_before": _model_snapshot(),
    }

    token = _admin_token(
        supabase_url,
        env["NEXT_PUBLIC_SUPABASE_ANON_KEY"],
        env["DATASET_CAPTURE_ADMIN_EMAIL"],
        env["DATASET_CAPTURE_ADMIN_PASSWORD"],
    )
    report["steps"]["admin_login"] = {"ok": True}

    seed = os.urandom(16)
    image_bytes = _minimal_png(seed)
    sha256 = hashlib.sha256(image_bytes).hexdigest()
    filename = f"audit-{int(time.time())}.png"

    first = _upload(base_url, token, image_bytes, filename)
    report["steps"]["upload_new"] = first
    body1 = first["body"]
    if first["status"] != 200 or not body1.get("success") or body1.get("duplicate"):
        report["errors"].append("First upload did not succeed as a new capture.")
        return report

    capture_id = body1.get("id")
    report["capture_id"] = capture_id
    report["sha256"] = sha256

    second = _upload(base_url, token, image_bytes, filename)
    report["steps"]["upload_duplicate"] = second
    body2 = second["body"]
    duplicate_ok = (
        second["status"] == 200
        and body2.get("success")
        and body2.get("duplicate") is True
        and body2.get("existing", {}).get("id") == capture_id
    )
    report["steps"]["duplicate_skipped"] = {"ok": duplicate_ok}
    if not duplicate_ok:
        report["errors"].append("Duplicate upload was not skipped as expected.")

    approve = _approve(base_url, token, capture_id)
    report["steps"]["approve"] = approve
    approve_body = approve["body"]
    approve_ok = (
        approve["status"] == 200
        and approve_body.get("success")
        and approve_body.get("trains_immediately") is False
    )
    report["steps"]["approve_api"] = {"ok": approve_ok}
    if not approve_ok:
        report["errors"].append("Approve API did not return success with trains_immediately=false.")

    row = _fetch_row(env["SUPABASE_URL"], env["SUPABASE_SERVICE_ROLE_KEY"], capture_id)
    report["steps"]["db_row"] = row
    flags_ok = bool(
        row
        and row.get("approved_for_training") is True
        and row.get("ready_for_import") is True
    )
    report["steps"]["approval_flags"] = {"ok": flags_ok}
    if not flags_ok:
        report["errors"].append(
            "DB row missing approved_for_training=true and/or ready_for_import=true."
        )

    time.sleep(1)
    report["model_after"] = _model_snapshot()
    unchanged = report["model_before"] == report["model_after"]
    report["steps"]["no_training_started"] = {"ok": unchanged}
    if not unchanged:
        report["errors"].append("Local model files changed during audit (unexpected training).")

    report["passed"] = not report["errors"]
    report["finished_at"] = datetime.now(tz=timezone.utc).isoformat()
    return report


def main():
    parser = argparse.ArgumentParser(description="Audit live dataset capture flow")
    parser.add_argument(
        "--base-url",
        default=os.getenv("DATASET_CAPTURE_BASE_URL", DEFAULT_BASE_URL),
        help="Website base URL (default: http://localhost:3000)",
    )
    parser.add_argument(
        "--dotenv",
        type=Path,
        default=None,
        help="Optional .env.local path (e.g. ../prooforigin/.env.local)",
    )
    args = parser.parse_args()

    default_dotenv = ROOT.parent / "prooforigin" / ".env.local"
    dotenv = args.dotenv or (default_dotenv if default_dotenv.is_file() else None)

    report = run_audit(base_url=args.base_url, dotenv=dotenv)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report.get("passed") else 1)


if __name__ == "__main__":
    main()
