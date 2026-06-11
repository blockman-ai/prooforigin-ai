#!/usr/bin/env python3
"""Safe auto-train coordinator: import, gate-check, train candidate, evaluate, promote cautiously."""

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.dataset_utils import MODELS_DIR
from ml.safe_train_eval import (
    CANDIDATE_MODEL_PATH,
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


def _train_candidate(output_dir, *, epochs=8):
    from datetime import datetime as dt, timezone as tz

    from ml.train_classifier import ProofOriginImageDataset, _compute_metrics, _require_torch, _split_samples

    merged = collect_merged_training_samples(include_correction=True)
    samples = merged["samples"]
    if merged["real_total"] < 2 or merged["ai_total"] < 2:
        raise SystemExit("Insufficient merged training samples.")

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


def write_gate_status_report(payload):
    lines = [
        "# Safe Training Gate Status",
        "",
        f"Generated: {payload['generated_at']}",
        "",
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
        lines.append(
            f"- `{bucket}`: {data.get('count')}/{data.get('target')} "
            f"({'met' if data.get('meets_target') else 'remaining ' + str(data.get('remaining_to_target'))})"
        )
    lines.extend(
        [
            "",
            "## Candidate model",
            "",
            f"- Status: {payload.get('candidate_status', 'not trained')}",
            f"- Promotion recommendation: {payload.get('promotion_recommendation', 'n/a')}",
            "",
        ]
    )
    if payload.get("gate_result"):
        lines.append("## Promotion gate result")
        lines.append("")
        for issue in payload["gate_result"].get("issues") or []:
            lines.append(f"- FAIL: {issue}")
        for ok in payload["gate_result"].get("passes") or []:
            lines.append(f"- PASS: {ok}")
        lines.append("")
    _write_markdown(GATE_STATUS_REPORT, lines)


def run_safe_auto_train(*, dry_run=False, epochs=8, force_train=False):
    generated_at = datetime.now(timezone.utc).isoformat()
    import_summary = import_private_captures(dry_run=dry_run)
    correction_audit = audit_correction_set()
    training_gate_open = correction_audit["retraining"]["allowed"]

    payload = {
        "generated_at": generated_at,
        "import_summary": import_summary,
        "training_gate_open": training_gate_open,
        "correction_progress": {
            bucket: {
                "count": data["count"],
                "target": data["target"],
                "remaining_to_target": data["remaining_to_target"],
                "meets_target": data["meets_target"],
            }
            for bucket, data in correction_audit["buckets"].items()
        },
        "candidate_status": "skipped",
        "promotion_recommendation": "none",
    }

    if not training_gate_open and not force_train:
        payload["candidate_status"] = "blocked"
        payload["promotion_recommendation"] = "training gate closed"
        write_gate_status_report(payload)
        print(json.dumps({"status": "gate_closed", **payload}, indent=2))
        return payload

    if dry_run:
        payload["candidate_status"] = "dry_run"
        write_gate_status_report(payload)
        print(json.dumps({"status": "dry_run", **payload}, indent=2))
        return payload

    stamp = _timestamp()
    candidate_dir = MODELS_DIR / "candidates" / stamp
    candidate_path, _metrics = _train_candidate(candidate_dir, epochs=epochs)
    production = load_production_baseline()
    candidate_eval = evaluate_model_bundle(candidate_path)
    gate_result = check_promotion_gates(candidate_eval, production)

    payload["candidate_status"] = "trained"
    payload["candidate_path"] = str(candidate_path)
    payload["candidate_metrics"] = candidate_eval
    payload["production_metrics"] = production
    payload["gate_result"] = gate_result

    if gate_result["passed"]:
        CANDIDATE_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(candidate_path, CANDIDATE_MODEL_PATH)
        report_path = REPORTS_DIR / f"safe_train_candidate_passed_{stamp}.md"
        payload["promotion_recommendation"] = "manual_confirmation_required"
        _write_markdown(
            report_path,
            [
                "# Safe Train Candidate PASSED",
                "",
                f"Generated: {generated_at}",
                "",
                f"Candidate: `{candidate_path}`",
                f"Copied to: `{CANDIDATE_MODEL_PATH}`",
                "",
                "Production model was **not** replaced automatically.",
                "",
                "## Gate passes",
                "",
                *[f"- {line}" for line in gate_result.get("passes") or []],
            ],
        )
        payload["report_path"] = str(report_path)
    else:
        report_path = REPORTS_DIR / f"safe_train_candidate_failed_{stamp}.md"
        payload["promotion_recommendation"] = "do_not_promote"
        _write_markdown(
            report_path,
            [
                "# Safe Train Candidate FAILED",
                "",
                f"Generated: {generated_at}",
                "",
                f"Candidate: `{candidate_path}`",
                "",
                "Production model unchanged.",
                "",
                "## Gate failures",
                "",
                *[f"- {line}" for line in gate_result.get("issues") or []],
            ],
        )
        payload["report_path"] = str(report_path)

    write_gate_status_report(payload)
    print(json.dumps({"status": "complete", **payload}, indent=2, default=str))
    return payload


def main():
    parser = argparse.ArgumentParser(description="Safe auto-train coordinator")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument(
        "--force-train",
        action="store_true",
        help="Train candidate even if correction targets are not fully met",
    )
    args = parser.parse_args()
    run_safe_auto_train(dry_run=args.dry_run, epochs=args.epochs, force_train=args.force_train)


if __name__ == "__main__":
    main()
