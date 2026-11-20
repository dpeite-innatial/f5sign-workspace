# TASK-002 — Child-table RLS (Envelope aggregate)

| Field | Value |
|-------|-------|
| **Status** | **Done (2026-07-17).** The schema landed in [ADR-0018](../adr/ADR-0018-dbal-only-persistence.md)'s Phase-A clean-baseline rewrite; the acceptance properties are now paid, in Phase B's realization step 9. **P-RLS-7 + P-RLS-8** are exercised by [`ChildTableRlsIsolationTest`](../../tests/F5Sign/Envelope/Integration/ChildTableRlsIsolationTest.php) (both sabotage-verified: a policy widened to `USING (true)` fails them). **P-RLS-9 + P-RLS-10 are discharged, not built** — each is already guarded and a test for it would pin nothing; the reasoning is in [§10](#10-realization-outcome-2026-07-13) and in that test's docblock, and it is worth reading before "restoring" either. §8's definition of done is met. |
| **Type** | Agent-delegable implementation task |
| **Builds on** | [TASK-001](TASK-001-rls-tenant-isolation.md) (root-table RLS + non-superuser runtime + `current_tenant_id()` + `app.current_tenant_id` scope) |
| **Closes** | The direct-child-table leak TASK-001 left open (its §3 out-of-scope note) |
| **Delivery bar** | Green `make qa` via the infra Makefile |

---

## 1. Why this task exists

TASK-001 put RLS on `domain.envelope` only. The child tables of the Envelope aggregate —
`domain.document`, `domain.document_artifact`, `domain.step`, `domain.recipient` — carry **no
`tenant_id`** and have **no policy**. Today they are protected only *transitively*: the realized
read paths reach children by joining from `envelope`, and an RLS-filtered envelope restricts the
joined rows. But a **direct** query against a child table (`SELECT * FROM domain.step WHERE …`)
bypasses that and would return every tenant's rows. No such query exists yet, but the defense is
incomplete — and "RLS is on" invites exactly such queries to be written without a second thought.

This task makes tenant isolation **per-table** so it holds regardless of access path.

Read first: [TASK-001 §10](TASK-001-rls-tenant-isolation.md#10-implementation-outcome-2026-06-08),
[ADR-0017](../adr/ADR-0017-tenant-isolation-rls-persistence-contract.md) (the persistence contract this
extends — its child-table-denormalization rule governs this task), and [ADR-0010](../adr/ADR-0010-command-bus-middleware-spine.md) Rule 4. The RLS substrate
(`current_tenant_id()`, the `f5sign_app` role, the `app.current_tenant_id` scope, the
runtime↔migration credential split) already exists — this task reuses it, it does not rebuild it.

## 2. What already exists (reuse, do not rebuild)

| Thing | From | Reuse |
|-------|------|-------|
| Fail-closed `public.current_tenant_id()` | TASK-001 migration | the policy predicate for every table |
| Non-superuser `f5sign_app` runtime role + privileged migration credential | TASK-001 / infra | RLS already bites; migrations run as admin |
| `GRANT … ON ALL TABLES IN SCHEMA domain` + `ALTER DEFAULT PRIVILEGES` to `f5sign_app` | TASK-001 migration | new columns/tables are already covered — **no new grants needed** |
| `tenant_id` on the root + the FK chain | schema | `document.envelope_id`, `step.envelope_id`, `recipient.envelope_id`, `document_artifact.document_id` give the backfill path |

## 3. Scope

**In scope** — extend RLS to the four child tables so isolation holds on direct access:
1. Add `tenant_id` to `document`, `document_artifact`, `step`, `recipient`; **backfill** from the parent chain; make it `NOT NULL`.
2. Populate `tenant_id` on **insert** (see §4 — the key design decision).
3. `ENABLE` + `FORCE ROW LEVEL SECURITY` + an isolation policy (`USING` + `WITH CHECK`) on each.
4. Extend the isolation test to assert **direct** child-table queries are tenant-scoped, and that the existing join-based read paths still work.

**Out of scope:**
- Anything in TASK-001's deferred list that isn't child-table RLS (the system/bootstrap branch; the real transactional outbox; LogCommand).
- Cross-aggregate or non-Envelope tables (none have RLS yet; handle per aggregate as they appear).

## 4. The design decision to resolve (pressure-test this first)

`tenant_id` must be present and correct on every child row at insert time, or the `WITH CHECK`
rejects the write. Two ways to populate it — **resolve this before building**:

- **Option A — DB trigger (recommended lean).** A `BEFORE INSERT` trigger on each child sets
  `tenant_id := public.current_tenant_id()`. No ORM/domain change; `tenant_id` stays a pure
  RLS-infra column the domain never sees. Consistent with TASK-001's philosophy (tenant scope is
  *ambient*, established at the edge — not domain state threaded through every child). Fail-closed
  falls out for free: with no scope, the trigger's `current_tenant_id()` RAISEs.
- **Option B — ORM-mapped column.** Add a `tenantId` field + XML mapping to `Document`,
  `DocumentArtifact`, `Step`, `Recipient`; the aggregate sets it from the root when creating
  children. More invasive, and arguably leaks a denormalized persistence concern into the domain
  model (children don't otherwise know their tenant).

**Lean: Option A.** It keeps the Envelope domain model unchanged and matches the "ambient tenant"
model. The trade-off to weigh in the pressure-test: a trigger is less visible than a mapped field
(a reviewer must know it exists), and it sets `tenant_id` from session context rather than from the
aggregate — fine here because the root's tenant *is* the session tenant (enforced by the envelope
`WITH CHECK`), but document the invariant.

## 5. Deliverables

### 5.1 Migration (new file; never edit an applied migration)
- `ALTER TABLE … ADD COLUMN tenant_id UUID` (nullable first) on the four child tables.
- **Backfill:** `UPDATE domain.document SET tenant_id = (SELECT e.tenant_id FROM domain.envelope e WHERE e.id = document.envelope_id)` and analogously for `step`, `recipient`; `document_artifact` backfills via `document` → `envelope`. (Run as the admin/owner — migrations already do.)
- `ALTER COLUMN tenant_id SET NOT NULL` after backfill.
- Per Option A: `CREATE FUNCTION`-backed `BEFORE INSERT` triggers (or one shared trigger function) setting `tenant_id := public.current_tenant_id()`.
- `ENABLE` + `FORCE ROW LEVEL SECURITY` + `CREATE POLICY … USING (tenant_id = public.current_tenant_id()) WITH CHECK (tenant_id = public.current_tenant_id())` on each child table.
- `down()` reverses all of it (drop policies, disable RLS, drop triggers/function, drop columns).

### 5.2 Tests
- Extend the isolation suite (new methods or a sibling of `EnvelopeRlsIsolationTest`): seed envelopes for tenant A and B (full aggregate — documents/steps/recipients), then under tenant A assert a **direct** `SELECT` on each child table returns only A's rows and never B's; assert a cross-tenant direct insert is rejected.
- Confirm the existing join-based read paths (`DoctrineEnvelopeReadRepository`, `EnvelopeQueryAdapter`) still return complete projections under a tenant scope (regression guard).

## 6. Acceptance criteria (properties)

- **P-RLS-7 (direct child read isolation).** For each child table, a direct query under tenant A returns only A's rows.
- **P-RLS-8 (child write isolation).** A direct insert/update of a child row with a foreign `tenant_id` (or under the wrong scope) is rejected.
- **P-RLS-9 (insert populates tenant).** Creating an envelope with documents/steps/recipients under tenant A stamps `tenant_id = A` on every child row (Option A: via the trigger).
- **P-RLS-10 (no projection regression).** The existing join-based read projections remain complete under a tenant scope.

## 7. Constraints

Same as TASK-001 §8: run everything via the infra Makefile (migrations as the admin role); new Doctrine migration (don't edit applied ones); Deptrac/PHPStan L9 clean; `@see` fully-qualified; no new baseline entries; contradicting an ADR is an ADR change, not a silent edit.

## 8. Definition of done

- New migration applies + reverses cleanly (`up`/`down`), backfill correct.
- `tenant_id` present + `NOT NULL` + policy + FORCE on all four child tables.
- New properties P-RLS-7…10 pass; existing suite still green.
- **Green `make qa`.**
- TASK-001 §3 child-table caveat marked closed; this task's outcome recorded.

## 9. Follow-ups (still out of scope after this)

- System/bootstrap branch (ADR-0010 Rule 4) — `ProvisionTenant`/signup above RLS; with Identity & Access.
- RLS for future non-Envelope aggregates as they land (same pattern).

## 10. Realization outcome (2026-07-13)

**The schema half landed, and it landed for free — not by running this task, but as a side-effect of the [ADR-0018](../adr/ADR-0018-dbal-only-persistence.md) Phase-A clean-baseline migration rewrite.**

**Why the deferral evaporated (the load-bearing part).** This task was deferred because §3.1 requires a **backfill** — adding `tenant_id` to four populated tables means deriving each row's tenant from the parent chain before the column can go `NOT NULL`. That backfill was the whole cost. But the Phase-A rewrite replaces the migration history with a **clean baseline** (viable pre-production: no deployed DB, dev/test recreated from scratch), and **a clean baseline has no data to backfill**. Scoping the children collapsed to `tenant_id UUID NOT NULL` + `FORCE RLS` + a policy + the *already-existing* `set_tenant_id_from_scope()` trigger. The deferral wasn't resolved — its cause ceased to exist.

**§4 resolved as Option A** (the spec's own recommended lean): a shared `BEFORE INSERT` trigger calling `public.set_tenant_id_from_scope()` stamps `tenant_id` from ambient scope. Neither the domain nor the DBAL adapter writes it; `tenant_id` stays pure RLS infrastructure the domain never sees. Option B (an ORM-mapped `tenantId` field) was never built and is now moot — the ORM write path is gone.

**Landed** in [`Version20260713000002`](../../migrations/Version20260713000002.php): `tenant_id` + FORCE RLS + isolation policy + the tenant-stamp trigger on `document`, `document_artifact`, `step`, `recipient` (and on `signing_assignment` / `signing_assignment_placement`). Verified by introspecting the rebuilt database: all seven `envelope.*` tables report `has tenant_id` + `FORCE RLS`.

~~**⚑ What is NOT done — do not read this section as closure.**~~ **Paid 2026-07-17** in ADR-0018 realization step 9. Recorded below rather than deleted, because *how* the four properties resolved is the useful part — and two of them resolved by **not** being built.

**P-RLS-7 + P-RLS-8 — built, and they were the real gap.** [`ChildTableRlsIsolationTest`](../../tests/F5Sign/Envelope/Integration/ChildTableRlsIsolationTest.php) reads and writes the four child tables *directly*, not through a join from a scoped parent — which is the precise leak this task exists to close, and which `EnvelopeRlsIsolationTest` (TASK-001, P-RLS-1…6) never touched because every one of its paths goes through `envelope.envelope`. Sabotage-verified: widening the child policies to `USING (true)` makes P-RLS-7 see two tenants' rows where one is allowed, and lets P-RLS-8's foreign-tenant insert through.

**P-RLS-9 — discharged: already guarded, and a test for it is vacuous.** *"An insert stamps `tenant_id` on every child row"* cannot be false when the insert succeeds: the column is `NOT NULL` (a missing stamp fails the insert) and `WITH CHECK (tenant_id = current_tenant_id())` rejects a wrong one. Measured, not argued — rewriting the trigger to stamp a constant kills the seed inside `AddStep` with *"new row violates row-level security policy"*, before any assertion runs. So an assertion after the fact pins nothing, and **every seeding test in the suite already exercises that path**. Option A's trigger is proven by the schema it feeds, not by a test of its own.

**P-RLS-10 — discharged: it is what the suite does.** *"The join-based read projections remain complete under a tenant scope"* is asserted by every projection test, all of which run scoped. A child policy that broke the joins takes the suite red. A dedicated test would restate that coverage.

**⚑ A correction to the plan, worth knowing if you follow its trail.** This section and [ADR-0018](../adr/ADR-0018-dbal-only-persistence.md) step 9 both said *"the introspection catalog generalizes P-RLS-7…9; add a direct-access isolation test for P-RLS-10"*. That mapping is garbled: **P-RLS-7/8 *are* the direct-access properties** — they are what needed the exercise — while **P-RLS-10 is projection-regression** and needed no test at all. The sentence assigned the direct-access test to the one property that did not want one, and delegated to structure the two that did. The catalog does carry half the weight, but not by generalizing: it asserts the **predicate** every table wires, and [`EnvelopeRlsIsolationTest`](../../tests/F5Sign/Envelope/Integration/EnvelopeRlsIsolationTest.php) proves that predicate isolates — structure plus one behavioural proof, composed. Structure alone would have accepted `USING (true)`.

**Consequence to know about (correct, but it bites).** A query reading a child table **without an established tenant scope now fail-closes** — `current_tenant_id()` RAISEs rather than returning rows. That is the intended TASK-001 philosophy extended per-table. If `make qa` ever surfaces one, it is a **real gap** (a path that was relying on transitive protection through the parent join), not a regression to paper over.
