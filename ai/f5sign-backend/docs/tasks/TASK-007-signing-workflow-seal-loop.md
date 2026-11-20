# TASK-007 — Signing-workflow Phase A: route authoring + close the seal loop over the event consume side

| Field | Value |
|-------|-------|
| **Status** | **Implemented 2026-06-22** — `make qa` green (PHPStan L9 · Deptrac **0** · lint · **216 tests**) incl. a live end-to-end seal-loop test vs MinIO + `eu-dss` + the relay/consume path. Decision record: [ADR-0027](../adr/ADR-0027-seal-loop-and-event-consume-side.md). |
| **Type** | **As-built record** — the ROADMAP "Signing-workflow wiring" **Phase A**. Documented after the build; the body records what landed. |
| **Builds on** | [TASK-004](TASK-004-envelope-http-exposure.md) (the HTTP edge + controller conventions), [TASK-006](TASK-006-dss-stage2-real-document-seal.md) (the real DSS document seal), and the [ADR-0024](../adr/ADR-0024-event-delivery-transactional-outbox.md) transactional-outbox build (whose **consumer hop** this realizes). |
| **Delivery bar** | An envelope goes **create → author → send → (mock-sign) → seal → COMPLETED entirely off the HTTP edge + the relay/consume workers**, with the seal triggered by the *outboxed* `EnvelopeReadyToSeal` (not a sync shortcut) and the consuming worker re-establishing the tenant from the outbox row. |
| **Auth** | **Header-stub** (inherited). The recipient-facing token-auth path is Phase B. |
| **Naming** | `F5Sign\` throughout. |

---

## 1. Why this task exists

After the DSS-seal slice (TASK-006) the seal *mechanism* worked, but the workflow could not close itself: the Envelope aggregate halted at `READY_TO_SEAL`, nothing reacted to the trigger, and the company seal rode the per-recipient `DocumentSigned` chain. Separately, three authoring use-cases (`AddStep`/`AddRecipient`/`SendEnvelope`) were built but unrouted. Phase A wires both — and, because the clean seal-trigger reacts to an *aggregate* event, it forced building [ADR-0024](../adr/ADR-0024-event-delivery-transactional-outbox.md)'s deferred **consume side**.

## 2. What was built

**Tier 1 — HTTP routing** (Envelope `UI/Http/`): controllers + wire-typed request DTOs (ADR-0022) + routes for `AddStep`/`AddRecipient`/`SendEnvelope` (incl. `POST /v1/envelopes/{id}/send`, the first **lifecycle-action** route), `Role::values()`, OpenAPI `#[OA\*]`.

**Tier 2a — the event consume side** (Foundation; realizes ADR-0024 D3d): `TenantStamp` + `ReestablishTenantMiddleware` (on `event.bus`); the relay reads the outbox `tenant_id` and stamps it, the serializer round-trips it as the `X-Tenant-Id` header and re-adds a `BusNameStamp('event.bus')` on decode (the codec drops the framework's), so the stock `messenger:consume async_events` worker delivers events to the reactors with the RLS scope re-established.

**Tier 2b — the seal loop** (Envelope + SignatureExecution): `EnvelopeReadyToSeal` → `OnEnvelopeReadyToSeal` [SE] → `SealEnvelope` → DSS PAdES-B-B seal (new `DocumentSealer` service, shared with the refactored `SealDocumentUseCase`) → distinct `EnvelopeSealed` [SE] → `OnEnvelopeSealed` [Envelope] → `CompleteEnvelope` → `Envelope::complete()` (`READY_TO_SEAL`→`COMPLETED`) → auditable `EnvelopeCompleted`.

## 3. Scope

**In scope (built):** the three authoring routes; the consume side (TenantStamp + middleware + serializer/relay carriers + BusNameStamp routing); the seal-loop reactors/commands/use-cases/events; `Envelope::complete()`; the attributed unit-test hardening + the end-to-end `EnvelopeSealLoopTest`; ADR-0027 + the ADR-0024/README updates.

**Out of scope (deferred — named so they're not silently dropped):**
- **Consumer-hop DLQ/retry** (`failure_transport` + `retry_strategy` + `symfony/doctrine-messenger`) — still ADR-0024 Proposed-within; the consume side is at-least-once + idempotent without it.
- **The SE no-aggregate producer seam** — `EnvelopeSealed` (like `DocumentSigned`) dispatches inline, so hop 2 is sync and the loop is **half-async**.
- **Active `SEALING`** + the async seal command (ADR-0015 / ADR-0024 D4).
- **Phase B** — the Signing Session BC, the recipient-facing surface, and token-auth (depends on the Session BC tech-doc).
- **Write-path domain-exception → HTTP mapping** — a `send` on an incomplete envelope surfaces as a 500 (only the read path translates today).

## 4. Key decisions

- **Symmetric, event-driven choreography** over an artifact-append-driven trigger — keeps the cross-BC port facts-only (ADR-0004) and mirrors the existing `OnDocumentSigned`. *(User-confirmed.)*
- **Build the consume side** over a sync shortcut — completes ADR-0024's deferred consumer hop and unblocks every future aggregate-event reaction. *(User-confirmed.)*
- **A distinct `EnvelopeSealed`** event — the company seal is no longer the per-recipient `DocumentSigned`; the seal is its own minted `SignatureExecutionId`.
- **`SEALING` stays a reserved state** — `complete()` accepts it for the future async path, but the synchronous seal completes `READY_TO_SEAL`→`COMPLETED` directly.
- **Defer the persistent audit sink** — the in-memory `AuditCommandAdapter` stays; a real Evidence & Audit sink is its own slice. *(User-confirmed.)*
- Full rationale + counterpoints in [ADR-0027](../adr/ADR-0027-seal-loop-and-event-consume-side.md).

## 5. Test plan & acceptance

- **`EnvelopeSealLoopTest`** (the load-bearing one): drives create→…→mock-sign→`READY_TO_SEAL`, **clears the ambient tenant** (simulating a fresh worker), then relay + consume → asserts `COMPLETED` + the `signed/` WORM artifact + `EnvelopeCompleted` on the outbox. Clearing the tenant first is what proves re-establishment rather than an in-process leak.
- **Attributed unit hardening:** `EnvelopeCompleteTest` (the `complete()` guards), `SealEnvelopeUseCaseTest` (the idempotency guard), `DocumentSealerTest` (seal + error guards), `ReestablishTenantMiddlewareTest` (all branches), `DomainEventPayloadTest` (the two new events).
- **`EnvelopeHttpTest`** gains the full `create→upload→…→send` 204 path over the HTTP client.
- Integration/scenario tests stay `#[CoversNothing]` by convention; the reactors + thin Messenger handlers are scenario-exercised, not unit-tested (consistent with `OnDocumentSigned`).

## 6. ADR / doc reconciliation done here

- **[ADR-0027](../adr/ADR-0027-seal-loop-and-event-consume-side.md)** authored (the seal loop + the consume side).
- **[ADR-0024](../adr/ADR-0024-event-delivery-transactional-outbox.md)** — the consumer-hop in-process reactor + `TenantStamp`/middleware moved from Proposed-within to realized (only DLQ/retry remains).
- ADR index + relationship graph updated.

## 7. Deviations & honest notes

- **The loop is half-async.** Hop 1 (`EnvelopeReadyToSeal`) rides the outbox + consume side; hop 2 (`EnvelopeSealed`) dispatches inline like `DocumentSigned` because SE has no aggregate (the deferred producer seam). Faithful to the current substrate, not a clean full-async loop.
- **`SEALING` is reserved, not exercised.** The synchronous seal occupies it for milliseconds; it becomes live with the async seal command.
- **`send` on an incomplete envelope → 500.** The write-path domain-exception→HTTP mapping isn't wired; surfaced as a follow-up, not fixed here (it's cross-cutting across every write endpoint).
- **Coverage discipline.** The seal-loop reactors/handlers read 0%-attributed but are exercised end-to-end (`#[CoversNothing]`); attributed coverage comes from the unit layer.

## 8. Open follow-ups (track, don't solve here)

*(As-built 2026-06-22; most have since landed — discharge status added 2026-07-20.)*

- Consumer-hop **DLQ/retry** + the **SE producer seam** (both ADR-0024 Proposed-within). → **Done**: the event-log cutover ([ADR-0031](../adr/ADR-0031-event-log-store.md), stage 1b) gave SE a first-class detached append; DLQ/retry landed with sequential-PAdES ([ADR-0034](../adr/ADR-0034-sequential-incremental-pades.md) slice 4 / ADR-0015).
- **Active `SEALING`** + the async seal command (ADR-0015 / D4). → still reserved: the loop is fully async via the event log, but there is no distinct active-`SEALING` command.
- The **write-path domain-exception → HTTP** mapping (a clean 409/422 for a bad `send`). → **Done**: [ADR-0029](../adr/ADR-0029-domain-exception-http-mapping.md).
- **Phase B** — Signing Session BC + recipient surface + token-auth. → **Done**: [TASK-008](TASK-008-signing-session-recipient-ceremony.md) / [ADR-0028](../adr/ADR-0028-recipient-signing-token-auth.md).
