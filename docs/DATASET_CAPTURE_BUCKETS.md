# Dataset Capture Buckets

ProofOrigin accepts private dataset captures into **20 buckets**. Only **5** participate in the CV v0.2 safe auto-train retraining gate.

## Full bucket list (20)

### CV v0.2 correction gate (5)

These buckets gate retraining via `audit_correction_set.py` and `safe_auto_train.py`:

| Bucket | Label | Local path |
|--------|-------|------------|
| `real_pet_photos` | real_camera | `ml/correction_sets/v0_2/real_pet_photos/` |
| `phone_screen_photos` | real_camera | `ml/correction_sets/v0_2/phone_screen_photos/` |
| `indoor_soft_light` | real_camera | `ml/correction_sets/v0_2/indoor_soft_light/` |
| `screenshots` | real_camera | `ml/correction_sets/v0_2/screenshots/` |
| `ai_controls` | ai_generated | `ml/correction_sets/v0_2/ai_controls/` |

Targets: 50 / 25 / 25 / 25 / 25 images respectively.

### General expansion (15)

Stored for future mapping. **Not included in CV v0.2 retraining** until explicitly mapped in code.

| Bucket | Label |
|--------|-------|
| `real_people_photos` | real_camera |
| `real_document_photos` | real_camera |
| `real_food_photos` | real_camera |
| `real_vehicle_photos` | real_camera |
| `real_nature_sky` | real_camera |
| `real_low_light` | real_camera |
| `real_reflections_glass` | real_camera |
| `photo_of_photo` | real_camera |
| `social_media_screenshots` | real_camera |
| `edited_real` | edited_real |
| `ai_generated_people` | ai_generated |
| `ai_generated_objects` | ai_generated |
| `ai_generated_art` | ai_generated |
| `ai_generated_screenshot_like` | ai_generated |
| `uncertain_mixed` | uncertain |

**Default import path:** `ml/correction_sets/general_expansion/{bucket}/`

**Alternate path (documented only):** `ml/datasets/private_expansion/{bucket}/`

Manifest: `ml/correction_sets/general_expansion/manifest.jsonl`

## Validation

Backend registry: `ml/capture_buckets.py`

- `is_valid_capture_bucket()` — any of the 20 buckets
- `is_v02_correction_bucket()` — v0.2 gate buckets only
- `is_general_expansion_bucket()` — expansion buckets only
- `normalize_capture_bucket()` — import/review validation

## Import routing

`scripts/import_private_dataset_captures.py`:

- v0.2 buckets → `ml/correction_sets/v0_2/{bucket}/` + v0.2 manifest
- Expansion buckets → `ml/correction_sets/general_expansion/{bucket}/` + expansion manifest
- SHA-256 dedup uses combined manifest index across both tiers

## Audit commands

```bash
python scripts/audit_correction_set.py --compact      # v0.2 gate only
python scripts/audit_general_expansion.py             # expansion inventory
python scripts/audit_private_dataset_captures.py      # remote + local combined
```

## Training scope

`ml/training_samples.py` and `safe_auto_train.py` merge **bootstrap dataset + v0.2 correction buckets only**. General expansion images are never pulled into CV v0.2 candidate training unless a future phase adds explicit mapping.
