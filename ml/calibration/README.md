# ProofOrigin Calibration Layer

Calibration teaches ProofOrigin how to score **real phone photos**, **AI images**, **edited media**, **screenshots**, and **uncertain cases** without claiming absolute truth.

## Manifest format

Append human-verified rows to `ml/calibration/calibration_manifest.jsonl` (not committed by default).

Each JSONL row:

| Field | Purpose |
| --- | --- |
| `file_path` | Image evaluated |
| `true_label` | Bucket label (`real_camera`, `ai_generated`, etc.) |
| `prooforigin_ai_probability` | Score from `/analyze` |
| `manipulation_risk` | Risk score from `/analyze` |
| `confidence` | Protocol confidence band |
| `decision_tier` | Policy tier (`do_not_accuse`, `caution`, etc.) |
| `model_sources_used` | Engines that contributed |
| `human_verified_label` | Reviewer-confirmed label |
| `reviewer_notes` | Why the label was chosen |
| `public_label` | Public-facing label at evaluation time |
| `evaluation_mode` | Analysis mode used |
| `recorded_at` | ISO timestamp |

See `calibration_manifest.jsonl.example` for a starter row (rainbow phone photo case).

## Evaluate calibration

```bash
python -m ml.calibrate_scores
python -m ml.calibrate_scores --threshold 45
```

Reports:

- accuracy, precision, recall, F1
- confusion matrix
- expected calibration error (ECE)
- **human-made photo protection**: false positive rate on `real_camera`
- false negative rate on AI images

No metrics are fabricated. An empty manifest returns a clear error.

## Workflow

1. Run `/analyze` on a labeled image.
2. Record outputs plus human-verified label in the manifest.
3. Run `ml.calibrate_scores` after each batch of reviews.
4. Tune thresholds and training data based on false positives on real camera photos.
