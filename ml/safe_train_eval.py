"""Safe auto-train evaluation and promotion gate checks."""

import json
from pathlib import Path

from ml.calibrate_scores import _expected_calibration_error, _predicted_label, _safe_div
from ml.correction_utils import CORRECTION_BUCKETS, bucket_dir
from ml.dataset_utils import (
    METRICS_PATH,
    MODEL_PATH,
    collect_binary_training_samples,
    list_valid_images,
)
from ml.inference_classifier import _build_model

REPO_ROOT = Path(__file__).resolve().parents[1]
EDGE_CASES_DIR = REPO_ROOT / "ml" / "edge_cases" / "real_phone"
CANDIDATE_MODEL_PATH = REPO_ROOT / "ml" / "models" / "prooforigin_cv_classifier_candidate.pt"

FAILURE_BUCKETS = (
    "real_pet_photos",
    "phone_screen_photos",
    "indoor_soft_light",
)

GATES = {
    "real_phone_fpr_max": 0.05,
    "real_pet_photos_fpr_max": 0.05,
    "phone_screen_photos_fpr_max": 0.10,
    "ai_controls_fnr_max": 0.05,
    "ece_worsen_max": 0.02,
}

INCONCLUSIVE_LOW = 20.0
INCONCLUSIVE_HIGH = 80.0
DEFINITE_AI_THRESHOLD = 80.0


def _require_torch():
    import torch

    return torch


def load_model_bundle(model_path):
    torch = _require_torch()
    checkpoint = torch.load(model_path, map_location="cpu")
    model = _build_model(num_classes=checkpoint.get("num_classes", 2))
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    return {
        "model": model,
        "class_names": checkpoint.get("class_names", ["real", "ai_generated"]),
        "image_size": checkpoint.get("image_size", 224),
    }


def predict_ai_probability(model_path, image_path, *, threshold=50.0):
    from PIL import Image
    from torchvision import transforms

    torch = _require_torch()
    loaded = load_model_bundle(model_path)
    image_size = loaded["image_size"]
    transform = transforms.Compose(
        [
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )

    with Image.open(image_path) as image:
        tensor = transform(image.convert("RGB")).unsqueeze(0)

    with torch.no_grad():
        logits = loaded["model"](tensor)
        probs = torch.softmax(logits, dim=1).squeeze(0).tolist()

    class_names = loaded["class_names"]
    ai_idx = class_names.index("ai_generated") if "ai_generated" in class_names else 1
    ai_probability = round(float(probs[ai_idx]) * 100, 2)
    predicted = _predicted_label(ai_probability, threshold=threshold)
    return ai_probability, predicted


def _evaluate_folder(model_path, folder, *, expected="real", threshold=50.0):
    folder = Path(folder)
    if not folder.is_dir():
        return {
            "count": 0,
            "false_positives": 0,
            "false_negatives": 0,
            "fpr": None,
            "fnr": None,
            "records": [],
        }

    false_positives = 0
    false_negatives = 0
    count = 0
    records = []

    for path in list_valid_images(folder):
        if path.name.startswith("."):
            continue
        prob, pred = predict_ai_probability(model_path, path, threshold=threshold)
        count += 1
        records.append({"file_path": str(path), "ai_probability": prob, "predicted": pred})
        if expected == "real" and pred == "ai":
            false_positives += 1
        if expected == "ai" and pred == "real":
            false_negatives += 1

    return {
        "count": count,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "fpr": round(_safe_div(false_positives, count), 4) if expected == "real" and count else None,
        "fnr": round(_safe_div(false_negatives, count), 4) if expected == "ai" and count else None,
        "records": records,
    }


def evaluate_bootstrap_accuracy(model_path, *, val_ratio=0.2):
    from PIL import Image
    from torchvision import transforms

    from ml.train_classifier import _split_samples

    torch = _require_torch()
    samples, _, _, _ = collect_binary_training_samples(min_per_class=2, split="train")
    binary = [(path, label) for path, label, _bucket in samples]
    _, val_samples = _split_samples(binary, val_ratio=val_ratio)

    eval_transform = transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )

    model = load_model_bundle(model_path)["model"]
    y_true = []
    y_pred = []

    for path, label in val_samples:
        with Image.open(path) as image:
            tensor = eval_transform(image.convert("RGB")).unsqueeze(0)
        with torch.no_grad():
            pred = int(model(tensor).argmax(dim=1).item())
        y_true.append(label)
        y_pred.append(pred)

    return round(_safe_div(sum(1 for t, p in zip(y_true, y_pred) if t == p), len(y_true)), 4)


def evaluate_correction_buckets(model_path, *, threshold=50.0):
    results = {}
    for bucket in CORRECTION_BUCKETS:
        expected = "ai" if bucket == "ai_controls" else "real"
        results[bucket] = _evaluate_folder(
            model_path,
            bucket_dir(bucket),
            expected=expected,
            threshold=threshold,
        )
    return results


def evaluate_edge_case_regression(model_path, *, threshold=50.0):
    return _evaluate_folder(
        model_path,
        EDGE_CASES_DIR,
        expected="real",
        threshold=threshold,
    )


def _records_for_ece(folder_results):
    records = []
    for bucket, payload in folder_results.items():
        expected = "ai" if bucket == "ai_controls" else "real"
        for row in payload.get("records", []):
            records.append(
                {
                    "true_label": bucket,
                    "human_verified_label": "ai" if expected == "ai" else "real",
                    "prooforigin_ai_probability": row["ai_probability"],
                }
            )
    return records


def compute_ece(model_path, *, threshold=50.0):
    folder_results = evaluate_correction_buckets(model_path, threshold=threshold)
    records = _records_for_ece(folder_results)
    if not records:
        return None
    return (_expected_calibration_error(records) or {}).get("ece")


def evaluate_model_bundle(model_path, *, threshold=50.0):
    correction = evaluate_correction_buckets(model_path, threshold=threshold)
    edge = evaluate_edge_case_regression(model_path, threshold=threshold)
    accuracy = evaluate_bootstrap_accuracy(model_path)
    ece = compute_ece(model_path, threshold=threshold)
    return {
        "model_path": str(model_path),
        "bootstrap_accuracy": accuracy,
        "ece": ece,
        "edge_case_regression": edge,
        "correction_buckets": correction,
    }


def load_production_baseline():
    baseline = {"bootstrap_accuracy": None, "ece": None}
    if METRICS_PATH.exists():
        metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
        val = metrics.get("validation_metrics") or {}
        baseline["bootstrap_accuracy"] = val.get("accuracy")
        full = metrics.get("full_dataset_evaluation") or {}
        cal = full.get("calibration_evaluation") or {}
        baseline["ece"] = (cal.get("calibration_error") or {}).get("ece")

    if MODEL_PATH.exists():
        prod = evaluate_model_bundle(MODEL_PATH)
        baseline["bootstrap_accuracy"] = baseline["bootstrap_accuracy"] or prod["bootstrap_accuracy"]
        baseline["ece"] = prod["ece"] if baseline["ece"] is None else baseline["ece"]
        baseline["correction_buckets"] = prod["correction_buckets"]
        baseline["edge_case_regression"] = prod["edge_case_regression"]
    else:
        baseline["correction_buckets"] = {}
        baseline["edge_case_regression"] = {"count": 0, "fpr": None}

    return baseline


def _is_inconclusive(ai_probability):
    if ai_probability is None:
        return True
    prob = float(ai_probability)
    return INCONCLUSIVE_LOW <= prob <= INCONCLUSIVE_HIGH


def _phone_screen_fpr_with_inconclusive(records):
    """FPR counting only definite AI calls (>=80%); inconclusive band is not a false positive."""
    count = len(records)
    if not count:
        return None, 0
    definite_fps = sum(
        1
        for row in records
        if float(row.get("ai_probability") or 0) >= DEFINITE_AI_THRESHOLD
    )
    return round(_safe_div(definite_fps, count), 4), definite_fps


def phone_screen_gate_passed(bucket_payload):
    """Pass if standard FPR <= 10% or all errors route to inconclusive (no definite AI FP)."""
    fpr = (bucket_payload or {}).get("fpr")
    records = (bucket_payload or {}).get("records") or []
    if fpr is not None and fpr <= GATES["phone_screen_photos_fpr_max"]:
        return True, f"phone_screen_photos FPR {fpr} within gate"
    inconclusive_fpr, definite_fps = _phone_screen_fpr_with_inconclusive(records)
    if inconclusive_fpr is not None and inconclusive_fpr <= GATES["phone_screen_photos_fpr_max"]:
        return True, (
            f"phone_screen_photos routes to inconclusive "
            f"(definite-AI FPR {inconclusive_fpr}, {definite_fps} definite false positives)"
        )
    return False, (
        f"phone_screen_photos FPR {fpr} exceeds {GATES['phone_screen_photos_fpr_max']} "
        f"and does not route to inconclusive"
    )


def check_promotion_gates(candidate_metrics, production_metrics):
    issues = []
    passes = []

    cand_acc = candidate_metrics.get("bootstrap_accuracy")
    prod_acc = production_metrics.get("bootstrap_accuracy")
    if cand_acc is not None and prod_acc is not None and cand_acc < prod_acc:
        issues.append(f"Bootstrap accuracy decreased ({cand_acc} < {prod_acc})")
    elif cand_acc is not None and prod_acc is not None:
        passes.append("Bootstrap accuracy maintained or improved")

    edge_fpr = (candidate_metrics.get("edge_case_regression") or {}).get("fpr")
    if edge_fpr is not None and edge_fpr > GATES["real_phone_fpr_max"]:
        issues.append(f"real_phone FPR {edge_fpr} exceeds {GATES['real_phone_fpr_max']}")
    elif edge_fpr is not None:
        passes.append(f"real_phone FPR {edge_fpr} within gate")

    correction = candidate_metrics.get("correction_buckets") or {}
    pet_fpr = (correction.get("real_pet_photos") or {}).get("fpr")
    if pet_fpr is not None and pet_fpr > GATES["real_pet_photos_fpr_max"]:
        issues.append(
            f"real_pet_photos FPR {pet_fpr} exceeds {GATES['real_pet_photos_fpr_max']}"
        )
    elif pet_fpr is not None:
        passes.append(f"real_pet_photos FPR {pet_fpr} within gate")

    phone_payload = correction.get("phone_screen_photos") or {}
    phone_ok, phone_msg = phone_screen_gate_passed(phone_payload)
    if phone_ok:
        passes.append(phone_msg)
    else:
        issues.append(phone_msg)

    ai_fnr = (correction.get("ai_controls") or {}).get("fnr")
    if ai_fnr is not None and ai_fnr > GATES["ai_controls_fnr_max"]:
        issues.append(f"ai_controls FNR {ai_fnr} exceeds {GATES['ai_controls_fnr_max']}")
    elif ai_fnr is not None:
        passes.append(f"ai_controls FNR {ai_fnr} within gate")

    cand_ece = candidate_metrics.get("ece")
    prod_ece = production_metrics.get("ece")
    if cand_ece is not None and prod_ece is not None:
        if cand_ece > prod_ece + GATES["ece_worsen_max"]:
            issues.append(
                f"ECE worsened by more than {GATES['ece_worsen_max']} "
                f"({cand_ece} vs {prod_ece})"
            )
        else:
            passes.append("ECE within tolerance")

    improved_bucket = False
    prod_correction = production_metrics.get("correction_buckets") or {}
    for bucket in FAILURE_BUCKETS:
        cand_fpr = (correction.get(bucket) or {}).get("fpr")
        prod_fpr = (prod_correction.get(bucket) or {}).get("fpr")
        if cand_fpr is not None and prod_fpr is not None and cand_fpr < prod_fpr:
            improved_bucket = True
            passes.append(f"Improved {bucket} FPR ({prod_fpr} -> {cand_fpr})")

    if prod_correction and not improved_bucket:
        issues.append("Candidate did not improve any known failure bucket")

    return {"passed": not issues, "issues": issues, "passes": passes}
