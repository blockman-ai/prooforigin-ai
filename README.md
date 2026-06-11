# ProofOrigin AI

ProofOrigin AI is a research system for building, labeling, training, and evaluating media authenticity models.

The first goal is not to build a massive AI model immediately.

The first goal is to build a clean labeled dataset for detecting:

- real
- ai_generated
- edited
- screenshot
- manipulated

## Mission

Build the data foundation for ProofOrigin’s future authenticity engine.

## Dataset Fields

- image_hash
- source
- detector_score
- human_feedback
- final_label
- confidence
- uploaded_at
- reviewed_by
- image_width
- image_height
- mime_type

## Labels

- real
- ai_generated
- edited
- screenshot
- manipulated

## How ProofOrigin protects proprietary training data

ProofOrigin keeps training imagery **out of GitHub and off public APIs**. Raw photos live only in private storage (encrypted local drive, private Supabase/S3/R2 bucket). The repo versions schemas, scripts, and `.gitkeep` placeholders — not pixels.

- **Manifests, not images** — `ml/datasets/manifest.jsonl` stores `sha256`, label, split, source, license, consent, and provenance. Paths point to private storage on your machine or bucket.
- **Hash and verify locally** — `python scripts/hash_dataset.py` scans buckets and writes manifests. `python scripts/verify_dataset_manifest.py` checks integrity before training.
- **Private capture import** — Future website captures land in a private Supabase bucket. Only human-approved rows are pulled locally via `python scripts/import_private_dataset_captures.py`. OpenAI Vision may suggest labels; reviewers must approve before import. Audit with `python scripts/audit_private_dataset_captures.py`.
- **Production ships weights only** — Deploy `prooforigin_cv_classifier.pt`; do not mount dataset folders. `/analyze` accepts one uploaded image and never lists or serves vault files.
- **Gitignore enforcement** — `ml/datasets/**`, `ml/correction_sets/**`, `ml/edge_cases/**`, `ml/models/*.pt`, `ml/models/*.json`, and local manifests are blocked. See [docs/PRIVATE_DATASET_VAULT.md](docs/PRIVATE_DATASET_VAULT.md) and [docs/PRIVATE_CAPTURE_ENV.example](docs/PRIVATE_CAPTURE_ENV.example).
