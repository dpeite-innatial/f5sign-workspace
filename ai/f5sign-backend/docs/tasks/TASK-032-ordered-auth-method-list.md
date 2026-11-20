# TASK-032 — The ordered method list: giving a stuck signer a move that is not the sender

| Field | Value |
|-------|-------|
| **Status** | ✅ **Merged into `develop` at `c79ce3d` and pushed** — all eleven of ADR-0054's decisions green. The branch `feat/ordered-auth-method-list` carried nine commits from `develop` at `e179a4a`: `91b4e3c` (the predicate + its mirror), `ab459a9` (the slot types, the `jsonb` migration, the authoring request, the presenter), `dbaf07a` (nine gate findings), `47dd25c`, `1bab9ee` (the ceremony — chosen method, effective-head resolution, the route's `method`, the descriptor), `2fc7fbc` (ADR §5/§6 + a four-surface sweep), `34b4a29` (phase-3 gate findings), and the presentation mode that closed the set; `97d7e3c` and `5daef92` landed on `develop` **after** the merge, both prose sweeps over the same re-cut. Green on the **worktree lane** (`WT_GATES="lint arch phpstan test" make -C ../f5sign-infra wt-backend src=$(pwd)`), the only harness that validated that tree: lint `0 of 986` · Deptrac `Violations 0` · PHPStan L9 `[OK]` · `OK (2294 tests, 10882 assertions)`, against a `develop` baseline of `2245 / 10587`. ⛔ **Infection was NOT run** (opt-in fifth gate, cannot share the lane with the suite) — a declared gap, not a pass. **Bar 8 remains unmet and unclaimed** ([`BL-179`](../BACKLOG.md)). ⛔ **Merged is not adopted, and that distinction is the whole answer to whether this task is done**: no sender can enable free choice until an authoring control exists in `f5sign-dashboard`, and the adoption state of both front ends is tracked in [the frontend handoff](../frontend-handoff/TASK-032-ordered-auth-method-list.md), not here. ⚑ **Two clauses of this row were retired on 2026-08-21**: *"NOT complete … §2.4, the presentation mode, is NOT built"* — §9 D9 now records what was built and why the shape is what it is — and *"NOT merged"*, which outlived the merge commit above. Verify against `git log` rather than trusting this row. |
| **Type** | **Forward build** — it widens a declaration, and with it the ceremony that reads it. The eleven decisions it realizes are already taken; what is left is shape, migration and tests, not design. |
| **Why** | A recipient whose delivered code does not arrive has **no move**. [`AccessGate`](../../src/F5Sign/Envelope/Contract/Type/AccessGate.php) and [`SigningGate`](../../src/F5Sign/Envelope/Contract/Type/SigningGate.php) name one method each, and [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.7 forbids falling back to another channel — correctly, because an automatic switch would silently downgrade the declared strength that feeds the signature-level projection. So every recovery is sender-side: the signer waits for someone who is not there, having done nothing wrong. |
| **Builds on** | **[TASK-030](TASK-030-sms-delivery-channel.md) and [TASK-023](TASK-023-sms-codes-and-recipient-phone.md), both hard dependencies rather than preferences** — the first is the only second channel in flight, the second is the destination without which no `OTP_SMS` can be declared for anyone. Reused unchanged: [TASK-022](TASK-022-delivered-codes-over-email.md) (the entire delivered-code ceremony, the cooldown, the three-key limiter, the correction path), [TASK-021](TASK-021-two-gate-auth-model-and-access-gate.md) (the two-gate model and the lockout generation), [ADR-0053](../adr/ADR-0053-access-grant-recovery.md) (the `recover` intent this composes with). |
| **Decision record** | **[ADR-0054](../adr/ADR-0054-ordered-auth-method-list.md)**, `Proposed` — it amends [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.1 and narrows §2.7, and carries all eleven decisions with their rejected alternatives. ⚑ **This slice is what promotes it**: landing the bars in §6 means the same changeset rewrites that ADR's `Status`, `Enforced by` and `Realized in` — not a later one (`CLAUDE.md` authoring rule 7). |
| **Delivery bar** | A recipient declared `[OTP_EMAIL, OTP_SMS]` in escalation mode receives the email code automatically; at `nextResendAt` the SMS option appears; choosing it mints an SMS challenge, kills the email code, does **not** restart the cooldown, and the completed ceremony records `OTP_SMS` as the executed method. A recipient declared `[OTP_EMAIL]` behaves exactly as they do today, byte for byte on the wire. |
| **Sibling — do not scope independently** | [TASK-030](TASK-030-sms-delivery-channel.md) authors SMS copy for every purpose including `AUTH_OTP`. If that authoring is dropped there, it lands here at full price and this task stops being about selection. |

---

## 1. Why this task exists

[ADR-0054](../adr/ADR-0054-ordered-auth-method-list.md) §1 states the gap; this record does not restate it. What
belongs here is the reason it is a task rather than a paragraph: **the shape change is cheap and its blast radius
is not.** `AccessGate` is a `Contract` type, so widening it touches the authoring request, the persistence, the
cross-BC read port, the descriptor and the published OpenAPI in one slice — and the ceremony reading it is the
one path where a mistake strands a signer at a gate instead of failing a test.

**The half that is genuinely new is small**: an ordered list where there was one value, a chosen-method fact on
the session, and one predicate minted on the side of a boundary that cannot see the one that exists.

## 2. What already exists (reuse, do not rebuild)

- **The ensure/mint split is exactly the selection mechanism.**
  [`IssueAuthChallengeUseCase`](../../src/F5Sign/Session/Application/UseCase/IssueAuthChallengeUseCase.php)
  already separates *ensuring* a challenge exists (mount the screen, send nothing) from *minting* one (a re-send,
  which invalidates the previous code). Choosing a method is a mint that names one. **No new state machine.**
- **The challenge already records the executed method.**
  [`AuthChallenge`](../../src/F5Sign/Session/Domain/Entity/AuthChallenge.php) holds
  `private ExecutedAuthMethod $method` and exposes `method()`, so evidence and the signature-level projection are
  correct for free the moment the executed method can differ from the declared head.
- **The cooldown is already per gate rather than per method, by construction.**
  [`DeliveredCodePolicy::nextIssuanceAllowedAt()`](../../src/F5Sign/Session/Application/Service/DeliveredCodePolicy.php)
  takes only `$issuedAt` and never looks at the method; its own docblock says so. ⚑ **So ADR-0054 §2.8 needs a
  test, not a change** — the risk is a later "fix", not today's behaviour.
- **The re-send instant is already published.** `nextResendAt` is on the wire, and under escalation it is the same
  instant at which the alternatives unlock. The signer app needs no second clock.
- **The three-key limiter is already per method on purpose** — `otp_email_*` today, `otp_sms_*` from
  [TASK-030](TASK-030-sms-delivery-channel.md) with its own numbers. Nothing about ADR-0054 §2.9 changes it.
- **The authoring guard already exists and asks the other half of the question.**
  `AddRecipientUseCase::guardDeclaredMethodsAreAvailable()` refuses a method this **deployment** cannot run
  ([ADR-0013](../adr/ADR-0013-deployment-mode-duality.md)); the per-recipient destination check joins it there.
- **The requirement is already re-read fresh at every verification.**
  [`RecipientAuthContext`](../../src/F5Sign/Session/Application/Query/RecipientAuthContext.php) carries
  `public int $authGeneration` and `public ?string $destination`, deliberately not cached at session start — which
  is what makes a sender-side reset take effect immediately, and what a per-method destination extends.
- **The mirror and its rot-guard are built.**
  [`ExecutedAuthMethod`](../../src/F5Sign/Session/Contract/Type/ExecutedAuthMethod.php) is Session's
  anti-corruption copy of Envelope's enum ([ADR-0004](../adr/ADR-0004-cross-bc-anti-corruption-layer.md)), and
  `ExecutedAuthMethodMirrorTest` already fails the build when a member is added on one side only. The new
  predicate rides that mechanism rather than inventing one.
- **The descriptor already masks server-side.** `GetAuthDescriptorController` publishes `masked_destination` via
  `MaskedDestination::of()` and hands it over already masked — the client never reconstructs it.

- **The OTP delivery path already takes its destination *with* the request**, so a second declarable
  method needs no new read there.
  [`OneTimeCodeDeliveryService::request()`](../../src/F5Sign/Notification/Application/Service/OneTimeCodeDeliveryService.php)
  builds its `ContactPoint` from `$request->destination` and never dereferences the recipient — which is
  [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.7's shape (the method names its channel
  **and** its destination), not a coincidence. ⚑ Reported by the TASK-030 session and verified here against
  `develop`: when `DeliveryChannel::SMS` lands, `EMAIL` and `SMS` share one arm of that `match` for exactly
  this reason. ⚠ The three envelope-arc use cases are the **opposite** case — they throw for want of a
  destination, because `Recipient` has no phone — and what closes those is
  [TASK-023](TASK-023-sms-codes-and-recipient-phone.md)'s column, not this slice.

**What does not exist:** any list anywhere; `AuthMethod::deliversCode()` on the Envelope side (the predicate lives
only on Session's mirror, which `EnvelopeApplication` cannot import — [ADR-0054](../adr/ADR-0054-ordered-auth-method-list.md) §2.2);
any tenant policy store ([`BL-120`](../BACKLOG.md)); any second declarable delivered method.

## 3. What gets built

**The slot types.** `AccessGate` / `SigningGate` widen from `?AuthMethod` to an ordered non-empty list, keeping
their neutral arms untouched. A one-element list is the current shape, so `AuthRequirement`'s structural rules and
every neutral case survive as written.

**The column.** `auth_access_gate` / `auth_signing_gate` are `TEXT` today. They become an ordered `jsonb` array of
method values under expand / backfill / contract with no database default on a domain-authored column
([ADR-0019](../adr/ADR-0019-database-schema-conventions.md) §4). ⚠ **The backfill writes rows the domain then
reads** (`CLAUDE.md` authoring rule 6): every existing declaration becomes its one-element list, which is
value-preserving in every aggregate state — draft, in-flight, terminal — because the list of one *is* what the
column already means. That is the property to state in the migration docblock, not "we wrapped it in an array".

**The predicate.** `AuthMethod::deliversCode()`, plus the mirror test extended to assert both predicates agree
member by member.

**The authoring refusal.** Per declared method, against the destination that method needs, inside the existing
guard — which is also the fix [`BL-162`](../BACKLOG.md) asks for, written once instead of twice.

**The mode.** Resolved at authoring and frozen beside the list on the recipient; default escalation, no tenant
tier yet. Under free choice route 4 refuses with `409 AUTH_METHOD_NOT_CHOSEN` when no method has been named
— see §9 D9 for the deploy-order rule that refusal carries.

**The chosen method.** A nullable executed-method fact on the signing session, set when the signer selects,
surviving `AWAITING_REAUTH`, read as the effective head. It is Session state, never Envelope's.

**The selection on the wire.** `POST /api/v1/signing/session/auth/otp/send` grows an **optional** `method`
alongside the `recover` boolean [ADR-0053](../adr/ADR-0053-access-grant-recovery.md) added. ⚑ **Additive, so
unlike [TASK-029](TASK-029-session-credential-and-refresh.md) this does not break the deployed signer** — omitting
it means *the current head*, which is exactly today's behaviour. A method absent from the gate's declared list is
a refusal, not a silent fallback to the head.

**The descriptor.** Route 3 publishes one entry per declared method — method plus its masked destination — for the
live gate and for the `access_gate` block, with the `#[OA\*]` strings updated in the same edit. Those strings are
emitted verbatim into the spec the front ends ratify, so they are contract, not comments.

**The handoff.** `docs/frontend-handoff/` gets the record: the new descriptor shape, the optional `method`, and the
rule that the alternatives unlock at `nextResendAt` under escalation and immediately under free choice.

## 4. Scope

**In scope:** the two slot types, the migration, the predicate and its mirror test, the authoring refusal, the mode,
the chosen-method fact, the route field, the descriptor, the OpenAPI strings, the handoff, and the tests of §6 —
plus the ADR-0054 realization edits named in the header's *Decision record*.

**Out of scope:**

- **The tenant tier.** No policy store exists ([`BL-120`](../BACKLOG.md)); the default is a constant read at the
  single point that already reads the others. The shape it will take when it arrives is
  [ADR-0054](../adr/ADR-0054-ordered-auth-method-list.md) §2.4 and it is a task of its own.
- **The per-recipient preference.** A recipient is not a user of this platform and has nowhere to state one — the
  same argument [TASK-031](TASK-031-channel-selection-beyond-email.md) §4 makes for notifications.
- **`WHATSAPP` and `VOICE`.** They are in the catalog and admissible in a list by
  [ADR-0054](../adr/ADR-0054-ordered-auth-method-list.md) §2.2, and neither has a channel. Each is a
  [TASK-030](TASK-030-sms-delivery-channel.md)-shaped task.
- **Any automatic fallback.** [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.7 stands, and
  [ADR-0054](../adr/ADR-0054-ordered-auth-method-list.md) §7.1 records why the list does not reopen it. ⛔ This is
  the change that makes reintroducing it look natural; the guard is a test plus that section, not a mechanism.
- **`SubstituteAuthMethod`.** Still parked, still owing the strength ordering
  ([ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.11).
- **Bounding the list's length.** See §7.

## 5. Key decisions

All eleven are [ADR-0054](../adr/ADR-0054-ordered-auth-method-list.md) §2 and are **not** restated here — a second
home for a decision is a second thing to keep true. What this record adds is the two the ADR delegates to
realization:

- **The list is a `jsonb` array on the existing rows, not a child table.** The gate's members carry no data beyond
  their order — destinations live on the recipient, not on the gate — so a child table would buy a join on a path
  read at every verification and nothing else.
- **The chosen method lives on the session row, not on the challenge.** A challenge is consumed and replaced on
  every issuance ([ADR-0037](../adr/ADR-0037-notification-supporting-bc.md)'s cause convergence), so a fact stored
  there would be lost by the very act it must survive.

## 6. Verification

Named as properties with the harness that can actually observe each one (`CLAUDE.md` authoring rule 4 — a gate says
nothing about a property its harness cannot reach):

1. **The predicates agree.** Unit, over both enums, every member. Sabotage: add a member to one side only and watch
   the build redden.
2. **A declared method with no destination is refused at authoring.** Application tier, and the discriminating case
   is the one where the **head is satisfiable and a later member is not** — a fixture whose members always agree
   cannot fail.
3. **Changing method does not restart the cooldown.** Acceptance, over HTTP. Sabotage: make
   `nextIssuanceAllowedAt()` take the method and watch it redden.
4. **A method absent from the signing gate's list is unreachable from a choice made at the access gate.**
   Acceptance, driving both gates.
5. **The choice survives `AWAITING_REAUTH`.** Integration, with the clock moved past `REFRESH_LIFE`.
6. **The descriptor's key set is closed.** Acceptance asserting the **exact** key set, not merely the presence of
   the new ones — PHPStan L9 rejects a missing key and accepts an extra one, so an absence check would wave a new
   field through (`CLAUDE.md` authoring rule 5).
7. **A one-element declaration is unchanged on the wire.** Acceptance, byte-comparing the descriptor against
   today's shape for a recipient declared `[OTP_EMAIL]`.
8. **The backfilled row means what an authored one means.** Integration over a migrated fixture in each aggregate
   state, not only a draft.

## 7. Open follow-ups (track, don't solve here)

- **Nothing bounds the list's length**, and each member is its own limiter budget. Four declared methods is four
  budgets and, on paid channels, four times the ceiling. It probably belongs in the authoring surface rather than
  on an invoice.
- **The tenant mode tier** — `session.tenant_default`, the shape [ADR-0054](../adr/ADR-0054-ordered-auth-method-list.md) §2.4
  names, alongside [`BL-120`](../BACKLOG.md).
- **The chosen method has no expiry of its own.** It dies with the session and nowhere else; a future change making
  sessions long-lived should revisit it.
- **[`BL-168`](../BACKLOG.md) is adjacent and independent.** A contact correction leaves the live challenge
  answerable at the old destination. [ADR-0054](../adr/ADR-0054-ordered-auth-method-list.md) §2.11 makes that
  exposure *detectable* by publishing the destinations; it does not fix it, and it should not be folded in here.

---

## 9. What actually happened — deviations, and the two things left undone

Appended rather than folded into §1–§8, because those numbers are anchors cited from other documents.
Written from the branch, not from the plan.

### D9 — §2.4, the presentation mode, and the contract question that had to be answered first

⚑ **This entry recorded the opposite until 2026-08-21.** It read *"§2.4 is NOT built, and the reason is
a CONTRACT one"*, and the reason it gave was sound: free choice means *nothing is issued until the
signer selects*, so route 4 — the path the shipped signer app calls **on mount** — has to answer
something when no method has been named, and that screen contract had deliberately never been agreed.
Building the backend half alone would have given senders a mode whose recipients then met a `409` on
mount against the deployed client, which is worse than not having the mode.

**What unblocked it was the conversation that entry named**, held with the `f5sign-signer` session on
2026-08-21. Three things came out of it and the code matches them rather than the other way round:

1. **The descriptor publishes `selection` inside EACH gate block** — beside `methods` in the live-gate
   object and inside `access_gate` — and it is `required`, like the other five members. Both blocks
   carry the same value today because the mode is per recipient; per-block anyway, so the recovery
   control never reads another block to learn its own mode and a per-gate mode later needs no shape
   change. ⚑ `required` rather than optional was their explicit ask, with a reason: an optional field
   arrives by inertia, and six of their descriptor fixtures had already been caught omitting two
   required members.
2. **Under free choice, before the first pick, there is no challenge** — therefore no
   `code_expires_at` and no `next_resend_at`, and they draw no clock.
3. **Changing method during the cooldown stays allowed** (the cooldown is the gate's, §2.8), so their
   selector stays visible while the clock runs. Nothing was added that hides or refuses it.

⛔ **THE DEPLOY ORDER IS THE PART THAT MATTERS, and it is why the 409 ships before anything can reach
it.** `AUTH_METHOD_NOT_CHOSEN` is unreachable on the deployed path today — no sender can enable free
choice until an authoring client offers the field. It ships first because the signer app routes any
**undeclared** 4xx to `/invalid`: an undeclared refusal would tell a signer holding a perfectly good
link that their link is invalid, and they have two existing scars from exactly that. The order is
**publish the code → the signer app declares it → only then may anyone enable free choice**, and it is
stated in bold in [the frontend handoff](../frontend-handoff/TASK-032-ordered-auth-method-list.md)
rather than only here.

**Two realization shapes are decisions rather than mechanics.** The refusal lives on a **second**
resolver method (`resolveForIssuance()`) instead of inside `resolve()`, because route 3's descriptor
asks the same resolver and must keep answering `200` for a free-choice recipient — presentation and
issuance are two questions and a 4xx on the first is the `/invalid` hazard above. And the mode is
**mirrored** into Session (`PresentedSelectionMode`) rather than imported, because `SessionUI` is
granted `SessionContract` and `SessionApplication` and **not** `EnvelopeContract`; handing the value
across as a bare string would have cleared deptrac only by being invisible to it.

⚠ **One wire asymmetry is worth knowing before you meet it.** The signer-facing descriptor publishes
the descriptor lower-cased what every other surface spelled in upper case — retired the same day, after a measurement in the consuming repo showed that case already carries meaning there (wire vocabulary upper, client state lower), so the lower-case form would have lied about its provenance. Both surfaces now publish `ESCALATION` / `FREE_CHOICE`.

▶ **What is still owed is the TENANT TIER, not the mode**: there is nowhere to state a default, so
every recipient's mode is authored per request ([`BL-120`](../BACKLOG.md), and §7).

### D8 — bar 8 is unmet, and was deliberately not claimed

No harness here can write a pre-migration row and run the migration over it. The two tests available
are worthless in opposite directions — one tautological, one reimplementing the migration's `CASE` in
a double — so the bar is reported open rather than met with a green that measures nothing.
[`BL-179`](../BACKLOG.md) holds it, including what a real harness would have to do.

### The reading of ADR-0054 §2.2 this slice had to fix

§2.2 read literally forbids an `ACCESS_CODE` gate, contradicting §2.1 in the same breath. Taken as an
**arity** rule instead: exactly one member may be anything the slot allowed; two or more must all
deliver a code and none may repeat. The full argument is in
[`AccessGate`](../../src/F5Sign/Envelope/Contract/Type/AccessGate.php)'s class docblock, which is
where a reader meets the rule.

### The authoring request keeps BOTH spellings

`access_method` survives beside `access_methods`, and sending both is a 422. Additive rather than
replacing, so no deployed client breaks; the retirement is §7's. ADR-0054 §3.2 contemplated a
breaking authoring change and this slice declined to take it.

### Four defects this branch found that were not in the plan

1. **`auth_status.method_used` published the DECLARATION** under a premise this task falsified (*"a
   gate declares exactly one method"*). Its own comment already named the condition that would retire
   it; that condition was this task. Now reads the executed method.
2. **The hand-maintained `Recipient.auth` schema was not updated**, and `OpenApiSpecTest` structurally
   cannot see it — its key-set census does not descend into nested objects.
3. **Two new list rules answered 400, not 422**, because only two of the slot constructors' four
   refusals had been mirrored at the edge.
4. **The whole plural REQUEST surface had no test at all** — measured by `task-validate-backend`, not
   reviewed. `AuthRequirementRequestTest` now holds it; two sabotages, one failure each.

⚑ Numbers 2, 3 and 4 were found by the gate skills **after** implementation rather than before, which
is a process deviation of this run: phase 2 was implemented inline and phase 3 was run late. The
findings would have been the same; they would have been cheaper.

### The guard whose docblock was wrong twice

`MapsAuthRequirement`'s `array_is_list()` check is narrower than two successive versions of its own
prose claimed — PHP coerces numeric string keys, **and** `jsonb` normalizes key order, so neither
`{"0":…}` nor `{"1":…,"0":…}` is refused and neither needs to be. Both narrowings were found by the
test failing, not by reasoning. Stated at both homes.

### Owed, with homes

| What | Home |
|---|---|
| the tenant tier for the presentation mode (the mode itself is built) | §7 and [`BL-120`](../BACKLOG.md) |
| bar 8 | [`BL-179`](../BACKLOG.md) |
| nothing bounds a declared list's length | [`BL-178`](../BACKLOG.md) |
| unknown request fields dropped silently, all 20 endpoints | [`BL-177`](../BACKLOG.md) |
| CLAIMABLE recipients vs §2.3 — ⚑ **decided and built 2026-08-28**, option (a): the guard is deferred at authoring **keyed on the declaration alone** and re-run entire at the claim. §2.3's refusal for every undeclared recipient is unchanged, so `BL-162` stays closed | [`BL-176`](../BACKLOG.md), which carries what shipped · [ADR-0057](../adr/ADR-0057-claimable-recipient-slot.md) §2.13 + [TASK-036](TASK-036-claimable-recipient-slot-and-claim.md) §4 D6 |
| Infection not run on this branch | this row and the `Status` field |
| migration `down()` exercised by nothing | stated here; no row — it is the standing state of every migration in this repo, not this one's debt |
