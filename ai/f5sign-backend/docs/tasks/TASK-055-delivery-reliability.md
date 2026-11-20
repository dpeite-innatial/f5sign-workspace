# TASK-055 — A delivery is retried by what it carries, ends instead of hanging, and is checked again before it goes out late

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `feat/delivery-reliability`** (code tip `f84c0b0d`), 2026-10-09 — suite green under the `wt-backend` lane of this worktree (6362 tests, 74185 assertions; lint, deptrac and PHPStan clean). contract-check passed; doctrine-guard and the security audit warned with 0 blockers (their follow-ups are homed in §7). Infection, filtered to the 51 `src/` files the branch touches (owner's 2026-10-09 per-task procedure): covered-MSI 88 % (gate 85), MSI 81 % (gate 70), 960 mutants in 6 min 17 s, measured at code tip `f84c0b0d`; of the 41 survivors on changed lines, 32 were then killed by tests-only commit `e440d32c` (fast tier green, 5305 tests) and 9 are justified in §8. Not merged; pending review. **Left out:** the delayed redelivery at 60/300/900 s through RabbitMQ is not observed (`async_events` is `in-memory://` under test); the observation on the dev stack is still owed (BL-404), ADR-0079 was accepted by the owner on 2026-10-09 as **Accepted (enforcement partial)** for that reason. |
| **Type** | **Forward build with a behaviour change on paths that run today** (email invitations and delivered one-time codes), across Notification (retry profile, transient failure, send-time check, cancellation), Foundation (the retry strategy of `async_events`) and Session (one field on the code request). |
| **Why** | A delivery that fails for longer than ~80 seconds stays `PENDING` for ever: the occasion is never decided, the stored link is never forgotten, and only an operator replaying the dead letter moves it. A code retried for those ~80 seconds can arrive after the signer's 60-second cooldown allowed a new one, and is then the wrong code. And nothing asks, before a late message goes out, whether it still makes sense. All three are true for email today. |
| **Decision record** | [ADR-0079](../adr/ADR-0079-a-delivery-retries-by-what-it-carries.md) — proposed on 2026-10-09; **Accepted (enforcement partial)** by the owner the same day, once the §6 bars were green (the broker delay is unobserved, BL-404). It amends [ADR-0037](../adr/ADR-0037-notification-supporting-bc.md): a `Delivery` gains a transient failure and a terminal "not needed". |
| **Builds on** | [`ChainConflictRetryStrategy`](../../src/F5Sign/SignatureExecution/Infrastructure/Messenger/ChainConflictRetryStrategy.php) and the `async_events` block of [`config/packages/messenger.yaml`](../../config/packages/messenger.yaml) · [`TransmitDeliveryUseCase`](../../src/F5Sign/Notification/Application/UseCase/TransmitDeliveryUseCase.php) (its convergence guard) · [`DeliveredCodePolicy`](../../src/F5Sign/Session/Application/Service/DeliveredCodePolicy.php) · [TASK-023](TASK-023-sms-codes-and-recipient-phone.md) and [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.7 (a code names its own channel) · [ADR-0065](../adr/ADR-0065-recipient-delivery-is-its-own-dimension.md). |
| **Order** | **First of four, and it stands alone.** [TASK-056](TASK-056-delivery-facts-and-sender-visibility.md) may be built in parallel or after (§5 D3 says who adapts to whom); [TASK-031](TASK-031-channel-selection-beyond-email.md) needs both (its ordered fallback moves on this task's transient failure and skips what TASK-056 marks); [TASK-059](TASK-059-the-trail-shows-how-each-invitation-travelled.md) needs TASK-056. |

---

## 1. Why this task exists (measured on the tree, 2026-10-09)

- **The schedule belongs to someone else.** `async_events` names `ChainConflictRetryStrategy` as its
  retry strategy: four retries at 2, 6, 18 and 54 seconds (about 80), then the `failed` transport. The
  retry is of the **event** `DeliveryRequested`; its reactor `OnDeliveryRequested` dispatches
  `TransmitDelivery` synchronously inside it. Every kind of message gets the same ~80 seconds.
- **After that the delivery hangs.** `TransmitDeliveryUseCase` records a terminal `FAILED` only for a
  *returned* rejection (a permanent provider verdict); a *thrown* failure rolls back and leaves the
  delivery `PENDING`. After the last retry nothing writes it again, so `isDelivered()` and
  `isUndeliverable()` are both `false` for ever and `Notification::forgetSecretsOnceSettled()` never
  runs: the signing link stays in `notification.notification.variables`.
- **A code can arrive after it was replaced.** `SignerAuthPolicy::MIN_SECONDS_BETWEEN_ISSUANCES` is 60,
  the retry ladder reaches ~80, and a new code invalidates the previous one. The signer who asked again
  at second 61 receives the first code at second 70, types it and spends an attempt.
  `OneTimeCodeRequest` carries no deadline.
- **A late message is not re-checked.** `TransmitDeliveryUseCase` sends whenever the delivery is
  `PENDING`. At ~80 seconds that is a footnote; at the ~20 minutes this task introduces it would send an
  invitation to a corrected-away address, for a voided envelope.

## 2. What already exists (reuse, do not rebuild)

- **Convergence.** `TransmitDeliveryUseCase` loads the occasion `FOR UPDATE` and returns when the
  delivery is not `PENDING`, so a dead-letter replay of a settled delivery is already a no-op. Every
  new terminal status below keeps that property by being terminal.
- **The bound for a code already has a home**: `DeliveredCodePolicy::nextIssuanceAllowedAt()` returns
  `issuedAt + MIN_SECONDS_BETWEEN_ISSUANCES`, and `IssueAuthChallengeUseCase` is the one construction
  site of `OneTimeCodeRequest` in `src/`. Session computes the deadline there; Notification never
  learns the policy.
- **Listener precedents** for `WorkerMessageFailedEvent`: `SentryMessengerContextListener` and
  `CustodianRunListener`. ⚠ The first records that **the tenant scope has already unwound** by the time
  that event fires (`ReestablishTenantMiddleware` restores the previous scope as the stack unwinds), so a
  listener that writes must lift the scope from the envelope's `TenantStamp` itself.
- **Reads of Envelope are allowed from Notification**: `EnvelopeQueryInterface::getEnvelopeContext()`
  returns an `EnvelopeContextView` (status, `closedAt`, `expiresAt`) whose `RecipientView`s carry `email`,
  `phone`, the leg `outcome` and `invitationsRevokedAt`. Only `Recipient::correctContact()` revokes
  invitations; a resend is additive and revokes nothing.
- **`failure_reason` is PII-bearing** (a refusal quotes the destination back; see the comment in
  `DbalNotificationRepository`), so a transient failure records a closed code, never an exception
  message.
- **`notification_delivery.status` is `TEXT` with no CHECK** (`Version20260721000001`), so a new status
  needs no constraint; hydration is strict (`DeliveryStatus::from`), so code deploys before data.
- **Tests to extend, not duplicate:** `ChainConflictRetryStrategyTest`, `TransmitDeliveryUseCaseTest`,
  `NotificationTest`, `DeliveryPolicyTest`, `DeliveryStatusTest`, `NotificationEventPayloadTest`,
  `PropagateDeliveryFailureUseCaseTest`, `IssueAuthChallengeUseCaseTest`,
  `DbalNotificationRepositoryTest`, and `NotificationRowLockTest` (the `ProbesRowLocks` precedent).

## 3. What gets built

**3.1 The profile on the message.** `DeliveryRequested` gains `profile` (`NOTICE` | `CODE`) and a
nullable `send_before`, both additive. `fromPayload()` accepts their absence (a log row or queued
message written before this task decodes as `NOTICE` with no deadline). The profile is read from the
purpose by a **new exhaustive predicate on `NotificationPurpose`** with no `default` arm; it is not
`namesItsOwnChannel()` reused for a different question. `send_before` rides `OneTimeCodeRequest` as a new
nullable-and-last field that the consumer **requires** (every purpose a code request resolves to is an
`AUTH_OTP_*` one; an unresolvable `gate`/`act` pair is already refused), and a delivery whose purpose has the
`NOTICE` profile refuses one where it is created. It is stored on the delivery
(`notification_delivery.send_before`, nullable `TIMESTAMPTZ`). Session sets it from
`DeliveredCodePolicy::nextIssuanceAllowedAt($requestedAt)`.

**3.2 The retry strategy.** A Foundation-level strategy on `async_events` that delegates **by message**
to tagged delegates, so Foundation names no bounded context (deptrac lets Foundation see only Kernel and
Vendor). `ChainConflictRetryStrategy` stays, unchanged, as the delegate for every message nobody else
claims; Notification registers a delegate claiming `DeliveryRequested`. Schedules are §5 D2. For a
`CODE` the delegate also answers "not retryable" when the next attempt would land at or after
`send_before` (it needs the `Clock`).

**3.3 The transient end.** A listener on `WorkerMessageFailedEvent` that acts only when no retry follows
and the message is a `DeliveryRequested`: it lifts the tenant scope from the `TenantStamp`, and
dispatches a Notification command that loads the occasion `FOR UPDATE` and records the delivery `FAILED`
with a **transient kind** and a closed reason code (`RETRIES_EXHAUSTED`, `SEND_WINDOW_PASSED`).
Idempotent: a delivery that is no longer `PENDING` is left alone. The same transient failure is recorded
by `TransmitDeliveryUseCase` itself when it finds `now >= send_before` on a `CODE`, before rendering or
sending: that is how a dead-letter replay a day later stays unsent.

**3.4 The send-time check.** Immediately before rendering, `TransmitDeliveryUseCase` reads Envelope and
applies the check the purpose calls for (§5 D4). A delivery that fails it is not sent and becomes
`NOT_NEEDED`: terminal, neither success nor failure. A failed *read* is not an answer (§5).

**3.5 Cancellation.** Reactors on `RecipientCorrected`, `EnvelopeVoided` and `EnvelopeCompleted` mark the
still-`PENDING` **invitation-family** deliveries of that recipient or envelope `NOT_NEEDED` (a new
repository query over the `notification_addressee_idx` / `notification_subject_idx` columns, loaded under
the root lock). The send-time check is the guarantee; this is the tidy-up that lets
`forgetSecretsOnceSettled()` fire promptly. ⚑ **Deliberately not cancelled by a reactor** (owner, 2026-10-09): `EnvelopeClosedBySender` (an `EnvelopeCompleted` always follows it) and the close of one recipient's leg (signed, declined, released). The send-time check refuses those invitations at their next attempt; the cost is the stored link living until then, at most ~15 minutes. [TASK-031](TASK-031-channel-selection-beyond-email.md)'s
channel change calls the same use case.

**3.6 Statuses and folds.** `DeliveryStatus::NOT_NEEDED` (terminal, `isFailure()` false, off the
success ladder). The `Notification` folds count **only deliveries that are not `NOT_NEEDED`** as the
total, and an occasion whose every delivery is `NOT_NEEDED` is neither delivered nor undeliverable.
⛔ `DeliveryPolicy::isDefeated(0, 0)` is `true` for every policy (`!isSatisfied(0, 0)`), so without an
explicit guard an occasion cancelled as stale would report itself **failed**.

**3.7 Propagation.** `PropagateDeliveryFailureUseCase` ignores a transient failure (§5 D3).

**3.8 Docs: a rule-1 sweep.** `rg -n 'rolls back and the retry ladder|retry ladder|stays .PENDING|ChainConflictRetryStrategy|transient' src tests docs config`
and convert one file at a time: `TransmitDeliveryUseCase`'s failure-contract docblock,
`DeliveryStatus`' class docblock (it says a throw "leaves the delivery `PENDING` for the retry ladder"),
`Notification::recordFailed()` and `isUndeliverable()` ("an outage is not a verdict"), the
`async_events` comment in `messenger.yaml`, ADR-0072 §2.10's retry sentence, ADR-0037's failure contract,
`docs/ddd/notification-domain-model.md`, `docs/LIVE_SCHEMA.md` (two new columns, `send_before` and `failure_kind`), ADR-0079's Status /
Enforced by / Realized in.

## 4. Scope

**In scope:** §3.1–§3.8, the migration for `send_before`, `failure_kind` and nothing else, and the wiring
test for the composite.

**Concepts re-cut:** "the retry ladder" (one schedule for every message becomes one per profile);
`DeliveryStatus` (gains `NOT_NEEDED`); `Notification::recordFailed()` and `isUndeliverable()` (a failure
now has a kind, and an outage can end a delivery); `TransmitDeliveryUseCase`'s failure contract (a thrown
failure no longer leaves the delivery `PENDING` for ever); `PropagateDeliveryFailureUseCase` (filters a
transient failure).

**Out of scope:** telling the signer a code was not sent (it needs Notification to signal Session, a new
cross-context path and a signer change); carrier receipts and late bounces ([BL-390](../BACKLOG.md));
a periodic sweep for deliveries lost by other means (ADR-0079 §7.4); anything that selects a channel
([TASK-031](TASK-031-channel-selection-beyond-email.md)); recording the failure for the sender
([TASK-056](TASK-056-delivery-facts-and-sender-visibility.md)).

## 5. Key decisions

**D1 — How a transient failure is represented.** (a) A new `failure_kind` column (`PERMANENT` |
`TRANSIENT`), status stays `FAILED`. (b) A new status `FAILED_TRANSIENT`. **Decided (owner, 2026-10-09): (a).** Every
existing reader of "failed" (`isFailure()`, `isUndeliverable()`, `isTerminal()`, the ordered fallback)
keeps working unchanged, and only the readers that must tell the two apart (the Envelope-bound
propagation) ask the kind. Rule 6: every `FAILED` row that exists was written from a returned rejection,
so the migration backfills `PERMANENT`, with `failure_kind IS NOT NULL` required exactly when
`status = 'FAILED'` as a CHECK. A new row must never be backfilled by a predicate on `failure_reason`.

**D2 — The schedules** (ADR-0079 §2.1 leaves the numbers to this task). **Decided (owner, 2026-10-09):** notices
retry at 60 s, 300 s and 900 s (three retries, about 21 minutes); codes at 5 s, 15 s and 30 s (three
retries, 50 s), never at or past `send_before`. Both are class constants with their rationale beside
them, as `ChainConflictRetryStrategy`'s are.

**D3 — Who marks a destination when a delivery fails transiently.** Today the whole occasion's failure
reaches Envelope through `OnNotificationFailed` → `PropagateDeliveryFailureUseCase` →
`markRecipientDeliveryFailed()`, which writes the destination's trace, `invitation_failed_at` and
`RecipientDeliveryFailed` **together**. A transient exhaustion that reached it would stamp the contact
`FAILED` in the trace, which [ADR-0078](../adr/ADR-0078-delivery-outcomes-come-back-as-facts.md) §2.1 and
TASK-031's skip rule read as "permanently refused". Options: (1) let it through and accept the stamp;
(2) split that method here; (3) filter transient failures out of the propagation, leaving the recipient
with no recorded failure until TASK-056 records the invitation's outcome. **Decided (owner, 2026-10-09): (3).** It
regresses nothing (today a hung delivery shows the sender nothing either), keeps the coupling's split in
the task that owns it, and a mixed occasion still propagates its permanent destinations. If TASK-056
merges first, its trace-only path filters on the same kind and the bar in §6 covers both paths.

**D4 — Which check each purpose gets.** Decided (owner, 2026-10-09). A closed table, as an exhaustive `match` on `NotificationPurpose`
with no `default` (a purpose added later must classify itself):

| Purposes | Checked before sending |
|---|---|
| `RECIPIENT_INVITATION`, `RECIPIENT_INVITATION_RESENT` | envelope not closed or terminal · recipient's leg open · destination equals the recipient's **current** contact for that channel · the occasion's `requestedAt` is not before `invitationsRevokedAt` |
| `ENVELOPE_COMPLETED`, `ENVELOPE_ENDED_*`, `SEALED_COPY_READY` | destination equals the current contact **only**. ⛔ "Envelope still open" cannot apply: these exist *because* it closed |
| `AUTH_OTP_ACCESS`, `AUTH_OTP_SIGNING`, `AUTH_OTP_DECLINE` | `send_before` only; no Envelope read on the code path (Session checked at issuance, and the window is 60 s) |

`requestedAt` is a conservative stand-in for the token's issue instant, which the occasion does not
store; it can only err towards not sending a link minted around a correction, and that correction
creates its own invitation. ADR-0079 §2.5's "superseded" is read narrowly: only a correction revokes.

**D5 — A failed read is a retry, never a verdict.** Decided (owner, 2026-10-09). Any exception from the Envelope read, including
`EnvelopeNotFoundException`, propagates and the delivery stays `PENDING` for the next attempt. A silent
drop of a valid invitation is the worse error.

## 6. Acceptance bars

| Id | Criterion (an observable behaviour) | Origin | Tier / harness | Sabotage |
|---|---|---|---|---|
| AC-1 | A `NOTICE` delivery at its second retry (retry count 1) waits 300 s | derived — ADR-0079 §2.1 | Unit | make the Notification delegate stop claiming `DeliveryRequested` |
| AC-2 | A `CODE` delivery at its second retry (retry count 1) waits 15 s | derived — ADR-0079 §2.1 | Unit | make the Notification delegate stop claiming `DeliveryRequested` |
| AC-3 | A non-delivery message at its second retry (retry count 1) waits 6 s | derived — ADR-0079 §2.4 | Unit | make the composite's fallback the Notification delegate (inferred) |
| AC-4 | A `CODE` with `send_before` 20 s ahead is not retryable when the wait would be 30 s | derived — ADR-0079 §2.2 | Unit | drop the `send_before` comparison in the delegate (inferred) |
| AC-42 | The same `CODE` with `send_before` 40 s ahead is retryable | derived — rule 4 (control case for AC-4) | Unit | answer "not retryable" for every `CODE` |
| AC-5 | `ArtifactChainConflictException` on a non-delivery message still gets 183 retries; `ChainConflictRetryStrategyTest` passes unmodified | derived — ADR-0079 §2.4 | Unit | make the composite's fallback the Notification delegate; the chain-conflict case must redden naming that case |
| AC-6 | The container's `async_events` retry strategy is the composite | derived — ADR-0079 §2.4 | Integration (`KernelTestCase`) | point `async_events` back at `ChainConflictRetryStrategy` (inferred) |
| AC-7 | The composite's delegates include `ChainConflictRetryStrategy` | derived — ADR-0079 §2.4 | Integration (`KernelTestCase`) | untag `ChainConflictRetryStrategy` as a delegate (inferred) |
| AC-8 | A `DeliveryRequested` payload without the new keys decodes as `NOTICE` with no deadline | derived — ADR-0079 §2.1 | Unit | make `fromPayload()` require the new keys (inferred) |
| AC-9 | The new `DeliveryRequested` payload has a closed key set: an extra key fails | derived — rule 5 (closed key set) | Unit | let `fromPayload()` accept unknown keys (inferred) |
| AC-10 | A `SINGLE` email invitation whose retries are exhausted is `FAILED`/`TRANSIENT` with `RETRIES_EXHAUSTED` | derived — ADR-0079 §2.3 | Application (faked ports) | drop the exhaustion handler (inferred) |
| AC-11 | That delivery's `link` variable is gone | derived — ADR-0079 §2.3 | Application (faked ports) | skip `forgetSecretsOnceSettled()` on the transient end (inferred) |
| AC-12 | `NotificationFailed` is recorded for it | derived — ADR-0079 §2.3 | Application (faked ports) | skip recording the event on the transient end (inferred) |
| AC-13 | Running the exhaustion listener twice changes nothing | derived — ADR-0079 §2.3 | Application (faked ports) | drop the "no longer `PENDING`" check (inferred) |
| AC-14 | An occasion mixing one `PENDING` and one transient `FAILED` under `ANY` is neither delivered nor undeliverable | derived — ADR-0079 §2.3 | Application (faked ports) | count a transient `FAILED` as undeliverable (inferred) |
| AC-15 | The listener, driven with a synthesized `WorkerMessageFailedEvent` carrying a `TenantStamp` and no ambient tenant, still ends the delivery | derived — ADR-0079 §2.3 | Infrastructure | stop lifting the tenant scope from the `TenantStamp` (inferred) |
| AC-43 | A failed `DeliveryRequested` that will still be retried leaves the delivery `PENDING` | derived — rule 5 (the set the listener exempts) | Infrastructure | end the delivery on every failure, ignoring `willRetry()` |
| AC-44 | A non-delivery message whose retries are exhausted makes the listener dispatch nothing | derived — rule 5 (the set the listener exempts) | Infrastructure | drop the message-class check in the listener |
| AC-16 | A `CODE` with `send_before = T+60` is sent at `T+59` | derived — ADR-0079 §2.2 | Application (`FakeClock`) | — see *Notes on AC-17* (inferred) |
| AC-17 | The same `CODE` at `T+61` is not sent: the delivery is `FAILED`/`TRANSIENT`/`SEND_WINDOW_PASSED` and the channel double recorded zero sends | derived — ADR-0079 §2.2 | Application (`FakeClock`) | delete the window guard; the `T+61` case must redden |
| AC-45 | The same `CODE` at exactly `T+60` is not sent (`now >= send_before`) | derived — ADR-0079 §2.2 (boundary of AC-16/AC-17) | Application (`FakeClock`) | compare with `>` instead of `>=` |
| AC-18 | A `NOTICE` a day late is sent | derived — ADR-0079 §2.2 | Application (`FakeClock`) | apply the window guard to `NOTICE` (inferred) |
| AC-19 | An occasion whose only failure is transient makes zero calls on the Envelope write port | derived — ADR-0078 §2.1 | Application (fake Envelope write port) | drop the kind filter |
| AC-20 | One permanent and one transient failure make exactly one call, for the permanent channel's destination | derived — ADR-0078 §2.1 | Application (fake Envelope write port) | drop the kind filter |
| AC-21 | Each stale invitation-family delivery ends `NOT_NEEDED` and is not sent (members AC-21a…h) | derived — ADR-0079 §2.5 | Application (fake Envelope query) | see *Notes on AC-21* |
| AC-22 | Each notice purpose on a closed envelope is sent (members AC-22a…g) | derived — ADR-0079 §2.5 | Application (fake Envelope query) | apply the invitation check to that purpose; its member must redden |
| AC-47 | Each notice purpose addressed to a destination no longer the recipient's current contact ends `NOT_NEEDED` (members AC-47a…g) | derived — ADR-0079 §2.5 | Application (fake Envelope query) | drop the current-contact check for notices |
| AC-48 | A `RECIPIENT_INVITATION` on an open envelope, open leg, current contact and no revocation is sent | derived — rule 4 (control case for AC-21) | Application (fake Envelope query) | answer `NOT_NEEDED` for every invitation |
| AC-23 | Each one-time-code purpose on a voided envelope is sent inside its window (members AC-23a…c) | derived — ADR-0079 §2.5 | Application (fake Envelope query) | add an Envelope read to the code path (inferred) |
| AC-24 | A census over `NotificationPurpose::cases()` fails naming any purpose the check table does not classify | derived — ADR-0079 §2.5 | Unit (inferred) | add a `default` arm, or a case with no arm (inferred) |
| AC-25 | When the Envelope read throws `RuntimeException`, the exception propagates, the delivery stays `PENDING` and nothing is sent | derived — ADR-0079 §2.5 | Application (query double throws) | catch the exception and mark the delivery `NOT_NEEDED` (inferred) |
| AC-26 | When the Envelope read throws `EnvelopeNotFoundException`, the exception propagates, the delivery stays `PENDING` and nothing is sent | derived — ADR-0079 §2.5 | Application (query double throws) | catch `EnvelopeNotFoundException` and mark the delivery `NOT_NEEDED` (inferred) |
| AC-27 | An occasion whose only delivery is `NOT_NEEDED` is neither delivered nor undeliverable | derived — ADR-0079 §2.5 | Unit | drop the explicit guard on `DeliveryPolicy::isDefeated(0, 0)` (inferred) |
| AC-28 | That occasion has forgotten its secrets | derived — ADR-0079 §2.5 | Unit | exclude `NOT_NEEDED` from the settled check (inferred) |
| AC-29 | `ANY` over `{SENT, NOT_NEEDED}` is delivered | derived — ADR-0079 §2.5 | Unit | count `NOT_NEEDED` in the total (inferred) |
| AC-30 | `ALL` over `{SENT, NOT_NEEDED}` is delivered | derived — ADR-0079 §2.5 | Unit | count `NOT_NEEDED` in the total; the `ALL` case must redden |
| AC-49 | Each multi-delivery policy over {permanent `FAILED`, `NOT_NEEDED`} is undeliverable (members AC-49a…b) | derived — ADR-0079 §2.5 | Unit | return "not decided" whenever a `NOT_NEEDED` is present |
| AC-31 | Each envelope end that cancels removes a recipient's pending invitation and leaves their pending ending notice (members AC-31a…b) | derived — ADR-0079 §2.5 | Application | cancel every pending delivery of the recipient, not the invitation family (inferred) |
| AC-32 | On `RecipientCorrected`, an occasion requested before the event is cancelled, in each subscriber order (members AC-32a…b) | derived — ADR-0079 §2.5 | Application | compare `requestedAt` with the wrong bound (inferred) |
| AC-33 | On `RecipientCorrected`, the correction's own new occasion (`requestedAt` equal to the event's `occurredAt`) is untouched, in each subscriber order (members AC-33a…b) | derived — ADR-0079 §2.5 | Application | cancel on `requestedAt <= occurredAt` (inferred) |
| AC-34 | A redelivery of the cancellation reactor changes nothing | derived — ADR-0079 §2.5 | Application | drop the "still `PENDING`" filter (inferred) |
| AC-35 | While the cancellation use case's transaction is open, a second session's probe reports the notification row locked | derived — ADR-0079 §2.5 | Integration (`#[SkipDatabaseRollback]` + `ProbesRowLocks`) | load with `find()` instead of `findLockedForUpdate()`; the probe must report unlocked |
| AC-36 | `send_before` round-trips through `DbalNotificationRepository` | derived — ADR-0079 §2.2 | Integration | drop the column from the mapping (inferred) |
| AC-37 | `failure_kind` round-trips through `DbalNotificationRepository` | derived — ADR-0079 §2.3 | Integration | drop the column from the mapping (inferred) |
| AC-38 | `NOT_NEEDED` round-trips through `DbalNotificationRepository` | derived — ADR-0079 §2.5 | Integration | drop the status from hydration (inferred) |
| AC-39 | A `FAILED` row seeded in the pre-migration shape is backfilled `PERMANENT` when the migration's backfill runs over it, and then hydrates as `PERMANENT` | derived — rule 6 | Integration (`#[SkipDatabaseRollback]`: the migration exposes its backfill as a public static, and the test drops the D1 CHECK in an owner transaction, seeds the row and runs it, as `EndingDataMigrationTest` does with `Version20260928131928::dataMapping()`; the CHECK refuses that row on the migrated schema) | revert the migration's backfill |
| AC-50 | Each half of the `failure_kind` CHECK refuses its row (members AC-50a…b) | derived — rule 6 | Integration | drop the CHECK from the migration |
| AC-40 | `IssueAuthChallengeUseCase` hands the delivery port a request whose `sendBefore` equals `requestedAt + 60 s` | derived — ADR-0079 §2.2 | Application | stop passing `nextIssuanceAllowedAt()` (inferred) |
| AC-41 | A request for an `AUTH_OTP_*` purpose without `sendBefore` is refused by the consumer | derived — ADR-0079 §2.2 | Application | make the consumer accept an absent `sendBefore` (inferred) |
| AC-46 | A delivery whose purpose has the `NOTICE` profile cannot carry a `send_before`: Notification refuses it where the delivery is created | derived — ADR-0079 §2.2 | Unit | drop the guard, so a `NOTICE` delivery accepts a `send_before` |

**Notes on AC-1…AC-5**
- The fixtures are ones where the same attempt count disagrees by message.
- The harness reaches the numbers, not the broker: `async_events` is `in-memory://` under test, so the delayed-queue behaviour is verified once on the dev stack (mail transport down, the async worker running, attempts at the stated gaps) <!-- OFFREPO: the worker is started by the `worker-up` target of the sibling repository f5sign-infra's Makefile, which runs the Messenger consumers (async worker, event relay, custodian) in their own containers; this repository has no Makefile. --> and the observation goes in this task's Status.

**Notes on AC-15**
- The synthesized event carries a `TenantStamp` and no ambient tenant, which is the condition that reproduces the unwound scope.

**Notes on AC-17**
- The delivery is `PENDING` in the failing fixture, so it is the window guard that fired, not the convergence guard above it.
- AC-16 is the control case for the same guard: the sabotage of AC-17 must leave AC-16 green.

**Notes on AC-21**
- AC-21a — `RECIPIENT_INVITATION` with the envelope closed. Sabotage: drop the envelope-closed check.
- AC-21b — `RECIPIENT_INVITATION` with the recipient's leg closed. Sabotage: drop the leg-open check.
- AC-21c — `RECIPIENT_INVITATION` to a destination no longer the current contact. Sabotage: drop the current-contact check.
- AC-21d — `RECIPIENT_INVITATION` requested before `invitationsRevokedAt`. Sabotage: drop the revocation check.
- AC-21e — `RECIPIENT_INVITATION_RESENT` with the envelope closed. Sabotage: drop the envelope-closed check.
- AC-21f — `RECIPIENT_INVITATION_RESENT` with the recipient's leg closed. Sabotage: drop the leg-open check.
- AC-21g — `RECIPIENT_INVITATION_RESENT` to a destination no longer the current contact. Sabotage: drop the current-contact check.
- AC-21h — `RECIPIENT_INVITATION_RESENT` requested before `invitationsRevokedAt`. Sabotage: drop the revocation check.
- AC-48 is the control case: every check passes and the invitation is sent.

**Notes on AC-22 and AC-47**
- The fixture where "closed" disagrees by purpose.
- Members of both (AC-22x and AC-47x share the letter), censused from `NotificationPurpose` on 2026-10-09: a `ENVELOPE_COMPLETED`, b `ENVELOPE_ENDED_SENDER_CANCELLED`, c `ENVELOPE_ENDED_SENDER_CANCELLED_WITH_REASON`, d `ENVELOPE_ENDED_DECLINED`, e `ENVELOPE_ENDED_TIME_RAN_OUT`, f `ENVELOPE_ENDED_OUT_OF_REACH`, g `SEALED_COPY_READY`. AC-24's census is what catches a purpose added later.

**Notes on AC-23**
- AC-23a — `AUTH_OTP_ACCESS`. AC-23b — `AUTH_OTP_SIGNING`. AC-23c — `AUTH_OTP_DECLINE`.

**Notes on AC-31**
- AC-31a — `EnvelopeVoided`. AC-31b — `EnvelopeCompleted`. The ends deliberately left to the send-time check are listed in §3.5.

**Notes on AC-32 and AC-33**
- AC-32a / AC-33a — the correction's re-invitation occasion (`NotifyCorrectedRecipientUseCase`) is created before the cancellation reactor runs. AC-32b / AC-33b — the cancellation reactor runs first. Both reactors subscribe to `RecipientCorrected`, so either order is possible.

**Notes on AC-49**
- AC-49a — `ANY`. AC-49b — `ALL`. `SINGLE` has one delivery and is AC-27's case.

**Notes on AC-50**
- AC-50a — a `FAILED` row with no `failure_kind`. AC-50b — a `PENDING`, `SENT` or `NOT_NEEDED` row carrying one.

**Notes on AC-35**
- A single DAMA connection cannot see this, which is why the probe is the only harness that reaches it.

- Tiers per [`tests/README.md`](../../tests/README.md). Run in the worktree lane
  (`make -C ../f5sign-infra wt-backend src=$(pwd)`), never the main-checkout targets. <!-- OFFREPO: the ephemeral per-worktree lane is a target of the sibling repository f5sign-infra's Makefile; it mounts the given tree into its own containers and runs this repo's own test suites there, so it validates this tree rather than the main checkout. -->
- **Gates:** full suite, Infection covered-MSI, PHPStan, deptrac and lint green in the worktree lane. Run
  `/doctrine-guard` (the migration writes rows the domain reads) and `/contract-check-backend` (the event
  payload widens).

## 7. Open follow-ups (track, don't solve here)

- **The signer is not told a code was not sent.** A new Notification → Session signal, ADR-level, plus a
  signer app change; the backlog already holds the row.
- **Receipts and late bounces** ([BL-390](../BACKLOG.md)): a message accepted and lost downstream still
  reads as `SENT`.
- **A sweep for deliveries lost by other means** (ADR-0079 §7.4): it races in-flight retries and needs
  the row lock this task's cancellation already takes.
- **The `failed` transport still receives the exhausted message.** Replaying it is safe (a settled
  delivery is a no-op) but it is operator noise; whether to drop it after the transient end is recorded
  wants a week of real traffic as evidence.
- **A per-method send window.** One 60-second interval covers every delivered method today
  (`DeliveredCodePolicy::nextIssuanceAllowedAt()` says so); the deadline moves with it if that changes.
- **No test pins the row lock in `RecordTransientDeliveryFailureUseCase` and `TransmitDeliveryUseCase`** ([BL-401](../BACKLOG.md)). Both load through `findLockedForUpdate`, but the fake lock is a plain `find`, so removing the lock stays green; only AC-35's cancellation has a `ProbesRowLocks` probe.
- **`delivery.failure_kind` has no value-set CHECK** ([BL-402](../BACKLOG.md)). Hydration is strict, so a bad value fails on read, not on write; the consistency rule of AC-50 (`FAILED` iff a kind) is enforced, the value set is not.
- **Confirm Monolog does not render DBAL bound parameters from the exhaustion listener's logged Throwable** ([BL-403](../BACKLOG.md)), found by the security audit; unverified, not shown to leak.
- **The RabbitMQ delay has not been observed** ([BL-404](../BACKLOG.md)): with the mail transport down and the async worker running on the dev stack, attempts at about 60, 300 and 900 s; the figures go in this Status. Post-merge.
- **Optional hardening** ([BL-405](../BACKLOG.md)): a second foreign message in the exhaustion listener's class-guard test (`any_other_message_is_not_its_business`), because removing the guard reds today as an `Error`, not as the assertion.

## 8. Deviations & honest notes

### Scope
- Comment-only files beyond the slice list, ratified in slice 14: the `Version20260723000001` docblock, `EnvelopeLockTimeoutException`, `SmsTransportException`, `ExecutedAuthMethod`, `DeliveryFailed`, `DeliveryTest`, ADR-0065, the `docs/adr/README.md` graph lines, `docs/ddd/README.md` and ADR-0079's Status text. Nothing else outside §4.

### Decisions made during implementation
- Under `ANY`, a `FAILED` delivery plus a `PENDING` one that becomes `NOT_NEEDED` leaves the occasion undeliverable with no `NotificationFailed` recorded: `NOT_NEEDED` records no fact. Accepted, because it only comes from a void, a correction, a completion or a stale contact, where telling Envelope of a failure would be wrong (slice 01).
- `markNotNeeded()` / `markFailedTransiently()` carry no `PENDING` guard; the use cases guard convergence first (slice 01).
- AC-33's inferred guard, `requestedAt <= occurredAt`, is **not** the realized one. `requested_at` is stored in whole seconds and `occurredAt` has sub-seconds, so a redelivered or reordered `RecipientCorrected` would have cancelled its own re-invitation. `CancelPendingInvitationsUseCase` compares `requestedBefore` to the second; storage is unchanged. Pinned by a use-case test, `CancelPendingInvitationsPrecisionTest` and an Acceptance case (correct-before-send plus redelivery). The AC-33 row is left as written (slice 13). Consequence: on a phone-only correction an older same-second EMAIL invitation is sent, which is harmless (the address is still right).
- AC-35's probe could not fail as planned (the `save()` upsert locks the row itself); it sits in a repository decorator before each `save()` and proves the locked re-read (slice 12). Extra test: a stale candidate sent before the locked re-read is left alone.
- The tenant comes from `TenantStamp` alone (ADR-0079 §2.4); the stampless branch logs at `error` and is unreachable today (slice 08).
- Slice 10: the constructor change broke three propagation tests; shape A ruled (a permissive `EnvelopeQueryInterface` double, assertions unchanged), copied into four files rather than a shared fake.
- Unreachable or equivalent: the empty-purposes guard is an equivalent mutant (PHPStan non-empty-list); `DeliveryRetryStrategy::requested()`'s `LogicException` narrowing is untested; dropping the CODE condition of the window guard stays green by design (a notice cannot carry a window); a `RecoverableExceptionInterface` thrown by a handler would bypass `isRetryable`, and none is thrown today.
- Deliveries whose subject is not an envelope or whose addressee is not a recipient are sent without the send-time check (none exist; all nine producers use envelope/recipient).
- The candidate query takes no tenant: RLS `FORCE` plus `current_tenant_id()` bounds it and fails closed; not EXPLAINed.

### Decisions that needed an ADR
- ADR-0079 (Proposed 2026-10-09). **Accepted (enforcement partial) by the owner on 2026-10-09**, on this proposal: move it to Accepted, because the §6 bars exercise it: `DeliveryRetryStrategy` and the retry-profile tests (AC-1..7), `TransmitDeliveryUseCase`'s window guard (AC-8..), `RecordTransientDeliveryFailureUseCase`, `CancelPendingInvitationsUseCase` with its `ProbesRowLocks` probe (AC-35) and the exhaustion listener. The one thing no harness reaches is the broker delay (BL-404), so `Accepted (enforcement partial)` is the honest form until it is observed.

### Declared and unproven properties
- Delayed redelivery at 60/300/900 s through RabbitMQ: `async_events` is `in-memory://` under test. Needs the dev-stack observation (BL-404).
- The row lock of `RecordTransientDeliveryFailureUseCase` and `TransmitDeliveryUseCase`: the single-connection DAMA harness cannot see it (BL-401).
- Infection: running (filtered to the diff, 85/70); its figures are added after the run.

### Debt left behind, and where it lives now
- Row-lock probe on the two use cases: §7, BL-401. `failure_kind` value-set CHECK: §7, BL-402. Monolog and bound parameters: §7, BL-403. RabbitMQ observation: §7, BL-404. Second foreign message in the listener test: §7, BL-405.
- The signer not told a code was not sent, receipts and late bounces (BL-390), the sweep for lost deliveries, the `failed` transport noise and a per-method send window were already in §7 and are unchanged.

### Delegated work
- 15 slices: 14 critical on opus, each reviewed by opus; slice 14 (prose sweep) standard on sonnet, reviewed by opus. Implementation rounds: 24 on opus, 2 on sonnet. Slice 10 used a `replicator` for the permissive double in three tests; the double was then copied into four files by hand. Slice 14 round 1 introduced a PHP parse error because lint could not run while another session held the lane; fixed in round 2 and the lane lint passed at the end.

### Cost of the run
- Slices, implementer tokens: opus 1,860,228 over 14 slices; sonnet 182,013 over 1 slice. Reviewer tokens recorded only for slices 01 and 02: 168,744.
- Rounds: 24 opus, 2 sonnet. Escalations: 1 (slice 10 first launch NEEDS_CONTEXT, 130,263 tokens, not in the totals above).
- Orchestrator, planner, gate-runner and Infection figures are not in `run.log`; Infection's duration is added by the orchestrator.

**Infection survivors on changed lines that no test kills** (each an equivalent mutant or a guard no public path reaches; the five on `EnvelopeLockTimeoutException.php:32` predate the branch, which changed only its docblock):

# Infection survivors justified (TASK-055, slice 16)

Paths under src/F5Sign/. Every other survivor on a changed line is killed by commit e440d32c.

- Notification/Application/UseCase/CancelPendingInvitationsUseCase.php:61 UnwrapArrayValues — equivalent mutant: the two invitation purposes (RECIPIENT_INVITATION, RECIPIENT_INVITATION_RESENT) are the first two cases of NotificationPurpose, so array_filter keeps keys 0 and 1 and its result is already a list; array_values changes nothing.
- Notification/Application/UseCase/CancelPendingInvitationsUseCase.php:66 ReturnRemoval — defensive guard unreachable through the public path: NotificationPurpose::isInvitation() is true for two cases, so $invitations is never empty.
- Notification/Application/UseCase/TransmitDeliveryUseCase.php:214 Break_ — equivalent mutant: recipient ids are unique on an envelope, so after the match no later candidate matches and continue leaves $recipient as break did.
- Notification/Application/UseCase/TransmitDeliveryUseCase.php:224 NullSafePropertyCall — defensive guard unreachable through the public path: Notification::request() throws DeliveryRequiresContactException for an EMAIL delivery with no contact, so the destination is never null on this arm. Were it null, the mutant would read null as well (with an E_WARNING) and compare the same.
- Notification/Application/UseCase/TransmitDeliveryUseCase.php:225 NullSafePropertyCall — same as :224, for SMS (DeliveryChannel::requiresContact() is true for SMS).
- Notification/Domain/Aggregate/Notification.php:394 DecrementInteger — equivalent mutant: with no needed delivery, the fall-through computes DeliveryPolicy::isSatisfied(0, 0), which is false for ANY (needs >= 1), ALL (needs total > 0) and SINGLE (needs total === 1), the same false the guard returns.
- Notification/Domain/Aggregate/Notification.php:395 ReturnRemoval — equivalent mutant, for the reason given at :394.
- Notification/Domain/Aggregate/Notification.php:457 UnwrapArrayValues — equivalent mutant: needed() is only ever passed to count() (in isDelivered() and isUndeliverable()), and the key order does not change the count.
- Notification/Domain/ValueObject/DeliveryStatus.php:71 DecrementInteger — equivalent mutant: progress() is read only by reaches(), which excludes FAILED through isFailure(). For NOT_NEEDED, -1 and -2 compare the same against every rung (PENDING 0, SENT 1, DELIVERED 2) and against NOT_NEEDED itself.
- Envelope/Infrastructure/Persistence/Doctrine/EnvelopeLockTimeoutException.php:32 Concat/ConcatOperandRemoval (x5, not on a changed line) — the only change this branch made to the file is a docblock line (d4f79f9a). The message survivors already existed before the branch and do not belong to it.
