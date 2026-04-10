# Security Policy

## Supported Security Baseline

This project targets healthcare-grade handling of sensitive data. The following controls are expected in production:

- secrets managed outside git (`.env` is local only)
- strict production `SECRET_KEY` and database credentials
- secure cookies and TLS transport
- audit logs for clinical and admin actions
- periodic dependency and secret scanning in CI

## Reporting a Vulnerability

If you discover a security issue:

1. Do not open a public issue with exploit details.
2. Share a private report with:
   - impact summary
   - affected component(s)
   - reproduction steps
   - suggested remediation (if available)
3. Include urgency level:
   - Critical: active exploit, PHI exposure, auth bypass
   - High: privilege escalation, sensitive data leakage
   - Medium: security misconfiguration
   - Low: defense-in-depth improvements

## Secret Handling Rules

- Never commit `.env`, keys, certs, or raw credentials.
- Rotate compromised credentials immediately.
- Use a vault/KMS in production where possible.
- Revoke old credentials after rotation.

## Incident Response (Minimum)

- Identify and contain affected service.
- Rotate exposed secrets.
- Review access logs and notification records.
- Restore service with patched configuration.
- Document root cause and preventive action.

