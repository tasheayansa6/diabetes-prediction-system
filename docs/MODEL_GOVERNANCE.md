# Model Governance and Clinical Review

## Purpose

Define minimum controls for safe ML use in clinical workflow.

## Release Requirements

- Training dataset version documented
- Model metrics documented (accuracy, precision, recall, F1)
- Bias and data-quality checks recorded
- Clinical sign-off for production deployment

## Runtime Controls

- Every prediction has timestamp and input snapshot
- High-risk outputs trigger clinical follow-up workflow
- Doctor review status is visible to patient (`pending_review`, `approved`, `rejected`, `needs_followup`)

## Monitoring

- Track prediction volume by risk level
- Track review turnaround time by doctor
- Track disagreement rate between model recommendation and clinical review

## Rollback Plan

If model degradation or safety incident is detected:

1. Freeze new model rollout.
2. Switch to last known stable model.
3. Notify clinical admins and engineering.
4. Re-run validation before re-enabling new model.

