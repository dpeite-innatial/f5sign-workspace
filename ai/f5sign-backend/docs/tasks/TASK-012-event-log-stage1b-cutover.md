# TASK-012 — Event log, Stage 1b: the cutover (producers → the log, retire the sync audit path)

<!-- OFFREPO: the `§10.x` / `§13x` / `§14` / `F7` markers reference the workspace design doc `EVENT-LOG-SUBSTRATE.md` and its planning-intent set (not in this repo). The landed decisions have their in-repo home in ADR-0031 (the store) and the ADRs amended below; this doc is design-trail, so the markers are kept as native vocabulary. -->

| Field | Value |
|-------|-------|
| **Status** | **✅ Shipped** — stage 1b, the cutover; merged to master (2026-07-01, commit `618882b`). This is the **as-planned** build record; §5.1 is the as-built coverage note. Builds on [TASK-011](TASK-011-event-log-stage1a-append-spike.md) (the append spike) + [TASK-010](TASK-010-event-log-stage0-kernel-contract-prep.md) (the record-first floor). |
| **Type** | **Build (forward) — the store cutover.** Stage 1b of the event-log substrate (`platform.event_log` = §10.4 S1). Repoint every producer off the transactional outbox and onto `EventLog::append`, retire the synchronous audit path (ADR-0003), fix the SignatureExecution inline dispatch, and swap the outbox relay for a watermark relay over the log. **Zero dual-write** (§10.4 option C): producers cut over in one coordinated slice, the outbox is left *dead* (dropped in stage 2), never dual-stored. |
| **Part of** | Branch `feat/event-log` (backend). **Backend-only** — the `f5sign_relay` role already holds `SELECT` on `event_log` + `event_checkpoint` + `event_dead_letter` (granted by the stage-1a migration), so no infra change. Substrate design: [ADR-0031](../adr/ADR-0031-event-log-store.md) (the relay/watermark model and the no-dual-write cutover); the derivation behind it is [ADR-0030](../adr/ADR-0030-record-first-event-floor.md) § Context. |
| **Delivery bar** | Every domain event and observation is appended to `platform.event_log` in the command's transaction (via the repository drain + `EventLog::append`), with `stream_id`, `actor`, and `actor_kind` populated. The **watermark `EventRelay`** drains the log (xid8 low-water-mark cursor over `event_checkpoint`) and publishes to the existing `event.bus` / AMQP, with poison → `event_dead_letter`. The synchronous audit path (ADR-0003) is **gone** — its rollback guarantee is preserved by the same-tx append. SignatureExecution's three inline `eventBus->dispatch(...)` sites append to the log instead. The full seal loop runs green end-to-end (now fully async). `platform.outbox` is untouched but **dead** (no writer, no relay) — dropped in stage 2. |
| **Blast radius** | Large but bounded. **Kernel:** `AggregateRoot` drain-collapse (`record(Event)` + `pullPendingEvents(): Event[]`, delete `peekAuditableEvents`), `streamKey()` on the event floor/`AuditableEvent` (F7). **Producers:** 2 drain repositories (1 Session + 1 Envelope), 3 SignatureExecution use-cases. **Retirements:** `AuditCommandInterface` + `InMemoryAuditCommandAdapter` + 9 `audit->record()` call-sites + 2 test fakes; `OutboxWriter` stops being called (dropped in stage 2). **New:** `EventRelay` + `SetIssuerMiddleware`. **ADRs:** 0003 → Superseded; 0024 major amend; 0027 (SE seam lands, loop fully async); 0010 (middleware order); 0015 (relay resilience/DLQ); 0031 status bump (producers live). Does **not** drop the outbox table (stage 2). |
| **Decision record** | ADR-0003 → **Superseded** (sync record replaced by same-tx append). ADR-0024 **major amend** (delivery is now a watermark projection over the permanent log, not a transient buffer). ADR-0027 **discharged-in-part** (the no-aggregate producer seam lands; the loop goes fully async — this is the deferral ADR-0027 itself names). ADR-0031 **status bump** (from "no producer writes it yet" to live) + the relay/watermark decision. See §4 for the open calls. |

---

## 1. Why this task exists

Stage 1a built and exercise-locked the store in isolation. Stage 1b makes it *the* system of record: every fact flows through `EventLog::append`, and the transient outbox stops being written. Three things collapse into that single append:

1. **The transactional outbox** (ADR-0024) — the `OutboxWriter::write` in each repository drain becomes `EventLog::append`. Delivery stops being a mutable row-state (`status`/`attempt_count`/`published_at`) and becomes a **watermark projection** over the immutable log.
2. **The synchronous audit path** (ADR-0003) — the 9 `audit->record($event)` calls that run *before* `save()` are deleted. The log **is** Audit; an evidence artifact is a projection. The audit-fail-rolls-back guarantee is preserved because the append is in the same transaction as the state change (a throw aborts the tx).
3. **SignatureExecution's inline dispatch** — SE is aggregate-less and today fires `EnvelopeSealed` / `DocumentSigned` inline on the event bus, bypassing durable recording entirely (a live defect). A first-class **detached append** (`EventLog::append` needs no aggregate) fixes it. ADR-0027 already names this as owed and marks the loop "half-async until the seam lands."

The diagnostic that recurs: each of these needed its own special mechanism (outbox buffer, sync audit port, inline dispatch); log-first needs **none** — each is just `append(fact)`.

## 2. What will be built

Blast radius is never "new contracts × new store" — stage 1a proved the store; this stage repoints onto it. Two **additive precursors** land green on their own, then a **coordinated core** (relay + repoint + drain-collapse + sync-retire must land together to keep the async loop working), then the SE fix and test rework.

### 2.1 Precursor — `streamKey()` (F7)

`AuditableEvent::envelopeId(): EntityId` returns the event's **subject** (≡ `subject()`) — redundant, and *wrong* for the stream: for `SignatureCommitted` the subject is the **session** id, while the envelope (the correlation root of the signing stream) lives in the payload. Rename/replace it with **`streamKey(): ?EntityId`** — the contextual correlation root (the envelope), nullable (NULL outside any envelope context, e.g. a platform fact).

- Envelope events (`EnvelopeCreated`, `EnvelopeSent`, `EnvelopeReadyToSeal`, `EnvelopeCompleted`, `StepCompleted`) → the envelope id (= their subject).
- `SignatureCommitted` (Session) → the **envelope** id (currently in payload), **not** the session subject.
- SE events (`EnvelopeSealed`, `DocumentSigned`) → the envelope id.
- Non-envelope / platform facts → `NULL`.

`DbalEventLog::append` reads it and populates `stream_id` (currently written `NULL`). **See §4 for where `streamKey()` lives** (floor vs `AuditableEvent`).

### 2.2 Precursor — `SetIssuerMiddleware`

Mirror [`SetTenantIdMiddleware`](../../src/F5Sign/Foundation/Bus/SetTenantIdMiddleware.php): a `command.bus` middleware that lifts the command's issuer (commands are `Issued`) into [`IssuerContext`](../../src/F5Sign/Foundation/Actor/IssuerContext.php), so the append during that command's `save()` stamps `actor`/`actor_kind` from it. Register on `command.bus` per the ADR-0010 order contract (alongside `SetTenantIdMiddleware`, before `doctrine_transaction`). Additive — `IssuerContext` is populated but only *read* once producers repoint (the 1a append already reads it if set). **Unlike tenancy, likely no cross-broker stamp** is needed (each follow-up command re-declares its own issuer via the reactor) — confirm in §4.

### 2.3 Core cutover (lands as a unit — the async loop must stay green)

**a. Drain-collapse on `AggregateRoot`** ([`src/F5Sign/Kernel/Entity/AggregateRoot.php`](../../src/F5Sign/Kernel/Entity/AggregateRoot.php)). Today it drains **two** buffers via a three-pull discipline: `pullEvents(): DomainEvent[]` (→ outbox), `peekAuditableEvents(): AuditableEvent[]` (→ sync audit, peek-not-drain), `pullActivityLogEntries(): ActivityLogEntry[]` (forensic, drained + discarded). Under record-first (stage 0 made `ActivityLogEntry` serialize via the floor) they unify: one buffer of `Event`, `record(Event)` replacing `recordEvent`/`recordActivityLogEntry`, **`pullPendingEvents(): Event[]`** replacing the two pulls, and **`peekAuditableEvents()` deleted** (the audit peek is subsumed — everything appends). Observations now persist to the log too ("log everything"); today's slice records none, so the addition is structural. *(As-built naming: the buffer is `$pendingEvents` and the drain `pullPendingEvents()`, not "recorded" — at buffer time the facts are staged, **pending** their append; the log's `append()` is where they become durably **recorded**. The `record()` verb stays, per ADR-0030's record-first vocabulary — the aggregate's act of recording that something happened.)*

**b. The watermark `EventRelay`** (Foundation). Replace `OutboxRelay`'s `SELECT ... WHERE status='pending' ORDER BY sys_sequence FOR UPDATE SKIP LOCKED` (the immutable log has no `status` column) with the §10.1 mechanism: read rows whose `sys_transaction_id` is at/after the checkpoint's `last_transaction_id` **and** below `pg_snapshot_xmin(pg_current_snapshot())` (the low-water-mark that skips in-flight transactions), `ORDER BY sys_transaction_id, sys_global_position`; dispatch each to `event.bus` (reusing the existing reconstruction + `AmqpStamp` routing-key + `TenantStamp` logic); advance `event_checkpoint (consumer, last_transaction_id, last_global_position)`; poison → `event_dead_letter` after N attempts. Delivery becomes **at-least-once** (a crash between dispatch and checkpoint-advance re-delivers) — consumers are already idempotent (outbox was too). Publishes to the unchanged `event.bus` / `async_events` AMQP; the 4 reactor subscribers and `ReestablishTenantMiddleware` are untouched.

**c. Repoint the drain repositories** — swap `outbox->write($event)` for `eventLog->append($event)` over `pullPendingEvents()`:
- [`DbalSigningSessionRepository`](../../src/F5Sign/Session/Infrastructure/Persistence/Doctrine/DbalSigningSessionRepository.php) `save()`
- [`DbalEnvelopeRepository`](../../src/F5Sign/Envelope/Infrastructure/Persistence/Doctrine/DbalEnvelopeRepository.php) `save()`

*(As-built: **2** repositories. At plan time there were two Envelope adapters — the ORM one plus the ADR-0018 DBAL head-to-head; the ORM adapter is gone (ADR-0018), so only `DbalEnvelopeRepository` remains.)*

Same transaction as the aggregate persist (INT-1 preserved). `OutboxWriter` is now uncalled (deleted in stage 2). Stop the old `OutboxRelay` worker; start the `EventRelay` worker.

**d. Retire the ADR-0003 sync path** (couples with the repoint — the append inherits the guarantee). Delete the 9 `audit->record($event)` call-sites (each a `foreach peekAuditableEvents()` block before `save()`), delete `AuditCommandInterface` + `InMemoryAuditCommandAdapter` + its services.yaml alias, delete the `RecordingAuditCommand` / `ThrowingAuditCommandAdapter` fakes. The 9 use-cases:

| BC | Use-case | file |
|----|----------|------|
| Session | `CommitSignatureUseCase` | `Session/Application/UseCase/CommitSignatureUseCase.php` |
| Envelope | `CreateEnvelopeUseCase` | `Envelope/Application/UseCase/Authoring/CreateEnvelopeUseCase.php` |
| Envelope | `AddDocumentUseCase` | `Envelope/Application/UseCase/Authoring/AddDocumentUseCase.php` |
| Envelope | `AddStepUseCase` | `Envelope/Application/UseCase/Authoring/AddStepUseCase.php` |
| Envelope | `AddRecipientUseCase` | `Envelope/Application/UseCase/Authoring/AddRecipientUseCase.php` |
| Envelope | `UploadDocumentBytesUseCase` | `Envelope/Application/UseCase/Authoring/UploadDocumentBytesUseCase.php` |
| Envelope | `SendEnvelopeUseCase` | `Envelope/Application/UseCase/Lifecycle/SendEnvelopeUseCase.php` |
| Envelope | `CompleteEnvelopeUseCase` | `Envelope/Application/UseCase/Lifecycle/CompleteEnvelopeUseCase.php` |
| Envelope | `RecordRecipientCompletionUseCase` | `Envelope/Application/UseCase/Lifecycle/RecordRecipientCompletionUseCase.php` |

Rework [`AuditFaultPropagationTest`](../../tests/F5Sign/Integration/AuditFaultPropagationTest.php): its guarantee ("an audit failure aborts the pipeline, no state leaks") **restates** as "an `EventLog::append` failure aborts the same transaction, no envelope row persists" — now a *real* same-tx rollback (stronger than the old before-save ordering trick). Mark **ADR-0003 → Superseded**.

### 2.4 SignatureExecution detached-append fix

Replace the three inline `eventBus->dispatch(...)` sites with `eventLog->append(...)` (SE stays aggregate-less — the append needs no aggregate):
- [`SealEnvelopeUseCase`](../../src/F5Sign/SignatureExecution/Application/UseCase/SealEnvelopeUseCase.php) — `EnvelopeSealed`
- [`SealDocumentUseCase`](../../src/F5Sign/SignatureExecution/Application/UseCase/SealDocumentUseCase.php) — `DocumentSigned`
- [`MockSignUseCase`](../../src/F5Sign/SignatureExecution/Application/UseCase/MockSignUseCase.php) — `DocumentSigned`

This relocates SE-driven Envelope completion from **sync → one relay-tick later**. ADR-0027 already anticipates it (its deferred section: "make `EnvelopeSealed`/`DocumentSigned` ride the outbox, not an inline dispatch") — so the gate is pre-cleared; the seal loop simply becomes fully async. `EnvelopeSealed`/`DocumentSigned` must satisfy the `Event` floor (they already carry `eventType`/`subject`/`occurredAt`/`toPayload`).

### 2.5 ADRs

ADR-0003 → Superseded; ADR-0024 major amend (delivery = watermark projection over the permanent log); ADR-0027 discharged-in-part (SE seam lands, loop fully async); ADR-0010 (add `SetIssuerMiddleware` to the order contract); ADR-0015 (the relay's DLQ/retry realized over `event_dead_letter`); ADR-0031 status bump (producers live) + the relay decision. README index/graph updated.

## 3. Scope

**In (this task):** `streamKey()` (F7) + the 6 events; `SetIssuerMiddleware` + registration; the `AggregateRoot` drain-collapse; the watermark `EventRelay` + worker wiring; repoint the 3 repositories; retire the ADR-0003 sync path (9 call-sites + port + adapter + 2 fakes + test rework); the SE 3-site detached-append fix; the ADR set; tests (append-via-save per BC, the reworked fault-propagation test, the relay watermark/poison tests, an SE-appends-to-log test, an end-to-end seal-loop test).

**Out (later / deferred — named so they are not silently assumed):**
- **Stage 2 sunset:** drop `platform.outbox`, delete `OutboxWriter` + `OutboxRelay` + the outbox migration's grants. (1b leaves them dead but present.)
- **Merkle / external anchoring, cipher-at-capture (Path A PII), partitioning** (firehose-tier rebuild), the **evidence projector / activity views** — deferred (the log is the substrate they read).
- **`correlation_id` / `causation_id`** tracing columns — additive-safe future enhancement.

## 4. Key decisions (open — resolve at build)

- **Where `streamKey()` lives.** *Lean: the `Event` floor as `streamKey(): ?EntityId` (default via each concrete event)* — the append is floor-typed and record-first records any fact, and SE events (not `AuditableEvent`) also need a stream root, so an `AuditableEvent`-only home would leave their `stream_id` NULL. Cost: every concrete event implements it (mostly `return $this->subject()` or `null`). Alternative: keep it on `AuditableEvent` + `instanceof` in `DbalEventLog` (matches the §13A note, fewer files, but SE events get no `stream_id`). **Confirm against the real event set at build.**
- **`AuditableEvent`'s fate (§13F #5).** Assume-removal-likely, deferred: once `record()`/the audit port are gone and `payload()` is subsumed by the floor `toPayload()`, `AuditableEvent` may reduce to a marker (observation-vs-transition) or fold into `DomainEvent`. Let the streamKey decision + the retirement inform it; don't pre-commit.
- **No `IssuerStamp` across the broker (lean).** Tenancy needs `TenantStamp` because RLS scope must survive the hop; the issuer does not — each consumed event triggers a follow-up *command* whose own issuer (a `SystemActorId`, e.g. `subscriber:OnEnvelopeSealed`) `SetIssuerMiddleware` lifts. Confirm no append happens on the raw consume hop (before a command) that would need the originating actor.
- **Single-consumer watermark vs multi-worker.** The outbox relay used `SKIP LOCKED` for N workers; the checkpoint watermark is **one advancing cursor per `consumer` key**. MVP runs one relay worker. Note the constraint (don't silently assume the old multi-worker parallelism); horizontal scaling is a partition-by-consumer future concern.
- **SE async-relocation gate — pre-cleared.** ADR-0027's deferred section already calls for exactly this move; the seal loop going fully async is the documented plan, not a regression. Verify the end-to-end seal-loop test still completes (one relay-tick later).
- **One commit.** Per the per-task-commit workflow, 1b lands as ONE green commit on `feat/event-log` (backend-only; no infra branch — the relay role's grants already exist from 1a).

## 5. Verification

- `make qa` green (PHPStan L9 · Deptrac 0 · lint · full suite).
- Each producing BC has a test that a use-case's `save()` **appends the fact to `event_log`** (read back via the relay connection) with `stream_id`/`actor`/`actor_kind` correct — and writes **nothing** to `platform.outbox`.
- The reworked `AuditFaultPropagationTest` proves an `EventLog::append` failure **aborts the transaction** — no envelope row persists (real same-tx rollback).
- The `EventRelay` tests: the watermark advances correctly, an in-flight transaction is **not** skipped past (low-water-mark), and a poison event lands in `event_dead_letter` without wedging the relay.
- An SE test proves `SealEnvelopeUseCase` / `SealDocumentUseCase` **append** to the log (no inline dispatch).
- An end-to-end seal-loop test completes fully async (append → relay → reactor → completion) — ADR-0027's loop, now with no inline hop.
- `platform.outbox` receives no new rows; the old `OutboxRelay` worker is retired.

### 5.1 Coverage status (as built, 2026-07-01)

`make qa` green — full suite (incl. `EventRelayTest` + the reworked flow/handler/unit tests). Line coverage of the net-new event-log code:

| Class | Lines | Note |
|-------|-------|------|
| `DbalEventLog` · `CanonicalJsonPayloadCodec` · `EventLogCommitment` · `ActorKind` · `IssuerContext` · `SetIssuerMiddleware` | **100%** | |
| `EventRelay` | **93.55%** (58/62) | poison/dead-letter path **covered** (`EventRelayTest` — dead-letters, climbs attempts, quarantines-at-MAX, doesn't wedge) |

**Deferred-with-awareness (not silently dropped — revisit at stage 2 / sunset):**
- **Low-water-mark adversarial test** — proving the watermark holds back a *late-committing in-flight* transaction (never skips it) needs a **third DB connection holding an open xid**, which the current test harness doesn't cleanly provide. The mechanism is exercised implicitly (the e2e loops converge deterministically) but not adversarially asserted. §5's "in-flight transaction is not skipped past" bar is therefore **partially met** (implicit, not adversarial).
- **`EventRelay` uncovered lines (4):** the `catch (Throwable) { rollBack; throw }` connection-rollback path (135–138, needs a simulated mid-batch DB failure) and the `['0', 0]` no-checkpoint floor (158, deliberately unhit — every test seeds its checkpoint for per-test isolation; it is the real production first-run path). Both are defensive/edge branches, low value to force — consistent with the repo's established "uncovered = defensive branches needing simulated infra failure" convention.
