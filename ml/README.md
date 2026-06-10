# ProofOrigin ML Training Foundation

This directory contains the **real** computer-vision training pipeline for ProofOrigin AI.

## Important

- No model is considered production-ready until you add labeled images and run training.
- Scripts exit with a clear message if the dataset is missing or too small.
- Metrics are written only after a real training run. Nothing is fabricated.

## Directory layout

```
ml/
  datasets/
    real/     # user-owned real photographs
    ai/       # AI-generated images
  models/
    prooforigin_cv_classifier.pt   # created by training (not committed by default)
    metrics.json                   # created by training
  train_classifier.py
  evaluate_classifier.py
  inference_classifier.py
```

## Dataset sources (license-safe)

Add images manually. Do **not** auto-scrape copyrighted collections.

Recommended sources:

1. **Real images** (`ml/datasets/real/`)
   - Photos you own or have explicit rights to use
   - Camera originals with EXIF when possible
   - Diverse lighting, subjects, and formats (JPEG, PNG, WEBP)

2. **AI-generated images** (`ml/datasets/ai/`)
   - Images you generated yourself (Midjourney, DALL·E, Stable Diffusion, etc.)
   - Clearly synthetic samples for classifier contrast

3. **Public datasets** (only when license allows commercial/research use)
   - Read each dataset license before importing
   - Keep provenance notes outside the repo if required by the license

## Prepare and audit dataset

```bash
python scripts/prepare_ml_dataset.py --source-dir /path/to/raw/images
python scripts/audit_ml_dataset.py
```

## Install training dependencies

```bash
pip install -r requirements-dev.txt
```

Training requires `torch` and `torchvision` (listed in `requirements-dev.txt`).

## Train

```bash
python -m ml.train_classifier --epochs 5 --min-per-class 10
```

Minimum default in script is 2 per class for smoke testing; use **at least 10+ per class** for meaningful results.

If the dataset is missing:

```
Dataset required: add real images to ml/datasets/real and AI images to ml/datasets/ai
```

## Evaluate

```bash
python -m ml.evaluate_classifier
```

## Backend inference

When `ml/models/prooforigin_cv_classifier.pt` exists and PyTorch is installed, `/analyze` will include:

- `model_sources_used`: includes `prooforigin_cv_classifier`
- `evaluation_mode`: includes `trained_model`

If the model file is missing, `/analyze` falls back to `local_heuristics` safely.

## Production note

Railway production can run without PyTorch installed. Heuristic analysis remains available. Install PyTorch and deploy the trained `.pt` file only when you are ready for CV inference in production.
