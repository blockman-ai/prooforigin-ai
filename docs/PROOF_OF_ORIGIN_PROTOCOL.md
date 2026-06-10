# Proof-of-Origin Protocol

## Definition

**Proof-of-Origin** is ProofOrigin's protocol for recording and verifying the existence, state, lineage, and evaluation context of a digital claim at a specific point in time.

ProofOrigin does **not** prove absolute truth. It produces a sealed, versioned evidence record that third parties can inspect and verify without trusting ProofOrigin's servers alone.

## Core Invariant

> ProofOrigin proves the existence, state, lineage, and evaluation context of a digital claim at a specific point in time — not absolute truth.

Every published bundle carries this invariant. Verification confirms record integrity, not moral or legal certainty.

## Evidence Bundle Structure

Immutable bundles are stored at:

```
data/evidence/{file_id}/v1.bundle.json
```

Each bundle includes:

| Field | Role |
|-------|------|
| `report_id` | Unique analysis identifier |
| `report_version` | Bundle schema version (currently `1`) |
| `published_at` | UTC timestamp when the bundle was sealed |
| `integrity` | Original and analysis SHA-256 hashes |
| `evidence_bundle_hash` | Canonical hash of the forensic payload |
| `policy_hash` | Hash of constitution policy config |
| `engine_snapshot_hash` | Hash of sanitized engine outputs |
| `protocol_name` | `"Proof-of-Origin"` |
| `protocol_version` | Protocol semver (e.g. `"0.1.0"`) |
| `protocol_invariant` | Non-negotiable scope statement |
| `protocol_claim_boundary` | What ProofOrigin explicitly does not claim |

Feedback is **never** stored inside the bundle. It is append-only at:

```
data/evidence/{file_id}/feedback_events.jsonl
```

## Versioned Evidence History

- `v1.bundle.json` is written **once** and never overwritten.
- Corrections publish new versions (`v2.bundle.json`, etc.) — never in-place edits.
- Each version has its own `evidence_bundle_hash` and `published_at`.
- History is preserved; older versions remain verifiable.

## Zero-Trust Verification Flow

1. **Load** the immutable bundle (`v1.bundle.json` or legacy flat file).
2. **Recompute** `evidence_bundle_hash` from canonical payload fields.
3. **Compare** recomputed hash to stored hash (`hash_match`).
4. **Confirm** file hash fields (`original_sha256`, `analysis_sha256`) are present.
5. **Optionally** upload the original file via `POST /verify` and compare SHA-256.
6. **Report scope** — `verified=true` means bundle + file hash integrity only, never "truth verified."

Public verification endpoints:

- `GET /verify-proof/{file_id}` — bundle integrity + stored hash presence
- `POST /verify` — uploaded file hash match against stored record
- `GET /report/{file_id}` — constitution-safe public summary

## Bitcoin Analogy

Bitcoin does not prove that a transaction is morally correct. It proves that a transaction existed, was ordered in a chain, and was witnessed by the network at a point in time.

Proof-of-Origin applies the same pattern to forensic evidence:

| Bitcoin | Proof-of-Origin |
|---------|-----------------|
| Transaction | Evidence bundle |
| Transaction ID | `evidence_bundle_hash` |
| Block | Merkle batch |
| Merkle root | Batch root over `evidence_bundle_hash` leaves |
| Chain history | Versioned bundle history (`v1`, `v2`, …) |

Anchor targets use `evidence_bundle_hash` as the merkle leaf — not the full mutable report. External Bitcoin/OpenTimestamps broadcast is planned but not yet implemented.

## What ProofOrigin Does NOT Claim

ProofOrigin does **not** claim:

- Absolute truth about media authenticity
- Legal guilt or innocence
- Moral certainty
- Definitive AI vs. human authorship as fact
- That forensic scores are infallible

Labels such as `public_label` and `decision_tier` are **constitution-safe evaluation signals**, not verdicts of truth.
