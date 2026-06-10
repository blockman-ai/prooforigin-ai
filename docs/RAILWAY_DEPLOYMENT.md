# Railway Deployment — ProofOrigin AI

This backend is deployed on [Railway](https://railway.app) from the `main` branch of this repository.

## Required environment variable

Set this in the Railway service **Variables** tab:

| Variable | Value |
|----------|-------|
| `RAILPACK_PYTHON_VERSION` | `3.11` |

Without Python 3.11, the build may use an incompatible runtime and fail health checks or import errors.

## Start command

Railway reads `railway.toml` for deploy settings. The start command must be:

```bash
uvicorn api.main:app --host 0.0.0.0 --port $PORT --workers 1
```

Do not override this in the Railway dashboard unless you are debugging locally. The `$PORT` variable is injected by Railway.

## Health check

| Setting | Value |
|---------|-------|
| Healthcheck path | `/health` |
| Expected response | `{"status": "ok", "service": "ProofOrigin AI"}` |
| Timeout | 120 seconds (configured in `railway.toml`) |

Railway uses `/health` to decide whether a deployment is healthy. If the health check fails, the deploy is rolled back.

## Deployment marker endpoints

After a successful deploy, verify these endpoints on your Railway public URL:

| Path | Purpose |
|------|---------|
| `/` | Root info; includes `health_path` and `version_path` |
| `/health` | Liveness probe for Railway |
| `/version` | Shows `commit_hint` (short git SHA from `RAILWAY_GIT_COMMIT_SHA`) and registered route names |

## Troubleshooting: `/` returns 200 but `/health` returns 404

This almost always means **Railway is serving an older deployment** that predates the `/health` route, not that the current code is wrong.

1. Confirm the latest commit is pushed to `main` on GitHub.
2. Open the Railway dashboard → your ProofOrigin AI service.
3. Set `RAILPACK_PYTHON_VERSION=3.11` if not already set.
4. Go to **Deployments** and click **Redeploy** on the latest commit (or trigger a new deploy from `main`).
5. Wait for the deploy to finish and the health check to pass.
6. Test:
   - `GET /health` → `200` with `{"status": "ok", "service": "ProofOrigin AI"}`
   - `GET /version` → `200` with `commit_hint` matching the deployed commit

If `/health` is still 404 after redeploying the latest commit, check that `railway.toml` is present at the repo root and that the start command points to `api.main:app`.
