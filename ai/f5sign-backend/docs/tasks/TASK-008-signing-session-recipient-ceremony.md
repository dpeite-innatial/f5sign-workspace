# TASK-008 — Signing-workflow Phase B (MVP): the recipient signing ceremony + token-auth edge

| Field | Value |
|-------|-------|
| **Status** | **Implemented 2026-06-23** (review polish 2026-06-25) — `make qa` green (PHPStan L9 · Deptrac **0** · lint · full suite) incl. a live end-to-end test where a real recipient signature drives the envelope to `COMPLETED` vs MinIO + `eu-dss` + the relay/consume path. Decision record: [ADR-0028](../adr/ADR-0028-recipient-signing-token-auth.md). |
| **Type** | **As-built record** — the ROADMAP "Signing-workflow wiring" **Phase B (MVP slice)**. Documented after the build; the body records what landed. |
| **Builds on** | [TASK-007](TASK-007-signing-workflow-seal-loop.md) (Phase A: the seal loop + the event consume side this feeds), [TASK-004](TASK-004-envelope-http-exposure.md) (the HTTP edge + controller conventions), and the [ADR-0024](../adr/ADR-0024-event-delivery-transactional-outbox.md) outbox (whose consume side carries `SessionCompleted`). |
| **Delivery bar** | A token-authenticated recipient **opens + signs** a session over HTTP with only `Authorization: Bearer <token>` (no tenant/user headers), and that real signature drives the envelope **create → send → sign → seal → COMPLETED** through the relay/consume workers. |
| **Auth** | **Bearer signing token** (MVP HMAC) — the first public, token-authenticated edge; tenant + recipient derived server-side, RLS-from-token. Replaces header-stub for the recipient surface; sender surface stays header-stub. |
| **Naming** | `F5Sign\` throughout. The BC namespace is `F5Sign\Session\` (the deptrac-scaffolded name); the aggregate is `SigningSession`. |

---

## 1. Why this task exists

After Phase A (TASK-007) the *sender* half closed end-to-end, but only via `MockSign` — the **Signing Session BC had zero source files** and every route trusted a stub `X-Tenant-Id` header a public signer cannot send. Phase B builds the recipient half: how a real signer reaches the platform and produces the per-recipient completion that feeds the existing seal loop. Per the source-of-truth direction, the design lives in [ADR-0028](../adr/ADR-0028-recipient-signing-token-auth.md) + the in-repo [domain-model doc](../ddd/signing-session-domain-model.md) rather than a design-repo tech-doc.

## 2. What was built

**The Signing Session BC (MVP slice)** under `src/F5Sign/Session/` — Contract / Domain / Application / Infrastructure / UI, mirroring the Envelope BC layering:
- `SigningSession` aggregate: `start` → `commitSignature` (DIRECT_LINK auth; click-to-sign captures consent + signer IP/UA on the row); `SessionStatus` (INITIATED/AUTH_PASSED/COMPLETED); the `SessionCompleted` domain event; ACL mirrors `EnvelopeRef`/`RecipientRef`.
- `StartSession` / `CommitSignature` commands + use-cases + Messenger handlers; `DoctrineSigningSessionRepository` + ORM mapping + the `domain.signing_session` migration (FORCE-RLS, ADR-0017).
- **Deterministic id** — `SigningSessionId::fromScope()` is the UUIDv5 of `(tenant, envelope, recipient)`, so the PK *is* the "one session per recipient" invariant (`UuidGenerator` gained a dependency-free `v5`).

**The token-auth edge** (Foundation): `SigningTokenCodec` (stateless HMAC-signed `(tenant, envelope, recipient, exp)` token, verified with no DB read) + `SigningTokenListener` (verifies the bearer token, sets `TenantContext` + the RLS GUC, 401 fail-closed) + a `TOKEN_SCOPED_PREFIXES` carve-out in `TenantRequestListener` (the second narrowing of ADR-0021's gate; that constant has since been deleted in favour of a per-route declaration — see `docs/adr/ADR-0048-route-declared-authentication-seam.md`).

**The HTTP surface** (`Session/UI/Http/` + `config/routes/api/signing.php`): `POST /api/v1/signing-tokens` (sender, tenant-scoped — mint a token), `POST /api/v1/signing/session` (recipient — open), `POST /api/v1/signing/commit` (recipient — sign), each with `#[OA\*]` (ADR-0026 coverage).

**The handoff** (Envelope): a new `OnSessionCompleted` reactor translates `SessionCompleted` → the existing `RecordRecipientCompletion` → the Phase-A seal loop. **Signature Execution is untouched.**

**Infra**: `queue.session.events` + an `App.Session.Event.#` binding (rabbitmq `definitions.json` + `messenger.yaml`); `SIGNING_TOKEN_SECRET` in `.env`.

## 3. Scope

**In scope (built):** the Session BC MVP (aggregate `start`/`commitSignature`, commands, persistence, deterministic id); the stateless token codec + the token-auth listener + the carve-out; the three HTTP routes; the Envelope `OnSessionCompleted` reactor; the infra event binding; ADR-0028 + the ADR-README + domain-model crosswalk updates; tests (aggregate unit, codec unit, HTTP ceremony, the full live signing-loop).

**Out of scope (deferred — named so they're not silently dropped):**
- **Richer auth methods** — access-code / OTP / FIDO / biometric, and the `AUTH_PENDING`/`AWAITING_REAUTH` states; **decline / expiry / re-auth**. The `SessionStatus` enum + aggregate grow non-breakingly.
- **E&A evidence handoff** — consent + signer IP/UA are captured on the session row, not yet shipped to Evidence & Audit's `EvidenceCollector`.
- **Write-path domain-exception → HTTP mapping** — `commitSignature` guards (already-signed → should be 409, not-authenticated) threw domain exceptions that surfaced as **500** (the pre-existing gap, TASK-007). → **since resolved** by [ADR-0029](../adr/ADR-0029-domain-exception-http-mapping.md): the kernel `DomainException` family (NotFound/Conflict/InvariantViolation) maps to 404/409/422 at the edge. The wire-shape consent guard (missing/false consent → 422) works at the DTO edge.
- **MVP token primitive** — symmetric HMAC, single secret, no revocation. → **The replacement is decided, and it is not lexik JWT** as this line originally said: [ADR-0050](../adr/ADR-0050-session-credential-jwt-and-refresh.md) converts the token to **opaque and store-backed** under [ADR-0045](../adr/ADR-0045-issued-credential-format.md)'s grammar, because it travels by email ([TASK-028](TASK-028-opaque-signing-token.md)). The mint endpoint does not yet verify the envelope/recipient exist (RLS + downstream guards bound the blast radius).
- **`BatchSigningSession`, offline sessions, the internal entities** (`AuthAttempt`/`ConsentRecord`/`FieldsDraft`/…), and a **real per-recipient SE aggregate** (the v2 insertion point is an SE reactor on `SessionCompleted`, ahead of the Envelope one).
- **Dev-DB migration** — `domain.signing_session` is applied to the test DB (suite green); the running dev postgres volume predates the `f5sign_relay` role, so a full dev migrate needs a re-provision (pre-existing infra gap, not this slice).

## 4. Key decisions

- **D2 handoff (Session → Envelope directly), SE untouched** — over routing through SE (D1). A kernel `Reactor` may dispatch only one command, so D1 would need a new SE command + use-case + adapters and touch SE; `RecordRecipientCompletion` needs no per-recipient signed artifact (right for MVP — recipient signing is evidence, not crypto), so the recipient's signing-act reference is the session's own id. `SessionCompleted` is the clean seam where real per-recipient SE signing attaches in v2. *(User-flagged; built as D2.)*
- **Stateless HMAC token** — resolves the RLS chicken-and-egg (tenant scope must be set before any tenant-scoped query, with no DB read). MVP-grade. ⚑ **The chicken-and-egg this decision worked around is no longer a constraint**: `DbalApiKeyDirectory` performs that lookup with no tenant scope set, against deliberately RLS-free tables ([ADR-0044](../adr/ADR-0044-principal-resolution-at-the-edge.md)'s explicitly-exempt-lookup limb). Correct when decided; dissolved by the machine half. See [ADR-0050](../adr/ADR-0050-session-credential-jwt-and-refresh.md) §1.1.
- **Deterministic session id** — makes the scoping invariant a structural PK guarantee + removes any read-after-write; the commit endpoint derives the id from the token (no client-supplied id → no cross-recipient access).
- **No design-repo tech-doc** — Phase B's design lives in ADR-0028 + the in-repo domain-model doc, per the agent-only source-of-truth direction. *(User's call.)*
