# contract-check-frontend — ADR-0073 package (TASK-048/049/050/051)

**Status:** PASS (after fixes)
**Tags evaluated:** api
**Issues:** 0 blocking, 2 warnings
**Contract:** `notes/adr-0073/doc.json`, backend `develop` e6a0af5e (tree e978346c), sha256 a805bb3f…
**Harness:** `make -C ../f5sign-infra wt-signer src=<worktree>` — lint 0 errors / 24 warnings, typecheck 0, 3543 passed / 5 skipped, coverage 91.3 / 85.6 / 92.0 / 93.2 %.

## Fixed during the check
- [types-outdated] `check-contract.mjs` LEG_OUTCOME lacked `RELEASED` → 1 break against the real spec. Added; `envelope_outcome` now checked on `/auth` and `GET /signing/session` (99 properties, 0 breaks).
- [types-outdated] `envelope_outcome` was optional in `types.ts`; published REQUIRED + nullable on both routes. Made required; 17 JSON fixtures gain `"envelope_outcome": null`.
- [error-unhandled] 503 `ENVELOPE_BUSY` on commit/decline was shown as a failure with a manual retry; the contract publishes `Retry-After` and says showing it as a failure "is showing the wrong thing". Adapter now repeats the same act after `Retry-After` (2 retries, wait capped at 10 s).
- [error-ux] `ENVELOPE_NO_LONGER_LIVE` on `/declined` did not ask `/auth` how it ended (TASK-050 §H); a member released by an AGREED close now sees the released screen.
- [copy] `sealPendingSubtitle` said "se anuló"; `SEAL_PENDING` now covers both outcomes.

## Warnings
- [adhoc-types] No OpenAPI→TS generation: `types.ts` is hand-written, guarded by `check-contract.mjs` + `openapi-snapshot.json` + fixture conformance.
- [legacy-codes] 12 codes in `errorCodeToPath` are not in the published `ProblemCode` (mock/legacy, pre-existing, documented in its header).

## Endpoints consumed
- POST /signing/session — LEG_CLOSED ✓, ENVELOPE_NO_LONGER_LIVE ✓, status 5 values ✓
- GET /signing/session/auth — outcome +RELEASED ✓, envelope_outcome ✓, `/copy` routing ✓
- POST /signing/session/auth/otp/send, POST /signing/session/auth — 409 LEG_CLOSED / ENVELOPE_NO_LONGER_LIVE routed (useAuthChallenge, useAccessCodeAuth) ✓
- GET /signing/session — LEG_CLOSED ✓, SEAL_PENDING ✓, envelope_outcome ✓
- POST /signing/commit — COMMIT_NOT_OFFERED_TO_ROLE ✓, LEG_CLOSED ✓, ENVELOPE_BUSY ✓ (retry)
- POST /signing/decline — DECLINE_NOT_OFFERED_IN_QUORUM_STEP removed ✓, LEG_CLOSED ✓, ENVELOPE_BUSY ✓ (retry)
- POST /signing/session/renew — bare 401 → existing reopen/relink path ✓

## Events listened to
- (none)

## Tag mismatches
- none
