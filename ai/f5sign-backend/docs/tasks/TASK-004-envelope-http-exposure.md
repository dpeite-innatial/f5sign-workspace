# TASK-004 — Envelope HTTP exposure (first web vertical)

| Field | Value |
|-------|-------|
| **Status** | **Implemented 2026-06-12** — thin spine green (`make qa`: PHPStan L9 · Deptrac 0 · lint · full test suite). [ADR-0021](../adr/ADR-0021-http-request-edge.md) Accepted. See §7. |
| **Type** | Agent-delegable implementation task (births the HTTP layer + an ADR) |
| **Builds on** | [TASK-001](TASK-001-rls-tenant-isolation.md) (RLS substrate + `app.current_tenant_id` scope + non-superuser runtime role); the realized Envelope Application + read-side surface |
| **Delivery bar** | Green `make qa` via the infra Makefile + a functional HTTP test proving the full request→RLS→response round trip |
| **Auth decision** | **Header-stub** (locked 2026-06-12). No SecurityBundle/JWT in this task — Lexik JWT deps are present but stay unwired until Identity & Access. |

---

## 1. Why this task exists

The backend has a mature framework-free DDD core (kernel + foundation + Envelope BC: Domain, Application, Contract, Infrastructure, persistence with RLS) and **zero HTTP surface**. Nothing is reachable over the wire. This task builds the first web vertical: expose the Envelope BC over HTTP so the converged stack (nginx `:8000` → our backend) serves real requests, and lock the entire request-edge spine — routing, tenant resolution, command dispatch, tenant-scoped reads, JSON (de)serialization, and error translation — on the smallest honest slice.

This is the first task where the **request edge** exists, which makes it the home of two things nothing has needed before: (a) **request-edge tenancy** — setting the RLS GUC for the *read* path (today only the command bus sets it, for writes); (b) an HTTP **error-translation boundary** (ADR-0004/0009 at the edge).

## 2. What already exists (reuse, do not rebuild)

| Thing | Where | Reuse |
|-------|-------|-------|
| `CreateEnvelope` command + `CreateEnvelopeUseCase` | `src/F5Sign/Envelope/Application/{Command,UseCase}/Authoring/` | POST create dispatches this |
| Fine-grained authoring commands | same | `AddDocument`, `AddRecipient`, `AddStep`, `UploadDocumentBytes` (later slices) |
| `SendEnvelope` + lifecycle commands | `…/{Command,UseCase}/Lifecycle/` | POST send (later slice); uses `findLockedForUpdate` |
| Command bus + middleware spine | `config/packages/messenger.yaml`, `Foundation/Bus/` | `SetTenantIdMiddleware` → `validation` → `doctrine_transaction`; controllers dispatch through it |
| `TenantContext` (shared request-scoped) | `Foundation/Tenancy/TenantContext.php` | edge listener sets it; middleware reads it |
| `SetTenantIdMiddleware` | `Foundation/Bus/SetTenantIdMiddleware.php` | already scopes the **write** connection via `set_config('app.current_tenant_id', …, false)` |
| `EnvelopeReadRepository::findById(): ?EnvelopeView` (DBAL) | `Envelope/Domain/ReadRepository/` + `…/Infrastructure/Persistence/Doctrine/Read/` | GET by id reads this directly (rich `EnvelopeView` incl. Settings) |
| `EnvelopeView` + `DocumentView`/`StepView`/`RecipientView` | `…/Domain/ReadRepository/` | the shape a presenter maps to JSON |
| Published Contract: `EnvelopeId`/`EnvelopeStatus`/`WorkflowType`/`Role`, `EnvelopeNotFoundException` | `Envelope/Contract/` | response field types; not-found → 404 |
| RLS substrate (`current_tenant_id()` fail-closed, FORCE, policy, `f5sign_app` role) | TASK-001 migration + infra | reads/writes already bite; this task only needs to **set the scope at the edge** |

**The crux finding (read this):** the read path is **not tenant-scoped at the HTTP edge today.** Read repositories run raw DBAL on the shared connection and do **not** pass through the command-bus middleware. RLS is fail-closed, so a read with no GUC set returns zero rows / raises — not a leak, but every GET would come back empty. The integration tests work only because `RlsIntegrationTestCase` sets the GUC *manually* (`actingAsTenant` calls both `setAmbientTenant` and `applySessionTenant`). Production has no equivalent. **The edge listener (§4.2) is the load-bearing new piece.**

## 3. Scope

**In scope (the thin spine — see §5 for the boundary decision):**
1. **HTTP infrastructure**: enable controller routing (fix `config/routes.yaml` — it points at a non-existent `routing.controllers` resource; switch to attribute routing over `src/F5Sign/*/Infrastructure/Http/Controller/`).
2. **Request-edge tenancy** (`kernel.request` listener): resolve tenant (+ acting user) from stub headers, set `TenantContext`, and apply the `app.current_tenant_id` GUC to the connection **before any handler/query runs** — so reads are scoped. Runs at the outermost boundary.
3. **`POST /v1/envelopes`** — create a DRAFT envelope (dispatch `CreateEnvelope`), return `201` + the new id.
4. **`GET /v1/envelopes/{id}`** — read via `EnvelopeReadRepository::findById`, present `EnvelopeView` as JSON; `404` on not-found.
5. **Edge error translation** (ADR-0004/0009): an exception→JSON mapper at the boundary — validation → `422`, `EnvelopeNotFoundException` → `404`, fail-closed/no-tenant → `400/401`, unexpected → `500`. Consistent error envelope (`{ error, code, … }` per the frontend's `ApiError` shape).
6. **Functional test(s)**: boot the kernel via `browser-kit` (now a dev dep), hit the endpoints with stub headers, assert the round trip **and** tenant isolation (tenant A cannot GET tenant B's envelope).
7. **ADR**: author `ADR-0021` (HTTP request edge: routing convention + request-edge tenancy + error-translation boundary). Proposed → Accepted when the slice is green (lock-via-exercise).

**Out of scope (deferred, named so they aren't silently dropped):**
- **Real auth** — SecurityBundle / Lexik JWT / OAuth. Header-stub stands in until Identity & Access. ADR-0010 Rule 4 (system/bootstrap BYPASSRLS branch) stays deferred with it.
- **The richer authoring/lifecycle endpoints** (`/documents`, `/recipients`, `/steps`, `/send`, `/void`, …) — repetition of the proven pattern; follow-on slices once the spine is locked (unless §5 widens this task).
- **Composite `POST /v1/envelopes`** matching Pilar 6 (create + documents + recipients + fields + upload URLs in one call) — see §5.
- **Workspace** dimension — the frontend speaks `workspace_id`; our domain has only `tenant_id`. Reconciliation is in the EP02/03 foundation backlog (tenant/workspace root tables); use tenant only here.
- **The Signer surface** (`/v1/signing/session/*`) — fully built in the frontend but belongs to Signing-Session / Signature-Execution BCs, **not** Envelope. Different task, different BC, different (per-recipient access-token) auth.
- Document **byte path** (presigned upload URLs / storage seam) — ADR-0016 open; needs the validation worker.
- CORS, rate-limit headers, idempotency-key handling, OpenAPI/Nelmio — layer on once the spine holds.

## 4. Design leans (recommended; mine to lock unless you object)

These are implementation-internal and reversible — stated so the build is unambiguous, not as open questions.

### 4.1 Routing & placement
- **Attribute routing** (`#[Route('/v1/envelopes', methods: ['POST'])]`) on controllers in `src/F5Sign/Envelope/Infrastructure/Http/Controller/`. Controllers are Infrastructure (framework-aware) — attributes there don't violate the framework-free core. One controller per action, mirroring the `Infrastructure/Messenger/Command/` layout.
- **Path prefix `/v1`** — *not* `/api`. Evidence: nginx is a straight pass-through (`:8000` → `public/index.php`, no prefix strip) and the real frontend calls `/v1/signing/session` against `apiBaseUrl: http://localhost:8000`. (Memory's "nginx → `/api`" was imprecise; corrected.)
- **Route conventions are NOT locked frontend-side (confirmed with the frontend teams 2026-06-12).** `/v1/envelopes` + the action sub-paths are *our provisional proposal*, not a fixed external contract — we have room to shift them. Implication: keep paths simple/RESTful, and treat the eventual naming as a reconciliation to propose *to* the frontend teams, not a constraint to conform to. Don't over-invest in matching Pilar 6 verbatim.

### 4.2 Request-edge tenancy
- A `kernel.request` listener in **`Foundation/Http/`** (cross-cutting, not Envelope-specific), priority high enough to run before controller execution. It: reads `X-Tenant-Id` (+ `X-Acting-User-Id`) stub headers → `TenantContext::set()` → `set_config('app.current_tenant_id', <id>, false)` on the connection. Missing/blank tenant on a tenant-scoped route → `400/401` (fail-closed, no silent empty reads).
- Reuse the exact GUC name + `set_config(…, false)` form from `SetTenantIdMiddleware` so write-path and edge agree; the middleware then just re-affirms an already-set scope.
- A `kernel.terminate`/`finally` `TenantContext::clear()` + GUC reset for connection-pool hygiene (mirrors the middleware's `finally`).

### 4.3 Serialization
- **Hand-written presenters** (a `Response/EnvelopeJsonPresenter` mapping `EnvelopeView` → array), not the reflection serializer. Keeps the JSON shape an explicit, reviewed contract; avoids leaking VO internals; honours the published-contract discipline. Request parsing: explicit `Request/CreateEnvelopeRequest` DTO + manual field extraction → command (with validation).
- IDs serialize via `->toString()`, enums via `->value`, dates as ISO-8601.

### 4.4 Acting-user / issuedBy under stubs
- `CreateEnvelope` needs `issuedBy: UserId` and `tenantId`. Both come from stub headers in this task (`X-Tenant-Id`, `X-Acting-User-Id`), resolved at the edge. When real auth lands, the same `TenantContext`/principal seam swaps the source — controllers and commands don't change.

### 4.5 Test layer
- New `tests/F5Sign/Envelope/Http/` (or `Functional/`) layer using `WebTestCase` + the RLS test base, kernel-booted. The isolation assertion (cross-tenant GET returns 404, not another tenant's row) is the load-bearing one — it proves §4.2 works end-to-end, not just in unit.

## 5. The decision to resolve before building

**How wide is this first slice, and how closely does it track the (spec-only) frontend contract?** The dashboard `/v1/envelopes/*` contract (Pilar 6) is **spec-only — no frontend consumer exists yet** (the dashboard app is a skeleton). So nothing live is broken by either choice; the question is sequencing.

- **Option A — Thin spine, domain-shaped (recommended).** Just `POST /v1/envelopes` (bare DRAFT create) + `GET /v1/envelopes/{id}` + the edge tenancy + error boundary + ADR-0021. Locks the whole request→RLS→response path on minimal surface. Every later endpoint (documents, recipients, send, void) is repetition of the proven pattern. Defers the composite-create shape (and its cross-command transactionality + upload-URL questions) until the dashboard is actually built and can pressure-test it. **Smallest honest vertical; fastest lock.**
- **Option B — Full DRAFT-authoring set.** Add `/documents`, `/recipients`, `/steps`, `/send` in this task so a complete envelope can be authored and sent over HTTP. More immediately useful, but multiplies surface before the spine is proven and still leaves the composite-vs-fine-grained reconciliation open.
- **Option C — Contract-faithful composite create.** Build `POST /v1/envelopes` to match Pilar 6's composite payload (documents + recipients + fields + upload URLs in one call), orchestrating multiple commands. Matches the eventual frontend shape, but bakes in orchestration/transactionality decisions against a contract with no live consumer — premature lock.

Recommendation: **A.** It's the lock-via-exercise move — prove the spine, then repeat. The composite shape (C) is a reconciliation to do *with* the dashboard team when their consumer is real, not speculatively now.

**Resolved 2026-06-12: Option A (thin spine).** Reinforced by the frontend teams confirming route conventions aren't locked (§4.1) — there's no fixed contract to be faithful to yet, so the speculative-match cost of B/C is real and the benefit is nil. Build the spine, propose the naming, reconcile when consumers are real.

## 6. Open follow-ups this task surfaces (track, don't solve here)
- Composite-create reconciliation with the dashboard team (Pilar 6 `POST /v1/envelopes` → our fine-grained commands; transactionality across them).
- Workspace vs tenant reconciliation (EP02/03 foundation backlog).
- Real auth swap (Identity & Access): header-stub seam → JWT principal; ADR-0010 Rule 4 system path.
- Whether request-edge tenancy belongs partly in the bus middleware's responsibility or fully at the edge (ADR-0021 states the division: edge sets, middleware re-affirms).

<!-- OFFREPO: external refs not followable from this repo — `Pilar 6` (design-repo dashboard contract spec) and `EP02/03 foundation backlog` (workspace discrepancy-audit docs), used here only to name deferred/out-of-scope reconciliation work; enough is described inline to act without them. Clean when the dashboard contract reconciliation (§6) is actually scoped in-repo. -->


## 7. Implementation outcome (2026-06-12)

Built Option A; `make qa` green end-to-end. Key deviation from §4.1: controllers landed in **`Envelope/UI/Http/`**, not `Infrastructure/Http/` — the deptrac visibility contract already designates a `<BC>/UI` layer for HTTP entry points with a deliberate **no-own-Domain** rule (HTTP→Command translation only). That constraint was load-bearing: it forced honest same-BC Application seams instead of letting a controller reach into Domain. ADR-0021 records the full decision; the short version:

- **UI seams (because UI can't touch Domain):** `CreateEnvelope::draft()` (Application named constructor builds the default `Settings` internally) for writes; a same-BC `Application/Query/GetEnvelope` + `GetEnvelopeHandler` returning the ACL-clean `EnvelopeContextView` (user-issued, nullable) for reads. The existing cross-BC `EnvelopeQueryInterface::getContextForSE` was *not* reused — its `SystemActorId` issuer is dishonest for a user request.
- **Edge (`Foundation/Http/`):** `TenantRequestListener` (`kernel.request`, sets `TenantContext` + the `app.current_tenant_id` GUC from `X-Tenant-Id` before any read; resets on terminate) + `ApiExceptionListener` (`kernel.exception`, Vendor-only JSON boundary; the UI translates not-found→`NotFoundHttpException`, so Foundation never imports a BC exception).
- **Endpoints:** `POST /api/v1/envelopes` (201 + id), `GET /api/v1/envelopes/{id}` (200 / 404). Stub headers `X-Tenant-Id` + `X-Acting-User-Id`. Create defaults expiry to issuedAt+30d (stub).
- **Route schema (revised from §4.1's attribute lean):** `/api` deployment base set once in `config/routes.yaml`; per-BC PHP route file `config/routes/api/envelope.php` owning its `/v1` version (cross-BC version skew allowed); controllers are plain services, no `#[Route]`. PHP-not-YAML for `::class` rename-safety; `RouteCollisionTest` guards against path+method collisions across the per-BC files. Full rationale in ADR-0021 "Route schema".
- **Lock:** `tests/F5Sign/Envelope/Http/EnvelopeHttpTest.php` — round-trip, cross-tenant 404 (the load-bearing isolation proof, driven through the real kernel), missing-tenant 400, invalid-input 422; `tests/F5Sign/Http/RouteCollisionTest.php` — no duplicate (method, path). `make qa`: full suite green.

Realized files: see ADR-0021 "Realized in".
