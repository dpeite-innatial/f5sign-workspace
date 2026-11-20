# TASK-015 — Void an envelope (lifecycle-action) + fail-closed signing

<!-- OFFREPO: design-trail cross-refs below are native design vocabulary, not followable from this branch's tree — inv 26 / inv 16 (design repo `01 - Envelope and Workflow BC.md §7` + backend `docs/ddd/envelope-domain-model.md`), `envelope.md §7.2/§12.4`, and the "Factor5 finding" + TASK-014 (both in-repo — `docs/ddd/envelope-domain-model.md` open-areas and `docs/tasks/TASK-014-evidence-audit-projector.md`). The recipient-decline path they describe is unbuilt. -->

| Field | Value |
|-------|-------|
| **Status** | **Commit 1 (void slice) built + green + reviewed → landing on `feat/envelope-void`, FF-merged to master.** Green bar = `make qa` (PHPStan L9 · Deptrac 0 · lint · 316 tests). **Commit 2 (the fail-closed Session revocation reactor, §4) is DEFERRED to a fast-follow** — the team pivoted to the eCMR sign-with-reservations work ahead of it; the known signable-after-void gap is queued, not lost. |
| **Type** | Forward build — a new envelope lifecycle-action (`POST …/void`) mirroring `send`, plus the cross-BC Session revocation reactor that makes void actually terminate in-flight signing. |
| **Part of** | Branch `feat/envelope-void` (backend). No infra change (no new table/role/topology — the `void` route rides the existing command/event path; the reactor rides the existing `event.bus`). |
| **Why now** | The dashboard (`dashboard-sf`) already ships a void button + gateway that throw against a missing backend endpoint. This is the first item of the eCMR NEXT-SESSION QUEUE. |
| **Decision record** | Follows the existing lifecycle-action pattern (ADR-0006 sub-resource routing, ADR-0024/0031 event delivery, ADR-0029 exception→HTTP, ADR-0004 cross-BC ACL). No new ADR for the endpoint. The Session revocation reactor is a **new cross-BC choreography edge** — candidate for an ADR note (see §5). |

---

## 1. Why this task exists

`EnvelopeStatus::VOIDED` was declared from day one but never had a domain method, event, command, or endpoint — voiding was explicitly deferred (the `Envelope` aggregate docblock said "Voiding/expiration/decline/correction/sealing-retry omitted"). A carta-de-porte sender needs to cancel a sent-but-not-completed envelope. The dashboard already models the whole void UX and only needs the backend endpoint.

A void is not merely a status flip: it must **terminate in-flight signing**. The signing ceremony (`SigningSession::commitSignature`) is fully decoupled from envelope status and the auth token is a stateless HMAC with no revocation — so a recipient holding a live authenticated session can still commit a signature *after* the envelope is voided. Void without a revocation path leaves a real hole (signable-after-void, with an orphan signature fact landing in the audit trail). Hence the second commit.

## 2. Locked decisions

- **D1 — Voidable states = {SENT, READY_TO_SEAL}.** Guard inline in `void()` (mirroring `send`/`complete`). Error states (`ROUTING_FAILED`/`SEALING_FAILED`) and `SEALING` are **not** voidable in this slice — widening the guard later is one line. `DRAFT` is not voidable (an unsent draft is discarded, not voided). `SEALING` stays out to avoid a race with `DocumentSealer`.
- **D2 — `reason` is optional (`?string`).** Captured into the `EnvelopeVoided` event **and** persisted on the aggregate. The dashboard may enforce its own "reason required" in the UI; the backend does not.
- **D3 — Who/why/when is envelope state, not only an event fact.** Persist `voided_at` + `voided_by` + `void_reason` on the aggregate (new nullable columns + migration) and expose them in the GET read projection. The event log still carries the same facts (system of record); the aggregate holds them as queryable current state so a reader sees who/why/when without replaying the log.
- **D4 — Idempotent no-op on already-VOIDED** (mirrors `complete()`): a second void returns without recording a second event. Any other non-voidable state → `EnvelopeStateException::illegalTransition` → **409**; not-found → `EnvelopeNotFoundException` → **404**.
- **Envelope-level only** — the void metadata lives on the envelope, **not** on steps/recipients. A recipient who already signed keeps their true `SIGNED` outcome (the void does not rewrite history); a pending recipient just becomes moot under the terminal envelope. The envelope's `VOIDED` status is the terminal authority for all its recipients.

### ⚑ Decision to confirm at review — read-view home (Option A)

The GET endpoint is served by the **cross-BC** `EnvelopeContextView` (Contract layer) via `findContextForSE`, because deptrac forbids the `UI` presenter from importing the rich same-BC `EnvelopeView` (it lives in `Domain/ReadRepository/` and carries `Settings`). So the void fields are added to `EnvelopeContextView` — the only Contract-surface view the presenter can consume.

- **Trade-off:** this widens the minimal cross-BC context view with sender-admin metadata (notably `voided_by`, an actor identity — the view otherwise carries none, e.g. no `sender_id`). SE/E&A consumers get 3 nullable fields they can ignore (ACL-clean: `UserId`/`string`/`datetime`).
- **Clean alternative (deferred):** a dedicated same-BC Contract view + read method for the GET detail path, leaving `EnvelopeContextView` pristine. That's a new view + near-duplicate read method + presenter rewire — disproportionate for 3 additive fields, and it grows the already-noted `EnvelopeView`/`EnvelopeContextView` split.
- **Chosen: Option A** (add to `EnvelopeContextView`) for this slice. Flagged for the review stop.

## 3. Commit 1 — Envelope void slice (Envelope BC)

**New:**
- `Contract/Event/EnvelopeVoided.php` — `AuditableEvent`, `EVENT_TYPE='ENVELOPE_VOIDED'`, streams under the envelope (INV-A), payload = `voided_by` + `reason` (+ `tenant_id`, mirroring `EnvelopeSent`, the nearest actor-driven sibling).
- `Application/Command/Lifecycle/VoidEnvelope.php` — `SendEnvelope` + a `?string $reason`.
- `Application/UseCase/Lifecycle/VoidEnvelopeUseCase.php` — load-locked → null→404 → `void()` → save. **No meter** (void is not billable).
- `Infrastructure/Messenger/Command/Lifecycle/VoidEnvelopeHandler.php` — `#[AsMessageHandler(bus: 'command.bus')]`.
- `UI/Http/VoidEnvelopeController.php` + `UI/Http/Request/VoidEnvelopeRequest.php` (optional `reason`, `#[MapRequestPayload]` nullable so an empty body → null).
- `migrations/Version…` — `ALTER TABLE domain.envelope ADD COLUMN voided_at TIMESTAMPTZ, voided_by UUID, void_reason TEXT` (all nullable); reversible `down()` drops them.
- `tests/…/Unit/Domain/Aggregate/EnvelopeVoidTest.php` — mirrors `EnvelopeCompleteTest`.

**Edited:**
- `Domain/Aggregate/Envelope.php` — `void(UserId $voidedBy, ?string $reason, DateTimeImmutable $now)` (note: takes the actor — the voider is the acting user, unlike `send()` which reuses the stored `senderId`) + `voidedAt()`/`voidedBy()`/`voidReason()` accessors + 3 ctor/rehydrate params + docblock (drop "Voiding … omitted").
- `config/doctrine/envelope/Domain.Aggregate.Envelope.orm.xml` — 3 field mappings. *(ORM mapping, removed in the DBAL-only adoption — ADR-0018.)*
- `Infrastructure/Persistence/Doctrine/DbalEnvelopeRepository.php` — SELECT + rehydrate + upsert (the ORM repo needs no code change; it hydrates from the XML mapping).
- `Contract/View/EnvelopeContextView.php` + `…/Read/DoctrineEnvelopeReadRepository::findContextForSE` + `UI/Http/EnvelopeJsonPresenter.php` — the read projection (Option A).
- `config/packages/nelmio_api_doc.yaml` — `Envelope` schema void fields + a shared `Conflict` (409) response (none existed).
- `config/routes/api/envelope.php` — the `void` route + docblock path list.
- `tests/…/Http/EnvelopeHttpTest.php` (happy 204→GET shows VOIDED; missing-actor→400; non-voidable→409) + `tests/…/Foundation/Unit/Serialization/DomainEventPayloadTest.php` (round-trip case, incl. null-reason) + `tests/…/Unit/Domain/Aggregate/EnvelopeCompleteTest.php` (rehydrate call gains the 3 null args).

## 4. Commit 2 — Session revocation reactor (Session BC) ✅ LANDED 2026-08-26 by [TASK-038](TASK-038-terminal-envelope-closes-the-ceremony.md)

> **Deferred 2026-07-08.** Landing commit 1 (void) alone and pivoting to the eCMR sign-with-reservations work. **Known gap while deferred:** `commitSignature` does not check envelope status, so a recipient holding a live authenticated session can commit a signature after the envelope is voided. Bounded (pre-production; "void wins" at the envelope level *if* `RecordRecipientCompletion` rejects a terminal envelope — unverified, confirm when building this). Queued in `USER-MEMOS.md`. Design below stands as written.
>
> ⛑ **Corrected 2026-08-25 — both halves of that gap are closed, and neither was closed by this reactor.** [TASK-021](TASK-021-two-gate-auth-model-and-access-gate.md) made the ceremony read `envelopeIsAlive: !$context->status->isTerminal()` behind the token seam and threaded it into all three acts, so `commitSignature` **does** check envelope status. The *"unverified"* half is verified too: `Envelope::recordRecipientCompletion()` no-ops on a terminal envelope, pinned by `EnvelopeCompletionRequiresSentEnvelopeTest`. ⛔ **So the reason recorded above no longer justifies anything, and the design below is no longer fail-closed machinery** — it is the *record* of the closure plus the mechanism that closes the **renewal** path, which is a different justification for the same code. [ADR-0059](../adr/ADR-0059-terminal-envelope-closes-the-ceremony.md) §2.4 states the split; [TASK-038](TASK-038-terminal-envelope-closes-the-ceremony.md) is the slice. ⚠ What is **not** closed is the read half — the read model, the document bytes, the renewal, and the crossing no record named until ADR-0059 §1: the session **open**, which under a neutral access gate mints a fresh credential on every knock ([`BL-87`](../BACKLOG.md)).


Symmetric to Envelope's `OnSessionCompleted` reactor, reversed direction: the Session BC subscribes to `EnvelopeVoided` and closes the envelope's live sessions.

⚠ **That sentence ended *"so `commitSignature`'s existing status guard rejects late commits"* until 2026-08-26, and it named the wrong beneficiary.** The commit is guarded synchronously by `envelopeIsAlive` and does not need this reactor at all. What the reactor is actually for is stated by [ADR-0059](../adr/ADR-0059-terminal-envelope-closes-the-ceremony.md) §2.3–§2.4: it is the **record** of the closure, and the mechanism that closes the **renewal** — the one crossing that performs no envelope read and must not start performing one every fifteen minutes, forever, for every live session.

- `SessionStatus::REVOKED` (new terminal case — the enum is designed to grow non-breakingly) + `SigningSession::revoke()` (guard→mutate→`record()`).
- `SigningSessionRepository::findByEnvelope(tenant, envelopeId)` finder (the `(tenant_id, envelope_id)` index already exists) + impl.
- `Session/Application/Subscriber/OnEnvelopeVoided.php` (pure `Reactor`) + `Session/Infrastructure/Messenger/Subscriber/OnEnvelopeVoidedHandler.php` (`#[AsMessageHandler(bus: 'event.bus')]`) dispatching a new `RevokeEnvelopeSessions` command → use-case that loads live sessions and revokes each.
- Tests: `revoke()` unit (guards + idempotent on terminal), the reactor, and an integration proving a voided envelope's live session is revoked.

**Caveat (record, don't over-engineer):** revocation is **eventually-consistent** (rides the log→relay→broker→consume path), so there is a small async window (~relay latency) between the void and the revocation.

⛑ **Corrected 2026-08-26, and both halves of this caveat were wrong in the same direction — they assumed the reactor was the guard.** (1) *"Closing it synchronously would require `commitSignature` to read Envelope status at commit time — which breaks the deliberate Session↔Envelope decoupling (ADR-0004)"* is falsified: TASK-021 closed it synchronously **without** breaking anything, by reading `envelopeIsAlive` once behind the token seam where tenant scope already exists and passing the boolean into the aggregate. The decoupling constrains where the read happens, not whether it can. (2) The window therefore no longer admits a late **commit** at all; what it admits is a renewal that mints a credential which buys only reads, and every read is refused synchronously — so the residual is *harmless* rather than merely small (ADR-0059 §2.4). **Confirmed at build:** `RecordRecipientCompletion` rejects a terminal envelope, pinned by `EnvelopeCompletionRequiresSentEnvelopeTest`.

## 5. Open items / follow-ups

- Explicit **token revocation** (stateless HMAC has none today) — deferred; the session-state revocation above is sufficient for MVP fail-closed. Named in the ADR-0028 deferred list. ⛑ **Corrected 2026-08-25: the parenthetical is stale, and it is the half that reads as timeless.** The token is no longer a stateless HMAC — [ADR-0045](../adr/ADR-0045-issued-credential-format.md) made it an opaque credential whose digest is stored in `session.signing_token`, so a row exists and revocation is mechanically **possible**. What is absent is a `revoked_at` column and a chokepoint honouring it, declined deliberately by [TASK-028](TASK-028-opaque-signing-token.md) §4.3. The two rows that make that declination cost something are [`BL-152`](../BACKLOG.md) and [`BL-158`](../BACKLOG.md); their home is a decision about ADR-0045's credential format, and explicitly **not** [TASK-038](TASK-038-terminal-envelope-closes-the-ceremony.md), which guards crossings rather than credentials.
- ~~Whether the Session revocation reactor warrants its own **ADR** (first reverse-direction cross-BC edge) or an amendment to the choreography ADR — decide at commit 2.~~ ✅ **Answered 2026-08-26: neither, and the reason is that the edge was never new to the context map.** [`deptrac.yaml`](../../deptrac.yaml) already grants `SessionApplication` and `SessionInfrastructure` the whole `EnvelopeContract` layer — that is how the ceremony reads the recipient context — so consuming an Envelope *fact* opens no dependency the ruleset did not already allow, and there is nothing for an ADR to decide. What was genuinely new is the **direction of the choreography**, and [ADR-0059](../adr/ADR-0059-terminal-envelope-closes-the-ceremony.md) §3.2 records it as a consequence rather than as a decision of its own.
- Error-state voidability (D1 widening) — one-line follow-up if the dashboard needs to void `ROUTING_FAILED`/`SEALING_FAILED`. ⛔ **Corrected 2026-08-25: do not build this yet, and the reason is not effort.** Neither status has a writer — `rg` finds both only in `EnvelopeStatus` itself and in one docblock naming them — so **no envelope can be in either**, and widening the guard to admit them is dead code that reads as a fix for stuck envelopes. [`BL-15`](../BACKLOG.md) carries the judgement: those cases are *vestigial scaffolding, not an accepted contract*, and *"just wire them" mistakes scaffold for design*. ⚑ It is also `CLAUDE.md` authoring rule 5's trap exactly — an exempted set that is empty today can never go red, so green proves nothing, and the set gets populated later by someone with no reason to know this guard exists. ▶ **The widening belongs in the same changeset as whatever first writes one of those statuses**, because a failure state with no exit is worse than no failure state.

## 6. Verification

- `make qa` green per commit (PHPStan L9 · Deptrac 0 · lint · full suite).
- Migration applies + `down()` reverses on a scratch DB.
- HTTP: void a SENT envelope → 204, GET shows `status: VOIDED` + `voided_by`/`void_reason`/`voided_at`; void a DRAFT → 409 `CONFLICT`; void without `X-Acting-User-Id` → 400.
- Commit 2: an envelope voided while a recipient holds a live `AUTH_PASSED` session → the session is revoked and a subsequent commit is rejected.
