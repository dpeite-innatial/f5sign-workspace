# TASK-026 — Three ways a logged fact silently stops becoming a notification, and the recovery path for each

<!-- OFFREPO: the sequencing of these three slices was argued in `notes/HANDOFF-notification-templating.md` §Parte 0, in the private workspace repo that assembles these subrepos; it is not reachable from a backend-only checkout. Every fact this task depends on is restated below and re-measured against this tree on 2026-08-17 — including the vendor behaviour in §2, which the handoff asserted and this record verified. Nothing here needs that file read. The infra half of §3.3 lives in the sibling repo `f5sign-infra` (`docker/rabbitmq/definitions.json`); its current contents are restated in §2 so the gap is checkable from here. -->

| Field | Value |
|-------|-------|
| **Status** | ✅ **Done — all three slices landed 2026-08-18 on `develop`, each verified by the harness [§5](#5-verification) names rather than by a green suite.** Slice 1 (`feat/event-log-replay-command` — `0c5690c`, `086365a`, `48ea7b5`): `app:event-log:replay` + `EventRelay::replayQuarantined()`, whose `DELETE` is a named `count: 1` exception to `NoRawDeleteRule` (§4 D2) decided by the user that day. Slice 2 (`feat/event-log-golden-payload-bytes` — `4e6335a`, and `32d9a11` for the two events [TASK-025](TASK-025-recipient-delivery-failure-and-correction.md) added): one frozen fixture per `EVENT_TYPE` under `tests/Fixtures/event-payloads/` — **23 when the slice landed, 25 today** — plus `GoldenPayloadBytesTest`'s two-armed census, which is what keeps that number right rather than any sentence here. Slice 3 (`feat/event-decoding-failure-dead-letter` — `7e9f610`, its infra half deployed first per §4 D5): `SelfSerializingMessageSerializer::decode()` wraps every failure in `MessageDecodingFailedException`, so an undecodable message is rejected into `queue.events.dead-letter` instead of killing the worker — the measurements are in [§7](#7-slice-3--what-was-measured-on-delivery-added-2026-08-18). ⚑ Every sha above was checked to be an ancestor of `origin/develop` before being written, which is the only thing that makes a sha a durable locator; `git log --grep='TASK-026'` is the fallback if a future rebase falsifies them. **All five sabotages §5 asks for were performed and observed failing for the stated reason** — and the last of them found a real defect in the census itself, which had both arms in one assertion so a renamed `EVENT_TYPE` reported only half the story; split into two cases, it now names the rename from both sides. ⚑ Slice 2 **discharges [BL-107](../BACKLOG.md)** (23 `EVENT_TYPE` constants pinned by nothing) and narrows BL-98, which it does **not** discharge; slice 1 narrows [BL-110](../BACKLOG.md) without closing it. **What did not land, and is not owed by this task:** the checkpoint-rewind command for a broad incident ([BL-110](../BACKLOG.md)), the dead-letter incident log ([§6.2](#6-open-follow-ups-track-dont-solve-here)), the RabbitMQ policy variant (§6.3), and BL-32's registry-against-bindings census (§6.4) — four tracked follow-ups, not gaps. ⚠ **This row read *"Slice 3 is NOT started and is deliberately out"* for a day after slice 3 had landed and this very table's *Decision record* field said so** — [`CLAUDE.md`](../../CLAUDE.md) authoring rule 7's realization mirror, in the under-claiming direction nobody chases because nothing breaks. Corrected 2026-08-19; it is the exact shape [TASK-020](TASK-020-derive-the-deferral-index.md) §9's `Status`-freshness lint exists to catch, and that lint would have caught this one, since `7e9f610` is an ancestor of `origin/develop`. The measurements in §2 are against this tree; the six mechanism decisions in §4 were taken 2026-08-17. |
| **Type** | Corrective, three slices. Each closes one path by which a fact that **is** in `platform.event_log` never reaches a recipient, with no error surfaced anywhere. Slices 1 and 2 are backend-only; slice 3 crosses into `f5sign-infra` and is therefore **two coordinated PRs**, infra first ([§4 D5](#4-key-decisions)). |
| **Why** | The event log is the system of record and delivery is a projection over it, so a fact being *logged* is supposed to mean it will *arrive*. Three independent gaps break that, and all three fail **silently** — no exception surfaces to an operator, no test reddens, and for the Notification BC the observable symptom is a recipient who was never emailed. The BC's own payload test docblock records that this shape has already reached dev/prod **twice** on this event path. |
| **Builds on** | [ADR-0031](../adr/ADR-0031-event-log-store.md) (the watermark relay, the `platform.event_dead_letter` quarantine and the `MAX_ATTEMPTS` threshold — reused **unchanged**), [ADR-0015](../adr/ADR-0015-async-resilience.md) (the dead-letter decision this completes), [ADR-0014](../adr/ADR-0014-idempotency-three-layer.md) (consumer idempotency, which is what makes any re-delivery safe to attempt), and the shipped quarantine-*visibility* slice ([`ListEventLogDeadLettersCommand`](../../src/F5Sign/Foundation/EventLog/Console/ListEventLogDeadLettersCommand.php)), whose read model this task gives an action to. |
| **Scope** | The **event path only** — the relay's read of the log, the wire codec, and the broker topology that carries it. The log's write side is untouched: no migration, no change to `append_event`, no payload grammar edited, no `PayloadSchemaVersion` bump, and no BC's domain or application layer opened. Slice 2 adds test assets only. |
| **Decision record** | **No new ADR.** [ADR-0015](../adr/ADR-0015-async-resilience.md) governs dead-lettering and [ADR-0031](../adr/ADR-0031-event-log-store.md) governs the relay; this task **completes** both rather than contradicting either, so [repo rule 7](../../CLAUDE.md) is satisfied without minting one. ⚑ **Both records are wrong today and both corrections belong to this changeset, not to the code**: ADR-0015's `Status` claims dead-lettering is *"realized on both failure paths"*, which §2.3 falsifies for the consume side, and its produce-side limb has no recovery path at all (§2.1); ADR-0031's golden-bytes bullet said *"Queued, not built"*. ✅ **All three corrections have since landed, and this field is written in the past tense because they did.** ADR-0015's limb (a) now records the produce-side replay instead of a hand-written checkpoint rewind, and its "neither is built" clause now says (a) is built and (b) deliberately is not; ADR-0031's golden-bytes bullet says *built 2026-08-18*; and both records gained their `Enforced by` / `Realized in` entries **in the changesets that built the code**, per [`README.md`](README.md) §3 and authoring rule 7 — not in a later tidy-up. ✅ **Slice 3 landed 2026-08-18** on `feat/event-decoding-failure-dead-letter`, after verifying its infra half was **deployed** rather than merely merged — `make -C ../f5sign-infra rabbit-check-dlx`, which is the check that reads the property, not the import log that reports success without applying it (D6). `SelfSerializingMessageSerializer::decode()` now wraps every failure in `MessageDecodingFailedException`, and [`EventBrokerUndecodableMessageTest`](../../tests/F5Sign/Foundation/Integration/EventBrokerUndecodableMessageTest.php) drives an undecodable message through the real AMQP receiver into `queue.events.dead-letter`. **Both §5 sabotages were performed and observed for the stated reason** — see §7. With that, **ADR-0015's limb (b) is discharged** and its `Status`, `Enforced by` and `Realized in` are updated in the same changeset ([`CLAUDE.md`](../../CLAUDE.md) authoring rule 7). |
| **Delivery bar** | Per slice in [§5](#5-verification), and none of the three is met by "the suite is green": two of the three properties are **invisible to the default harness** (§5) and one lives in another repository. |
| **Sibling** | ⚑ **BL-32 / BL-84 enumerate the same registry this task's §3.2 census enumerates.** BL-32 wants a completeness check cross-referencing the event-type registry against the broker bindings; §3.2 wants one cross-referencing it against payload fixtures. **Do not scope them independently** — the enumeration half is shared, and BL-32 has already been closed with a point-fix three times (SignatureExecution, Notification, Identity & Access) precisely because nobody built the shared half. |

---

## 1. Why this task exists

A fact reaches a recipient by travelling one path:

```
platform.event_log  ->  EventRelay  ->  f5sign.events (AMQP)  ->  worker  ->  channel
   system of record      watermark            broker              consumes     e.g. email
                          cursor
```

Three drops sit on that path. They are independent, they have different mechanisms, and **each one ends with a fact that is permanently in the log and permanently undelivered**, with nothing raised anywhere a human looks.

1. **A quarantined fact has no way back** (§2.1). The relay is *right* to skip past a poison row after `MAX_ATTEMPTS` — otherwise one bad row wedges delivery for every tenant. But the cursor has then passed it, so no future poll will ever reconsider it. The quarantine became *visible* when [`ListEventLogDeadLettersCommand`](../../src/F5Sign/Foundation/EventLog/Console/ListEventLogDeadLettersCommand.php) landed; it did not become *recoverable*. [BL-15](../BACKLOG.md) stated the residue exactly: *"a quarantined fact still needs `platform.event_checkpoint` rewound by hand."* ✅ **That is the sentence slice 1 falsified on 2026-08-18**, and it is kept here as the record of what this task was written against — the row itself is corrected, and its remaining subject (consume-side dead-lettering, §2.3) is still open.
2. **Nothing asserts the log stays readable** (§2.2). Payload round-trip tests encode and decode with the *same* code, so they agree with themselves while both halves drift away from the bytes already committed to an append-only table. ADR-0031 names this and files the fix as **not built**. It is not hypothetical: [BL-86](../BACKLOG.md) is a live instance — three Envelope payload grammars were retyped `UserId` to `ActorId` on the read side, and `ActorId::fromString()` throws on a bare pre-cutover UUID, so every historical row of those three types is undecodable today. The suite never noticed, because *"nothing anywhere feeds a pre-cutover payload to any `fromPayload()`."* Undecodable is drop 1's input: the relay quarantines it.
3. **An undecodable message kills the worker and comes back** (§2.3). At the far end, a message the wire codec cannot decode is not rejected, not retried and not parked — it is redelivered forever to a worker that dies on it each time.

Drops 2 and 3 both *feed* drop 1's failure mode, which is why the recovery path (§3.1) is worth building even though the other two slices reduce how often it is needed: the class of "a row this code cannot read" is open-ended, and the log outlives every version of the code that reads it.

---

## 2. What already exists (reuse, do not rebuild)

Measured against this tree on 2026-08-17.

### 2.1 The quarantine is complete except for the way out

[`EventRelay`](../../src/F5Sign/Foundation/EventLog/EventRelay.php) already carries the whole produce-side mechanism, and **none of it should be modified**:

- `relayBatch()` reads the slice after the checkpoint, and its counted `try` wraps `reconstruct()` **only** — a deliberate, recently-corrected split (a broker outage must not burn a row's poison counter). Slice 1 must not widen that `try`; `reconstruct()`'s docblock states that adding anything network-shaped to it silently converts outages into permanent quarantines.
- `recordDeadLetter()` upserts `(event_id, consumer)` with an attempt counter and returns the new count. Below `MAX_ATTEMPTS` the batch breaks with the cursor unmoved; at the threshold the cursor advances past the row.
- `deadLetters()` is the read model, and it already computes the field that matters: `quarantined`, i.e. `attempts >= MAX_ATTEMPTS`. Only this class can draw that line, because the threshold is private to it.
- `sanitizeErrorMessage()` already strips NUL bytes and scrubs invalid UTF-8 out of anything written to the `error` column.

`platform.event_dead_letter` holds `event_id`, `consumer`, `error`, `attempt_count`, `failed_at`, keyed `(event_id, consumer)`. **There is no `resolved_at` column and no status column** — the table is a work queue, not an incident log (§4 D2).

[`RelayEventLogCommand`](../../src/F5Sign/Foundation/EventLog/Console/RelayEventLogCommand.php) exposes `limit`, `sleep`, `max-batches` and `time-limit` — **no option touches the checkpoint or replays a row**. [`ListEventLogDeadLettersCommand`](../../src/F5Sign/Foundation/EventLog/Console/ListEventLogDeadLettersCommand.php) exposes `limit` and a `--fail-on-quarantined` switch for cron. So the operator can see the parked fact and can do nothing about it from a CLI.

The relay connects as the `BYPASSRLS` relay role and owns the checkpoint and dead-letter side tables — so slice 1's command needs no new grant.

### 2.2 The payload tests cannot catch a backward-incompatible edit, and ADR-0031 says so

Three tests cover payload round-tripping and **coverage is split across all three**, which constrains §3.2's census:

- [`DomainEventPayloadTest`](../../tests/F5Sign/Foundation/Unit/Serialization/DomainEventPayloadTest.php)
- [`NotificationEventPayloadTest`](../../tests/F5Sign/Notification/Unit/Contract/Event/NotificationEventPayloadTest.php)
- [`SessionEventSerializationTest`](../../tests/F5Sign/Session/Unit/Contract/Event/SessionEventSerializationTest.php)

ADR-0031's *Consequences* files the gap verbatim as **"Not enforced — golden-bytes replay conformance. Queued, not built."**, and states why the existing shape is structurally blind: it *"serializes and deserializes with the same code and therefore can never catch a backward-incompatible `fromPayload()` edit — the two move together and agree with each other while both drift away from the bytes already in the log."* It also promises the fix is *"self-maintaining once seeded"* — which is **only true if a census exists** (§4 D3); with a hand-written list it is self-maintaining in name only.

Already present and reusable:

- [`RegisterDomainEventsPass::isRegistrableEvent()`](../../src/DependencyInjection/Compiler/RegisterDomainEventsPass.php) is **already the authority** on what the event-type registry carries. The census must reuse it rather than re-deriving the rule, or there are two answers to one question.
- [`CanonicalJsonPayloadCodec`](../../src/F5Sign/Foundation/EventLog/CanonicalJsonPayloadCodec.php) is the encoder whose output the fixtures freeze, and it has its own unit test.
- `tests/Fixtures/` exists and holds `pdf/` only — the directory convention is established, the payload set is empty.

### 2.3 A decode failure escapes every net Messenger has — verified, not assumed

This is the one the handoff asserted and this record checked against the installed vendor sources on 2026-08-17.

- `Symfony\Component\Messenger\Bridge\Amqp\Transport\AmqpReceiver::get()` decodes inside a `try` that catches **exactly one type**: `MessageDecodingFailedException`. On that type it rejects the AMQP envelope and rethrows. Any other throwable propagates with the message **neither acked nor rejected**.
- `MessageDecodingFailedException` appears **zero times** in `src/` and `tests/`. [`SelfSerializingMessageSerializer::decode()`](../../src/F5Sign/Foundation/Serialization/SelfSerializingMessageSerializer.php) throws `RuntimeException` on a malformed envelope, a missing `X-Event-Type` header and a body that is not an array; `json_decode` under `JSON_THROW_ON_ERROR` throws `JsonException`; and the terminal `fromPayload()` call throws whatever the event class throws. **None of those is the caught type.**
- `Symfony\Component\Messenger\Worker::run()` calls `$receiver->get()` and iterates the returned generator **outside any `try`**. Its only `try/catch` is inside `handleMessage()`, which is reached with an already-decoded `Envelope` in hand.

Three consequences follow, and the third is the one that makes ADR-0015 wrong:

1. The worker process dies on the throw.
2. The message was never acked or rejected, so the broker treats it as an interrupted delivery and redelivers it — to the next worker, which dies identically. A poison loop.
3. **`retry_strategy` and `failure_transport` are unreachable for this failure.** Both operate on `Envelope`s inside `handleMessage()`, and no `Envelope` is ever produced. So ADR-0015's `Status` claim that the consume side is covered *"then `failure_transport: failed` → `queue.failed`, replayable with `messenger:failed:retry`"* holds for a **handler** failure and not for a **decode** failure. ⚑ ADR-0015's own *Cautionary note* already records three separate ways this retry path *looked* configured while being non-functional, and closes with *"a retry path is not real until a test has watched a message travel it."* This is a fourth of exactly that shape.

**And rejecting is not currently safe either.** In the infra repo's `docker/rabbitmq/definitions.json`, measured 2026-08-17: **none of the 14 declared queues carries `x-dead-letter-exchange`**, and no policy exists (`policies` is an empty list). AMQP `reject` with no dead-letter configuration **discards** the message. The `alternate-exchange` on `f5sign.events` is a different mechanism — it catches messages that match *no binding*, not messages a consumer rejected. This is why §4 D5 fixes the order.

### 2.4 The harness reality that shapes §5

- `async_events` is `in-memory://` under `when@test`, so **the default suite cannot redeliver anything** and is structurally silent about §2.3.
- A real-AMQP transport exists and is opt-in: `async_events_amqp`, used by [`EventLogBrokerRoundTripTest`](../../tests/F5Sign/Foundation/Integration/EventLogBrokerRoundTripTest.php), [`EventBrokerRetryDeliveryTest`](../../tests/F5Sign/Foundation/Integration/EventBrokerRetryDeliveryTest.php) and [`EventBrokerAlternateExchangeTest`](../../tests/F5Sign/Foundation/Integration/EventBrokerAlternateExchangeTest.php). Those are the only tests that touch the broker.
- The per-worktree validation lane brings up **postgres only**, so every broker test **skips** there. A green worktree run is not evidence for slice 3.
- `make worker-status` runs `rabbitmqctl list_queues name messages consumers`, which lists **every** queue with its depth — so a new dead-letter queue reports itself with no new command (§4 D6).

---

## 3. Scope

### 3.1 Slice 1 — a replay command for one quarantined fact (backend)

A console command that takes an event id, re-reads that row from `platform.event_log`, reconstructs and dispatches it exactly as the relay does, and clears its dead-letter row on success. **It does not move the checkpoint.**

**In:** the command; the `EventRelay` method it calls (the reconstruct-and-dispatch path is private today and must be reachable without duplicating the stamp construction); a report of what happened, including a legible failure when the row still cannot be reconstructed.
**Out:** the checkpoint-rewind variant (§4 D1, deferred to §6.1); any change to `relayBatch()`, `reconstruct()` or the counted-`try` split; any new grant.

### 3.2 Slice 2 — golden payload bytes plus a census (backend, tests only)

One frozen canonical-JSON fixture per registrable event type under `tests/Fixtures/`, written once and never edited, plus a hermetic test that decodes each with **today's** `fromPayload()`; plus a census case that enumerates registrable events via `RegisterDomainEventsPass::isRegistrableEvent()` and **fails naming any event type with no fixture**.

**In:** the fixture set; the replay test; the census.
**Out:** repairing what the census finds. ⚑ If the census reddens on the three `ActorId`-retyped Envelope events, that is [BL-86](../BACKLOG.md) being *detected*, which is this slice working — **its repair is BL-86's and must not be smuggled in here**, because BL-86 carries a specific instruction not to bump `PayloadSchemaVersion` and a specific in-tree precedent to mirror. Record the finding, leave the fix.

### 3.3 Slice 3 — make an undecodable message rejectable, then reject it (infra, then backend)

**Infra PR, first:** a dead-letter exchange plus one shared dead-letter queue, and `x-dead-letter-exchange` on the four event queues, in `docker/rabbitmq/definitions.json`.
⚑ **That half is handed off and no longer this repo's to write** — it is specified end to end, including the ordering constraint and the queue-recreation trap, in `notes/HANDOFF-infra-event-dead-letter-exchange.md` in the workspace repo. <!-- OFFREPO: the workspace repo that assembles these subrepos; not reachable from a backend-only checkout. Nothing in this task depends on reading it — §4 D4/D5/D6 carry every fact it restates. -->
**Backend PR, second:** wrap the decode failures in `SelfSerializingMessageSerializer::decode()` in `MessageDecodingFailedException` so `AmqpReceiver` rejects rather than letting the worker die.

**In:** those two changes and the tests in §5.
**Out:** classifying permanent vs transient *handler* faults (ADR-0015 files that separately as *"refinement, queued"*); any change to the `failed` transport or `queue.failed`; a reader command for the new queue (§4 D6).

---

## 4. Key decisions

**D1 — Recovery is a surgical replay of one event, not a checkpoint rewind.** Rewinding `platform.event_checkpoint` re-delivers *everything* after the rewind point; consumers are idempotent ([ADR-0014](../adr/ADR-0014-idempotency-three-layer.md)) so it is survivable, but it is a blunt instrument for the real case, which is *"one row was poison, the cause is fixed, send that one."* Replay touches exactly the named row and leaves the cursor alone. The rewind variant is deferred, not rejected (§6.1).

⚠ **The accepted cost, stated so it is not discovered later: a replayed fact arrives out of order** relative to its siblings in the log. Idempotent consumers absorb repetition, which is not the same property as absorbing reordering. Any reactor whose correctness depends on ordering must be identified before the command is used in anger; today the relay's single cursor is the only thing providing that ordering, and nothing documents a reactor that requires it.

**D2 — A successful replay deletes the dead-letter row.** `platform.event_dead_letter` has no `resolved_at` and no status column, and `deadLetters()` presents it as a queue an operator drains. Deleting is what "resolved" means in that shape, and it keeps `--fail-on-quarantined` honest — a cron that stays red after a successful replay trains operators to ignore it. The alternative (add a `resolved_at` column, keep the history) is a migration and an incident-log model; it is a reasonable future shape and is recorded in §6.2, not built here.

**D3 — The fixture set is guarded by a census, not by a hand-written list.** An enumeration is a predicate whose exempt set is *"everything nobody has remembered to add yet"* ([`CLAUDE.md`](../../CLAUDE.md) authoring rule 5). That exact shape is BL-32, which has now been point-fixed three times because the shared census was never built. A hand-written fixture list would ship the identical defect into the identical subsystem.

⚑ **The census must see the union of the three payload tests** named in §2.2, not one file. A single-file census reddens on events that are genuinely covered elsewhere, and the first person to hit that will "fix" it by shrinking the census.

**D4 — One shared dead-letter queue for the four event queues, not one each.** The reader is a human running a command during an incident; four places to look buys nothing. RabbitMQ stamps the originating queue into the `x-death` header, so provenance is not lost.

**D5 — Infra ships first, and this order is the opposite of the intuitive one.** Landing the backend wrap first would convert a *loud* failure (poison loop, dead worker, message still in the broker) into a *silent* one (message rejected into nothing and discarded), because a reject with no dead-letter configuration discards. That trades an obvious bug for data loss. Infra PR, deployed, then backend PR. ⚑ **A backend PR merged while the infra one is unmerged is a regression, not a partial improvement** — reviewers of the backend half must check the infra half is deployed, not merely open.

**D6 — The dead-letter exchange is declared as per-queue `x-dead-letter-exchange` arguments, and the queue-recreation cost is accepted and written down.** The alternative is a RabbitMQ *policy*, which applies to already-declared queues without recreating them; it is rejected here for consistency with `definitions.json`, where every other topology fact is declared explicitly per object, and because `definitions.json` is plain JSON with no comments, so a policy's effect would be invisible to someone reading the queue list.

⚠ **The cost, stated because it is a genuine future operation: queue arguments are immutable in RabbitMQ.** Re-declaring an existing queue with different arguments fails `PRECONDITION_FAILED`, so the four event queues must be **deleted and recreated** for the new argument to take. **Re-measured 2026-08-18 against RabbitMQ 4.0 and this sentence is right — but it is right one level below where the deployment happens, and that gap is the dangerous part.** At the AMQP protocol level a redeclare does fail loudly: `AMQPQueueException — Server channel error: 406, PRECONDITION_FAILED - inequivalent arg 'x-dead-letter-exchange' … received the value … but current is none`. ⛔ **`rabbitmqctl import_definitions`, which is how the topology is actually deployed, does NOT surface it.** It keeps the queue's **old** arguments, reports success, and logs no warning — so `make reload-rabbitmq` can exit green with the argument not applied. That makes the failure **silent**, which is the exact class this whole task exists to remove, sitting in the task's own deployment step. **So the deployed state is verified with `make -C ../f5sign-infra rabbit-check-dlx`, never with the import log**; it asserts the argument on all four queues and reddens if any lacks it. Today that is a volume reset in dev and costs nothing. The day a long-lived environment exists, it is a real operation that must drain the queues first — `make worker-down`, depth 0 via `make worker-status`, then recreate. It is safe to drain because the log, not the queue, is the system of record. If that operation ever looks unacceptable, the policy variant (§6.3) is the escape hatch and switching to it is not a redesign.

**D7 — No reader command for the dead-letter queue.** The mistake this task exists to avoid repeating is a quarantine nobody reads, so this needs a reason rather than an omission: `make worker-status` already lists every queue with its depth, so a new queue surfaces itself with no code. Recovery does not come from that queue either — the fact is still in the log, so the recovery path is slice 1's replay. The queue is a **diagnostic** surface, not a recovery one.

---

## 5. Verification

⛔ **"The suite is green" is not a bar for any slice here, and for slice 3 a green run is actively misleading** — `async_events` is `in-memory://` in test, so the default harness cannot redeliver a message and is structurally incapable of observing the poison loop. Each property below names the harness that can actually reach it ([`README.md`](README.md) §6).

| Slice | Property | Harness that can see it | Why the default one cannot |
|---|---|---|---|
| 1 | A quarantined fact is dispatched again and its dead-letter row is gone | `Foundation/Integration` — real Postgres, DAMA rollback | Needs the log, checkpoint and dead-letter tables |
| 1 | The checkpoint is **unchanged** after a replay | `Foundation/Integration`, asserting the row before and after | Nothing else distinguishes replay from rewind |
| 2 | Frozen bytes still decode under today's `fromPayload()` | `Unit` — hermetic, no DB or broker | Reachable everywhere, including the per-worktree lane |
| 2 | A registrable event with no fixture reddens, **naming it** | `Unit` census case | — |
| 3 | An undecodable message is **rejected**, not redelivered, and the worker survives | `Foundation/Integration` on `async_events_amqp`, beside the existing `EventBroker*` tests | `in-memory://` never redelivers; this property does not exist there |
| 3 | The rejected message lands in the dead-letter queue rather than vanishing | Same, and it **also depends on the infra PR being deployed** | The topology is declared in another repository |

⚠ **The per-worktree validation lane runs postgres only**, so every slice-3 test **skips** there and a green worktree run is not evidence. Slice 3 must be validated against a stack with RabbitMQ up. This is the same gap that was named honestly when the relay's poison-counter fix landed, and the same one BL-31 records for Notification end-to-end.

**Sabotage before trusting any of it** ([`CLAUDE.md`](../../CLAUDE.md) authoring rule 4). Each step must fail *for the stated reason*, not incidentally:

1. **Slice 1** — point the replay at an event id that is *not* quarantined, and at one that still cannot be reconstructed. Both must report legibly rather than succeed quietly. Then re-run a successful replay with the dead-letter delete removed: the "row is gone" assertion must redden.
2. **Slice 2** — hand-edit one frozen fixture's bytes. The replay test must redden. Restore. Then delete one fixture file: the census must redden **naming that event type**, not merely counting. ⚑ Then add a throwaway registrable event class with no fixture and confirm the census reddens for it too — deleting an existing fixture and adding a new event are different code paths through the census, and only the second is the case it exists for.
3. **Slice 3** — revert the `MessageDecodingFailedException` wrap and confirm the integration test observes the worker dying and the message returning, not merely "an exception was thrown". Then, with the wrap restored but the infra dead-letter argument removed, confirm the message is *discarded* — this is the D5 order made observable, and it is the single most important assertion in the task.

---

## 6. Open follow-ups (track, don't solve here)

1. **The checkpoint-rewind command is deferred, not rejected** (D1). It is the right tool for a *broad* incident — many rows quarantined across a window, e.g. after a bad deploy — where replaying ids one at a time is impractical. What would force it: the first incident with more quarantined rows than an operator will paste by hand. It needs a guard the replay does not: rewinding re-delivers everything after the point, so it must state the blast radius before doing it. Indexed as [BL-110](../BACKLOG.md). ⚑ This read `BL-113` until the replay landed, and `BL-113` is an unrelated row about a plaintext credential — the same wrong pair [ADR-0031](../adr/ADR-0031-event-log-store.md)'s Consequences carried, from the same authoring moment. Both named a row that never held this deferral: `BL-113` did not exist on `develop` when either was written.
2. **`platform.event_dead_letter` as an incident log rather than a work queue** (D2). Deleting on successful replay loses the record that a fact ever failed, which is fine for operations and not fine for a post-mortem. A `resolved_at` column would keep both, at the cost of a migration and a `deadLetters()` predicate change. Not needed until someone asks the question *"how often does this happen?"* — which nothing can answer today either way. ⚑ **Indexed as [BL-129](../BACKLOG.md), which reaches the same deferral from the security audit and proposes the *opposite mechanism* — read both before building either.** That row wants an append to `platform.event_log` at replay time carrying actor and reason, and argues explicitly against keeping the dead-letter row, because a row that survives its resolution re-opens the permanently-red-alarm problem the delete exists to avoid. The two shapes are not compatible and neither has been chosen; what is agreed is only that the incident currently has no home at all. BL-129 also asks for something this item does not — *who* replayed and *why* — which a `resolved_at` column cannot carry.
3. **The RabbitMQ policy variant of the dead-letter declaration** (D6). If a long-lived environment ever makes deleting and recreating the four event queues unacceptable, a policy sets the same argument on live queues without recreation. Recorded so the escape hatch is known rather than rediscovered under incident pressure. Indexed as [BL-154](../BACKLOG.md) — it was the one follow-up here with no cross-cutting entry, and it is the one whose reader is an operator under pressure who has no reason to open this task at all. ⚠ The change itself lands in `f5sign-infra`, not here.
4. **BL-32's forcing check is still owed and this task does not discharge it.** §3.2's census cross-references the event-type registry against **payload fixtures**; BL-32 wants one cross-referencing it against **broker bindings**. Same registry, same shape, different right-hand side — and BL-32 has been point-fixed three times without the check being built. Whoever builds either should read the other first; see the `Sibling` field.
5. ✅ **ADR-0015 and ADR-0031 realization updates — done, and done where this said they had to be: with the code.** ADR-0015's `Status` gained the produce-side recovery path in `48ea7b5` and the consume-side decode limb in `7e9f610`; ADR-0031's golden-bytes bullet reads *built 2026-08-18* from `4e6335a`. Both records name the new artifacts under `Enforced by` / `Realized in`. This item is kept rather than deleted because the reason it was written still binds the next task: [`README.md`](README.md) §3 and [`CLAUDE.md`](../../CLAUDE.md) authoring rule 7 both record that the error here is always in the under-claiming direction — three separate branches shipped work and left the record saying *not yet*, and this task's own `Status` then did it again about slice 3, which is recorded as an instance in [TASK-020](TASK-020-derive-the-deferral-index.md) §9 rather than counted here — two records counting the same series independently is how a count goes wrong.
6. **Notification has still never been driven end-to-end with workers up** ([BL-31](../BACKLOG.md)). This task removes three ways the path drops a fact silently; it does not substitute for once watching a `NotificationRequested` become an email against a real broker and a real SMTP sink. The two are complements — and BL-31 is the only one of them that would have caught the missing binding that stranded delivery in dev.

---

## 7. Slice 3 — what was measured on delivery (added 2026-08-18)

§5's two sabotage steps for this slice, with what each produced. Both were run against the live broker;
neither is inferable from a green suite.

**1. Wrap reverted — the message comes back.** §5 asks for *the worker dying and the message returning,
not merely "an exception was thrown"*, so the observation is a queue depth taken **from outside the PHP
process**, because in-process the two worlds are indistinguishable:

| | `queue.envelope.events` ready | `queue.events.dead-letter` ready |
|---|---|---|
| wrap reverted | **1** — the identical bytes are back for the next worker | 0 |
| wrap in place | **0** — gone from the source queue | 1 |

⚑ **This step also caught a decorative assertion in the new test and it is worth recording why.** The
natural in-process check — *"a second `get()` comes back empty"* — was written first and **passes in both
worlds**: an unrejected message is merely *unacknowledged on the receiver's own channel*, so it is not
`ready` for any reader either, and it returns to the queue only when that connection dies. It was removed
rather than left as a green line, and the test's docblock carries the table above so nobody restores it.

**2. Dead-letter argument absent — the message is discarded.** Run on a throwaway queue rather than by
mutating the four shared event queues, so the experiment is repeatable and destroys nothing:

| probe queue | source ready after `nack` | `queue.events.dead-letter` |
|---|---|---|
| no `x-dead-letter-exchange` | 0 | **0 — discarded** |
| with `x-dead-letter-exchange` | 0 | **1 — captured** |

That is D5 made observable: the wrap without the infra half converts a loud failure into data loss.

**3. D6's `PRECONDITION_FAILED` claim was re-measured, and it survives — one level below where it
matters.** See D6, now corrected in place: the protocol-level redeclare does fail loudly (406), and
`import_definitions` does not surface it. The task's own deployment step was the silent failure.

### 7.1 What this slice did not do

- **The `x-death` header is not asserted.** D4 leans on it for provenance, and it is present, but reading
  it is a diagnostic an operator performs rather than a property this pins. Asserting it here would pin
  RabbitMQ's header format, which is not ours to freeze.
- **No reader command for the dead-letter queue** (D7, unchanged): `make worker-status` already lists
  every queue with its depth, and recovery comes from the log via slice 1's replay, not from that queue.

