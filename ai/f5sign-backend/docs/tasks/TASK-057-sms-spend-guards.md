# TASK-057 — SMS spend is bounded where a person can run it up, and nothing cuts a live flow off

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `feat/sms-spend-guards`**, merged with develop (TASK-058) in `242f9a64`, 2026-10-19. Last full suite on the merged tree **`bba6a384`: 7462 tests / 83311 assertions**, lint, deptrac and PHPStan green, under the `wt-backend` lane of this worktree; the one commit after it, `9b564625`, adds a test (its class green, lint and PHPStan green on the tip). Infection judged on changed lines: 6 escaped, all justified as equivalent (§8). The channel-change re-invite is not capped here (§7, BL-413), and the provider-side hard cap remains a production prerequisite. |
| **Type** | **Forward build** across Envelope (a resend cap, an allowance, an unblock command), Session (the OTP destination limiter's key, a limiter-clearing command), Notification (a per-tenant volume report) and Foundation (an operator issuer). |
| **Why** | SMS is the first transport that spends money per message, and four things bound it badly. The invitation resend has only a 60-second interval and no count (`Recipient::resendsMade` is monotonic and unbounded). The OTP destination limiter is keyed on the phone alone (`OtpSendKeys::of()` hashes `sha256(destination)`), so `otp_sms_destination` (5 per hour) is shared across every session, envelope and tenant: a warehouse or traffic-desk phone signing several waybills in an hour is locked out at the sixth code. Nothing lets an operator lift either block. Nothing counts what a tenant sends, so a runaway loop is invisible until the invoice ([BL-166](../BACKLOG.md)). |
| **Decision record** | [ADR-0077](../adr/ADR-0077-a-recipient-declares-the-channels-that-reach-them.md) §2.10. The ADR is **Accepted** (owner, 2026-10-19): TASK-031 realized §2.1–§2.9 and this task §2.10. It read *Accepted (enforcement partial)* from 2026-10-14 until this task landed §2.10. Adding an issuer prefix to `Foundation/Actor`/`Identity` and a limiter key to a Session port are structural (the repo's rule 7): the owner gave the go-ahead for both on 2026-10-09, so the implementer does not re-ask. ADR-0077 §2.10 records the operator actor; the limiter key and its ceilings are decided here (§5, D-c2, D-e), since §2.10 leaves "the key or the ceiling" to this task. |
| **Builds on** | [TASK-031](TASK-031-channel-selection-beyond-email.md) (the recipient's `notification_channels`, which is what makes "the list includes SMS" a property of the row), [TASK-022](TASK-022-delivered-codes-over-email.md) §2 and [ADR-0014](../adr/ADR-0014-idempotency-three-layer.md) (the OTP send limiter this re-cuts, and the fail-open choice both cite), [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.8 (the sender-side auth unlock, `RecipientAuthUnlocked`, which is **not** this). |

---

## 1. Why this task exists

The deployment this is built for is **on-premise for a single client** (Factor5), who pays for every message. So this
is not billing and not tenant metering: it is a runaway guard and a way for an operator to rescue a person the
guards stranded. Two principles come from the owner and bind every choice below:

- **Nothing cuts a live flow off at a spend ceiling.** An invitation or a code stopped mid-flow stalls an envelope
  someone is waiting on, which is worse than the spend it saves (ADR-0077 §7.8). The volume alert therefore never
  blocks.
- **The hard cap lives outside the code**: provider usage triggers, a prepaid balance without auto-recharge and
  geo permissions. They are a production prerequisite, listed in §7, and are not built here.

## 2. What already exists (reuse, do not rebuild)

Checked against the tree on 2026-10-09.

- **The resend.** `Recipient::resendInvitation()` refuses inside `MIN_RESEND_INTERVAL_SECONDS` (60), increments
  `resendsMade` and stamps `lastResentAt`; `resends_made` has a `CHECK >= 0` and the accessor documents the count
  as monotonic. The route is `POST /api/v1/envelopes/{id}/recipients/{recipientId}/resends`
  (`ResendRecipientInvitationUseCase`), and `RecipientInvitationResent` is the Envelope event.
- **The OTP limiter.** `Session\Application\Port\OtpSendLimiter::consume(OtpSendKeys, DeliveryMedium, now)`;
  adapter `FailOpenOtpSendLimiter` holds one `RateLimiterFactoryInterface` per policy and fails open (logging at
  `error`; that log line is the control). `config/packages/rate_limiter.yaml` defines per medium a session (SMS 3/h),
  destination (SMS 5/h) and source (SMS 10/h) policy and a machine source policy keyed on the API client (SMS
  100/h). **Every key is a digest**: `OtpSendKeys` has a private constructor and hashes the session id, the
  lower-cased destination and the source address (or `'unattributed'`); the machine arm hashes the API client id.
  The numbers are estimates (no SMS has ever left the system, [BL-169](../BACKLOG.md)).
- **No count of what is sent exists anywhere.** `notification.notification` carries `tenant_id`, `purpose`,
  `requested_at`; `notification.notification_delivery` carries `channel`, `status` and no timestamp of its own.
- **Reports on the custodian.** `app:storage:report-overdue` and siblings (`Storage/Infrastructure/Console`),
  `app:envelope:report-pending-seals --fail-over-hours=2`, scheduled by `Foundation/Custodian/CustodianSchedule`
  (`CustodianScheduleCensusTest` iterates the closed list). The cross-tenant read goes through a `SECURITY DEFINER`
  funnel (`Version20260908000003`, `DbalTenantsWithOverdueCustodies`), because the custodian has no tenant scope
  and the tables are `FORCE ROW LEVEL SECURITY`.
- **Actors.** `SystemActorId` has the factories `eventSubscriber`, `scheduler`, `bootstrap`, `boundedContext` and
  the `recipient` prefix; `fromString()` accepts five prefixes. `bootstrap()` is documented as the issuer of
  commands that run *outside* any tenant (its log row has `tenant_id` NULL) and is what `ProvisionTenantCommand` and
  `ProvisionApiClientCommand` use. `ActorKind` is a closed enum (`USER`, `SYSTEM`, `RECIPIENT`, `ANONYMOUS`,
  `MACHINE`) pinned by `ActorKindTest`, and `platform.event_log.actor_kind` is a `TEXT` column. **There is no operator
  actor**, though `bootstrap` is the nearest thing.
- **Session lookup.** `SigningSessionRepository::findByRecipient(EnvelopeRef, RecipientRef)` returns the recipient's
  session, so a command can derive the session key.

## 3. What gets built

**3.1 The resend cap.** When the recipient's `notification_channels` (TASK-031) include `SMS`, `Recipient` refuses a
resend once `resendsMade` has reached the cap (**5**, decided by the owner on 2026-10-09; a constant beside `MIN_RESEND_INTERVAL_SECONDS`),
with its own refusal code (not the interval's, so a client can tell "wait a minute" from "ask an operator"), on top
of the 60-second interval. A recipient whose channels are `["EMAIL"]` or `[]` is not capped: an email costs
nothing. The cap belongs in the aggregate because it is a rule about the row; the only Application input is none,
since the list is on the recipient. `#[OA\*]` on the resend route lists the new `409`/`422` and the handoff says so.

**3.2 The allowance, and the unblock command for resends** (decision D-c, §5). `app:envelope:unblock-resends
--tenant=<id> --envelope=<id> --recipient=<id> --operator=<label> [--grant=<n>]` enters the tenant's scope the
way the existing tenant-scoped commands do (a required `--tenant` option, as on `ReconcileEndingsCommand`, then `TenantContext::withScope` around
`ConnectionTenantScope::within`, as that command does, since a console has no
tenant and the tables are `FORCE ROW LEVEL SECURITY`), loads the envelope through the repository's
locked path, grants the recipient a further allowance, and records an Envelope event
(`RecipientResendsUnblocked`: who, when, how many) in the same unit of work. It does not reset `resendsMade`.

**3.3 The OTP destination limiter is re-cut** (decision D-e, §5). Two destination counters instead of one: a
**narrow** one keyed on the destination **and the envelope**, and a **wide** one keyed on the destination alone with
a much higher ceiling, so one warehouse phone signing five waybills an hour no longer shares five codes with
itself, while a sender who authors a hundred envelopes against one victim phone still hits a bound.

**3.4 The OTP unblock command.** `app:session:clear-otp-limits --tenant=<id> --envelope=<id> --recipient=<id> --operator=<label>`
enters the tenant's scope as §3.2 does, derives the recipient's session id (`findByRecipient`) and the destination of
each declared delivered-code method (the same `destinationFor($method)` read that `IssueAuthChallengeUseCase` makes),
builds the keys through `OtpSendKeys::of()` with the envelope id it was given (the narrow key of §3.3 needs it, so
both factories, `of()` and `ofMachine()`, gain an envelope parameter, and their one call site in
`IssueAuthChallengeUseCase` passes it; a machine-driven send gets the narrow counter too), and clears the session counter and the destination
counters through a new method on the `OtpSendLimiter` port (`LimiterInterface::reset()` on the same keys), then
records a Session event. ⚠ **The source-address counter cannot be cleared**: its key is a digest of the request's
address, which no operator can re-derive, and the port's docblock insists nobody treats it as an identity. The
command says so in its output, and the machine counter is cleared by `--api-client=<id>` only when that is passed.
This is a limitation to state, not to engineer around.

**3.5 The per-tenant SMS volume alert, which never blocks** (decision D-d, §5). A custodian-scheduled report
`app:notification:report-sms-volume --warn-over=<n>` counts, per tenant, the SMS deliveries requested in the last
hour and logs at `error` for each tenant above the threshold, exiting non-zero so the custodian's run record keeps
the output. It changes no state and no send path.

## 4. Scope

**In scope:** §3.1–§3.5, and a frontend handoff in `docs/frontend-handoff/` for the new resend refusal code (the
dashboard's resend button must explain it) — a deliverable of this task, not written with this record.

**Out of scope:** the SMS provider's usage triggers, a prepaid balance without auto-recharge, geo permissions, the approved
sender ID and the provider agreement (ops; production prerequisites). A money budget per tenant ([BL-166](../BACKLOG.md)).
The sender-side auth-lockout unlock (`RecipientAuthUnlocked`) is an existing, different mechanism. Cutting any
send off at a ceiling is **rejected**, not deferred. Tightening the machine-source limits, which are a safety valve
(`otp_machine_*` comments in `rate_limiter.yaml`).
**Re-arguing fail-open for SMS** is not done here: [ADR-0014](../adr/ADR-0014-idempotency-three-layer.md) records that the fail-open choice
was argued for email and "does not generalize to a spend ceiling on a billable effect". The code fails open today for both
media and the new counters inherit that, so the volume alert of §3.5 is what makes an unmetered window visible; whether SMS
should fail closed is a decision for the owner, noted in §7.

**Concepts re-cut:** the OTP destination limiter (`OtpSendKeys::of()` destination key, the `otp_*_destination` policies), the resend bound (`MIN_RESEND_INTERVAL_SECONDS` as its only limit; `resendsMade`), `SystemActorId::fromString()` prefixes, `ActorKind::fromIssuer()`.

## 5. Key decisions (made here, with options)

**D-c — what an unblock does to `resendsMade`.**

| Option | Effect | Cost |
|---|---|---|
| A. Reset `resendsMade` to 0 | The cap is a plain comparison; one column | Destroys the count, which the accessor documents as monotonic evidence; the `CHECK >= 0` and every reader that treats it as history is now lying; repeated unblocks are invisible in the row |
| B. **Grant an allowance** (a new `resend_allowance` integer column, cap = base + allowance) | Keeps the count; each grant is cumulative and is also an event | One migration and one more field on `Recipient` |

**Decided by the owner on 2026-10-09: B.** The count is evidence and the grant is a decision; they should not share a column. Migration
rule: `resend_allowance INTEGER NOT NULL DEFAULT 0 CHECK (resend_allowance >= 0)`; a backfilled row of every state
(draft, sent, terminal) means "no grant made", which is true. (A default is right here, unlike TASK-031's field: `0`
is the real neutral value.)

**D-c2 — the operator actor.** Options: (1) reuse `SystemActorId::bootstrap('unblock-resends')`, whose docblock
reserves it for commands outside any tenant and whose log rows carry `tenant_id` NULL, so an unblock inside a
tenant would be mis-scoped or mislabelled; (2) a new `SystemActorId::operator(string $label)` factory with prefix
`operator:`, added to `fromString()`'s prefix list, mapped by `ActorKind::fromIssuer()` onto `SYSTEM` (no change to
the closed enum and no DB change, since the column is `TEXT`); (3) a new `ActorKind::OPERATOR` (a change to a
published audit vocabulary, `ActorKindTest`, and every consumer of the kind). **Decided by the owner on 2026-10-09: (2)**, recorded in ADR-0077 §2.10, with the
label a required `--operator=` option. Honest limit stated in the command's docblock: a console has no
authenticated identity, so the label is *asserted*, not proven; the fact still records who claimed to act and when.
It touches `Foundation`; the owner gave the go-ahead on 2026-10-09 and ADR-0077 §2.10 records it (repo rule 7).

**D-d — how the volume alert counts.**

| Option | Cost |
|---|---|
| A. A Redis counter incremented on the send path | Adds work and a failure mode to the hot path of every SMS; a counter in a store "nobody treats as a datastore" is disposable evidence |
| B. **An hourly custodian report** over `notification.notification` joined to `notification_delivery` (`channel = 'SMS'`, status not `PENDING`/`NOT_NEEDED` (so `SENT`, `DELIVERED` and `FAILED` count), `requested_at` in the last hour, grouped by tenant) | Durable, off the hot path, same shape as `app:storage:report-*`; reads rows the system already keeps; cadence-late by up to an hour |

**Decided by the owner on 2026-10-09: B.** Implementation facts: the custodian has no tenant scope and the tables are `FORCE ROW LEVEL
SECURITY`, so the count goes through a `SECURITY DEFINER` function in the style of `Version20260908000003`
(returning `tenant_id, sms_count` only, no destinations, and naming every column it reads, never `SELECT *`, because
TASK-058 adds columns to `notification_delivery` on a parallel branch), called from a Notification `Infrastructure` read adapter;
the job is added to `CustodianSchedule::jobs()` and to the predicate `CustodianScheduleCensusTest` iterates. It counts
by the occasion's `requested_at`, not a per-delivery time, so it does not wait for TASK-058's timestamps; an
`IN_ORDER` fallback requested minutes later is counted in the earlier hour, an error well inside what a runaway
guard needs. The default threshold is a deployment parameter, starting at **1,000 SMS per tenant per hour** (2026-10-09):
ten times the expected peak, the way `otp_machine_*` is sized. The peak was measured on the client's own
waybill volume from 2026-10-05, when it went into daily use: about 200 waybills a day, at most 30 in one hour,
and about 3 SMS per waybill from the sent envelopes' mix (2.4 signers each, 38% with SMS declared), so about 90
SMS an hour at peak. Revisited against real traffic, not a complaint.
<!-- OFFREPO: the client's waybill volume of 2026-10-05, measured outside this repo; the figures are restated above and nothing here depends on reading the source. -->
`FAILED` is counted: a provider may bill a message it then reports as failed, and a loop of failures is still a
runaway, so a guard that over-counts errs towards the alert, which is the side §1 asks for. Only the two statuses
that never reach a provider are left out.

**D-e — the destination limiter's key and ceiling.** Options: (1) key on destination + envelope only (drops the
cross-envelope bound: an authoring-side abuse could fan out over envelopes); (2) key on destination + tenant (a
carrier-tenant's warehouse still shares one bucket across all its waybills, which is the case that failed); (3) raise
the one ceiling (a higher number for everyone, which loosens the bound on a person who is not the warehouse);
(4) **two counters**, narrow (destination + envelope, at today's destination ceiling per medium, unchanged: **SMS 5/h**, **email 10/h**) and wide (destination alone, **30/h**, an
estimate in the same spirit as the rest, a safety valve for the cross-envelope case, the same number for both media). **Decided by the owner on 2026-10-09: (4)**, for
both mediums since `OtpSendKeys::of()` serves both and a shared mailbox signing many waybills fails the same way.
`consume()` spends the counters in a fixed order, session, narrow destination, wide destination, then source,
so the narrow one refuses before the wide one can; it spends all of them as today (fail-open stays; the `error` log stays), `OtpSendKeys`
gains one digest member, and `rate_limiter.yaml` carries a narrow and a wide destination policy per medium (one of them replacing today's
`otp_*_destination`), with comments saying what each bounds. The wide number is an estimate and the file says so.

## 6. Acceptance bars

| Id | Criterion (an observable behaviour) | Origin | Tier / harness | Sabotage |
|---|---|---|---|---|
| AC-1 | Each channel list classifies the sixth resend correctly: refused with the cap's own code when it includes `SMS`, allowed when it does not (members AC-1a…c) | derived — ADR-0077 §2.10 | Unit (aggregate), `Clock` test double | ignore the channel list in `Recipient` |
| AC-2 | A grant of 3 leaves `resendsMade` unchanged, three more resends succeed and the fourth is refused | derived — ADR-0077 §2.10 | Unit (inferred) | implement the grant as a reset |
| AC-3 | The grant persists, and a negative allowance is refused by the database | derived — rule 6 | Integration (real SQL, `CHECK`s) | drop the `resend_allowance >= 0` check (inferred) |
| AC-4 | The grant and `RecipientResendsUnblocked` commit together: a failed event append rolls the grant back | derived — ADR-0077 §2.10 | Integration | append the event outside the unit of work (inferred) |
| AC-5 | `RecipientResendsUnblocked`'s payload is the closed key set operator, grant, instant and ids, with no destination | derived — rule 5 (closed key set) | Unit (inferred) | add a key to the payload |
| AC-23 | Two grants accumulate: grants of 2 and 2 allow four more resends, and the fifth is refused | derived — ADR-0077 §2.10 | Unit | let a grant replace the previous allowance |
| AC-6 | Each medium sends one code to one destination on six envelopes in an hour (members AC-6a…b) | derived — ADR-0077 §2.10 | Unit, `array` cache adapter | restore the single destination-only key |
| AC-7 | Each medium refuses the request one past its narrow ceiling on one envelope (the sixth SMS, the eleventh email), and the refusal names the narrow counter (members AC-7a…b) | derived — ADR-0077 §2.10 | Unit, `array` cache adapter | drop the narrow counter (inferred) |
| AC-8 | Each medium refuses the thirty-first request across thirty-one envelopes, and the refusal names the wide counter (members AC-8a…b) | derived — ADR-0077 §2.10 | Unit, `array` cache adapter | drop the wide counter (inferred) |
| AC-9 | After the session counter is exhausted, `app:session:clear-otp-limits` makes the next send succeed | derived — ADR-0077 §2.10 | Application / console, `array` cache adapter (inferred) | skip the session reset (inferred) |
| AC-10 | After the source counter is exhausted the command does not make the next send succeed, and its output names that | derived — ADR-0077 §2.10 | Application / console, `array` cache adapter (inferred) | drop the output line (inferred) |
| AC-11 | The keys the command derives equal `OtpSendKeys::of()`'s for the same inputs | derived — ADR-0077 §2.10 | Unit (inferred) | change the lower-casing in one place |
| AC-24 | `app:session:clear-otp-limits` records a Session event whose payload is the closed key set operator, instant and ids, with no destination | derived — rule 5 (closed key set) | Application / console | skip recording the event |
| AC-25 | The machine counter is cleared only when `--api-client` is passed | derived — rule 5 (the other half of the flag) | Application / console, `array` cache adapter | clear the machine counter on every run |
| AC-12 | Each new destination counter fails open with the store unreachable: the send goes through and an `error` is logged (members AC-12a…b) | derived — ADR-0014 | Unit (inferred) | make the limiter fail closed (inferred) |
| AC-13 | With tenant A over the threshold and B under, the report names A only and exits non-zero | derived — ADR-0077 §2.10 | Integration (real database, RLS) | drop the threshold comparison (inferred) |
| AC-14 | A send in tenant A still succeeds after the report | derived — ADR-0077 §2.10 | Integration (real database, RLS) | make the report gate the send path (inferred) |
| AC-15 | 10 SMS and 10 emails for one tenant against a threshold of 15 is under | derived — ADR-0077 §2.10 | Integration (real database, RLS) | drop the `channel = 'SMS'` filter |
| AC-16 | The `SECURITY DEFINER` function returns only `tenant_id` and `sms_count` | derived — ADR-0077 §2.10 | Integration (real database, RLS) | add a destination column to the function (inferred) |
| AC-26 | Each SMS delivery that has not cost anything is left out of the count (members AC-26a…b) | derived — rule 5 (the set the filter exempts) | Integration (real database, RLS) | drop the status filter |
| AC-27 | An SMS requested just over an hour before the report runs is not counted; one just inside is | derived — ADR-0077 §2.10 (boundary of the window) | Integration (real database, RLS) | widen the window by a minute |
| AC-17 | The new job is in each place the custodian census reads (members AC-17a…b) | derived — ADR-0061 | `CustodianScheduleCensusTest` | remove it from that place |
| AC-18 | `fromString('operator:ana')` round-trips, and a label that is blank, longer than 64 characters, untrimmed or not printable is refused before it can reach the append-only log (the bound added after review: 64, printable, trimmed) | derived — ADR-0077 §2.10 | Unit, `ActorKindTest` extended (inferred) | drop the prefix from `fromString()` (inferred) |
| AC-19 | `ActorKind::fromIssuer()` returns `SYSTEM` for an `operator:` issuer; no case is added to the enum | derived — ADR-0077 §2.10 | Unit, `ActorKindTest` extended | map the prefix elsewhere (inferred) |
| AC-20 | An unknown prefix is still refused | derived — ADR-0077 §2.10 | Unit, `ActorKindTest` extended | accept any prefix (inferred) |
| AC-21 | The new refusal code is in the resend route's OpenAPI responses | derived — rule 1 (closed enumerations in `#[OA\*]`) | Acceptance (inferred) | drop the `#[OA\*]` response (inferred) |
| AC-22 | A frontend handoff for the new refusal code exists | derived — ADR-0077 §2.10 | review of `docs/frontend-handoff/` (inferred) | — (inferred) |

**Notes on AC-1**
- AC-1a — `["SMS"]`: refused. AC-1b — `["EMAIL","SMS"]`: refused, so the cap reads the whole list and not its first member. AC-1c — `["EMAIL"]`: allowed.
- Fixture: two recipients, same envelope, both resent five times past the interval. The `["EMAIL"]` case is the one that reddens under the sabotage.
- The interval is driven by the `Clock` test double, with a case where the interval would allow the resend and the cap does not, so the cap is the guard that fired, not the interval.

**Notes on AC-2**
- Sabotage: the `resendsMade` assertion reddens.

**Notes on AC-6, AC-7 and AC-8**
- Members a — SMS, b — email, per `OtpSendKeys::of()` serving both (§5 D-e).
- The sabotage of AC-6 is restoring the single destination-only key: the first member reddens.
- ⛔ Several counters stand in series (session, narrow, wide, source). Each fixture uses a distinct session per request and a distinct source address per envelope, and the test asserts **which** policy refused, so a sabotage cannot be reported green by a counter upstream (the repo's authoring rule 4).
- "Names the counter" is an **internal** observable: `OtpSendRateLimitedException` gains the refusing policy's name as a
  read-only property that nothing serializes. The wire refusal stays identical whichever key refused (same status,
  `OTP_SEND_COOLING_DOWN`, same wait), as the port's docblock requires, and a test pins that two refusals from
  different policies produce the same problem body. The name is for tests and logs only.

**Notes on AC-9…AC-11**
- The cache pool is the array adapter, so the property is the keys, not Redis.
- AC-11's sabotage is the failure mode of a re-derived digest: the keys diverge and the clear misses.

**Notes on AC-12**
- AC-12a — the narrow counter. AC-12b — the wide counter. The existing fail-open test stays green and is extended to them.

**Notes on AC-13…AC-16**
- Run through the lane's real database (Integration), since RLS is the property.

**Notes on AC-17**
- AC-17a — `CustodianSchedule::jobs()`. AC-17b — the census test's predicate. Removing the job from either reddens `CustodianScheduleCensusTest`.

**Notes on AC-26 and AC-27**
- AC-26a — a `PENDING` delivery. AC-26b — a `NOT_NEEDED` delivery (TASK-055). Both sit beside a counted `SENT` one, so the count is 1, not 0.
- A `FAILED` delivery is counted (§5 D-d); the fixture carries one, so the count reads 2 with it and the exemption stays two members wide.
- AC-27 uses the `Clock` test double: one SMS at `now - 61 min`, one at `now - 59 min`; the count is 1.

- Each bar names the fixture whose variables disagree and the sabotage that must redden it.
- Full suite, Infection covered-MSI, PHPStan, deptrac (`--fail-on-uncovered`) and lint green in the worktree lane. A migration is generated, never numbered by hand.

## 7. Open follow-ups (track, don't solve here)

- **Provider-side hard cap** (production prerequisite, ops): usage triggers, a prepaid balance without auto-recharge,
  geo permissions, an approved sender ID, and the provider agreement and privacy notice.
- A money budget per tenant, if the single-client deployment ever becomes multi-client ([BL-166](../BACKLOG.md)).
- Deferring non-urgent notices to daytime (never invitations or codes), and reminders for unopened invitations;
  revisit when a recipient or the client complains about a night-time notice, or asks for reminders.
- **Whether the SMS limiter should fail closed** when its store is unreachable, which ADR-0014 says has to be argued per operation.
- **Whether to alert on email volume too**; nothing suggests it costs. Revisit if the email provider starts billing
  per message or a deliverability block is traced to volume.
- A recipient shared by many envelopes still sees the narrow counter reset only by the clock; whether a per-sender
  ceiling is wanted waits on real traffic. ⚠ The wide destination counter is keyed on the destination alone (D-e), with
  no tenant, so one tenant's envelopes to a phone can exhaust its 30 an hour for another tenant's recipient: a
  cross-tenant lockout, availability only and bounded at 30 an hour. It is the same question as the per-sender
  ceiling, so it is revisited there ([BL-427](../BACKLOG.md)).
- **The channel-change re-invite is not capped** ([BL-413](../BACKLOG.md)). This task capped only the resend route
  (`RECIPIENT_RESEND_CAP_REACHED`); a client looping on the channel-change route can still send one SMS per call while
  the destination never accepts. Revisit with real SMS traffic ([BL-169](../BACKLOG.md)).
- The limiter keys are unsalted `sha256` of low-entropy values (a phone, an address); this predates the task and a
  read of the Redis pool could brute-force them ([BL-428](../BACKLOG.md)).
- **Revisit the SMS ceilings** against the first real traffic ([BL-169](../BACKLOG.md)).

---

## 8. Deviations & honest notes

### Scope
- Beyond the record: `assets/evidence-audit/trail.typ` (two labels for the new session and envelope facts, see *Decisions*), the audit trail's sentinel-scope census, `config/packages/nelmio_api_doc.yaml`, a cross-reference in `docs/tasks/TASK-041-*.md`, and a docblock edit of the published migration `Version20260831000002` (comments are always in scope, repo rule 2). Nothing falls under the record's *Out*.
- A coordinated change in `f5sign-infra`: the role `f5sign_notification_custodian` did not exist and the funnel's owner needs it (commit `15bfdc5`, merged on infra master, not pushed). ⚠ **Production: run `make init-roles-prod` BEFORE `migrate-prod`**, or the migration that grants to the role fails.

### Decisions made during implementation
- **`resend_allowance` has no database default.** The migration backfills with `DEFAULT 0` and then drops it, as `Version20260831000002` did: [ADR-0019](../adr/ADR-0019-schema-conformance.md) §4 (Accepted) and `SchemaConformanceTest` forbid a column default, which overrides the record's D-c sentence "a default is right here".
- **AC-6b uses eleven envelopes, not six.** Six emails would pass under the old destination-only key (10 an hour), so only eleven discriminates; eleven includes six.
- **AC-22 is proven by the handoff and `/contract-check-backend`, not by a test** (`docs/frontend-handoff/TASK-057-dashboard-resend-cap.md`; precedent TASK-056 AC-36). The handoff also tells the signer and the integrator that an OTP send refusal can now wait up to an hour (`12c70171`).
- **The two corrections of `0ec692bd`** (claims check, before any code): the narrow ceiling keeps today's value per medium (SMS 5, email 10), so AC-7 names the sixth SMS and the eleventh email; and "the refusal names the counter" is an internal, unserialized field on `OtpSendRateLimitedException`, the wire refusal staying identical whichever counter refused. Both unblock commands take a required `--tenant`; FAILED deliveries count in the volume report.
- **Bounds added after review.** `--grant` is at most 32767 (`resends_made` is a SMALLINT; above that the write failed with a raw SQL message). The operator label is bounded: 64 characters, printable, trimmed, with `SystemActorId::operatorLabel()` as the one source of the bare label the event payload carries (slice 15, the security audit's W1).
- **Fix slice for the trail labels and the sentinel census** (slice 13, finished in 14): `OTP_SEND_LIMITS_CLEARED` reads "Contadores de envío de códigos reiniciados" and `RECIPIENT_RESENDS_UNBLOCKED` reads "Reenvíos de invitación adicionales permitidos" (the first wordings overstated what was cleared or granted and named an unauthenticated operator as actor); the sentinel-scope census lists the new facts.
- Refusal code `RECIPIENT_RESEND_CAP_REACHED` (409), asked before the interval because waiting does not cure it. The cap is `resendsMade >= 5 + resendAllowance` for any list that includes SMS, and a grant adds to the allowance and never resets `resendsMade`. `clear()` does not fail open: a store error propagates so no fact is recorded.
- **On deploy, an in-flight SMS recipient already at 5 resends or more is refused at once**; an operator grant (`app:envelope:unblock-resends`) is the repair. Say so in the PR notes.

### Decisions that needed an ADR
- None drafted: every structural choice was approved by the owner on 2026-10-09 or follows an in-repo precedent. [ADR-0077](../adr/ADR-0077-a-recipient-declares-the-channels-that-reach-them.md) §2.10 is exercised by this task; the owner moved the ADR to **Accepted** on 2026-10-19, in its own commit on this branch.

### Declared and unproven properties
- **Declared environmental failure:** the last full run (tip `2e7730be`, 7356 tests, 82515 assertions) had one failure, `StorageLifecycleScenarioTest`. It passes alone on the same tree on the lane (1 test, 645 assertions, 2026-10-19), and the branch touches no Storage file; it ran beside a parallel lane. The previous full run, on `8a7ce7ed`, was green. The run on the merged tree (`bba6a384`) was green, that test included.
- **Two merge repairs after merging develop (TASK-058):** TASK-058 excluded `Notification/Domain/ReadRepository` from autodiscovery, which was how `SmsVolumeByTenant` had been bound, so the container stopped compiling (`29f59233` binds it by name); and it gave `Notification::recordSent()`, `recordFailed()` and `recordNotNeeded()` new required arguments, which two of this branch's test fixtures still called the old way (fixed in the tests, recording each outcome at the occasion's request time, so the SMS-volume windows keep their meaning).
- AC-22 has no test (above). The `down()` of the two migrations was left to doctrine-guard, not re-run by the suite.
- Console paths of `app:envelope:unblock-resends` and `app:session:clear-otp-limits`: the INVALID cases are tested, and so is a cross-tenant refusal (`a_tenant_that_does_not_own_the_envelope_is_refused` in `UnblockResendsCommandTest` and `ClearOtpLimitsCommandTest`). That refusal is pinned by the not-found and no-session messages; dropping the scope is caught earlier by the bus's missing-tenant check, so the RLS half rests on `SchemaConformanceTest`'s FORCE RLS pin.
- Infection, filtered to the branch's 34 `src/` files (`make wt-backend-infection`, lane `wt-f5sign-backend-sms-spend-guards`,
  2026-10-19). **Whole-file** on `2e7730be`: covered-MSI 82.26 %, MSI 71 % (2567 mutants: 1639 killed, 354 escaped,
  306 not covered). Below the 85 % covered bar only because `--filter` mutates whole files, so `Envelope.php`,
  `Recipient.php` and `SigningSession.php` bring their pre-existing survivors (311 of the 354), the debt tracked as
  BL-409. **Changed lines**, the gate the infra script `infection-changed-lines.py` applies: 43 escaped, 0 not covered,
  0 timed out on `2e7730be`; after the kill slice, re-run on the eight files it targeted against merge-base `67253940`:
  **7 escaped, 0 not covered, 0 timed out**; review then showed one of the seven was not equivalent and a test kills it, so six remain, all justified as equivalent:
  - `UnblockResendsCommand` `CastInt` on `--grant`: after `ctype_digit()` the comparison with the bound is numeric
    either way.
  - `ClearOtpSendLimitsUseCase` inner `LogicalOr` on the skip of a method that delivers no code: `deliversCode()` is
    true exactly when the medium is non-null, so `(A && B) || C` skips the same methods. (The outer one is not
    equivalent: an SMS method declared with no phone would reach `OtpSendKeys::of()` with a null destination; a test
    kills it.)
  - `ClearOtpSendLimitsUseCase` `Concat` ×2 and `ConcatOperandRemoval` ×2 on the de-duplication key: the destination is
    a function of the medium and no medium value prefixes another, so de-duplication is unchanged.
  The other 37 changed-line survivors are killed by tests, each sabotage-checked (slice 16 of the run).

### Debt left behind, and where it lives now
- Channel-change re-invite uncapped: [BL-413](../BACKLOG.md), repointed to "not taken by TASK-057"; §7.
- Cross-tenant lockout of the wide destination counter: [BL-427](../BACKLOG.md); §7.
- Unsalted limiter keys: [BL-428](../BACKLOG.md); §7.
- Provider-side hard cap, SMS ceilings against real traffic ([BL-169](../BACKLOG.md)), fail-open versus fail-closed, email volume alert: §7.
- Resend cap and `resends_made` prose: [BL-213](../BACKLOG.md) is read for tense (still correct for an email-only recipient).

### Delegated work
- 14 slices: 13 critical on opus (slices 01–11, 14, 15; 9 fix rounds across them: 01, 02, 04, 05, 07, 10, 11, 14, 15 one each; 03, 06, 08, 09 none) and one standard on sonnet (12, the handoff, round 0). Statuses: 10 DONE and 4 DONE_WITH_CONCERNS (02, 06, 08, 09). Slice 13 (trail labels and the census, standard) ran as a fix slice and is not in the log's tally.
- Every slice report's `## Delegated` reads "none" (no slice had three or more repetitive targets), so no replicator output was accepted or redone.

### Cost of the run
- Slices: 13 on opus, 2,064,447 tokens; 1 on sonnet, 93,346 tokens (14 slice lines in the log).
- Review rounds: 9 fix rounds in total, plus the closing review (7 findings, a 22-item worklist, slice 14) and the security audit's W1 (slice 15).
- Escalations: none to a higher tier; four NEEDS_CONTEXT stops answered by the orchestrator (slices 02, 03, 04 and 10: a retired-name census, the column default against ADR-0019, the conformance census).
- Suite: baseline 6066 tests, final 7356 (82515 assertions), under the kept `wt-backend` lane.
- Gates: task-validate, doctrine-guard pass; contract-check and security-audit warn, resolved or routed (W2/W3 to the backlog).
