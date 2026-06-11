# ProofOrigin ML Dataset + Calibration Foundation

This directory contains the **real** computer-vision training and calibration pipeline for ProofOrigin AI.

## Important

- **No production-trained model exists** until you add labeled images and run training.
- Scripts exit with a clear message if the dataset is missing or too small.
- Metrics are written only after a real training or calibration run. **Nothing is fabricated.**

## Directory layout

```
ml/
  datasets/
    real_camera/      # Authentic phone/DSLR photos
    ai_generated/     # Midjourney, DALL·E, SD, Flux, Gemini, etc.
    edited_real/      # Filters, Canva, Photoshop, re-encoded originals
    screenshots/      # Social posts, phone screenshots, reposted media
    uncertain/        # Mixed media ProofOrigin should not classify confidently
    validation/       # Holdout mirrors of each bucket above
    manifest.jsonl    # Dataset provenance (created by prepare script)
    manifest.csv
  calibration/
    calibration_manifest.jsonl   # Human-verified score reviews (local only)
  models/
    prooforigin_cv_classifier.pt # Created by training (not committed)
    metrics.json                 # Created by training
  train_classifier.py
  evaluate_classifier.py
  inference_classifier.py
  calibrate_scores.py
  dataset_utils.py
  calibration_utils.py
```

Legacy folders `ml/datasets/real/` and `ml/datasets/ai/` are still scanned and mapped into `real_camera` / `ai_generated` for backward compatibility.

## Dataset targets

| Phase | real_camera | ai_generated | edited_real | screenshots |
| --- | ---: | ---: | ---: | ---: |
| Bootstrap calibration | 500 | 500 | 100 | 100 |
| Stronger model | 10,000 | 10,000 | 2,000 | 2,000 |

## Dataset sources (license-safe)

### Option A — Fastest (recommended first)

- **Real photos you own**: phone/DSLR originals into `real_camera/`
- **AI images you generate yourself** into `ai_generated/`
- Clean rights, clear labels, no license review delay

### Option B — Research scale (license review required)

| Dataset | Use case | License note |
| --- | --- | --- |
| [GenImage](https://genimage-dataset.github.io/) | 1M+ real/fake pairs across many generators | Review before commercial use |
| [DIRE](https://arxiv.org/abs/2303.09295) | Diffusion detection, unseen-generator robustness | Academic; verify redistribution |
| [Hugging Face AI-vs-Deepfake-vs-Real](https://huggingface.co/datasets/prithivMLmods/AI-vs-Deepfake-vs-Real) | Bootstrap smaller splits | Verify dataset card license |

**Do not** scrape copyrighted collections. **Do not** claim model performance without evaluation on real labeled data.

### Option C — Long-term moat

With explicit user permission, ProofOrigin uploads can append to a proprietary calibration dataset (`ml/calibration/` + optional training buckets). This is the strongest long-term asset.

## Add real images

```bash
python scripts/prepare_ml_dataset.py \
  --source-dir C:/Photos/my_phone_photos \
  --label real_camera \
  --source user_owned \
  --license user-owned \
  --generator-or-camera-source "iPhone 15 Pro" \
  --notes "Outdoor originals with EXIF"
```

## Add AI images

```bash
python scripts/prepare_ml_dataset.py \
  --source-dir C:/AI/midjourney_exports \
  --label ai_generated \
  --source self_generated \
  --license user-owned \
  --generator-or-camera-source "Midjourney v6"
```

## Add edited images and screenshots

```bash
python scripts/prepare_ml_dataset.py --source-dir ./raw/edited --label edited_real
python scripts/prepare_ml_dataset.py --source-dir ./raw/screens --label screenshots
python scripts/prepare_ml_dataset.py --source-dir ./holdout/real --label real_camera --split validation
```

## Audit dataset quality

```bash
python scripts/audit_ml_dataset.py
python scripts/audit_ml_dataset.py --split validation
```

Audits per-bucket counts, unreadable files, duplicate SHA256 hashes, image sizes, formats, EXIF presence, and class imbalance.

## Install training dependencies

```bash
pip install -r requirements-dev.txt
```

## Train (binary real-origin vs AI)

Training collapses buckets for the first classifier:

- **Real-origin (label 0)**: `real_camera`, `edited_real`, `screenshots`
- **AI (label 1)**: `ai_generated`
- **Skipped**: `uncertain`

```bash
python -m ml.train_classifier --epochs 5 --min-per-class 10
```

Minimum default is 2 per class for smoke tests; use **500+ per primary class** before trusting calibration.

If the dataset is missing:

```
Dataset required: add labeled images under ml/datasets/<bucket>/ ...
```

## Evaluate classifier

```bash
python -m ml.evaluate_classifier
```

## Calibrate scores (human-verified)

After reviewing `/analyze` outputs against known labels:

```bash
python -m ml.calibrate_scores
```

See `ml/calibration/README.md` for manifest format and human-made photo protection metrics.

## Backend inference

When `ml/models/prooforigin_cv_classifier.pt` exists and PyTorch is installed, `/analyze` includes:

- `model_sources_used`: may include `prooforigin_cv_classifier`
- `evaluation_mode`: `trained_model` or `trained_model_with_external`
- `detector_comparison`: optional signal comparison bundle

If the model file is missing, `/analyze` falls back to `local_heuristics` safely.

## External detector comparison (not blind trust)

`core/external_detectors.py` provides optional adapters:

| Detector | Enable with |
| --- | --- |
| Sightengine | `SIGHTENGINE_USER`, `SIGHTENGINE_SECRET` |
| OpenAI Vision | `OPENAI_API_KEY` |
| Hugging Face classifier | `PROOFORIGIN_HF_MODEL` + `transformers` |
| Local ProofOrigin classifier | trained `.pt` file |

When external models **disagree** (spread ≥ 25 points), ProofOrigin shifts to cautious modes (`calibration_uncertain`, `calibration_caution`) and avoids hard fake/real claims. External APIs inform calibration; they do not override human-verified labels.

## Production note

Railway production can run without PyTorch. Heuristic analysis remains available. Deploy trained weights only after real labeled training and calibration review.
