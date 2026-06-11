#!/usr/bin/env python3
"""Safe auto-train coordinator: import, audit, train candidate, evaluate, report (no auto-promote)."""

import argparse
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.dataset_utils import MODELS_DIR, MODEL_PATH
from ml.safe_train_eval import (
    GATES,
    check_promotion_gates,
    evaluate_model_bundle,
    load_production_baseline,
)
from ml.training_samples import collect_merged_training_samples
from scripts.audit_correction_set import audit_correction_set
from scripts.import_private_dataset_captures import import_private_captures

REPORTS_DIR = ROOT / "ml" / "reports"
GATE_STATUS_REPORT = REPORTS_DIR / "safe_training_gate_status.md"


def _timestamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _write_markdown(path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _correction_progress_payload(correction_audit):
    return {
        bucket: {
            "count": data["count"],
            "target": data["target"],
            "remaining_to_target": data["remaining_to_target"],
            "meets_target": data["meets_target"],
        }
        for bucket, data in correction_audit["buckets"].items()
    }


def write_gate_status_report(payload):
    lines = [
        "# Safe Training Gate Status",
        "",
        f"Generated: {payload['generated_at']}",
        "",
        f"**Pipeline status:** `{payload.get('status', 'unknown')}`",
        f"**Training gate:** {'OPEN' if payload.get('training_gate_open') else 'CLOSED'}",
        "",
        "## Capture import",
        "",
        f"- Import status: {payload.get('import_summary', {}).get('status', 'n/a')}",
        f"- Imported: {payload.get('import_summary', {}).get('imported', 0)}",
        f"- Duplicates skipped: {payload.get('import_summary', {}).get('duplicates_skipped', 0)}",
        "",
        "## Correction progress",
        "",
    ]
    for bucket, data in (payload.get("correction_progress") or {}).items():
        remaining = data.get("remaining_to_target", 0)
        lines.append(
            f"- `{bucket}`: {data.get('count')}/{data.get('target')} "
            f"({'met' if data.get('meets_target') else 'remaining ' + str(remaining)})"
        )
    lines.extend(
        [
            "",
            "## Candidate model",
            "",
            f"- Status: {payload.get('candidate_status', 'not trained')}",
            f"- Path: `{payload.get('candidate_model_path', 'n/a')}`",
            f"- Outcome: {payload.get('promotion_recommendation', 'n/a')}",
            "",
            f"Production model (`{MODEL_PATH.name}`) is never replaced automatically.",
            "",
        ]
    )
    if payload.get("gate_result"):
        lines.extend(["## Promotion gate result", ""])
        for issue in payload["gate_result"].get("issues") or []:
            lines.append(f"- FAIL: {issue}")
        for ok in payload["gate_result"].get("passes") or []:
            lines.append(f"- PASS: {ok}")
        lines.append("")
    if payload.get("report_paths"):
        lines.extend(["## Reports", ""])
        for path in payload["report_paths"]:
            lines.append(f"- `{path}`")
        lines.append("")
    _write_markdown(GATE_STATUS_REPORT, lines)


def write_gate_closed_report(stamp, payload):
    path = REPORTS_DIR / f"safe_training_gate_closed_{stamp}.md"
    reason = (payload.get("correction_audit") or {}).get("retraining", {}).get(
        "reason", "correction targets not met"
    )
    _write_markdown(
        path,
        [
            "# Safe Training Gate Closed",
            "",
            f"Generated: {payload['generated_at']}",
            "",
            "No candidate training was performed.",
            "",
            f"**Reason:** {reason}",
            "",
            "## Correction progress",
            "",
            *[
                f"- `{bucket}`: {data['count']}/{data['target']}"
                for bucket, data in (payload.get("correction_progress") or {}).items()
            ],
            "",
            "Approve more captures and re-run when all correction targets are met.",
        ],
    )
    return path


def write_candidate_eval_reports(stamp, candidate_eval, production_metrics, gate_result):
    json_path = REPORTS_DIR / f"candidate_eval_{stamp}.json"
    md_path = REPORTS_DIR / f"candidate_eval_{stamp}.md"
    bundle = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "candidate_metrics": candidate_eval,
        "production_baseline": production_metrics,
        "promotion_gates": GATES,
        "gate_result": gate_result,
    }
    _write_json(json_path, bundle)

    lines = [
        "# Candidate Evaluation",
        "",
        f"Generated: {bundle['generated_at']}",
        "",
        f"**Candidate:** `{candidate_eval.get('model_path')}`",
        "",
        "## Bootstrap validation",
        "",
        f"- Candidate accuracy: {candidate_eval.get('bootstrap_accuracy')}",
        f"- Production accuracy: {production_metrics.get('bootstrap_accuracy')}",
        f"- Candidate ECE: {candidate_eval.get('ece')}",
        f"- Production ECE: {production_metrics.get('ece')}",
        "",
        "## Edge-case regression (real_phone)",
        "",
    ]
    edge = candidate_eval.get("edge_case_regression") or {}
    prod_edge = production_metrics.get("edge_case_regression") or {}
    lines.append(f"- Candidate FPR: {edge.get('fpr')} ({edge.get('false_positives')}/{edge.get('count')})")
    lines.append(f"- Production FPR: {prod_edge.get('fpr')}")

    lines.extend(["", "## Correction buckets", ""])
    for bucket, data in (candidate_eval.get("correction_buckets") or {}).items():
        prod = (production_metrics.get("correction_buckets") or {}).get(bucket) or {}
        lines.append(
            f"- `{bucket}`: candidate FPR/FNR={data.get('fpr') or data.get('fnr')} "
            f"(prod {prod.get('fpr') or prod.get('fnr')}, n={data.get('count')})"
        )

    lines.extend(["", "## Promotion gates", ""])
    for ok in gate_result.get("passes") or []:
        lines.append(f"- PASS: {ok}")
    for issue in gate_result.get("issues") or []:
        lines.append(f"- FAIL: {issue}")
    lines.append("")
    _write_markdown(md_path, lines)
    return md_path, json_path


def write_outcome_report(stamp, payload, *, passed):
    if passed:
        path = REPORTS_DIR / f"candidate_passed_{stamp}.md"
        title = "Candidate Passed Promotion Gates"
        footer = (
            "Production model was **not** replaced. "
            "Manual promotion is required after reviewing candidate reports."
        )
    else:
        path = REPORTS_DIR / f"candidate_failed_{stamp}.md"
        title = "Candidate Failed Promotion Gates"
        footer = "Production model unchanged. Do not promote this candidate."

    lines = [
        f"# {title}",
        "",
        f"Generated: {payload['generated_at']}",
        "",
        f"Candidate: `{payload.get('candidate_model_path')}`",
        "",
        footer,
        "",
    ]
    gate = payload.get("gate_result") or {}
    if gate.get("passes"):
        lines.extend(["## Passes", ""])
        lines.extend(f"- {line}" for line in gate["passes"])
        lines.append("")
    if gate.get("issues"):
        lines.extend(["## Failures", ""])
        lines.extend(f"- {line}" for line in gate["issues"])
        lines.append("")
    _write_markdown(path, lines)
    return path


def _train_candidate(output_dir, *, epochs=8):
    from datetime import datetime as dt, timezone as tz

    from ml.train_classifier import ProofOriginImageDataset, _compute_metrics, _require_torch, _split_samples

    merged = collect_merged_training_samples(include_correction=True)
    samples = merged["samples"]
    if merged["real_total"] < 2 or merged["ai_total"] < 2:
        raise RuntimeError("Insufficient merged training samples.")

    torch, nn, DataLoader, _, models, transforms = _require_torch()
    train_samples, val_samples = _split_samples(samples, val_ratio=0.2)

    train_transform = transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )
    eval_transform = transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )

    train_loader = DataLoader(
        ProofOriginImageDataset(train_samples, train_transform),
        batch_size=16,
        shuffle=True,
    )
    val_loader = DataLoader(
        ProofOriginImageDataset(val_samples, eval_transform),
        batch_size=16,
        shuffle=False,
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
    model.classifier[3] = nn.Linear(model.classifier[3].in_features, 2)
    model = model.to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)

    for _epoch in range(epochs):
        model.train()
        for inputs, labels in train_loader:
            inputs = inputs.to(device)
            labels = labels.to(device)
            optimizer.zero_grad()
            loss = criterion(model(inputs), labels)
            loss.backward()
            optimizer.step()

    model.eval()
    y_true = []
    y_pred = []
    with torch.no_grad():
        for inputs, labels in val_loader:
            inputs = inputs.to(device)
            preds = model(inputs).argmax(dim=1).cpu().tolist()
            y_pred.extend(preds)
            y_true.extend(labels.tolist())

    metrics = _compute_metrics(y_true, y_pred)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "prooforigin_cv_classifier.pt"
    metrics_path = output_dir / "metrics.json"

    checkpoint = {
        "model_state_dict": model.cpu().state_dict(),
        "class_names": ["real", "ai_generated"],
        "num_classes": 2,
        "image_size": 224,
        "trained_at": dt.now(tz.utc).isoformat(),
        "dataset_counts": {
            "real": merged["real_total"],
            "ai_generated": merged["ai_total"],
        },
    }
    torch.save(checkpoint, model_path)
    metrics_path.write_text(
        json.dumps(
            {
                "model_path": str(model_path),
                "trained_at": checkpoint["trained_at"],
                "validation_metrics": metrics,
                "correction_counts": merged["correction_counts"],
                "model_version": "cv_v0.2_candidate",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return model_path, metrics


def run_safe_auto_train(*, dry_run=False, epochs=8, force_train=False, quiet_import=False):
    """Run full import → audit → train → evaluate → report pipeline."""
    generated_at = datetime.now(timezone.utc).isoformat()
    stamp = _timestamp()
    report_paths = []

    payload = {
        "generated_at": generated_at,
        "status": "failed",
        "import_summary": {},
        "training_gate_open": False,
        "correction_progress": {},
        "correction_audit": {},
        "candidate_status": "not_started",
        "candidate_model_path": None,
        "promotion_recommendation": "none",
        "gate_result": None,
        "report_paths": report_paths,
        "result_report_path": None,
        "error": None,
    }

    try:
        import_summary = import_private_captures(dry_run=dry_run, quiet=quiet_import)
        payload["import_summary"] = import_summary

        import_blocked = import_summary.get("status") == "blocked"
        missing_supabase_only = import_blocked and import_summary.get("missing_env")

        if import_blocked and not (dry_run and missing_supabase_only):
            payload["status"] = "failed"
            payload["error"] = import_summary.get("reason", "import blocked")
            payload["candidate_status"] = "import_blocked"
            write_gate_status_report(payload)
            report_paths.append(str(GATE_STATUS_REPORT))
            payload["result_report_path"] = str(GATE_STATUS_REPORT)
            return payload

        if missing_supabase_only:
            payload["import_summary"] = {
                **import_summary,
                "note": "Supabase not configured; local audit and dry-run continue without remote import.",
            }

        correction_audit = audit_correction_set()
        payload["correction_audit"] = correction_audit
        payload["correction_progress"] = _correction_progress_payload(correction_audit)
        training_gate_open = correction_audit["retraining"]["allowed"]
        payload["training_gate_open"] = training_gate_open

        if not training_gate_open and not force_train:
            payload["promotion_recommendation"] = "training gate closed"
            if dry_run:
                payload["status"] = "dry_run"
                payload["candidate_status"] = "dry_run_gate_closed"
                write_gate_status_report(payload)
                report_paths.append(str(GATE_STATUS_REPORT))
                payload["result_report_path"] = str(GATE_STATUS_REPORT)
                return payload

            payload["status"] = "gate_closed"
            payload["candidate_status"] = "blocked"
            closed_path = write_gate_closed_report(stamp, payload)
            report_paths.extend([str(GATE_STATUS_REPORT), str(closed_path)])
            write_gate_status_report({**payload, "report_paths": report_paths})
            payload["result_report_path"] = str(closed_path)
            return payload

        if dry_run:
            payload["status"] = "dry_run"
            payload["candidate_status"] = "dry_run"
            payload["promotion_recommendation"] = "dry_run_only"
            write_gate_status_report(payload)
            report_paths.append(str(GATE_STATUS_REPORT))
            payload["result_report_path"] = str(GATE_STATUS_REPORT)
            return payload

        candidate_dir = MODELS_DIR / "candidates" / stamp
        candidate_path, _train_metrics = _train_candidate(candidate_dir, epochs=epochs)
        payload["candidate_status"] = "trained"
        payload["candidate_model_path"] = str(candidate_path)

        production = load_production_baseline()
        candidate_eval = evaluate_model_bundle(candidate_path)
        gate_result = check_promotion_gates(candidate_eval, production)
        payload["candidate_metrics"] = candidate_eval
        payload["production_metrics"] = production
        payload["gate_result"] = gate_result

        eval_md, eval_json = write_candidate_eval_reports(
            stamp, candidate_eval, production, gate_result
        )
        report_paths.extend([str(eval_md), str(eval_json)])

        if gate_result["passed"]:
            payload["status"] = "promotion_ready"
            payload["promotion_recommendation"] = "manual_promotion_required"
            outcome_path = write_outcome_report(stamp, payload, passed=True)
        else:
            payload["status"] = "rejected_candidate"
            payload["promotion_recommendation"] = "do_not_promote"
            outcome_path = write_outcome_report(stamp, payload, passed=False)

        report_paths.append(str(outcome_path))
        payload["result_report_path"] = str(outcome_path)
        write_gate_status_report({**payload, "report_paths": report_paths})
        report_paths.append(str(GATE_STATUS_REPORT))
        payload["report_paths"] = report_paths
        return payload

    except Exception as exc:
        payload["status"] = "failed"
        payload["error"] = str(exc)
        payload["candidate_status"] = "error"
        payload["traceback"] = traceback.format_exc()
        write_gate_status_report(payload)
        report_paths.append(str(GATE_STATUS_REPORT))
        payload["result_report_path"] = str(GATE_STATUS_REPORT)
        payload["report_paths"] = report_paths
        return payload


def main():
    parser = argparse.ArgumentParser(description="Safe auto-train coordinator")
    parser.add_argument("--dry-run", action="store_true", help="Import + audit only; no training")
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument(
        "--force-train",
        action="store_true",
        help="Train candidate even if correction targets are not fully met",
    )
    args = parser.parse_args()
    result = run_safe_auto_train(
        dry_run=args.dry_run,
        epochs=args.epochs,
        force_train=args.force_train,
        quiet_import=True,
    )
    print(json.dumps(result, indent=2, default=str))
    if result.get("status") == "failed":
        raise SystemExit(1)
    if result.get("status") == "gate_closed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
