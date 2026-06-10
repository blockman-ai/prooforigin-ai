#!/usr/bin/env python3
"""Evaluate trained ProofOrigin CV classifier on validation split."""

import argparse
import json

from ml.dataset_utils import METRICS_PATH, MODEL_PATH, ensure_dataset_ready
from ml.train_classifier import ProofOriginImageDataset, _compute_metrics, _require_torch, _split_samples


def evaluate(val_ratio=0.2, min_per_class=2):
    torch, _, DataLoader, _, _, transforms = _require_torch()
    from ml.inference_classifier import _build_model

    counts = ensure_dataset_ready(min_per_class=min_per_class)
    samples = []
    for path in counts["real_images"]:
        samples.append((path, 0))
    for path in counts["ai_images"]:
        samples.append((path, 1))

    _, val_samples = _split_samples(samples, val_ratio=val_ratio)
    eval_transform = transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )
    val_loader = DataLoader(
        ProofOriginImageDataset(val_samples, eval_transform),
        batch_size=16,
        shuffle=False,
    )

    if not MODEL_PATH.exists():
        raise SystemExit("Trained model not found. Run ml/train_classifier.py first.")

    checkpoint = torch.load(MODEL_PATH, map_location="cpu")
    model = _build_model(num_classes=checkpoint.get("num_classes", 2))
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    y_true = []
    y_pred = []
    with torch.no_grad():
        for inputs, labels in val_loader:
            outputs = model(inputs)
            preds = outputs.argmax(dim=1).tolist()
            y_pred.extend(preds)
            y_true.extend(labels.tolist())

    metrics = _compute_metrics(y_true, y_pred)
    print(json.dumps(metrics, indent=2))

    if METRICS_PATH.exists():
        payload = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
        payload["reevaluation"] = metrics
        METRICS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Evaluate ProofOrigin CV classifier")
    parser.add_argument("--val-ratio", type=float, default=0.2)
    parser.add_argument("--min-per-class", type=int, default=2)
    args = parser.parse_args()
    evaluate(val_ratio=args.val_ratio, min_per_class=args.min_per_class)


if __name__ == "__main__":
    main()
