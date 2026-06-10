import json
import os
from pathlib import Path

from ml.dataset_utils import METRICS_PATH, MODEL_PATH

_MODEL = None
_METRICS = None
_LOAD_ERROR = None


def _torch_available():
    try:
        import torch  # noqa: F401

        return True
    except ImportError:
        return False


def _load_metrics():
    global _METRICS
    if _METRICS is not None:
        return _METRICS

    if not METRICS_PATH.exists():
        _METRICS = {}
        return _METRICS

    try:
        _METRICS = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    except Exception:
        _METRICS = {}
    return _METRICS


def _build_model(num_classes=2):
    import torch
    from torchvision import models

    model = models.mobilenet_v3_small(weights=None)
    model.classifier[3] = torch.nn.Linear(model.classifier[3].in_features, num_classes)
    return model


def _load_model():
    global _MODEL, _LOAD_ERROR

    if _MODEL is not None:
        return _MODEL

    if _LOAD_ERROR is not None:
        return None

    if not _torch_available():
        _LOAD_ERROR = "PyTorch not installed"
        return None

    if not MODEL_PATH.exists():
        _LOAD_ERROR = "Trained model file not found"
        return None

    try:
        import torch

        checkpoint = torch.load(MODEL_PATH, map_location="cpu")
        model = _build_model(num_classes=checkpoint.get("num_classes", 2))
        model.load_state_dict(checkpoint["model_state_dict"])
        model.eval()
        _MODEL = {
            "model": model,
            "class_names": checkpoint.get("class_names", ["real", "ai_generated"]),
            "image_size": checkpoint.get("image_size", 224),
        }
        return _MODEL
    except Exception as exc:
        _LOAD_ERROR = str(exc)
        return None


def model_is_available():
    return _load_model() is not None


def run_cv_inference(image_path):
    loaded = _load_model()
    if loaded is None:
        return {
            "status": "unavailable",
            "ai_probability": None,
            "confidence": None,
            "label": None,
            "source": "prooforigin_cv_classifier",
            "reason": _LOAD_ERROR or "Model unavailable",
        }

    try:
        import torch
        from PIL import Image
        from torchvision import transforms

        image_size = loaded["image_size"]
        transform = transforms.Compose(
            [
                transforms.Resize((image_size, image_size)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225],
                ),
            ]
        )

        with Image.open(image_path) as image:
            tensor = transform(image.convert("RGB")).unsqueeze(0)

        with torch.no_grad():
            logits = loaded["model"](tensor)
            probs = torch.softmax(logits, dim=1).squeeze(0).tolist()

        class_names = loaded["class_names"]
        class_to_idx = {name: idx for idx, name in enumerate(class_names)}
        ai_idx = class_to_idx.get("ai_generated", 1)
        ai_probability = round(float(probs[ai_idx]) * 100, 2)
        predicted_idx = int(max(range(len(probs)), key=lambda i: probs[i]))
        predicted_label = class_names[predicted_idx]
        confidence = round(float(probs[predicted_idx]) * 100, 2)

        return {
            "status": "complete",
            "ai_probability": ai_probability,
            "confidence": confidence,
            "label": predicted_label,
            "source": "prooforigin_cv_classifier",
            "class_probabilities": {
                class_names[idx]: round(float(probs[idx]) * 100, 2)
                for idx in range(len(class_names))
            },
            "metrics": _load_metrics(),
        }
    except Exception as exc:
        return {
            "status": "failed",
            "ai_probability": None,
            "confidence": None,
            "label": None,
            "source": "prooforigin_cv_classifier",
            "reason": str(exc),
        }
