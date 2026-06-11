# Private Dataset Vault

ProofOrigin treats training imagery as **proprietary, consent-bound assets**. Raw images never belong in GitHub, public APIs, or production deploy artifacts. This document describes how the backend keeps datasets private while still supporting reproducible training and validation.

## Core principles

1. **Raw images never go in GitHub** — Only schemas, scripts, `.gitkeep` placeholders, and example manifests are versioned.
2. **Dataset images live only in private storage** — Local encrypted drives, private Supabase buckets, S3, or R2. Never in the public repo.
3. **Manifests store metadata, not pixels** — Each row records `sha256`, `label`, `split`, `source`, `license`, `provenance`, `consent_status`, and optional notes. Manifests may reference private paths that exist only on the machine or bucket where training runs.
4. **Training pulls private data locally or from a private bucket** — `scripts/hash_dataset.py` and `scripts/prepare_ml_dataset.py` operate on local paths. Sync from private storage before training; never commit the sync target.
5. **Production deploy uses model weights only** — Railway and `/analyze` ship `prooforigin_cv_classifier.pt` (or heuristics fallback). Raw dataset folders are not deployed.
6. **Raw images are never exposed through API routes** — `/analyze` accepts a single uploaded image for inference. It does not list, download, or serve dataset files.

## Directory layout (local only)

```
ml/datasets/              # Training buckets (gitignored)
ml/datasets/validation/   # Holdout buckets (gitignored)
ml/datasets/manifest.jsonl
ml/calibration/           # Human-verified calibration rows (gitignored)
ml/edge_cases/            # Ad-hoc edge-case samples (gitignored)
ml/models/                # Weights + metrics (gitignored)
ml/reports/               # Evaluation output (gitignored JSON; local MD)
```

## Manifest contract

Schema: `ml/dataset_manifest.schema.json`

Required fields per image:

| Field | Purpose |
|-------|---------|
| `file_path` | Local or bucket-relative path (private) |
| `sha256` | Content fingerprint for dedup and integrity |
| `label` | Bucket label (`real_camera`, `ai_generated`, etc.) |
| `split` | `train` or `validation` |
| `source` | Dataset origin (e.g. `tigas_bootstrap`, `user_upload`) |
| `license` | License or usage rights reference |
| `consent_status` | `granted`, `pending`, `not_applicable`, or `unknown` |
| `provenance` | How the asset was obtained or verified |
| `generator_or_camera_source` | Model name or camera/device hint |
| `created_at` | ISO-8601 timestamp |
| `notes` | Free-form reviewer notes |

Run `python scripts/hash_dataset.py` to scan buckets and build/update the manifest.  
Run `python scripts/verify_dataset_manifest.py` before training to validate integrity.

## Storage options

| Option | Use case |
|--------|----------|
| Encrypted local drive | Solo dev, air-gapped training |
| Private Supabase Storage | Team sync with RLS, no public URLs |
| Private S3 / R2 bucket | CI training runners, signed URLs for pull only |
| Signed URLs | Time-limited download during train job; no client-facing access |

**Never** expose bucket objects through ProofOrigin API routes. Clients upload one image at a time for analysis; they do not browse the vault.

## Audit and access control

- Prefer bucket policies that deny public read.
- Log manifest verification and training runs (who, when, record count).
- Rotate credentials for private buckets; do not store secrets in the repo.
- Review `consent_status` and `license` before adding new sources.

## Production vs development

| Environment | Dataset | Model | API |
|-------------|---------|-------|-----|
| Local dev | Full private vault on disk | `.pt` + `metrics.json` | `/analyze` with CV blend |
| CI / train job | Pulled from private bucket | Writes `.pt` to artifact store | N/A |
| Production | **Not mounted** | Weights only (optional) | `/analyze` unchanged contract |

## What must never be committed

- Any file under `ml/datasets/**` except `.gitkeep`
- `ml/datasets/manifest.jsonl` / `manifest.csv` (contain private paths)
- `ml/calibration/*.jsonl` (except `.example`)
- `ml/models/*.pt`, `ml/models/*.json`
- `ml/edge_cases/**` except `.gitkeep`
- `ml/reports/*.json`
- Raw training images anywhere in the repo

## Related scripts

```bash
python scripts/hash_dataset.py --split all
python scripts/verify_dataset_manifest.py
python scripts/audit_ml_dataset.py
python scripts/evaluate_edge_cases.py
python scripts/import_private_dataset_captures.py --dry-run
python scripts/audit_private_dataset_captures.py
python scripts/safe_auto_train.py --dry-run
python scripts/generate_safe_training_gate_status.py
```

See also: [ml/README.md](../ml/README.md), [dataset_rules.md](./dataset_rules.md), [PRIVATE_CAPTURE_ENV.example](./PRIVATE_CAPTURE_ENV.example).

## Temporary Dataset Capture Workflow

This workflow supports a **future website capture tool** that uploads training candidates to private Supabase storage. It is temporary infrastructure until a full review UI ships.

### Flow

1. **Website capture** — User submits a photo through a future capture tool with explicit consent.
2. **Private Supabase bucket** — Raw bytes land in `PRIVATE_DATASET_BUCKET` (default `po-private-dataset`). Bucket is private; no public URLs.
3. **Suggested label (optional)** — OpenAI Vision may propose a label and correction bucket. Suggestions are stored on the capture row only; they are **not** used for training.
4. **Human review required** — A reviewer sets `human_verified_label`, `correction_bucket`, and `approved_for_training=true` only after manual approval.
5. **Backend import** — `scripts/import_private_dataset_captures.py` pulls approved rows locally into `ml/correction_sets/v0_2/{bucket}/`, computes SHA-256, skips duplicates, and appends to the correction manifest. Approval does **not** train immediately.
6. **Safe auto-train gate** — `scripts/safe_auto_train.py` imports approved captures, verifies correction targets, trains a candidate model, evaluates regression gates, and only copies a passing candidate to `prooforigin_cv_classifier_candidate.pt` (manual promotion required).
7. **Training (later)** — When all correction targets are met and promotion gates pass, v0.2 may replace production weights manually. Production deploy ships **weights only**.

### Supabase table contract

Table: `private_dataset_captures`

| Column | Purpose |
|--------|---------|
| `id` | Primary key |
| `storage_path` | Object path inside private bucket |
| `correction_bucket` | One of: `real_pet_photos`, `phone_screen_photos`, `indoor_soft_light`, `screenshots`, `ai_controls` |
| `approved_for_training` | Must be `true` for import |
| `consent_status` | Must be `granted` or `owner_provided` |
| `consent_granted` | Boolean fallback for consent |
| `human_verified_label` | Reviewer-confirmed label |
| `suggested_label` | OpenAI Vision suggestion (not used without approval) |
| `sha256` | Optional pre-upload hash for dedup |
| `source` | e.g. `website_capture` |
| `reviewer_notes` | Audit trail |

### Environment variables

See [PRIVATE_CAPTURE_ENV.example](./PRIVATE_CAPTURE_ENV.example):

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `PRIVATE_DATASET_BUCKET=po-private-dataset`

### Safety rules

- **Consent required** — Captures without consent are skipped at import.
- **Human approval required** — Only `approved_for_training=true` rows are downloaded.
- **No public API exposure** — `/analyze` is unchanged. No route lists, downloads, or serves vault/capture files.
- **No upload from import script** — Import is download-only into gitignored local folders.
- **No auto-train** — Import never triggers training.
