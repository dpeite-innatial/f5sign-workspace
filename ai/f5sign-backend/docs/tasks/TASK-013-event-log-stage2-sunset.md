# TASK-013 — Event log, Stage 2: sunset the transactional outbox

<!-- OFFREPO: the `§10.x` / `§13x` / `§14` / `S1`/`S2` markers reference the workspace design doc `EVENT-LOG-SUBSTRATE.md` and its staging ledger (not in this repo). The landed decisions have their in-repo home in ADR-0031 (the store), ADR-0024 (the outbox being retired), and the ADRs touched below; this doc is design-trail, so the markers are kept as native vocabulary. -->

| Field | Value |
|-------|-------|
| **Status** | **✅ Shipped** — stage 2 sunset; merged to master (2026-07-01, the final event-log commit). As-planned build record. Builds on [TASK-012](TASK-012-event-log-stage1b-cutover.md) (the cutover). |
| **Type** | **Sunset / removal — §10.4 S2.** Drop the now-dead transactional outbox (`platform.outbox` + `OutboxWriter` + `OutboxRelay` + `RelayOutboxCommand` + its tests) and the code that only existed to feed it (the dead `EventBus` port + `MessengerEventBus` adapter, the `nameForClass` seed machinery). Fold in the small set of stage-1b deferrals. No behaviour change — everything removed has had **zero callers since stage 1b**; this is the bookkeeping slice that makes the tree honest. |
| **Part of** | Branch `feat/event-log` (backend). **Backend-only** — dropping the outbox table is a new migration; the `f5sign_app` / `f5sign_relay` roles **stay** (the event log uses them), only the outbox-table grants disappear with the table, so **no infra change**. Substrate design: [ADR-0031](../adr/ADR-0031-event-log-store.md), which supersedes ADR-0024 and records the outbox's retirement as the substrate's final stage. |
| **Delivery bar** | `platform.outbox` is dropped by a new reversible migration; `OutboxWriter`, `OutboxRelay`, `RelayOutboxCommand`, and the 3 `Outbox*` integration tests are deleted; the dead `EventBus` port + `MessengerEventBus` adapter + their services.yaml alias are gone; `EventTypeNaming::nameForClass()` and `DeclaredEventTypeSeedFidelityTest` are retired (`routingKeyForClass()` stays — it is live in `EventRelay`). Config (services.yaml / messenger.yaml / doctrine.yaml) and docblock prose no longer describe the outbox as a live mechanism. The stage-1b deferrals are folded in (see §2.5). `make qa` green; the seal/signing loops still run end-to-end through the log + `EventRelay`. |
| **Blast radius** | Bounded — almost entirely deletion of code that has **no callers**. **Deleted:** `Foundation/Outbox/` (writer, relay, console command), 3 outbox integration tests, `Foundation/Bus/EventBus` + `MessengerEventBus`, `EventTypeNaming::nameForClass()` + the seed-fidelity test. **Trimmed:** `EventTypeNamingTest` (drop the `nameForClass` case), config wiring + docblock prose. **New:** one drop migration. **ADRs:** ADR-0024 → Superseded (the outbox is physically gone); ADR-0031 status bump (outbox retired — S2 done); README index. **No producer, reactor, relay, or middleware behaviour changes.** |
| **Decision record** | ADR-0024 → **Superseded** by [ADR-0031](../adr/ADR-0031-event-log-store.md) (the transactional outbox it specified no longer exists; its delivery guarantee is discharged by the watermark `EventRelay` over the permanent log). ADR-0031 **status bump** ("outbox left dead but present — stage 2" → "outbox retired"). See §4 for the open calls (broker round-trip coverage, `AuditableEvent` reduction). |

---

## 1. Why this task exists

Stage 1b (TASK-012) cut every producer over to `EventLog::append` and swapped the outbox relay for the watermark `EventRelay`. Since that commit (`618882b`) the outbox has been **dead but present**: `platform.outbox` receives no rows, `OutboxWriter` has no callers, `OutboxRelay` / `RelayOutboxCommand` are never run. Leaving dead infrastructure in the tree is a lie the code tells — it reads as if there are two delivery paths when there is one. Stage 2 removes it so the codebase matches reality: **the log is the single system of record, the watermark relay is the single delivery path.**

This is the ontologically-honest end of the strangler-fig (§10.4 option C): build the log disjoint from the outbox → cut over in one no-dual-write slice → **drop the outbox**. The design always named this as the final step; ADR-0031's status line already says "retiring it is stage 2."

Nothing here changes behaviour. Every deletion targets code that has had **zero callers since 1b** (verified by grep, §2). The risk is not "will it break" but "did I miss a live reference" — so the task is grep-driven and each removal is justified by its (empty) caller set.

## 2. What will be built (removed)

### 2.1 Drop the outbox table (new migration)

`platform.outbox` was created by the original outbox migration `Version20260619000001` (table + FORCE RLS + per-actor/per-column grants, ADR-0024 D2/D3e/D3f), which was removed in ADR-0018's Phase-A clean-baseline rewrite (the 12→4 `Version20260713*` baselines; ADR-0019 §11's "never edit applied migrations" waived for that one pre-prod rewrite). Applied migrations are never edited (repo rule #2), so the plan below added a **new** migration:

- `up()`: `DROP TABLE IF EXISTS platform.outbox` (the table's grants and RLS policy drop with it).
- `down()`: recreate the table + policy + grants — mirror `Version20260619000001::up()` exactly, so the migration is reversible.

The `f5sign_app` and `f5sign_relay` roles **are not touched** — the event log grants to both, so they remain live. Only the outbox-*table* grants vanish (with the table).

> **As-built (2026-07-20 doc-cleanup):** this standalone drop-migration was **folded into ADR-0018's Phase-A clean-baseline rewrite** — the four `Version20260713*` baselines simply never create `platform.outbox`, so on master there is no separate drop/`down()` step and no dependency on the (also-removed) `Version20260619000001`. The reversibility concern in the bullets above is moot on the clean baseline.

### 2.2 Delete the outbox code

The whole `src/F5Sign/Foundation/Outbox/` directory — **no callers remain** (`OutboxWriter` is referenced only by its own class + the services.yaml def; the 3 repositories repointed to `EventLog::append` in 1b):

- `Foundation/Outbox/OutboxWriter.php`
- `Foundation/Outbox/OutboxRelay.php`
- `Foundation/Outbox/Console/RelayOutboxCommand.php` (the `app:outbox:relay` worker — replaced by `app:event-log:relay` / `RelayEventLogCommand` in 1b)

And the 3 outbox integration tests (their event-log equivalents `EventLogAppendTest` / `EventRelayTest` / `EventLogAccessControlTest` already cover the same guarantees for the log):

- `tests/F5Sign/Foundation/Integration/OutboxRelayFailureTest.php`
- `tests/F5Sign/Foundation/Integration/OutboxAccessControlTest.php`
- `tests/F5Sign/Foundation/Integration/OutboxBrokerRoundTripTest.php` — **⚠ see §4**: this is the only broker *round-trip* integration test; the event log has no equivalent yet. Resolve before deleting (port it, or confirm the coverage is redundant).

### 2.3 Delete the dead event-bus port

`SignatureExecution` was the last consumer of the `EventBus` port; its 3 inline `eventBus->dispatch(...)` sites became detached appends in 1b. Grep confirms nothing now injects `F5Sign\Foundation\Bus\EventBus` (only the services.yaml alias + the two classes' self-references remain):

- `Foundation/Bus/EventBus.php` (the port)
- `Foundation/Bus/MessengerEventBus.php` (the adapter)
- the `EventBus → MessengerEventBus` alias in `services.yaml`

### 2.4 Retire the event-type seed machinery

Stage 0 declared a stable `EVENT_TYPE` on every event, seeded behaviour-neutrally from the old class-derived name; `DeclaredEventTypeSeedFidelityTest` locked the seed against drift so it could be retired once the declared names are the source of truth. That time is now:

- Delete `DeclaredEventTypeSeedFidelityTest`.
- Remove **`EventTypeNaming::nameForClass()`** (its only remaining callers are that test + `EventTypeNamingTest`).
- **`EventTypeNaming` the class STAYS** — `routingKeyForClass()` is live (`EventRelay` uses it to build the `AmqpStamp` routing key — `rg -n 'routingKeyForClass' src/`). Rework `EventTypeNamingTest` to drop the `nameForClass` data-provider/case and keep the `routingKeyForClass` coverage.

### 2.5 Fold in the stage-1b deferrals

Recorded in [TASK-012 §5.1](TASK-012-event-log-stage1b-cutover.md) as "deferred-with-awareness — revisit at stage 2":

- **Low-water-mark adversarial test.** Add a test proving `EventRelay` holds back a *late-committing in-flight* transaction (never skips past an uncommitted xid below a concurrent one). Needs a **third DB connection holding an open transaction** (an un-committed `append` with a live `xid8`) while the relay runs. This closes §5's "in-flight transaction is not skipped past" bar *adversarially* (1b met it only implicitly). If the harness genuinely can't hold a concurrent open xid cleanly, **say so and leave it deferred** — don't fake it.
- **`EventRelay` defensive lines (the 4 uncovered from 1b, 93.55%).** The `catch (Throwable) { rollBack; throw }` connection-rollback path (needs a simulated mid-batch DB failure) and the `['0', 0]` no-checkpoint floor (the real production first-run path, unhit because every test seeds its checkpoint for isolation). Cover what's cheap; leave genuinely-defensive branches noted (consistent with the repo's "uncovered = defensive branches needing simulated infra failure" convention) rather than contorting tests.

### 2.6 Prose + config sweep

The outbox is referenced in **docblocks and comments** across the kernel/foundation (e.g. `Repository.php`, `AggregateRoot.php`, `Event.php`, `SelfSerializing.php`, `ActivityLogEntry.php`, `EventTypeRegistry.php`, and the reactor/serialization prose) that describe drain-to-the-outbox as a live mechanism. Sweep them so they describe the event log + `EventRelay` (greppable: `grep -rin outbox src config`). Update the config comments that survive:

- `services.yaml` — remove the `OutboxWriter` service def + the `EventBus` alias + the outbox comment.
- `messenger.yaml` — the `async_events` / `event.bus` transports **stay** (the relay uses them); rewrite the comments that attribute publishing to the "transactional-outbox relay" to name the `EventRelay`.
- `doctrine.yaml` — the `relay` DBAL connection **stays** (the `EventRelay` drains via the BYPASSRLS `f5sign_relay` role); rewrite its comment (it currently says "drains the outbox").

This is part of the touched-file hygiene pass (run [`v1-touched-file-hygiene`](../../.claude/skills) before commit).

### 2.7 ADRs

- **ADR-0024 → Superseded** by ADR-0031. The transactional outbox it specified no longer exists; its at-least-once delivery guarantee is discharged by the watermark `EventRelay` over the permanent log. Add the superseding note (mirror the ADR-0003 supersession that landed in 1b).
- **ADR-0031 status bump** — from "the outbox is left dead but present — retiring it is stage 2" to "outbox retired (stage 2, this commit)."
- **README** index/graph — reflect ADR-0024 → Superseded.
- Check ADR-0015 (async resilience) and ADR-0027 (seal loop): both were amended in 1b to point delivery/DLQ at the `EventRelay` / `event_dead_letter`; confirm neither still describes the outbox as live, patch if so.

## 3. Scope

**In (this task):** the drop migration; delete `Foundation/Outbox/` (3 files) + 3 outbox integration tests; delete `EventBus` + `MessengerEventBus` + alias; retire `nameForClass` + `DeclaredEventTypeSeedFidelityTest` + rework `EventTypeNamingTest`; fold in the 2 stage-1b test deferrals (§2.5); the prose/config sweep; ADR-0024 → Superseded + ADR-0031 bump + README.

**Out (later / deferred — named so they are not silently assumed):**
- **`AuditableEvent` reduction** — deferred to the evidence projector (see §4). `payload()` / `emittingContext()` are consumed only by tests now, but the category still marks observation-vs-transition; removing it before the projector exists is premature.
- **Merkle / external anchoring, cipher-at-capture (Path A PII), partitioning (firehose-tier rebuild), the evidence projector / activity views** — the log is the substrate they read; each is its own future task.
- **CDC / logical decoding (Debezium) delivery** — the documented **v2 escalation** if the single-worker watermark relay's poll-load, or the watermark stall behind a long-running transaction, ever bites. The `sys_transaction_id` (xid8) column is additive groundwork laid down to keep that path open; the MVP delivery mechanism stays the polling `EventRelay`.
- **`correlation_id` / `causation_id`** tracing columns — additive-safe future enhancement.
- **Log archival / WORM-then-drop mechanism + DB backup/DR** — pointer-plus-principle only (ADR-0016); no day-one seam.

> **Precondition — why this no-data-migration cutover is safe.** Stage 2 leaves the outbox dead-but-present through 1b, then drops it with **no row copy** and no dual-run. That is valid **only because the system is not yet in production**: there are no live outbox rows whose in-flight delivery must survive the swap, and the deletions are justified by "zero callers since 1b" (behaviour), not by any data-migration having run. Re-running this strangler-fig style against a **live** log would need a drain-and-verify step before the drop — record that here so the pattern isn't copied blind onto a running system.

## 4. Key decisions (open — resolve at build)

- **`OutboxBrokerRoundTripTest` — port or drop?** It is the only broker *round-trip* integration test (append → AMQP → consume). The event log's `EventRelayTest` covers the watermark/poison logic but (confirm at build) may not exercise the real broker hop end-to-end. **Lean: port it to an `EventLogBrokerRoundTripTest`** (append via `EventLog::append` → `EventRelay` → AMQP → reactor) so broker-integration coverage isn't lost — the seal/signing flow tests exercise the loop but a focused broker round-trip is cheaper to diagnose when the broker misbehaves. Only delete outright if an existing test already covers the log→broker→consume path.
- **`AuditableEvent`'s fate (§13F #5, still open).** Assume-removal-likely but **defer**: once the evidence projector exists it will decide whether `AuditableEvent` reduces to a marker (observation-vs-transition) or folds into `DomainEvent`. Removing it here — before anything reads the distinction — is premature. Note it, don't act.
- **Migration `down()` fidelity.** The drop migration's `down()` must recreate `platform.outbox` byte-identically to `Version20260619000001::up()` (table + RLS policy + all grants) to stay reversible. Copy, don't paraphrase.
- **One commit.** Per the per-task-commit workflow, stage 2 lands as ONE green commit on `feat/event-log` (backend-only). This is the last event-log commit before the user's end-of-branch PR-like review.

## 5. Verification

- `make qa` green (PHPStan L9 · Deptrac 0 · lint · full suite) — with the outbox code and its tests gone.
- `grep -rin outbox src config` returns only intentional history references (e.g. an ADR's supersession note), no live-mechanism prose.
- The drop migration applies cleanly (`make migrate`) and its `down()` recreates `platform.outbox` (round-trip: migrate down then up on a scratch DB).
- The seal loop and signing-session flow tests still pass end-to-end through the log + `EventRelay` (no regression from removing the dead paths).
- `EventTypeNaming::routingKeyForClass()` still covered; `nameForClass` and `DeclaredEventTypeSeedFidelityTest` gone.
- No service-container errors from the removed `EventBus` alias / `OutboxWriter` def (`make sf cmd="lint:container"` or a boot).
- ADR-0024 shows **Superseded**; ADR-0031 shows the outbox retired; README index consistent.
