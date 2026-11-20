# TASK-036 — The claimable recipient slot, and the sender-side fill that names it once

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `feat/claimable-recipient-slot`** — `0008bc9` (the slice) · `da06f5d` (the missing Messenger handler + nine prose surfaces) · `2b98b5c` (the schema rows + two migration citations) · `ac20f13` (four §5 bars that were never written), over a merge of `origin/develop` at `a259389`. **2026-08-28, green under the harness §5 declares**: `make -C ../f5sign-infra wt-backend src=$(pwd)` at `ac20f13` gave lint `Found 0 of 1052`, deptrac `Violations 0`, PHPStan `[OK] No errors`, **`OK (2499 tests)`**, exit 0 — against `2460 tests` on the branch point. ⛔ **The assertion count is deliberately not pinned and no reader should add one**: three runs over identical trees here gave 12079 / 12081 and 11850 / 11851 / 11853, and `3cff138` is the commit whose whole purpose was to stop pinning it. **Pending review; not merged.** ⚑ **Amended 2026-08-28: seven further commits, and the first of them is a security fix rather than prose.** The list above stops at `ac20f13`; since then `b0c5eb5` closed ADR-0057 §2.5's **third door**, which was open — the activation fan-out was minting and mailing a live seven-day credential for an unclaimed slot authored with a contact (§8 *Scope*, and §5's bar-1 row, which that fix also placed) — followed by `d6f881e`, `013a758`, `0084d58`, `c65200f`, `0b84191` and `cd8947a`, all record corrections. **Lane green at `cd8947a`: `OK (2500 tests)`** — superseded by the `22328ad` run recorded at the end of this row, and kept as the reading that was current on 2026-08-28; the assertion count was, and stays, deliberately unpinned. ⚠ **What the green does not cover**, stated here rather than left to be inferred: `infection` **was** run on this branch, on 2026-08-28 after the four missing bars landed — `WT_GATES="infection"`, exit 0, **`Covered Code MSI: 85%`** and `MSI: 53%`, both over the configured floor (by 6.06 and 3.97 points). ⚠ **Both are lower than the last figure recorded in [`CLAUDE.md`](../../CLAUDE.md)** — 87% / 58%, measured 2026-08-19 — and **this branch does not attribute that drift to itself**: no infection run exists at its branch point, the tree moved a great deal between the two dates, and a delta with no baseline is not a finding. What the run does say is that the gate passes; what it does not say is which of §5's bars are strong, since covered-MSI is a whole-tree figure; and `Version20260828000001::down()` was exercised **after** that run, on a throwaway database, with the full `up → down → up` cycle green and the `DROP DEFAULT` surviving it (§8). **ADR-0057 stays `Proposed`** — see the `Decision record` row, and §8 for which of its conditions this branch moved. ⚑ **This field read *"Not started — forward plan, written 2026-08-25. Nothing here is built, and the check is one command: `rg -n 'declared_claimable\|claimedAt\|RecipientClaimed' src tests migrations config` returns **nothing** on `docs/claimable-recipient` at `49b8e3b`"*** — that command now returns matches in all four of `src`, `tests`, `migrations` and `config`. Every measurement in §2 was taken against `49b8e3b` on 2026-08-25 and is dated there; §2.5 and §2.8 carry corrections found on 2026-08-28.
⚑ **Re-dated 2026-09-01, and the green this row cited did not cover the branch.** It named the lane at
`cd8947a` (`OK (2500 tests)`), and **three commits touching `src/` landed after it** — `0802326` and
`c1c0516`, both behaviour fixes, plus `39014a4` — so nothing had validated the tip, including the commit
that introduced the two orphaned docblocks. A fix round then landed twelve more commits and a merge of
`origin/develop` at `5db1d28`. **Lane green at `22328ad`**, the merge commit: `lint 0 of 1058` ·
`Violations 0` · PHPStan `[OK] No errors` · **`OK (2547 tests)`**, run as `f5sign_app` against real RLS,
exit 0. ⛔ The assertion count stays unpinned (`3cff138`). What that round changed, in one line each:
`Recipient::guardClaimable()`'s two conditions had **no test at any tier** while §5 below said they were
proved at two; the replay convergence promised unconditionally in the published `#[OA\*]` was bounded by
time in the code, and the obvious fix in the entity left the HTTP path still answering `409` because the
Application layer asks its own early guard first; and the spec published that `locale` was not editable
while this task's own handoff asked the dashboard to send it. |
| **Type** | **Forward build.** A recipient may already be authored with no contact and sent that way ([ADR-0057](../adr/ADR-0057-claimable-recipient-slot.md) §1); what does not exist is any way to *say* that was deliberate, and any way to fill it afterwards. This adds the declaration, the fill, and the four refusals that keep the fill small. |
| **Why** | The eCMR consignee is not known when the waybill is authored and sent. Today [`Envelope::addRecipient()`](../../src/F5Sign/Envelope/Domain/Aggregate/Envelope.php) opens with `guardDraft()`, so the roster closes at `send()` and **no sender-side write names a party afterwards** — the three that exist (`correctContact()`, `resetAccessCode()`, `unlockAuth()`) all adjust a party already named. The request therefore arrives as *"let us edit the recipient after sending"*, and the cheapest place to put it is `correctContact()`, which already has a route, a command, a handler and a controller — and a docblock saying in terms that it *"changes where a party is reached, never who they are"*. This task builds the right door before somebody finds the cheap one. |
| **Builds on** | Reused unchanged: [ADR-0048](../adr/ADR-0048-route-declared-authentication-seam.md)'s route-declared credential kind (§2.2 is one line of `defaults()`); [ADR-0047](../adr/ADR-0047-declared-subject-on-machine-requests.md)'s `DeclaredSubject` grammar and its reserved `f5s:none`; [TASK-023](TASK-023-sms-codes-and-recipient-phone.md)'s `DeclaredMethodDestinations` and `PhoneNumber`; [TASK-025](TASK-025-recipient-delivery-failure-and-correction.md)'s recipient sub-resource shape, its `RecipientCorrected` payload precedent and its `RecipientNotCorrectableException` code discipline; [TASK-034](TASK-034-recipient-access-trace.md)'s migration and seal-once idioms; [ADR-0054](../adr/ADR-0054-ordered-auth-method-list.md)'s every-member-of-both-slots rule. |
| **Scope** | ⚑ **Out, and they are the sibling's**: ADR-0057 §2.7 (the claim's notification occasion, its cause token, the not-yet-activated guard and the `declared claimable AND still unclaimed` fan-out exclusion) and §2.11's **read-model field** — `EnvelopeJsonPresenter`, the envelope read route's `#[OA\*]` schema and the `docs/frontend-handoff/` note. **Falsifier:** if this task's diff touches `EnvelopeJsonPresenter`, `docs/frontend-handoff/` or `NotifyActivatedStepRecipientsUseCase`, the boundary is wrong. ⚑ **2026-08-28: it fired on two of those three, and this row is kept as the assignment rather than rewritten as the outcome.** `EnvelopeJsonPresenter` is untouched; the handoff note and `NotifyActivatedStepRecipientsUseCase` are both in the diff, the second deliberately, for a live credential leak. **Read §8 *Scope* before acting on this falsifier** — it classifies each firing, and the fan-out exclusion of §2.7 is no longer TASK-037's to build. |
| **Decision record** | [ADR-0057](../adr/ADR-0057-claimable-recipient-slot.md), **`Proposed`** — and this task **must not promote it**, which still holds with the branch green. It realizes ten of its seventeen clauses, plus §2.7's fan-out exclusion; the rest of §2.7 — the claim's own notification occasion, its cause token and the not-yet-activated guard — and §2.11's read-model field stay unbuilt until TASK-037 lands, and §5 bars **7 and 12** cannot be reached from here (§5 below says why for each). Promotion to `Accepted` needs those clauses built and those **two** bars placed. ⚑ **Corrected 2026-09-01.** This row said *"§2.7 and §2.11 stay unbuilt … §5 bars **1**, 7 and 12 … those **three** bars placed"*, and its own §5 *Bars this task cannot place* has read **"(1) PLACED after all, on 2026-08-28"** since `b0c5eb5` — the fan-out exclusion was built here, so the bar it needed became placeable and cheap. The header table was the surface nobody re-read; ADR-0057 §5 and its README row agree that two are outstanding. ⚑ **Corrected 2026-08-28.** This row carried a third condition — *"and this record's own §4 D2 folded back into ADR-0057 §2.5 — whose sizing is wrong in a way that matters (§4 D2)"* — and it is discharged in the **opposite** direction from the one it anticipated: ADR-0057 §2.5 was itself re-cut by `9087e31` on 2026-08-25, and what shipped follows the ADR while **§4 D2 below is the half that was superseded**. Nothing is owed to §2.5 from here. |
| **Delivery bar** | A sender authors a recipient declaring `OTP_EMAIL` and **no contact**, marks it claimable, sends the envelope, and gets a 422 for the same recipient without the declaration. Nothing mints a signing token for that slot, from any of the three doors. A later `POST /api/v1/envelopes/{id}/recipients/{recipientId}/claim` names the party, and a second one is refused with the slot still naming the first. An identical replay of the first is indistinguishable from it. |
| **Deployment** | ⛔ **Migration first, deploy second — the inverse of `f5sign-infra`'s default**, and for the reason [TASK-034](TASK-034-recipient-access-trace.md) §8 sets out unchanged: the DDL is additive, so the default sends it after the deploy, but `DoctrineEnvelopeReadRepository::loadRecipients()` will name both new columns in its `SELECT`, so new code on the old schema fails `GET /api/v1/envelopes/{id}` **outright**. What is lost in that window is the whole envelope read, not two fields. Nothing runs the migration for you on any tag. |
| **Sibling** | ⚑ [**TASK-037**](TASK-037-claimable-invitation-and-visibility.md), authored alongside this record. It owns ADR-0057 §2.7 and §2.11. The two must not be scoped independently: §2.7's exclusion and §2.11's projection both read **both** of this task's flags, and neither can be built before the flags exist. |
| **Sequencing** | **This task is first; TASK-037 follows it.** The order is forced rather than preferred: §2.7 excludes an unclaimed slot from a fan-out and §2.11 reports it in a read model, and **there is nothing to exclude or report until the slot exists**. Building them in the other order gives both a predicate with no column to read, which resolves by inference from an absent contact — precisely the shape ADR-0057 §7.2 rejects, and the one that then never gets un-inferred. There is also a concrete handoff: TASK-037's occasion needs a cause token, and §4 D7 records that `RecipientClaimed` needs no ordinal *because* §2.4 makes the claim happen once. That is an input to the sibling, not a coincidence. |

---

## 1. Why this task exists

The state this feature needs already exists, and that is the trap rather than the opening. `$email`, `$phone`
and `$fullName` are all nullable on [`Recipient`](../../src/F5Sign/Envelope/Domain/Entity/Recipient.php), and
`ensurePreSendInvariants()` requires documents, steps, a recipient per step, every signer assigned and every
recipient seeing something — and **no contact of any kind**. So an envelope carrying an identity-less
recipient is already authorable and already sendable. It is simply inert: nothing invites that recipient,
nothing can, and nothing anywhere says whether the emptiness was deliberate. **A sender who forgot a field
and a sender who deliberately left a slot open produce byte-identical rows.**

Three consequences follow, and each is a separate piece of this task:

- **Nothing can tell the two apart**, so any behaviour keyed on the emptiness works by coincidence and stops
  working the moment somebody sets a contact for an unrelated reason, with nothing red anywhere
  ([`CLAUDE.md`](../../CLAUDE.md) authoring rule 5). Hence §2.1's *declaration*.
- **Nothing can fill it.** `guardDraft()` closes the roster at `send()`. Hence §2.2's route.
- **Nothing stops a link being issued over it.** `MintSigningTokenController` mints for the
  `(envelope_id, recipient_id)` pair it is handed with no existence check and no status check — the write
  half of [`BL-61`](../BACKLOG.md) — so a session can open over a slot nobody has claimed and the whole of
  §2.4's once-only argument would rest on nobody having tried. Hence §2.5's refusal.
  ⚑ **Tense corrected 2026-08-28.** That measurement was `49b8e3b`'s and the bullet was written in the
  present. `BL-61` has since been **Closed** — its pre-send direction on 2026-08-25 by TASK-035 / ADR-0058,
  its terminal direction on 2026-08-28 by [TASK-038](TASK-038-terminal-envelope-closes-the-ceremony.md) /
  [ADR-0059](../adr/ADR-0059-terminal-envelope-closes-the-ceremony.md) — and the controller no longer mints
  unguarded: it routes through `SigningTokenIssuance`, which refuses an unsent envelope. **The argument
  below is unaffected**, because neither of those predicates asks whether the recipient is a slot nobody
  has claimed.

⛔ **This is not a repair of BL-61 and must not be written as one.** BL-61 was the general defect: a ceremony
runs over an envelope whose status nothing checks. §2.5 refuses one specific, newly-created state that BL-61
did not describe. Closing BL-61 did not discharge this, and this does not reopen it.

## 2. What already exists (reuse, do not rebuild)

Measured against `49b8e3b` on 2026-08-25. Everything below is in the tree; none of it is to be rebuilt.

### 2.1 The authoring path, and the two doors it closes

- [`Envelope::addRecipient()`](../../src/F5Sign/Envelope/Domain/Aggregate/Envelope.php) opens with
  `guardDraft()` (`status !== DRAFT` → `EnvelopeStateException::notDraft()`), then requires the step ordinal to
  exist, then calls `Recipient::create()` and stores into `$this->recipients` **keyed by id with no existence
  check** — a replayed add overwrites, which `Recipient::locale()`'s docblock records as `BL-69`'s and
  explicitly forbids papering over with a private guard.
- `Envelope::ensurePreSendInvariants()` (private, called from `send()`) checks documents, artifacts, steps,
  a recipient per step, `ensureEverySignerIsAssigned()`, `ensureEveryRecipientSeesSomething()`,
  `ensureEveryFieldIsPlaced()`. **No contact check of any kind.** So §2.1's *"`send()` accepts an unclaimed
  slot"* needs **no change here** — it already does, for every recipient, declared or not. What this task adds
  is not permission but *legibility*.

### 2.2 `Recipient`'s nullable contact fields, and `correctContact()` — the wrong home, already reasoned

- `Recipient::$email` is a plain `?string`; `$phone` is a `?PhoneNumber` value object (the asymmetry is
  TASK-023 §7 D2's, not half-done work); `$fullName` is `?string`. All three are nullable at authoring.
- `Recipient::correctContact(?string $email, ?PhoneNumber $phone, DateTimeImmutable $now): int` guards
  `outcome->isTerminal()` → `RecipientNotCorrectableException::legAlreadyClosed()`, then
  `correctionsMade >= MAX_CORRECTIONS` (3) → `::budgetExhausted()`, then applies **`null` = leave this one
  alone**, resets `outcome` to `PENDING`, clears `outcomeRecordedAt`, increments the counter and returns it.
- Its aggregate caller `Envelope::correctRecipientContact()` adds two guards the entity does not have —
  envelope terminal, and `sentAt === null` — and records `RecipientCorrected`.
- ⛔ The **access trace is deliberately not cleared** by a correction, and that method's docblock argues why.
  Nothing in this task disturbs that.

⚑ **The line this task has to move is written down in `Recipient::locale()`'s docblock**: *"The correction is
deliberately a **contact** patch and nothing wider — it changes where a party is reached, never who they are
or what they were asked to do."* That sentence is why the claim is a separate operation, and it is also one of
the prose surfaces this task must correct (§7).

### 2.3 `DeclaredMethodDestinations` and its two injection sites

[`DeclaredMethodDestinations`](../../src/F5Sign/Envelope/Application/Service/DeclaredMethodDestinations.php)
answers *can this recipient be reached by every method declared on them*, over **every member of both slots**
in declaration order, reading `AuthMethod::requiredDestination()` (`EMAIL_ADDRESS` / `MOBILE_PHONE` / `PHONE`,
`null` for the rest) and refusing with `RecipientCannotReceiveMethodException::forSlot()` → 422. Its `match`
over `RequiredDestination` has no `default`, deliberately.

Its two call sites differ in **when** they run, and the difference is load-bearing:

- `AddRecipientUseCase::execute()` calls it **before** `findLockedForUpdate()`, so a refused declaration takes
  no row lock and a 422 beats a 404 on an unknown envelope.
- `CorrectRecipientUseCase::execute()` calls it **after** the load, on the state the write *will* leave
  behind (`$command->email ?? $recipient->email()`), because a correction cannot remove a contact but can
  replace a mobile with a landline — the door that reopens [`BL-162`](../BACKLOG.md) after the authoring guard
  closed it. It runs **before** the mutation so a refused correction spends none of the budget.

`DeclaredMethodDestinationsTest::a_later_member_with_nowhere_to_deliver_is_refused_even_when_the_head_is_fine`
is the twin fixture ADR-0057 §5 bar 3 asks this task to copy.

### 2.4 `DeclaredSubject`, validated centrally and then discarded

[`DeclaredSubject`](../../src/F5Sign/Foundation/Actor/DeclaredSubject.php) carries `RESERVED_PREFIX = 'f5s:'`,
`NONE = 'f5s:none'`, `MAX_LENGTH = 128` and `isNone()`.
`TenantRequestListener::requireDeclaredSubject()` reads the `F5Sign-Declared-Subject` header on every route
whose `Authn` kind `requiresDeclaredSubject()`, refuses an absent one with a 400, calls
`DeclaredSubject::fromString($value)` for grammar — and **throws the value away**. Its own docblock says so
and forbids simplifying the call out: *"nothing consumes the value yet"*, deliberately, per ADR-0047 part 5.

⚑ **Consequence for §2.6, and it is why that clause costs more than it reads.** The listener **accepts**
`f5s:none` — it is the documented legal reserved value — and carries nothing forward. So the claim route's
refusal cannot be a downstream check on a parsed object: the controller must read the same header off the
request itself. That makes this the **first route-specific rule about the declared subject** in the repo, with
no precedent to copy, and §4 D8 records the shape.

### 2.5 `SigningTokenIssuer`, and its three production callers

[`SigningTokenIssuer`](../../src/F5Sign/Session/Contract/Service/SigningTokenIssuer.php) is a
`Session/Contract/Service/` port with one method —
`issueFor(string $tenantId, string $envelopeId, string $recipientId): IssuedSigningToken`. Its own docblock
is explicit about what it is not: *"a storage seam,
not a domain guard … It does not check that the recipient belongs to the envelope, that the envelope is in a
state that admits signing … **Do not read a successful issuance as an authorization.**"*

The three production callers, enumerated by `rg -n 'SigningTokenIssuer' src/` and confirmed by hand:

| Caller | Layer | Grants it holds |
|---|---|---|
| `Session\Application\Service\SigningTokenIssuance` | `SessionApplication` | `SessionContract`, `EnvelopeContract` |
| `Notification\Application\UseCase\NotifyActivatedStepRecipientsUseCase` | `NotificationApplication` | `EnvelopeContract`, `SessionContract` — **not** `SessionApplication` |
| `Notification\Application\UseCase\NotifyCorrectedRecipientUseCase` | `NotificationApplication` | same |

⚑ **Corrected 2026-08-28.** The first row read `Session\UI\Http\MintSigningTokenController` / `SessionUI` /
*"`SessionContract`, `SessionApplication` — **not** `EnvelopeContract`"*, and it was false when written: the
controller has injected `SigningTokenIssuance` since
[ADR-0058](../adr/ADR-0058-signature-requires-a-readable-envelope.md), and the only place it names the port
is a docblock. Re-derive with `rg -n 'SigningTokenIssuer' src/` and read the **constructor** lines, not the
`{@see}` ones — three of the hits are prose. ADR-0057 §2.5 already carries this correction; **§4 D2 below
was reasoned from the wrong membership and is superseded** (see the banner there).

The sole implementation is
`Session\Infrastructure\Persistence\Doctrine\StoreBackedSigningTokenIssuer` (`SessionInfrastructure`, which
holds `SessionApplication` **and** `EnvelopeContract`), aliased in `config/services.yaml`. It executes one
statement — `SELECT session.issue_signing_token(...)` — because `f5sign_app` holds `EXECUTE` on that function
and **no privilege at all** on `session.signing_token` ([`docs/LOAD-BEARING.md`](../LOAD-BEARING.md) §1.14).

### 2.6 `RecipientCorrected` — the payload precedent; `Recipient::assign()` — the replay template

- [`RecipientCorrected`](../../src/F5Sign/Envelope/Contract/Event/RecipientCorrected.php) publishes exactly
  five keys — `envelope_id`, `recipient_id`, `step_ordinal`, `correction_ordinal`, `occurred_at` — and **no
  contact of any kind**. Its docblock states the reason: the corrected contact is PII, the consumer re-reads
  it through the RLS-scoped `EnvelopeQueryInterface`, and putting it on the wire would copy it into
  `platform.event_log` for ever. It uses the `DeclaredEventType` / `OccurredAtAccessor` /
  `OrderedByOccurredAt` / `StreamsUnderSubject` traits and `Row` for `fromPayload()`.
- `Recipient::assign()` is the fully-worked replay answer [`BL-69`](../BACKLOG.md) names as the template:
  an identical re-declaration **returns the existing row**, a divergent one throws naming *which half*
  differed — `DocumentAssignmentConflictException::grantsDiffer()` / `::placementsDiffer()`.
- `Recipient::markDeliveryFailed()`, `::recordAuthHardLock()`, `::recordFirstOpened()` and
  `::recordAuthenticated()` are the seal-once/converge idiom: return `bool` for *did anything change*.

### 2.7 The recipient sub-resource routes

[`config/routes/api/envelope.php`](../../config/routes/api/envelope.php) declares every route with
`Authn::MACHINE_KEY` and carries a **hand-maintained "Full paths" list in its header** that a new route
appends one line to. Four sub-resources already nest under a recipient, and the file header explains the shape
of each:

- `…/recipients/{recipientId}/corrections` — a POSTed **collection of recorded facts**, bounded to three, the
  only route requiring the envelope to have been sent.
- `…/access-code` — singular, POSTed because the value is server-minted and appears once.
- `…/auth-unlock` — a **verb sub-resource** *"like `send` and `void` — a state change with nothing to name"*.
- `…/signing-assignments` — a collection whose parent is the recipient rather than the envelope.

`CorrectRecipientController` is the shape to copy for a UI-layer translation: constructor of `CommandBus`,
`Clock`, `PrincipalContext`, `PhoneNumberParser`; `#[MapRequestPayload]` request DTO; `204 No Content`; and
409s carrying a `code` (`RECIPIENT_LEG_CLOSED`, `RECIPIENT_CORRECTION_BUDGET_EXHAUSTED`) because *"a client
retrying blindly wastes a call on the first and can never succeed on the second"*.

### 2.8 The persistence and schema substrate

- `envelope.recipient` carries `ENABLE` + `FORCE ROW LEVEL SECURITY`, its `current_tenant_id()` isolation
  policy and its `BEFORE INSERT` tenant stamp since `Version20260713000002`'s `tenantStamp('recipient')`.
  **New columns inherit all of it.** ⚑ **Corrected 2026-08-28**: this said *"since `Version20260721000001`"*.
  That migration is the **Notification** BC baseline and contains **zero** `envelope.*` statements, so it
  could not have applied any of the four. The conclusion drawn from it is unaffected — the wrong id was
  attached to a true guarantee, which is authoring rule 2's shape and rots independently of it. The same
  mis-citation was live in `Version20260820000002`'s docblock and is fixed on this branch (`2b98b5c`); this
  record is the third member of that family.
- Grants are **table-level, never column-level**: `Version20260713000002` issues
  `GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA envelope` plus
  `ALTER DEFAULT PRIVILEGES … GRANT … ON TABLES`. **A new column needs no grant.**
- Two migration precedents, and they answer opposite halves of §4 D1:
  `Version20260818000001` (`corrections_made`) is `ADD COLUMN … NOT NULL DEFAULT 0` then
  `ALTER COLUMN … DROP DEFAULT` — the default backfills, the drop satisfies
  [ADR-0019](../adr/ADR-0019-database-schema-conventions.md) §4, and
  `SchemaConformanceTest::domain_columns_carry_no_database_default` fails if the drop is left out.
  [`Version20260824000001`](../../migrations/Version20260824000001.php) (the access trace) is the docblock
  shape to copy: what a backfilled row means in each aggregate state, why there is no status predicate, why
  the write is **not** wrapped in a `NO FORCE` window, and why there is no index.
- ⛔ **The hydration trap is documented on the entity and has bitten here.** `save()` upserts **every**
  recipient row on **every** authoring command, so a field dropped from `Recipient::rehydrate()` is written
  back as its default by the next unrelated `AddStep`. `authRequirement`'s own comment calls this *"the entry
  with the worst failure mode on the entity"* — the gate does not become wrong, it disappears. Both new
  fields must be carried through `create()`, `rehydrate()`, `DbalEnvelopeRepository` and
  `DoctrineEnvelopeReadRepository`, and §5 has a bar for exactly that.

### 2.9 The deptrac position — measured, not assumed

Read out of [`deptrac.yaml`](../../deptrac.yaml) on 2026-08-25:

| Layer | Holds `EnvelopeContract`? | Holds `SessionApplication`? |
|---|---|---|
| `SessionUI` | **no** | yes |
| `SessionApplication` | **yes** | — |
| `SessionInfrastructure` | **yes** | **yes** |
| `NotificationApplication` | yes | **no** |

`Session\Application\Query\RecipientAuthContextReader` is the live precedent for a Session Application class
reading across the boundary: it injects `EnvelopeQueryInterface` and calls
`getContextForRecipient(GetEnvelopeContextForRecipient)`, whose `RecipientEnvelopeContextView` carries
`RecipientView $recipient` in full. ⚑ **So §2.5's cross-BC read needs no new method on
`EnvelopeQueryInterface`** — once `RecipientView` carries the two fields (which this task does anyway, §3),
the existing query already answers. That matters: `EnvelopeQueryInterface` is a published cross-BC Contract
port and widening it would be an [ADR-0004](../adr/ADR-0004-cross-bc-anti-corruption-layer.md) change.

## 3. Scope

**In.**

- **The declaration** — `Recipient` gains the permanent claimable flag and the mutable claim instant, carried
  through `create()`, `rehydrate()`, both persistence mappings and `RecipientView`; `Envelope::addRecipient()`,
  `AddRecipient`, `AddRecipientRequest` (+ its `#[OA\*]` property) and `AddRecipientUseCase` gain the
  declaration.
- **One migration** — two columns on `envelope.recipient`, per §4 D1.
- **The predicate** — a single accessor on `Recipient` answering *is this an unclaimed slot*, reading **both**
  terms, and the only thing any caller asks.
- **The claim** — `Recipient::claim()`, `Envelope::claimRecipient()` (guards per §2.12 + §2.4 + §2.15),
  `ClaimRecipient` command under `Application/Command/Lifecycle/`, `ClaimRecipientUseCase` under
  `Application/UseCase/Lifecycle/`, `ClaimRecipientController` + `ClaimRecipientRequest`, and one route with
  its line in the route file's header list.
- **`RecipientClaimed`** in `Envelope/Contract/Event/`, four keys (§4 D7).
- **The three refusals** — `correctContact()` on an unclaimed slot (§4 D3); a second or divergent claim
  (§4 D4); a mint for an unclaimed slot, at the seam §4 D2 establishes.
- **The destination-guard deferral** at `AddRecipientUseCase`, and its re-run in `ClaimRecipientUseCase`
  (§4 D6).
- **The four prose surfaces** §7 enumerates — three dated `docs/ddd/` banners and one docblock pointer, plus
  the `Recipient::locale()` correction §7 names.
- The tests §5 names.

**⚠ In, and not in the assignment — flagged rather than smuggled.** ADR-0057 **§2.12** (a claim is refused
once the named party could no longer act) was assigned to neither this record nor TASK-037. It is taken here
because it is not separable: it is a precondition of the claim command, there is no other operation it could
attach to, and shipping the route without it means naming an addressee on a **voided** envelope — the one
state §2.12 records as reachable today. §5 places its bar. If the split was deliberate, this is the paragraph
to overrule.

**Out.**

- **ADR-0057 §2.7 in full** — the claim's notification occasion, its cause token, the not-yet-activated guard
  it must copy from `NotifyCorrectedRecipientUseCase`, and the `declared claimable AND still unclaimed`
  exclusion in `NotifyActivatedStepRecipientsUseCase`.
  [**TASK-037's**](TASK-037-claimable-invitation-and-visibility.md).
- **ADR-0057 §2.11's read-model field** — `EnvelopeJsonPresenter`, the envelope read route's `#[OA\*]` schema,
  and the `docs/frontend-handoff/` note the additive contract change owes. **TASK-037's.** `RecipientView`
  carrying the values is *this* task's, because the entity's fact must round-trip persistence to work at all;
  publishing them on the wire is the sibling's.
- **§2.9 self-claim, §2.10 in-person, §2.17 certified delivery** — named exclusions in the ADR; nothing to
  build. §6 carries what would admit each.
- **BL-61**, **BL-173**, **BL-192**, and the `DefaultChannelSelector` `SMS`-arm rot ADR-0057 §2.7 records —
  the last belongs to the changeset that touches that file, which is TASK-037's.
- **Re-assignment**, and editing `fullName` / `role` / `locale` on a party already named. §2.4 defers them as
  **one** question; §6 carries it.
- Any change to `deptrac.yaml`, `phpstan.dist.neon` or `phpstan-baseline.neon`. §4 D2 exists precisely so that
  none is needed; if the diff touches one, that decision is wrong.

## 4. Key decisions

### D1 — The migration: two columns, and what a backfilled row means on every state it lands on

⛔ **ADR-0057 mentions no migration anywhere.** This is the gap the ADR leaves and the one place this task
can do permanent damage, so it is argued here in full and the argument is restated in the migration's own
docblock (authoring rule 1 names migration docblocks as the highest-value rotting surface).

**The shape.**

```
ALTER TABLE envelope.recipient
    ADD COLUMN declared_claimable BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN claimed_at         TIMESTAMPTZ;
ALTER TABLE envelope.recipient ALTER COLUMN declared_claimable DROP DEFAULT;
```

**Why a nullable instant and not a second boolean.** The mutable fact could be an `unclaimed BOOLEAN NOT
NULL`. It must not be, for three reasons and the third is the one that decides it:

1. Every *has this happened yet* fact in these schemas is a nullable instant — `sent_at`, `voided_at`,
   `outcome_recorded_at`, `first_opened_at`, `activated_at`. A boolean would be the only one.
2. §2.15 requires an identical replay to return **the existing claim**. A claim with an instant is a recorded
   thing that can be returned; a flipped bit is not.
3. ⛑ **It makes the single-flag collapse structurally impossible.** *Unclaimed* is
   `declared_claimable AND claimed_at IS NULL` — **a conjunction, not a column** — so there is no field an
   implementer can key a predicate on by accident. That is what ADR-0057 §3.3 calls *"the thing most likely to
   be built as one flag"*, and the asymmetry is worth spelling out: keying on `claimed_at IS NULL` alone mutes
   **every ordinary recipient** and dies on the first fixture, while keying on `declared_claimable` alone
   mutes only **claimed** slots — for ever, silently, and invisibly to any fixture built from an unclaimed
   one. The dangerous single flag is the permanent one, which is why the conjunction is published as one
   accessor on `Recipient` and the raw columns are never read by a caller.

**⛔ The trap, stated before the answer: a recipient authored before this exists was never unclaimed.** It was
**named at authoring**. Writing the *unclaimed* term `true` for those rows would record a false history —
a backfilled row is indistinguishable from an authored one (authoring rule 6's first sentence), so every
pre-existing recipient would read as a slot the sender deliberately shipped empty, which is not what happened
and which the envelope's audit record would then assert for ever. And it would be **unrepairable through the
API**: there is no route that clears the flag, and the claim itself is once-only and demands a name, so a
sender could not fix it. Every live envelope would become unsendable and unrepairable — the exact shape of the
finding [TASK-025](TASK-025-recipient-delivery-failure-and-correction.md) shipped and had to withdraw.

**What each backfilled value means, per aggregate state — write side as well as read side** (authoring
rule 6):

`declared_claimable = false` is not an assertion about the recipient's *state*; it is an assertion about the
**authoring vocabulary**: *nobody declared this slot claimable* — and nobody could have, because the
declaration did not exist when the row was written. That is a fact, not an invention, exactly as
`corrections_made = 0` was and unlike the `locale` backfill `Version20260817000001` deliberately did **not**
write. `claimed_at = NULL` is *no claim has occurred*, which is likewise true of every row.

| State the row lands on | What `(false, NULL)` means there | Write side |
|---|---|---|
| **DRAFT** | Nothing was declared and nothing was claimed. | `addRecipient()` still refuses nothing new; the destination guard runs unchanged (§4 D6 keys its skip on the declaration alone). |
| **SENT, in flight** | An ordinary named recipient. | Mint, invitation and correction all proceed exactly as today — the conjunction is `false`, so §2.3's, §2.5's and §2.7's refusals never see them. This is the population the false-history backfill would have destroyed. |
| **Recipient terminal** (COMPLETED / DECLINED / DELEGATED / SKIPPED) | Same, and never read: the leg-closed guard fires first on the correction path, and a terminal leg has no ceremony to mint for. | Inert. |
| **Envelope terminal** (COMPLETED / VOIDED / EXPIRED) | Same, and never read: §2.12's guard and the existing envelope-terminal guards refuse before reaching either column. | Inert. |
| **DELIVERY_FAILED** | An ordinary named recipient whose invitation bounced. Correction remains available, which is the whole point of that state. | Unchanged — and this is the row that would have been *permanently* unrepairable under the false backfill, since its only recovery is the correction §2.3 would then refuse. |

⚑ **There is deliberately no status predicate**, and per authoring rule 6 that is stated as the property
rather than as a list: a predicate is owed when a backfilled value would be *wrong* in some state, and there
is no state in which *"nobody declared this claimable"* is wrong. A `WHERE sent_at IS NOT NULL` guard here
would be decoration a later reader mistakes for a rule — the same conclusion `Version20260824000001` reached
and for the same reason.

**No CHECK.** The unreachable fourth combination `(declared_claimable = false, claimed_at IS NOT NULL)` is
tempting to forbid in the schema. It must not be: *only a declared slot may be claimed* is a state-transition
legality rule with business meaning, and [ADR-0019](../adr/ADR-0019-database-schema-conventions.md) §7 admits
only *"universal, business-meaning-free data-sanity guards"* — its own test is *could it change as the
business evolves?*, and this one changes the day re-assignment lands. The invariant is the aggregate's; §5
asserts it there instead.

**No index, and the predicate that would earn one.** Both columns are projected with the recipient row that
is already fetched by `envelope_id`; nothing filters or sorts on them today. The query that *would* earn
`(declared_claimable, claimed_at)` is a cross-envelope *"which envelopes are waiting on a claim"* listing —
which is ADR-0057 §2.11's *visible wait*, and whose home is
[TASK-037](TASK-037-claimable-invitation-and-visibility.md). It does not exist. Recorded so the next slice
adds it deliberately rather than this one adding it defensively.

⚑ **Corrected 2026-08-28.** That sentence attributed the listing to *"§2.11's neighbourhood and
[`BL-192`](../BACKLOG.md)'s"*. `BL-192` is the **release** capability — taking a party out of a step's
required set without voiding the envelope — which is a step-completion question and earns no index on these
two columns. ⛔ **This paragraph is the *source* `Version20260828000001`'s docblock was copied from**, and the
copy was corrected on 2026-08-28 while the original was not — the mis-citation reached the migration by being
copied out of here, and a reader who checks the migration finds it right and a reader who checks the plan
finds it wrong. That is authoring rule 1's *convert one file at a time, completely* failing in the direction
nobody checks: the file with the **empty diff** is the one that started it.

**No RLS and no grant work**, and the reason is §2.8: the table already forces RLS with its tenant policy and
the schema grant is table-level with `ALTER DEFAULT PRIVILEGES` behind it. ⛔ **This migration is not wrapped
in a `NO FORCE ROW LEVEL SECURITY` window and must never be** — migrations connect as the bootstrap
superuser, which bypasses `FORCE` outright in every environment including production
([`docs/LOAD-BEARING.md`](../LOAD-BEARING.md) §1.7), so such a wrapper is a no-op that reads as a guard.

**`down()` is reversible and lossy, and that is stated rather than glossed.** Dropping the columns discards
authored facts — which slots a sender declared, and when each was filled — and unlike
`Version20260824000001`'s backfill there is **no source to reproduce them from**: nothing else in the system
records either. Reversible in the schema sense, destructive in the data sense, exactly as
`Version20260818000001`'s `down()` is.

### D2 — ⛔ The mint refusal's seam, and ADR-0057 §2.5 sizes it wrongly in a way that matters

> ⛔ **SUPERSEDED 2026-08-28 — do not build what this decision prescribes.** The paragraphs below are kept
> as the record of what was reasoned on 2026-08-25 and why it did not survive; **what shipped is the term
> inside [`SigningTokenIssuance::issueFor()`](../../src/F5Sign/Session/Application/Service/SigningTokenIssuance.php),
> beside its `sentAt` refusal, and there is no decorator anywhere on this branch.**
>
> **What moved.** D2 concluded *"the enforcement is a decorator in `Session/Infrastructure/` implementing
> `SigningTokenIssuer`, wrapping `StoreBackedSigningTokenIssuer`, re-aliased at the existing
> `config/services.yaml` alias"*, and it reached that from §2.5's own sizing plus the caller table in §2.9 —
> whose first row was **wrong** (§2.5 above). ADR-0057 §2.5 was then re-cut by `9087e31` on 2026-08-25
> (*"six corrections the merge made necessary"*) to say the opposite in bold: *"The term goes inside
> `SigningTokenIssuance` … and NOT on the port."* Its reason is not deptrac's — it is **accepted**
> [ADR-0058](../adr/ADR-0058-signature-requires-a-readable-envelope.md) §2.3, which refuses to bind the port
> because that binds **every** caller, and answers *"who catches the fourth minting site"* with the
> `ISSUER_CALLERS` census instead. What shipped follows the ADR.
>
> **The measurement, because it is the evidence and not a preference** — same tree, three arms, taken while
> deciding:
>
> | Arm | `composer arch` | `SigningReadersRefuseUnsentEnvelopeTest` |
> |---|---|---|
> | baseline (no refusal) | Violations **0** | `OK (13 tests)` |
> | the decorator D2 prescribes | Violations **0** | **4 failures** |
> | the term inside `SigningTokenIssuance` | Violations **0** | `OK (13 tests)` — identical to baseline |
>
> ⚑ **Deptrac cannot separate the two compositions; the census can.** Both are layer-conformant, so the arch
> gate is green either way and D2's whole argument — that the seam question *is* deptrac's — could never have
> been settled by running it. What reddens is ADR-0058's caller census. That matters beyond this decision:
> §5's harness must not rest on deptrac alone for anything about where a guard sits, and §5 bar 6 is worded
> accordingly.
>
> ⚠ **The `honest cost` paragraph below is void rather than reworded**, and §6 drops it: the extra read it
> worries about **is not incurred**. `SigningTokenIssuance` was already reading envelope state to answer
> `sentAt`, so the slot term is a second question of a load already paid, not a new one.

ADR-0057 §2.5 gets the **conclusion** right — the refusal belongs on `SigningTokenIssuer` rather than on
`MintSigningTokenController`, because the issuer has three callers and a controller guard closes one of
three — and then sizes the work as *"a Session Application use case reading across the boundary through
`EnvelopeQueryInterface`, in the pattern `RecipientAuthContextReader` already sets."* **Those two sentences
are in tension, and the tension is deptrac's, not a matter of taste.** Measured (§2.9):

- `SessionUI` holds no `EnvelopeContract`, so the controller genuinely cannot do the check itself. ✅ The ADR
  is right about that half.
- `NotificationApplication` holds no `SessionApplication`, so **the two Notification callers cannot reach a
  Session Application use case at all.** A guard placed there is reachable only from the controller — which
  is precisely the one-of-three-doors shape §2.5 rejects, arrived at by following §2.5's own sizing.

**The only seam all three callers cross is the `SigningTokenIssuer` interface**, so the enforcement point must
be behind it. `SessionInfrastructure` holds both `SessionApplication` and `EnvelopeContract`, so the
conformant composition is two pieces and no deptrac edit:

1. **The predicate** is a `Session/Application/` service injecting `EnvelopeQueryInterface` and calling
   `getContextForRecipient()` — the `RecipientAuthContextReader` pattern the ADR names, which *is* the right
   pattern and needs no new port method (§2.9).
2. **The enforcement** is a decorator in `Session/Infrastructure/` implementing `SigningTokenIssuer`, wrapping
   `StoreBackedSigningTokenIssuer`, re-aliased at the existing `config/services.yaml` alias.

⛑ **A decorator rather than an `if` inside `StoreBackedSigningTokenIssuer`**, because that class's docblock is
a decision: *"This is a storage seam, not a domain guard, and the distinction is deliberate."* Putting a
domain guard inside it contradicts a written decision (repo rule 7) and would make the next reader who trusts
that docblock wrong. The decorator's name says what it refuses and the storage seam stays a storage seam.

⚠ **The honest cost, stated so nobody discovers it as a surprise:** the decorator reads envelope state on
**every** mint, including the two Notification callers that are already holding a `RecipientView` when they
call. That is one extra RLS-scoped read on a path that already does several. The alternative — passing the
fact in — puts the predicate back at the three call sites, which is what §2.5 exists to prevent. Taken
knowingly; §6 records it.

⚑ **The predicate reads both terms.** A mint is refused when the slot is `declared_claimable AND claimed_at
IS NULL`. A **claimed** slot mints normally — it is an ordinary recipient — and §5's regression arm asserts
that, because a refusal keyed on the declaration alone would leave every claimed party permanently unable to
receive a link.

### D3 — `correctContact()` is refused on an unclaimed slot, and the refusal reads both terms

ADR-0057 §2.3's reciprocal clause. Without it a plain correction on an unclaimed slot sets an address, emits
`RecipientCorrected`, and `NotifyCorrectedRecipientUseCase` mints a token and mails the invitation —
producing a reachable, addressed party who is still formally **unclaimed**: no `RecipientClaimed`, no declared
subject, no once-only accounting, and §2.5's refusal untouched because it guards a different question. The
outcome §1 exists to prevent, reached without widening anything.

- **Home:** `Recipient::correctContact()`, as a third `RecipientNotCorrectableException` factory beside
  `legAlreadyClosed()` and `budgetExhausted()`, with its own RFC-9457 `code` so the body **names the claim as
  the operation that applies** (§2.3). The controller docblock's two-code paragraph gains a third.
- **Ordering:** checked **before** the budget, so a refused correction spends nothing — the rule
  `CorrectRecipientUseCase` already states for the destination guard.
- ⚑ **Both terms, and each single-term version fails differently.** On `claimed_at IS NULL` alone every
  ordinary correction is refused — loud, and the first fixture catches it. On `declared_claimable` alone a
  **claimed** party can never be corrected again, for ever — silent, and invisible to any fixture built from
  an unclaimed slot. §5 gives each direction its own arm.

### D4 — Once-only, replay, and what *identical* means

§2.4 refuses a second claim; §2.15 requires an identical replay to be indistinguishable from the first call.
`Recipient::assign()` is the template: return the existing on identical, throw naming the differing field on
divergence.

⚠ **ADR-0057 §5 bar 11 says *identical* "must be defined before this can be written" and does not define it.
This task defines it:**

> **A field the replay does not supply is not compared.** Absent means *not asserted* — on the first call
> there is nothing to leave alone, so it simply lands as `null`; on a replay it is excluded from the
> comparison. A field the replay **does** supply must equal what is stored, or the claim is refused naming
> that field.

That single rule produces bar 11's required case for free: a retry that omits `locale` after a first call that
sent one is **identical**, not divergent — which is exactly the network-timeout retry §2.15 exists to serve,
and the case where a 409 would be worst.

**The wire answers:** `204 No Content` on the first claim **and** on an identical replay — deliberately
indistinguishable, because making them differ would hand the integrator a way to detect a retry, which is not
a feature and would tempt a branch on it. A divergent replay is `409` with a `code` naming the field. A claim
on an already-claimed slot with a *different* party is the same 409 — §2.15's whole point is that what is
refused is a genuine re-assignment, never a retry.

**The concurrency half is not the same guard.** A sequential test cannot see a lost update. The write loads
through `EnvelopeRepository::findLockedForUpdate()` exactly as `CorrectRecipientUseCase` does, and that lock
is the mechanism by which two racing claims produce one winner. §5 names the only harness that can observe
it.

### D5 — What a claim body must carry, and the one thing ADR-0057 leaves open

§2.13 states the **upper** bound — *"nothing beyond the declared gate may be required"* — and §2.16 says the
locale may travel. **Neither states a lower bound**, and for a slot whose gates are the neutral pair or
`ACCESS_CODE` the gate-derived requirement is *nothing at all* — so a claim could name **nobody** and still
consume the once-only fill, which defeats §1's *"who was this addressed to?"*.

**This task requires `full_name` on every claim.** The evidence that the ADR assumes it is §3.3, which says
in terms *"the claim writes a name and an address"*. And it does not breach §2.13, which bounds what
**contact** may be demanded: a name is not a destination, and the operation *is* naming the party.
⚠ Recorded as this task's decision, not the ADR's — if it is wrong, ADR-0057 is where to fix it, not here.

Everything else is derived: exactly the destinations the declared gates require (§2.13), plus an optional
`locale`. Nothing else about the party may be set — and §4 D9 covers `userId`.

### D6 — The destination guard is deferred at authoring and re-run at the claim, keyed on the declaration alone

- **`AddRecipientUseCase`** skips `DeclaredMethodDestinations::guard()` when the request declares the slot
  claimable. ⛔ **Keyed on the declaration and on nothing else** (§2.13's closing paragraph): a deferral keyed
  on *"has no contact yet"* silently reopens [`BL-162`](../BACKLOG.md), whose refusal for an ordinary
  contactless recipient stays exactly as it is today.
- **The skip lives at the call site, not inside the service.** `DeclaredMethodDestinations` answers *can this
  recipient be reached by every declared method*, and that question does not change; what changes is **when**
  it is asked. A `$declaredClaimable` parameter inside would make the service's answer conditional on a state
  it does not own — and the service is shared with the correction path, which must never skip.
- **`ClaimRecipientUseCase`** runs the same guard against what the claim supplies merged with what the slot
  holds, **before** the mutation, so a refused claim does not consume the once-only fill —
  ⚑ **Corrected 2026-09-01: this said *"merged with what the slot holds (which is nothing)"*.** It is not
  necessarily nothing — a slot may be authored **with** a contact, which `AddRecipientRequest::$claimable`
  publishes and which the eCMR case relies on (the sender knows the depot's mailbox, not the operator). The
  parenthesis made the merge read as decoration, and that reading is what cost this branch twice: `b0c5eb5`
  (a live credential mailed to a declared, unclaimed, **reachable** slot) and `0802326` (a claim omitting
  the address passed the guard on the stored value and then removed it) were both reasoned from it —
  the ordering `CorrectRecipientUseCase` already establishes for the budget. Same 422, same
  `RecipientCannotReceiveMethodException::forSlot()`, naming the **first** unreachable method in declaration
  order, exactly as the authoring path does.
- ⛑ **The guard's purpose is preserved rather than weakened**, and the comment inside `guard()` is the proof:
  it exists so the failure does not surface *"at the gate — to the signer, long after the sender has moved
  on."* Deferred to the claim it surfaces to the **integrator**, synchronously, on the call that caused it —
  strictly earlier than the case it was written against.

### D7 — `RecipientClaimed` carries no identity, and needs no ordinal

Four keys — `envelope_id`, `recipient_id`, `step_ordinal`, `occurred_at` — and `EVENT_TYPE =
'RECIPIENT_CLAIMED'`, copying `RecipientCorrected` trait for trait.

**No name, no e-mail, no phone.** The reason is sharper here than it was there and is worth writing on the
event: a correction adjusts a person already named, while a claim **introduces** one — so it is the natural
place for somebody to add the name *"for the audit trail"*. `platform.event_log` is append-only
([ADR-0031](../adr/ADR-0031-event-log-store.md)) and its rows outlive the aggregate's erasure path, so a name
written there cannot be taken back.

⚑ **No `correctionOrdinal` twin, and the absence is a consequence rather than an omission.**
`RecipientCorrected` carries its ordinal because `NotificationId::fromCause()` derives the notification id
from the cause, so a re-invitation reusing an earlier cause converges and sends nothing. A claim happens
**once** (§2.4) and an identical replay emits **no second event** (§2.15), so `(envelope, recipient)` is
already unique per claim and convergence is free. That is §2.4 buying something concrete — and it is an input
TASK-037 depends on when it picks the occasion's cause token.

⚠ `EVENT_TYPE`'s value is fixed by nothing and changing it re-types history already written. Nothing has been
written under this type, so choosing it now is free and choosing it later would not be.

### D8 — `f5s:none` is refused at the route, by the controller, reading the header itself

§2.6. The central `TenantRequestListener` validates the header's grammar and **accepts** `f5s:none` — it is
the legal reserved value — then discards it (§2.4 above). So the refusal is the controller's: read
`F5Sign-Declared-Subject` off the request, `DeclaredSubject::fromString()` it (the listener has already
guaranteed it parses), and refuse `isNone()` with a `400` carrying a `code`.

⛔ **And the record must claim no more than that.** The declared subject is validated and **discarded**;
nothing stamps it, and §2.14 keeps it out of the event payload. So this refusal proves a human was
**asserted**, never that one was **recorded** — nothing in this repository can yet answer *"which dispatcher
named this consignee?"*. Recording it is ADR-0047's open consumer question and §6 carries it. No docblock,
no `#[OA\*]` string and no test may imply an audit trail that does not exist.

### D9 — The locale may travel; `userId` stays `null`

- **Locale.** `null` still means *"not indicated"* and still falls through recipient → tenant → system in
  `NotificationTemplates::localeFor()` exactly as today. The claim is the **first** moment the party's
  language is knowable at all, which is why a fill may carry it where a correction deliberately may not
  (TASK-027 §3).
- **`userId` stays `null`, and the discipline is the point.** A claim supplying an e-mail is precisely where
  somebody resolves the recipient→user link opportunistically, inventing the matching rule in passing, in the
  place least likely to be reviewed as an identity decision.
  [`identity-access-domain-model.md`](../ddd/identity-access-domain-model.md) records that the link is built
  **without** the rule. When the rule is decided, this path is one of its cases rather than its precedent.
  §5 says why an absence check on one field is the wrong bar for this.

## 5. Verification

Each property names the tier that can actually observe it, the fixture that makes the two candidate causes
disagree, and what sabotage must turn it red (authoring rule 4). Bar numbers in parentheses are
[ADR-0057](../adr/ADR-0057-claimable-recipient-slot.md) §5's.

**Harness**: the worktree lane, which is the only one that validates this tree —
`WT_GATES="lint arch phpstan test" make -C ../f5sign-infra wt-backend src=$(pwd)`. The infra Makefile's plain
targets bind-mount the **main** checkout and would report green for another branch.

1. **P-unclaimed-is-a-conjunction** — `Unit/` on `Recipient`. A truth table over **all four** column
   combinations, including the unreachable `(declared = false, claimed_at set)`: the accessor answers `true`
   for `(true, NULL)` and `false` for the other three. ⚑ **This is the design-separating bar available at this
   tier**, and it is the substitute for ADR-0057 bar 1, which cannot be reached here (see *bars not placed*).
   **Sabotage:** drop either term from the accessor and exactly one row reddens — which term reddens which
   row is the check that both are load-bearing.
2. **(2) P-claimable-defers-the-destination-guard, as a pair** — `Application/` on `AddRecipientUseCase` with
   a faked `PhoneNumberParser`. Arm A: a slot declaring `OTP_EMAIL` with no e-mail and the declaration →
   accepted. Arm B: the same command **without** the declaration → 422. ⛔ The pair, never either arm: arm B
   is today's behaviour and is the BL-162 regression guard. **Sabotage:** key the skip on *"has no contact"*
   and arm B goes green, reddening the test.
3. **(3) P-claim-names-the-first-unreachable-method** — `Application/` on `ClaimRecipientUseCase`. Access gate
   `[OTP_EMAIL, OTP_SMS]`; the claim supplies a valid e-mail and a **landline**. The refusal names `OTP_SMS`.
   ⚑ Built with a **later** member unreachable and the head fine, because a head-only guard passes every
   fixture whose members agree — the twin `DeclaredMethodDestinationsTest::a_later_member_…` already in the
   tree. **Sabotage:** guard the head only; this reddens and nothing else does.
4. **(4a) P-second-claim-refused-on-the-resulting-state** — `Application/` + `Acceptance/`. Two claims naming
   different parties; assert **the slot still names the first** and `claimed_at` is unmoved. ⛔ Never on the
   status code alone: a guard that returns 409 and mutates anyway passes a status-code test.
   **Sabotage:** remove the once-only check and the state assertion reddens while a status-code-only test
   would not.
5. **(4b) P-two-racing-claims-produce-one-winner** — `Integration/`, `#[SkipDatabaseRollback]`, using
   [`ProbesRowLocks`](../../tests/F5Sign/Support/ProbesRowLocks.php) and following
   `ConcurrentSessionOpenTest`'s shape. ⛔ **`Integration/` under DAMA cannot see this**: it runs one
   connection, so `findLockedForUpdate()` and a plain read are indistinguishable to it — the exact case
   [`CLAUDE.md`](../../CLAUDE.md) authoring rule 4 records. **Sabotage:** flip `lockForUpdate` to `false`;
   only the probe arm reddens, which is the evidence that it is the arm doing the work.
6. **(5, at the issuance service) P-no-token-for-an-unclaimed-slot** — `Integration/`, driving the real
   `SigningTokenIssuance` out of the container against a real declared, unclaimed slot; plus a **claimed**
   slot and an **ordinary** recipient, both of which must mint. ⚑ The two positive arms are the ones that
   catch a refusal keyed on the declaration alone. **Sabotage:** remove the slot term from
   `SigningTokenIssuance::issueFor()` and the negative arm reddens; drop the `claimed_at` half of the
   conjunction and the claimed arm reddens.
   ⚑ **Reworded 2026-08-28, substance unchanged.** This bar read *"driving the real **decorated**
   `SigningTokenIssuer`"* with the sabotage *"remove the **decorator alias**"*. No decorator exists — §4 D2's
   banner says why — and a sabotage target that does not exist is a sabotage pass that cannot have been run.
   The three arms and the discriminating property they encode (a negative arm plus **both** positives) are
   exactly as specified.
7. **(5, through the controller) P-the-mint-route-refuses** — `Acceptance/` on `POST /api/v1/signing-tokens`.
8. **(6) P-a-correction-on-an-unclaimed-slot-mints-and-mails-nothing** — `Acceptance/`, extending
   [`tests/F5Sign/Acceptance/RecipientCorrectionHttpTest.php`](../../tests/F5Sign/Acceptance/RecipientCorrectionHttpTest.php),
   the cross-BC `#[CoversNothing]` walk that already drives the correction route end to end. Assert the
   refusal **and** the observable outcome: no signing token row, no delivery. Add the mirror arm — an
   ordinary recipient's correction still mints and mails — because that is the direction D3's
   declaration-only failure hides in. **Sabotage:** remove the guard; the first arm's *outcome* assertions
   redden, not merely its status.
9. **(8) P-an-SMS-only-gate-is-claimable-with-a-phone-and-no-e-mail** — `Acceptance/`, written as the
   **positive** case, because the defect it guards is a blanket e-mail requirement creeping back and no
   absence check can see that. ⚠ The bar stops at the 2xx: with no address the party then lands in
   [`BL-173`](../BACKLOG.md)'s hole, no worse and no better than an ordinary phone-only recipient authored
   today. Inherited, not created here; asserting delivery would assert a hole this task does not own.
10. **(9) P-the-claim-route-refuses-a-none-subject** — `Acceptance/`: `F5Sign-Declared-Subject: f5s:none` →
    400 with its `code`; a real value → 204. ⛔ **Asserts the refusal and nothing more.** Per §4 D8 the value
    is discarded downstream, so no assertion here may imply it was recorded.
11. **(10) P-claimed-payload-key-set-is-closed** — `Unit/` on `RecipientClaimed::toPayload()`, written as
    **equality over `array_keys()`**, never as `assertArrayNotHasKey('email', …)`. PHPStan L9 rejects a
    missing key and accepts an extra one, so only a closed-set assertion catches the next field somebody adds.
    **Sabotage:** add a key; the test reddens naming it.
12. **(11) P-identical-replay-is-indistinguishable; divergent-replay-names-the-field** — `Unit/` on
    `Recipient::claim()` for the return value and the absence of a second recorded event, plus `Acceptance/`
    for 204/409. ⚑ **The omitted-locale case is in this bar, not beside it**: a first claim carrying a locale
    followed by a replay omitting it is **identical** (§4 D4). **Sabotage:** compare unsupplied fields too;
    that one case reddens and no other does — which is the evidence the rule, not the code, is under test.
13. **(13) P-an-unclaimed-slot-holds-its-step-open** — `Unit/` on `Envelope`: drive
    `recordRecipientCompletion()` for every other member of a step containing one unclaimed slot and observe
    the step still open. ⛔ **Written against the aggregate, never against
    [`StepCompletionEvaluator`](../../src/F5Sign/Envelope/Domain/Service/StepCompletionEvaluator.php)**, which
    has zero production callers — a test there is green whatever the aggregate does.
    ⚠ **Honest label: this bar cannot fail as of this task's diff.** An unclaimed slot is `PENDING`, and
    `advanceAfterRecipientTerminal()` (the step predicate at the time; TASK-048 has since replaced it with
    `Envelope::advance()` asking `EnvelopeEndingEvaluator`) filtered on `isTerminal()`, so the property already held and green was
    the *expected* signal rather than evidence. It is carried as a regression pin against the plausible next
    move — giving a slot its own `RecipientOutcome` member — and its only real check is the sabotage:
    make `isTerminal()` answer `true` for a declared, unfilled slot and watch it redden.
14. **(14) P-a-claim-is-refused-once-the-party-could-no-longer-act** — `Acceptance/`, through the
    **reachable** route: `POST …/void`, then claim. ⛔ Not through a non-blocking role, a state the live
    predicate cannot produce (ADR-0057 §9). Written as a predicate over *could this party still be invited
    and still act* — leg non-terminal, step not complete, envelope not terminal — so a fourth fact joins it
    rather than being forgotten.
15. **(15) P-a-claim-writes-exactly-the-fields-it-may** — `Unit/` on `Recipient`, as a **closed assertion over
    what the claim changed**: e-mail, phone, name, locale, `claimed_at`, and nothing else — with `userId`,
    `role`, `stepOrdinal`, `authRequirement`, `authSelectionMode` and `outcome` all asserted unmoved.
    ⛔ **Not `assertNull($recipient->userId())`.** Nothing sets it, so an absence check on one field cannot
    fail — authoring rule 5's empty-exempted-set shape exactly. The closed comparison can.
    ⚑ The locale half of bar 15 splits: *a claim carrying no locale leaves `locale()` `null`* is asserted
    here; *and the chain then resolves recipient → tenant → system* is `NotificationTemplates::localeFor()`'s
    property, already locked by TASK-027, and is **cited rather than re-tested**.
16. **P-the-two-fields-survive-an-unrelated-authoring-command** — `Integration/`. Author a claimable slot,
    run an unrelated `AddStep` on the same envelope, re-read, assert both values unchanged. ⚑ **Not an
    ADR-0057 bar, and the one most likely to catch a real defect**: `save()` upserts every recipient row on
    every authoring command, so a field dropped from `rehydrate()` is silently written back as its default —
    the failure `Recipient`'s own `authRequirement` comment calls *"the entry with the worst failure mode on
    the entity"*. Here the slot would stop being a slot and every refusal above would quietly lift.
    **Sabotage:** drop the field from `rehydrate()`'s parameter list; this reddens and **nothing else does**.
17. **P-a-pre-existing-shaped-recipient-is-untouched** — `Integration/` + `Acceptance/`. A recipient with
    `(declared_claimable = false, claimed_at = NULL)` — the shape the migration leaves on every existing row —
    mints a token, receives an invitation and accepts a correction, exactly as before. ⚑ This is the
    behavioural half of §4 D1's argument, and the arm that would have gone red under the false-history
    backfill.

⛔ **The migration's own backfill is NOT covered by a test, stated rather than papered over.** The backfill is
a column `DEFAULT` filling pre-existing rows, and the lane migrates from an **empty** database on every run,
so the default fills nothing and there is nothing to observe — the same honest gap
[TASK-025](TASK-025-recipient-delivery-failure-and-correction.md) accepted for `corrections_made` and
[TASK-034](TASK-034-recipient-access-trace.md) §6 for its `UPDATE`. **What is guaranteed:** the DDL parses and
executes against the real schema (a mistyped column reddens), `SchemaConformanceTest` asserts the dropped
default and the `text`/RLS conventions, the *meaning* of the value is argued in the migration docblock against
every aggregate state (§4 D1), and its *behavioural* consequence is bar 17. ⚠ This is the place a reviewer
should push back if they disagree.

**Sabotage pass before citing any green run** (authoring rule 4): revert, in one batch, the conjunction in the
unclaimed accessor, the once-only check, the `correctContact()` guard, the slot term inside
`SigningTokenIssuance::issueFor()`, and the `rehydrate()` carry — then run the lane and confirm each reddens
**naming its own property** and none masks another. Restore.

⚑ **Corrected 2026-08-28.** The fourth target read *"the issuer decorator's alias"*, which does not exist
(§4 D2). ⛔ **The consequence is worse than a wrong name and is the reason this is written out rather than
quietly fixed**: a five-target pass whose targets are not all real cannot have been run, while the partial
output it does produce reads exactly like a completed one unless somebody counts the targets. `ac20f13`'s
message records the same failure from the other end — two of the five had no test to redden because the bars
were never written.

### Bars this task cannot place, and why

⚑ **Two of these four moved on 2026-08-28, in `b0c5eb5`, and both moved because the fan-out exclusion was
built here after all** (§8 records why). The retired text of each is quoted in place rather than replaced
silently, because in both cases the reason given for *not* placing a bar was the same false premise that let
the leak ship.

- **(1) *"A recipient who has been claimed is invited when their step activates."*** ⛑ **PLACED after all,
  on 2026-08-28**, as the second fixture of
  `NotifyActivatedStepRecipientsUseCaseTest::it_does_not_invite_a_slot_nobody_has_claimed`: a **claimed**
  slot on the activating step, asserted to be the one recipient a credential is minted for and the one
  addressee an occasion is created for. Under a guard keyed on `declaredClaimable` alone that recipient is
  muted, zero credentials are issued and the assertion reddens — which is exactly the separation ADR-0057
  calls *"the one that matters most"*. ⚑ **This bullet read**: *"⛔ **Not placeable here, and writing it
  would be worse than omitting it.** Under this task alone there is no fan-out exclusion at all, so a claimed
  recipient is invited trivially and the test is green whatever the flag design is — a bar that cannot fail,
  read as evidence. It is **TASK-037's**."* The premise held only while the exclusion did not exist; building
  it made the bar both placeable and cheap, since the negative fixture the leak forced already needed a
  positive arm beside it. ⚠ **One honest limit, stated rather than left to a tier name**: the harness drives
  `NotifyActivatedStepRecipientsUseCase::execute()` with a step-ordinal command over a faked
  `EnvelopeContextView`. What is proved is *the fan-out invites a claimed party and refuses an unclaimed
  one*; what is **not** proved is that a real `RecipientStepActivated` reaches that use case through the
  relay. Bar 1 above stays as the domain-level companion rather than being retired.
- **(5, through the Notification callers).** ADR-0057 asks for the refusal *"asserted at the issuer and
  through all three of its callers"*. ⚑ **Corrected 2026-08-28: it is one caller that cannot be reached, not
  two.** This read *"**Two of those three become unreachable with an unclaimed slot the moment this task
  lands** … `NotifyActivatedStepRecipientsUseCase` already skips on `email === null`, which an unclaimed slot
  always is, before TASK-037's explicit exclusion arrives. A test through either would be green with the
  guard **and** without it."* ⛔ **The second clause was false, and it was false in the direction that hides a
  leak**: an unclaimed slot is *not* always without an e-mail, so that caller was reachable, unguarded, and
  minting. It now carries its own refusal and its own discriminating test (above), so the bar **is** placed
  through it. What genuinely stays unreachable is `NotifyCorrectedRecipientUseCase`: it is reached only by a
  `RecipientCorrected`, which `Envelope::correctRecipientContact()` is the sole emitter of and which §4 D3
  now refuses upstream for an unclaimed slot — so a test there would be green with the guard and without it,
  and bar 8's *no token was minted* through the correction route is the observable substitute. ⛑ **And the
  guard stays at the issuer regardless**, precisely because it must not depend on either upstream refusal
  staying in place.
- **(7) A claim on a not-yet-activated step mints nothing, mails nothing, and the invitation arrives exactly
  once when the step opens.** ⛔ Entirely about the notification occasion. **TASK-037's**; there is no
  occasion here to test.
- **(12) The read model separates an unclaimed slot from a claimed recipient who has not acted.**
  §2.11's field is out of scope; the projection has nothing to publish yet. **TASK-037's.**

## 6. Open follow-ups (track, don't solve here)

- **Re-assignment, and editing a recipient's identity generally — one question, not two.** §2.4 defers
  changing a slot's occupant, and confirms with the product owner (2026-08-25) that it is the *same*
  deferral as editing `fullName` / `role` / `locale` on a party already named: all of them are *change who
  this party is*, so whatever answers one must answer all. It needs the signing session resettable first —
  [`SigningSessionId`](../../src/F5Sign/Session/Contract/Type/SigningSessionId.php) is a deterministic UUIDv5
  over `(tenant, envelope, recipient)`, so a second occupant would inherit the first one's session row,
  access trace and **passed gate**, contradicting ADR-0049 §2.3. ▶ Forced the day a consignee changes
  between dispatch and delivery. **Home: [`BL-193`](../BACKLOG.md).**
  ⚑ **Two corrections, 2026-08-28.** (a) This bullet ended *"**No BACKLOG row exists for it** — §7 proposes
  one"*. `BL-193` was filed on 2026-08-25 under *"TASK-036 planning"*, before this record was finished, and
  this branch's own migration docblock cites it in the `No CHECK` paragraph — so the row existed, was
  reachable by `rg 'BL-193'`, and the sentence denying it survived because nothing re-reads a paragraph whose
  diff is empty. (b) The bullet named *"the in-repo precedent to follow is the **generation counter**
  (`authGeneration` / `authHardLockedAtGeneration`)"*. `BL-193` records that
  [ADR-0060](../adr/ADR-0060-retiring-a-credential-whose-holder-changed.md) §2.2 **evaluated and rejected**
  it, on a first reason that is factual and disqualifying: the generation cannot see a contact correction,
  because `correctRecipientContact()` does not advance it, and bumping it there would make one counter mean
  the auth-attempt epoch and the credential epoch at once. Its answer is **an instant on the recipient**,
  compared against a claim the credential already carries. The clause that survives both corrections is the
  one that was never in doubt: minting a fresh session id would break a determinism ADR-0055 §2.7 depends on.
- ⛔ **Withdrawn 2026-08-28, not reworded.** This position held *"the mint **decorator** reads envelope state
  on every issuance (§4 D2) … one extra RLS-scoped read on a path that already does several"*. No decorator
  exists (§4 D2's banner), and the cost it worries about **is not incurred**: `SigningTokenIssuance` was
  already loading envelope state to answer `sentAt`, so the slot term is a second question of a read that was
  already being paid for. Nothing is owed here, which is why the bullet is removed rather than repointed —
  keeping it would leave a follow-up standing against a cost nobody pays.
- **The declared subject is asserted, never recorded** (§4 D8). `TenantRequestListener` discards it and
  §2.14 keeps it out of the payload, so nothing can answer *"which dispatcher named this consignee?"*. That
  is [ADR-0047](../adr/ADR-0047-declared-subject-on-machine-requests.md) **§2.6**'s open consumer question,
  tracked at [`BL-73`](../BACKLOG.md) — not this task's, but a claim is now a second, stronger argument for
  answering it, and this is the first surface where the absence has a name attached. ⚑ **Citation corrected
  2026-08-28**: this read *"its part 5 / D10 (d)"*, and neither resolves — ADR-0047 §5 is its *Enforced by*
  section and the record has no `D10`. A pointer that does not resolve is worse than none, because it reads
  as though somebody checked.
- **Self-claim** (§2.9) — excluded, with three admission bars stated so a later reader can tell an unresolved
  question from a closed one: a way for the arriving party to prove something checkable against something we
  already hold; a statement of what a claim confers when that check is unavailable; and whether an unclaimed
  slot's link may be issued at all before somebody is named — which §2.5 currently answers *no* for a
  different reason.
- **The exit from a slot nobody will ever claim** — [`BL-192`](../BACKLOG.md), and deliberately not
  claimable's: the same capability is what a named recipient who must be substituted needs. Until it lands
  the only way out of a stalled envelope is `void()`, which ends everything on it. ⚠ An envelope may
  therefore wait **indefinitely** on a claim; §2.11 makes the wait legible and does not end it.
- **A claimable `CERTIFIED_DELIVERY` slot is permitted by ADR-0057 §2.17 and buildable by nothing.** Four
  separate blockers, none of them claimable's: `RecipientOutcome::ACKNOWLEDGED` does not exist; there is no
  second completion path into Envelope for *passing the access gate*; the role cannot reach its own ceremony
  and fails in the **expensive** direction ([`BL-190`](../BACKLOG.md) — invited, charged for an SMS,
  authenticated in full, then refused the read model); and its blocking classification is disputed with the
  live code implementing neither reading. ▶ Recorded because the failure mode of silence is specific: the
  authoring succeeds and the first sign of trouble is a charged SMS to a party who then cannot read anything.
- ⚠ **Added at close, 2026-08-28 — a `f5s:none` refusal and a malformed header are indistinguishable from
  the response body.** Both are `400` carrying `code: INVALID_DECLARED_SUBJECT` with a generic `detail`,
  because the shared handler suppresses value-object messages so a rejected value can never leak into a
  response. ⛑ **That suppression is correct for its original reason and wrong for this one**: a rejected
  subject may be personal data, but `f5s:none` is a **reserved constant** and saying it was the value tells
  an integrator nothing they did not send. So a client that gets a 400 cannot tell *"you named nobody"* from
  *"your header does not parse"* without re-reading what it sent. ▶ What it needs is a distinct `code`, which
  needs an exception the UI layer owns — and this repository has **no UI-layer exception class at all**, so
  introducing the first one is a shape decision outside §3's scope. ⚑ **Published rather than merely noted**:
  the claim route's `#[OA\*]` 400 response states the ambiguity and tells the client to branch on the code and
  check the header it sent, so an integrator meets the limit in the contract instead of discovering it.
- **[`BL-173`](../BACKLOG.md) is not discharged**: a claimable slot declaring an SMS-only gate is claimable
  with a phone alone and then lands in exactly that hole — no worse and no better than an ordinary
  phone-only recipient authored today. Claimable neither widens it nor is entitled to close it;
  [TASK-031](TASK-031-channel-selection-beyond-email.md) is what lifts it.
  ⚑ **Tense corrected 2026-08-28.** This bullet opened *"[`BL-61`](../BACKLOG.md) is not discharged (§1), and
  neither is [`BL-173`](../BACKLOG.md)"*. **`BL-61` was Closed on 2026-08-28** by
  [TASK-038](TASK-038-terminal-envelope-closes-the-ceremony.md) /
  [ADR-0059](../adr/ADR-0059-terminal-envelope-closes-the-ceremony.md), after its pre-send half closed on
  2026-08-25 — so it is no longer an open follow-up anything can decline to discharge. **The substance is
  unchanged and still worth saying**: this task does not close BL-61 and never did, which §1 now states in
  the past tense. `BL-173` is untouched by the closure and stays open.

## 7. Prose surfaces this changeset owes (scoped here, deliberately not written here)

⚑ Authoring rule 1: *the diff is not the search surface* — every file below shows an **empty diff** across
this change and every one of them starts instructing wrongly the moment it lands. The sweep is one command:
`rg -n 'RecipientClaimed|CLAIMABLE|RecipientResolver|self-identif' src tests migrations docs config CLAUDE.md`.

**Three dated banners on `docs/ddd/` models.** ADR-0057's `Crosswalk` records that this decision **keeps the
event name and replaces its semantics** — the design lineage defines `RecipientClaimed` as the *self-claim*
shape §2.9 excludes and §7.4 rejects. Per [`AUTHORING.md`](../adr/AUTHORING.md) § Maintenance item 5 each
displaced row carries a dated banner pointing at ADR-0057. The three homes, located by symbol:

- [`docs/ddd/envelope-domain-model.md`](../ddd/envelope-domain-model.md) — four surfaces, not one: the
  `AssignClaimableRecipient` bullet under § Lifecycle transitions (*"resolves a recipient whose identity was
  unknown at send time"*); the events-table row defining `RecipientClaimed` as *"A CLAIMABLE recipient
  **self-identified** and passed initial auth"*; the `RecipientResolver` ports row (*"Validate a proposed
  identity when assigning a CLAIMABLE recipient"*); and the **Signing Session** integration row that lists
  `RecipientClaimed` as an outbound fact to that context.
- [`docs/ddd/signing-session-domain-model.md`](../ddd/signing-session-domain-model.md) — the note that
  *"`RecipientClaimed` is emitted by Envelope"* and the `RecipientResolver` (read) port row restating
  validation *"at claim time"*.
- [`docs/ddd/identity-access-domain-model.md`](../ddd/identity-access-domain-model.md) — the **Claimable
  recipients** row describing *"Identity is resolved **after** send"* as *"a mode-D capability that becomes a
  mode-C ceremony credential, so two access modes meet inside one recipient's lifetime"*, which is the
  self-resolution flow in full.

Each banner says: the event name survives, the semantics are ADR-0057's — the claim is a **sender-side fill
under `MACHINE_KEY`**, not a self-identification; `RecipientResolver` is **not** the port that realizes it and
nothing validates a proposed identity, because nothing is proposed. ⛔ **Keep the historical text.** *"An
earlier cut held this as self-claim"* is a correct record of what changed; the banner dates the displacement
rather than erasing it.

**One docblock pointer.** [`Recipient::correctContact()`](../../src/F5Sign/Envelope/Domain/Entity/Recipient.php)
gains an `(ADR-0057)` reference on its new refusal, saying that a correction changes *where a named party is
reached* and an unclaimed slot has no named party to reach — and naming the claim as the operation that
applies. ⚑ Its neighbouring paragraphs are correct and stay: nothing here disturbs the `null` = *leave alone*
reading or the access-trace non-clearing note.

**⚠ And one surface the assignment did not name, found by the sweep.** `Recipient::locale()`'s docblock says
*"Set once, at add time, and never edited — for this field"*, then argues at length that the **correction**
deliberately does not touch it. That paragraph becomes wrong the moment a claim writes a locale. §2.16 gives
the exact replacement — a *fill* is the opposite case from a *correction*, because the moment the party is
named is the first moment their language is knowable at all, so *the authoring-only property stays true of
every path except this one*. ⛔ **Do not delete the clause** (authoring rule 2): the reason it gives is still
right, only its *scope* moved. The same docblock's *"immutability is a property of the API surface, not of the
aggregate"* sentence needs the claim added to its list of exceptions.

## 8. Deviations & honest notes

Written at close, **2026-08-28**, over `feat/claimable-recipient-slot` at `ac20f13`. Appended as the last
section and nothing above renumbered: `§N` here are cited from ADR-0057, from
[TASK-037](TASK-037-claimable-invitation-and-visibility.md) and from the migration docblock.

⚑ **Read §2.5, §2.8, §4 D1's *No index*, §4 D2, §5 bar 6, §5's sabotage pass and §6 with their dated
banners.** Every one of those corrections was found by a validation pass, and **every one of them showed an
empty diff across this branch** — the file was never edited by the work it describes. That is authoring
rule 1's named surface, and the count is the finding: seven separate claims in the record that specified the
work went stale or were wrong when written, in a file whose diff said nothing had changed.

### Scope

- ⚠ **§3's falsifier fired TWICE, on two of the three surfaces it names, and the two firings mean opposite
  things.** ⚑ **Rewritten 2026-08-28, after `b0c5eb5`.** This bullet previously concluded *"Two of the three
  held — neither `EnvelopeJsonPresenter` nor `NotifyActivatedStepRecipientsUseCase` is touched … **The
  boundary is intact; the falsifier was written as a path test where the property is about which
  contract.**"* That was true when written and stopped being true in the same branch. The falsifier reads
  *"if this task's diff touches `EnvelopeJsonPresenter`, `docs/frontend-handoff/` or
  `NotifyActivatedStepRecipientsUseCase`, the boundary is wrong."* **`EnvelopeJsonPresenter` is still
  untouched. The other two are both in the diff.**
- **The `NotifyActivatedStepRecipientsUseCase` firing is a real scope deviation, taken deliberately, and it
  is not a boundary error — it is a live security defect that could not wait for the sibling.** ADR-0057
  §2.5's third door was **open**: the record held that the pre-existing `email === null` skip already closed
  it, *"which an unclaimed slot always is"*, and that premise is false — a claimable slot may be authored
  **with** a contact, and `AddRecipientRequest::$claimable` publishes that it may. So a declared, unclaimed,
  reachable slot was being mailed a **seven-day bearer signing credential nothing can revoke**, for a party
  the system records as unnamed; whoever received it could sign, and the evidence would attribute that
  signature to nobody. Measured before the fix, on the fixture written for it: `Failed asserting that actual
  size 2 matches expected size 1` — two credentials minted where one was owed. The guard added is one
  `continue` on [`RecipientView::isUnclaimedSlot()`](../../src/F5Sign/Envelope/Contract/View/RecipientView.php),
  **before** the issuer call rather than around the message, pinned by
  `NotifyActivatedStepRecipientsUseCaseTest::it_does_not_invite_a_slot_nobody_has_claimed` over three
  fixtures. ⛔ **This is the honest shape of the deviation: the boundary §3 drew was right, and shipping a
  known credential leak to honour it would not have been.** What is *not* taken is the rest of §2.7 — no
  claim occasion, no cause token, no not-yet-activated guard — so [TASK-037](TASK-037-claimable-invitation-and-visibility.md)
  keeps its subject and loses one item; its `Status` row records the reduction and tells whoever picks it up
  not to rebuild the guard.
- ⚠ **The `docs/frontend-handoff/` firing is the other kind, and the original reasoning for it stands.** The
  path is shared by two different contract changes: the handoff §3 excludes is ADR-0057 §2.11's **read-model
  field**, which is TASK-037's and is not published here; what this note publishes is *this* task's own
  additive surface — the declaration on `AddRecipientRequest`, the new claim route, and **three new refusal
  codes on two routes clients already call**. Those are not the sibling's to announce, and withholding them
  would leave a published `#[OA\*]` contract change with no handoff. **That firing was a path test standing
  in for a property about which contract**; whoever writes TASK-037's falsifier should name
  `EnvelopeJsonPresenter` and the read route's schema, not the directory.
- ⛑ **The lesson the pair teaches is about falsifiers, not about this diff.** A falsifier written as a list
  of file paths cannot distinguish *"you drifted"* from *"you found something that must not ship"*, and both
  came back as the same red. A falsifier is still worth writing — it is what made both firings visible at all
  — but a record must classify each firing when it happens rather than let a green-looking count of *"two of
  three held"* stand in for the classification.
- **Two comment-only files outside §3, both pre-existing rot on surfaces this branch touched**, landing under
  repo-specific rule 2's docblock carve-out (nothing re-runs): `Version20260820000002`'s docblock attributed
  `envelope.recipient`'s RLS to `Version20260721000001`, the **Notification** baseline, where the real home is
  `Version20260713000002` — the same family of mis-citation §2.8 above carried, and the fourth member found;
  and [`LIVE_SCHEMA.md`](../LIVE_SCHEMA.md) gained the two new columns, a file nothing enforces and no test
  reads, so the green lane said nothing about the omission.
- **`config/packages/nelmio_api_doc.yaml`** gains four `code` enum members. Not named in §3, and not
  optional: the enum is the published contract clients branch on.
- **[`EnvelopeCredentialRetirementTest`](../../tests/F5Sign/Envelope/Unit/Domain/Aggregate/EnvelopeCredentialRetirementTest.php)**
  gained an arm because it refused to let `claimRecipient()` go unclassified against
  [ADR-0060](../adr/ADR-0060-retiring-a-credential-whose-holder-changed.md) §2.5. The classification is
  *does not retire*, and the reason is structural rather than *"nothing happened"*: at the moment a slot is
  filled there **is** no credential to retire and there cannot be, because §2.5's mint refusal holds while
  the slot is unclaimed and the declaration is permanent. ⚑ **That exemption rests on the mint refusal**, so
  the condition is written where the classification is; the gesture that *will* retire is re-assignment,
  deferred at [`BL-193`](../BACKLOG.md).

### Decisions taken during the implementation

- **The mint refusal went inside `SigningTokenIssuance`, not into a decorator** — §4 D2's banner carries the
  full record, the measurement and why deptrac could not have decided it. This is the one deviation from a
  §4 decision, and it deviates *towards* an accepted ADR rather than away from one.
- **`Recipient::claim()` reads `declaredClaimable` and `claimedAt` as separate terms**, which every other
  caller is forbidden to do. It is the one place the conjunction is not the question: *never declared* and
  *already claimed* are different refusals with different codes (`RECIPIENT_NOT_CLAIMABLE` /
  `RECIPIENT_ALREADY_CLAIMED`), and collapsing them would answer a sender who mistyped a recipient id with
  the message meant for a genuine second claim. Written as an explicit exception in the accessor's docblock
  rather than left to look like the defect it resembles.
- **The `f5s:none` refusal reuses `INVALID_DECLARED_SUBJECT`** rather than minting a code of its own — see
  *Debt left* below, which is where that decision is owed back.
- **Bar 15 is a reflection census over the entity's declared properties, not a hand-written list.** A
  hand-list is authoring rule 5's enumeration-as-predicate: it exempts every property added after it was
  written. The census fails from both sides — adding a `role` write reports `+ role`, dropping the phone
  write reports `- phone` — and the fixture disagrees with every default it can, so *unmoved* is falsifiable.

### Decisions that needed an ADR

**None.** ADR-0057 already governs, and this task deliberately does not promote it (see the `Decision
record` row). Two accepted decisions were consulted and obeyed rather than contradicted: ADR-0058 §2.3 on
where the mint term may sit, and ADR-0060 §2.5 on classifying a new write edge against credential
retirement.

### Properties declared and not proven

- ⚠ **`infection` ran, it passes, and the number is lower than the last one on record — all three stated
  together on purpose.** `Covered Code MSI: 85%`, `MSI: 53%`, exit 0, over the configured floor by 6.06 and
  3.97 points. [`CLAUDE.md`](../../CLAUDE.md) carries 87% / 58% from 2026-08-19. ⛔ **The drop is reported,
  not explained, and must not be read as this slice weakening the suite**: there is no infection run at this
  branch's own starting point, so there is no baseline to subtract, and between the two dates the tree grew
  by several slices. A delta measured against someone else's tree is a number, not a cause.
  ⚑ **And a passing covered-MSI says nothing about §5's bars specifically** — it is a whole-tree figure, so
  it cannot distinguish a strong new bar from a weak one diluted by 2500 tests. The evidence that §5's
  guards are load-bearing is the batch sabotage pass recorded above, where each of the five reddened its own
  property and none masked another; infection is a floor, not that.

- ⚑ **`Version20260828000001::down()` HAS been exercised, on 2026-08-28, and this bullet said it had not.**
  It read *"has never been exercised, and the docblock argues its reversibility without measuring it"*, which
  was true when written: the lane migrates forward from an **empty** database on every run, so no lane pass
  can ever reach a `DROP COLUMN`.
  **Measured against a throwaway Postgres of its own** — `postgres:18-alpine` with this repo's own
  `init-test.sql` + `init-app-role.sh`, on a private network, torn down afterwards. ⛔ Deliberately **not**
  the shared cluster and **not** `make migrate-prev`: that target mounts the **main checkout**, so it would
  have run another branch's migration set, against a database other sessions are using.
  Full cycle, `up → down → up`:
  1. up → `Successfully migrated to version: …Version20260828000001`; both columns present, and typed as
     intended (`declared_claimable boolean NOT NULL`, `claimed_at timestamptz NULL`).
  2. `migrate prev` → `Successfully migrated to version: …Version20260827000001`; `information_schema`
     returns **nothing** for either column.
  3. up again → both back, and — the assertion that actually matters — `column_default` is **`(none)`** on
     both.
  ⛑ **Step 3 is the point of the exercise, not step 2.** A `down()` that drops columns is hard to get wrong;
  what could silently rot is the `DROP DEFAULT` half, because a surviving DB-side default is exactly what
  [ADR-0019](../adr/ADR-0019-database-schema-conventions.md) §4 forbids and what
  `SchemaConformanceTest::domain_columns_carry_no_database_default` exists to catch. It survives the round
  trip.
  ⚠ **What this still does not measure, and nothing can from here**: the *data* half. `down()` remains
  destructive — the columns it drops have no other source in the system, so which slots a sender declared
  and when each was filled are gone for good. The docblock says so; that half stays an argument, correctly,
  because there is nothing to run that would turn it into a result.
  Following [TASK-032](TASK-032-ordered-auth-method-list.md)'s disposition of the same gap, this still gets
  **no BACKLOG row** — but the reason has narrowed: it is no longer *"unmeasured like every other
  migration"*, it is *"measured here, and the general absence of a migration-reversibility gate is the
  repo's standing state rather than this slice's debt."*
- **The migration's backfill is covered by no test**, as §5 already states before citing any green run: the
  backfill is a column `DEFAULT` filling pre-existing rows and the lane starts empty, so the default fills
  nothing. Bar 17 is its behavioural half and is the honest substitute.
- **Bar 13 cannot fail as of this diff** and is labelled so in §5. An unclaimed slot is `PENDING` and
  `advanceAfterRecipientTerminal()` (since replaced by `Envelope::advance()` asking `EnvelopeEndingEvaluator`,
  TASK-048) filtered on `isTerminal()`, so green was the *expected* signal rather than
  evidence; its only real check is the sabotage recipe in its own docblock.
- ⚠ **Bar 5 proves the row lock works today, not that it survives — and this task is inside
  [`BL-105`](../BACKLOG.md)'s blast radius.**
  [`AuthoringLoadsUnderRowLockTest`](../../tests/F5Sign/Envelope/Application/UseCase/Authoring/AuthoringLoadsUnderRowLockTest.php)
  globs `*UseCase.php` **beside itself**, i.e. `UseCase/Authoring/` only, and `ClaimRecipientUseCase` sits in
  `UseCase/Lifecycle/`. So `findLockedForUpdate()` can be swapped for `find()` in the claim path with nothing
  red **except** bar 5, which is a single `Integration/` test rather than a census. Widening the glob to
  `UseCase/*/` is BL-105's one-character fix and is **not taken here** — taking it would redden or exempt
  every other Lifecycle use case in the same commit, which is a different change with a different review.
- ⚠ **Bar 14 moved tier: `Acceptance/` as specified → `Unit/` on the aggregate as built**
  (`EnvelopeClaimRecipientTest::a_claim_is_refused_once_the_envelope_is_terminal_and_names_nobody`, plus a
  step-complete twin). **The half the bar was about survives**: the terminal state is produced by calling
  `void()` rather than constructed, so the unreachable fixture ADR-0057 §5 rejected in its predecessor is
  still rejected here. **What is not exercised is the route in front of it** — `ClaimRecipientController`'s
  translation of `RecipientNotClaimableException` into a 409 carrying `RECIPIENT_CAN_NO_LONGER_ACT` is
  asserted by nothing. ⚑ **And it is not alone**: over HTTP the claim route asserts `204`,
  `INVALID_DECLARED_SUBJECT` and `RECIPIENT_ALREADY_CLAIMED` — so three of the five codes it can emit
  (`RECIPIENT_NOT_CLAIMABLE`, `RECIPIENT_CAN_NO_LONGER_ACT`, `RECIPIENT_CANNOT_RECEIVE_METHOD`) are proved at
  the domain and application tiers and **never through the controller's translation**. Each is proved where
  the *decision* lives, which is the tier that matters; what is untested is the mapping, and it is stated
  rather than left for a reader to infer from a tier name.
- ⚑ **Removed 2026-08-28: this bullet said the opposite of the first bullet in this same subsection.** It
  read *"**`infection` was not run on this branch.** It is the lane's fifth, opt-in gate
  (`WT_GATES="infection"`), costs minutes, and was not part of the cited run."* It was true when written and
  was left standing when the run happened, so this subsection asserted both *ran, 85% / 53%* and *was not
  run*, eleven lines apart. **The first bullet is the current one.** What survives from this one, and is
  the reason it is corrected rather than deleted: **no claim in §5 rests on mutation strength** — covered-MSI
  is a whole-tree floor, and the evidence that §5's guards are load-bearing is the batch sabotage pass.
  ⛔ It is quoted here rather than dropped because *"a docblock that contradicts itself nineteen lines down"*
  is [`CLAUDE.md`](../../CLAUDE.md) authoring rule 1's named shape, and this record has now produced one.

### Debt left, and where it lives now

| What | Home |
|---|---|
| ADR-0032 decision 7 designates `RecipientClaimed` as the event that snapshots the recipient's presented identity; ADR-0057 §2.14 and the shipped four-key payload keep it off the wire | **NEW [`BL-204`](../BACKLOG.md)** — filed at close; trigger named as whoever starts [TASK-014](TASK-014-evidence-audit-projector.md) |
| Re-assignment, and editing `fullName` / `role` / `locale` on a party already named — one question, not three | [`BL-193`](../BACKLOG.md), and §6, whose two wrong claims about it are corrected above |
| The declared subject is asserted and never recorded, so nothing answers *"which dispatcher named this consignee?"* | [`BL-73`](../BACKLOG.md) via ADR-0047 §2.6, and §6 |
| ⚠ **A `f5s:none` refusal and a malformed `F5Sign-Declared-Subject` are indistinguishable from the response body** — both are `400` `INVALID_DECLARED_SUBJECT` with a generic `detail`, because the shared handler suppresses value-object messages so a rejected value can never leak. Correct for its original reason (a rejected subject may be personal data) and **wrong here**: `f5s:none` is a reserved constant and is not personal data. A distinct term needs this repo's first UI-layer exception class, which is outside §3 | §6 (**Open follow-ups**), and **published**: the claim route's `#[OA\*]` 400 response states the ambiguity and tells the client to branch on the code and check the header it sent. **No BACKLOG row** — the durable home is §6 plus the published contract |
| The census that would keep the claim's row lock honest | [`BL-105`](../BACKLOG.md), whose enumeration now names `ClaimRecipientUseCase` |
| ⚑ **Corrected 2026-08-28.** The claimable exclusion in the activation fan-out becomes the only guard once TASK-031 lands. This row read *"— TASK-037's, not this task's"*; the exclusion shipped **here**, in `b0c5eb5`, so the guard TASK-031 must not delete is one this task wrote | [`BL-194`](../BACKLOG.md), whose subject changed the same day, plus §8 *Scope* above |
| An SMS-only claimable slot inherits the reachability hole rather than creating it | [`BL-173`](../BACKLOG.md), and §6 |
| No exit from a slot nobody will ever claim, short of `void()` | [`BL-192`](../BACKLOG.md), and §6 |
| A claimable `CERTIFIED_DELIVERY` slot is permitted by ADR-0057 §2.17 and buildable by nothing | §6, which enumerates the four blockers; [`BL-190`](../BACKLOG.md) holds the expensive one |
| The CLAIMABLE-vs-ADR-0054-§2.3 contradiction, filed before either side existed | [`BL-176`](../BACKLOG.md) — **resolved by §4 D6 and updated at close**; option (a) is what shipped |
| *"A docblock that counts its own callers or siblings"* — this branch supplied three more instances and the generalisation they earned | [`BL-165`](../BACKLOG.md), updated at close |

### The process finding this slice paid for, recorded because it will recur

⛔ **The unit that needs an owner is not the file that changes, it is the *claim* that changes** — and claims
live in files nobody is editing. Three of this branch's four commits are corrections of that shape, in four
different surfaces: a docblock counting its own callers (`DeclaredMethodDestinations`), a published `#[OA\*]`
string enumerating today's refusal codes (`MintSigningTokenController`), an exception docblock saying *"the
two"* where a third factory landed (`RecipientNotCorrectableException`), and this record's own seven stale
claims. **Authoring rule 1's retired-term sweep is structurally blind to all of them**, because none of them
retires a term to grep for — and so is a per-worker file allowlist, because the offending diff is empty
exactly where the claim lives. The sweep that finds them is per-file: **re-read the whole prose block, not the
lines that changed**, plus a separate `rg 'BL-NNN'` / `rg 'ADR-NNNN'` pass read for **tense**. Filed as the
generalisation on [`BL-165`](../BACKLOG.md) rather than proposed as an eighth authoring rule, per that rule
section's own bar — it looks mechanical, and the row already owns the *"this prose rule is lintable"* bucket.

### Five gaps a post-merge audit surfaced, recorded here and deliberately not built

**Written 2026-08-28**, after two independent audits of the merged slice. Each needs a design decision that is
not this task's to take, so each is recorded with what was measured and what the candidate answers are, and
four of the five have a `docs/BACKLOG.md` row. ⛔ **None of them is a defect in what §5's bars assert** — the
bars hold; these are questions the bars were never pointed at.

1. ⛔ **The deferred destination guard can strand an envelope with no repair but `void()`** —
   [`BL-205`](../BACKLOG.md), and the most serious of the five. §4 D6 justifies deferring
   `DeclaredMethodDestinations::guard()` on the grounds that *"a refused claim consumes none of the once-only
   fill, so fixing the body and retrying is free."* **That is true when the BODY is wrong and false when the
   PARTY cannot satisfy the declared gate.** Traced end to end through the public API: `claimable: true` with
   `OTP_SMS` and no phone → **201** (guard deferred) → `send` → claim naming a consignee with a landline, or
   with no phone → **422, permanently, no matter how often it is retried** → the correction route → **409
   `RECIPIENT_SLOT_NOT_CLAIMED`**, correctly, since the slot is still unclaimed → and **no route amends
   `authRequirement`**: `config/routes/api/envelope.php` declares 17 routes, all `GET` or `POST`, zero
   `PUT`/`PATCH`/`DELETE`. The leg stays `PENDING`, the step's ending rule (`Envelope::advance()`, asking `EnvelopeEndingEvaluator`; at the time
   `advanceAfterRecipientTerminal()`, which needed **every** member terminal) keeps the step open, so it never closes and the envelope never seals. Only `void()` remains, and it discards the
   consignor's already-collected signature. ⚑ **For an ordinary recipient the identical authoring is refused at
   the `POST …/recipients` call itself** — so the deferral does not create the bad state, it **moves the
   refusal past the point of repair**, which is the generalisable half. ⚠ The escape an integrator will
   actually take is to claim the slot naming a phone they control, which unsticks the envelope and puts the
   wrong party in the evidence. BL-205 records three candidate resolutions — a route amending `authRequirement`
   while the slot is unclaimed; refusing at authoring any claimable slot whose gate a claim could not always
   satisfy (**which kills the eCMR case D6 exists for**); or accepting it with a published warning — and
   deliberately chooses none.
2. **`resetAccessCode()` and `unlockAuth()` are unguarded on an unclaimed slot** — [`BL-206`](../BACKLOG.md).
   ADR-0057 §1 names all three sender-side post-`send()` gestures as one family and §2.3 guards one of them.
   `Envelope::resetRecipientAccessCode()` and `Envelope::unlockRecipientAuth()` each carry a single
   `status->isTerminal()` guard and then call `recordAuthUnlock()` **unconditionally**, so
   `RecipientAuthUnlocked` lands on the append-only log as a fact about a party that does not exist. ⛑ Material
   harm today is low and each reason is a separate fact that could change: nothing subscribes to that event,
   `credentialsRetiredAt` is monotonic-forward, and a null verifier fails closed at
   `gateHasNoVerifier`. **The asymmetry is ours to explain or close** — explaining is a legitimate answer, and
   `unlockAuth()`'s own docblock already carries the argument that would do it.
3. **`IN_PERSON_HOST` and `CERTIFIED_DELIVERY` claimable slots are refused nowhere** —
   [`BL-207`](../BACKLOG.md). ADR-0057 §2.10 says out-of-scope and §2.17 says permitted-but-buildable-by-none;
   **neither is enforced in code**. ⛑ Closed 2026-10-01: since ADR-0073 §2.6, `send()` refuses either role
   (`RECIPIENT_ROLE_NOT_BUILT`), slot or not, so no claim can reach one; the rest of this item is history. `Envelope::claimRecipient()` and `Recipient::claim()` carry no role
   predicate, so both author, send and claim cleanly — spending the once-only fill — and then
   `SigningSessionReader::role()` throws `roleNotInteractive` for exactly those two roles, so the leg can never
   terminate and the step never closes. ⚠ The stranding itself is inherited from [`BL-190`](../BACKLOG.md) /
   [`BL-191`](../BACKLOG.md) rather than created here; what is new is that an irreversible fill is spent on it,
   and that two ADR clauses state a boundary no predicate holds.
4. **An `ACCESS_CODE`-gated claimable slot needs a second call the claim contract never mentions** —
   [`BL-208`](../BACKLOG.md). `ClaimRecipientRequest` carries no code, and `ACCESS_CODE`'s
   `requiredDestination()` is `null`, so the guard D6 defers and re-runs **asks nothing at all** about this
   gate. ⚠ **Recorded more narrowly than the audit stated it**: the audit called the gate *unpassable*, and it
   is not — the code is settable at authoring (returned once) or afterwards via `POST …/access-code`. What is
   genuinely unavailable is the *natural* pattern, since `AddRecipientRequest`'s own `#[OA\*]` recommends a
   sender-supplied code only *"when the signer already knows the value"* and a claimable slot has no signer
   yet. So the working flow is claim → reset → transmit out of band, and nothing published says so; the failure
   is quiet, surfacing to the **signer** at `gateHasNoVerifier` long after the sender has moved on.
5. ⛑ **§2.7's known gap is sharper than *"the invitation is deferred"*, and the sharp version is the one that
   matters.** Nothing subscribes to `RecipientClaimed` (`rg RecipientClaimed src/ config/` reaches the
   aggregate that records it and nothing that reads it), so a claim invites nobody — **but only in one of three
   orderings, and it is *the* one the feature exists for**:
   - a claim landing **before `send()`** *is* invited, because `send()` activates step 1 afterwards and the
     fan-out reads envelope state fresh at reactor time;
   - a claim landing **before the slot's step activates** *is* invited, for the same reason, when that step
     opens — which is the ordering §2.7's not-yet-activated guard is written about;
   - a claim landing **after its step is already active** fires nothing, because the only trigger that would
     have invited them has already been consumed.
   ⛔ So this is not *"the invitation is deferred to TASK-037"*; it is **"the invitation works except in the
   case ADR-0057 §1 was written for"** — the eCMR consignee named while the goods are in transit, on a step
   that is already open. ⚠ **And whether a claim is invited at all currently turns on relay timing**: the
   activation event travels event log → relay → broker, so a claim racing that path lands on either side of it
   by chance, and an at-least-once **redelivery** of `RecipientStepActivated` after a claim would invite the
   party that the first delivery skipped. **No BACKLOG row** — the durable home is ADR-0057 §2.7 plus
   TASK-037's own record, both of which now carry this ordering rather than the flat *"nothing fires"*.
