# Healthcare Compliance Checklist (Project-Level)

This checklist is for engineering readiness and does not replace legal/compliance review.

## Data Protection

- [ ] `.env` and secrets are not tracked in git
- [ ] encryption keys are managed outside source control
- [ ] production data backups are encrypted
- [ ] least-privilege DB access is enforced

## Access Control

- [ ] role-based access is verified per route
- [ ] admin actions are logged
- [ ] stale sessions/tokens can be revoked
- [ ] MFA is enabled for privileged users (recommended)

## Auditability

- [ ] prediction actions are auditable (who/when/what)
- [ ] lab, diagnosis, and review actions are auditable
- [ ] notification events are traceable
- [ ] audit logs are retained and protected

## Clinical Safety

- [ ] AI output is presented as decision support, not final diagnosis
- [ ] doctor review status is available to patient
- [ ] high-risk results have clear escalation paths
- [ ] model updates follow documented approval process

## Operational Readiness

- [ ] CI security scans pass
- [ ] CI quality gate passes
- [ ] backup/restore smoke checks pass
- [ ] incident response procedure is documented

