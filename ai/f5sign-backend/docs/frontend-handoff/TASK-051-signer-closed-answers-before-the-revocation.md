# Frontend handoff — a closed envelope or leg answers the same before and after the revocation

| | |
|---|---|
| **Origin** | branch `feat/envelope-answers-first` · [ADR-0074](../adr/ADR-0074-a-closed-envelope-or-leg-answers-before-the-session.md) (`Accepted`, §2.5 amended 2026-09-29) · [TASK-051](../tasks/TASK-051-closed-answers-do-not-wait-for-the-revocation.md) |
| **Date** | 2026-09-29 |
| **Repos affected** | **signer**; `/v1` integrators on the machine twins of the two gate routes and the delegated commit |
| **Nature** | **Changes which code a route answers; no catalog change.** Every code that changes on a route changes to one whose published remedy is the same (*stop; nothing was done; do not retry*). One status moves: on the two gate routes a closed envelope or leg met after the revocation moves from 401 to 409. `LEG_CLOSED` is new on the gate routes. |
| **Action required** | Handle 409 `LEG_CLOSED` on `POST /api/v1/signing/session/auth/otp/send` and `POST /api/v1/signing/session/auth` as on the commit and the decline. Do not rely on 401 `AUTH_NO_OPEN_CHALLENGE` on those routes to learn that an envelope ended. |
| **Deployed** | not yet — not merged into `develop`; lands after the ADR-0073 package |
| **Status** | Pending |

## Lo que cambió en el contrato

The code a recipient act receives on a closed envelope or a closed leg no longer depends on whether the
Session revocation of their session (a reaction that rides the relay) has run. Before, the same act got one
code before the revocation and another after it.

| Route | Situation | Before | Now |
|---|---|---|---|
| `POST /api/v1/signing/commit`, `POST /api/v1/signing/decline`, `POST /api/v1/envelopes/{id}/recipients/{recipientId}/signature` | envelope closed, session already revoked | 409 `SESSION_CLOSED` | 409 `ENVELOPE_NO_LONGER_LIVE`, as before the revocation |
| same | leg released on an open envelope, session already revoked | 409 `SESSION_CLOSED` | 409 `LEG_CLOSED`, as before the revocation |
| same | idled session (`AWAITING_REAUTH`) on a closed envelope or leg | 401 `AUTH_REAUTH_REQUIRED` | 409 `ENVELOPE_NO_LONGER_LIVE` / `LEG_CLOSED` |
| same | step deadline passed, not yet swept, and it ends the envelope | 409 `LEG_CLOSED` | 409 `ENVELOPE_NO_LONGER_LIVE` |
| same | step deadline passed, not yet swept, the envelope goes on | 409 `LEG_CLOSED` | unchanged |
| `POST /api/v1/signing/session/auth/otp/send`, `POST /api/v1/signing/session/auth` and their machine twins `…/recipients/{recipientId}/auth/otp/send`, `…/recipients/{recipientId}/auth` | envelope closed, session already revoked | **401** `AUTH_NO_OPEN_CHALLENGE` | **409** `ENVELOPE_NO_LONGER_LIVE` |
| same | leg released on an open envelope, session live | 409 `ENVELOPE_NO_LONGER_LIVE` (false: the envelope was live) | 409 **`LEG_CLOSED`** |
| same | leg released on an open envelope, session already revoked | **401** `AUTH_NO_OPEN_CHALLENGE` | **409** `LEG_CLOSED` |
| same | the recipient already signed or declined | 401 `AUTH_NO_OPEN_CHALLENGE` | unchanged |
| commit, decline | an informational member (`VIEWER`, `REVIEWER`, `EDITOR`) acts past their step's deadline, before the sweep | 409 `LEG_CLOSED` | 409 `COMMIT_NOT_OFFERED_TO_ROLE` / `DECLINE_NOT_OFFERED_TO_ROLE`, as after the sweep |
| same | an informational member acts on a step already closed (swept, or completed), envelope open | 409 `STEP_NOT_ACTIVE` | 409 `COMMIT_NOT_OFFERED_TO_ROLE` / `DECLINE_NOT_OFFERED_TO_ROLE` |

- **`SESSION_CLOSED` is narrowed**: the session ended without the recipient acting **while the envelope and their
  leg are still open**. No production path produces it today; it stays in the catalog for a future cause. On the two
  gate routes it is never the answer: a session that is over is the 401 `AUTH_NO_OPEN_CHALLENGE`, and
  `SESSION_ALREADY_COMPLETED`, `SESSION_ALREADY_DECLINED` and `SESSION_CLOSED` reach them only when the session closes
  between two reads of one request.
- On the gate routes, `ENVELOPE_NO_LONGER_LIVE` and `LEG_CLOSED` send no code, charge nothing and spend no attempt.
- **An informational member's role answers ahead of the step and the deadline** (maintainer, 2026-09-29): the sweep
  does not release their leg, so the role refusal is the answer on both sides of it. A deadline that ends the envelope
  still answers `ENVELOPE_NO_LONGER_LIVE` first.
- Published text also updated: the OTP send's 401 now says a session that is over lands there, `recover: true`
  included; the decline's `AUTH_REAUTH_REQUIRED` says a closed envelope or leg answers the 409 first; `SESSION_CLOSED`
  on the three act routes says it is not produced today.
- Unchanged: the open, the auth descriptor, the read model, the document download and the renewal.

## Lo que el frontal tiene que hacer

1. Map 409 `LEG_CLOSED` on the two gate routes to the screen the commit and the decline already use for it.
2. Keep 401 `AUTH_NO_OPEN_CHALLENGE` on those routes for *nothing is left to prove* (signed, declined, or no gate
   open), not for a cancelled envelope.
3. An idled session on a closed envelope or leg no longer asks to re-authenticate: make sure the re-auth screen is
   not the only path for that state.
4. No change on the commit and the decline beyond knowing that `SESSION_CLOSED` no longer stands for a released leg.

## Release order

**Backend first is safe**: no code moves to one with a different remedy, and an unmapped `LEG_CLOSED` on the gate
routes falls to the unknown-code branch, which the spec tells clients to read as *stop*. Check before the backend
deploys that the signer does not report a 409 on the two gate routes as an unexpected error; if it does, ship both
together.

## Cómo verificarlo desde el frontal

`doc.json` of the deployment: the 409 blocks of the seven routes above describe the new answers; `ProblemCode`
is unchanged. The backend pins the table in
`tests/F5Sign/Session/Acceptance/ClosedAnswersDoNotWaitForTheRevocationHttpTest.php`.
