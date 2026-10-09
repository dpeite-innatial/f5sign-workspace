# Spec-claims report — TASK-050

Checked against: `feat/task-048-how-an-envelope-ends` @ `786c39c2` (TASK-048 implemented, gates running;
TASK-049 not started). Task file: `docs/tasks/TASK-050-a-step-says-how-much-agreement-it-needs.md`. Decision
record: `docs/adr/ADR-0073-step-policy-expiry-and-what-an-unagreed-envelope-keeps.md`.

This supersedes the stale `var/task-runner/TASK-050/old-0929/spec-claims.report.md` (dated 2026-09-25,
before the ADR's 2026-09-28 re-cuts and before TASK-048 landed).

## Method

Read the task, the ADR, `var/task-runner/TASK-048/plan.md`, and the parked
`var/task-runner/TASK-048/task-050-quorum-decline-retirement.patch`. Then read/grepped the actual source for
every "what already exists" claim, every mechanism the task leans on, and every verification bar, rather than
trusting names. TASK-049's task file was read in full to determine the real dependency boundary.

## Headline

TASK-050's "what already exists" and "already built, ahead of this task" claims are, to an unusually high
degree, **accurate** — the pure decision rules (`StepCompletionEvaluator`, `EnvelopeEndingEvaluator`,
`ReleaseReasons`, `EndingScenarioCatalog`, the same-facts census) genuinely exist, already implement ADR-0073
almost verbatim, and already pass at the pure-evaluator tier. TASK-048 built substantially more of the
groundwork (`RecipientOutcome::RELEASED`, the `RELEASED`/`release_reason`/`released_by` OpenAPI census,
`EnvelopeCompleted`'s declined/released payload, the two-process harness, the `D-T1` transitional mode, the
parked decline-retirement patch) than the task's own "Builds on" table credits by name. One genuine gap was
found (§2 below) and two minor cross-reference imprecisions (§3). No verification bar was found unmeetable,
and no external-system claim needed measuring (nothing in this task's scope touches EU DSS, SMS, or a
browser).

---

## 1. Claims verified TRUE (representative sample, with evidence)

| Claim (§) | Evidence |
|---|---|
| §3.2 "Already built, ahead of this task": `StepCompletionEvaluator`, `EnvelopeEndingEvaluator`, `ReleaseReasons` exist and implement ADR-0073 §2.4/§2.6/§2.7/§2.8 | `src/F5Sign/Envelope/Domain/Service/StepCompletionEvaluator.php`, `EnvelopeEndingEvaluator.php`, `ReleaseReasons.php` — read in full; logic matches the ADR clause-for-clause (counting order, veto rule, `MEMBER_NOT_REACHED`, cause precedence, `DELEGATED`/`SKIPPED` fail-closed) |
| §3.2 "the catalog... same-facts census in `StepCompletionEvaluatorTest`" exists | `tests/F5Sign/Envelope/Unit/Domain/Service/StepCompletionEvaluatorTest.php:67-171` — `everyClosedStep()` is a real 5-policy × 5³-member-fact census (625 cases), already asserting step-deadline-close ≡ expiry-close outcome/cause/release_reason. This is the verification bar already met at this tier. |
| §3.2 D-T1 transitional mode (`InformationalMembers::HOLD_THEIR_STEP`) is what the aggregate currently runs, and TASK-050 deletes it | `src/F5Sign/Envelope/Domain/Aggregate/Envelope.php:2475-2478,2535` wires `new StepCompletionEvaluator(InformationalMembers::HOLD_THEIR_STEP)`; `InformationalMembers.php`'s own docblock says "TASK-050... deletes this type." Default evaluator ctor arg is already `NEVER_HOLD` (`StepCompletionEvaluator.php:40`) — the pure predicate is already ADR-compliant; only the aggregate's wiring needs to flip. |
| §1/§3.1 `AddStepRequest` accepts ordinal only | `src/F5Sign/Envelope/UI/Http/Request/AddStepRequest.php` — one `int $ordinal` field, nothing else |
| §2.6/§3.1 "No route sets `min_signatures` today... the migration asserts no step carries it" | `Step::create()` has exactly one caller (`Envelope::addStep()`, line 594), which forwards `$minSignatures` from `addStep()`'s own optional param — no controller/request path supplies a non-null value. The `min_signatures` column exists since the baseline migration `Version20260713000002.php` with no CHECK constraint yet — consistent with "the migration [TASK-050 adds] asserts no step carries it and adds `CHECK`". |
| §3.1 D12 unanimity refusal, "more than one blocking role", "no blocking member" already implemented | `EnvelopeEndingEvaluator::refusalsAtSend()` (lines 84-119) already emits `MINIMUM_NOT_BELOW_MEMBERS` when `minimum >= blocking`, `MORE_THAN_ONE_BLOCKING_ROLE`, `NO_BLOCKING_MEMBER`, `ROLE_NOT_BUILT` (which is what refuses `IN_PERSON_HOST`/`CERTIFIED_DELIVERY` once the aggregate runs `NEVER_HOLD`; `RoleStanding::of()` maps both to `NOT_BUILT`) |
| §1 `Step::isQuorumStep()`/`isQuorumMet()` exist as named | `src/F5Sign/Envelope/Domain/Entity/Step.php:120-127` |
| §1 `DECLINE_NOT_OFFERED_IN_QUORUM_STEP` still a published `ProblemCode`, still thrown | `config/packages/nelmio_api_doc.yaml:116`; `SigningSessionStateException::declineNotOfferedInQuorumStep()` (`SigningSessionStateException.php:158`); still called from `SigningSession::guardDecline()` and `DeclineSignatureUseCase.php:98,114` |
| §3.3 the parked patch retires it correctly and is self-consistent with the current tree | Read `task-050-quorum-decline-retirement.patch` in full against the live files it touches (`SigningSession.php`, `SigningSessionStateException.php`, `DeclineSignatureUseCase.php`, `DeclineSignatureController.php`, `GetEnvelopeContextForRecipientHandler.php`, `EnvelopeContextView.php`, `RecipientEnvelopeContextView.php`, `RecipientAuthContext.php`, `RecipientAuthContextReader.php`, `config/packages/nelmio_api_doc.yaml`) — every hunk applies against a real, matching current line; it is `git apply`-able as-is |
| §1 `RecipientOutcome::DELEGATED`/`SKIPPED` have no writer | `RecipientOutcome.php` docblock says so explicitly and still holds; `RecipientOutcome::RELEASED` already exists (TASK-048) |
| §1 `SigningSessionReader::role()` refuses `IN_PERSON_HOST`/`CERTIFIED_DELIVERY` | `SigningSessionReader.php:506-515` |
| §1 `NotifyActivatedStepRecipientsUseCase` skips an unclaimed slot before minting | Read in full — `if ($recipient->isUnclaimedSlot()) { continue; }` before the token-issuer call |
| §1 `RecipientDeliveryTrace` per-destination, `DELIVERED` has no writer | `RecipientDeliveryTrace.php` read in full; only reference to `RecipientDeliveryState::DELIVERED` outside its own enum is the comparison inside `observing()`, never a write |
| §3.4 "`RecipientReleased`... now also triggers Session's revocation... new here: until now the only revocation (`OnEnvelopeVoided`) is envelope-wide" | `OnEnvelopeVoided.php` read in full — reacts only to `EnvelopeVoided`, dispatches `RevokeEnvelopeSessions` (envelope-wide). No `RecipientReleased` subscriber exists anywhere in `src/` (grep: only the event class itself and the aggregate that emits it). Confirmed real, unbuilt work. |
| §3.7 `NotificationPurpose::ENVELOPE_COMPLETED` exists, classified "carrying no means to act" | `NotificationPurpose.php` — `carriesMeansToAct()` returns `false` for it; `namesItsOwnChannel()` also `false` |
| §3.7 the copy-ready notice is TASK-050's to build on top of the existing completion notice | `NotifyCompletedEnvelopeRecipientsUseCase.php` already gates on `$envelope->outcome !== EnvelopeOutcome::AGREED` (D-T10) and mints no link, with its own docblock saying explicitly: "who is told of its sealed copy, and with what link, is TASK-050's copy-ready notice" |
| §2 `EnvelopeRosterDeclared`'s `RosterStepShape` exists, carries `min_signatures`, is a real extension point for veto/deadline | `EnvelopeRosterDeclared.php:61` `@phpstan-type RosterStepShape array{step_ordinal: int, step_id: string, min_signatures: int|null, recipients: ...}` |
| §5 "Contract census" — `RELEASED`, `release_reason`, `released_by` already published in OpenAPI | `config/packages/nelmio_api_doc.yaml:458,463,574,579` (built by TASK-048) |
| §5 two-process harness pattern is reusable | `tests/F5Sign/Envelope/Integration/EnvelopeConcurrentAppendTest.php` exists |
| §5 "the aggregate ends each story as the story says" bar currently excludes exactly the TASK-050/049 stories, correctly and by name | `tests/F5Sign/Envelope/Unit/Domain/Aggregate/EnvelopeEndingStoriesTest.php` — `EXPECTED` lists 4 stories; `expressibleStories()` filters via `EndingScenario::isWithoutClocksOrPolicyFlags()`; the `TriggerKind::CLOCK`/`CLOSE_NOW` branches explicitly `self::fail('not expressible before TASK-049/050')`. This is the verification bar's starting point, not a false claim — it shows the exact, correctly-scoped work TASK-050 does (delete the filter, extend `EXPECTED`). |
| ADR-0073 §2.11/§2.4 EnvelopeCompleted already carries `declined`/`released` (ids + enums only) | `src/F5Sign/Envelope/Contract/Event/EnvelopeCompleted.php` — constructor already has `array $declined = []`, `array $released = []` with `ReleaseReason`/`ReleasedBy` typed entries; `EnvelopeAgreed.php` already exists |
| TASK-049 confirmed not started | No `expires_at`/`expiresAt` reference in `src/F5Sign/Envelope/` (all hits are Session/JWT, unrelated); no funnel/sweep/schedule class for envelope endings exists (`PendingCustodySweep` is Storage's, unrelated); `Step` entity/migration has no deadline column; `EnvelopeClosedBySender.php` and `EnvelopeExpiryExtended.php` do not exist yet |

## 2. False claim — BLOCK

**Claim (§3.2):** *"Its docblock states ADR-0073 §2.4: every clock only closes a step and evaluates it here. A
`LOAD-BEARING.md` entry forbids a special evaluation for expiry or any new clock."*

The first sentence is **true**: `StepCompletionEvaluator.php`'s docblock (lines 16-20) does state exactly this.

The second sentence is **false** on this tree. `docs/LOAD-BEARING.md` has no entry about clocks, the
same-facts principle, `StepCompletionEvaluator`, or `EnvelopeEndingEvaluator` — grepped for "same facts", "one
predicate", and "ADR-0073" (the only ADR-0073 hits are in §1.5/§1.17/§1.16-adjacent entries about the opening
write and artifact append, unrelated to the clock-evaluation rule). The document's `§1.*` entries run through
`§1.20`; none of them is this one. ADR-0073 itself only *asks* for this guard — §2.4 says "Held by... a
`LOAD-BEARING.md` entry forbidding a special evaluation for any clock," and §5 ("Enforced by") lists it under
what "the tasks owe," not what exists.

Why this matters here specifically: every other `LOAD-BEARING.md` reference in this codebase's docblocks cites
an exact `§N.M` (e.g. `docs/LOAD-BEARING.md §1.16` in `OnEnvelopeVoided.php`, `§1.5`/`§1.17` in
`EnvelopeCommandInterface.php`'s docblock). This is the one reference in the task with no section number,
which is itself a tell that it's aspirational rather than a citation — but the sentence is still phrased as a
present-tense fact ("forbids") in the same paragraph that opens "Already built, ahead of this task." An
implementer skimming that paragraph could reasonably read it as already-done and skip adding the entry,
leaving ADR-0073 §2.4's own "Enforced by" line permanently unfulfilled and violating this repo's authoring
rule 7 (landing/realizing a record's guard belongs in the changeset that discharges it). This is the same
*shape* of defect this role exists to catch (TASK-046's `SEALING_FAILED`): a guard/mechanism described as
already in place that does not exist.

Mitigating context: this is a one-entry, low-cost fix (add a `docs/LOAD-BEARING.md` §1.2x entry citing
`StepCompletionEvaluator`/`EnvelopeEndingEvaluator`), not a structural problem, and the actual runtime rule it
protects is already correctly implemented and tested (§1 above). Flagged as `block` because it is a false
claim about present state the implementation could build on (by omission); the fix is cheap once flagged.

## 3. False claims — WARN (minor, self-correcting via the parked patch)

**a) §1/§3.3 — "`Envelope::recordRecipientDecline()` throws for a quorum step"; "Both refusals of a decline in
a quorum step are removed."**

`§1` frames this as "Measured on `develop` at `3bda20a`, 2026-09-24" — i.e. explicitly historical, and on that
commit it was likely true. On **this** tree (post-TASK-048), it is no longer accurate: `admitDecline()`
(`Envelope.php`, admission path) does not special-case a quorum step at all — it defers entirely to
`StepCompletionEvaluator`'s policy, with no named quorum refusal. `recordRecipientDecline()` (`Envelope.php:1248`)
is now the **relayed, convergent no-op** path (per TASK-048 D-T5): it returns silently once the leg is
terminal and throws only on the impossible case (an unadmitted decline reaching it), never on a quorum step by
name. The only remaining code that refuses a quorum-step decline is `SigningSession::guardDecline()`'s
`stepIsQuorum` parameter, invoked from **two** call sites inside `DeclineSignatureUseCase.php` (the pre-check
at line 95-99, and again inside `session->decline()` itself at line 110-116) — which is plausibly what "both
refusals" means, but the task text does not say so and could be read as "Envelope-side + Session-side." No
practical risk: the parked patch (`task-050-quorum-decline-retirement.patch`) already targets exactly the
correct (Session-only) scope and applies cleanly against the current tree, so an implementer who works from
the patch rather than the prose is unaffected. `Category: false-claim, severity: warn.`

**b) §3.3 — "`Step::isQuorumStep()` (also called by `Step::isQuorumMet()` and `StepCompletionEvaluator`) ...
serve the two refusals removed here; each carrier goes with them unless the predicate reuses it."**

`StepCompletionEvaluator` does **not** call `Step::isQuorumStep()`/`isQuorumMet()` — it operates entirely over
`StepSnapshot`/`StepPolicy`/`Completion`, a pure-domain-service layer with no reference to the `Step` entity.
Grepped for every caller of `isQuorumStep()`/`isQuorumMet()` in `src/`+`tests/`: the only hits outside
`Step.php` itself are `StepTest.php` (the entity's own unit test) and one `@see` docblock reference in
`EnvelopeContextView.php`. No production caller exists. This could send an implementer looking inside
`StepCompletionEvaluator` for a call to remove that isn't there. The actual carriers that do need removing —
`EnvelopeContextView::recipientStepIsQuorum()`, `RecipientEnvelopeContextView::$recipientStepIsQuorum`,
`RecipientAuthContext::$recipientStepIsQuorum`, `RecipientAuthContextReader`, `DeclineSignatureUseCase`,
`SigningSession::guardDecline()`/`decline()` — are correctly named elsewhere in the same paragraph and are
exactly what the parked patch touches. `Category: false-claim, severity: warn.`

## 4. Mechanisms the task leans on — opened and confirmed

- **"Every clock only closes a step and evaluates it here" (ADR-0073 §2.4).** Opened
  `EnvelopeEndingEvaluator::clock()` end to end (lines 165-214): it already implements *both* step-deadline
  closing and expiry-as-last-deadline in one function, releasing pending blocking members, calling
  `StepCompletionEvaluator::evaluate()`, and handling the "no step open, later step outstanding" case exactly
  as ADR-0073 §2.12 describes. This is real, already-written logic — TASK-050's remaining work here is
  persistence + wiring (a deadline column, a caller), not fresh algorithm design.
- **Close-now independence.** `EnvelopeEndingEvaluator::closeNow()` (lines 216-223) requires only
  `$envelope->securedAt !== null` — no clock, no deadline, no dependency on TASK-049's sweep whatsoever. This
  directly supports the dependency mapping in §5 below.
- **`ReleaseReasons::reasonFor()` first-match order** (lines 27-54) matches ADR-0073 §2.8's declared order
  exactly: `NOT_REQUIRED → INTEGRATOR_NO_ACT → OPENED_NO_ACT → DELIVERY_FAILED → UNCLAIMED → NOT_REACHED →
  LINK_EXPIRED → SENT_NO_RESPONSE`.
- **ADR-0064's "webhook catalog" TASK-050 §3.5 amends is itself unbuilt.** `ADR-0064` (outbound integrator
  webhooks) Status: `Proposed — nothing exercised... No src/F5Sign/Webhook/ tree exists`. TASK-050's
  "excluded from ADR-0064 §2.4's webhook catalog" (§3.5, `EnvelopeClosedBySender`) is therefore a pure-text
  amendment to a still-hypothetical catalog inside another Proposed ADR, not a runtime dependency — TASK-050's
  own Verification section (§5) names no webhook test, so this does not block or complicate implementation.
  Noted so an implementer does not go looking for webhook-delivery code to update. Not scored as an issue.

## 5. TASK-049 dependency mapping (as requested)

### Genuinely dependent on TASK-049's per-envelope command / funnel

| § | What | Why it needs TASK-049 | Files |
|---|---|---|---|
| §3.4 (deadline half) | "Release at a step's close" via `released_by: STEP_DEADLINE` | Task text names it directly: "by its deadline (**TASK-049's command**, before the expiry)". Needs a real caller to fire `TriggerKind::CLOCK` for a step deadline in production. | TASK-049's not-yet-existing per-envelope command (likely `Envelope/Application/Command/...` + a Messenger/Scheduler handler) |
| §3.6 | "The sweep reaches step deadlines" | Explicit, named: "TASK-049's funnel widens to tenants with a due step deadline, and its per-envelope command's slot for closing due steps is filled here". TASK-049 must exist first to have a slot to fill. | TASK-049's funnel (`SECURITY DEFINER` fn + dedicated `NOBYPASSRLS` role, per ADR-0073 §2.13) and per-envelope command |
| Delivery bar (d), (e), (g), (h) at HTTP | Step-deadline-driven `RELEASED` outcomes, live over HTTP | Need the real worker/scheduler consuming the schedule (TASK-049's `f5sign-infra` change) for an end-to-end bar, not just the pure-evaluator tier (already green, §1) | infra worker wiring (outside this repo per TASK-049 Sibling row) |
| Delivery bar (j) | Expiry closing a step with no deadline | Pure TASK-049 mechanism (expiry is "the last deadline") — no step-deadline column even involved | TASK-049's expiry sweep entirely |
| §5 "Same facts, same outcome" **at the aggregate/HTTP tier** | Comparing a real step-deadline close against a real expiry close | Needs both clocks reachable through the sweep; already proven at the pure-evaluator tier independent of both tasks (`StepCompletionEvaluatorTest::everyClosedStep`, §1 above) | TASK-049's command (both paths) |
| §5 "Two processes: a commit admitted just before the deadline command counts" | Needs TASK-049's per-envelope command as the concrete second actor to race | TASK-049's command class |

### Buildable BEFORE or IN PARALLEL with TASK-049, from 048's tip

| § | What | Files |
|---|---|---|
| §3.1 | Step route accepts `completion`/`veto`/`deadline`; `send()` refusals (unanimity, blocking-role count, no-blocking-member, `IN_PERSON_HOST`/`CERTIFIED_DELIVERY`) — the refusal logic already exists in `refusalsAtSend()`; migration adds veto/deadline columns + `CHECK`; `RosterStepShape` gains members | `src/F5Sign/Envelope/UI/Http/Request/AddStepRequest.php`, the `AddStep` command/handler, `src/F5Sign/Envelope/Domain/Aggregate/Envelope.php` (`addStep()`, `send()`), `src/F5Sign/Envelope/Domain/Entity/Step.php`, `src/F5Sign/Envelope/Contract/Event/EnvelopeRosterDeclared.php`, a new migration, `config/packages/nelmio_api_doc.yaml` |
| §3.2 | Flip the aggregate from `InformationalMembers::HOLD_THEIR_STEP` to `NEVER_HOLD`, delete the enum, refuse an informational commit by name in Session's commit use cases — no clock involved, purely admission-time | `src/F5Sign/Envelope/Domain/Aggregate/Envelope.php:2475-2535`, `src/F5Sign/Envelope/Domain/Service/InformationalMembers.php` (delete), `StepCompletionEvaluator.php` (ctor default), `src/F5Sign/Session/Application/UseCase/CommitSignatureUseCase.php` / `CommitDelegatedSignatureUseCase.php`, `tests/.../EnvelopeEndingStoriesTest.php` (extend `EXPECTED`/simplify the filter for non-clock stories) |
| §3.3 | Retire `DECLINE_NOT_OFFERED_IN_QUORUM_STEP` and its carriers — a decline is evaluated at admission, never by a clock | Exactly the files in `task-050-quorum-decline-retirement.patch` (already prepared, applies cleanly) |
| §3.4 (non-deadline half) | New `RecipientReleased` → Session per-recipient revocation reactor, mirroring `OnEnvelopeVoided`; reacts to any release regardless of cause, so it can be built/tested using close-now- or decline-triggered releases alone | new `Session/Application/Subscriber/OnRecipientReleased.php` + Messenger adapter, new `RevokeRecipientSessions` command (mirroring `RevokeEnvelopeSessions`) |
| §3.5 | Close now — confirmed independent (`closeNow()` needs only `securedAt !== null`) | new sender route/controller, `Envelope.php` close-now wiring, new `EnvelopeClosedBySender` event (does not exist yet) |
| §3.7 (mostly) | Step view publishing policy/veto/deadline; `EnvelopeCompleted`'s declined/released payload already exists (TASK-048); the copy-ready notice extension (link minting + `NOT_AGREED`/step-activated branch) reacts to `outcome`/`closed_at`/step-activation, all producible via close-now or a decline without any sweep; claim refusal on "step deadline has passed" is a synchronous `app_now()` comparison, not dependent on the sweep having run | `NotifyCompletedEnvelopeRecipientsUseCase.php`, `NotificationPurpose.php`'s exhaustive predicates, the step read-model view, `ClaimRecipientUseCase`-adjacent code |
| Delivery bar (a), (b), (c), (f), (i) | Decline/veto/close-now/informational-step mechanics only, no clock | already-existing HTTP routes + the above |

Note: the pure-evaluator-tier "same facts, same outcome" census (§1 above, `StepCompletionEvaluatorTest`) is
already complete and needs no change from either task.

## 6. Verification bars — meetability

No bar was found unmeetable. All rely on infrastructure that either already exists (two-process harness,
OpenAPI census scaffolding, the reconcile command referenced in `var/task-runner/TASK-048/plan.md` D-T14 —
`app:envelope:reconcile-endings`, confirmed present) or is explicitly and correctly scoped as TASK-049's to
build first (§5 above). The "scenario catalog stays green... the HTTP bars included" bar currently has a
narrow, correctly-named starting point (`EnvelopeEndingStoriesTest`'s `EXPECTED`/`isWithoutClocksOrPolicyFlags()`)
rather than being a false present-tense claim.

## 7. External systems

None of this task's scope touches EU DSS, SMS/mail delivery, or a browser-only property. Not applicable.

## 8. Contradictions

None found. Cross-checked ADR-0057 §2.11/§2.12/§2.17 (unclaimed-slot stall, claim-refused predicate,
certified-delivery-slot permission) — all three sections exist with exactly the content TASK-050/ADR-0073
attribute to them. No contradiction with an accepted ADR TASK-050 doesn't declare amending was found.
