# Operations Runbook

## 1) Health Checks

- API liveness: `GET /health`
- Model info: `GET /api/model/info`

Expected:
- health endpoint returns HTTP 200
- model endpoint returns model metadata without server error

## 2) Startup Checklist

- `SECRET_KEY` is set and not default
- `DATABASE_URL` is set (production)
- migrations are applied
- logs directory is writable
- ML model artifacts are present

## 3) Backup/Restore Smoke

Run:

```bash
python tools/backup_restore_smoke.py
```

Result:
- `OK` means backup copy and restore connectivity check passed
- `SKIP` on non-sqlite environments is acceptable in CI smoke

## 4) Deployment Safety Gates

- Secret scan workflow passes
- Quality gate workflow passes
- Ops smoke workflow passes

## 5) Incident Quick Response

1. Put service in maintenance mode (if needed).
2. Rotate compromised credentials.
3. Validate auth/login and prediction endpoints.
4. Re-run smoke checks.
5. Publish incident timeline and corrective actions.

