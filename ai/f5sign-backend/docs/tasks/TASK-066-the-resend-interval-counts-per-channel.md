# TASK-066 — The resend interval counts per channel, not per recipient

<!-- OFFREPO: the incident in §1 was reported by the dashboard team's session on 2026-10-21, and the decisions marked "owner, 2026-10-21" were taken in the owner's working session that day. Every fact taken from them is restated here; nothing in this record depends on reading either. -->

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `feat/resend-interval-per-channel`** (last `src/` commit `b5b6447d`), 2026-10-21. Validated under the `wt-backend` lane of this worktree. First full run on `b5b6447d`: lint, Deptrac and PHPStan clean, 7802 tests, 10 errors, all `ENVELOPE_EXPIRED` from a fixture date bomb that was also red on `develop` (`76c70285`); it was fixed on `fix/fixture-expiry-date-bomb`, merged to `develop` as `5a6d8ea0`. Final full run after merging that `develop` (`bdf654d9`): lint, Deptrac and PHPStan clean, 7806 tests, 88843 assertions, 1 failure, the new fixed-date census naming this branch's own migration test; that test was classified (`e7998c43`, green under the +200-day probe) and the census re-ran green. Gates: contract-check pass, doctrine-guard pass, security-audit warn (0 blocking), task-validate pass; perf-smoke skipped (no `perf:seed` script). **Infection on the changed lines** (diff-filtered over the five changed `src/` files, `StorageLifecycleScenarioTest` excluded for BL-356 and the three date-bomb classes excluded): 133 changed lines, 0 not covered, 6 escaped. One was a real gap (`Recipient` keeping the latest refusing deadline when the channel checked last refuses earlier), killed by `66c1ef1d` and checked by sabotage. Two are equivalent (`'+' . 60 . ' seconds'` without the `+`; `>` against `>=` on equal deadlines). Three are in the `resentTooRecently()` message text, which no test pins. Whole-file covered-MSI is 78.77% (MSI 70%), below 85% because of code this branch does not change: 233 of the 239 escaped mutants are on unchanged lines. The deferrals are in §6. |
| **Type** | **Forward build** in Envelope: the minimum interval between resends is kept per notification channel instead of once per recipient. One migration. No new route, key or HTTP code. |
| **Why** | A recipient declared `[EMAIL, SMS]` under `IN_ORDER` gets an unnamed resend by email only. To reach them on both, the sender names `EMAIL` and then `SMS`, and the second call is refused `RECIPIENT_RESENT_TOO_RECENTLY` because the 60-second interval is one clock per recipient. The interval exists so that a retry loop cannot flood one mailbox or one phone, and a resend on the other channel floods neither. |
| **Builds on** | [TASK-041](TASK-041-resending-a-signing-invitation.md) (the resend route and the interval, §5 D5), [TASK-060](TASK-060-a-resend-may-name-one-declared-channel.md) (a resend may name one declared channel) and [ADR-0080](../adr/ADR-0080-a-resend-may-name-one-declared-channel.md) (the guard order of §2.2 and the "may go out by SMS" rule of §2.6), all reused unchanged. |
| **Scope** | The interval only. The SMS cap (`MAX_SMS_RESENDS`, ADR-0080 §2.6), the resend ordinal and the operator's grant do not change. |
| **Decision record** | **No ADR yet.** The interval was decided in TASK-041 §5 D5, a task record, and no ADR states it; ADR-0080 §2.2 names only its place in the guard order, which this task keeps. What would force one: changing the guard order, the cap, or letting a resend name more than one channel. |

---

## 1. Why this task exists

<!-- OFFREPO: the dashboard is another repository; the only facts taken from it are the calls it made and the answers it got, both restated below. -->
Since 2026-10-20 the dashboard declares recipients who have an email and a phone as
`notification_channels: ["EMAIL", "SMS"]` with `IN_ORDER`, because `ALL_AT_ONCE` doubled every invitation and
every closing notice. The operator still wants to "resend by email and by SMS". An unnamed
`POST …/recipients/{recipientId}/resends` under `IN_ORDER` goes out by email only. On 2026-10-21 the dashboard
sent `{"channel": "EMAIL"}` and then `{"channel": "SMS"}`; the second was refused with
`409 RECIPIENT_RESENT_TOO_RECENTLY` and a `next_resend_at` one minute later.

The owner chose (2026-10-21) to keep the interval per channel rather than to let one resend name several
channels: the contract does not change and the two calls the dashboard already makes start working.

## 2. What already exists (reuse, do not rebuild)

- **The route.** `ResendInvitationController` (`POST …/recipients/{recipientId}/resends`, machine key, 204)
  takes `ResendInvitationRequest` with one nullable key, `channel` (`EMAIL` or `SMS`). Its 409 codes include
  `RECIPIENT_RESENT_TOO_RECENTLY`, the only one that carries `next_resend_at` and the only one that waiting
  resolves. Its operation description says the resend is refused "inside a short minimum interval since the
  last resend to the same recipient".
- **The use case.** `ResendRecipientInvitationUseCase` loads the envelope with `findLockedForUpdate`, checks the
  expiry, finds the recipient, resolves the channels and calls `Envelope::resendInvitation()`, then
  `saveLifecycle()`.
- **The aggregate.** `Envelope::resendInvitation()` runs the envelope-level refusals (closed, unclaimed slot,
  delegated, notified by the integrator, a named channel not declared or not reachable, no reachable channel,
  step not active), then `Recipient::resendInvitation()`, then records `RecipientInvitationResent`.
- **The entity.** `Recipient::resendInvitation()` refuses a closed leg, then the SMS cap
  (`mayGoOutBySms()` and `smsResendsMade >= MAX_SMS_RESENDS + resendAllowance`), then the interval:
  `lastResentAt !== null` and fewer than `MIN_RESEND_INTERVAL_SECONDS` (60) whole seconds since it, compared with
  `<`, so a resend exactly on the boundary is admitted. Then it increments `resendsMade`, increments
  `smsResendsMade` when `mayGoOutBySms()`, and sets `lastResentAt`. It is the only writer of `lastResentAt`.
- **"May go out by SMS".** `Recipient::mayGoOutBySms()` is true when the resend names `SMS`, or names nothing
  and the recipient's **declared** channels include `SMS`. It reads the declaration, not today's reach.
- **The refusal.** `RecipientNotResendableException::resentTooRecently()` carries `nextResendAt`
  (`lastResentAt` plus the interval), published as `next_resend_at` (RFC 3339).
- **Persistence.** `envelope.recipient.last_resent_at` (`TIMESTAMPTZ NULL`), added by
  `Version20260831000002` beside `resends_made`; read and written by `DbalEnvelopeRepository`
  (`loadRecipients`, `upsertRecipient`). Nothing outside `Recipient` and the repository reads it: no read
  model, no `GET` field, no trail field.
- **The event and the occasion.** `RecipientInvitationResent` carries `envelope_id`, `recipient_id`,
  `step_ordinal`, `resend_ordinal`, `channel`, `occurred_at`. Notification keys its occasion on
  `…|resend:<ordinal>`. Neither depends on the interval.
- **Tests beside it.** `EnvelopeInvitationResendTest` (the 30 s, 59 s and 60 s cases and the deadline),
  `EnvelopeResendCapTest` (the cap asked before the interval), `EnvelopeNamedChannelResendTest` (a refused
  named resend leaves `lastResentAt` unchanged), `ResendRecipientInvitationUseCaseTest`,
  `RecipientInvitationResendHttpTest` (an immediate second POST is 409; `backdateLastResend` moves the stamp
  by SQL), `ResendOnANamedChannelHttpTest`, `RecipientInvitationResendPersistenceTest`. The row-lock probe
  `ProbesRowLocks` exists and `ChannelChangeRowLockTest` uses it.

## 3. Scope

In:

- One interval stamp per channel (`EMAIL`, `SMS`) on the recipient, replacing `last_resent_at`.
- A named resend is checked against, and stamps, its channel only.
- An unnamed resend is checked against, and stamps, every channel it may go out on.
- `next_resend_at` from the stamp or stamps that refused.
- The migration, the repository, the route's `#[OA\*]` prose, the `Recipient` docblocks, a frontend handoff.

Out:

- The interval's value (60 s) and the SMS cap.
- A resend naming several channels (owner, 2026-10-21: refused in favour of this).
- Corrections and the channel change: they do not stamp the interval today and still do not.

Concepts re-cut: `lastResentAt`, `last_resent_at`, `MIN_RESEND_INTERVAL_SECONDS`, `resentTooRecently`,
`nextResendAt`, "since the last resend to the same recipient", "one went out inside the minimum interval".

## 4. Key decisions

1. **The clock is per channel** (owner, 2026-10-21).
2. **An unnamed resend may go out on every declared channel that resolves now** (the reach the aggregate
   already receives): under `IN_ORDER` the next channel is the fallback, under `ALL_AT_ONCE` all go at once.
   So it is refused while **any** of those channels is inside its interval, and when admitted it stamps them
   all. Counting only the head channel would let the fallback SMS go out inside its interval. ⚑ The set is
   the **reach, not the declaration**, unlike `Recipient::mayGoOutBySms()`, which the SMS cap counts by
   declaration (ADR-0080 §2.6; that difference is BL-429's). A declared channel that cannot resolve cannot
   flood anyone, so it gets no stamp and refuses nothing. Accepted consequence: under `IN_ORDER` "unnamed,
   then `SMS`" is refused although only the email went out (AC-2a).
3. **The migration is conservative**: every channel inherits the recipient's current stamp, so no resend is
   admitted earlier after the deploy than it would have been before it.

## 5. Verification

| Id | Criterion (an observable behaviour) | Origin | Tier / harness | Sabotage |
|---|---|---|---|---|
| S-1 | The incident replayed over HTTP: a recipient `["EMAIL", "SMS"]` `IN_ORDER`; `{"channel": "EMAIL"}` → 204, then at once `{"channel": "SMS"}` → 204, and both deliveries are requested | owner | Acceptance | the code before this task |
| AC-1 | The same channel twice inside the interval is refused `RECIPIENT_RESENT_TOO_RECENTLY` (members AC-1a…b) | owner | Unit + Acceptance | stamp per recipient |
| AC-2 | An unnamed resend is refused while any declared channel that resolves now is inside its interval, and stamps every one of them (members AC-2a…e) | derived — docs/adr/ADR-0080-a-resend-may-name-one-declared-channel.md | Unit | stamp only the head channel |
| AC-3 | `next_resend_at` names when the refused resend becomes admissible: a named resend's channel deadline; for an unnamed one, the latest of its channels' deadlines | derived — tests/F5Sign/Envelope/Unit/Domain/Aggregate/EnvelopeInvitationResendTest.php | Unit + Acceptance | return the earliest deadline |
| AC-4 | The boundary holds per channel: 59 s refused, 60 s admitted | derived — tests/F5Sign/Envelope/Unit/Domain/Aggregate/EnvelopeInvitationResendTest.php | Unit | compare with `<=` |
| AC-5 | The guard order is unchanged (the SMS cap before the interval), and a refused resend writes no stamp, no counter and no event | derived — docs/adr/ADR-0080-a-resend-may-name-one-declared-channel.md | Unit | stamp before the interval check |
| AC-6 | The migration gives each channel the recipient's current stamp; a null stamp stays null on every channel; `down()` restores `last_resent_at` as the latest channel stamp (members AC-6a…c) | derived — rule 6 | Integration (migration test) | backfill only the email stamp |
| AC-7 | The per-channel stamps round-trip through the repository | derived — tests/F5Sign/Envelope/Integration/RecipientInvitationResendPersistenceTest.php | Integration | write one stamp to both columns |
| AC-8 | Two concurrent resends on the same channel: one is admitted, the other refused | derived — rule 4 | Integration with `ProbesRowLocks` (second connection) | read the recipient outside the lock |
| AC-9 | Regression: the resend ordinal, the SMS cap's count, the `RecipientInvitationResent` payload and the notification occasion are unchanged | derived — tests/F5Sign/Envelope/Unit/Domain/Aggregate/EnvelopeResendCapTest.php | existing suites | — |
| AC-10 | The route's `#[OA\*]` strings say the interval is per channel and what `next_resend_at` names; the `Recipient` docblocks match; a frontend handoff for the dashboard | derived — rule 1 | review + `OpenApiSpecTest` | — |

<!-- OFFREPO: the `wt-backend` lane is a target of the f5sign-infra Makefile; its one relevant fact is restated in the line below. -->
- **Gates:** suite, PHPStan, deptrac and lint, under the `wt-backend` lane: an ephemeral stack (its own PHP
  container, Postgres cluster and broker) that mounts this worktree's tree rather than the main checkout's.
- **Reproduction first.** S-1 is written and run red against the unchanged `src/` (409 on the second call)
  before the fix; the literal failure goes in the slice report.

**Notes on AC-1**
- AC-1a — `EMAIL` then `EMAIL` at +30 s → refused.
- AC-1b — `SMS` then `SMS` at +30 s → refused, and the SMS cap's count is not incremented by the refusal.

**Notes on AC-2**
- AC-2a — `["EMAIL", "SMS"]`: unnamed, then `SMS` at once → refused.
- AC-2b — `["EMAIL", "SMS"]`: `EMAIL`, then unnamed at once → refused.
- AC-2c — `["EMAIL"]`: unnamed stamps `EMAIL` only, so a later change of the declaration to add `SMS` leaves an
  immediate named `SMS` resend admissible.
- AC-2d — `["EMAIL", "SMS"]` `ALL_AT_ONCE`: unnamed stamps both.
- AC-2e — `["EMAIL", "SMS"]` with SMS not resolving (the tenant has SMS off, or the phone takes no SMS):
  unnamed stamps `EMAIL` only. Sabotage: stamp from the declaration.

**Notes on AC-10** — the surfaces that carry the per-recipient wording or the column, every one in the sweep:
- the route's `#[OA\*]` operation and 409 descriptions; `RecipientNotResendableException::resentTooRecently()`
  and the `Recipient` docblocks (`MIN_RESEND_INTERVAL_SECONDS`, `MAX_SMS_RESENDS`, `resendInvitation()`);
- `docs/ddd/envelope-domain-model.md` (the `Recipient` row and the invariant on the stored `lastResentAt`) and
  `docs/LIVE_SCHEMA.md`;
- the tests that read `lastResentAt` or `last_resent_at`: `RecipientInvitationResendHttpTest`
  (`backdateLastResend`), `RecipientInvitationResendPersistenceTest`, `EnvelopeResendCapTest`,
  `EnvelopeNamedChannelResendTest`, `ResendRecipientInvitationUseCaseTest`, `EnvelopeInvitationResendTest`.

**Notes on AC-6**
- AC-6a — a recipient with `last_resent_at` set → both channel stamps equal it.
- AC-6b — `last_resent_at` null → both null.
- AC-6c — `down()` after two different channel stamps → `last_resent_at` is the later one.

## 6. Open follow-ups (track, don't solve here)

- **A resend naming several channels** was the dashboard's first proposal; refused for now (§4 #1). It would
  amend ADR-0080 §2.1.
- **Two resends a minute to one person** (one per channel) is the new ceiling. Bounded in money by the SMS cap;
  if it reads as harassment in practice, the trigger is a complaint, and the repair is the interval's value,
  not its scope.
- **The resend abuse bound is per recipient and channel only** ([BL-442](../BACKLOG.md)): no per-envelope or
  per-tenant aggregate caps resends. It predates this task; the security audit flagged it.
- **The Acceptance test for AC-3 cannot tell the latest deadline from the earliest** ([BL-443](../BACKLOG.md)); the
  Unit test does.
- **The migration docblock overstated "never resent, NULL"** for a recipient resent and only later delegated
  ([BL-444](../BACKLOG.md), closed on this branch: the docblock was corrected before the merge).

## 7. Deviations & honest notes

### Scope
- None beyond the record's §3. Docblock-only edits in `Envelope.php` and in the unpublished migration's class
  docblock (SQL unchanged) were authorised during slice 04.

### Decisions made during implementation
- The empty-set guard in the per-channel check is typed `non-empty-list<NotificationChannel>` instead of a
  `LogicException`, which `NoGenericDomainExceptionRule` forbids; the no-reachable-channel refusal is written as
  `$reach->channels === []` in the unnamed branch (same refusals, codes and order for every input).
- The stamp set is the channels a resend may go out on (reach), not the declaration (plan D3, conservative: at most
  60 s after deploy a resend on the other channel is still refused, never admitted earlier than before).
- A true concurrent race on the resend row is accepted as unreachable from one PHP process (plan D8); the lock is
  proven by a second-session probe instead.

### Decisions that needed an ADR
- None.

### Declared and unproven properties
- AC-8 (concurrent resends): proven as a lock held against a second session plus a sequential committed refusal,
  not as a race.
- The migration lies outside Infection's source: `ResendIntervalPerChannelMigrationTest` is its only guard.
- AC-9 (regression of the existing suites) and AC-10c to AC-10h (docblocks, living docs, handoff, sweep) are review
  criteria with no `@criterion` citation by design.

### Debt left behind, and where it lives now
- Resend abuse aggregate: BL-442. AC-3 Acceptance test: BL-443. Migration docblock wording: BL-444 (closed on this branch).
- Several channels in one resend and the two-resends-a-minute ceiling: §6 of this record.
- The loose wording of the `resentTooRecently()` refusal message when the refusing stamp came from an unsent
  fall-back channel: not an `#[OA]` string and unpinned; left as is (slice 04 review).
- `BL-429` (an unnamed resend classified from the declaration at resend time) was reworded to state its real bound
  under per-channel stamps; it stays open.

### Delegated work
- Slices 01, 02, 03 (critical) and 04 (standard, escalated sonnet to opus after two prose rounds): opus, 1 to 3
  rounds; slice 05 (mechanical, the dashboard handoff): sonnet, 1 round. No `replicator` delegation in any slice.
  Slice 01 had no red-first on the guards (the lane applied the generated migration at once); each guard was proven
  by its own sabotage instead.

### Cost of the run
- Slice tokens: 01 145525, 02 167754, 03 94140, 04 321472, 05 78481 (about 807k). Closing review: approve, no
  findings, seven low-confidence notes. Subagent totals: opus implementers about 511k (01, 02, 03 and slice 04's escalated round), sonnet implementers about 297k (04's first two rounds and 05); opus reviews about 754k (every slice review except 05, plus the closing review), sonnet review 80k (05); plan 231k; spec-lint and claims 162k; gates, Infection (three attempts), docs-sync, task-close and suites about 751k. Total about 2.79M, not counting the orchestrator or the separate date-bomb fix.
