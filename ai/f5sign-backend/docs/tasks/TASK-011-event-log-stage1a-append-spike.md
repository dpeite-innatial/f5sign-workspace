# TASK-011 — Event log, Stage 1a: the append spike (exercise-lock the novel core)

<!-- OFFREPO: the `§10.x` / `§13x` / `§14` / `D1`–`D7` markers throughout this task-trail doc reference the workspace design doc `EVENT-LOG-SUBSTRATE.md` (not in this repo). The landed decisions have their in-repo home in ADR-0031; this doc is design-trail, so the markers are kept as native vocabulary. Re-home if the substrate migrates in-repo. -->

| Field | Value |
|-------|-------|
| **Status** | **✅ Shipped** — stage 1a; the append substrate is production-merged (2026-07-01). As-planned build record. Green bar was `make qa` (PHPStan L9 · Deptrac 0 · lint · full suite). |
| **Type** | **Build (forward).** Stage 1a of the event-log substrate — build the **append mechanism in isolation** and exercise-lock it *before any producer depends on it*. **No producer repoint, no outbox change, no relay** (those are stage 1b). |
| **Part of** | Branch `feat/event-log`. Substrate design: [ADR-0031](../adr/ADR-0031-event-log-store.md) — entry shape, naming, day-one footprint, the commitment scheme, and the access model all live there. **Builds on** [TASK-010](TASK-010-event-log-stage0-kernel-contract-prep.md) + [ADR-0030](../adr/ADR-0030-record-first-event-floor.md) (the record-first `Event` floor: `SelfSerializing` + declared `eventType()` — the append reads both). Stage sequence: `0 (done) → 1a (this) → 1b cutover → 2 sunset`. |
| **Delivery bar** | A standalone `EventLog::append(Event)` writes an **immutable** row to `platform.event_log` through the `SECURITY DEFINER` `platform.append_event(...)` function — the app role holding **EXECUTE on the function only, no grant on the table** — in the **caller's transaction**, with a **function-computed `sys_commitment`**. A property test proves **a tampered or omitted entry is detected**, and a privilege test proves the app role **cannot** `SELECT`/`UPDATE`/`DELETE` the table. §10.8 (commitment) + §10.9 (access) are **exercise-locked**. Nothing produces into the log yet. |
| **Blast radius** | **All net-new** (migration, DB function, `EventLog` port + `DbalEventLog` adapter, the JCS payload codec, `IssuerContext`, tests) + a services.yaml wiring + **one infra touch** (a new NOLOGIN function-owner role + a reader role in `f5sign-infra`'s role provisioning, mirroring the outbox's `f5sign_app`/`f5sign_relay` split). Does **not** touch producers, the outbox, the relay, or any BC. |
| **Decision record** | The store/append/commitment/access model graduates from the substrate (§10.3/§10.5/§10.8/§10.9). *(As-built: resolved to a new **[ADR-0031](../adr/ADR-0031-event-log-store.md)** — the event-log store: append function, commitment, access model — as the lean below anticipated.)* |

---

## 1. Why this task exists

Per lock-via-exercise, the highest-risk, least-exercised parts of the substrate are the **novel DB mechanism**: the `SECURITY DEFINER` append chokepoint (§10.9), the per-entry **commitment** scheme (§10.8), and **grant-enforced immutability**. §13E sequences the build so these get **locked in isolation** — a narrow, deep spike — *before* stage 1b repoints producers onto them. If the commitment formula, the fn's stamping, or the access model is wrong, we find out here, against a property test, not when nine producers already depend on it.

The spike builds the mechanism and exercises it with a **standalone append** (the test constructs an `Event` and appends it — no aggregate, no use-case, no outbox). Producers, the watermark relay, `streamKey` population, and the ADR-0003 retirement all stay out (stage 1b).

## 2. What will be built

### 2.1 The migration — `platform.event_log` + function + side tables + grants

Template: the outbox migration `Version20260619000001` (removed in ADR-0018's Phase-A clean-baseline rewrite — the 12→4 `Version20260713*` baselines; ADR-0019 §11's "never edit applied migrations" was waived for that one pre-prod rewrite — schema, FORCE-RLS, per-role grants, `GENERATED ALWAYS AS IDENTITY`). New migration creates:

**`platform.event_log`** — the full §10.3 locked shape:

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID` PK | record identity (eventId), app-minted UUIDv7; the consumer dedup key |
| `sys_global_position` | `BIGINT` `GENERATED ALWAYS AS IDENTITY` | gappy global monotonic position; infra-owned, app-unforgeable |
| `sys_transaction_id` | `xid8` | `pg_current_xact_id()` at insert (the §10.1 watermark key); fn-set |
| `stream_id` | `UUID` NULL | contextual correlation root (envelope); **populated `NULL` at 1a** — `streamKey()` lands in 1b |
| `subject_id` | `UUID` NOT NULL | the aggregate the fact is about (`Event::subject()`) |
| `event_type` | `TEXT` NOT NULL | the declared stable name (`Event::eventType()`, ADR-0030) |
| `schema_version` | `SMALLINT` NOT NULL | per-`event_type` payload shape-version |
| `payload` | `BYTEA` NOT NULL | exact canonical **JCS (RFC 8785)** bytes of `toPayload()` — storage form = hash form; **lz4** compressed; plaintext at MVP (Path B) |
| `tenant_id` | `UUID` NULL | scope marker (`NULL` = platform); write-check key, not a read-gate |
| `actor_kind` | `TEXT` NOT NULL | coarse stable actor class (USER/SYSTEM/RECIPIENT/ANONYMOUS) |
| `actor` | `TEXT` NULL | the kernel `Issuer::toString()`; NULL = anonymous |
| `occurred_at` | `TIMESTAMPTZ` NOT NULL | domain time (`Event::occurredAt()`) |
| `sys_recorded_at` | `TIMESTAMPTZ` NOT NULL | recording time; **fn-set** (not `DEFAULT now()` — ADR-0019 app-unforgeable) |
| `sys_commitment` | `BYTEA` NOT NULL | the entry's self-hash leaf; **fn-computed** (§10.8) |

- **Constraints/footprint (§10.7):** `PRIMARY KEY (id)` + `UNIQUE (sys_global_position)`; **do not partition** at MVP. Two btree indexes: `(sys_transaction_id, sys_global_position)` (relay tail) + `(stream_id, sys_global_position)` (projection). `payload` column `SET STORAGE`/lz4 compression. A **mandatory insert-only autovacuum/freeze** policy on the table (append-only still freezes for XID-wraparound; PG13+ insert-triggered autovacuum settings).
- **RLS:** `ENABLE` + `FORCE ROW LEVEL SECURITY`; a policy `WITH CHECK (tenant_id IS NULL OR tenant_id = current_tenant_id())` — **write-side only, no `USING` read-gate** (§10.9; readers are trusted projectors). *(The append runs as the fn owner; the WITH CHECK binds the platform-scope vs tenant-scope rule.)*
- **No `status`/`attempt_count`/`published_at`** (those were the outbox's mutable delivery state — gone).

**`platform.event_checkpoint`** `(consumer TEXT, last_transaction_id xid8, last_global_position BIGINT)` — legitimately mutable processing-state (no `sys_` prefix). Created here; **its relay consumer is 1b** (table exists as the seam).

**`platform.event_dead_letter`** `(event_id UUID, consumer TEXT, error TEXT, attempt_count SMALLINT, failed_at TIMESTAMPTZ)` — poison record; created here, exercised in 1b.

**`platform.append_event(...)` — the `SECURITY DEFINER` function (§10.9):**
- Params: the domain columns the caller supplies (`id`, `stream_id`, `subject_id`, `event_type`, `schema_version`, `payload` bytea, `tenant_id`, `actor_kind`, `actor`, `occurred_at`). The function **stamps** `sys_transaction_id := pg_current_xact_id()`, `sys_recorded_at := clock_timestamp()`, computes `sys_commitment`, and `INSERT`s (letting `sys_global_position` be IDENTITY-assigned).
- **Commitment (§10.8 D4), computed in-fn via `pgcrypto`:** `sys_commitment = scheme_id_byte || digest(scheme_id_byte || E'\\x00' || preimage, 'sha256')` where `preimage` = **length-prefixed, typed, fixed-order binary concat** of the **D1 field set** (`id`, `stream_id`, `subject_id`, `event_type`, `schema_version`, payload-bytes, `tenant_id`, `actor_kind`, `actor`, `occurred_at`, `sys_recorded_at`, `sys_transaction_id`) — uuids→16 bytes, text→UTF-8, timestamps→int64 µs-since-epoch, null→a distinct marker. `sys_global_position` is **excluded by construction** (assigned during INSERT). `scheme_id_byte` = `0x01` (first scheme). `0x00` = CT leaf domain-separation prefix.
- Runs **in the caller's transaction** (SECURITY DEFINER doesn't open a new tx) → same-tx atomicity (INT-1). Needs `CREATE EXTENSION IF NOT EXISTS pgcrypto`.

**Roles & grants (§10.9) — the infra touch:**
- A **NOLOGIN function-owner role** (e.g. `f5sign_log_writer`) owns `append_event()` and holds `INSERT` on `platform.event_log`. Provisioned in `f5sign-infra` (mirrors how `init-app-role.sh` creates `f5sign_app`/`f5sign_relay`); the migration issues the object grants.
- **App role (`f5sign_app`): `GRANT EXECUTE ON FUNCTION platform.append_event(...)` — and NOTHING on the table** (no SELECT/INSERT/UPDATE/DELETE). This is the load-bearing property: the app can only append via the function; it cannot read, mutate, or delete the log, and there is no privileged connection to steal.
- **Reader role** (minimal-scope; can be `f5sign_relay` reused or a new `f5sign_log_reader`): `SELECT` for the forthcoming projectors/relay (1b). Grant the SELECT here so the seam exists; no reader runs yet.

### 2.2 Foundation — the port, adapter, codec, actor seam

- **`EventLog` port** (`F5Sign\Foundation\EventLog` or `Kernel`): `append(Event $event): void` — accepts the **floor** `Event` type (any fact).
- **`DbalEventLog` adapter:** extracts `subject_id`/`event_type`/`schema_version`/`occurred_at` from the `Event`; encodes `toPayload()` → **canonical JCS bytes** (the codec below); resolves `tenant_id` from `TenantContext` (NULL = platform) and `actor`/`actor_kind` from `IssuerContext`; mints the UUIDv7 `id`; passes `stream_id = NULL` (1a); calls `platform.append_event(...)` on the default DBAL connection (same tx).
- **The JCS canonical-bytes codec** (Foundation): `array → RFC 8785 canonical JSON bytes` and back (`bytes → array`). Contained here so `SelfSerializing` stays array↔array. **Locked by a round-trip+rehash property test** (store→read→byte-identical ∧ `digest(stored)==sys_commitment==PHP-recompute`).
- **`IssuerContext`** — an ambient holder for the current `Issuer` (mirrors `TenantContext`). At 1a the spike test **sets it directly**; the `SetIssuerMiddleware` that populates it from the command bus is **1b** (producer wiring). `actor_kind` is classified from the `Issuer` (UserId→USER, `SystemActorId` prefix→SYSTEM, recipient→RECIPIENT, null→ANONYMOUS).

### 2.3 Tests (the exercise-lock)

- **Round-trip + rehash property test** — append → read the row → `payload` bytes are byte-identical to the codec output, and `digest(payload-preimage)` recomputed in PHP equals the stored `sys_commitment` (fn ≡ verifier).
- **Tamper/omission detection (§14)** — the core integrity lock: recompute the commitment over a row's fields and detect a mismatch when a field is altered; assert an omitted/renumbered entry is detectable by the chain axis. (Row mutation for the test is done as a privileged role, since the app role *can't* — which is itself the point.)
- **Privilege test** — connecting as `f5sign_app`, `SELECT`/`UPDATE`/`DELETE` on `platform.event_log` are **denied**, and `append_event(...)` **succeeds**. DB-enforced immutability + the no-stealable-credential property.
- **Standalone append integration test** — construct a real `Event`, append, assert the row exists with `sys_global_position`/`sys_transaction_id`/`sys_recorded_at`/`sys_commitment` populated and the domain columns correct.

## 3. Scope

**In (this task):** the migration (table + fn + `event_checkpoint` + `event_dead_letter` + indexes + RLS-write-check + grants); the `pgcrypto` commitment; the `EventLog` port + `DbalEventLog` + the JCS codec + `IssuerContext` holder; the infra role (owner + reader) provisioning; the four tests; ADR-0031 (or ADR-0030 expansion).

**Out (later stages — named so they're not silently assumed):**
- **Producer repoint** (3 repos `save()` → `EventLog::append`), the **SE detached-append fix**, `SetIssuerMiddleware`, **`streamKey()` rename + `stream_id` population**, the **watermark cursor relay** consuming `event_checkpoint`, **drain-collapse** — all **stage 1b**.
- **Retire the ADR-0003 sync path** (9 use-cases) + **ADR-0003 → Superseded** — **stage 1b** (with the append that replaces its guarantee).
- **Sunset `platform.outbox` / `OutboxWriter` / old relay** — **stage 2**.
- **Cipher-at-capture / Path A PII in the log**, the **Merkle/anchoring layer**, **partitioning** (firehose-tier rebuild), **reader projections / evidence projector** — deferred.

## 4. Key decisions

- **PII posture = Path B (§10.9).** Plaintext PII stays **out** of the log at MVP; the log `payload` is pseudonymous / refs. Real PII goes to the WORM evidence artifact at seal (1b+). Cipher-at-capture (Path A) is the deferred seam the scheme-version byte + reversible-only payload already accommodate.
- **Tamper-evident ≠ tamper-proof (§10.8 D7).** State plainly in the ADR: a DB-recomputable commitment is **weak against a privileged insider** (a superuser who can DELETE can recompute). Its day-one value is accidental-corruption + non-privileged tamper detection + being the **leaf substrate** for the insider-resistant layer (WORM-sealed projection chain; deferred Merkle + external anchoring).
- **`stream_id` deferred (stage 0 finding).** The column exists (nullable); `append` writes `NULL` until `streamKey()` lands in 1b with its real envelope-stream semantics.
- **Actor sourcing (§13F #3, locked).** Ambient `IssuerContext` (mirrors `TenantContext`). The holder + `append`-reads-it land here; the bus middleware that populates it lands with producers (1b).
- **ADR: expand ADR-0030 vs new ADR-0031.** *Lean: a new **ADR-0031** (event-log store: `append_event` DEFINER fn + commitment scheme + access model) — ADR-0030 is scoped to the kernel floor; the store is a distinct, larger decision.* Confirm at build.
- **Scheme byte = `0x01`.** First commitment scheme; the agility envelope for evolving algo/encoding later.

## 5. Verification

- `make qa` green.
- The **round-trip+rehash** and **tamper/omission** property tests pass — the commitment + immutability core is exercise-locked.
- The **privilege test** proves the app role cannot read/mutate/delete the table and can only `EXECUTE` the append function.
- The standalone append writes a correct, immutable entry; `sys_*` columns are function-stamped.
- No producer, outbox, or relay behavior changed (the outbox suite stays green).
