# TASK-034 — The recipient access trace: publishing that somebody opened their link

| Field | Value |
|-------|-------|
| **Status** | ✅ **Built and green** on `feat/recipient-access-trace`, branched from `develop` at `2679b42`. Contract agreed with the `f5sign-dashboard` side before any code was written (see §2.1); the four naming questions and the three consumer conditions are settled and recorded in §5. Green on the **worktree lane** (`WT_GATES="lint arch phpstan test" make -C ../f5sign-infra wt-backend src=$(pwd)`), the only harness that validates this tree: lint `0 of 1011` · Deptrac `Violations 0` · PHPStan L9 `[OK] No errors` · `OK (2336 tests, 11149 assertions)`, against a `develop` baseline of `2294 / 10882`. ⛔ **Infection was NOT run** (opt-in fifth gate, cannot share the lane with the suite) — a declared gap, not a pass. **The four load-bearing guards were sabotage-checked**; see §9. |
| **Type** | **Forward build** — a fact the system already stores privately becomes a published one. No new decision: the cross-BC direction it uses is already granted and already carries two live reactors (§3.1). |
| **Why** | A sender can see that a recipient **signed**, and nothing before that. `GET /api/v1/envelopes/{id}` publishes `outcome` + `outcome_recorded_at` and no intermediate milestone, so from the sender's side a recipient who opened their link three days ago and stalled is indistinguishable from one who never opened it at all. **The fact exists**: `session.signing_session.created_at` is written by the first open and never moves. It has simply never had a way out of the Signing Session BC. |
| **Builds on** | Reused unchanged: the reactor pattern of [ADR-0002](../adr/ADR-0002-framework-free-event-reaction.md), the boundary re-typing of [ADR-0004](../adr/ADR-0004-cross-bc-anti-corruption-layer.md), the event log + relay of [ADR-0031](../adr/ADR-0031-event-log-store.md), and — the closest sibling, whose shape this copies almost line for line — the `AuthHardLockReached` crossing built by [TASK-021](TASK-021-two-gate-auth-model-and-access-gate.md). |
| **Decision record** | **None, and the absence is the claim.** This task opens no cross-BC dependency (`EnvelopeApplication → SessionContract` is already granted in [`deptrac.yaml`](../../deptrac.yaml) and already used by [`OnAuthHardLockReached`](../../src/F5Sign/Envelope/Application/Subscriber/OnAuthHardLockReached.php) and `OnSessionCompleted`), touches neither `Kernel/` nor `Foundation/`, and edits neither `deptrac.yaml`, `phpstan.dist.neon` nor the baseline. **Falsifiable:** if the diff touches any of those four files, this field is wrong and an ADR is owed. The one alternative shape that *would* have needed a decision — reading `session.*` from Envelope's read repository — is refused by [ADR-0019](../adr/ADR-0019-database-schema-conventions.md) §1, not by preference (§5 D1). |
| **Delivery bar** | A recipient who opens their signing link once, from two devices, and reloads it six times, has exactly one `first_opened_at` on `GET /api/v1/envelopes/{id}`, equal to the instant of the first open. A recipient who has never opened it has `null` — **including every recipient that existed before this task**, because the migration backfills from the session rows that already hold the fact. |
| **Deployment** | ⛔ **Migration first, deploy second — the inverse of `f5sign-infra`'s default.** The DDL is additive, so that default sends it after the deploy; but the new read repository names the three columns in its `SELECT`, so the new code against the old schema fails `GET /api/v1/envelopes/{id}` outright. See §8. |
| **Consumer** | `f5sign-dashboard`, branch `feat/ecmr-signature`: `RefreshWaybillSignaturesCommand` (`app:waybill:refresh-signatures`) is the sole reader, on a 10-minute timer over non-terminal envelopes plus an opportunistic refresh. It needs no listing endpoint and asks for the fields on no other surface. |

---

## 1. Why this task exists

The gap is not that the platform fails to record the open — it records it precisely, and idempotently, and has
since the Signing Session BC was built. The gap is that the record has **no exit**.

Three exits were checked and none works:

- **`GET /api/v1/signing/session`** requires `Authn::SESSION_CREDENTIAL`, which is minted only by passing the
  access gate. A sender cannot hold one, and a caller who obtained one would be a signer, not an observer. And
  even holding one it would not answer: [`SigningSessionReader`](../../src/F5Sign/Session/Application/Query/SigningSessionReader.php)
  projects from the **envelope**, not from the session row.
- **The event log** carries `AuthChallengeIssued` and `OtpSent`, from which an open can sometimes be inferred —
  but only behind a *declared* gate. Under an open access gate nothing is appended at all, so for the commonest
  configuration the log is silent. There is no `Session/Contract/Event/` member for the open itself.
- **Polling `POST /api/v1/signing/session`** would *create* the row and falsify the very fact being measured,
  besides minting a credential and evicting an idle grant. It is not an option and no consumer should be left
  to discover that for themselves.

**What makes this a task rather than a field**: the fact lives in one BC and is needed in another's read model,
so the shape question — where the value is stored, who writes it, and what `null` means for rows that predate
it — has to be answered before any of it is typed. §5 answers those three.

## 2. What already exists (reuse, do not rebuild)

### 2.1 The consumer's half is already built

The dashboard side is not speculative. `RecipientSignatureStatus::VIEWED`, `WaybillSignatureRecipient::$viewedAt`
and `WaybillSignatureReconciler::markViewed()` all exist and the timeline already renders a *"Visto"* point.
Today `viewedAt` is stamped only retroactively, from `markSigned()`'s backfill (*"if they signed, they saw it"*),
which is why the point never lights before the signature. Their integration is one line in the gateway's
`getStatus()` plus a `markViewed()` call.

⚑ **Their reconciler backfills earlier milestones from later ones**, which is what makes §5 D5's non-guarantee
safe to leave unaddressed.

### 2.2 The crossing pattern is built, twice

[`OnAuthHardLockReached`](../../src/F5Sign/Envelope/Application/Subscriber/OnAuthHardLockReached.php) is this
task's template and the resemblance is near-total: a Session milestone, relayed, landing on the Envelope
recipient row so the sender's read model can render it. Its paired Messenger adapter, its dispatch-only body, its
`SystemActorId::eventSubscriber()` issuer and its use case's *"skip the write when nothing changed"* shape are
all copied rather than re-derived.

⛔ **Do NOT copy `PropagateDeliveryFailureUseCase` instead.** That one runs *outward from* Notification and calls
Envelope's write port, and it is shaped that way only because Notification is a category-(c) supporting BC that
no layer may depend on ([ADR-0037](../adr/ADR-0037-notification-supporting-bc.md)). Session is a core BC; the
inversion buys nothing here and would put the translation on the wrong side of the boundary.

### 2.3 The executed-method enum already exists, on the right side

[`Envelope\Contract\Type\AuthMethod`](../../src/F5Sign/Envelope/Contract/Type/AuthMethod.php) is already the
anti-corruption mirror of `Session\Contract\Type\ExecutedAuthMethod`, with the same fourteen members. Its
`DIRECT_LINK` docblock says outright why the member is there: *"it is the method a completed ceremony records
having executed … Removing it would leave the executed-method projection unable to name the commonest case."*

**This task is that projection.** Nothing new is minted; the enum was authored anticipating it.

### 2.4 The seal-once idiom is established

[`Recipient::markDeliveryFailed()`](../../src/F5Sign/Envelope/Domain/Entity/Recipient.php) and
`Recipient::recordAuthHardLock()` both return `bool` — *did anything change* — so the aggregate records once and
the use case skips a write that would say nothing. That is exactly the convergence at-least-once relay delivery
requires, and the new writers take the same shape.

### 2.5 The fact itself is already exactly-once, by construction

`StartSessionUseCase` calls `SigningSessionRepository::startIfAbsent()`, whose implementation is a single
`INSERT … ON CONFLICT DO NOTHING` against a session id that is deterministic over `(tenant, envelope, recipient)`.
A reload, a second device and two simultaneous opens all aim at the same row. **`created_at` is the first open
and cannot drift** — which is why no de-duplication logic is needed anywhere in this task.

## 3. What gets built

### 3.1 Session — the fact gets a name

- `Session/Contract/Event/SigningSessionStarted` — `sessionId`, `tenantId`, `envelopeRef`, `recipientRef`,
  `accessMethodExecuted: ?ExecutedAuthMethod`, `occurredAt`. `EVENT_TYPE = 'SIGNING_SESSION_STARTED'`. Registered
  automatically by `RegisterDomainEventsPass`; nothing hand-maintained.
  ⚑ **The method, not a `bool accessGateWasOpen`** — the shape this record first proposed. A boolean would make
  the consumer synthesize `DIRECT_LINK` on the far side of an asynchronous boundary: a second home for a rule
  Session already states once, and one that would keep answering after the rule changed. `null` behind a declared
  gate, `DIRECT_LINK` behind a neutral one — and `null` is a fact, not a gap.
- `SigningSession::start()` records it.
- **`SigningSessionRepository::startIfAbsent()` returns `bool`** — whether it inserted — and the DBAL adapter
  drains the aggregate's pending events to the event log **only then**, inside the caller's transaction
  (ADR-0031). See §5 D2 for why this is the whole design.

### 3.2 Envelope — the fact lands on the recipient

- Migration: `first_opened_at TIMESTAMPTZ`, `authenticated_at TIMESTAMPTZ`, `access_method_executed TEXT` on
  `envelope.recipient`, all nullable, **plus the backfill** (§5 D3).
- `Recipient::recordFirstOpened(DateTimeImmutable): bool` and
  `Recipient::recordAuthenticated(AuthMethod, DateTimeImmutable): bool` — both seal-once, both converging.
- `Envelope::recordRecipientFirstOpen()` / `::recordRecipientAuthentication()` — no state guard, silent drop for
  an unknown recipient, for the reasons `Envelope::recordRecipientAuthHardLock()` already writes out.
- Commands + use cases under `Application/{Command,UseCase}/Lifecycle/`, loading under the row lock.
- `Envelope/Application/Subscriber/OnSigningSessionStarted` and `OnAccessGatePassed`, each with its Messenger
  adapter under `Infrastructure/Messenger/Subscriber/`. The first dispatches **two** commands when the fact names
  a method and one when it does not; the second acts on the `ACCESS` arm only.

### 3.3 The wire

- `RecipientView` gains the three fields; `DbalEnvelopeRepository` and `DoctrineEnvelopeReadRepository` map them.
- `EnvelopeJsonPresenter::recipient()` publishes `first_opened_at`, `authenticated_at`,
  `access_method_executed` — **flat**, beside `outcome_recorded_at` (§5 D4).
- The `#[OA\*]` schema on the envelope read route is updated in the same changeset. ⚑ Authoring rule 1 names
  those attribute strings as emitted verbatim into the spec the frontend ratifies; they are not comments.

## 4. Scope

**In:** `Session/Contract/Event/`, `SigningSession::start()`, the `startIfAbsent()` port + adapter, one migration,
`Recipient`/`Envelope`, two commands + two use cases, two subscribers + two adapters, `RecipientView`, the two
persistence mappings, the presenter, the `#[OA\*]` schema, `services.yaml` if wiring is not autowired, and the
tests §6 names.

**Out:** `notified_at` / delivery receipts (§7). Any decline surface (§7). `last_opened_at` or an open counter
(§7). Recording `AuthGatePassed` on the open-gate path (§7). Any change to `deptrac.yaml`, `phpstan.dist.neon` or
the baseline — see the Decision record field, where that is the falsifier.

## 5. Key decisions

**D1 — Envelope stores the stamp; it does not read Session's tables.** The consumer offered a read-side
projection as an equally acceptable alternative. It is not available: [ADR-0019](../adr/ADR-0019-database-schema-conventions.md)
§1 — *"A BC's SQL touches only its own schema plus a shared `platform` schema"* — and the tree obeys it today
(a census of `FROM <schema>.` across `src/` finds **zero** cross-schema reads). `EnvelopeUI` is also granted no
visibility of `SessionContract` in `deptrac.yaml`. So the stamp is the only conformant shape, and this is a
refusal with a reason rather than a preference.

**D2 — "Only the first open" is a property of one SQL statement, not a check.** `startIfAbsent()` returns whether
its `ON CONFLICT DO NOTHING` inserted, and the events drain only on the insert. The rejected alternative — emit
on every open and let Envelope seal only when the column is null — works, but puts the exactly-once property on
the *far* side of an asynchronous boundary and appends a permanent log row on every page reload of the signing
app. ⚑ The Envelope side stays seal-once **anyway**, because the relay is at-least-once; the two guards answer
different questions and neither replaces the other.

**D3 — The migration backfills, and the backfill is a copy rather than an inference.** Without it `NULL` would
mean *"either they never opened it, or the envelope predates this column"* and the consumer would have to render
the point as *unknown* for all history — which for a strip whose whole job is to say what happened is the same
as not shipping. The fact is already stored, so:

```sql
UPDATE envelope.recipient r
   SET first_opened_at        = s.created_at,
       authenticated_at       = s.authenticated_at,
       access_method_executed = s.access_method_executed
  FROM session.signing_session s
 WHERE s.envelope_id = r.envelope_id AND s.recipient_id = r.id;
```

Authoring rule 6 asks what a backfilled row means in **each** aggregate state, and here the answer is uniform
because the row is not an assertion about the envelope's state at all: it copies an instant that did happen, on
draft, in-flight, completed and voided envelopes alike, and it writes nothing where no session row exists. There
is no status predicate because there is no status for which the copy would be wrong. It is in the same `up()` as
the `ALTER TABLE`, so the columns cannot exist without it.

⚑ **A migration may cross schemas** — it *is* the schema authority and already creates every one of them.
D1's rule binds repository SQL. And per authoring rule 6 this write is **not** wrapped in a `NO FORCE` window:
migrations connect as the bootstrap superuser, which bypasses `FORCE ROW LEVEL SECURITY` outright, so such a
wrapper would be a no-op that reads as a guard.

**D4 — Flat keys, not a nested object.** The consumer proposed `access: { … }`. Rejected on the naming
collision: `auth.access_method` is the **declared** gate and would sit one line from `access.authenticated_at`,
the instant that gate was passed. The recipient payload already publishes `outcome_recorded_at` flat, and the
envelope publishes `created_at` / `sent_at` / `voided_at` flat; these milestones are the same species. Agreed
with the consumer, who withdrew the container.

**D5 — Nothing orders the two subscribers, and nothing will be added to.** `first_opened_at` arrives via
`SigningSessionStarted` and `authenticated_at` via `AuthGatePassed`, on two independent at-least-once relays. A
reader may therefore observe `authenticated_at` set with `first_opened_at` still `null`. ⛔ **This is recorded as
a non-guarantee rather than repaired**: the consumer's reconciler already backfills earlier milestones from later
ones, and a synchronizing mechanism here would be machinery bought for a problem the only reader does not have.
Agreed explicitly with that consumer so neither side later assumes an order.

**D6 — Both stamps are the FIRST, and `access_method_executed` is frozen with them.** A recipient ejected into
`AWAITING_REAUTH` who passes the access gate again does not move `authenticated_at`, and therefore does not move
the method beside it: a signer who first entered with `ACCESS_CODE` and later re-authenticated with `OTP_SMS`
still publishes `ACCESS_CODE`. The field describes *that* moment, not the current state. "How they authenticated
most recently" is Evidence & Audit's question ([TASK-014](TASK-014-evidence-audit-projector.md)), not the read
model's.

**D7 — A contact correction does NOT clear these three fields, and the reason is that clearing would strand
them.** The tempting symmetry is `outcomeRecordedAt`, which `correctContact()` *does* clear so a corrected
recipient projects like one that never failed. It does not transfer. The signing session id is deterministic over
`(tenant, envelope, recipient)` and a contact correction changes **no** part of that triple, so the session row
survives the correction untouched, `startIfAbsent()` never inserts again, and `SigningSessionStarted` is never
re-emitted. A cleared column would therefore stay `null` **forever**, including after the corrected addressee
really opens their link — a value that actively lies, replacing one that is merely optimistic.

⚠ **The residual case is real and is accepted knowingly**: a mistyped address delivered to the wrong person who
opened it leaves *their* open recorded against the corrected recipient. The honest repair is for a correction to
reset the signing session, which is a materially larger decision and its own task (§7). It is written into the
method's docblock rather than left for someone to rediscover.

**D8 — The method is published as the catalog string, not as a derived boolean.** `access_method_executed`
carries the `AuthMethod` value. The consumer can derive *"identity was verified"* from
`!== 'DIRECT_LINK'` and can change that rule without a backend deploy; from a boolean they could recover nothing.
⚑ **Without this field `authenticated_at` would be near-worthless to them**, because under an open access gate
`SigningSession::start()` stamps `authenticatedAt = createdAt` with `DIRECT_LINK` — passing an open gate *is*
arriving with the link (ADR-0028) — so the two timestamps would be identical to the millisecond.

## 6. Verification

Properties, each with the tier that can actually observe it (authoring rule 4: name where the property lives and
check the harness goes there).

1. **P-first-open-is-once** — `Integration/`. Open a session; assert one `SIGNING_SESSION_STARTED` in
   `platform.event_log`. Open it four more times (reload, second device) and assert the count is **still one** and
   `created_at` unmoved. This is the property `startIfAbsent()`'s return value exists to produce.
2. **P-first-open-survives-redelivery** — `Unit/` on `Recipient::recordFirstOpened()`: a second call with a
   *later* instant returns `false` and leaves the stamp at the first. The relay is at-least-once; this is the
   guard that makes that safe.
3. **P-open-gate-stamps-direct-link** — `Integration/`, end to end across the crossing: a recipient behind an
   open access gate ends with `first_opened_at == authenticated_at` and `access_method_executed == 'DIRECT_LINK'`.
4. **P-declared-gate-separates-the-two** — `Integration/`: behind a declared `OTP_EMAIL` gate, the session opens
   `AUTH_PENDING` with `first_opened_at` stamped and `authenticated_at` **still null**; after the code is
   verified, `authenticated_at` is strictly later and the method is `OTP_EMAIL`. ⚑ **This is the discriminating
   case** — a fixture whose two timestamps always agree could not fail (authoring rule 4).
5. **P-reauth-does-not-move-the-stamp** — `Unit/`: `recordAuthenticated()` a second time, with a different
   method, returns `false` and moves neither field. Locks D6.
6. ⛔ **The backfill itself is NOT covered by a test, and that is stated rather than papered over.** A
   migration's data write is not reachable after the fact: by the time any test runs it has already executed, and
   re-typing its `UPDATE` into a test would assert the test's own SQL rather than the migration's. There is no
   precedent for testing one in this repo, and inventing a weak one here would read as coverage where there is
   none. **What IS guaranteed**: the lane migrates from an empty database on every run, so the statement parses
   and executes against the real schema — a mistyped column reddens — and the *meaning* of the value it writes is
   argued in the migration docblock against every aggregate state (authoring rule 6). The runtime half of D3 —
   that a `null` reaching the wire means *"has not opened"* — is locked by property 7 and by the crossing test.
   ⚠ **This is the one place a reviewer should push back if they disagree**, because it is a deliberate gap.
7. **P-payload-key-set-is-closed** — `Acceptance/`: assert the recipient object's **exact** key set, not merely
   that the three are present. ⚑ Authoring rule 5: PHPStan L9 rejects a missing key and accepts an extra one, so
   only a closed-set assertion can catch a field that should not be on this wire.

**Sabotage before trusting any of these** (authoring rule 4): revert `recordFirstOpened()`'s null check and watch
2 and 5 fail *for the right reason*; drop the backfill `UPDATE` and watch 6 fail naming the recipient; then
restore.

⛔ **Non-guarantee, asserted as such**: no test may assert an order between `SigningSessionStarted` and
`AuthGatePassed` arriving. Per D5 there is none, and a test that happened to observe one would lock a property
the system does not have.

⚑ **`ReactorConvergenceTest` censuses the reactor directory** and fails naming any subscriber missing from its
map, so the two new ones cannot land unclassified. That is the rule-5 shape working as intended; do not weaken it
to make them pass.

**Harness**: the worktree lane, which is the only one that validates this tree —
`WT_GATES="lint arch phpstan test" make -C ../f5sign-infra wt-backend src=$(pwd)`. The infra Makefile's plain
targets mount the **main** checkout and would report green for another branch.

## 7. Open follow-ups (track, don't solve here)

- **`notified_at` / delivery receipts.** `notification.notification_delivery` has **no timestamp column at all**
  — only `status`, `failure_reason` and `provider_reference` — and there is no `DeliverySent` contract event
  (only `DeliveryRequested` / `DeliveryFailed`). It needs a column, an event and a `PropagateDeliverySent` twin
  of the existing failure propagation. ⚠ And what it could publish is `SENT` — *handed to the transport* — not
  *delivered*: `DELIVERED`/`BOUNCED` remain unreachable while no channel has a receipt webhook.
- **A decline surface.** `RecipientOutcome::DECLINED` is modeled and **unreachable**: no route declines,
  and `SessionCompleted` carries no outcome. Until that exists, a `declined_reason` field has no value to carry.
- **`last_opened_at` / an open counter.** Deliberately refused here: `first_opened_at` is written at most once
  per recipient ever, whereas a last-open stamp writes on **every** open, putting a row lock and a log append on
  the signing app's reload path. Its home is the Evidence & Audit projector ([TASK-014](TASK-014-evidence-audit-projector.md)).
- **The open access gate passes without recording any fact.** `SigningSession::start()` sets `authenticatedAt`,
  `accessGatePassedAt` and `DIRECT_LINK` under an open gate but records no `AuthGatePassed`, so the event log has
  no trace of a gate that was genuinely passed. A real evidence gap, tracked as [`BL-185`](../BACKLOG.md); kept
  out of this task because changing an already-published event's semantics is a decision, not a slice. ⚑ This
  task retired the *mechanical* half of the original argument — `startIfAbsent()` now drains — so what is left is
  purely the semantic call.
- **A contact correction does not reset the signing session** (D7), which is what would let the access trace be
  cleared safely.

## 8. Deployment — the migration runs BEFORE the code, and the default is the other way round

⛔ **Do not take `f5sign-infra`'s default ordering for this one.** Migrations are not part of the deploy there
(`docker-compose.prod.yml` says they *"run outside this environment"*); they are a manual host step, and
`make migrate-prod`'s own `help` line reads: *"Orden por defecto: DESPUES de deploy-prod — … una migracion NO
aditiva se corre ANTES"*.

**The stated criterion mis-classifies this migration.** It is purely additive in DDL — three nullable columns —
so the default sends it after the deploy. But the criterion that actually matters is *does the new code depend on
it*, and this one does: `DoctrineEnvelopeReadRepository::loadRecipients()` names its columns explicitly in the
`SELECT`. Deploy the new backend first and every `GET /api/v1/envelopes/{id}` **fails outright** — an undefined
column, not a degraded payload — for the whole window until someone remembers the manual step. The dashboard's
`app:waybill:refresh-signatures` poller hits that route every ten minutes across all in-flight envelopes, so the
window is not quiet.

**Order: `make migrate-prod`, then `make deploy-prod`.** Safe in that direction precisely because the migration
is additive: run against the old code the three columns and their backfill are inert — nothing selects them,
nothing writes them.

### There is no separate "preprod", and knowing that makes the warning stronger

⚠ **This paragraph asserted the opposite until 2026-08-24 and the correction is the point.** It read *"whether
preprod runs migrations at all is not answerable from this repo"*, which took a **preprod environment** for
granted. There is none. `f5sign-infra` has three: `dev`, `test` and `prod` — one `docker-compose.prod.yml`, one
`.env.prod`. The word survives as a **tag convention**, stated in `.env.prod.example`: *"`develop` es mutable y
sigue la rama de desarrollo (lo normal en preprod); `vX.Y.Z` es inmutable (lo normal en prod)"*. So "preprod" is
the production stack running `BACKEND_TAG=develop`, not a fourth environment with its own migration practice.
⚑ The claim entered this record second-hand — the consuming repo's session reported test envelopes *"in
preprod"*, and it was written down without checking whether such an environment exists.

⛔ **So the ordering rule above is not conditional on anything.** Migrations are never part of a deploy on that
stack in any tag: `deploy-prod` is two lines, `pull` and `up -d`. Whichever machine carries `BACKEND_TAG=develop`
gets the new image and **no migration**, until somebody runs `make migrate-prod` by hand.

⚠ **And a mutable tag makes it worse rather than better.** A `vX.Y.Z` deploy is a deliberate act somebody
sequences; `develop` moves on its own as the branch advances, so the new image can arrive on a schema nobody has
migrated, with no human in the loop to remember the manual step. That is the window in which every
`GET /api/v1/envelopes/{id}` returns an undefined-column error.

### ⛔ Two different failures live here, and only the harmless one degrades gracefully

**Do not let the second bullet reassure you about the first.** They were conflated in this record's first
draft and the consuming repo separated them; the distinction decides how carefully a deploy has to be sequenced.

- **New code on an unmigrated schema — the one this section exists for.** `loadRecipients()` names columns that
  do not exist, so `GET /api/v1/envelopes/{id}` **fails outright**. There is no payload to read defensively:
  it is not an absent key, it is an absent response. Nothing on the consumer's side can soften this, and it is
  precisely the window a mutable `develop` tag opens without a human in the loop. ⚑ **What is lost is not the
  three new timestamps — it is the whole envelope read**, so signature progress stops being observed too. That
  is the real reason the migration goes first.
- **Old code, old schema — the harmless one.** The recipients are published without the three keys, the consumer
  reads them defensively, and an absent key means *"nothing to report"*. The poll completes; everything else on
  it survives.

⚑ **What holds in both is that a value is never wrong**: *"the fields do not exist"*, never *"they exist and
lie"* — the columns and their backfill land in the same `up()` (D3) and cannot be applied apart. And the
consumer's own degradation in the first case is honest rather than silent: per-envelope isolation with the
failure counted and logged, a `FAILURE` exit when every envelope fails, and the last persisted picture served
rather than a broken screen. Honest degradation is not coverage — the window is still a window.

## 9. What actually happened — deviations from §3, and the sabotage pass

**D-a — the reactor shape in §3.2 was wrong, and a census test caught it, not review.** The first build
had `OnSigningSessionStarted` dispatch **two** commands (one per milestone) and `OnAccessGatePassed`
filter to the access arm with an early `return`. Both violate
[`Kernel/Event/Reactor`](../../src/F5Sign/Kernel/Event/Reactor.php) commitment 3 — *"Reactor produces
**one** Command … multi-command reactions are saga shapes"* — and every one of the eight reactors
already in the tree is a single unconditional dispatch. `ReactorConvergenceTest` reddened on the count.

The repair moved both decisions inward, which is also where this codebase already keeps them:

- **One command carries both milestones.** `RecordRecipientFirstOpen` gained
  `?AuthMethod $accessMethodExecuted`, and `Envelope::recordRecipientFirstOpen()` decides which seals
  fire — so *"is an open also an authentication?"* is answered by the aggregate that owns both fields,
  not by a reactor.
- **The gate predicate moved to the use case.** `RecordRecipientAuthentication` carries `AuthGate`
  unfiltered and `RecordRecipientAuthenticationUseCase` refuses anything but `ACCESS`, exactly as
  [`PropagateDeliveryFailureUseCase`](../../src/F5Sign/Notification/Application/UseCase/PropagateDeliveryFailureUseCase.php)
  carries its three positive predicates. The reactor was renamed `OnAuthGatePassed`, because it no
  longer filters and the name should say which fact it translates.

⚑ **The predicate is not dead defence, and the reason is §5 D5.** A signing gate is only reachable
with a credential a passed access gate minted, so in wall-clock terms `ACCESS` always happens first —
but the two facts travel independent at-least-once relays with no ordering guarantee, so `SIGNING`
can be *delivered* first and would otherwise seal the signing method as the access method, on a field
written once for all time. That case is driven in
`RecordRecipientAuthenticationUseCaseTest::a_passed_signing_gate_stamps_nothing_even_when_it_arrives_first`.

**D-b — the event carries the executed method, not `accessGateWasOpen: bool`** (§3.1 records why).

**D-c — the sabotage pass, and what it turned up.** Four guards were reverted together and the suite
run; each failed naming the property it holds, and none masked another:

| Guard reverted | Test that reddened | Failure |
|---|---|---|
| `Recipient::recordFirstOpened()` seal-once | `RecipientTest::the_first_open_is_sealed_and_never_moves` | `true is false` on the changed-flag |
| `Recipient::recordAuthenticated()` seal-once | `…the_first_authentication_is_sealed_…` + `…a_later_reauthentication_writes_nothing…` | both arms |
| `startIfAbsent()` conditional drain | `RecipientAccessTraceCrossingTest::repeated_opens_…record_one_fact` | `actual size 5 matches expected size 1` — five opens, five facts |
| the `AuthGate::ACCESS` predicate | `…a_passed_signing_gate_stamps_nothing_even_when_it_arrives_first` | the wrong method sealed |

⚑ **The unconditional drain also reddened a test nobody wrote for this slice**, and it is the more
useful result: `ConcurrentSessionOpenTest::two_overlapping_opens_write_one_row_and_neither_fails`
already asserted the loser of a real race appends nothing. Its *message* had gone stale — it read
*"opening a session records no fact, so a losing open records none either"*, whose premise this task
made false — while the property it holds became **stronger**: it is now the concurrency half of the
once-per-recipient guarantee, and the half no single-threaded test can reach. Message corrected in
place; the assertion is unchanged.

**D-d — a rot fix that came out of the sweep, and it was wrong in the direction that keeps happening.**
`DbalSigningSessionRepository`'s class docblock said *"**Two** methods drain, not one"*. Adding this
task's drain site, the obvious edit was "three" — and `rg -n 'drainPendingEvents' src/F5Sign/Session/`
says **four**: `issueAuthChallenge()` drained already and had simply been missed, so the sentence was
wrong *before* this branch touched it. It now names all four and tells the next reader to count rather
than trust it. ⚑ The generator is worth noting: each drain site is added by the slice that needs it,
and that paragraph is never in that slice's diff — authoring rule 1's *"the diff is not the search
surface"*, one level up.

**D-e — a stale docblock removed from `SigningSession::start()`.** It carried two stacked docblocks,
the upper one a leftover reading *"the session opens already `AUTH_PASSED` and may sign immediately"*,
which the two-gate model had already made false. Deleted rather than corrected: the live docblock
below it says the same thing accurately. ⚑ Its neighbour on `rehydrate()` — *"Unlike `start()` it
records no fact"* — was false when written and is **true now**, so it was left alone.

**Not deviations, recorded so nobody goes looking:** `deptrac.yaml`, `phpstan.dist.neon` and
`phpstan-baseline.neon` are untouched, as the header's Decision-record field said they would be, and
`SchemaConformanceTest` needed no edit — its `BC_SCHEMAS` already names `envelope` and it iterates that
schema's tables, so the three new columns were covered the moment they landed.
