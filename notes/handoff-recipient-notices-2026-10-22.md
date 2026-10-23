# Handoff 2026-10-22 — per-recipient receipt, early seal, copy link, notices

Four backend records designed with the owner on 2026-10-22. Implementation order agreed: TASK-068 → TASK-047 → TASK-069 → TASK-070 → notices (TASK-071, not written).

| Record | Branch / worktree | ADR | State |
|---|---|---|---|
| TASK-047 per-recipient sealed receipt | `feat/per-recipient-receipt` / `f5sign-backend-per-recipient-receipt` | ADR-0086 Proposed | committed + pushed (`01a971f4`, `c90c8135`) |
| TASK-069 early per-document seal (SEQUENTIAL_PADES, after agreement) | `feat/early-document-seal` / `f5sign-backend-early-document-seal` | ADR-0087 Proposed | committed + pushed (`34a6dde7`) |
| TASK-070 read-only copy link (closes BL-188) | `feat/copy-link` / `f5sign-backend-copy-link` | ADR-0088 Proposed | committed + pushed (`331aa0ce`) on 2026-10-23, owner-confirmed after spec-lint pass and claims check |
| TASK-071 per-recipient notices | — | ADR-0089 (to draft) | not written |

Root `.gitignore` has three uncommitted worktree lines (one per worktree above).

## TASK-070 changes since the owner confirmed its criteria (show as a diff before committing)

- TASK-047 is a prerequisite (receipt bars AC-4, AC-6f, S-1, S-2 wait for it).
- Ceiling check runs in Session use cases (Foundation cannot read Envelope's contract); a deleted custody reads 409.
- Retirement is by anchors (`invitationsRevokedAt` vs link `issued_at`; `credentialsRetiredAt` vs credential `gpa`).
- Copy gate: own aggregate + own use cases; reuses `OtpSendKeys`/limiter/`OneTimeCodeRequest` and the soft-lock tier (429 `AUTH_COOLING_DOWN`), never escalates to 423; owner chose a temporary self-releasing lock.
- AC-14 census over `RoleStanding` × the facts reads use (released informational members are minted; delegated, unclaimed, NOT_BUILT refused); guard lives in the mint service.
- New AC-9 (lock) and AC-17 (route/Authn/reader censuses); infra must inject `COPY_READ_CREDENTIAL_SECRET` (coordinated f5sign-infra PR).

## Owner decisions already taken for TASK-071 (the notices)

- Principle: a recipient whose part ends gets something complete and final at that moment.
- One final notice when, at their act, their receipt exists and all documents they sign are sealed (TASK-069); otherwise an act notice ("your signature is recorded; the process continues; you'll get everything when it completes") and a close notice. SINGLE_SEAL always two.
- Decliner: one notice, link opens only their receipt.
- Close notices (`ENVELOPE_COMPLETED`, `ENVELOPE_ENDED_*`) carry the copy link for those who signed and had no final notice yet, annulled outcomes included.
- Informational: `SEALED_COPY_READY` unchanged in who/when, moved to the copy link.
- Delivery by link on the recipient's declared channels (ADR-0077), email and SMS.
- Mechanism to settle in ADR-0089: Notification needs a fact for "receipt issued" (amends ADR-0086, which records none) and reacts to it and to `DOCUMENT_SEALED`; idempotent by `NotificationId::fromCause`.
