# Handoff 2026-10-22 — per-recipient receipt, early seal, copy link, notices

Four backend records designed with the owner on 2026-10-22. Implementation order agreed: TASK-068 → TASK-047 → TASK-069 → TASK-070 → notices (TASK-071, not written).

| Record | Branch / worktree | ADR | State |
|---|---|---|---|
| TASK-047 per-recipient sealed receipt | `feat/per-recipient-receipt` / `f5sign-backend-per-recipient-receipt` | ADR-0086 Proposed | committed + pushed (`01a971f4`, `c90c8135`) |
| TASK-069 early per-document seal (SEQUENTIAL_PADES, after agreement) | `feat/early-document-seal` / `f5sign-backend-early-document-seal` | ADR-0087 Proposed | committed + pushed (`34a6dde7`) |
| TASK-070 read-only copy link (closes BL-188) | `feat/copy-link` / `f5sign-backend-copy-link` | ADR-0088 Proposed | committed + pushed (`331aa0ce`) on 2026-10-23, owner-confirmed after spec-lint pass and claims check |
| TASK-071 per-recipient notices | `feat/recipient-notices` / `f5sign-backend-recipient-notices` | ADR-0089 Proposed | committed + pushed (`52591c2a`) on 2026-10-23, owner-confirmed; needs an f5sign-infra change (EvidenceAudit event queue + binding with DLX, `NOTIFICATION_COPY_BASE_URL`) in the same infra PR as TASK-070's secret |

## Launch order and test-lane priority (owner, 2026-10-23)

Run in parallel, with **TASK-047 first in the queue for the test lane** (the per-worktree `wt-backend` lane is
exclusive): a session working on any other of these tasks lets a TASK-047 run go ahead of its own runs and gates.

| Wave | In parallel | Starts when |
|---|---|---|
| 1 | TASK-047 (priority), TASK-068, TASK-069, and TASK-070 without its receipt part | now |
| 2 | TASK-070's receipt route and bars (AC-4, AC-6f, S-1, S-2) | TASK-047 on develop |
| 3 | TASK-071 | TASK-047, TASK-069 and TASK-070 on develop |

Merge order: 068 → 047 → 069 → 070 → 071. Conflict spots: `TrailAssembler` (047, 069),
`SigningReadersRefuseUnsentEnvelopeTest` (068, 070), `signed_copy: FINAL` (068, 069). TASK-068's ADR takes ADR-0090
or higher. Before deploying TASK-070: an `f5sign-infra` PR injecting `COPY_READ_CREDENTIAL_SECRET`.

Root `.gitignore` has three uncommitted worktree lines (one per worktree above).

## TASK-070 changes since the owner confirmed its criteria (show as a diff before committing)

- TASK-047 is a prerequisite (receipt bars AC-4, AC-6f, S-1, S-2 wait for it).
- Ceiling check runs in Session use cases (Foundation cannot read Envelope's contract); a deleted custody reads 409.
- Retirement is by anchors (`invitationsRevokedAt` vs link `issued_at`; `credentialsRetiredAt` vs credential `gpa`).
- Copy gate: own aggregate + own use cases; reuses `OtpSendKeys`/limiter/`OneTimeCodeRequest` and the soft-lock tier (429 `AUTH_COOLING_DOWN`), never escalates to 423; owner chose a temporary self-releasing lock.
- AC-14 census over `RoleStanding` × the facts reads use (released informational members are minted; delegated, unclaimed, NOT_BUILT refused); guard lives in the mint service.
- New AC-9 (lock) and AC-17 (route/Authn/reader censuses); infra must inject `COPY_READ_CREDENTIAL_SECRET` (coordinated f5sign-infra PR).

## Owner decisions for TASK-071 (now written; kept for context)

- Principle: a recipient whose part ends gets something complete and final at that moment.
- One final notice when, at their act, their receipt exists and all documents they sign are sealed (TASK-069); otherwise an act notice ("your signature is recorded; the process continues; you'll get everything when it completes") and a close notice. SINGLE_SEAL always two.
- Decliner: one notice, link opens only their receipt.
- Close notices (`ENVELOPE_COMPLETED`, `ENVELOPE_ENDED_*`) carry the copy link for those who signed and had no final notice yet, annulled outcomes included.
- Informational: `SEALED_COPY_READY` unchanged in who/when, moved to the copy link.
- Delivery by link on the recipient's declared channels (ADR-0077), email and SMS.
- Mechanism to settle in ADR-0089: Notification needs a fact for "receipt issued" (amends ADR-0086, which records none) and reacts to it and to `DOCUMENT_SEALED`; idempotent by `NotificationId::fromCause`.

## 2026-10-23 additions

- Delegated recipients are treated like everyone else (copy link minted, notices of their position, copy-ready included); TASK-070's census was amended by its session.
- A signer of an annulled envelope gets one ending notice, after the seal, with the copy link.
- "Final" = every document the recipient can see is sealed or requested for an early seal in the same call.
- Sessions running: cc = TASK-047 (lane priority), a6 = TASK-068, 08 = TASK-069, 31 = TASK-070.

## Open for TASK-071 before its launch (from the TASK-069 session, 2026-10-23)

With TASK-068 and TASK-069 both in, a signer whose documents are sealed early downloads the sealed revision at once,
but their `signed_copy` reads `CONTAINS_YOUR_SIGNATURE`, not `FINAL`, until the envelope completes: ADR-0090 §2.2
keys `FINAL` on `completedAt` (`SignedCopy::of()`). Owner decision 2026-10-23: TASK-069 leaves it; TASK-071 decides
the "your copy is final" signal. TASK-071's record says its notices must not contradict the signer's screen, so its
final notice (sent at the early seal) would contradict `CONTAINS_YOUR_SIGNATURE`. To settle with the owner before
TASK-071 runs: amend ADR-0090 §2.2 / `SignedCopy::of()` so `FINAL` uses TASK-071's own "final" (every document the
recipient can see is sealed), or keep `FINAL` at completion and word the notice to match. TASK-069 adds a BACKLOG
row pointing here (BL-465 or above).

Owner decision 2026-10-23 (option A): `FINAL` takes TASK-071's meaning. TASK-071 amends ADR-0090 §2.2 and
`SignedCopy::of()` so a recipient's copy reads `FINAL` once every document they can see is sealed, early seal
included, not only at `completedAt`; TASK-071's record and ADR-0089 take that amendment into their scope.
