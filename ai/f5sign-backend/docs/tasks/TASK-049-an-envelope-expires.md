# TASK-049 — An envelope expires: a chosen, extendable life that ends it as its last deadline, read by a sweep

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `feat/envelope-expiry`** (`f706a214`; code last changed in `d5ec4976`), 2026-09-29 — full suite green under the main checkout via the infra Makefile (`make test`, lint, PHPStan, deptrac) at `fc05cc4a`: 4247 tests, 24542 assertions, 0 failures; the later commits (`ceb8d1f2`, `d5ec4976`) were validated by filtered runs of the tests they touch. It joined `feat/task-048-how-an-envelope-ends` with the rest of the ADR-0073 package (`febb589b`, `a7c8f81d`), which was merged into `develop` on 2026-09-30 at `e6a0af5e` (⛑ corrected 2026-10-01; this read "Pending review; not pushed, not merged"). **Infection not run** (deferred to the package end by the maintainer). **Not verified:** that a running worker consumes the new schedule (workers were down; a package-level stack check, §6). Drafted 2026-09-24, re-cut through 2026-09-28. |
| **Type** | **Forward build with one retirement.** `expiresAt` gains a consumer, a sender-chosen value and an extension; expiry becomes the last deadline, ending an envelope like any other; `EnvelopeStatus::EXPIRED` is retired. |
| **Why** | `expiresAt` is decorative ([`BL-202`](../BACKLOG.md)): persisted, frozen at send, consumed by nothing in the signing flow, and hard-coded by `CreateEnvelopeController` to thirty days after **creation**. An envelope past its date stays `SENT` and signable for ever, and a step that waits cannot be bounded. |
| **Builds on** | Reused unchanged: Symfony Scheduler as `CustodianSchedule` uses it · the cross-tenant funnel pattern (a `SECURITY DEFINER` function, sentinel-tenant pin and restore, a column-scoped grant, a policy written `TO` its role) that `Version20260908000004` introduced — its function bodies were since replaced by `Version20260928131928` and `Version20260928142509`, which are the ones to read · `ConservationCeiling` resolved in `Envelope::send()` · the two-process harness of `EnvelopeConcurrentAppendTest`. |
| **Scope** | The sender's choice of expiry (a duration held while a draft, resolved at send) and the migration of existing drafts' dates to it; extension; the date in `acceptsActs()`, read through TASK-048's `app_now()`; the sweep, its schedule, its dedicated role and its per-envelope command; expiry as the last deadline; wiring the real `expires_at` into the evaluator (`Envelope::snapshot()` passes the `NO_EXPIRY_YET` sentinel until then) — `EndCause::EXPIRED`, `ReleasedBy::EXPIRY` and `EnvelopeVoided`'s partyless `EXPIRED` already exist since TASK-048; the retirement of `EnvelopeStatus::EXPIRED` (its read in `StepCompletionEvaluator` already went with that class's rewrite, 2026-09-28); conservation re-resolved at the end. Out of scope (§6): other status members without a writer, the link's fixed life, reminders. |
| **Decision record** | **[ADR-0073](../adr/ADR-0073-step-policy-expiry-and-what-an-unagreed-envelope-keeps.md)**, drafted `Proposed` on 2026-09-24 and re-cut through 2026-09-28, before implementation. This task exercises its §2.3 (the date), §2.4 (for expiry), §2.8 (`released_by: EXPIRY`), §2.12, §2.13 and §2.16. |
| **Delivery bar** | Over HTTP with `app_now()` pinned on the test database: create an envelope with a 2-day life, send it, one of two signers in its one `ALL` step signs, extend by 1 day (200); past the new date and one sweep run → `COMPLETED`, `outcome: NOT_AGREED`, `end_cause: EXPIRED`, no party, the signed document sealed and conserved, the unsigned signer `RELEASED` · `SENT_NO_RESPONSE` · `EXPIRY` (invited at the send, link still valid); a further extension answers a named 409. A second envelope whose last signer committed one second before its date, with DSS held, ends `AGREED` once DSS is released. |
| **Sibling** | **[TASK-048](TASK-048-what-an-unagreed-envelope-keeps.md)**, built before this task on the same branch: its admission, securing and closing, `acceptsActs()` and lifecycle are used here (not under *Builds on*, since they are not built yet). **[TASK-050](TASK-050-a-step-says-how-much-agreement-it-needs.md)**, after it, gives the step deadline and the one step predicate that expiry evaluates with. **`f5sign-infra`**, two coordinated changes: the worker consumes the new schedule's transport (development and production compose files); `init-app-role.sh` creates the sweep's dedicated role (the test body of `app_now()` is TASK-048's infra change). <!-- OFFREPO: f5sign-infra is the sibling repo holding the compose files and `docker/postgres/init-app-role.sh`; the two changes are restated here in full (a worker consuming the schedule's transport; the sweep role created NOBYPASSRLS), and nothing in this repo's code depends on reading it. --> |

---

## 1. Why this task exists

Measured on `develop` at `3bda20a`, 2026-09-24: `Settings::$expiresAt` is written by `CreateEnvelopeController` as
`issuedAt + 30 days` at **creation**, persisted in `settings_expires_at`, and read only by the storage lifecycle.
Nothing ends an envelope because of it. `EnvelopeStatus::EXPIRED` has no writer; it is read by `isTerminal()`,
`withholdsDocumentFromRecipient()`, `readsWaitForTheSeal()`'s classification, `StepCompletionEvaluator` (no
production caller), a `#[OA\*]` string in `VoidEnvelopeController` and the published `status` enum. No frontend
code branches on it; the signer carries it only in its OpenAPI snapshot fixture (the envelope `status` enum),
and its own `'EXPIRED'` in `app/composables/api/types.ts` belongs to the session status union, not the envelope's. The `worker` container consumes only `async_events`. `send()` is DRAFT-only.

## 2. What already exists (reuse, do not rebuild)

- Symfony Scheduler (`#[AsSchedule]`, `RecurringMessage::every`) on `scheduler_custodian`, consumed by `custodian`.
- The funnel pattern: a `SECURITY DEFINER` function naming tenants with work, per-tenant work in ordinary scope.
- `ConservationCeiling`, resolved only in `Envelope::send()`.
- TASK-048's `app_now()`, with its test body.

## 3. What gets built

### 3.1 The sender chooses; the send resolves

The create route accepts an optional life as a duration (default 30 days, 1–180). A draft holds the duration;
`send()` resolves it to `expires_at`. `CreateEnvelopeController` stops computing a date. The migration turns every
existing `DRAFT`'s date into its duration (`expires_at − created_at`, which today is always thirty days, within
1–180). `expires_at` is published
on the read side. The `#[OA\*]` strings state the default, the range, the anchor, and advise step deadlines that
fit the life and a resend when a deadline outlives the seven-day link.

### 3.2 Extension

A sender route extends `expires_at` forward, repeatedly, never past 180 days from the send, only while
`acceptsActs()`, comparing against `app_now()` under the root lock, by a narrow write. Each extension is a recorded
fact, `EnvelopeExpiryExtended` (the previous and the new date, the sender), classified in ADR-0064 §2.4's census as excluded — the sender's own act (maintainer, 2026-09-28). Refusals name their condition (ADR-0067): closed, past its date, beyond the cap, not forward.

### 3.3 The date in `acceptsActs()`

`acceptsActs()` requires `app_now() < expires_at`, through TASK-048's `app_now()`, on every route that asks it — the
gate's unlocked read included. PHP fast-path checks are advisory; the locked database check decides.

### 3.4 The sweep

A dedicated schedule with a recurring message every minute, consumed by the worker once the infra change lands.
Its handler asks a funnel which tenants hold an unclosed envelope with a past `expires_at` (TASK-050 widened the
funnel to due step deadlines on 2026-09-29, `3be2c390`, and created the column), then dispatches one per-envelope command in that tenant's
scope. The funnel's definer is a
**dedicated `NOBYPASSRLS` role** with a column grant limited to its predicate and a policy written `TO` it,
created by `f5sign-infra` (the role's creation script; <!-- OFFREPO: sibling infra repo, see the Sibling row -->). The command, under the root lock, closes due steps (the slot TASK-050 filled: the evaluator's clock path already closed a due step, `3be2c390` gave the funnel its half), then
evaluates the expiry, re-checking each; a repeated or late run does nothing twice.

### 3.5 Expiry as the last deadline

At `expires_at` the envelope stops admitting acts. The command releases every member still pending with `released_by: EXPIRY` and the `release_reason` TASK-048 derives from their facts (ADR-0073 §2.8), evaluates the open step with the one step predicate — the same rule a step
deadline uses (ADR-0073 §2.4) — and ends `AGREED` if that yields agreement with no later step outstanding, else
`NOT_AGREED` with the cause ADR-0073 §2.6 names (`MEMBER_NOT_REACHED` in a veto step with an unreached member,
else `EXPIRED`), recorded as `EnvelopeVoided` with no party. With no step open — a closed step's next one still waiting for its landings — expiry finds a later step outstanding: `NOT_AGREED` · `EXPIRED`. An envelope already closed is left alone; one whose agreement
is secured is closed `AGREED` with its pending members released — expiry is what closes it when its last step has
no deadline. The command calls the aggregate's predicate, never a copy of it: `Envelope::evaluator()` over `Envelope::snapshot()`,
applied by `Envelope::apply()` — `EnvelopeEndingEvaluator` over `StepCompletionEvaluator`, in which informational
members never hold their step (TASK-050's half that retired `InformationalMembers::HOLD_THEIR_STEP`, merged into this
branch from `feat/step-policy`); the three tasks deploy together.

### 3.6 Nothing but the sweep after the date

From `expires_at` the void, close-now and extension routes, and a landing that would activate the next step, are refused or deferred as expired; the sweep closes the envelope within a minute (maintainer, 2026-09-28, ADR-0073 §2.12). `ExpiryGapTest` holds it: every case closed with the action before the sweep and after it ends alike.

### 3.7 Retirement of `EnvelopeStatus::EXPIRED`

Removed from the enum, its classifications, the `#[OA\*]` strings, the
published `status` enum and the signer's OpenAPI snapshot fixture (in the signer's handoff);
`EnvelopeStatusTest`'s hardcoded members updated. Docblocks that assumed expiry was decorative are corrected:
`Version20260908000004` and `ConservationCeiling`/`Envelope::send()` (repo rule 2 keeps published migration
docblocks in scope).

### 3.8 Conservation re-resolved at the end

At `COMPLETED` the ceiling becomes `max(provisional, completed_at + retention)`; it never moves backwards.

## 4. Key decisions (maintainer, 2026-09-24/25)

- **D1** — Expiry is the last deadline: same rule as a step deadline, `AGREED` possible, else the cause §2.6 names.
- **D2** — Existing envelopes are not special-cased. (The expiry notice this decision once said did not exist is
  [TASK-040](TASK-040-cancellation-notice.md)'s *time ran out* family, `ENVELOPE_ENDED_TIME_RAN_OUT`, reached with no
  further wiring once expiry records `EnvelopeVoided` with cause `EXPIRED`; it lives on `feat/ending-notice` in the same package.)
  So every `SENT` envelope whose date — thirty days after its **creation** — has already passed is expired by the
  sweep's first run after the deploy; the deploy's handoff and release note say so.
- **D3** — Default 30 days; 1–180; extensions forward to 180 days from the send.
- **D4** — No extension and no act once the date has passed, by the database clock under the lock.
- **D5** — Counted from the send, not from creation.
- **D6** — Clocks are database dates read by a sweep on the ordinary worker, one command per envelope.
- **D7** — Conservation anchored at the end, the send-time ceiling as a floor.
- **D8** — The link keeps its seven days ([`BL-306`](../BACKLOG.md)).

## 5. Verification

- The delivery bar, both envelopes, with `app_now()` pinned.
- **Expiry evaluates with the aggregate's predicate**: an open step with one signature and one silent member ends
  `NOT_AGREED`/`EXPIRED` at expiry, by the same predicate an admission uses (no copy). The comparison with a step
  deadline closing the same step is TASK-050's property test, which needs that task's deadline.
- **Idempotency**: overlapping sweep runs, and the same command handled twice by direct re-invocation, close once.
  (No test transport redelivers — the scheduler transport refuses `send()` and `async_events` is in-memory.)
- **The lock orders an extension and a commit** (two connections, `app_now()` pinned on each, between the old
  date and the new): the extension commits first → the commit is admitted; the commit takes the lock first → it
  is refused, and the extension after it is refused as past its date. With the clock pinned past both dates, both
  are refused.
- **Retirement census**: no live reference to `EnvelopeStatus::EXPIRED` in `src/`, `tests/`, `config/`,
  `migrations/` (docblocks included), the spec or either frontend (fixtures included; the signer's session-status
  `'EXPIRED'` is another enum and is not in scope); `docs/` references classified, historical ones
  kept (authoring rule 1).
- **Conservation**: a 180-day envelope's ceiling at `COMPLETED` is `completed_at + retention`.
- **Grant boundary and two tenants**: the sweep role reads only its columns and sees both tenants' due work
  (ADR-0061 §2.11), through a role-switched harness: TASK-048's `SwitchesToCustodianRole` hardcodes `f5sign_envelope_custodian`, so it is parametrised by role (or given a sibling) for the sweep's own role.
- **The schedule is consumed**: verified on the stack once the infra change is in place, never from the suite alone.

## 6. Open follow-ups (track, don't solve here)

- The other status members without a writer — [`BL-202`](../BACKLOG.md) keeps them; its row says the expiry half closed.
- [`BL-306`](../BACKLOG.md); reminders (`RemindersSchedule` has no consumer). ~~An expiry notice with TASK-040~~ — done by TASK-040's *time ran out* family (`ENVELOPE_ENDED_TIME_RAN_OUT`), which needs no wiring from this task (2026-09-29).
- Extending a step's deadline (ADR-0073 §2.18).
- **Package-level check, no BL:** that the worker actually consumes `scheduler_envelope_clocks` and the `envelope_clocks` schedule fires `app:envelope:sweep-clocks` every minute. The suite cannot reach it (the scheduler transport refuses `send()`); it is checked at the joined package's stack validation, with the workers up and the infra change live.
- **Package-level check, no BL:** `Infection` over the joined package (deferred by the maintainer), and the frontend handoff for this task's contract changes (`expires_in_days`, the nullable `expires_at`, the extension route and its three new codes, `EXPIRED` leaving the published `status` enum), written at the join.
- ~~[`BL-202`](../BACKLOG.md)'s expiry half~~ — closed by this task, 2026-09-29; the row stays open for the unwritten status members (`SEALING`, `CORRECTING`, `ROUTING_FAILED`, `SEALING_FAILED`).

## 7. Deviations & honest notes

### Scope
- Beyond §3: `EnvelopeExpiredException` and the `ENVELOPE_EXPIRED` problem code on the sender's void, correction, resend, claim and extension past the date (§3.6 named the refusal, not the code); `RecipientEnvelopeContextView::$pastExpiry` (the view twin of `acceptsActs()`, computed in SQL from `app_now()`); a merge of `feat/step-policy` (`d2b9f169`) so the predicate expiry evaluates is the one TASK-050 leaves; docblock corrections in `Version20260908000002`, `Version20260908000004`, `ConservationCeiling` and `Envelope::send()`, and the stale `advanceAfterRecipientTerminal()` references (six files).
- Fixtures: `EnvelopeBuilder` gives units a 180-day life, and DB seeds write a far-future date (`KeepsSentFixturesUnexpired`) — a send-relative life would be a time bomb for tests that act on the real clock.

### Decisions made during implementation
- **D1 (wire names)** — create takes optional `expires_in_days` (1–180, default 30); the read side publishes `expires_in_days` and a nullable `expires_at`; the extension is `POST /api/v1/envelopes/{id}/expiry-extensions` with an absolute `{"expires_at": RFC 3339}` (the "not forward" refusal only has meaning for an absolute date; a collection because each extension is an appended fact) answering 200 `{"expires_at"}`.
- **D2 (codes)** — sender side `ENVELOPE_EXPIRED`, `EXPIRY_NOT_FORWARD`, `EXPIRY_BEYOND_LIMIT`; a closed envelope's extension answers the existing `ENVELOPE_NO_LONGER_LIVE`, a draft's `ENVELOPE_NOT_SENT`. `EnvelopeStatus::EXPIRED` leaves the published enum.
- **D3 (fixtures)** — as under Scope.
- **D4 (landings)** — a landing keeps its fact's instant; the activation it would trigger is judged at that instant and deferred to the sweep when past the date.
- **D5 (schedule)** — its own `#[AsSchedule('envelope_clocks')]` in Envelope Infrastructure running a console command through `RunCommandMessage` on the tenantless `custodian.bus`, locked; not a `CustodianSchedule` job (ADR-0073 keeps the sweep off the custodian).
- **D6 (entry point)** — `Envelope::applyClocks($at)` is `decide(snapshot(), Trigger::clock($at))` plus `apply()`; TASK-050's due step deadlines are already in the evaluator's clock path, so its slot in the funnel is the predicate.
- **Sender writes stamp with the command's instant and judge the date by `app_now()`** — correction, resend and claim keep stamping with `issuedAt` (the resend interval depends on it); their use cases first ask `Envelope::guardBeforeExpiry(appNow())` under the lock and the aggregate methods re-ask with their own instant. The extension controller's `issuedAt` exists because the Kernel `Command` requires it and is unused by design.
- **The lock-ordering bar's clocks are per process, not one shared instant**: the winning extension is pinned a minute before the old date (an extension at or past it is refused by §2.12), the commit between the dates.
- **The funnel's `closed_at` clause is guarded twice** (function and `TO`-role policy): sabotaging the function alone stays green; both reddens two cases. Recorded rather than "fixed".
- **`Version20260929095359` was verified live** (`up → down → up` on the test DB with drafts and sent rows present), not by a fixture test; its `down()` is exact only for 30-day rows, as its docblock says. It was edited after a first local run to drop a `DEFAULT 30`, so a local database that ran the earlier cut needs a reset.
- **The delivery bar's signatures go through the recipient HTTP ceremony**, the sealing is live EU DSS.

### Decisions that needed an ADR
- None. The sweep role, schedule and funnel are [ADR-0073](../adr/ADR-0073-step-policy-expiry-and-what-an-unagreed-envelope-keeps.md) §2.13's own words. ADR-0073 was already `Accepted (enforcement partial)`; its Status, §5 and §6 now name this task's slice (§2.3's date, §2.12, §2.13, §2.16), and §2.4 stayed Proposed at this task's close until TASK-050's deadline clock made the same-facts comparison discriminating. ⛑ Done 2026-09-29: TASK-050 built the deadline (`3be2c390`) and the comparison (see the last bullet of "Declared and unproven properties"), and ADR-0073's Status now names §2.4 among the sections it exercised.

### Declared and unproven properties
- The schedule being consumed by a running worker: unverified from the suite by construction, and the workers were down.
- `down()` of the two migrations is not under a test (`Version20260929095359` was checked live once).
- Covered-MSI: not measured (deferred to the package end).
- The comparison of expiry with a step deadline closing the same step was TASK-050's property test, and it exists on the joined package (2026-09-29): `StepCompletionEvaluatorTest::a_deadline_and_the_expiry_close_the_same_facts_to_the_same_outcome` (the pure census), `EnvelopeEndingStoriesTest` (both clocks through `Envelope::applyClocks()`) and `StepDeadlineGapTest`. Its HTTP-tier twin is not built (TASK-050 §7).

### Debt left behind, and where it lives now
- The worker/schedule check, Infection and the frontend handoff: §6, package-level, no BL row.
- [`BL-202`](../BACKLOG.md) (the unwritten status members), [`BL-306`](../BACKLOG.md) (the link's fixed life), reminders: §6.
- No new BACKLOG row was needed.

### Deploy notes
- **The first sweep after the deploy expires every open envelope whose old date has passed.** Existing sent envelopes keep the date they were given (thirty days after their creation, D2), so the first run of `app:envelope:sweep-clocks` ends each one past it as `COMPLETED` · `NOT_AGREED` · `EXPIRED` and releases its pending members; TASK-040's *time ran out* notice emails their invited recipients. The release note says so.
- **The infra role must exist before the migration runs.** `Version20260929102939` hard-depends on `f5sign_envelope_clock_sweep`, a `NOBYPASSRLS` role that the infra repo's role-creation script (`docker/postgres/init-app-role.sh`) must create, and on a database whose init script was re-run (`make init-roles` locally); without it the migration fails closed. The same infra change makes the worker consume the `scheduler_envelope_clocks` transport in the development and production compose files. Both land before the backend.

