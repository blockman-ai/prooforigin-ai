#!/usr/bin/env python3
"""Train ProofOrigin real vs ai_generated image classifier."""

import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path

from ml.dataset_utils import (
    DATASET_REQUIRED_MESSAGE,
    METRICS_PATH,
    MODEL_PATH,
    MODELS_DIR,
    collect_binary_training_samples,
)


def _require_torch():
    try:
        import torch
        from torch import nn
        from torch.utils.data import DataLoader, Dataset
        from torchvision import models, transforms

        return torch, nn, DataLoader, Dataset, models, transforms
    except ImportError as exc:
        raise SystemExit(
            "PyTorch is required for training. Install with: pip install torch torchvision"
        ) from exc


class ProofOriginImageDataset:
    def __init__(self, samples, transform):
        self.samples = samples
        self.transform = transform

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):
        from PIL import Image

        path, label = self.samples[index]
        with Image.open(path) as image:
            tensor = self.transform(image.convert("RGB"))
        return tensor, label


def _collect_samples(min_per_class):
    samples, counts, real_count, ai_count = collect_binary_training_samples(
        min_per_class=min_per_class,
        split="train",
    )
    binary_samples = [(path, label) for path, label, _bucket in samples]
    return binary_samples, real_count, ai_count


def _split_samples(samples, val_ratio=0.2, seed=42):
    random.Random(seed).shuffle(samples)
    val_size = max(1, int(len(samples) * val_ratio))
    val_samples = samples[:val_size]
    train_samples = samples[val_size:]
    if not train_samples:
        raise SystemExit("Training split is empty. Add more labeled images.")
    return train_samples, val_samples


def _build_model(num_classes, torch, models, nn):
    model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
    model.classifier[3] = nn.Linear(model.classifier[3].in_features, num_classes)
    return model


def _compute_metrics(y_true, y_pred):
    labels = [0, 1]
    matrix = {actual: {pred: 0 for pred in labels} for actual in labels}
    for actual, pred in zip(y_true, y_pred):
        matrix[actual][pred] += 1

    metrics = {}
    for label, name in [(0, "real"), (1, "ai_generated")]:
        tp = matrix[label][label]
        fp = matrix[1 - label][label]
        fn = matrix[label][1 - label]
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall)
            else 0.0
        )
        metrics[name] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }

    accuracy = sum(1 for a, p in zip(y_true, y_pred) if a == p) / len(y_true)
    return {
        "accuracy": round(accuracy, 4),
        "confusion_matrix": matrix,
        "per_class": metrics,
    }


def train(
    *,
    epochs=5,
    batch_size=16,
    learning_rate=1e-4,
    val_ratio=0.2,
    min_per_class=2,
    image_size=224,
):
    samples, real_count, ai_count = _collect_samples(min_per_class=min_per_class)
    torch, nn, DataLoader, Dataset, models, transforms = _require_torch()
    train_samples, val_samples = _split_samples(samples, val_ratio=val_ratio)

    train_transform = transforms.Compose(
        [
            transforms.Resize((image_size, image_size)),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )
    eval_transform = transforms.Compose(
        [
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )

    train_loader = DataLoader(
        ProofOriginImageDataset(train_samples, train_transform),
        batch_size=batch_size,
        shuffle=True,
    )
    val_loader = DataLoader(
        ProofOriginImageDataset(val_samples, eval_transform),
        batch_size=batch_size,
        shuffle=False,
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = _build_model(num_classes=2, torch=torch, models=models, nn=nn).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

    for epoch in range(epochs):
        model.train()
        running_loss = 0.0
        for inputs, labels in train_loader:
            inputs = inputs.to(device)
            labels = labels.to(device)
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            running_loss += float(loss.item())

        avg_loss = running_loss / max(1, len(train_loader))
        print(f"epoch={epoch + 1}/{epochs} train_loss={avg_loss:.4f}")

    model.eval()
    y_true = []
    y_pred = []
    with torch.no_grad():
        for inputs, labels in val_loader:
            inputs = inputs.to(device)
            outputs = model(inputs)
            preds = outputs.argmax(dim=1).cpu().tolist()
            y_pred.extend(preds)
            y_true.extend(labels.tolist())

    eval_metrics = _compute_metrics(y_true, y_pred)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    checkpoint = {
        "model_state_dict": model.cpu().state_dict(),
        "class_names": ["real", "ai_generated"],
        "num_classes": 2,
        "image_size": image_size,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "dataset_counts": {"real": real_count, "ai_generated": ai_count},
    }
    torch.save(checkpoint, MODEL_PATH)

    metrics_payload = {
        "model_path": str(MODEL_PATH),
        "trained_at": checkpoint["trained_at"],
        "dataset_counts": checkpoint["dataset_counts"],
        "train_samples": len(train_samples),
        "validation_samples": len(val_samples),
        "epochs": epochs,
        "validation_metrics": eval_metrics,
        "note": "Metrics computed on validation split only.",
    }
    METRICS_PATH.write_text(json.dumps(metrics_payload, indent=2), encoding="utf-8")

    print(f"Saved model to {MODEL_PATH}")
    print(f"Saved metrics to {METRICS_PATH}")
    print(json.dumps(eval_metrics, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Train ProofOrigin CV classifier")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--val-ratio", type=float, default=0.2)
    parser.add_argument("--min-per-class", type=int, default=2)
    args = parser.parse_args()

    train(
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        val_ratio=args.val_ratio,
        min_per_class=args.min_per_class,
    )


if __name__ == "__main__":
    main()
