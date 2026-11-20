# TASK-009 — Evidence & Audit persistence: the hash-chained audit trail (and the identity tension it surfaces)

> **⚠️ Direction superseded (2026-06-29 reframe; realized on the `feat/event-log` branch) — read the tensions here for the *why*; the resolution is [§9](#9-resolution--inherited-design-constraints-event-log-reframe) below.** The tensions (esp. **§4.0** same-tx-vs-isolation) drove a reframe: the audit trail is **not an aggregate** but a **projection** over a **platform-wide append-only event log as the system of record** ([ADR-0030](../adr/ADR-0030-record-first-event-floor.md) / [ADR-0031](../adr/ADR-0031-event-log-store.md)). **§4.0's platform-escape, the sync `record()` port, and its emitter call-sites are superseded** — retired on the event-log branch; the durability guarantee now rides the same-tx `EventLog::append`, and facts flow through the log's watermark relay (the transactional outbox is gone). The §4 tensions remain the load-bearing *why*; **their resolution — and the design constraints the future evidence-projector inherits — are captured durably in [§9](#9-resolution--inherited-design-constraints-event-log-reframe)** (previously these lived only in temporal design scratchpads).

| Field | Value |
|-------|-------|
| **Status** | **Superseded design record.** The original write-time hash-chain-*aggregate* design was **dissolved** by the event-log reframe ([§9](#9-resolution--inherited-design-constraints-event-log-reframe)); the substrate it now rests on shipped ([ADR-0030](../adr/ADR-0030-record-first-event-floor.md)/[ADR-0031](../adr/ADR-0031-event-log-store.md)). The E&A **evidence projector** it feeds is deferred — its scope doc is [TASK-014](TASK-014-evidence-audit-projector.md). Read §4 for the load-bearing *why*, §9 for the resolution + the constraints the projector inherits. |
| **Type** | Forward design + build. The first substantive build-out of the **Evidence & Audit BC** — which, since the event-log reframe (stage 1b), has **no `src/F5Sign/EvidenceAudit/` code**: the old `AuditCommandInterface` + `InMemoryAuditCommandAdapter` stub was removed, leaving only the kernel `AuditableEvent` marker. |
| **Builds on** | [TASK-008](TASK-008-signing-session-recipient-ceremony.md) (the signing ceremony that now *emits* auditable + evidence facts with nowhere to persist), [ADR-0003](../adr/ADR-0003-synchronous-pre-commit-audit-recording.md) (the sync-pre-commit discipline this realizes), [ADR-0024](../adr/ADR-0024-event-delivery-transactional-outbox.md) (the outbox build whose DBAL-writer + per-column-GRANT + RLS migration pattern is the template). |
| **Design grounding** | In-repo [`docs/ddd/evidence-audit-domain-model.md`](../ddd/evidence-audit-domain-model.md) (authoritative *what* under the agent-only premise); design-repo `04 - Evidence and Audit BC.md` (*why*). |
| **Delivery bar (slice 1)** | The 8 already-wired `record()` call sites persist a real, hash-chained, tamper-evident `audit_event` chain per envelope, under RLS, **in the same transaction** as the aggregate save + outbox row — finally **falsifying ADR-0003 invariant 1b** (atomicity-as-participant), which is unfalsifiable today. |

---

## 1. Why this task exists

The signing workflow is end-to-end complete (create → send → sign → seal → COMPLETED). But the **Evidence & Audit BC is a stub**: the sync audit port `AuditCommandInterface::record()` is already called by **8 legally-material transitions** —

```
CreateEnvelope · AddDocument · AddStep · AddRecipient · SendEnvelope
RecordRecipientCompletion · CompleteEnvelope · CommitSignature (the signing act)
```

— and every call lands in an in-memory array that is discarded. The consent + signer IP/UA captured on the session row in TASK-008 likewise have **no home**. For an e-signature product the **hash-chained audit trail + evidence packet *is* the legal product** ("their integrity *is* the product's evidentiary value" — domain-model §Domain).

Persisting it is the natural next move and a small *mechanical* delta — one new adapter + one migration, no call-site changes. **But it surfaces an architectural tension** (§4) that is the real reason this file exists: the audit chain's natural shape runs head-on into the identity + schema discipline the whole codebase is built on.

## 2. Design grounding (what the BC is)

Two distinct-but-bound halves, three aggregates (domain-model §Aggregates):

| Aggregate | Identity (per design) | What it is | Slice |
|---|---|---|---|
| **EnvelopeAuditLog** + `AuditEvent` (child) | root `envelopeId`; child **`(envelopeId, sequence)`** | Per-envelope **append-only hash chain** of legally-material events. Root holds `lastSequence` + `lastHash`; appends serialize via `SELECT FOR UPDATE` on the root. | **1 (this task)** |
| **RecipientEvidenceLog** + `EvidenceEntry` (child) | root **`(recipientId, envelopeId)`**; child `entryId` polymorphic by `kind` | Per-recipient evidence capture (consent / auth / IP-UA / geo / device / biometric). The `EvidenceCollectorInterface` Session calls at commit. | 2 |
| **BiometricEncryptionKeyPair** | `keyId` | RSA-4096 cipher pair + custodian; ≤1 ACTIVE per `(scope, tenantId)`. Gated on the **biometric feature = v2**. | v2 |

The hash chain (domain-model §UL): `hash_n = SHA256(envelopeId ‖ sequence ‖ eventType ‖ detail ‖ hashPrev_n)`, `sequence` monotonic `0..N` per envelope; a gap or out-of-order insert marks the trail "integrity compromised."

ADR-0003 binds the write: `record()` is called **synchronously, before commit, inside the emitter's command transaction** — the audit row, the aggregate state, and the outbox row are participants in the **same** `EntityManager` transaction; if `record()` throws, `doctrine_transaction` aborts everything (no state change, no bus event, no partial chain).

## 3. The slice-1 build (mechanically)

- **Migration** `envelope_audit_log` (root: `envelope_id` PK, `tenant_id`, `last_sequence`, `last_hash`) + `audit_event` (child: chain columns + `event_type`, `emitting_context`, `detail` jsonb, `hash`, `hash_prev`, `occurred_at`) — RLS + FORCE + policy on `current_tenant_id()`, per-column GRANTs. Template: `Version20260619000001` (the outbox migration — removed in ADR-0018's Phase-A clean-baseline rewrite; ADR-0019 §11's "never edit applied migrations" waived for it). **Schema placement (`platform.*` vs an E&A `domain/evidence_audit.*`) is gated by §4.0 / decision §7.0** — `platform.*` if the chain-append is platform infrastructure.
- **`DbalAuditCommandAdapter`** implementing `record()`: `SELECT … FOR UPDATE` the root (lazy-create on first event) → `sequence = last + 1` → compute `hash` → `INSERT audit_event` → `UPDATE` root tip — all on the **default DBAL connection**, so it joins the ambient `doctrine_transaction` (same pattern the `OutboxWriter` already uses).
- **Wire** it as the prod adapter; keep `InMemoryAuditCommandAdapter` for unit tests.
- **Lock** ADR-0003 invariant 1b: a test that makes `save()` fail *after* `record()` succeeds and asserts the `audit_event` row rolled back with the aggregate (the partial-commit substrate the design says "likely awaits the persistence build-out").

No `record()` call site changes. The chain key is read from `payload()['envelope_id']` (see the F7 note in §5).

---

## 4. ⚑ The architectural tensions (the reason for this artifact)

The tensions span the BC's three aggregates. **§4.0** — the audit write's *transaction/role* impossibility (the most fundamental: a flat impossibility-without-reframe). **§4.1–4.3** — the audit chain's *identity / ordering / unforgeability* axis (hard, but doable). **§4.4** — the evidence write recurs §4.0 *without* its escape (slice 2). **§4.5** — the platform biometric key vs the tenant-uniform RLS contract (v2).

### 4.0 — Same-transaction atomicity vs per-BC role/connection isolation *(the impossibility, with one escape)*

[ADR-0003](../adr/ADR-0003-synchronous-pre-commit-audit-recording.md) requires the audit insert and the aggregate state transition to share **one transaction** (single `EntityManager`, commit-or-rollback together). [ADR-0019](../adr/ADR-0019-database-schema-conventions.md) §1's *future* enforcement wants **per-BC DB roles + per-BC connections** so a BC physically cannot reach another BC's tables. These collide head-on:

> A DB transaction is bound to **one connection**; a connection authenticates as **one role**. So *"share a transaction"* ⟹ *"share a connection"* ⟹ *"same role."* You cannot have `role(state-transition) ≠ role(audit-write)` **and** one transaction.

Both naive escapes fail: **two coordinated connections (2PC/XA)** = the dual-write ADR-0003 forbids (audit commits while state rolls back); **one connection that `SET ROLE`s to E&A** = the BC role must be a *member* of E&A's role (can assume all its privileges) = isolation hole. And **async chaining** would give up ADR-0003 (chain must be durable+chained *before* the transition commits). So of {audit table is E&A-**private**, no other role touches E&A's schema, audit write in the **emitter's** tx}, one must give.

**Escape — the audit-append substrate is `platform`, not E&A-private (by ADR-0019 §1's own criterion).** §1 puts the outbox / command-queue / `current_tenant_id()` in `platform` *because every BC uses them*, and keeps activity-logs BC-local *because one BC writes them*. By that exact test the audit-append substrate **is platform** (every BC records legally-material events into one shared chain). "No cross-BC access" means *no access to another **BC's** schema*; `platform` is the shared exemption §1 already grants (every BC role already gets narrow `INSERT` on `platform.outbox`). So:

- **`platform.audit_event` + `platform.envelope_audit_log`** (chain head) — not `evidence_audit.*`.
- Written **in-band** by each BC's own role, in the emitter's tx, via **narrow per-column GRANTs** (the outbox model: `INSERT` on fact columns; `SELECT … FOR UPDATE` + `UPDATE` on the chain-head tip — nothing else).
- **E&A owns the *meaning*** (read side): classification of legally-material facts (per-BC `AuditableEvent`), chain verification, XAdES Audit-Trail-XML generation, retention, custody — exactly as the outbox table is `platform` while its events are BC-owned and a separate **relay** role owns the read/forward side.

Per-BC isolation survives: Session still can't see `envelope.*` / `evidence_audit.*`; it can only append to a shared `platform` log. **Today this is moot** (one `f5sign_app` role, one connection) — the conflict is only with §1's *future* per-BC roles. So we don't build the split now; we **place the tables in `platform` now** so the future split is GRANT-only, never a table move (precisely §1's "authored enforcement-ready, no future schema rework" discipline).

**The price (the real decision):** this splits *"the hash chain is E&A core domain"* into **mechanism vs meaning** — the tamper-evident append becomes a **Foundation capability** (sibling of `OutboxWriter`), and `AuditCommandInterface`'s *write* side lands in Foundation/platform while E&A keeps the semantics. If we won't call the chain-append "platform infrastructure," the reconciliation wobbles. *(Open decision §7.0.)*

### 4.1–4.3 — Identity / ordering / unforgeability

**The audit chain's natural identity + ordering shape is also the exact shape this codebase's identity discipline was built to forbid.** Three layers, surface → deep.

### Layer 1 — `(envelope_id, sequence)` identity is the Step composite, reincarnated *(precedented, resolvable)*

The design gives `AuditEvent` the identity **`(envelopeId, sequence)`**. That is structurally identical to `Step`'s original **`(envelope_id, ordinal)`** identity — which [ADR-0006](../adr/ADR-0006-step-surrogate-identity.md) **rejected** ("bakes position into identity") and [ADR-0007](../adr/ADR-0007-kernel-identity-discipline.md) **generalized into kernel doctrine**: *composite `EntityId` forbidden by default; model the natural composite key as **attributes** + a `UNIQUE` constraint, identity is a single-field surrogate UUID.* The `CompositeValueObjectShapeRule` lint would **statically reject** a multi-field `AuditEventId`.

**Resolution (clean, precedented):** `AuditEvent` gets a surrogate **`AuditEventId` (app-minted UUID, `StringEntityId`)** as PK; `(envelope_id, sequence)` becomes a named `UNIQUE` on *attributes*. Identical to how Step was resolved. → Layer 1 is not actually hard; it just means we **must not** copy the design's literal `(envelope_id, sequence)`-as-PK into the kernel identity. *(Same applies to `RecipientEvidenceLog`'s `(recipientId, envelopeId)` in slice 2 — a composite of two cross-BC refs → surrogate + UNIQUE.)*

### Layer 2 — the `sequence` itself has no home in our sequence toolkit *(needs a mechanism choice)*

Even demoted to a non-identity attribute, `sequence` must be **(a) per-envelope, (b) gap-free, (c) strictly monotonic, (d) known *before* the INSERT** (the hash consumes it). The architecture has exactly two sequence tools and **neither fits**:

| Tool | Per-envelope? | Gap-free? | Known pre-INSERT? | Unforgeable? |
|---|---|---|---|---|
| App-minted UUID (ADR-0007 / [ADR-0019](../adr/ADR-0019-database-schema-conventions.md) §3) | n/a | n/a — unordered | yes | no (app mints) |
| `GENERATED ALWAYS AS IDENTITY` (outbox `sys_sequence`) | **no — global** | **no — gappy** (rolled-back tx consumes the value) | no (DB-allocated on insert) | yes (infra-owned) |
| **what the chain needs** | **yes** | **yes** | **yes** | **ideally yes** |

ADR-0019 §3 is explicit: identity is **"never DB/server-allocated — no serial, `GENERATED` identity, `DEFAULT gen_random_uuid()`, or sequence."** The outbox's `sys_sequence` deliberately accepts global + gappy because it only needs *relative ordering*. The audit chain needs strictly more. **The only fit is app-computed under `SELECT … FOR UPDATE` on the root** — allowed, but it is a **new pattern** here and is intrinsically **read-before-write** (read the tip to compute the next link).

### Layer 3 — read-before-write + app-computed-yet-unforgeable cut against the architecture's grain *(the deep friction)*

This is the part that is genuinely *"difficult to address with our current architecture,"* not just a decision to make:

- **(a) The hash chain fits neither §4 column category.** [ADR-0019](../adr/ADR-0019-database-schema-conventions.md) §4 splits columns into **domain-authored** (no DB default — the domain decides the value) and **infra/audit** (`db_`/`sys_` prefix, **trigger-set, app-unwritable, immutable, app-unforgeable**). The chain's `hash`/`sequence` are a **third thing**: the *app* must compute them (the hash is a function of domain content), yet for tamper-evidence they must be **unforgeable after the fact**. There is no slot for "app-writes-once, then immutable + unforgeable." The outbox's per-column-GRANT lever gets us *append-only at the DB* (app gets `INSERT`-only, no `UPDATE`/`DELETE` on `audit_event`) — but that only stops *editing old rows*; a compromised app role can still forge a **new internally-consistent chain**. WORM S3 covers the *generated Audit Trail XML*, not the live Postgres rows. **So the live chain's tamper-evidence is, under our current substrate, disciplinary — not structural** — which is precisely the property this BC exists to make non-disciplinary.

- **(b) Read-before-write is against the optimized grain.** The whole id/idempotency architecture ([ADR-0007](../adr/ADR-0007-kernel-identity-discipline.md) + [ADR-0014](../adr/ADR-0014-idempotency-three-layer.md)) is built on values that **don't depend on existing DB state** — mint-ahead, *pre-allocated-id-is-the-idempotency-key*, no read-after-write (e.g. `SigningSessionId::fromScope`, deterministic). The hash chain is the inverse: each link `= f(previous link)`, so it **must** read the tip under a lock. Not forbidden — but it interacts with idempotency: at-least-once command redelivery would **re-append** a chain entry unless something guards it. *Today the guard is implicit*: the upstream aggregate's state transition is non-repeatable (a re-delivered `CommitSignature` throws "already signed" before `record()` is reached), so the chain is idempotent **by virtue of the emitter**, not by the audit layer. The design's "idempotent per `(envelopeId, emittingContext, idempotencyKey)`" port is the explicit version we don't have. **Worth deciding: rely on the emitter's non-repeatability, or give the port a real idempotency key?**

> The kernel already *anticipates* this case — `OrderedByOccurredAt`'s docblock names "sequence number on a hash-chained event" and `Event.php` contemplates "insertion sequence" ordering. ADR-0007's **reopening clause** (4-item bar) and ADR-0019 §3's **`ServerAllocatedAggregateRoot` escape** are the sanctioned doors. The question is whether the audit chain walks through one of them or is resolved entirely below the identity layer (Layer-1 surrogate + Layer-2 lock-serialized attribute).

### 4.4 — `EvidenceCollector`: §4.0 again, without the platform escape *(slice 2)*

`EvidenceCollectorInterface` is, by design, **"synchronous, on the durability path — the session blocks on this before commit"** (domain-model §Ports). So shipping evidence to `RecipientEvidenceLog` is a cross-BC same-tx write — structurally the §4.0 problem. But §4.0's escape was *"every BC writes it ⟹ platform infra."* Evidence **fails that test**: only **Session** writes it (at `CommitSignature`), into clearly E&A-*domain* data (per-recipient capture). So the platform reframe doesn't apply and the same-tx-vs-isolation impossibility recurs, **sharper**.

**The MVP already sidesteps it.** [TASK-008](TASK-008-signing-session-recipient-ceremony.md) captures consent + signer IP/UA on the **session's own row**, not E&A's. So slice 2 can ship evidence as an **async projection off `SessionCompleted`** (already flowing through the outbox/consume side) instead of a sync cross-BC write — clean, isolation intact — **at the cost of diverging from the design's synchronous `EvidenceCollector`.**

**The caveat that may *be* the answer:** biometric evidence genuinely *is* on the durability path (invariant 2 — no `EvidencePacket` → no provable signing act), so it **cannot** go async. The non-biometric MVP captures (consent / IP-UA / device / geo) *can*. So the resolution may be **asymmetric** — async-project the forensic captures now; reserve a sync path for biometric in v2. *(Decision §7.6.)*

### 4.5 — PLATFORM biometric key vs the tenant-uniform RLS contract *(v2)*

The biometric key resolution walks `TENANT(tenantId) → PLATFORM` (domain-model §Aggregates); the **PLATFORM key serves every tenant**. But [ADR-0017](../adr/ADR-0017-tenant-isolation-rls-persistence-contract.md) / [ADR-0019](../adr/ADR-0019-database-schema-conventions.md) §8 mandate every tenant-scoped table be `tenant_id UUID NOT NULL` + a *uniform* `tenant_id = current_tenant_id()` isolation policy. A platform-global row (`tenant_id` NULL, visible cross-tenant) breaks **both** — it needs a `… OR scope = 'PLATFORM'` policy carve-out, plus `NULLS NOT DISTINCT` (or a sentinel) on the `≤1 ACTIVE per (scope, tenantId)` partial unique (the pre-PG15 gotcha [ADR-0019](../adr/ADR-0019-database-schema-conventions.md) §9 already flags). This is the first concrete bite of the **deferred system/bootstrap-RLS branch** ([ADR-0010](../adr/ADR-0010-command-bus-middleware-spine.md) Rule 4). **v2** — doesn't touch slices 1–2.

## 5. Secondary tensions / notes

- **F7 — `AuditableEvent::envelopeId()` is misnamed.** It returns the *subject* aggregate id (for `SignatureCommitted`, the **session** id); the real envelope id the chain keys on rides in `payload()['envelope_id']`. The adapter can read the payload (ships now) or we do the kernel `envelopeId() → subjectId()` rename + an explicit chain-key accessor (cross-cutting, ~9 implementers). Separable from the §4 tension.
- **Port shape.** Current stub is `record(AuditableEvent): void`. The design port returns `AuditEventId` and is idempotent. Evolving it is orthogonal to slice 1's persistence and can be its own change.
- **RLS scope.** The audit write happens inside the emitter's tenant scope (sync, same tx) — so RLS-from-`current_tenant_id()` applies exactly like every other write. `audit_event.envelope_id` is a **cross-BC `EntityReference`** (ADR-0020), no FK (ADR-0019 §6).

## 6. Scope

- **Slice 1 (this task):** persist `EnvelopeAuditLog` + `AuditEvent` + hash chain; DBAL adapter, same-tx, RLS; lock ADR-0003 1b. **Blocked on resolving §4 to the depth we choose** (at minimum Layer 1 + Layer 2; Layer 3 may be explicitly deferred-with-rationale rather than solved now).
- **Slice 2:** `RecipientEvidenceLog` + `EvidenceEntry` + `EvidenceCollectorInterface`; ships TASK-008's on-row consent/IP-UA into the BC. Needs the collector port shape pinned (domain-model §13) **and the sync-vs-async-projection fork resolved (§4.4 / decision §7.6).**
- **v2:** `BiometricEncryptionKeyPair` + cipher + custodian (gated on the biometric feature) **— carries the PLATFORM-key RLS tension (§4.5).**
- **Later:** Audit Trail XML generation (XAdES-B-LTA via SE) on `EnvelopeCompleted` + WORM storage (ADR-0016); `(emittingContext, type)` catalog aggregation; per-event subscriber wiring.

## 7. Open decisions (for iteration)

**0. (§4.0 — the gating one) Is the chain-append "platform infrastructure" (mechanism) with E&A owning the meaning?** If yes → `platform.audit_event`/`platform.envelope_audit_log`, a Foundation append capability (sibling of `OutboxWriter`), narrow per-column GRANTs per BC role, and the future per-BC-role split is GRANT-only. If no (the chain tables must live in E&A's private schema) → same-tx atomicity and per-BC isolation are genuinely irreconcilable and one of ADR-0003 / ADR-0019 §1 has to bend. *(Recommend yes — it's §1's own cross-cutting criterion, and the outbox is the proof.)* This gates table placement in §3 and decisions 1–4.

1. **§4 Layer 3 — how far do we go now?** Accept disciplinary tamper-evidence for the live rows (append-only GRANT + WORM only on the generated XML) for the MVP, with the structural-unforgeability question deferred-with-rationale? Or does the audit chain force a substrate decision (e.g. a DB-side trigger that computes/seals the chain, an `audit` role separation, or an append-only/event-store mechanism) *before* slice 1 lands?
2. **Sequence mechanism** — confirm app-computed-under-`SELECT FOR UPDATE`-on-root (Layer 2), and whether `sequence` is a plain domain attribute or earns a sanctioned `ServerAllocated`-style treatment.
3. **Identity** — confirm surrogate `AuditEventId` (UUID) + `UNIQUE(envelope_id, sequence)` (Layer 1). *(Recommend yes — mirrors Step.)*
4. **Idempotency** — rely on the emitter's non-repeatable transition, or give `record()` a real idempotency key?
5. **Kernel cleanups (F7 / port shape)** — fold into slice 1, or separate focused changes? *(Lean: separate.)*
6. **Evidence collection — sync or async? (§4.4, slice 2)** Honor the design's synchronous `EvidenceCollector` (cross-BC same-tx write, no platform escape), or async-project evidence off `SessionCompleted` (clean, but a divergence from the design)? *(Lean: async-project the forensic captures — consent / IP-UA / device / geo; reserve sync-collect for biometric, the only capture truly on the durability path, when it lands in v2.)*

## 8. Realization crosswalk (current)

| Axis | Status | Code |
|---|---|---|
| `AuditCommandInterface.record()` | ✖ removed (event-log 1b) | — (superseded by same-tx `EventLog::append`, [ADR-0031](../adr/ADR-0031-event-log-store.md)) |
| In-memory adapter | ✖ removed (event-log 1b) | — |
| Kernel `AuditableEvent` | ✅ | [`Kernel/Event/AuditableEvent`](../../src/F5Sign/Kernel/Event/AuditableEvent.php) |
| `EnvelopeAuditLog` / `AuditEvent` / hash-chain persistence | ◯ | — (this task) |
| `RecipientEvidenceLog` / `EvidenceEntry` | ◯ | — (slice 2) |
| `BiometricEncryptionKeyPair` | ◯ | — (v2) |

---

## 9. Resolution & inherited design constraints (event-log reframe)

> The §4 tensions were **not solved as originally framed** (a write-time, per-envelope hash-chain aggregate under `SELECT … FOR UPDATE`). They were **dissolved** by the record-first event-log reframe. This section is the durable in-repo home for that resolution and for the design constraints the **future evidence-projector task inherits** — content that previously lived only in the temporal design scratchpads (`EVENT-LOG-SUBSTRATE.md §10.6/§10.10`, `EA-EXEMPLAR-WALK.md §0` — `OFFREPO:`, historical origin, not a live dependency). The substrate itself is realized and locked in [ADR-0030](../adr/ADR-0030-record-first-event-floor.md) / [ADR-0031](../adr/ADR-0031-event-log-store.md); what follows is the E&A-side reasoning those ADRs do not carry.

### 9.1 How the §4 tensions resolved

- **§4.0 (same-tx atomicity vs per-BC role/connection isolation)** → dissolved. Producers append raw facts through the `SECURITY DEFINER` `platform.append_event(...)` function **in their own command transaction** (same-tx durability, INT-1, preserved), holding `EXECUTE` on the function and **no table grant** — so isolation and one-transaction-durability no longer collide. The audit-append substrate is `platform` (every BC records into one shared log), exactly as §4.0's escape reasoned; E&A owns only the read-side *meaning* (the projection).
- **§4.1 (composite `(envelope_id, sequence)` identity)** → moot. There is no per-envelope chain aggregate; a log entry's identity is a single app-minted `UUIDv7` record id. The identity discipline (ADR-0007) is not challenged.
- **§4.2 / §4.3 (the `sequence` mechanism; read-before-write; app-computed-yet-unforgeable)** → the per-envelope **hash chain moves to projection time**. The live log uses a global, gappy `sys_global_position` (IDENTITY) plus a contextual `stream_id` correlation, and the append is a **pure `INSERT`** — no read-before-write, no write-time counter. Tamper-evidence on the live log is **immutability** (no `UPDATE`/`DELETE` grant) **+ the per-row `sys_commitment` leaf**; the strong chain/Merkle anchor is the WORM-sealed projection ([ADR-0016](../adr/ADR-0016-storage-model.md)). This is why ADR-0031 deliberately ships **no per-stream gapless counter** (recorded there as an accepted limit).

### 9.2 Completeness is a projection-time property (the INT-4 reframe)

Because `sys_global_position` is **global and gappy**, a missing per-envelope event is **not** detectable by contiguity. So the objective "gap-free" (INT-4) is realized as **"gap-*detectable* + fail-closed"**, not "gap-impossible by construction":

- The evidence **projector reconciles completeness against the envelope's authoritative final state** (read via the producers' ACL ports) **before sealing**. A detected hole → **do not seal, alert, recover** (redeliver from the durable log). Ordering (INT-3) comes from `sys_global_position`, not broker arrival.
- **E&A is a projector, not a store.** The durable audit store dissolves; the per-envelope chain becomes a **projection-time fold living *inside* the evidence artifact** (the `FOR UPDATE` chain-tip lock is gone). The old "Consumer A3" decode/scope/dedup dissolves upstream into the producer append + the append chokepoint; the "Worker A4" survives as a **pure log-projector** (reconcile the `stream_id` stream + ACL final-state → chain → seal → WORM).
- **Open (projector build):** projector wake-up — **log-polled vs broker-triggered**. Lean: log-polled, since E&A acts at envelope completion, not per event.

### 9.3 Recorded-form ≠ transported-form (inherited constraint)

A load-bearing distinction the projector and the event contracts must honor:

- **The collision:** *lean events* (refs, PII off the wire) vs *self-containment* (log entries reference only immutable holdings) vs *replayability* (replay needs the referenced data recoverable). A lean event stored as-is inherits refs to **mutable** producer data → the log is not self-contained → replay breaks when that data changes or is erased.
- **The resolution:** **recorded-form ≠ transported-form** — the *stored* fact is richer than the *bus* message. Scoping rule: **stable id refs (UUIDs) are fine forever**; only **mutable evidential attributes** (presented identity, consent, IP/UA — the PII) must be **eager-custody-snapshotted at occurrence**. The lean-event PII-avoidance job moves to **wire-redaction** (the broker projection strips PII at publish), freeing the event to carry its evidential snapshot. Shapes: *born-with-evidence → stored-complete (eager custody) → projected per reader* (bus = redacted-lean · domain replay = referential · evidence = full/decrypted).
- **Re-opens Path A vs B.** Path A = complete-encrypted in the log (single-store, self-contained replay); Path B (MVP) = split across lean-log + WORM artifact (log replay rebuilds *pseudonymous* projections only — sound **iff** lean events carry stable-id refs and the evidential snapshot goes to an immutable holding).
- **Kernel commitments to re-evaluate under this lens:** "lean events" (PII role → wire-redaction); `DomainEvent`'s ubiquitous-language payload vs the complete recorded form; `SelfSerializing` (the codec owns the *complete* form, lean = a derived projection); possibly a new kernel concept *recorded-form ≠ transported-form*, or keep it a Foundation concern. **Provisional lean:** ONE canonical event carrying its evidential snapshot, stored complete, with lean/wire as a *redaction projection* — not two event *types*; eager-custody + redaction live in Foundation.
- **Accepted residual (not a mechanism flaw):** a per-event-type evidential *schema* that under-specifies what must be captured is an **upstream modeling** concern, not a defect in the redaction/append mechanism.

### 9.4 🛡 Redaction guardrail (safety-critical — do not weaken)

Redaction must **never** let one create events *missing* the would-be-redacted data (incomplete records masquerading as complete audit facts). **Redaction is a one-way, lossy, NON-authoritative projection — not round-trippable into a valid event.** Three guards, all required:

1. **Type-enforced construction** — an event cannot be built without its evidential fields (non-nullable constructor params); incompleteness is unrepresentable, not merely discouraged.
2. **Asymmetric serialization** — `fromPayload` accepts **only the complete form**; the redacted wire form is a **terminal view**, explicitly refused as a reconstruction input. Redaction flows one way (complete → redacted), never back.
3. **Completeness validated at the append chokepoint** — `EventLog::append` / `platform.append_event` **rejects records missing required evidential fields**; the `sys_commitment` then anchors exactly what was stored. *(Today the append fn enforces only generic column `NOT NULL` — the evidential-completeness concept above is the constraint the projector/cipher work must add; it is recorded here so it is not lost.)*

Losing this guardrail is the failure mode this section most guards against: a future implementer could otherwise build redaction that mints incomplete records indistinguishable from complete ones, silently defeating the evidentiary value the whole BC exists to provide.
