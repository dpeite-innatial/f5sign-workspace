# security-audit — TASK-047

**Status:** WARN
**Total issues:** 0 blocking, 5 warnings
**Delegations:** security-audit-backend (warn); eidas-compliance (not delegated, see below)
**Validation basis:** static read of the worktree; no tests run. last_green_run cited from the orchestrator: sha 1404641b, 8403 tests, wt-backend lane (its log, /tmp/tmp.oYP13m9v89.log, was not present when checked, so it was not re-read). HEAD is f3bc315a, which differs from 1404641b only by two lines in tests/F5Sign/Integration/StorageLifecycleScenarioTest.php, so the green run covers the src tip.

## Core issues
- [dependencies] `composer audit` output was not provided and was not run (needs network). Dependency state is undeclared, not clean. The diff changes neither composer.json nor composer.lock.
- [headers] Both new PDF routes lack `X-Content-Type-Options: nosniff` (repo-wide gap, nothing in src/ or config/). Content-Type is a server constant and the disposition is attachment, so practical risk is low (warn).
- [PII at rest] The sealed receipt (PDF and attached JSON) holds the recipient's name, IP, User-Agent, Accept-Language and asserted identity in clear. ADR-0033 is not enforced (same posture as the audit trail). `evidence_audit.issued_receipt` itself has no PII column (warn, per the audit rule on PII at rest).

## security-audit-backend
See security-audit-backend.report.md. 0 blocking, 4 warnings: no nosniff; PII at rest; retirement comparison duplicated inline in `GetSessionReceiptHandler` instead of `RecipientAuthContext::retires()` (and `recipientCouldPassTheGate()` not asked; equal today); rejection tests for the session route (retired credential, closed envelope) exist only at handler level, not HTTP, and the machine route's cross-tenant test runs on one connection (isolation comes from RLS plus the derived id, which that test cannot separate).

Verified fine: both routes declare their credential (MACHINE_KEY, SESSION_CREDENTIAL), no identity header read; the session route takes envelope and recipient only from verified claims; liveness checks (unsent, retired, withheld/closed, step not reached) all give one 404 before the 409 NOT_READY, so no state disclosure; machine route gives one 404 for unknown, foreign tenant, other recipient, not issued; UUID-validated ids, so the filename is safe; all SQL bound; issued_receipt has ENABLE+FORCE RLS, policy, tenant trigger; both SECURITY DEFINER functions have pinned search_path ending in pg_temp, NOLOGIN owner, EXECUTE revoked from PUBLIC and granted to f5sign_app only; the custodian has a column grant (tenant_id, conserved_at) and a SELECT policy limited to conserved_at IS NULL; the sentinel tenant set_config is transaction-local and restored (same pattern as the existing funnels); the edit to the published Version20260922000002 is docblock-only; Typst runs with an argument array, empty environment, timeout, 0700 random job dir removed in finally, --root on the job dir, and data passed as JSON (no markup interpolation; the template has no eval/raw/import); the receipt covers one recipient (others appear only as a count and chain root); no PII in logs or events.

## eidas-compliance
Not delegated. Decision: the diff touches no SignatureExecution internals, Foundation/Crypto, DSS adapters or PAdES parameters. The receipt is sealed through `SignatureExecution\Contract\Service\PdfSealer` exactly as the existing audit trail is (`IssueAuditTrailUseCase`, path without `fieldId`), and reads back through `SignatureReadBack`. The signature level, digest enum, format and WORM custody order are unchanged. No eIDAS property is altered, so a delegation would return green by vacuity. Caveat: the receipt's seal is the platform's PAdES B-B seal, not a signer signature; whether a "sealed receipt" carries any qualified-signature claim is a product wording matter outside this gate.

## Categories reviewed
- Secrets: OK (none in the diff; Dockerfile and evidence_audit.yaml are comments and a template-path parameter)
- PII: WARN (at rest, ADR-0033; none in logs, URLs or events)
- Auth/Authz: OK
- Multi-tenant: OK (RLS and derived id; test strength noted as a warn)
- Dependencies: not run (undeclared)
