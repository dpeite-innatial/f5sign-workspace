# TASK-010 — Event log, Stage 0: kernel-contract prep (still on `platform.outbox`)

| Field | Value |
|-------|-------|
| **Status** | **✅ Shipped** — stage 0 of the event-log substrate; merged to master (the full substrate landed 2026-07-01…07-03, stages 0–2). This is the **as-planned** build record; the one as-built divergence is noted in *Decision record* below. Green bar was `make qa` (PHPStan L9 · Deptrac 0 · lint · full suite) after **each** of the 4 steps. |
| **Type** | **Build plan (forward).** Stage 0 of the platform event-log substrate — the wide-but-shallow **kernel-contract sweep**, done *before* the store changes and *with no dual-write*: producers keep writing `platform.outbox` throughout. |
| **Part of** | The event-log substrate — derivation and floor in [ADR-0030](../adr/ADR-0030-record-first-event-floor.md), store in [ADR-0031](../adr/ADR-0031-event-log-store.md). This is **stage 0 of 4**: `0 (this) → 1a append-spike → 1b cutover → 2 sunset`; stages 1a+1b were the no-dual-write step, stage 2 the sunset. <!-- OFFREPO: the `§13A`–`§13G` / `§10.4` / `S1`/`S2` markers throughout this doc indexed a workspace scratchpad (`EVENT-LOG-SUBSTRATE.md`) that has been retired and is NOT followable; the ADRs above carry what survived. --> |
| **Delivery bar** | The kernel event contracts are the **new shape** — serialization on the `Event` floor, a **declared stable `eventType()`**, and the **ADR-0003 synchronous audit path deleted** — while every producer still persists to `platform.outbox` and the full suite stays green. **Zero wire-behavior change** (event-type names identical, guarded by a seed-fidelity test). *(The `streamKey()` rename — originally step 3 — is **deferred to stage 1a/1b**; see step 3 below.)* |
| **Blast radius** | Kernel event contracts + ~12 concrete events + 3 repositories + the retirement of the sync-audit path. **No store, no migration, no producer repoint** (those are 1a/1b). Safe because the outbox path is untouched as a sink. |
| **Decision record** | Seeds **ADR-0030** (record-first floor + the stage-0 contract deltas). *(As-built: ADR-0030 explicitly does **not** supersede ADR-0003 — it covers only the kernel floor; **ADR-0003 is Superseded by [ADR-0031](../adr/ADR-0031-event-log-store.md)** (the event-log store), when the same-tx append replaced the sync path in stage 1b.)* |

---

## 1. Why this task exists

The event-log design was fully settled before any of it was built, and the build was sequenced deliberately to keep the blast radius from ever being "new contracts × new store" at once. **Stage 0 is the contract half, done in isolation:** evolve the kernel event ontology to the log-first shape while the shipped outbox still absorbs the writes, so this large-surface-but-low-risk sweep lands and goes green on its own — before the novel storage mechanism (the `SECURITY DEFINER` append fn + commitment, stage 1a) exists.

The through-line for every change here: **record-first / react-later** — every fact serializes, carries a stable permanent-contract name, and is recorded uniformly; "witnesses a state transition" vs "is a forensic observation" survives only as a *property of the fact's type*, never as a storage destination. That collapses the DomainEvent-vs-ActivityLogEntry storage fork and retires the synchronous audit route ADR-0003 built to compensate for the absence of a system-of-record log.

## 2. What will be built (steps 1, 2, 4 — each green on `make qa`; step 3 deferred to 1a/1b)

Order is chosen so each step compiles + tests green standing alone.

### Step 1 — declared stable `eventType()` on the `Event` floor (behavior-neutral)

**Contract.** `event_type` becomes a **stable, explicitly-declared, permanent-contract id**, not derived from the class name (a class rename must never change the stored type — it would break replay/upcasting/the chain once the log is permanent).

- Add `eventType(): string` to `Kernel/Event/Event.php`. **Lean: an interface method backed by a `public const string EVENT_TYPE` per event** (structural enforcement — the type system forces every event to declare its name; greppable), over a `#[EventType]` attribute (not type-enforced). Trait vs per-class const is a build-time call.
- **Seed each event's const from today's derived value** so the wire name is *identical*: `EventTypeNaming::nameForClass()` currently yields `UPPER_SNAKE` of the short class name, and ADR-0011 guarantees that reproduces every hand-written `AuditableEvent::type()` exactly. Copy those literals in.
- `Foundation/Serialization/EventTypeRegistry::nameFor($event)` reads `$event->eventType()` instead of class-deriving.
- **Drop `AuditableEvent::type()`** — subsumed by the floor `eventType()` (it *was* this value already).
- **Surface:** ~12 concrete events (Envelope: `DocumentAddedToEnvelope`, `EnvelopeCompleted`, `EnvelopeCreated`, `EnvelopeReadyToSeal`, `EnvelopeSent`, `RecipientCompleted`, `RecipientStepActivated`, `StepCompleted`; Session: `SessionCompleted`, `SignatureCommitted`; SE: `DocumentSigned`, `EnvelopeSealed`) + `Event`, `AuditableEvent`, `EventTypeRegistry`.
- **Green + a new seed-fidelity test:** assert `$event->eventType() === EventTypeNaming::nameForClass($event::class)` for every registered event — this *locks* the zero-wire-change guarantee at cutover (and can be deleted with `nameForClass` in stage 2).

### Step 2 — `SelfSerializing` down to the `Event` floor

**Contract.** Serialization is a property of *being a recordable fact*, now universal (record-first). The old rationale — "keep it off the floor so non-transported facts needn't carry a codec" — is **reversed**: everything logged serializes.

- Move `extends SelfSerializing` from `DomainEvent` **up** to `Event` (`interface Event extends SelfSerializing`); remove it from `DomainEvent` (inherited).
- **Rewrite the docblocks** on `Event`, `DomainEvent`, `SelfSerializing`, `ActivityLogEntry` to the record-first rationale. *This prose is the real work of the step* — the signatures barely move.
- `ActivityLogEntry` (interface-only, no concrete impls yet): drop its ad-hoc `payload(): array`; it now inherits `toPayload()`/`fromPayload()` from the floor (its `eventType()` is satisfied by step 1's floor method).
- **Surface:** 4 interface docblocks. **No concrete-event change** — they already implement `SelfSerializing` via `DomainEvent`. Green.

### Step 3 — `streamKey()` rename → 🔵 DEFERRED to stage 1a/1b (user's call 2026-07-01)

**Finding that drove the deferral.** The task originally assumed a mechanical rename `AuditableEvent::envelopeId(): EntityId` → `streamKey(): ?EntityId`. Reading the code first showed it is **not** mechanical:

- `envelopeId()` is documented as *"the subject aggregate's identifier"* and in fact returns **exactly what `subject()` returns** for all 6 events — it is **redundant with `subject()`**.
- For `SignatureCommitted` it returns the **session id, not the envelope**; the envelope lives only in `payload['envelope_id']` (the event's own docblock: *"the envelope the chain keys on travels in payload()"*).
- The §13 design wants `streamKey()` to be the **envelope/stream, genuinely distinct from subject** (it is what the per-envelope log projection keys on via `stream_id`). So the real F7 fix **pulls the envelope out of the payload into a first-class accessor** — a semantic change (plus a type wrinkle: `SignatureCommitted`'s envelope is an `EnvelopeRef`, not an `EntityId`), not a rename.

**Why defer.** Nothing at stage 0 consumes `streamKey()`'s value (the outbox writes `subject_id`/`tenant_id`). Its value only becomes load-bearing when the **log projection reads `stream_id` (stage 1a/1b)**. Doing the rename **and** the correct envelope-stream semantics together there — tested against the real projection — is cleaner than enshrining a placeholder now. Stage 0 stays purely mechanical (steps 1, 2, 4). *(The `Envelope`/`Recipient`/`Document`/`Step` aggregate `envelopeId()` accessors are a different method — untouched regardless.)*

### Step 4 — retire the ADR-0003 synchronous audit path

**Contract.** ADR-0003's guarantee ("no act commits without its record") **survives as the same-tx append** — which the normal outbox drain already provides. The synchronous `record()` route was compensating for the log's absence and is now redundant.

- **Delete:** `EvidenceAudit/Contract/Command/AuditCommandInterface`, `EvidenceAudit/Infrastructure/Adapter/InMemoryAuditCommandAdapter`, and `AggregateRoot::peekAuditableEvents()`.
- **Rewire** `Session/Application/UseCase/CommitSignatureUseCase` — remove the sync-record call; `SignatureCommitted` still reaches the outbox via the aggregate's normal `recordEvent → pullEvents` drain (confirm it is recorded to the aggregate, not *only* sync-recorded).
- **ADR bookkeeping:** author **ADR-0030** (record-first floor + the stage-0 contract shape — the in-repo supersession target, since in-repo ADRs may not cite the design repo); mark **ADR-0003 `Superseded` by ADR-0030**; update the ADR README index/graph.
- **Test surface (rework, don't just delete green):**
  - `tests/…/EvidenceAudit/Fake/RecordingAuditCommand.php` + `ThrowingAuditCommandAdapter.php` — delete (fakes for the removed port).
  - `tests/…/Envelope/Scenario/AuditFaultPropagationTest.php` — **this is the ADR-0003 audit-fail-rolls-back property.** The property itself (a failed record rolls back the transition) now holds via the same-tx append; it gets its real exercise in **stage 1a** (the append + tamper/omission property test). Here: retire or restate it as "the event reaches the outbox in the same tx" — do not silently drop the guarantee.
  - `tests/…/Kernel/Unit/Entity/AggregateRootTest.php` — drop the `peekAuditableEvents` cases.
  - `tests/…/Session/Handler/…/CommitSignatureUseCaseTest.php` — update to the outbox-only expectation.
- Green.

## 3. Scope

**In scope (this task):** the 4 steps above — declared `eventType()` (+ seed-fidelity test); `SelfSerializing`→floor (+ docblock rewrites); `streamKey()` rename; ADR-0003 sync-path deletion + `CommitSignatureUseCase` rewire; ADR-0030 seed + ADR-0003 supersession + README update; the test reworks named in step 4.

**Out of scope (later stages — named so they're not silently assumed):**
- **`record()` unify** (`recordEvent`/`recordActivityLogEntry` → one `record(Event)`) and the **dual-drain collapse** (`pullEvents`+`pullActivityLogEntries` → `pullPendingEvents(): Event[]`) — **stage 1b**, because the `Event[]` return pairs with `EventLog::append(Event)`. Stage 0 leaves the dual-drain in place (activity entries are unbuilt, so the drain-and-discard is a no-op).
- **`EventLog` port, `platform.event_log`, `append_event()` DEFINER fn, `IssuerContext` + actor stamping, checkpoint/dead-letter, the tamper/omission property test** — **stage 1a** (the append spike; where §10.8 commitment + §10.9 access get exercise-locked).
- **Repoint the 3 repos, the SE detached-append fix, the watermark relay** — **stage 1b** (the cutover). The **§13D gate** (verify the async relocation of Envelope completion vs ADR-0027) precedes 1b.
- **Sunset `platform.outbox` / `OutboxWriter` / old relay / grants / `EventTypeNaming::nameForClass`** — **stage 2**.
- **The `streamKey()` rename (was step 3)** — **stage 1a/1b**, done together with its real envelope-stream semantics + the `stream_id` projection that consumes it (see step 3 finding above).
- **Removing `AuditableEvent`** — assumed likely, deferred, reevaluated during the build (§Key decisions).

## 4. Key decisions

- **Locked leans (2026-07-01, at design time):** `record()`-unify · `streamKey()` nullable · actor = ambient `IssuerContext` · staged sequencing. Only `streamKey`-nullable is *exercised* in stage 0; the rest land later. *(As-built note: the shipped floor signature is `streamKey(): ?string`, not `?EntityId` — see [`Event`](../../src/F5Sign/Kernel/Event/Event.php), whose docblock carries the reasoning.)*
- **`AuditableEvent`'s fate — assume-removal, defer, reevaluate-during-build (user's call).** With `type()`→`eventType()` and `envelopeId()`→`streamKey()` leaving, it's down to `emittingContext()` + `payload()`; most likely it folds into `DomainEvent` + a marker. **Stage 0 does not remove it** — the `streamKey()` rename's content survives any later host relocation, so renaming it here is not throwaway; the removal is a build-informed follow-on once real `stream_id`/`emittingContext`/`payload` usage is visible across producers + the projector.
- **`eventType()` home = `Event` floor, not `SelfSerializing`.** Commands opt into `SelfSerializing` too but have no event-type registry key — putting it on `Event` keeps it an event concern and off commands.
- **Behavior-neutrality is a *tested* invariant, not a claim.** The seed-fidelity test (step 1) locks that no wire event-type name changed at cutover; it retires with `nameForClass` in stage 2.
- **ADR-0030 now vs a `Superseded`-pending stub.** In-repo ADRs can't cite the design-repo substrate, so ADR-0003 needs an in-repo supersession target. **Lean: author a focused ADR-0030** (record-first floor + the stage-0 kernel-contract deltas) now; the fuller substrate (append fn, commitment, cutover) graduates across the ADR-0024/0027 amendments in stages 1a/1b. *(Confirm the ADR-0030 scope when building — focused-now vs comprehensive.)*

## 5. Verification

- `make qa` green after **each** step (PHPStan L9 · Deptrac 0 · lint · full suite).
- The **seed-fidelity test** passes for every registered event (zero wire-name drift).
- The ADR-0003 guarantee is **restated, not dropped** — the `AuditFaultPropagationTest` rework asserts same-tx co-commit, with the full tamper/omission lock deferred to stage 1a.
- No change to `platform.outbox`, its schema, or the relay; producers still write it.
