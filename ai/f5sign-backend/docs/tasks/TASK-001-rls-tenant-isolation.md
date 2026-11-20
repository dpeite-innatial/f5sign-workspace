# TASK-001 — RLS tenant-isolation backstop (Envelope)

| Field | Value |
|-------|-------|
| **Status** | Implemented 2026-06-08 — **RLS enforced in runtime + tests** (app connects as a non-superuser role; tests exercise the production invariant). `make qa` green. See [§10 Implementation outcome](#10-implementation-outcome-2026-06-08). |
| **Type** | Agent-delegable implementation task |
| **Exercises** | [ADR-0017](../adr/ADR-0017-tenant-isolation-rls-persistence-contract.md) (the tenant-isolation persistence contract this realizes) + [ADR-0010](../adr/ADR-0010-command-bus-middleware-spine.md) Rule 1 (#2 `SetTenantId`) + Rule 4 (fail-closed RLS, system branch *deferred*) |
| **Closes** | The cross-tenant-isolation gap (the system's named #1 catastrophic risk) for the realized Envelope read/write paths |
| **Delivery bar** | Green `make qa` (PHPStan L9 + Deptrac + PHPUnit) run via the infra Makefile |

---

## 1. Why this task exists (self-contained context)

Tenant leakage — one tenant reading or writing another tenant's data — is the platform's **#1 catastrophic-failure mode**. Two mechanisms are meant to defend it:

1. **Explicit `TenantId`** — every command/query/aggregate carries the tenant as a parameter. **This is already built** and threaded through Envelope.
2. **Ambient RLS** — Postgres Row-Level-Security policies read a session variable and filter every row at the database, so a bug that forgets the explicit filter still can't leak across tenants. **This does not exist** — there are no `CREATE POLICY` / `FORCE ROW LEVEL SECURITY` statements anywhere, no carrier for "current tenant," and no middleware to set it. The defense we call paramount is neither built nor tested.

This task builds mechanism 2 for the `domain.envelope` aggregate and locks it with a cross-tenant isolation test. It is the substrate the queued isolation test in [`tests/README.md`](../../tests/README.md) was blocked on.

Read before starting: [ADR-0010](../adr/ADR-0010-command-bus-middleware-spine.md) (the middleware-order + transactional-boundary contract this realizes), and the "Tenant scoping & RLS" section of [`docs/ddd/identity-access-domain-model.md`](../ddd/identity-access-domain-model.md) (the decided model). Per repo rule #7, an ADR governs this change — do not contradict ADR-0010 silently.

## 2. What already exists (do not rebuild)

| Thing | Where | Use it |
|-------|-------|--------|
| `tenant_id UUID NOT NULL` column on the root table | `domain.envelope` (migration `Version20260504000001`, since consolidated into the `Version20260713` baseline) | RLS policy filters on it |
| `TenantId` value object | [`Foundation/Identity/TenantId.php`](../../src/F5Sign/Foundation/Identity/TenantId.php) | the typed tenant id |
| `TenantIdType` Doctrine type | `Foundation/Persistence/Doctrine/Type/TenantIdType.php` (retired with the ORM — ADR-0018) | persistence mapping |
| Explicit tenant on commands | e.g. `CreateEnvelope` has `public TenantId $tenantId` | the middleware keys off it |
| Native bus middleware order | [`config/packages/messenger.yaml`](../../config/packages/messenger.yaml) — `validation → doctrine_transaction` | insert `SetTenantId` ahead of these |

## 3. Scope

**In scope** — the minimal end-to-end RLS backstop for Envelope:

1. **DB migration** — enable + FORCE RLS on `domain.envelope`, a fail-closed `current_tenant_id()` function, and the isolation policy.
2. **`TenantContext`** (Foundation) — request-scoped carrier of the current `TenantId` + applier that sets the Postgres session variable.
3. **`SetTenantId` command-bus middleware** (Foundation/Bus) — sets the scope before the transaction, resets in `finally`.
4. **RLS-aware integration test base** + the **cross-tenant isolation test**.
5. **Update the existing DB-touching Envelope tests** so they establish tenant context (see §7 — FORCE RLS will break them otherwise).

**Out of scope — deferred and recorded, do NOT build here:**

- **Child-table RLS.** Only `domain.envelope` carries `tenant_id`; `document`, `document_artifact`, `step`, `recipient` are FK-scoped to it. Realized read paths reach children only via joins from `envelope`, so an RLS-filtered envelope transitively protects them; **direct** child-table queries (none exist today) would still leak. Hardening the children (denormalize `tenant_id` + per-table policies) is the immediate follow-up — TASK-002 candidate.
- **The system / bootstrap branch** (ADR-0010 Rule 4). `ProvisionTenant` / signup run *above* RLS under a system context. The prototype has a single DB role + single connection, so this needs either a second `BYPASSRLS` role/connection (pulls in `f5sign-infra`) or a session-flag bypass. Not needed for the isolation test (the test sets tenant context for both tenants directly). Deferred — and note for the follow-up: ADR-0010 Rule 4 prescribes "a BYPASSRLS connection/role"; a single-role **session-flag bypass** is a simpler realization worth evaluating, which would be a Rule 4 refinement.
- Live HTTP-stack wiring of read-path context-setting beyond what the tests exercise (there is no query bus; reads are called directly).

## 4. Deliverables (detailed)

### 4.1 Migration (new file — never edit an applied migration; repo rule #2)

A new Doctrine migration that, on `up()`:

- Creates a **fail-closed** tenant-resolver function (schema-qualify it; `STABLE`):
  ```sql
  CREATE FUNCTION public.current_tenant_id() RETURNS uuid
  LANGUAGE plpgsql STABLE AS $$
  DECLARE v text := current_setting('app.current_tenant_id', true); -- missing_ok=true → NULL if unset
  BEGIN
      IF v IS NULL OR v = '' THEN
          RAISE EXCEPTION 'no tenant scope set (app.current_tenant_id)';
      END IF;
      RETURN v::uuid;
  END;
  $$;
  ```
  Fail-closed = **RAISE when unset** (loud), not silent zero rows — matching the decided model in `identity-access-domain-model.md`.
- Enables **and FORCES** RLS (the app connects as the table owner; plain `ENABLE` does not bite the owner — `FORCE` is required):
  ```sql
  ALTER TABLE domain.envelope ENABLE ROW LEVEL SECURITY;
  ALTER TABLE domain.envelope FORCE ROW LEVEL SECURITY;
  ```
- Creates the isolation policy (both directions — reads *and* writes):
  ```sql
  CREATE POLICY envelope_tenant_isolation ON domain.envelope
      USING (tenant_id = public.current_tenant_id())
      WITH CHECK (tenant_id = public.current_tenant_id());
  ```

`down()` drops the policy, disables RLS, drops the function.

### 4.2 `TenantContext` (Foundation/platform)

- A small request-scoped holder of the current `TenantId` (`set(TenantId)`, `clear()`, `current(): ?TenantId`).
- The mechanism that applies it to Postgres: `set_config('app.current_tenant_id', <uuid>, false)` via the DBAL connection (`false` = session-scoped, **not** transaction-local — the variable must precede `doctrine_transaction`, which is why `SET LOCAL` is wrong here).
- Register it as a **non-shared** service (`shared: false`) so it does not bleed across requests/messages. *(Superseded during the build — §10 correction 2 made `TenantContext` a shared singleton so the middleware and the request edge observe the same ambient value.)*

### 4.3 `SetTenantId` middleware (Foundation/Bus)

- Implements Symfony Messenger `MiddlewareInterface`; lives in `Foundation/Bus` (framework code — Deptrac keeps it out of Domain/Application).
- Reads the tenant from tenant-scoped commands. Introduce a small marker interface — e.g. `Foundation\Bus\TenantScoped` with `tenantId(): TenantId` — implemented by existing tenant-carrying commands (`CreateEnvelope`, …). The middleware: if the message is `TenantScoped`, set the context + session var **before** delegating; **always** reset in a `finally` (`set_config('app.current_tenant_id', '', false)` → back to fail-closed) for connection-pool safety.
- Wire it into `command.bus` **ahead of** the native stack, per ADR-0010 Rule 1 (`SetTenantId → validation → doctrine_transaction`; `LogCommand` is not built yet, so `SetTenantId` is outermost today):
  ```yaml
  command.bus:
      middleware:
          - tenant_scope        # SetTenantId
          - validation
          - doctrine_transaction
  ```
- A command that is **not** `TenantScoped` leaves the scope unset → any DB access fail-closes (RAISE). That is correct for this slice (system commands are deferred; none are exercised here).

## 5. Acceptance criteria (properties)

Cite these in test docblocks as `P-RLS-N` per the in-repo property convention ([`tests/README.md`](../../tests/README.md)).

- **P-RLS-1 (read isolation).** *Given* envelopes for tenant A and tenant B, *when* the session context is tenant A, *then* a query returns only A's envelopes and never B's.
- **P-RLS-2 (write isolation / WITH CHECK).** *Given* the session context is tenant A, *when* a row is inserted/updated with `tenant_id` = B, *then* the database rejects it.
- **P-RLS-3 (fail-closed).** *Given* no tenant context is set, *when* any DML touches `domain.envelope`, *then* it raises (no silent empty result).
- **P-RLS-4 (middleware establishes scope).** *Given* a `TenantScoped` command for tenant A dispatched on `command.bus`, *when* it runs, *then* the handler sees the RLS scope set to A; *and* after it completes the scope is reset (next no-context access fail-closes).
- **P-RLS-5 (FORCE bites the owner).** The isolation holds even though the app connects as the table owner — i.e. the migration used `FORCE`, verified by P-RLS-1 passing under the app's own connection.
- **P-RLS-6 (no ambient tenant ⇒ fail-closed write).** *Given* no tenant context, *when* a command that writes the envelope is dispatched, *then* the middleware passes through (sets no scope) and the insert is rejected by the fail-closed `current_tenant_id()` — never a silent write.

## 6. Test specification

- **Layer:** `Integration/` (DB-touching) — per the test-layering convention in `tests/README.md`. Runs only via the infra Makefile (`make test`); direct host `vendor/bin/phpunit` fails on `postgres-test` host resolution (CLAUDE.md).
- **New base:** an RLS-aware `AbstractIntegrationTestCase` (or extend the existing integration base) exposing a helper to set/clear the session tenant (`set_config('app.current_tenant_id', …)` via the test connection) so each test runs under an explicit tenant.
- **New test:** `EnvelopeRlsIsolationTest` (or similar) covering the properties below. Every test declares `#[CoversClass]` for the class under test (the middleware / context / migration-backed behavior) and `#[UsesClass]` for collaborators — `phpunit.dist.xml` has `requireCoverageMetadata="true"`.
- **Fixtures:** insert envelopes for two distinct `TenantId`s, each under its own session context (P-RLS-2's WITH CHECK means you must set context = tenant before inserting that tenant's rows).
- **Negative assertion:** P-RLS-3 expects an exception when querying with no context set.

## 7. Known consequence — existing tests will break (and must be fixed here)

FORCE RLS makes **every** `domain.envelope` access fail-closed without a tenant context. These existing DB-touching tests do not set one and **will start raising** — update them (ideally by routing them through the new context-aware base, or setting a default tenant in setup):

- `tests/F5Sign/Envelope/Scenario/EnvelopeVerticalSliceTest.php`
- `tests/F5Sign/Envelope/Scenario/AuditFaultPropagationTest.php`
- `tests/F5Sign/Envelope/Integration/DoctrineEnvelopeReadRepositoryTest.php`
- `tests/F5Sign/Envelope/Integration/EnvelopeQueryAdapterTest.php`

(The `CreateEnvelopeUseCaseTest` handler test uses in-memory fakes — not DB-touching — so it is unaffected by RLS.)

Making these green again (under tenant context) is part of "done" — it also broadens the isolation guarantee's exercise for free.

## 8. Constraints & conventions

- **Run everything via the infra Makefile** from `../f5sign-infra/` (`make qa`, `make test`, `make migrate`, `make migration`). Never run tooling from the host; never run `docker compose` from this repo (CLAUDE.md rules #5, #6).
- **Schema changes go through a new Doctrine migration** — do not edit an applied migration (rule #2).
- **Deptrac boundary** — the middleware, context applier, and DBAL calls live in `Foundation`/`Infrastructure`; Domain and Application stay framework-free. Do not import Messenger or DBAL from the core.
- **PHPStan level 9** + custom architecture rules must pass. **`@see` tags are fully-qualified** (`@see \F5Sign\…`) — the repo enforces this.
- **No new `phpstan-baseline.neon` entries** without categorizing the finding (CLAUDE.md).
- If anything here forces a deviation from ADR-0010, that is an **ADR change** (amend the ADR / open a follow-up), not a silent edit (rule #7).

## 9. Definition of done

- New migration applies cleanly (`make migrate`) and reverses (`down()` verified).
- `TenantContext` + `SetTenantId` middleware landed; middleware wired into `command.bus` in the ADR-0010 order.
- `EnvelopeRlsIsolationTest` covers the properties above and passes.
- The listed existing tests pass again under tenant context.
- **Green `make qa`** (PHPStan L9 + Deptrac + full PHPUnit) via the infra Makefile.
- ADR-0010's status / "Realized in" updated to reflect that `SetTenantId` + fail-closed RLS (envelope) are now realized; child-table RLS + system branch remain queued.

## 10. Implementation outcome (2026-06-08)

Implemented as a first agent-delegable shot. **Verified green via the infra Makefile:** PHPStan L9 clean · php-cs-fixer clean · PHPUnit **95 tests / 274 assertions** (5 new; the suite was 90) · migration `up`/`down` reverse cleanly · Deptrac unchanged (the pre-existing cross-BC ACL violations only — `SignatureExecutionId`, [ADR-0004](../adr/ADR-0004-cross-bc-anti-corruption-layer.md); this slice added none). **Coverage of the new code: `SetTenantIdMiddleware` and `TenantContext` both 100% (lines + methods)** under the isolation test (P-RLS-1…6).

**Landed:** `Version20260608000001` — the RLS baseline, since folded into the `Version20260713` conformant migrations (ADR-0018's Phase-A clean-baseline rewrite; ADR-0019 §11 waived) — (fail-closed `current_tenant_id()` + `f5sign_app` schema grants + FORCE RLS + policy) · [TenantContext](../../src/F5Sign/Foundation/Tenancy/TenantContext.php) · [SetTenantIdMiddleware](../../src/F5Sign/Foundation/Bus/SetTenantIdMiddleware.php) (wired ahead of `validation`/`doctrine_transaction` in [messenger.yaml](../../config/packages/messenger.yaml)) · [RlsIntegrationTestCase](../../tests/F5Sign/Support/RlsIntegrationTestCase.php) + [EnvelopeRlsIsolationTest](../../tests/F5Sign/Envelope/Integration/EnvelopeRlsIsolationTest.php) (P-RLS-1…6).

**Three corrections to the spec, from grounding against the code:**
1. **Ambient context, not a per-command marker.** Only `CreateEnvelope` carries a `tenantId` (the explicit tenant for the *new* aggregate); `AddDocument`/`AddStep`/`SendEnvelope`/etc. carry none. So the `TenantScoped` marker was dropped — the middleware lifts `TenantContext` (populated by auth in prod; a test helper here) uniformly, which is the model the identity-access doc already describes.
2. **`TenantContext` is a shared singleton**, not `shared: false` — the middleware and the request edge must observe the same ambient value.
3. **Reset = restore-prior, not blank** — preserves a multi-command request span while staying pool-safe (a fresh connection's prior is empty → fail-closed for the next borrower).

**The load-bearing finding (and its resolution).** The bootstrap role (`f5sign`) is **both `rolsuper` and `rolbypassrls`**; superusers/BYPASSRLS roles ignore RLS regardless of `FORCE`, so a policy alone is never consulted on a superuser connection. **Resolved by a runtime↔migration credential split** (infra updated):
- The `f5sign-infra` repo provisions a dedicated **non-superuser, non-BYPASSRLS login role `f5sign_app`** (its `docker/postgres/init-app-role.sh`, mounted on both Postgres services).
- The **application + tests connect as `f5sign_app`** (`DATABASE_URL` in `.env` / `.env.test`), so RLS is genuinely enforced — verified: `SELECT current_user` → `f5sign_app`, `rolsuper`/`rolbypassrls` both false.
- **Migrations run as the privileged role** via the infra Makefile (`DB_ADMIN_URL` / `DB_TEST_ADMIN_URL` override `DATABASE_URL` on `migrate` / `init-db` / `reset-db` / `test-db-setup`); the RLS migration grants `f5sign_app` its schema privileges.
- The integration test therefore needs **no `SET ROLE` scaffolding** — it exercises the same connection production uses.
- The predicted "existing tests break" blast radius **materialized correctly**: with the app now non-superuser, the 4 DB-touching Envelope tests run under RLS and were updated to establish a tenant scope (extend `RlsIntegrationTestCase` + `actingAsTenant`). 95/274 green.

## 11. Follow-ups this unblocks (record, do not do here)

- ~~**Production enforcement — non-superuser login role.**~~ **DONE 2026-06-08** (see §10 resolution): `f5sign_app` provisioned in infra; runtime + tests connect as it; migrations use the admin credential via the Makefile. RLS is now enforced on the app path, not merely present.
- **TASK-002 — child-table RLS:** denormalize `tenant_id` onto `document` / `document_artifact` / `step` / `recipient` + per-table policies; close the direct-child-table leak.
- **System / bootstrap branch (ADR-0010 Rule 4):** second `BYPASSRLS` role/connection *or* session-flag bypass; `ProvisionTenant` / signup above RLS. Evaluate the Rule 4 wording ("BYPASSRLS connection/role" → possibly "+ session-flag") at that point.
- **Async/worker path:** the same scope must be re-established per message on the worker (services reset between messages) — ADR-0010's sync/worker-divergence risk.
