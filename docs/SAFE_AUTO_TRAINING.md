# Safe Auto-Training Pipeline

ProofOrigin separates **capture approval** from **model training**. Approving a private dataset capture marks it ready for import; it does **not** train or deploy a model immediately.

## Flow overview

```
Capture approved (UI)
       ↓
ready_for_import=true  (no training yet)
       ↓
Training job requested (dataset_training_jobs.status='requested')
       ↓
run_training_jobs.py  OR  safe_auto_train.py
       ↓
  A. Auto-import approved captures
  B. Auto-audit correction targets
  C. Train candidate (only if gate OPEN)
  D. Evaluate candidate vs production baseline
  E. Check promotion gates (report only)
  F. Write reports (never auto-promote production)
```

## What runs automatically

| Step | Allowed | Notes |
|------|---------|-------|
| Import approved captures | Yes | `approved_for_training`, `ready_for_import`, not rejected/duplicate |
| Audit correction targets | Yes | All five v0.2 buckets must meet targets |
| Train candidate model | Yes (gate open only) | Writes to `ml/models/candidates/<timestamp>/` |
| Evaluate candidate | Yes | Bootstrap, correction buckets, edge-case regression |
| Generate reports | Yes | See report list below |
| Promote to production | **No** | `ml/models/prooforigin_cv_classifier.pt` is never replaced |
| Deploy to Railway | **No** | Manual deploy after human review |

## Import eligibility

Captures are imported only when **all** of the following are true:

- `approved_for_training = true`
- `ready_for_import = true`
- `rejected = false`
- `is_duplicate = false`
- `keep_for_regression_only = false`
- Valid consent and correction bucket

Duplicates are skipped by SHA-256 before download (manifest index + Supabase unique index).

## Training gate

Before training, `audit_correction_set.py` checks **v0.2 correction bucket targets only** (general expansion buckets are excluded):

| Bucket | Target |
|--------|--------|
| real_pet_photos | 50 |
| phone_screen_photos | 25 |
| indoor_soft_light | 25 |
| screenshots | 25 |
| ai_controls | 25 |

General expansion captures are stored under `ml/correction_sets/general_expansion/` for future use but do **not** affect this gate. See [DATASET_CAPTURE_BUCKETS.md](./DATASET_CAPTURE_BUCKETS.md).

If targets are not met, the pipeline exits with `status=gate_closed`, writes a gate-closed report, and **does not train**.

## Promotion gates (candidate evaluation)

A candidate **passes** (status `promotion_ready`) only if:

- Bootstrap accuracy does not decrease vs production
- `real_phone` edge-case FPR ≤ 5%
- `real_pet_photos` FPR ≤ 5%
- `phone_screen_photos` FPR ≤ 10% **or** errors route to inconclusive (20–80 band, no definite-AI FP ≥ 80%)
- `ai_controls` FNR ≤ 5%
- ECE does not worsen by more than 0.02 vs production
- At least one known failure bucket improves vs production

Passing gates means **manual promotion is still required**. Production weights and Railway deploy are unchanged.

## Local commands

```bash
# Full pipeline (import → audit → train if gate open → evaluate → report)
python scripts/safe_auto_train.py

# Import + audit only (no training)
python scripts/safe_auto_train.py --dry-run

# Process Supabase job queue (requires dataset_training_jobs table)
python scripts/run_training_jobs.py

# Gate status report without training
python scripts/generate_safe_training_gate_status.py
```

### Required environment (import + jobs)

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
PRIVATE_DATASET_BUCKET=po-private-dataset
```

## Reports

| Report | When |
|--------|------|
| `ml/reports/safe_training_gate_status.md` | Always (latest gate snapshot) |
| `ml/reports/safe_training_gate_closed_<timestamp>.md` | Gate closed, no training |
| `ml/reports/candidate_eval_<timestamp>.md` | Candidate trained |
| `ml/reports/candidate_eval_<timestamp>.json` | Candidate trained (machine-readable) |
| `ml/reports/candidate_passed_<timestamp>.md` | Candidate passed promotion gates |
| `ml/reports/candidate_failed_<timestamp>.md` | Candidate failed promotion gates |

Reports are gitignored. They may reference local private paths; do not commit them.

## Inspecting a candidate

1. Open `ml/reports/safe_training_gate_status.md` for the latest run summary.
2. If trained, read `candidate_eval_<timestamp>.md` and `.json` for metrics vs production.
3. Candidate weights live at `ml/models/candidates/<timestamp>/prooforigin_cv_classifier.pt`.
4. If status is `promotion_ready`, review `candidate_passed_<timestamp>.md` before any manual promotion.

## Manual promotion (not automated)

To promote after review:

1. Back up `ml/models/prooforigin_cv_classifier.pt`.
2. Copy the approved candidate checkpoint over production weights locally.
3. Re-run validation scripts (`evaluate_classifier`, edge-case eval).
4. Deploy to Railway manually when satisfied.

The `/analyze` API contract is unchanged; only the weight file behind CV inference changes after manual promotion.

## Supabase job queue

See `docs/supabase/dataset_training_jobs.sql` for the `dataset_training_jobs` table schema.

Job statuses: `requested`, `running`, `blocked_gate_closed`, `failed`, `passed_candidate`, `rejected_candidate`, `promotion_ready`.

Insert a row with `status='requested'` to queue a run; `run_training_jobs.py` picks it up, runs the safe pipeline, and updates the row with report path and candidate path.
