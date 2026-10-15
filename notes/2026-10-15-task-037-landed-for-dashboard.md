# TASK-037 landed on backend develop — for the factor5-dashboard session

Backend `develop` at `cf8fc9b9` (pushed 2026-10-15). Merged, not deployed.

- **A claim on an already-active step now invites the named party**, exactly once, on the channels they declared
  (`RecipientClaimed` → `NotifyClaimedRecipientUseCase`, sharing the activation's cause token). Repeat the claimable
  e2e (the `["EMAIL","SMS"]` + `IN_ORDER` slot) without a manual resend. A claim on a dormant step sends nothing until
  the step opens; closed, delegated and unclaimed recipients are never invited by it.
- **Read model, additive**: `recipients[]` of `GET /api/v1/envelopes/{id}` gains `declared_claimable` (bool) and
  `claimed_at` (ISO-8601 or null). The wait is `declared_claimable === true && claimed_at === null`. Do not branch on
  `declared_claimable` alone, nor infer a slot from `invitation_state: null`.
- Handoff (Spanish): `f5sign-backend/docs/frontend-handoff/TASK-037-dashboard-integrator-claimable-wait.md`.
- The dev stack's workers were restarted after the merge and wire the new handler.
