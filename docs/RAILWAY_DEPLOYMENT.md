# Railway Deployment — ProofOrigin AI

Deploy from `main` using **Railpack** (Railway default). Do not use the legacy Nixpacks builder.

## Python version (fix mise install failures)

Railway installs Python via **mise**. Exact patch pins (e.g. `python-3.11.9` in `runtime.txt`) often fail with:

```text
mise ERROR failed to install core:python@X.Y.Z: no precompiled python found
```

**Use major.minor only:**

| Method | Value |
|--------|-------|
| `.python-version` (repo root) | `3.11` |
| Railway Variable | `RAILPACK_PYTHON_VERSION=3.11` |

Do **not** add `runtime.txt`, `nixpacks.toml`, `Procfile`, or `mise.toml` unless you have a specific need.

## Railway service settings

| Setting | Value |
|---------|-------|
| Builder | **Railpack** (default) |
| Root directory | repo root |
| Start command | from `railway.toml` (do not override unless debugging) |

## Required environment variable

| Variable | Value |
|----------|-------|
| `RAILPACK_PYTHON_VERSION` | `3.11` |

Optional API keys (analysis quality): `OPENAI_API_KEY`, `SIGHTENGINE_USER`, `SIGHTENGINE_SECRET`, `PROOFORIGIN_API_KEY`.

## Dependencies

Production install uses **`requirements.txt` only** (slim — no PyTorch).

ML training (`torch`, `torchvision`) is in `requirements-dev.txt` for local/offline training, not Railway production.

## Start command

```bash
uvicorn api.main:app --host 0.0.0.0 --port $PORT --workers 1
```

Configured in `railway.toml`. `$PORT` is injected by Railway.

## Health check

| Setting | Value |
|---------|-------|
| Healthcheck path | `/health` |
| Expected response | `{"status": "ok", "service": "ProofOrigin AI"}` |
| Timeout | 120 seconds |

## Verify after deploy

```text
GET /
GET /health
GET /version
POST /analyze  (multipart field: file)
```

CORS allowed origins include `prooforigin.org`, `prooforigin-site.vercel.app`, and `prooforigin.vercel.app`.

## Troubleshooting

### Build fails at `mise install` / Python step

1. Confirm builder is **Railpack**, not Nixpacks.
2. Set `RAILPACK_PYTHON_VERSION=3.11`.
3. Ensure `.python-version` contains `3.11` (not a bleeding-edge patch).
4. Remove `runtime.txt` if it was re-added.
5. Redeploy with a clean build if cache is stale.

### `/` returns 200 but `/health` returns 404

Railway is serving an older deployment. Redeploy latest `main` commit.
