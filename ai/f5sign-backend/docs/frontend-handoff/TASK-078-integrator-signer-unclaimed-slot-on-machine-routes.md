# Handoff to the integrator and the signer: the machine routes refuse a slot nobody has claimed

| | |
|---|---|
| **Origin** | branch `fix/unclaimed-slot-on-machine-routes` · TASK-078 |
| **Date** | 2026-11-04 |
| **Repos affected** | **integrator (machine key)**, **signer** |
| **Nature** | a state that was admitted is now refused; no route, body or new code (`RECIPIENT_SLOT_NOT_CLAIMED` already existed on the token mint, the copy link, the correction and the resend) |
| **Required action** | integrator: claim a slot before driving these routes. signer: none |
| **Deployed** | not yet |
| **Status** | Pending |

Read from the routes' `#[OA\*]` attributes and `config/routes/api/`, not from the plan. Where this file and the spec
differ, the spec wins.

## 1. The three answers, on a claimable slot nobody has claimed

| Route | Before | Now |
|---|---|---|
| `POST /api/v1/envelopes/{id}/recipients/{recipientId}/auth/otp/send` | 409 `AUTH_NO_DESTINATION` with no contact, 200 `minted: true` with one; the recipient was recorded as opened | 409 `RECIPIENT_SLOT_NOT_CLAIMED`; no session is opened, nothing is sent or charged, and this call records no opening |
| `POST /api/v1/envelopes/{id}/recipients/{recipientId}/auth` | 401 `AUTH_NO_OPEN_CHALLENGE` with no code open, 200 with a credential pair on a correct code; recorded as opened | 409 `RECIPIENT_SLOT_NOT_CLAIMED`; no session is opened, this call records no opening and spends no attempt |
| `POST /api/v1/envelopes/{id}/recipients/{recipientId}/signature` | 204 on a `MACHINE_KEY` slot, signed unclaimed; 404 for a relayed act with no session | 409 `RECIPIENT_SLOT_NOT_CLAIMED`; nothing is signed and this call opens no session |

- "This call records no opening" is all that is stated: a slot that an earlier call already stamped keeps that stamp.
  Nothing here repairs or counts such rows.
- Because no opening is recorded, a refusal does not stop the slot's gates being changed afterwards; that route's other
  refusals still apply (`RECIPIENT_HAS_NO_GATES` on a `MACHINE_KEY` slot, `RECIPIENT_ALREADY_ENTERED` on a slot already
  stamped).
- A session credential pair this submit route returned on a slot before this change, on a correct code, is not
  withdrawn: renew, commit and decline do not ask the slot question, so the pair lasts at most until the session's
  twelve-hour cap and its last access credential's fifteen minutes.

## 2. What keeps its answer, and when the code can be cured

- A closed envelope still answers `ENVELOPE_NO_LONGER_LIVE`; a released slot still answers `LEG_CLOSED`. The signature
  route's call with no `asserted_subject` on a `SIGNING_PLATFORM` slot with no session keeps its 404 instead.
- On the signature route `ASSERTION_NOT_ACCEPTED` (a `SIGNING_PLATFORM` slot sending `asserted_subject`) and
  `ASSERTION_REQUIRED` (a `MACHINE_KEY` slot with no whole assertion) answer first. Asserted members sent without
  `asserted_subject`, on a `SIGNING_PLATFORM` slot with no session, get `RECIPIENT_SLOT_NOT_CLAIMED` instead.
- On a slot that is both unclaimed and on a step not yet reached, the answer is `RECIPIENT_SLOT_NOT_CLAIMED`, not
  `STEP_NOT_ACTIVE`.
- `PUT /api/v1/envelopes/{id}/recipients/{recipientId}/auth` stays open on an unclaimed slot.
- Claimed slots and named recipients see no change.

⚠ **The code does not say the claim is still possible.** Claim the slot with
`POST /api/v1/envelopes/{id}/recipients/{recipientId}/claim` and call again; calling again without claiming cannot
help. But an informational slot (VIEWER, REVIEWER, EDITOR) keeps getting the code after its step or the envelope has
ended, and where the claim is refused because the recipient's part, their step or the envelope is over, the code never
lifts: stop. On the signature route, claiming also cannot cure it once the slot's step has completed or reached its
deadline, and an informational slot never commits there, claimed or not.

## 3. Integrator

Read on 2026-11-04; nothing here tests the dashboard's repo. From what we read of your dashboard no call reaches this:
you call the signature route for `CARGADOR`, a named `MACHINE_KEY` recipient, and `PUT .../auth` before the claim,
which stays open. Your `F5SignErrorMessages` maps `slot_not_claimed` to text about assigning the recipient before
generating their link; none of your calls can now receive it from these routes, so nothing changes unless you start
calling them on a slot.

## 4. Signer

Read on 2026-11-04; nothing here tests the signer's repo. None: you call the token twins, and an unclaimed slot gets no
token. `openapi-snapshot.json` lists no machine route.
